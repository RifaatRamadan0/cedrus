"""Headless check of the website: loads, renders, toggles, draws, downloads, and compares the two CSVs.

    python tools/probe_site.py              # serves web/ itself on the first free port from 8765
    python tools/probe_site.py --url http://localhost:8000/

Needs Python Playwright and Chrome (C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe by default).
Screenshots go to tools/shots/. Exit code 1 if any check fails.
"""
import argparse
import http.server
import io
import json
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
NAMES = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

results = []


def check(name, ok, detail=""):
    results.append((name, bool(ok)))
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" :: {detail}" if detail else ""), flush=True)
    return ok


def info(text):
    print(f"[INFO] {text}", flush=True)


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


# Records, from navigation start: when the calendar first has cells, when the hero video first plays,
# and the state of the map panel, draw buttons and video at the moment the calendar first appears.
INIT = r"""
new MutationObserver((_, obs) => {
  const g = document.getElementById('cal-grid');
  if (g && g.dataset.cells && !window.__calendarAt) {
    window.__calendarAt = performance.now(); obs.disconnect();
    const v = document.querySelector('.hero-video');
    window.__atParse = { loading: document.getElementById('map-loading')?.textContent || '',
      drawDisabled: document.getElementById('draw-rectangle')?.disabled, hint: document.getElementById('draw-hint')?.textContent,
      preload: v?.getAttribute('preload'), autoplay: v?.hasAttribute('autoplay') };
  }
}).observe(document, { subtree: true, childList: true, attributes: true });
document.addEventListener('play', () => { if (!window.__playAt) window.__playAt = performance.now(); }, true);
"""


def download(page, button, dest):
    with page.expect_download(timeout=180000) as dl:
        page.click(button)
    path = dest / dl.value.suggested_filename
    dl.value.save_as(path)
    return path


def read_monthly(path):
    text = path.read_text(encoding="utf-8")
    return text.splitlines()[0], pd.read_csv(io.StringIO(text), comment="#")


def expected_default_month(region="portugal"):
    """Independent of app.js: the most recent month with >= 5 baseline years (2003..year-1) and a median >= 5,
    whole region."""
    m = json.loads((ROOT / "web" / "data" / region / "monthly.json").read_text(encoding="utf-8"))
    total = np.array(m["m"]).sum(axis=0)
    y0, m0 = map(int, m["months"]["first"].split("-"))
    ym = [divmod(y0 * 12 + m0 - 1 + j, 12) for j in range(len(total))]
    for j in range(len(total) - 1, -1, -1):
        y, mo = ym[j]
        base = [total[k] for k, (yy, mm) in enumerate(ym) if mm == mo and 2003 <= yy < y]
        if len(base) >= 5 and np.median(base) >= 5:
            prev = ym[j - 1]
            return f"{NAMES[mo]} {y}", f"{NAMES[prev[1]]} {prev[0]}"
    return None, None


def rounding_bound(region):
    """Whole-region calendar = sum of cell values rounded to 2 dp; hotspot w are rounded to 4 dp."""
    m = np.array(json.loads((ROOT / "web" / "data" / region / "monthly.json").read_text(encoding="utf-8"))["m"])
    n_frac = int((np.abs(m - np.round(m)) > 1e-9).sum())
    rows = sum(json.loads(f.read_text(encoding="utf-8"))["n"] for f in (ROOT / "web" / "data" / region / "hotspots").glob("*.json"))
    return 0.005 * n_frac + 0.00005 * rows


def compare_csvs(page, label, dest, tol=None):
    mpath = download(page, "#csv-monthly", dest)
    hpath = download(page, "#csv-hotspots", dest)
    header, monthly = read_monthly(mpath)
    hot = pd.read_csv(hpath, low_memory=False, dtype={"version": str, "acq_date": str})
    check(f"{label}: monthly CSV parses with methods line",
          header.startswith("# CEDRUS") and list(monthly.columns) == ["month", "harmonized_estimate", "p10", "p90", "naive", "background", "source_flag"],
          f"{len(monthly)} months")
    check(f"{label}: hotspot CSV parses", {"latitude", "longitude", "acq_date", "sensor", "source_flag", "w", "version"} <= set(hot.columns),
          f"{len(hot)} rows, {len(hot.columns)} columns")
    a, bg = float(monthly.harmonized_estimate.sum()), float(monthly.background.sum())
    b = float(hot.w.sum()) + bg
    why = "rounding bound of 2-dp cell values" if tol is not None else "exact area: both sides add the same 4-dp weights"
    tol = 0.01 if tol is None else tol
    check(f"{label}: calendar sum == hotspot CSV sum(w) + background", abs(a - b) <= tol,
          f"calendar {a:.4f} vs hotspots {b - bg:.4f} + background {bg:.4f}, |diff| {abs(a - b):.4f}, tolerance {tol:.4f} ({why})")
    flags = set(monthly.source_flag)
    known = ("bridged", "observed", "estimated (S-NPP+NOAA-20)", "estimated (S-NPP only)", "estimated (NOAA-20 only)")
    bases = {next((k for k in known if f == k or f.startswith(k + " (")), None) for f in flags}
    check(f"{label}: source flags are the documented ones (plus the combination note)", None not in bases, str(sorted(flags))[:200])
    return monthly, hot


def month_matches(monthly, hot, month, label):
    """One month: the monthly CSV value against the hotspot CSV's weights in that month plus its background."""
    row = monthly[monthly.month == month]
    a, bg = float(row.harmonized_estimate.sum()), float(row.background.sum())
    b = float(hot.loc[hot.acq_date.str[:7] == month, "w"].sum())
    check(f"{label}: {month} calendar == sum(w) of its detections + background", abs(a - (b + bg)) <= 0.01,
          f"{a:.4f} vs {b:.4f} + {bg:.4f}")
    return a


def circle(page, lat, lon, km):
    page.fill("#lat", str(lat)); page.fill("#lon", str(lon)); page.fill("#radius", str(km))
    page.click("#circle-go")
    page.wait_for_function(f"document.querySelector('#area-summary').textContent.includes('{km} km around')"
                           " && !document.querySelector('#area-summary').textContent.includes('Reading')", timeout=120000)


def wait_season(page):
    page.wait_for_function("!document.querySelector('#cal-start').textContent.includes('…')", timeout=120000)


def model_checks():
    """Model A in the data, its fit windows, and its refusal to be fitted on 2020 or later."""
    idx = json.loads((ROOT / "web" / "data" / "regions.json").read_text(encoding="utf-8"))
    names = {r["id"]: r["model"] for r in idx["regions"]}
    check("regions.json: model is A, the bake-off winner, in every region", set(names.values()) == {"A — shrinkage ratio (bake-off winner)"}, str(names))
    wins = {r["id"]: {k: v["train"] for k, v in r["model_detail"]["satellites"].items()} for r in idx["regions"]}
    ok = all(w == {"snpp": ["2012-02", "2019-12"], "noaa20": ["2018-04", "2019-12"]} for w in wins.values())
    check("model A fit windows: Suomi NPP 2012-02..2019-12, NOAA-20 2018-04..2019-12", ok, str(wins))
    sys.path.insert(0, str(ROOT / "pipeline"))
    import weights_a
    saved = dict(weights_a.TRAIN)
    det = pd.DataFrame({"month": ["2019-12", "2020-01"], "moy": [12, 1], "dn": ["D", "D"], "fam": ["snpp", "modis"], "ci": [0, 0]})
    try:
        weights_a.TRAIN["snpp"] = ("2012-02", "2020-03")
        try:
            weights_a.fit(det, "probe")
            refused = False
        except AssertionError:
            refused = True
    finally:
        weights_a.TRAIN.clear(); weights_a.TRAIN.update(saved)
    check("model A refuses a fit window reaching into 2020", refused)

    # Combination rule: a satellite enters a slot's average only where A's prior ratio r0 > 0.
    bad = [(r["id"], slot, f) for r in idx["regions"] for slot, sats in r["combination"]["slots_when_both_cover"].items()
           for f in sats if not r["model_detail"]["satellites"][f]["prior_ratio_r0"][slot] > 0]
    check("combination rule: no slot's average includes a satellite with r0 = 0", not bad, str(bad[:5]))
    # Lebanon December days: NOAA-20's r0 is 0, so Suomi NPP carries the slot alone in 2022-2024 (both satellites fly)
    # exactly as in Dec 2025 (Suomi NPP only): one weight per cell, not halved; NOAA-20 weighs 0 there.
    w_n, w_j = {}, []
    for y in (2022, 2023, 2024, 2025):
        h = json.loads((ROOT / "web/data/lebanon/hotspots" / f"{y}.json").read_text(encoding="utf-8"))["cols"]
        for i in range(len(h["lat"])):
            if h["doy"][i] < 335 or h["dn"][i] != 0:
                continue  # December starts on day 335 in these years (336 in 2024 is still December)
            if pd.Timestamp(y, 1, 1) + pd.Timedelta(days=h["doy"][i] - 1) < pd.Timestamp(y, 12, 1):
                continue
            cell = (int(np.floor(h["lon"][i] / 0.25)), int(np.floor(h["lat"][i] / 0.25)))
            if h["sensor"][i] == 2:
                w_n.setdefault(cell, set()).add((y == 2025, h["w"][i]))
            elif h["sensor"][i] == 3:
                w_j.append(h["w"][i])
    same = [c for c, v in w_n.items() if len({w for _, w in v}) == 1 and {flag for flag, _ in v} == {True, False}]
    differ = [c for c, v in w_n.items() if len({w for _, w in v}) > 1]
    check("Lebanon December days: S-NPP weight in 2022-24 (both fly) equals its Dec 2025 weight (S-NPP only); NOAA-20 weighs 0",
          same and not differ and all(w == 0 for w in w_j), f"{len(same)} cells compared, {len(differ)} differ; {len(w_j)} NOAA-20 rows, max w {max(w_j, default=0)}")


def run(url, shots):
    model_checks()
    shots.mkdir(parents=True, exist_ok=True)
    dl = shots / "downloads"
    dl.mkdir(exist_ok=True)
    errors = []

    def watch(page, tag=""):
        page.on("console", lambda m: errors.append(f"{tag}console.{m.type}: {m.text} ({m.location.get('url', '')})") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"{tag}pageerror: {e}"))
        page.on("response", lambda r: errors.append(f"{tag}HTTP {r.status} {r.url}") if r.status >= 400 else None)

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, headless=True)

        # ---- cold load on a throttled "normal" connection (20 Mbit/s, 40 ms), cache off
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        watch(page, "cold ")
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
        at = page.evaluate("window.__atParse")
        check("map loading state when the calendar appears: 'Loading map…', draw buttons disabled with a matching hint",
              at["loading"].startswith("Loading map") and at["drawDisabled"] and "load with the map" in at["hint"], str(at))
        served = page.request.get(url).text()
        tag = served[served.index("<video"):served.index(">", served.index("<video")) + 1]
        check("hero video as served: preload=none and no autoplay attribute", 'preload="none"' in tag and "autoplay" not in tag, tag[:120])
        page.wait_for_timeout(2500)
        play_at = page.evaluate("window.__playAt || null")
        check("hero video starts only after the calendar rendered", play_at is not None and play_at >= page.evaluate("window.__calendarAt"),
              f"calendar {t:.2f} s, video play {'never' if play_at is None else f'{play_at / 1000:.2f} s'}")
        ctx.close()

        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, reduced_motion="reduce")
        page = ctx.new_page()
        page.add_init_script(INIT)
        page.goto(url, wait_until="commit")  # the calendar does not wait for CDN scripts; neither does the probe
        page.wait_for_function("window.cedrus", timeout=60000); page.evaluate("window.cedrus.ready")
        page.wait_for_timeout(2000)
        check("reduced motion: hero video never plays", page.evaluate("!window.__playAt && document.querySelector('.hero-video').paused"))
        ctx.close()

        # ---- desktop
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        page = ctx.new_page()
        watch(page)
        page.add_init_script(INIT)
        page.goto(url, wait_until="commit")  # the calendar does not wait for CDN scripts; neither does the probe
        page.wait_for_function("window.cedrus", timeout=60000); page.evaluate("window.cedrus.ready")
        n_cells = page.locator("#cal-grid [role=gridcell]").count()
        n_nd = page.locator("#cal-grid .cal-cell.nd").count()
        n_b = page.locator("#cal-grid .cal-cell.b").count()
        n_e = page.locator("#cal-grid .cal-cell.e").count()
        check("calendar rendered: 26 years x 12 months", n_cells == 312, f"{n_cells} cells; no-data {n_nd}, bridged {n_b}, estimated {n_e}")
        check("record runs to Dec 2025: no-data = Jan-Oct 2000 only; bridged Nov 2000..Jun 2002; estimated 2022-01..2025-12",
              (n_nd, n_b, n_e) == (10, 20, 48))
        note = page.inner_text("#record-end-note")
        check("record-end note names the pending near-real-time key", "December 2025" in note and "near-real-time API key" in note, note)
        check("default area is Portugal, whole region", "Portugal (whole region)" in page.inner_text("#area-summary"))
        want, before = expected_default_month()
        check("default month = most recent with >= 5 baseline years and median >= 5", want in page.inner_text("#month-title"),
              f"{page.inner_text('#month-title')} (expected {want})")

        # zero = "nothing": a dark tile, not a light colour
        zero = page.evaluate(r"""() => { const z = document.querySelector('#cal-grid .cal-cell.zero'); if (!z) return null;
          const s = getComputedStyle(z); return { bg: s.backgroundColor, img: s.backgroundImage.slice(0, 40), label: z.getAttribute('aria-label') }; }""")
        if zero:
            rgb = [int(x) for x in zero["bg"][zero["bg"].index("(") + 1:zero["bg"].index(")")].split(",")[:3]]
            lum = (0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]) / 255
            check("zero months are a dark tile with a centred dot", lum < 0.15 and "radial-gradient" in zero["img"] and "no detections" in zero["label"],
                  f"{zero['bg']} luminance {lum:.2f}; {zero['label']}")
        else:
            check("zero months are a dark tile with a centred dot", False, "no zero cell in the Portugal calendar")
        wait_season(page)
        info(f"season (Portugal): {page.inner_text('#season-dates').replace(chr(10), ' ')}")
        check("season dates shown for Portugal", page.locator("#season-dates").get_attribute("data-state") == "dated")

        jump = page.evaluate(r"""() => { const c = window.cedrus; const s = c.state.series; const y = (yr, a) => { let t = 0; for (let m = 1; m <= 12; m++) t += a[c.indexOf(yr, m)]; return t; };
          return { h11: y(2011, s.m), h12: y(2012, s.m), n11: y(2011, s.naive), n12: y(2012, s.naive) }; }""")
        info(f"2011 -> 2012 totals: naive {jump['n11']:.0f} -> {jump['n12']:.0f} (x{jump['n12'] / jump['n11']:.2f}); "
             f"harmonized {jump['h11']:.0f} -> {jump['h12']:.0f} (x{jump['h12'] / jump['h11']:.2f})")

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
        check("anomaly mode: vs median by default, switch visible", "baseline median" in page.inner_text("#calendar-legend")
              and page.locator("#ref-switch").is_visible() and "Median by default" in page.inner_text("#calendar-note"))
        early = page.get_attribute("#cal-grid [data-year='2005'][data-moy='8']", "aria-label")
        check("anomaly: a month with < 5 baseline years has no anomaly colour", "not enough history" in early, early)
        grid_styles = "() => [...document.querySelectorAll('#cal-grid [role=gridcell]')].map((c) => c.getAttribute('style'))"
        before_mean = page.evaluate(grid_styles)
        page.click("#ref-mean")
        after_mean = page.evaluate(grid_styles)
        changed = sum(a != b for a, b in zip(before_mean, after_mean))
        check("vs mean switch recolours and relabels", "baseline mean" in page.inner_text("#calendar-legend") and changed > 0,
              f"{changed} of {len(after_mean)} cells changed colour")
        # the tooltip and the panel use one baseline: the mean in Aug 2019's tooltip is the panel's multi-year mean
        tip = page.get_attribute("#cal-grid [data-year='2019'][data-moy='8']", "title")
        tip_mean = tip.split(" vs ")[2].split(")")[0] if tip.count(" vs ") >= 2 else tip
        page.click("#cal-grid [data-year='2019'][data-moy='8']")
        panel_mean = page.inner_text("#month-body dl.stats div:nth-child(2) dd").split()[0]
        check("tooltip mean == panel mean (Aug 2019)", tip_mean == panel_mean, f"tooltip '{tip_mean}' vs panel '{panel_mean}' :: {tip}")
        page.locator(".history").screenshot(path=str(shots / "desktop_harmonized_anomaly_mean.png"))
        page.click("#ref-median")
        page.click("#mode-counts")
        check("ref switch hidden outside anomaly mode", page.locator("#ref-switch").is_hidden())
        page.click(f"#cal-grid [data-year='{want.split()[1]}'][data-moy='{NAMES.index(want.split()[0]) + 1}']")
        page.locator(".history").screenshot(path=str(shots / "desktop_counts.png"))

        page.focus("#cal-grid [tabindex='0']")
        page.keyboard.press("ArrowLeft")
        page.keyboard.press("Enter")
        check(f"keyboard: ArrowLeft + Enter selects {before}", before in page.inner_text("#month-title"), page.inner_text("#month-title"))
        page.keyboard.press("ArrowUp")
        focused = page.evaluate("document.activeElement.getAttribute('aria-label')")
        month, year = before.split()
        check("keyboard: ArrowUp moves focus a year back", focused.startswith(f"{month} {int(year) - 1}"), focused)

        page.click("#cal-grid [data-year='2017'][data-moy='10']")
        body = page.inner_text("#month-panel")
        check("selected month panel: October 2017 with median, mean, rank, chance, trust",
              all(k in body for k in ("October 2017", "median", "mean", "percentile", "Chance", "Trust check")))
        page.click("#cal-grid [data-year='2024'][data-moy='9']")
        sep = page.inner_text("#month-panel")
        info(f"Sep 2024 panel: {sep.replace(chr(10), ' | ')[:700]}")
        check("Sep 2024 (far above normal) is Reliable", "Trust check: Reliable" in sep)
        page.click("#cal-grid [data-year='2006'][data-moy='6']")
        check("June 2006 (3 baseline years) says 'Not enough history for a baseline'",
              "Not enough history for a baseline" in page.inner_text("#month-panel") and page.locator("#trust").count() == 0)

        page.click("#table-toggle")
        rows = page.locator("#calendar-table tbody tr").count()
        check("table fallback lists every year", rows == 26 and page.locator("#cal-grid").is_hidden(), f"{rows} rows")
        page.click("#table-toggle")

        # ---- whole region CSVs; NOAA-20 in the estimated era; version strings exactly as in FIRMS
        page.select_option("#csv-from", "2000"); page.select_option("#csv-to", "2025")
        monthly, hot = compare_csvs(page, "Portugal whole region 2000-2025", dl, rounding_bound("portugal"))
        check("model A background is in the record (bg > 0) and inside the equality above", monthly.background.sum() > 0,
              f"background {monthly.background.sum():.2f} of {monthly.harmonized_estimate.sum():.2f}")
        check("hero badge names model A", page.inner_text("#data-badge") == "MODEL A · BAKE-OFF WINNER", page.inner_text("#data-badge"))
        j1 = hot[(hot.sensor == "J1") & (hot.acq_date >= "2022-01-01")]
        check("NOAA-20 detections carry weight in the estimated era", (j1.w > 0).mean() > 0.99, f"{(j1.w > 0).sum()} of {len(j1)} with w > 0")
        check("estimated months are flagged S-NPP+NOAA-20", monthly[monthly.month >= "2022-01"].source_flag.str.startswith("estimated (S-NPP+NOAA-20)").all())
        versions = sorted(hot.version.unique())
        check("CSV version strings exactly as in the FIRMS files", versions == ["2", "6.03", "6.2", "61.03"], str(versions))

        # ---- exact areas: two circles, the calendar against the hotspot CSV
        for lat, lon, km, month in ((37.3, -8.6, 12, "2023-08"), (40.13, -8.36, 9, None)):
            label = f"{km} km circle at {lat},{lon}"
            circle(page, lat, lon, km)
            info(f"{label}: {page.inner_text('#area-summary').replace(chr(10), ' ')[:220]}")
            m_csv, h_csv = compare_csvs(page, label, dl)
            month_matches(m_csv, h_csv, month or m_csv.loc[m_csv.harmonized_estimate.idxmax(), "month"], label)
            if month:
                page.click("#cal-grid [data-year='2023'][data-moy='8']")
                shown = page.inner_text("#month-value")
                want_v = float(h_csv.loc[h_csv.acq_date.str[:7] == month, "w"].sum()) + float(m_csv.loc[m_csv.month == month, "background"].sum())
                check(f"{label}: Aug 2023 panel shows the hotspot sum + background", shown in (f"{want_v:.1f}", f"{round(want_v):,}"), f"panel {shown} vs {want_v:.3f}")
                page.locator(".history").screenshot(path=str(shots / "desktop_circle_12km.png"))

        # ---- mouse-drawn rectangle: exact too
        page.wait_for_selector("#map-panel[data-draw=ready]", state="attached", timeout=300000)  # CDN-bound wait
        page.click("#draw-clear")
        page.wait_for_timeout(900)
        page.click("#draw-rectangle")
        pts = page.evaluate(r"""() => { const m = window.cedrus.state.map; const r = m.getCanvas().getBoundingClientRect();
          return [[-8.9, 38.3], [-7.9, 39.1]].map(([x, y]) => { const p = m.project([x, y]); return [r.left + p.x, r.top + p.y]; }); }""")
        page.mouse.move(*pts[0]); page.mouse.click(*pts[0])
        page.mouse.move(*pts[1], steps=8); page.mouse.click(*pts[1])
        page.wait_for_function("document.querySelector('#area-summary').textContent.includes('drawn rectangle')"
                               " && !document.querySelector('#area-summary').textContent.includes('Reading')", timeout=60000)
        check("mouse-drawn rectangle becomes the area", True, page.inner_text("#area-summary").replace("\n", " ")[:200])
        page.wait_for_timeout(900)
        page.screenshot(path=str(shots / "desktop_drawn_rectangle.png"), full_page=True)
        compare_csvs(page, "mouse-drawn rectangle", dl)

        # ---- region switch mid-draw cancels the drawing
        page.click("#draw-rectangle")
        page.mouse.click(*pts[0])
        page.select_option("#region", "lebanon")
        page.wait_for_function("document.querySelector('#area-summary').textContent.includes('Lebanon (whole region)')", timeout=20000)
        st = page.evaluate("""() => ({ drawing: window.cedrus.state.drawing, shapes: window.cedrus.state.draw.getSnapshot().length,
          pressed: [...document.querySelectorAll('.tool[aria-pressed]')].map((b) => b.getAttribute('aria-pressed')) })""")
        check("region switch mid-draw: mode cancelled, partial shape cleared, buttons released",
              st["drawing"] is None and st["shapes"] == 0 and st["pressed"] == ["false", "false"], str(st))

        # ---- Lebanon: overlays, few fires, S-NPP-only final month
        page.wait_for_timeout(500)
        n_care = page.locator("#cal-grid .cal-cell.care").count(); n_hz = page.locator("#cal-grid .cal-cell.hz").count()
        lab = page.get_attribute("#cal-grid .cal-cell.hz", "aria-label") if n_hz else ""
        check("Lebanon: trust overlays drawn and spoken (dashed = care, hatched = too uncertain)",
              (n_care + n_hz) > 0 and "too uncertain" in lab, f"care {n_care}, hatched {n_hz}; {lab}")
        quiet = page.evaluate(r"""() => [...document.querySelectorAll('#cal-grid .cal-cell.zero')].map((c) => [c.dataset.year, c.getAttribute('aria-label')])""")
        q22 = [l for y, l in quiet if int(y) >= 2022]
        check("quiet months under 0.5 use the ≈ zero tile after 2022 too, exact value in the tooltip",
              any("≈ zero" in l for l in q22) and any(int(y) < 2022 for y, _ in quiet), f"{len(q22)} after 2022, e.g. {q22[:1]}")
        n_few = page.locator("#cal-grid .cal-cell.few").count()
        check("few-fires months carry a calendar mark and a legend entry", n_few > 0 and "few fires" in page.inner_text("#calendar-legend"),
              f"{n_few} cells")
        page.click("#cal-grid [data-year='2025'][data-moy='1']")
        check("Lebanon Jan 2025 (baseline median < 5): 'Few fires — too few to judge'", "Few fires — too few to judge" in page.inner_text("#month-panel"),
              page.inner_text("#trust").split("\n")[0] if page.locator("#trust").count() else "no trust box")
        dec = page.get_attribute("#cal-grid [data-year='2025'][data-moy='12']", "aria-label")
        check("Lebanon Dec 2025 is S-NPP only (NOAA-20 file's last detection 24 Dec)", "S-NPP only" in dec, dec)
        want_lb, _ = expected_default_month("lebanon")
        page.click("#example-lebanon")
        page.select_option("#region", "portugal")
        page.wait_for_function("document.querySelector('#area-summary').textContent.includes('Portugal (whole region)')", timeout=20000)
        page.click("#example-lebanon")
        page.wait_for_function("document.querySelector('#area-summary').textContent.includes('Lebanon (whole region)')", timeout=20000)
        check("Lebanon default month", want_lb in page.inner_text("#month-title"), f"{page.inner_text('#month-title')} (expected {want_lb})")
        wait_season(page)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(shots / "desktop_lebanon.png"), full_page=True)
        compare_csvs(page, "Lebanon whole region", dl, rounding_bound("lebanon"))

        # ---- region race: from Lebanon, ask for Portugal and at once for Lebanon again; Lebanon must stay
        outcome = page.evaluate("() => Promise.all([window.cedrus.useRegion('portugal'), window.cedrus.useRegion('lebanon')])")
        page.wait_for_timeout(1000)
        race = page.evaluate("() => ({ id: window.cedrus.state.meta.id, area: document.querySelector('#area-summary').textContent, region: document.querySelector('#region').value })")
        check("region race: the older Portugal request is discarded, Lebanon renders",
              outcome == [False, True] and race["id"] == "lebanon" and "Lebanon" in race["area"] and race["region"] == "lebanon",
              f"returns {outcome}; {str(race)[:140]}")

        # ---- outside coverage: a circle across the Spanish border; Madrid refused
        page.select_option("#region", "portugal")
        page.wait_for_function("document.querySelector('#area-summary').textContent.includes('Portugal (whole region)')", timeout=20000)
        circle(page, 39.0, -7.0, 40)
        warn = page.inner_text("#outside-warning") if page.locator("#outside-warning").count() else ""
        check("border circle: share outside Portugal's data is stated", "outside Portugal’s data (FIRMS country file)" in warn and "not counted" in warn, warn)
        check("border circle: the area's label says it", "outside Portugal’s data" in page.inner_text("#area-summary strong"), page.inner_text("#area-summary strong"))
        page.screenshot(path=str(shots / "desktop_border_circle.png"), full_page=True)
        page.fill("#lat", "40.42"); page.fill("#lon", "-3.70"); page.fill("#radius", "20"); page.click("#circle-go")
        page.wait_for_timeout(800)
        check("Madrid circle refused, not relabelled as Portugal", "Outside the regions we cover" in page.inner_text(".toast")
              and "40.420" not in page.inner_text("#area-summary"), page.inner_text(".toast"))

        # ---- skip link, About text, v1 files
        page.goto(url, wait_until="commit")  # the calendar does not wait for CDN scripts; neither does the probe
        page.wait_for_function("window.cedrus", timeout=60000); page.evaluate("window.cedrus.ready")
        page.keyboard.press("Tab")
        first = page.evaluate("document.activeElement.className")
        page.keyboard.press("Enter")
        check("skip link is the first stop and moves focus to the calendar", first == "skip-link"
              and page.evaluate("document.activeElement.id") == "calendar-panel", f"{first} -> {page.evaluate('document.activeElement.id')}")
        page.click("button[data-dialog=about]")
        check("About: Suomi NPP stops delivering data on 2 Nov 2026", "stops delivering data on 2 Nov 2026" in page.inner_text("#detail-dialog"))
        page.click(".dialog-done")
        page.click("button[data-dialog=methodology]")
        dlg = page.inner_text("#detail-dialog")
        check("methodology: model A in plain words, the bake-off link, B lost, NOAA-20, SHA-256, credits",
              all(k in dlg for k in ("A — shrinkage ratio (bake-off winner)", "BAKEOFF_RESULTS.md", "lost", "NOAA-20", "SHA-256", "Kiln Watch", "Agun-Panjika", "Use of AI"))
              and page.locator("#detail-dialog a[href$='BAKEOFF_RESULTS.md']").count() == 1)
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        check("README: Suomi NPP stops delivering data on 2 Nov 2026", "stops delivering data on **2 Nov 2026**" in readme
              and "1 November 2026" not in readme)
        page.screenshot(path=str(shots / "desktop_methodology.png"))
        page.click(".dialog-done")
        check("unused v1 files removed", not (ROOT / "web/data/portugal.json").exists() and not (ROOT / "web/data/portugal-cells.geojson").exists())
        page.wait_for_timeout(2500)
        page.screenshot(path=str(shots / "desktop.png"), full_page=True)
        ctx.close()

        # ---- mobile
        ctx = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        page = ctx.new_page()
        watch(page, "mobile ")
        page.goto(url, wait_until="commit")  # the calendar does not wait for CDN scripts; neither does the probe
        page.wait_for_function("window.cedrus", timeout=60000); page.evaluate("window.cedrus.ready")
        page.wait_for_timeout(2500)
        overflow = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        check("mobile 390 px: no horizontal overflow", overflow <= 0, f"scrollWidth - innerWidth = {overflow}")
        box = page.evaluate("(() => { const r = document.querySelector('#cal-grid [role=gridcell]').getBoundingClientRect(); return [r.width, r.height]; })()")
        check("mobile: calendar cells at least 24 px tall", box[1] >= 24, f"{box[0]:.1f} x {box[1]:.1f} px")
        page.screenshot(path=str(shots / "mobile_early.png"), full_page=True)  # whatever the CDN has delivered by now
        t_map = time.time()
        try:  # not a check: how long the CDN takes is not the site's doing; the screenshot just waits for it
            page.wait_for_selector("#map-panel[data-draw=ready]", state="attached", timeout=150000)
            info(f"mobile: map and drawing tools ready {time.time() - t_map + 2.5:.1f} s after the calendar (CDN-bound)")
        except Exception:
            info(f"mobile: map not ready {time.time() - t_map + 2.5:.0f} s after the calendar (CDN-bound); screenshot shows the loading state")
        page.wait_for_timeout(1500)
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
