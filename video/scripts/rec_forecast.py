"""Records the Fire weather outlook strip (cedrus-forecast worktree, commit 101b572) for Lebanon, opening 'Day by day'."""
import asyncio, sys
from playwright.async_api import async_playwright
from vrec import Shot, CLOCK_JS, CURSOR_JS, box
URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8064/"
async def main():
    async with async_playwright() as p:
        b = await p.chromium.launch(headless=False, args=["--window-size=1920,1080", "--hide-scrollbars"])
        ctx = await b.new_context(viewport={"width": 1920, "height": 1080}, device_scale_factor=1.5, accept_downloads=True)
        pg = await ctx.new_page(); await pg.add_init_script(CLOCK_JS); await pg.goto(URL)
        for _ in range(120):
            if await pg.evaluate("!!(window.cedrus && window.cedrus.state && window.cedrus.state.monthly)"): break
            await asyncio.sleep(0.5)
        await pg.add_style_tag(content="::-webkit-scrollbar{display:none}")
        await pg.evaluate("document.querySelector('#explore').scrollIntoView()"); await asyncio.sleep(2)
        await pg.click("#example-lebanon")
        for _ in range(80):
            if await pg.evaluate("(()=>{const w=document.querySelector('#wx');return w&&!w.hidden&&!/loading|off/.test(w.className)&&w.dataset.region==='lebanon'})()"): break
            await asyncio.sleep(0.5)
        await asyncio.sleep(3)
        await pg.evaluate("scrollTo(0, document.querySelector('#wx').getBoundingClientRect().top + scrollY - 200)"); await asyncio.sleep(1)
        await pg.evaluate(CURSOR_JS)
        x, y = await box(pg, "#wx .wx-more summary")
        s = Shot("forecast", 13, scale=1.5); s.pos = (x + 300, y + 260)
        t = s.move(4.0, x, y, 1.0); s.click(t + 0.2)
        await s.run(pg); print(await pg.evaluate("document.querySelector('#wx').innerText.slice(0,300)"))
        # CSV export shot: the download fold in 'Your area'
        await pg.evaluate("scrollTo(0, document.querySelector('#area-form').getBoundingClientRect().top + scrollY - 80)")
        for _ in range(30): await pg.evaluate("window.__step(1000/30)")
        x1, y1 = await box(pg, "#more-download summary")
        c = Shot("csv", 7, scale=1.5); c.pos = (x1 + 380, y1 - 120); t = c.move(0.4, x1, y1, 0.9); c.click(t + 0.2)
        async def go_btn(page):
            bx, by = await box(page, "#csv-burning"); c.path.append((2.4, 3.2, (x1, y1), (bx, by))); c.click(3.5)
        c.at(1.9, go_btn)
        await c.run(pg)
        await b.close()
asyncio.run(main())
