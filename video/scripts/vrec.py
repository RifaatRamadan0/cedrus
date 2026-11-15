"""Frame-exact recorder: the page runs on a virtual clock (rAF, timers, performance.now, Date.now and CSS/Web Animations),
advanced 1/30 s per captured frame, so every clip is a smooth 30 fps regardless of how slow the GPU or screenshots are.
Usage: build a Shot, add timed actions, await shot.run(page)."""
import asyncio, subprocess, math
FF = r"C:\Users\hussein\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"
CLIPS = r"C:\Users\hussein\Downloads\cedrus-video\work\clips"

CLOCK_JS = r"""
(() => {
 const R = { raf: window.requestAnimationFrame.bind(window), caf: window.cancelAnimationFrame.bind(window),
   st: window.setTimeout.bind(window), ct: window.clearTimeout.bind(window), si: window.setInterval.bind(window), ci: window.clearInterval.bind(window),
   pn: performance.now.bind(performance), dn: Date.now };
 let V = false, now = 0, D0 = 0, P0 = 0;
 const rafQ = new Map(); let rid = 1e6; const timers = new Map(); let tid = 1e6;
 window.requestAnimationFrame = (cb) => { if (!V) return R.raf(cb); const id = rid++; rafQ.set(id, cb); return id; };
 window.cancelAnimationFrame = (id) => { if (id >= 1e6) rafQ.delete(id); else R.caf(id); };
 window.setTimeout = (fn, ms, ...a) => { if (!V) return R.st(fn, ms, ...a); const id = tid++; timers.set(id, { at: now + Math.max(0, +ms || 0), fn, a }); return id; };
 window.clearTimeout = (id) => { if (id >= 1e6) timers.delete(id); else R.ct(id); };
 window.setInterval = (fn, ms, ...a) => { if (!V) return R.si(fn, ms, ...a); const id = tid++; const e = Math.max(4, +ms || 0); timers.set(id, { at: now + e, fn, a, every: e }); return id; };
 window.clearInterval = (id) => { if (id >= 1e6) timers.delete(id); else R.ci(id); };
 performance.now = () => V ? now : R.pn();
 Date.now = () => V ? D0 + (now - P0) : R.dn();
 const seen = new WeakMap();
 window.__virtual = () => { if (V) return; now = R.pn(); P0 = now; D0 = R.dn(); V = true;
   for (const a of document.getAnimations()) { seen.set(a, now - (a.currentTime || 0)); a.pause(); } };
 window.__step = (ms) => {
   const target = now + ms; let guard = 0;
   for (;;) { let best = null, bid; for (const [id, t] of timers) if (t.at <= target && (!best || t.at < best.at)) { best = t; bid = id; }
     if (!best || ++guard > 2000) break; now = Math.max(now, best.at);
     if (best.every) best.at += best.every; else timers.delete(bid);
     try { typeof best.fn === 'function' ? best.fn(...best.a) : (0, eval)(best.fn); } catch (e) { console.error(e); } }
   now = target;
   const q = [...rafQ.values()]; rafQ.clear(); for (const cb of q) { try { cb(now); } catch (e) { console.error(e); } }
   for (const a of document.getAnimations()) { try { if (!seen.has(a)) seen.set(a, now - (a.currentTime || 0)); a.pause(); a.currentTime = now - seen.get(a); } catch (e) {} }
 };
})();
"""

CURSOR_JS = r"""
(() => { if (window.__fc) return; const c = document.createElement('div'); c.id='__fc';
 c.innerHTML = '<svg width="30" height="30" viewBox="0 0 24 24"><path d="M4 2l15 9-6.5 1.6L9.6 19z" fill="#fff" stroke="#111" stroke-width="1.4" stroke-linejoin="round"/></svg>';
 Object.assign(c.style,{position:'fixed',left:'0',top:'0',zIndex:2147483647,pointerEvents:'none',transform:'translate(-200px,-200px)',filter:'drop-shadow(0 2px 4px rgba(0,0,0,.6))'});
 document.documentElement.appendChild(c); window.__fc=c;
 addEventListener('mousemove', e => { c.style.transform = `translate(${e.clientX-4}px,${e.clientY-2}px)`; }, true);
 addEventListener('mousedown', e => { const r=document.createElement('div'); Object.assign(r.style,{position:'fixed',left:(e.clientX-22)+'px',top:(e.clientY-22)+'px',width:'44px',height:'44px',borderRadius:'50%',border:'3px solid #ff8a3d',zIndex:2147483646,pointerEvents:'none'});
   document.documentElement.appendChild(r); r.animate([{transform:'scale(.6)',opacity:1},{transform:'scale(1.9)',opacity:0}],{duration:550,easing:'ease-out',fill:'forwards'}); setTimeout(()=>r.remove(),600); }, true);
})();
"""

def ease(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)

class Shot:
    def __init__(self, name, seconds, scale=1.0, out_w=None):
        self.name, self.n, self.scale, self.out_w = name, int(round(seconds * 30)), scale, out_w
        self.path = []       # (t0, t1, (x0,y0), (x1,y1)) cursor moves
        self.acts = []       # (t, async fn(page))
        self.pos = (2100, 900)
    def move(self, t0, x, y, dur=0.8):
        self.path.append((t0, t0 + dur, self.pos, (x, y))); self.pos = (x, y); return t0 + dur
    def click(self, t, x=None, y=None):
        async def f(pg):
            await pg.mouse.down(); await pg.mouse.up()
        self.acts.append((t, f))
    def at(self, t, fn): self.acts.append((t, fn))
    def cursor_at(self, t):
        cur = None
        for (a, b, p0, p1) in self.path:
            if t >= a: u = 1.0 if b <= a else ease((t - a) / (b - a)); cur = (p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u)
        return cur
    async def run(self, page, crf=16):
        vf = (f"scale={self.out_w}:-2:flags=lanczos," if self.out_w else "") + "format=yuv420p"
        p = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", "30", "-c:v", "mjpeg", "-i", "-",
            "-vf", vf, "-c:v", "libx264", "-preset", "fast", "-crf", str(crf), "-r", "30", rf"{CLIPS}\{self.name}.mp4"], stdin=subprocess.PIPE)
        await page.evaluate("window.__virtual()")
        acts = sorted(self.acts, key=lambda a: a[0]); k = 0; last = None
        for i in range(self.n):
            t = i / 30
            c = self.cursor_at(t)
            if c and c != last: await page.mouse.move(c[0], c[1]); last = c
            while k < len(acts) and acts[k][0] <= t: await acts[k][1](page); k += 1
            if getattr(self, '_hook', None): await self._hook(t)
            if getattr(self, 'waitmap', False) and any(a <= t < b for a, b in self.waitmap):
                for _ in range(20):
                    if await page.evaluate("(()=>{const m=window.cedrus&&window.cedrus.state.map;return !m||(m.loaded()&&m.areTilesLoaded())})()"): break
                    await page.evaluate("window.__step(0)"); await asyncio.sleep(0.12)
            await page.evaluate("window.__step(1000/30)")
            p.stdin.write(await page.screenshot(type="jpeg", quality=93))
            if i % 150 == 0: print(self.name, i, "/", self.n, flush=True)
        p.stdin.close(); p.wait(); print(self.name, "done", flush=True)

async def box(page, sel, dx=0.5, dy=0.5):
    b = await page.locator(sel).first.bounding_box(); return (b["x"] + b["width"] * dx, b["y"] + b["height"] * dy)
