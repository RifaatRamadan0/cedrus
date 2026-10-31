"""Headless check of the website: loads, renders, toggles, draws, downloads, and compares the two CSVs.

    python tools/probe_site.py              # serves web/ itself on the first free port from 8765
    python tools/probe_site.py --url http://localhost:8000/

Needs Python Playwright and Chrome (C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe by default).
Screenshots go to tools/shots/. Exit code 1 if any check fails.
"""
import argparse
import http.server
import io
import socket
import socketserver
import sys
import threading
import time
from functools import partial
from pathlib import Path

import numpy as np
import pandas as pd
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SHOTS = ROOT / "tools" / "shots"
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""), flush=True)
    return ok


def free_port(start=8765):
    for port in range(start, start + 50):
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise SystemExit("no free port")


class Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve(port):
    handler = partial(Quiet, directory=str(ROOT / "web"))
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


# Records when the calendar first has cells, measured from navigation start.
INIT = r"""
new MutationObserver((_, obs) => {
  const g = document.getElementById('cal-grid');
  if (g && g.dataset.cells && !window.__calendarAt) { window.__calendarAt = performance.now(); obs.disconnect(); }
}).observe(document, { subtree: true, childList: true, attributes: true });
"""


def download(page, button, dest):
    with page.expect_download(timeout=120000) as info:
        page.click(button)
    path = dest / info.value.suggested_filename
    info.value.save_as(path)
    return path


def read_monthly(path):
    text = path.read_text(encoding="utf-8")
    first = text.splitlines()[0]
    return first, pd.read_csv(io.StringIO(text), comment="#")


def expected_default_month(region="portugal"):
    """Independent of app.js: the most recent month whose 2003..(year-1) median, whole region, is >= 5."""
    import json
    m = json.loads((ROOT / "web" / "data" / region / "monthly.json").read_text(encoding="utf-8"))
    total = np.array(m["m"]).sum(axis=0)
    y0, m0 = map(int, m["months"]["first"].split("-"))
    ym = [divmod(y0 * 12 + m0 - 1 + j, 12) for j in range(len(total))]
    names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    for j in range(len(total) - 1, -1, -1):
        y, mo = ym[j]
        base = [total[k] for k, (yy, mm) in enumerate(ym) if mm == mo and 2003 <= yy < y]
        if base and np.median(base) >= 5:
            return f"{names[mo]} {y}", (f"{names[ym[j - 1][1]]} {ym[j - 1][0]}" if j else None)
    return None, None


def compare_csvs(page, label, dest, expect_equal=True):
    mpath = download(page, "#csv-monthly", dest)
    hpath = download(page, "#csv-hotspots", dest)
    header, monthly = read_monthly(mpath)
    hot = pd.read_csv(hpath, low_memory=False)
    check(f"{label}: monthly CSV parses with methods line",
          header.startswith("# CEDRUS") and list(monthly.columns) == ["month", "harmonized_estimate", "p10", "p90", "naive", "background", "source_flag"],
          f"{len(monthly)} months, columns {list(monthly.columns)}")
    check(f"{label}: hotspot CSV parses", {"latitude", "longitude", "acq_date", "sensor", "source_flag", "w"} <= set(hot.columns),
          f"{len(hot)} rows, {len(hot.columns)} columns")
    a, bg = float(monthly.harmonized_estimate.sum()), float(monthly.background.sum())
    b = float(hot.w.sum()) + bg
    diff = abs(a - b)
    tol = max(1.0, 1e-4 * max(a, b))
    if expect_equal:
        check(f"{label}: sum(harmonized_estimate) == sum(hotspot w) + sum(background)", diff <= tol,
              f"monthly {a:.2f} vs hotspots {b - bg:.2f} + background {bg:.2f}, |diff| {diff:.2f}, tolerance {tol:.2f} (rounding: 2 dp per month, 4 dp per row)")
    else:
        print(f"[INFO] {label}: monthly (cell-level) {a:.2f} vs hotspots (exact area) {b:.2f}, diff {a - b:+.2f} "
              f"-- expected to differ: the calendar counts whole 0.25 deg cells", flush=True)
    flags = set(monthly.source_flag)
    check(f"{label}: flags are bridged/observed/estimated only", flags <= {"bridged", "observed", "estimated"}, str(sorted(flags)))
    return monthly, hot


def run(url, shots):
    shots.mkdir(parents=True, exist_ok=True)
    dl = shots / "downloads"
    dl.mkdir(exist_ok=True)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=True)

        # ---- cold load on a throttled "normal" connection (20 Mbit/s, 40 ms), cache off
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        cdp = ctx.new_cdp_session(page)
        cdp.send("Network.enable")
        cdp.send("Network.setCacheDisabled", {"cacheDisabled": True})
        cdp.send("Network.emulateNetworkConditions", {"offline": False, "latency": 40,
                                                       "downloadThroughput": 20e6 / 8, "uploadThroughput": 5e6 / 8})
        page.add_init_script(INIT)
        page.goto(url, wait_until="commit")
        page.wait_for_function("window.__calendarAt", timeout=60000)
        t = page.evaluate("window.__calendarAt") / 1000
        check("cold load to rendered calendar < 5 s (20 Mbit/s, 40 ms, no cache)", t < 5, f"{t:.2f} s")
        ctx.close()

        # ---- desktop
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(f"console.{m.type}: {m.text} ({m.location.get('url', '')})") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.on("response", lambda r: errors.append(f"HTTP {r.status} {r.url}") if r.status >= 400 else None)
        page.add_init_script(INIT)
        page.goto(url)
        page.evaluate("window.cedrus.ready")
        n_cells = page.locator("#cal-grid [role=gridcell]").count()
        n_nd = page.locator("#cal-grid .cal-cell.nd").count()
        n_b = page.locator("#cal-grid .cal-cell.b").count()
        n_e = page.locator("#cal-grid .cal-cell.e").count()
        check("calendar rendered: 26 years x 12 months", n_cells == 312, f"{n_cells} cells; no-data {n_nd}, bridged {n_b}, estimated {n_e}")
        check("no-data = Jan-Oct 2000 + Dec 2025 (incomplete); bridged = Nov 2000..Jun 2002; estimated = 2022-01..2025-11",
              (n_nd, n_b, n_e) == (11, 20, 47))
        check("default area is Portugal, whole region", "Portugal (whole region)" in page.inner_text("#area-summary"),
              page.inner_text("#area-summary").splitlines()[0])
        want, before = expected_default_month()
        check("default month = most recent with baseline median >= 5", want in page.inner_text("#month-title"),
              f"{page.inner_text('#month-title')} (expected {want})")
        page.wait_for_function("!document.querySelector('#cal-start').textContent.includes('…')", timeout=60000)
        print("[INFO] season (Portugal, baseline 2003-2024):", page.inner_text("#season-dates").replace("\n", " "), flush=True)
        check("season dates shown for Portugal", page.locator("#season-dates").get_attribute("data-state") == "dated",
              page.inner_text("#season-note")[:120])

        # the 2012 jump: naive vs harmonized, whole region, 2011 vs 2012 totals
        jump = page.evaluate(r"""() => { const c = window.cedrus; const s = c.state.series; const y = (yr, a) => { let t = 0; for (let m = 1; m <= 12; m++) t += a[c.indexOf(yr, m)]; return t; };
          return { h11: y(2011, s.m), h12: y(2012, s.m), n11: y(2011, s.naive), n12: y(2012, s.naive) }; }""")
        print(f"[INFO] 2011 -> 2012 totals: naive {jump['n11']:.0f} -> {jump['n12']:.0f} (x{jump['n12'] / jump['n11']:.2f}); "
              f"harmonized {jump['h11']:.0f} -> {jump['h12']:.0f} (x{jump['h12'] / jump['h11']:.2f})", flush=True)

        aug12 = "#cal-grid [data-year='2012'][data-moy='8']"
        bg_h = page.get_attribute(aug12, "style")
        page.click("#rec-naive")
        bg_n = page.get_attribute(aug12, "style")
        check("naive toggle recolours Aug 2012", bg_h != bg_n and "Naive merge" in page.inner_text("#calendar-note"), f"{bg_h} -> {bg_n}")
        page.locator(".history").screenshot(path=str(shots / "desktop_naive.png"))
        page.click("#mode-anomaly")
        page.locator(".history").screenshot(path=str(shots / "desktop_naive_anomaly.png"))
        page.click("#rec-harmonized")
        page.locator(".history").screenshot(path=str(shots / "desktop_harmonized_anomaly.png"))
        check("anomaly mode: PuOr legend vs median by default, switch visible",
              "baseline median" in page.inner_text("#calendar-legend") and page.locator("#ref-switch").is_visible()
              and "Median by default" in page.inner_text("#calendar-note"))
        before_mean = page.get_attribute(aug12, "style")
        page.click("#ref-mean")
        check("vs mean switch recolours and relabels", "baseline mean" in page.inner_text("#calendar-legend")
              and page.get_attribute(aug12, "style") != before_mean, f"{before_mean} -> {page.get_attribute(aug12, 'style')}")
        page.locator(".history").screenshot(path=str(shots / "desktop_harmonized_anomaly_mean.png"))
        page.click("#ref-median")
        page.click("#mode-counts")
        check("ref switch hidden outside anomaly mode", page.locator("#ref-switch").is_hidden())
        page.locator(".history").screenshot(path=str(shots / "desktop_counts.png"))

        # keyboard: from the selected cell, left arrow then Enter selects the month before
        page.focus("#cal-grid [tabindex='0']")
        page.keyboard.press("ArrowLeft")
        page.keyboard.press("Enter")
        check(f"keyboard: ArrowLeft + Enter selects {before}", before in page.inner_text("#month-title"), page.inner_text("#month-title"))
        page.keyboard.press("ArrowUp")
        focused = page.evaluate("document.activeElement.getAttribute('aria-label')")
        month, year = before.split()
        check("keyboard: ArrowUp moves focus a year back", focused.startswith(f"{month} {int(year) - 1}"), focused)

        # click a month and read the panel
        page.click("#cal-grid [data-year='2017'][data-moy='10']")
        body = page.inner_text("#month-panel")
        check("selected month panel: October 2017 with median, mean, rank, chance, trust",
              all(k in body for k in ("October 2017", "median", "mean", "percentile", "Chance", "Trust check")), body.replace("\n", " | ")[:400])
        page.click("#cal-grid [data-year='2024'][data-moy='9']")
        sep = page.inner_text("#month-panel")
        print("[INFO] Sep 2024 panel:", sep.replace("\n", " | ")[:900], flush=True)
        check("Sep 2024 (far above normal, narrow range relative to that distance) is Reliable", "Trust check: Reliable" in sep)
        page.click("#cal-grid [data-year='2025'][data-moy='2']")
        print("[INFO] Feb 2025 panel:", page.inner_text("#month-panel").replace("\n", " | ")[:900], flush=True)
        page.click("#cal-grid [data-year='2025'][data-moy='11']")

        # table fallback
        page.click("#table-toggle")
        rows = page.locator("#calendar-table tbody tr").count()
        check("table fallback lists every year", rows == 26 and page.locator("#cal-grid").is_hidden(), f"{rows} rows")
        page.click("#table-toggle")

        # ---- whole-region CSVs: monthly total must equal the hotspot weights
        page.select_option("#csv-from", "2000")
        page.select_option("#csv-to", "2025")
        compare_csvs(page, "Portugal whole region 2000-2025", dl)

        # ---- grid-aligned rectangle (cell approximation exact) through the same entry point the draw tool calls
        ring = [[-8.5, 39.5], [-7.5, 39.5], [-7.5, 40.5], [-8.5, 40.5], [-8.5, 39.5]]
        ok = page.evaluate("ring => window.cedrus.useRing(ring, 'rectangle')", ring)
        check("grid-aligned rectangle accepted", ok, page.inner_text("#area-summary").replace("\n", " ")[:160])
        page.select_option("#csv-from", "2010")
        page.select_option("#csv-to", "2025")
        compare_csvs(page, "grid-aligned rectangle 2010-2025", dl)

        # ---- draw a rectangle with the mouse (terra-draw)
        page.wait_for_selector("#map-panel[data-draw=ready]", timeout=60000)
        page.click("#draw-clear")
        page.wait_for_timeout(900)
        page.click("#draw-rectangle")
        pts = page.evaluate(r"""() => { const m = window.cedrus.state.map; const r = m.getCanvas().getBoundingClientRect();
          return [[-8.9, 38.3], [-7.9, 39.1]].map(([x, y]) => { const p = m.project([x, y]); return [r.left + p.x, r.top + p.y]; }); }""")
        page.mouse.move(*pts[0]); page.mouse.click(*pts[0])
        page.mouse.move(*pts[1], steps=8); page.mouse.click(*pts[1])
        page.wait_for_function("document.querySelector('#area-summary').textContent.includes('drawn rectangle')", timeout=10000)
        check("mouse-drawn rectangle becomes the area", True, page.inner_text("#area-summary").replace("\n", " ")[:200])
        page.wait_for_timeout(900)
        page.screenshot(path=str(shots / "desktop_drawn_rectangle.png"), full_page=True)
        compare_csvs(page, "mouse-drawn rectangle 2010-2025", dl, expect_equal=False)

        # ---- lat/lon + radius
        page.fill("#lat", "40.2"); page.fill("#lon", "-8.4"); page.fill("#radius", "30")
        page.click("#circle-go")
        page.wait_for_function("document.querySelector('#area-summary').textContent.includes('30 km around')", timeout=10000)
        check("lat/lon/radius area", True, page.inner_text("#area-summary").replace("\n", " ")[:200])
        page.wait_for_function("!document.querySelector('#cal-start').textContent.includes('…')", timeout=60000)
        print("[INFO] season (30 km around Coimbra):", page.inner_text("#season-dates").replace("\n", " "), "|", page.inner_text("#season-note")[:160], flush=True)

        # ---- one-click Lebanon
        page.click("#example-lebanon")
        page.wait_for_function("document.querySelector('#area-summary').textContent.includes('Lebanon (whole region)')", timeout=20000)
        page.wait_for_function("!document.querySelector('#cal-start').textContent.includes('…')", timeout=60000)
        check("Lebanon calendar rendered", page.locator("#cal-grid [role=gridcell]").count() == 312)
        want_lb, _ = expected_default_month("lebanon")
        check("Lebanon default month = most recent with baseline median >= 5", want_lb in page.inner_text("#month-title"),
              f"{page.inner_text('#month-title')} (expected {want_lb})")
        print("[INFO] Lebanon month panel:", page.inner_text("#month-panel").replace("\n", " | ")[:500], flush=True)
        print("[INFO] Lebanon season:", page.inner_text("#season-dates").replace("\n", " "), "|", page.inner_text("#season-note")[:200], flush=True)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(shots / "desktop_lebanon.png"), full_page=True)
        compare_csvs(page, f"Lebanon whole region {page.input_value('#csv-from')}-{page.input_value('#csv-to')}", dl)

        # ---- methodology dialog
        page.click("button[data-dialog=methodology]")
        dlg = page.inner_text("#detail-dialog")
        check("methodology names the interim model, SHA-256 and credits",
              all(k in dlg for k in ("interim", "SHA-256", "Kiln Watch", "Agun-Panjika", "Use of AI")))
        page.screenshot(path=str(shots / "desktop_methodology.png"))
        page.click(".dialog-done")

        page.click("#example-lebanon")
        page.select_option("#region", "portugal")
        page.wait_for_function("document.querySelector('#area-summary').textContent.includes('Portugal (whole region)')", timeout=20000)
        page.wait_for_timeout(2500)
        page.screenshot(path=str(shots / "desktop.png"), full_page=True)
        ctx.close()

        # ---- mobile
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        page = ctx.new_page()
        page.on("console", lambda m: errors.append(f"mobile console.{m.type}: {m.text} ({m.location.get('url', '')})") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"mobile pageerror: {e}"))
        page.on("response", lambda r: errors.append(f"mobile HTTP {r.status} {r.url}") if r.status >= 400 else None)
        page.goto(url)
        page.evaluate("window.cedrus.ready")
        page.wait_for_timeout(2500)
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        check("mobile 390 px: no horizontal overflow", overflow <= 0, f"scrollWidth - innerWidth = {overflow}")
        cell_w = page.evaluate("document.querySelector('#cal-grid [role=gridcell]').getBoundingClientRect().width")
        check("mobile: calendar cells at least 18 px wide", cell_w >= 18, f"{cell_w:.1f} px")
        page.screenshot(path=str(shots / "mobile.png"), full_page=True)
        ctx.close()
        browser.close()

    check("no console errors", not errors, "; ".join(errors[:8]))
    return all(ok for _, ok in results)


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--url")
    args = ap.parse_args()
    httpd = None
    url = args.url
    if not url:
        port = free_port()
        httpd = serve(port)
        url = f"http://127.0.0.1:{port}/"
        print(f"serving web/ on {url}", flush=True)
    t0 = time.time()
    try:
        ok = run(url, SHOTS)
    finally:
        if httpd:
            httpd.shutdown()
    failed = [n for n, o in results if not o]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed in {time.time() - t0:.0f} s; screenshots in {SHOTS}")
    if failed:
        print("FAILED: " + "; ".join(failed))
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
