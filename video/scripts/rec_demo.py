"""One continuous frame-exact demo take of the Fire Calendar workspace at 1.5x pixel density (for sharp zoom-crops):
Lebanon -> Oct 2024 -> month card -> Hotspots/Burning days -> draw rectangle -> season card -> right-now strip -> CSV.
Prints a timing log (demo_log.txt) used by the edit."""
import asyncio, sys, json
from playwright.async_api import async_playwright
from vrec import Shot, CLOCK_JS, CURSOR_JS, ease
URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8063/"
LOG = r"C:\Users\hussein\Downloads\cedrus-video\work\demo_log.json"

class Demo(Shot):
    def __init__(self, *a, **k):
        super().__init__(*a, **k); self.scrolls = []; self.log = []
    def goto(self, t, sel, dur=0.9, dx=0.5, dy=0.5):
        async def f(pg):
            b = await pg.locator(sel).first.bounding_box(); c = self.cursor_at(t) or self.pos
            self.path.append((t, t + dur, c, (b["x"] + b["width"] * dx, b["y"] + b["height"] * dy)))
        self.at(t, f)
    def gopt(self, t, x, y, dur=0.7):
        async def f(pg):
            c = self.cursor_at(t) or self.pos; self.path.append((t, t + dur, c, (x, y)))
        self.at(t, f)
    def scroll_to(self, t, sel, dur=1.2, off=90):
        async def f(pg):
            y0 = await pg.evaluate("scrollY"); y1 = await pg.evaluate(f"document.querySelector('{sel}').getBoundingClientRect().top + scrollY - {off}")
            self.scrolls.append((t, t + dur, y0, y1))
        self.at(t, f)
    def mark(self, t, label): 
        async def f(pg): self.log.append((round(t, 2), label))
        self.at(t, f)
    async def run(self, page, crf=16):
        orig = page.evaluate
        sc = self
        async def per_frame_hook(t):
            for (a, b, y0, y1) in sc.scrolls:
                if a <= t <= b + 1/30: await page.evaluate(f"scrollTo(0,{y0 + (y1 - y0) * ease((t - a) / (b - a))})")
        self._hook = per_frame_hook
        await super().run(page, crf)

async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=False, args=["--window-size=1920,1080", "--window-position=0,0", "--hide-scrollbars"])
        ctx = await b.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1.5, accept_downloads=True)
        pg = await ctx.new_page(); await pg.add_init_script(CLOCK_JS); await pg.goto(URL)
        for _ in range(120):
            if await pg.evaluate("!!(window.cedrus && window.cedrus.state && window.cedrus.state.monthly && window.cedrus.state.draw)"): break
            await asyncio.sleep(0.5)
        await pg.add_style_tag(content="::-webkit-scrollbar{display:none}")
        await pg.evaluate("document.querySelector('#explore').scrollIntoView()"); await asyncio.sleep(4)
        await pg.evaluate(CURSOR_JS)
        await pg.evaluate("scrollTo(0, document.querySelector('#explore').getBoundingClientRect().top + scrollY - 70)"); await asyncio.sleep(1.5)
        # preload: Lebanon, a big month (Oct 2020), map fully loaded, so no shot shows an empty map
        await pg.click("#example-lebanon"); await asyncio.sleep(3)
        await pg.click('#cal-grid [data-year="2020"][data-moy="10"]')
        for _ in range(60):
            if await pg.evaluate("(()=>{const m=window.cedrus.state.map;return m&&m.loaded()&&m.areTilesLoaded()})()"): break
            await asyncio.sleep(0.5)
        await asyncio.sleep(2.5)
        s = Demo("demo", 31, scale=1.5); s.pos = (1300, 900); s.waitmap = [(2.0, 2.6), (12.0, 12.5), (15.4, 15.9), (21.8, 22.8), (24.3, 24.9)]
        s.goto(0.5, '#cal-grid [data-year="2024"][data-moy="10"]', 1.2); s.click(2.0); s.mark(2.0, "oct2024")
        s.scroll_to(4.5, "#month-panel", 1.4, 110); s.gopt(4.7, 1500, 700, 1.0); s.mark(5.9, "monthcard")
        s.scroll_to(9.5, "#area-form", 1.2, 90); s.goto(11.0, "#unit-hot", 0.9); s.click(12.0); s.mark(12.0, "hotspots")
        s.goto(14.5, "#unit-bd", 0.7); s.click(15.4); s.mark(15.4, "burningdays")
        s.goto(17.0, "#draw-rectangle", 0.9); s.click(18.0); s.mark(18.0, "rect-tool")
        s.goto(18.6, "#map", 1.0, 0.40, 0.38); s.click(20.0); s.goto(20.3, "#map", 1.3, 0.62, 0.64); s.click(21.8); s.mark(21.8, "rect-done")
        s.goto(23.0, '#cal-grid [data-year="2024"][data-moy="10"]', 1.0); s.click(24.3); s.mark(24.3, "rect-oct")
        s.scroll_to(27.0, "#explore", 1.4, 70); s.gopt(27.2, 1400, 600, 1.0); s.mark(28.4, "live")
        await s.run(pg)
        json.dump(s.log, open(LOG, "w")); print(s.log)
        await b.close()
asyncio.run(main())
