"""Records the app's 3D story stage frame-exact: (1) 'broll': clean calendar/problem/fix/any-area/season slides with page text hidden,
(2) 'tour': the orbit-slide globe region tour with its UI and cursor."""
import asyncio, sys
from playwright.async_api import async_playwright
from vrec import Shot, CLOCK_JS, CURSOR_JS, box
URL = "http://localhost:8063/"
HIDE = ".topbar,.hud,.deck-ctl,.copy,.lang-note,#satLabels{opacity:0!important}"
async def boot(p, hide):
    b = await p.chromium.launch(headless=False, args=["--window-size=1920,1080", "--window-position=0,0", "--hide-scrollbars"])
    pg = await b.new_page(viewport={"width": 1920, "height": 1080})
    await pg.add_init_script(CLOCK_JS)
    await pg.goto(URL)
    for _ in range(120):
        if await pg.evaluate("!!(window.cedrus && window.cedrus.state && window.cedrus.state.monthly)"): break
        await asyncio.sleep(0.5)
    if hide: await pg.add_style_tag(content=HIDE)
    await asyncio.sleep(3); return b, pg
async def key(pg): await pg.keyboard.press("ArrowRight")
async def main(which):
    async with async_playwright() as p:
        if which in ("broll", "all"):
            b, pg = await boot(p, True)
            g = Shot("globe_broll", 13); await g.run(pg); await pg.evaluate("window.__virtual_off && window.__virtual_off()")
            for _ in range(3): await key(pg); await pg.evaluate("window.__step(1500)"); await asyncio.sleep(0.5)
            for _ in range(60): await pg.evaluate("window.__step(1000/30)")
            s = Shot("story_broll", 31)
            for j in range(4): s.at(1 + j * 7.5, key)
            await s.run(pg); await b.close()
        if which in ("tour", "all"):
            b, pg = await boot(p, False); await pg.evaluate(CURSOR_JS)
            await pg.add_style_tag(content=".dive-hint,.keyhint{opacity:0!important}")
            for _ in range(2): await key(pg); await asyncio.sleep(2.5)
            await asyncio.sleep(4)
            x, y = await box(pg, "#tour-next")
            s = Shot("tour", 14); s.pos = (1200, 700); t = s.move(0.6, x, y, 1.0)
            for j in range(3): s.click(t + 0.2 + j * 3.8)
            await s.run(pg); await b.close()
asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "all"))
