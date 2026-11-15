"""Final compositor. Base layer: recorded clips placed on the film timeline with smooth float-precision Ken Burns crops,
dims and crossfades. Top layer: overlay/overlay.html (captions, cards, chart, mascot, grain) rendered frame-exact with alpha.
Usage: python compose.py <first_frame> <last_frame_exclusive> <out.mp4>   (run in 2 halves in parallel, then concat)."""
import sys, subprocess, asyncio, json, numpy as np
from PIL import Image, ImageChops
from playwright.async_api import async_playwright
FF = r"C:\Users\hussein\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"
V = r"C:\Users\hussein\Downloads\cedrus-video"; C = V + r"\work\clips"
FPS = 30; W, H = 1920, 1080
SIZES = {"tour": (1920, 1080), "story_broll": (1920, 1080), "demo": (2880, 1620), "csv": (2880, 1620), "forecast": (2880, 1620), "globe_broll": (1920, 1080), "nasa_sat": (1920, 1080), "nasa_fire": (1920, 1080)}
# (film_start, film_end, clip, src_at_film_start, [(film_t, cx, cy, zoom)], fade_in, dim)
SEG = [
    (0.0, 7.8, "nasa_sat", 0.0, [(0, .5, .5, 1.0), (7.8, .5, .5, 1.08)], 1.0, 0.68),
    (7.4, 11.4, "nasa_fire", 1.5, [(7.4, .5, .5, 1.0), (11.4, .5, .5, 1.1)], 0.4, 0.6),
    (11.2, 17.3, "story_broll", 1.2, [(11.2, .5, .5, 1.0), (17.3, .56, .5, 1.18)], 0.5, 0.55),
    (32.2, 39.8, "story_broll", 8.6, [(32.2, .5, .5, 1.05), (39.8, .6, .52, 1.25)], 0.6, 0.5),
    (39.4, 45.4, "story_broll", 23.4, [(39.4, .5, .5, 1.0), (45.4, .5, .5, 1.15)], 0.5, 0.5),
    (45.0, 52.2, "tour", 7.0, [(45.0, .5, .5, 1.0), (52.2, .45, .62, 1.12)], 0.5, 1.0),
    (52.0, 61.7, "demo", 0.0, [(52.0, .5, .5, 1.0), (52.4, .5, .5, 1.0), (53.4, .74, .75, 1.7), (56.6, .74, .75, 1.7), (58.0, .24, .26, 1.9), (61.7, .24, .26, 1.95)], 0.4, 1.0),
    (61.5, 67.5, "demo", 10.7, [(61.5, .42, .4, 1.3), (67.5, .4, .4, 1.36)], 0.35, 1.0),
    (67.3, 76.8, "demo", 17.2, [(67.3, .36, .45, 1.35), (76.8, .4, .48, 1.45)], 0.35, 1.0),
    (76.6, 80.2, "demo", 6.0, [(76.6, .48, .25, 2.3), (80.2, .48, .25, 2.5)], 0.35, 1.0),
    (80.0, 83.6, "demo", 27.6, [(80.0, .3, .32, 2.0), (83.6, .3, .32, 2.15)], 0.35, 1.0),
    (83.4, 86.8, "csv", 1.2, [(83.4, .2, .6, 1.9), (86.8, .2, .62, 2.1)], 0.35, 1.0),
    (86.6, 97.8, "forecast", 1.0, [(86.6, .33, .26, 1.75), (89.0, .35, .26, 1.75), (90.3, .72, .25, 1.75), (91.6, .72, .25, 1.75), (93.0, .3, .34, 1.9), (97.8, .3, .34, 2.0)], 0.4, 1.0),
]
GRAIN = [Image.fromarray(np.repeat(np.clip(np.random.default_rng(k).normal(8, 4, (H, W, 1)), 0, 16).astype(np.uint8), 3, 2)) for k in range(6)]  # subtle film grain (mean 8, offset -8)
def kf(keys, t):
    if t <= keys[0][0]: return keys[0][1:]
    for a, b in zip(keys, keys[1:]):
        if a[0] <= t <= b[0]:
            u = (t - a[0]) / (b[0] - a[0] or 1); u = u * u * (3 - 2 * u)
            return tuple(a[i] + (b[i] - a[i]) * u for i in (1, 2, 3))
    return keys[-1][1:]
class Dec:
    def __init__(self, clip, start):
        self.w, self.h = SIZES[clip]; self.idx = -1; self.frame = None
        self.p = subprocess.Popen([FF, "-loglevel", "error", "-ss", f"{max(0, start):.3f}", "-i", rf"{C}\{clip}.mp4", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    def get(self, i):
        while self.idx < i:
            b = self.p.stdout.read(self.w * self.h * 3)
            if len(b) < self.w * self.h * 3: break
            self.frame = Image.frombuffer("RGB", (self.w, self.h), b); self.idx += 1
        return self.frame
BLACK = Image.new("RGB", (W, H))
def base(f, decs):
    t = f / FPS; out = BLACK
    for k, (t0, t1, clip, s0, keys, fin, dim) in enumerate(SEG):
        if not (t0 <= t < t1):
            if k in decs and t >= t1: decs.pop(k).p.kill()
            continue
        if k not in decs: decs[k] = Dec(clip, s0 + (t - t0)); decs[k].f0 = f
        im = decs[k].get(f - decs[k].f0)
        if im is None: continue
        cx, cy, z = kf(keys, t); bw, bh = im.width / z, im.height / z
        x0 = min(max(cx * im.width - bw / 2, 0), im.width - bw); y0 = min(max(cy * im.height - bh / 2, 0), im.height - bh)
        fr = im.resize((W, H), Image.BICUBIC, box=(x0, y0, x0 + bw, y0 + bh))
        if dim < 1: fr = Image.blend(BLACK, fr, dim)
        a = min(1.0, (t - t0) / fin) if fin else 1.0; a = a * a * (3 - 2 * a)
        out = fr if a >= 1 else Image.blend(out, fr, a)
    return out
async def main(f0, f1, outp):
    mouth = open(V + r"\work\mouth.json").read()
    enc = subprocess.Popen([FF, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
        "-c:v", "libx264", "-profile:v", "high", "-preset", "fast", "-crf", sys.argv[4] if len(sys.argv) > 4 else "18", "-pix_fmt", "yuv420p", outp], stdin=subprocess.PIPE)
    async with async_playwright() as p:
        b = await p.chromium.launch(); pg = await b.new_page(viewport={"width": W, "height": H})
        await pg.add_init_script(f"window.__MOUTH = {mouth};")
        await pg.goto("file:///" + V.replace("\\", "/") + "/overlay/overlay.html"); await pg.wait_for_timeout(2500)
        await pg.evaluate("document.fonts.ready")
        cdp = await pg.context.new_cdp_session(pg)
        await cdp.send("Emulation.setDefaultBackgroundColorOverride", {"color": {"r": 0, "g": 0, "b": 0, "a": 0}})
        decs = {}
        for f in range(f0, f1):
            await pg.evaluate(f"render({f / FPS})")
            shot = await cdp.send("Page.captureScreenshot", {"format": "png", "optimizeForSpeed": True})
            ov = Image.open(__import__("io").BytesIO(__import__("base64").b64decode(shot["data"]))).convert("RGBA")
            fr = Image.alpha_composite(base(f, decs).convert("RGBA"), ov).convert("RGB")
            fr = ImageChops.add(fr, GRAIN[f % 6], 1.0, -8)
            enc.stdin.write(fr.tobytes())
            if f % 150 == 0: print(outp[-12:], f, flush=True)
        await b.close()
    enc.stdin.close(); enc.wait()
if __name__ == "__main__":
    asyncio.run(main(int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]))
