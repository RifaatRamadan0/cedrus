"""Headless check of the website: loads, renders, toggles, draws, downloads, and compares the CSVs, in both units
(burning days, the default, against a Python sum over web/data/<region>/burning/; then hotspots, as before).

    python tools/probe_site.py              # serves web/ itself on the first free port from 8765
    python tools/probe_site.py --url http://localhost:8000/

Needs Python Playwright and Chrome (C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe by default).
Screenshots go to tools/shots/. Exit code 1 if any check fails.
"""
import argparse
import http.server
import io
import json
import re
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


class Server(socketserver.ThreadingTCPServer):
    # The page asks for up to 25 hotspot years at once; the default backlog of 5 refuses some of them
    # (ERR_CONNECTION_REFUSED), which is the test server's limit, not the site's.
    request_queue_size = 128
    daemon_threads = True

    def handle_error(self, request, client_address):
        pass  # a browser context closed mid-download aborts the connection; not a finding


def serve(port):
    handler = partial(Quiet, directory=str(ROOT / "web"))
    httpd = Server(("127.0.0.1", port), handler)
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
      preload: v?.getAttribute('preload'), autoplay: v?.hasAttribute('autoplay'),
      fetched: performance.getEntriesByType('resource').map((e) => e.name).filter((n) => n.includes('/data/')).map((n) => n.split('/data/').pop()) };
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


def expected_default_month(region="portugal", name="monthly.json"):
    """Independent of app.js: the most recent month with >= 5 baseline years (2003..year-1) and a median >= 5,
    whole region."""
    m = json.loads((ROOT / "web" / "data" / region / name).read_text(encoding="utf-8"))
    total = np.array(m["m"]).sum(axis=0)
    y0, m0 = map(int, m["months"]["first"].split("-"))
    ym = [divmod(y0 * 12 + m0 - 1 + j, 12) for j in range(len(total))]
    for j in range(len(total) - 1, max(-1, len(total) - 1 - 36), -1):  # only the record's last 3 years
        y, mo = ym[j]
        base = [total[k] for k, (yy, mm) in enumerate(ym) if mm == mo and 2003 <= yy < y]
        if len(base) >= 5 and np.median(base) >= 5:
            prev = ym[j - 1]
            return f"{NAMES[mo]} {y}", f"{NAMES[prev[1]]} {prev[0]}"
    for j in range(len(total) - 1, -1, -1):
        if total[j] >= 1:
            y, mo = ym[j]
            prev = ym[j - 1]
            return f"{NAMES[mo]} {y}", f"{NAMES[prev[1]]} {prev[0]}"
    return None, None


def anomaly_shares(page, label):
    """Anomaly mode, vs median: the share of strongly-above cells (>= +100%) before and from 2022."""
    page.click("#mode-anomaly")
    page.click("#ref-median")
    cells = page.evaluate(r"""() => [...document.querySelectorAll('#cal-grid [role=gridcell]')].map((c) => [Number(c.dataset.year),
      c.dataset.anom == null ? null : Number(c.dataset.anom), c.classList.contains('few')])""")
    def share(rows):
        coloured = [a for _, a, _ in rows if a is not None]
        return (sum(a >= 1 for a in coloured) / len(coloured)) if coloured else 0.0, len(coloured)
    pre, n_pre = share([c for c in cells if 2008 <= c[0] < 2022])
    post, n_post = share([c for c in cells if c[0] >= 2022])
    few = sum(f for _, _, f in cells)
    check(f"{label}: no false 2022 jump in anomaly mode (strong-above share from 2022 <= 2x before)", post <= 2 * pre + 1e-9,
          f"strong-above share 2008-21 {pre:.2f} of {n_pre} coloured, 2022+ {post:.2f} of {n_post}; {few} few-fires neutral cells")
    page.click("#mode-counts")


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
    check(f"{label}: methods line wording", "replaced by the bake-off winner" not in header and "identical to the exact sum" not in header
          and ("whole" in label.lower() and "equal to the exact sum within rounding; ≤0.1/month" in header or "region" not in label.lower()),
          header[header.find("Area"):header.find("Area") + 140])
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
    """The frozen round-2 model in the data: its settings file, fit windows, refusal of 2020+, frozen-by-construction
    fit, combination rule and NOAA-20 weights."""
    import hashlib
    idx = json.loads((ROOT / "web" / "data" / "regions.json").read_text(encoding="utf-8"))
    names = {r["id"]: r["model"] for r in idx["regions"]}
    check("regions.json: model is the frozen round-2 choice in every region", set(names.values()) == {"A2 + NOAA-20 via Suomi NPP (round-2 choice, frozen)"}, str(names))
    frozen = ROOT / "data" / "processed" / "round2" / "frozen.json"
    digest = hashlib.sha256(frozen.read_bytes()).hexdigest()
    recorded = {r["model_detail"]["frozen"]["sha256"] for r in idx["regions"]}
    check("frozen.json SHA-256 is the one recorded at the freeze, and regions.json names it", digest == "bedc56d5ba85b851931cd6912dfcab832dc38b26a8fe80712a72974cf46e0686" and recorded == {digest},
          f"file {digest[:16]}…, regions.json {[x[:16] for x in recorded]}")
    wins = {r["id"]: {k: v["train"] for k, v in r["model_detail"]["satellites"].items()} for r in idx["regions"]}
    ok = all(w == {"snpp": ["2012-02", "2019-12"], "noaa20": ["2018-04", "2019-12"]} for w in wins.values())
    check("fit windows as frozen: Suomi NPP 2012-02..2019-12, NOAA-20 s on 2018-04..2019-12", ok, str(wins))
    sys.path.insert(0, str(ROOT / "pipeline"))
    import weights_r2
    try:
        weights_r2.check_frozen(frozen.read_bytes().replace(b'"a": 30', b'"a": 31'))
        tamper = False
    except SystemExit:
        tamper = True
    check("weights_r2 refuses a frozen.json that is not the frozen file", tamper)
    saved = dict(weights_r2.WINDOWS)
    det = pd.DataFrame({"month": ["2019-12", "2020-01"], "moy": [12, 1], "dn": ["D", "D"], "fam": ["snpp", "modis"], "ci": [0, 0]})
    try:
        weights_r2.WINDOWS["snpp"] = ("2012-02", "2020-03")
        try:
            weights_r2.fit(det, "probe")
            refused = False
        except (AssertionError, ValueError):
            refused = True
    finally:
        weights_r2.WINDOWS.clear(); weights_r2.WINDOWS.update(saved)
    check("the round-2 fit refuses a window reaching into 2020", refused)

    # Frozen by construction: a detection in 2023 in a cell that never burned before changes no fitted parameter,
    # and that cell gets A2's region-level ratio (r0 of its slot).
    import export_v2
    det = export_v2.detections("lebanon")
    cells = det.groupby(["iy", "ix"]).size().reset_index()
    det["ci"] = [dict(zip(zip(cells.ix, cells.iy), range(len(cells))))[k] for k in zip(det.ix, det.iy)]
    m1 = weights_r2.fit(det, "lebanon")
    new = det.iloc[[0]].copy()
    new["month"], new["moy"], new["dn"], new["fam"], new["sensor"], new["ci"] = "2023-07", 7, "D", "snpp", "N", len(cells)
    m2 = weights_r2.fit(pd.concat([det, new], ignore_index=True), "lebanon")
    same = all(np.array_equal(m1["a2"][k], m2["a2"][k]) for k in ("r0", "bA", "SY", "SV", "r0_level")) \
        and np.array_equal(m1["s"], m2["s"]) and np.array_equal(m1["var_s"], m2["var_s"])
    md = (7 - 1) * 2
    region_level = abs(m2["ratio"][len(cells) * 24 + md] - m2["a2"]["r0"][md]) < 1e-12
    check("frozen by construction: a synthetic 2023 detection in a brand-new cell leaves r0, b, cell sums and s bit-identical",
          same, f"cells {len(cells)} -> {len(cells) + 1}")
    check("a cell that first burns after the fit window gets A2's region-level ratio for its slot", region_level,
          f"{m2['ratio'][len(cells) * 24 + md]:.6f} vs r0 {m2['a2']['r0'][md]:.6f}")

    # Combination rule: a satellite enters a slot's average only where its ratio is above 0.
    bad = [(r["id"], slot, f) for r in idx["regions"] for slot, sats in r["combination"]["slots_when_both_cover"].items()
           for f in sats if not r["model_detail"]["satellites"][f]["prior_ratio_r0"][slot] > 0]
    check("combination rule: no slot's average includes a satellite with ratio 0", not bad, str(bad[:5]))

    # NOAA-20 weights in months both satellites cover: 1/2 x A2's ratio x s, for a sample of Portugal 2023 detections.
    mon = json.loads((ROOT / "web/data/portugal/monthly.json").read_text(encoding="utf-8"))
    cmap = {(x, y): k for k, (x, y) in enumerate(zip(mon["cells"]["ix"], mon["cells"]["iy"]))}
    det = export_v2.detections("portugal")
    det["ci"] = [cmap.get(k, -1) for k in zip(det.ix, det.iy)]
    m = weights_r2.fit(det[det.ci >= 0], "portugal")
    h = json.loads((ROOT / "web/data/portugal/hotspots/2023.json").read_text(encoding="utf-8"))["cols"]
    rows = [i for i in range(len(h["lat"])) if h["sensor"][i] == 3][::20][:300]
    gaps = []
    for i in rows:
        moy = (pd.Timestamp(2023, 1, 1) + pd.Timedelta(days=h["doy"][i] - 1)).month
        ci = cmap[(int(np.floor(h["lon"][i] / 0.25)), int(np.floor(h["lat"][i] / 0.25)))]
        want = 0.5 * m["ratio"][ci * 24 + (moy - 1) * 2 + h["dn"][i]] * m["s"][h["dn"][i]]
        gaps.append(abs(h["w"][i] - want))
    check("NOAA-20 weights in both-covered months = 1/2 x A2 ratio x s (Portugal 2023 sample)", gaps and max(gaps) <= 6e-5,
          f"{len(gaps)} detections, max |w - expected| {max(gaps, default=0):.6f}; s = {np.round(m['s'], 4).tolist()}")
    # Lebanon January nights: A2's ratio is 0, so no satellite joins and detections weigh 0 (background only).
    wj = []
    for y in (2022, 2023, 2024, 2025):
        hh = json.loads((ROOT / "web/data/lebanon/hotspots" / f"{y}.json").read_text(encoding="utf-8"))["cols"]
        wj += [hh["w"][i] for i in range(len(hh["lat"])) if hh["doy"][i] <= 31 and hh["dn"][i] == 1 and hh["sensor"][i] in (2, 3)]
    check("Lebanon January nights (ratio 0): VIIRS detections weigh 0", all(w == 0 for w in wj), f"{len(wj)} detections")


# ---------------------------------------------------------------- burning days (the default view)
BD_SHA = "f3130df9ed80894e0176866cd3c8e51a3c4a7233c3cb40dd1c7b93651d4357a2"
BD_MODEL = "D-a + NOAA-20 via Suomi NPP (burning days, round-3 confirmed)"
FAMILY = ["MODIS", "Suomi NPP", "NOAA-20"]


def in_ring(lon, lat, ring):
    """app.js inRing, operation for operation (ray casting on lon/lat)."""
    inside = False
    k = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xk, yk = ring[k]
        if (yi > lat) != (yk > lat) and lon < ((xk - xi) * (lat - yi)) / (yk - yi) + xi:
            inside = not inside
        k = i
    return inside


def burning_files(region):
    return [json.loads(f.read_text(encoding="utf-8")) for f in sorted((ROOT / "web" / "data" / region / "burning").glob("*.json"))]


def bd_inside(region, ring):
    """Independent of app.js: every burning day whose 0.01 deg square's centre is inside the ring (the contract's rule;
    ring None = whole region), read straight from burning/<year>.json."""
    out = []
    if ring is not None:
        xs, ys = [p[0] for p in ring], [p[1] for p in ring]
        bx0, bx1, by0, by1 = min(xs), max(xs), min(ys), max(ys)
    for d in burning_files(region):
        c = d["cols"]
        for i in range(d["n"]):
            fx, fy = d["x0"] + c["x"][i], d["y0"] + c["y"][i]
            lon, lat = (fx + 0.5) * 0.01, (fy + 0.5) * 0.01
            if ring is not None and (lon < bx0 or lon > bx1 or lat < by0 or lat > by1 or not in_ring(lon, lat, ring)):
                continue
            day = pd.Timestamp(d["year"], 1, 1) + pd.Timedelta(days=c["doy"][i] - 1)
            out.append((fx, fy, day.strftime("%Y-%m-%d"), "N" if c["dn"][i] else "D", FAMILY[c["fam"][i]], c["w"][i]))
    return pd.DataFrame(out, columns=["cell_x", "cell_y", "acq_date", "daynight", "family", "w"])


def bd_rounding_bound(region):
    m = np.array(json.loads((ROOT / "web" / "data" / region / "monthly_bd.json").read_text(encoding="utf-8"))["m"])
    n_frac = int((np.abs(m - np.round(m)) > 1e-9).sum())
    return 0.005 * n_frac + 0.00005 * sum(d["n"] for d in burning_files(region))


def compare_bd(page, label, dest, region, tol=None):
    """Burning days: the monthly CSV against the burning-day CSV, and both against a Python sum over the files of the
    burning days whose square's centre is inside the area's ring (read from the page)."""
    mpath = download(page, "#csv-monthly", dest)
    bpath = download(page, "#csv-burning", dest)
    header, monthly = read_monthly(mpath)
    rows = pd.read_csv(bpath, dtype={"acq_date": str})
    check(f"{label}: monthly CSV is in burning days (methods line and file name)",
          header.startswith("# CEDRUS monthly burning days") and mpath.name.endswith("_monthly_burning_days.csv")
          and list(monthly.columns) == ["month", "harmonized_estimate", "p10", "p90", "naive", "background", "source_flag"],
          f"{mpath.name}; {header[:90]}")
    check(f"{label}: burning-day CSV parses", list(rows.columns) == ["latitude", "longitude", "cell_x", "cell_y", "acq_date", "daynight",
          "family", "detections", "max_frp", "frp_class", "source_flag", "w"], f"{len(rows)} rows")
    ring = page.evaluate("() => { const a = window.cedrus.state.area; return a.kind === 'region' ? null : a.ring; }")
    py = bd_inside(region, ring)
    key = ["cell_x", "cell_y", "acq_date", "daynight", "family"]
    same = len(py) == len(rows) and set(map(tuple, py[key].astype(str).to_numpy())) == set(map(tuple, rows[key].astype(str).to_numpy()))
    check(f"{label}: the burning-day CSV is exactly the burning days whose square's centre is inside (Python, from the files)",
          same and abs(py.w.sum() - rows.w.sum()) < 1e-6, f"CSV {len(rows)} rows, Python {len(py)}; sum w {rows.w.sum():.4f} vs {py.w.sum():.4f}")
    if ring is not None:
        want_bg = expected_background(region, ring)
        check(f"{label}: background = each cell's bg x the exact share of its area inside the shape (Python clip)", abs(float(monthly.background.sum()) - want_bg) <= 0.02,
              f"CSV {float(monthly.background.sum()):.4f} vs Python {want_bg:.4f}")
    shown = page.evaluate("() => window.cedrus.state.series.exact ? window.cedrus.state.series.count : null")
    if shown is not None:
        check(f"{label}: the page counts the same burning days", shown == len(py), f"page {shown}, Python {len(py)}")
    a, bg = float(monthly.harmonized_estimate.sum()), float(monthly.background.sum())
    tol_ = 0.01 if tol is None else tol
    check(f"{label}: burning-day calendar sum == sum(w) inside + background", abs(a - (py.w.sum() + bg)) <= tol_,
          f"calendar {a:.4f} vs burning days {py.w.sum():.4f} + background {bg:.4f}, |diff| {abs(a - py.w.sum() - bg):.4f}, tolerance {tol_:.4f}"
          f" ({'rounding bound of 2-dp cell values' if tol is not None else 'exact area: both sides add the same 4-dp weights'})")
    if len(py):
        py["month"] = py.acq_date.str[:7]
        top = monthly.loc[monthly.harmonized_estimate.idxmax(), "month"]
        row = monthly[monthly.month == top]
        want = float(py.loc[py.month == top, "w"].sum()) + float(row.background.sum())
        # an exact area adds the same 4-dp weights; the whole region adds its cells' 2-dp values (0.005 each at most)
        n_cells = len(json.loads((ROOT / "web" / "data" / region / "monthly_bd.json").read_text(encoding="utf-8"))["m"])
        tol_m = 0.01 if tol is None else 0.005 * n_cells + 0.00005 * int((py.month == top).sum())
        check(f"{label}: {top} (its largest month) calendar == its burning days' w + background", abs(float(row.harmonized_estimate.sum()) - want) <= tol_m,
              f"{float(row.harmonized_estimate.sum()):.4f} vs {want:.4f}, tolerance {tol_m:.4f}")
    known = ("bridged", "observed", "estimated (S-NPP+NOAA-20)", "estimated (S-NPP only)", "estimated (NOAA-20 only)")
    flags = set(monthly.source_flag) | set(rows.source_flag.dropna())
    check(f"{label}: source flags are the documented ones", all(any(f == k or f.startswith(k + " (") for k in known) for f in flags), str(sorted(flags))[:160])
    return monthly, rows


def busiest_square(region):
    """The centre of the 0.01 deg square with the most burning days in the region: a small circle there cannot be empty."""
    n = {}
    for d in burning_files(region):
        c = d["cols"]
        for i in range(d["n"]):
            k = (d["x0"] + c["x"][i], d["y0"] + c["y"][i])
            n[k] = n.get(k, 0) + 1
    (fx, fy), _ = max(n.items(), key=lambda kv: (kv[1], kv[0]))
    return round((fy + 0.5) * 0.01, 3), round((fx + 0.5) * 0.01, 3)


def fmt_js(v):
    """app.js fmt()."""
    if v > 0 and v < 0.05:
        return "<0.1"
    if abs(v) < 10 and abs(v - round(v)) > 0.005:
        return f"{v:.1f}"
    return f"{round(v):,}"


def cell_share(ring, x0, y0, deg):
    """app.js cellShare(), operation for operation: the shape clipped to the cell, shoelace area over the cell's."""
    pts = [(x - x0, y - y0) for x, y in ring]
    cut_x = lambda a, b, x: (x, a[1] + ((b[1] - a[1]) * (x - a[0])) / (b[0] - a[0]))
    cut_y = lambda a, b, y: (a[0] + ((b[0] - a[0]) * (y - a[1])) / (b[1] - a[1]), y)
    sides = [(lambda p: p[0] >= 0, lambda a, b: cut_x(a, b, 0)), (lambda p: p[0] <= deg, lambda a, b: cut_x(a, b, deg)),
             (lambda p: p[1] >= 0, lambda a, b: cut_y(a, b, 0)), (lambda p: p[1] <= deg, lambda a, b: cut_y(a, b, deg))]
    for inside, cut in sides:
        nxt = []
        for i in range(len(pts)):
            a, b = pts[i], pts[(i + 1) % len(pts)]
            ia = inside(a)
            if ia:
                nxt.append(a)
            if ia != inside(b):
                nxt.append(cut(a, b))
        pts = nxt
        if not pts:
            return 0.0
    s = 0.0
    for i in range(len(pts)):
        (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % len(pts)]
        s += xa * yb - xb * ya
    return min(1.0, abs(s) / 2 / (deg * deg))


def expected_background(region, ring, name="monthly_bd.json"):
    """Independent of app.js: sum over cells of bg x the exact share of the cell's area inside the ring."""
    mon = json.loads((ROOT / "web" / "data" / region / name).read_text(encoding="utf-8"))
    deg = mon["cell_deg"]
    return sum(sum(mon["bg"][c]) * f for c, f in ((c, cell_share(ring, x * deg, y * deg, deg))
                                                     for c, (x, y) in enumerate(zip(mon["cells"]["ix"], mon["cells"]["iy"]))) if f > 0)


def zero_notes_from_files(region):
    """Independent of the export: per month, VIIRS burning days of the satellites the month uses (E both, N Suomi NPP,
    J NOAA-20) and how many weigh 0; months where that is >= 10%."""
    mon = json.loads((ROOT / "web" / "data" / region / "monthly_bd.json").read_text(encoding="utf-8"))
    y0, m0 = map(int, mon["months"]["first"].split("-"))
    use = {"E": (1, 2), "N": (1,), "J": (2,)}
    cnt = {}
    for d in burning_files(region):
        c = d["cols"]
        for i in range(d["n"]):
            moy = (pd.Timestamp(d["year"], 1, 1) + pd.Timedelta(days=c["doy"][i] - 1)).month
            j = (d["year"] * 12 + moy - 1) - (y0 * 12 + m0 - 1)
            if c["fam"][i] in use.get(mon["flags"][j], ()):
                k = f"{d['year']}-{moy:02d}"
                m, z = cnt.get(k, (0, 0))
                cnt[k] = (m + 1, z + (c["w"][i] == 0))
    return {k: (z, m) for k, (m, z) in cnt.items() if m and z / m >= 0.10}, cnt


def rounding_checks():
    """Whole region: the sum of its cells equals the exact sum of the records' weights + background within 0.1 per month."""
    for region in ("portugal", "lebanon"):
        for name, folder in (("monthly.json", "hotspots"), ("monthly_bd.json", "burning")):
            mon = json.loads((ROOT / "web" / "data" / region / name).read_text(encoding="utf-8"))
            y0, m0 = map(int, mon["months"]["first"].split("-"))
            w = np.zeros(mon["months"]["n"])
            for f in sorted((ROOT / "web" / "data" / region / folder).glob("*.json")):
                d = json.loads(f.read_text(encoding="utf-8"))
                mo = np.asarray((pd.Timestamp(d["year"], 1, 1) + pd.to_timedelta(np.array(d["cols"]["doy"]) - 1, unit="D")).month)
                np.add.at(w, (d["year"] * 12 + mo - 1) - (y0 * 12 + m0 - 1), np.array(d["cols"]["w"], float))
            gap = np.abs(np.array(mon["m"]).sum(axis=0) - w - np.array(mon["bg"]).sum(axis=0))
            check(f"{region} {folder}: whole-region month = exact sum within 0.1 (as the site says)", gap.max() <= 0.1,
                  f"largest gap {gap.max():.4f} over {len(gap)} months")


def bd_model_checks():
    """The burning-day model in the data: frozen file, fit windows, nothing from 2020 on, frozen by construction, the
    same refit as the round-3 exam, NOAA-20 via s, and every file adding up."""
    import hashlib
    idx = json.loads((ROOT / "web" / "data" / "regions.json").read_text(encoding="utf-8"))
    check("regions.json: the default unit is burning days", idx.get("default_unit") == "burning_days", str(idx.get("default_unit")))
    names = {r["id"]: r["burning_days"]["model"] for r in idx["regions"]}
    check("regions.json: the burning-day model is D-a, round-3 confirmed, in every region", set(names.values()) == {BD_MODEL}, str(names))
    frozen = ROOT / "data" / "processed" / "tournament" / "frozen_round3.json"
    digest = hashlib.sha256(frozen.read_bytes()).hexdigest()
    recorded = {r["burning_days"]["model_detail"]["frozen"]["sha256"] for r in idx["regions"]}
    check("frozen_round3.json SHA-256 is the one recorded at the freeze, and regions.json names it", digest == BD_SHA and recorded == {digest},
          f"file {digest[:16]}…, regions.json {[x[:16] for x in recorded]}")
    check("burning-day model uses the frozen a = 10", {r["burning_days"]["model_detail"]["a"] for r in idx["regions"]} == {10})
    wins = {r["id"]: {k: v["train"] for k, v in r["burning_days"]["model_detail"]["satellites"].items()} for r in idx["regions"]}
    check("burning days: fit windows Suomi NPP 2012-02..2019-12, NOAA-20 s on 2018-04..2019-12",
          all(w == {"snpp": ["2012-02", "2019-12"], "noaa20": ["2018-04", "2019-12"]} for w in wins.values()), str(wins))
    sys.path.insert(0, str(ROOT / "pipeline"))
    import weights_bd
    from pipeline.round3 import data as r3d
    from pipeline.round3.model import fit_frozen
    tampered = SHOTS / "frozen_round3_tampered.json"
    SHOTS.mkdir(parents=True, exist_ok=True)
    tampered.write_bytes(frozen.read_bytes().replace(b'"frozen_setting": 10', b'"frozen_setting": 30'))
    try:
        r3d.load_frozen(tampered)
        refused = False
    except SystemExit:
        refused = True
    tampered.unlink()
    check("the burning-day model refuses a frozen_round3.json that is not the frozen file", refused and weights_bd.FROZEN_SHA256 == BD_SHA)

    import export_v2
    for region in ("lebanon", "portugal"):
        det = export_v2.detections(region)
        mon = json.loads((ROOT / "web" / "data" / region / "monthly_bd.json").read_text(encoding="utf-8"))
        cmap = {(x, y): k for k, (x, y) in enumerate(zip(mon["cells"]["ix"], mon["cells"]["iy"]))}
        det["ci"] = [cmap[k] for k in zip(det.ix, det.iy)]
        m1 = weights_bd.fit(det, region)
        keys = ("r0", "bA", "SY", "SV", "r0_level")
        if region == "lebanon":
            saved = dict(weights_bd.WINDOWS)
            try:
                weights_bd.WINDOWS["snpp"] = ("2012-02", "2020-03")
                try:
                    weights_bd.fit(det, region)
                    late = False
                except (AssertionError, ValueError):
                    late = True
            finally:
                weights_bd.WINDOWS.clear(); weights_bd.WINDOWS.update(saved)
            check("the burning-day fit refuses a window reaching into 2020", late)
            m0 = weights_bd.fit(det[det.month <= "2019-12"], region)
            check("no 2020+ in the burning-day fit: dropping every 2020-2025 detection leaves r0, b, cell sums and s bit-identical",
                  all(np.array_equal(m0["fit"][k], m1["fit"][k]) for k in keys) and np.array_equal(m0["s"], m1["s"])
                  and np.array_equal(m0["var_s"], m1["var_s"]), f"{int((det.month > '2019-12').sum())} detections after 2019 dropped")
            new = det.iloc[[0]].copy()
            new["month"], new["moy"], new["dn"], new["fam"], new["sensor"], new["acq_date"] = "2023-07", 7, "D", "snpp", "N", "2023-07-01"
            ix, iy = next((x, y) for y in range(132, 139) for x in range(140, 147) if (x, y) not in cmap)  # a cell inside the box that never burned
            new["longitude"], new["latitude"], new["ix"], new["iy"], new["ci"] = (ix + 0.5) * 0.25, (iy + 0.5) * 0.25, ix, iy, len(cmap)
            m2 = weights_bd.fit(pd.concat([det, new], ignore_index=True), region)
            md = (7 - 1) * 2
            r0 = m2["fit"]["r0"][md]
            check("burning days frozen by construction: a 2023 burning day in a brand-new cell changes nothing fitted, and that cell gets r0_k of its slot",
                  all(np.array_equal(m1["fit"][k], m2["fit"][k]) for k in keys) and np.array_equal(m1["s"], m2["s"])
                  and np.allclose(m2["ratio"][len(cmap) * 24 + md], np.where(r0 > 0, r0, 0.0), rtol=1e-12, atol=0),
                  f"cells {len(cmap)} -> {len(cmap) + 1}; new cell ratios {np.round(m2['ratio'][len(cmap) * 24 + md], 4).tolist()} vs r0 {np.round(r0, 4).tolist()}")
        # The same refit as the round-3 exam, through its own code on its own reading of the raw files.
        px = r3d.pixels(region)
        R, _ = r3d.rows(region, px)
        T = r3d.burning_days(R)
        mr = fit_frozen(r3d.load_frozen()[0], T, (T.ym <= "2019-12").to_numpy(), ("probe", region))
        check(f"{region}: the product's D-a fit is bit-identical to round 3's own refit of this region (r0, b, cell sums)",
              all(np.array_equal(mr["fit"][k], m1["fit"][k]) for k in keys), f"{len(T)} rows in round 3's table, {m1['fit_cells']} fit cells")
        # Every file adds up: per cell-month, the burning days' w + background = m (whole region, from the files).
        files = burning_files(region)
        n_m = mon["months"]["n"]
        y0, mo0 = map(int, mon["months"]["first"].split("-"))
        w = np.zeros((len(cmap), n_m))
        sample = []
        for d in files:
            c = d["cols"]
            for i in range(d["n"]):
                fx, fy = d["x0"] + c["x"][i], d["y0"] + c["y"][i]
                ci = cmap[(fx // 25, fy // 25)]
                moy = (pd.Timestamp(d["year"], 1, 1) + pd.Timedelta(days=c["doy"][i] - 1)).month
                j = (d["year"] * 12 + moy - 1) - (y0 * 12 + mo0 - 1)
                w[ci, j] += c["w"][i]
                if d["year"] == 2023 and c["fam"][i] in (1, 2) and mon["flags"][j] == "E":
                    sample.append((ci, moy, c["dn"][i], c["fam"][i], c["k"][i], c["w"][i]))
        gap = np.abs(w + np.array(mon["bg"]) - np.array(mon["m"]))
        check(f"{region}: monthly_bd.json m = the burning days' w + bg in every cell-month", gap.max() <= 0.005 + 1e-9 + 0.00005 * max(d["n"] for d in files),
              f"max |sum w + bg - m| {gap.max():.5f} over {gap.size} cell-months")
        gaps = []
        for ci, moy, dn, fam, k, wv in sample[::7][:400]:
            r = m1["ratio"][ci * 24 + (moy - 1) * 2 + dn, k]
            want = 0.5 * r * (m1["s"][dn] if fam == 2 else 1.0)
            gaps.append(abs(wv - want))
        check(f"{region}: 2023 VIIRS burning days weigh 1/2 x D-a's class ratio (x s for NOAA-20)", gaps and max(gaps) <= 6e-5,
              f"{len(gaps)} burning days, max |w - expected| {max(gaps, default=0):.6f}; s = {np.round(m1['s'], 4).tolist()}")
        ts = {int(k): v for k, v in next(r for r in idx["regions"] if r["id"] == region)["burning_days"]["terra_share"]["by_month"].items()}
        br = [(abs(c["w"][i] - 1 / ts[(pd.Timestamp(d["year"], 1, 1) + pd.Timedelta(days=c["doy"][i] - 1)).month]))
              for d in files if d["year"] <= 2002 for c in [d["cols"]] for i in range(d["n"])
              if mon["flags"][(d["year"] * 12 + (pd.Timestamp(d["year"], 1, 1) + pd.Timedelta(days=c["doy"][i] - 1)).month - 1) - (y0 * 12 + mo0 - 1)] == "B"]
        check(f"{region}: bridged MODIS burning days weigh 1 / Terra's burning-day share", br and max(br) <= 1e-3, f"{len(br)} burning days")


def run(url, shots):
    model_checks()
    bd_model_checks()
    rounding_checks()
    for region in ("portugal", "lebanon"):
        want, cnt = zero_notes_from_files(region)
        got = json.loads((ROOT / "web" / "data" / region / "monthly_bd.json").read_text(encoding="utf-8"))["zero_notes"]
        parsed = {k: tuple(int(x) for x in v.split(" VIIRS")[0].split(" of ")) for k, v in got.items()}
        late = [v for k, v in cnt.items() if k >= "2022-01"]
        share = sum(z for _, z in late) / max(1, sum(m for m, _ in late))
        zw = next(r for r in json.loads((ROOT / "web/data/regions.json").read_text(encoding="utf-8"))["regions"] if r["id"] == region)["burning_days"]["zero_weight"]
        check(f"{region}: zero-weight notes are exactly the months where >= 10% of the used VIIRS burning days weigh 0 (Python, from the files)",
              parsed == want and abs(zw["share"] - share) < 1e-4, f"{len(got)} months noted; 2022+ share {share:.4f} (regions.json {zw['share']})")
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
        # What the calendar waited for: the data files requested before it first had cells (the season dates read the
        # burning-day records afterwards, which is not part of the cold load).
        fetched = page.evaluate("window.__atParse.fetched")
        sizes = {f: (ROOT / "web" / "data" / f).stat().st_size for f in sorted(set(fetched))}
        check("cold load: the calendar waits only for the burning-day calendar files (no hotspot or burning-day records)",
              set(fetched) == {"regions.json", "portugal/monthly_bd.json", "portugal/drift_bd.json"},
              f"{sizes}, {sum(sizes.values()) / 1e6:.2f} MB")
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

        # ---- burning days: the default view
        st = page.evaluate("""() => ({ unit: window.cedrus.state.unit, bd: document.querySelector('#unit-bd').getAttribute('aria-pressed'),
          hot: document.querySelector('#unit-hot').getAttribute('aria-pressed'), note: document.querySelector('#calendar-note').textContent,
          legend: document.querySelector('#calendar-legend').textContent, body: document.querySelector('#month-body').textContent,
          caption: document.querySelector('#map-caption').textContent, area: document.querySelector('#area-summary').textContent,
          csv: [!document.querySelector('#csv-burning').hidden, !document.querySelector('#csv-hotspots').hidden] })""")
        check("default unit is burning days: switch pressed, calendar, legend, panel, map caption, area and downloads say so",
              st["unit"] == "bd" and st["bd"] == "true" and st["hot"] == "false" and "in MODIS-equivalent burning days" in st["note"]
              and "Burning days per month" in st["legend"] and "burning days (MODIS-equivalent)" in st["body"] and "burning days per 0.25° cell" in st["caption"]
              and "every burning day in Portugal" in st["area"] and st["csv"] == [True, True], str(st)[:300])
        want_bd, _ = expected_default_month("portugal", "monthly_bd.json")
        check("burning days: default month = most recent with >= 5 baseline years and median >= 5 (monthly_bd.json)", want_bd in page.inner_text("#month-title"),
              f"{page.inner_text('#month-title')} (expected {want_bd})")
        cnt = [page.locator(f"#cal-grid {s}").count() for s in ("[role=gridcell]", ".cal-cell.nd", ".cal-cell.b", ".cal-cell.e")]
        check("burning days: the same record and policy (312 cells; no-data 11, bridged 19, estimated 48)", cnt == [312, 11, 19, 48], str(cnt))
        tot = page.evaluate("() => window.cedrus.state.series.m.reduce((a, b) => a + b, 0)")
        file_tot = float(np.array(json.loads((ROOT / "web/data/portugal/monthly_bd.json").read_text(encoding="utf-8"))["m"]).sum())
        check("burning days: the whole-region calendar is monthly_bd.json", abs(tot - file_tot) < 1e-6, f"{tot:.2f} vs {file_tot:.2f}")
        check("burning days: the drift chart is drift_bd.json, in burning days", page.evaluate("window.cedrus.state.drift.unit") == "burning days"
              and "MODIS burning days actually observed ÷ MODIS burning days predicted" in page.inner_text("#drift-caption"), page.inner_text("#drift-caption")[:120])
        wait_season(page)
        check("burning days: season dates shown for Portugal, counted in burning days", page.locator("#season-dates").get_attribute("data-state") == "dated"
              and "burning days" in page.inner_text("#season-note"), page.inner_text("#season-dates").replace("\n", " "))
        jump = page.evaluate(r"""() => { const c = window.cedrus; const s = c.state.series; const y = (yr, a) => { let t = 0; for (let m = 1; m <= 12; m++) t += a[c.indexOf(yr, m)]; return t; };
          return { h11: y(2011, s.m), h12: y(2012, s.m), n11: y(2011, s.naive), n12: y(2012, s.naive) }; }""")
        info(f"burning days, 2011 -> 2012 totals: naive {jump['n11']:.0f} -> {jump['n12']:.0f} (x{jump['n12'] / jump['n11']:.2f}); "
             f"harmonized {jump['h11']:.0f} -> {jump['h12']:.0f} (x{jump['h12'] / jump['h11']:.2f})")
        page.wait_for_timeout(1500)
        page.screenshot(path=str(shots / "desktop_bd.png"), full_page=True)
        page.click("#cal-grid [data-year='2001'][data-moy='1']")
        check("burning days: a bridged month says Terra's share of MODIS burning days", "share of MODIS burning days" in page.inner_text("#month-body"),
              page.inner_text("#month-body")[:200].replace("\n", " "))
        # two models side by side: where the burning-day estimate is above the hotspot estimate, the panel says so
        mb = json.loads((ROOT / "web/data/portugal/monthly_bd.json").read_text(encoding="utf-8"))
        B = np.array(mb["m"]).sum(axis=0)
        H = np.array(json.loads((ROOT / "web/data/portugal/monthly.json").read_text(encoding="utf-8"))["m"]).sum(axis=0)
        up = [j for j in range(len(B)) if B[j] > H[j] and B[j] >= 0.5]
        down = [j for j in range(len(B)) if mb["flags"][j] == "E" and B[j] <= H[j]]
        page.wait_for_function("window.cedrus.state.loaded.has('portugal/hot')", timeout=60000)
        ym = lambda j: divmod(2000 * 12 + 11 + j, 12)
        y, mo = ym(up[0]); page.click(f"#cal-grid [data-year='{y}'][data-moy='{mo + 1}']")
        note = page.inner_text("#two-models") if page.locator("#two-models").count() else ""
        y2, mo2 = ym(down[0]); page.click(f"#cal-grid [data-year='{y2}'][data-moy='{mo2 + 1}']")
        none = page.locator("#two-models").count() == 0
        check("two models: where burning days exceed hotspots (whole region) the panel says so with both numbers; elsewhere it does not",
              f"burning-day estimate ({fmt_js(B[up[0]])}) is above the hotspot estimate ({fmt_js(H[up[0]])})" in note and "can’t happen in real counts" in note and none,
              f"{len(up)} such months in Portugal; {y}-{mo + 1:02d}: {note[:160]}")
        y, mo = ym(up[0]); page.click(f"#cal-grid [data-year='{y}'][data-moy='{mo + 1}']")
        page.locator("#month-panel").screenshot(path=str(shots / "desktop_bd_two_models.png"))
        page.select_option("#csv-from", "2000"); page.select_option("#csv-to", "2025")
        compare_bd(page, "burning days: Portugal whole region 2000-2025", dl, "portugal", bd_rounding_bound("portugal"))
        lat_s, lon_s = busiest_square("portugal")
        for lat, lon, km in ((37.3, -8.6, 12), (40.13, -8.36, 9), (39.6, -8.2, 25), (lat_s, lon_s, 1), (37.32, -8.55, 1.5), (37.32, -8.55, 3)):
            circle(page, lat, lon, km)
            info(f"burning days, {km} km circle at {lat},{lon}: {page.inner_text('#area-summary').replace(chr(10), ' ')[:200]}")
            compare_bd(page, f"burning days: {km} km circle at {lat},{lon}", dl, "portugal")
            if km == 12:
                page.click("#cal-grid [data-year='2023'][data-moy='8']")
                page.locator(".history").screenshot(path=str(shots / "desktop_bd_circle_12km.png"))
            if km == 1:
                page.locator("#month-panel").screenshot(path=str(shots / "desktop_bd_circle_1km_panel.png"))
            if km in (3, 25):
                anomaly_shares(page, f"burning days: {km} km circle at {lat},{lon}")
                if km == 3:
                    page.click("#mode-anomaly")
                    page.locator(".history").screenshot(path=str(shots / "desktop_bd_quiet_circle_anomaly.png"))
                    page.click("#mode-counts")
        for kind, ring in (("rectangle", [[-8.9, 38.3], [-7.9, 38.3], [-7.9, 39.1], [-8.9, 39.1], [-8.9, 38.3]]),
                           ("polygon", [[-8.4, 39.7], [-7.6, 40.4], [-7.4, 39.6], [-8.0, 39.3], [-8.4, 39.7]])):
            page.evaluate("([ring, kind]) => window.cedrus.useRing(ring, kind)", [ring, kind])
            page.wait_for_function(f"document.querySelector('#area-summary').textContent.includes('drawn {kind}')"
                                   " && !document.querySelector('#area-summary').textContent.includes('Reading')", timeout=120000)
            compare_bd(page, f"burning days: drawn {kind}", dl, "portugal")

        # ---- the switch: same area and month, the other unit; back again gives the same number; remembered for the session
        circle(page, 37.3, -8.6, 12)
        page.click("#cal-grid [data-year='2023'][data-moy='8']")
        v_bd = page.inner_text("#month-value")
        page.click("#unit-hot")
        page.wait_for_function("window.cedrus.state.loadedUnit === 'hot' && document.querySelector('#area-summary').textContent.includes('detections inside the shape')", timeout=120000)
        sw = page.evaluate("""() => ({ title: document.querySelector('#month-title').textContent, value: document.querySelector('#month-value').textContent,
          body: document.querySelector('#month-body').textContent, note: document.querySelector('#calendar-note').textContent,
          csv: [!document.querySelector('#csv-burning').hidden, !document.querySelector('#csv-hotspots').hidden],
          pressed: [document.querySelector('#unit-bd').getAttribute('aria-pressed'), document.querySelector('#unit-hot').getAttribute('aria-pressed')] })""")
        h_csv = pd.read_csv(download(page, "#csv-hotspots", dl), dtype={"acq_date": str})
        m_csv = read_monthly(download(page, "#csv-monthly", dl))[1]
        want_h = float(h_csv.loc[h_csv.acq_date.str[:7] == "2023-08", "w"].sum()) + float(m_csv.loc[m_csv.month == "2023-08", "background"].sum())
        check("switch to hotspots: same area and month, numbers and words in detections, hotspot downloads",
              sw["title"].startswith("August 2023 · 12 km around 37.300, -8.600") and "fire detections, harmonized" in sw["body"] and "in MODIS-equivalent detections" in sw["note"]
              and sw["csv"] == [False, True] and sw["pressed"] == ["false", "true"] and sw["value"] in (f"{want_h:.1f}", f"{round(want_h):,}"),
              f"burning days {v_bd} -> hotspots {sw['value']} (hotspot CSV {want_h:.2f}); {sw['title']}")
        page.click("#unit-bd")
        page.wait_for_function("window.cedrus.state.loadedUnit === 'bd' && document.querySelector('#area-summary').textContent.includes('burning days inside the shape')", timeout=120000)
        check("switch back to burning days: the same value again", page.inner_text("#month-value") == v_bd and "August 2023" in page.inner_text("#month-title"),
              f"{v_bd} -> {page.inner_text('#month-value')}")

        # ---- Lebanon in burning days: whole region and a small circle
        page.select_option("#region", "lebanon")
        page.wait_for_function("document.querySelector('#area-summary').textContent.includes('Lebanon (whole region)')", timeout=20000)
        lb_monthly, lb_rows = compare_bd(page, "burning days: Lebanon whole region", dl, "lebanon", bd_rounding_bound("lebanon"))
        zn = json.loads((ROOT / "web/data/lebanon/monthly_bd.json").read_text(encoding="utf-8"))["zero_notes"]
        first = sorted(zn)[0]
        tip = page.get_attribute(f"#cal-grid [data-year='{int(first[:4])}'][data-moy='{int(first[5:])}']", "aria-label")
        page.click(f"#cal-grid [data-year='{int(first[:4])}'][data-moy='{int(first[5:])}']")
        panel = page.inner_text("#zero-note") if page.locator("#zero-note").count() else ""
        csv_ok = lb_rows[lb_rows.acq_date.str[:7] == first].source_flag.str.contains(zn[first], regex=False).all() \
            and lb_monthly[lb_monthly.month == first].source_flag.str.contains(zn[first], regex=False).all()
        check(f"Lebanon {first}: the zero-weight note is in the tooltip, the panel and both burning-day CSVs", zn[first] in tip and zn[first] in panel and csv_ok, zn[first])
        page.locator("#month-panel").screenshot(path=str(shots / "desktop_bd_lebanon_zero_note.png"))
        hot = pd.read_csv(download(page, "#csv-hotspots", dl), dtype={"acq_date": str, "version": str}, low_memory=False)
        hm = json.loads((ROOT / "web/data/lebanon/monthly.json").read_text(encoding="utf-8"))
        hot_total = float(np.array(hm["m"]).sum()) - float(np.array(hm["bg"]).sum())
        idx = json.loads((ROOT / "web/data/regions.json").read_text(encoding="utf-8"))
        n_det = sum(next(r for r in idx["regions"] if r["id"] == "lebanon")["detections"].values())
        flags = set(hot.source_flag.dropna())
        check("burning-day view: the hotspot CSV downloads too, with the hotspot view's weights and notes",
              len(hot) == n_det and abs(hot.w.sum() - hot_total) <= rounding_bound("lebanon") and any("detections weigh 0" in f for f in flags)
              and not any("VIIRS burning days" in f for f in flags) and "hotspot view’s harmonized estimate" in page.inner_text("#csv-status"),
              f"{len(hot)} rows of {n_det}; sum w {hot.w.sum():.2f} vs {hot_total:.2f}; {page.inner_text('#csv-status')[:120]}")
        circle(page, 34.4, 36.1, 5)
        compare_bd(page, "burning days: Lebanon 5 km circle at 34.4,36.1", dl, "lebanon")
        small = page.evaluate("() => { const s = window.cedrus.state.series; for (let j = s.m.length - 1; j >= 0; j--) if (s.m[j] > 0 && s.m[j] < 0.05) return j; return -1; }")
        one = page.evaluate("() => { const s = window.cedrus.state.series; for (let j = s.m.length - 1; j >= 0; j--) if (Math.abs(s.m[j] - 1) < 0.005) return j; return -1; }")
        shown = {}
        for key, j in (("small", small), ("one", one)):
            if j >= 0:
                y, mo = divmod(2000 * 12 + 11 + j, 12)
                sel = f"#cal-grid [data-year='{y}'][data-moy='{mo + 1}']"
                shown[key] = (page.get_attribute(sel, "aria-label"), (page.click(sel), page.inner_text("#month-value"))[1])
        check("a value between 0 and 0.05 shows as <0.1 (its tooltip does not say 'no burning days'), and a value of 1 takes the singular unit",
              small >= 0 and one >= 0 and shown["small"][1] == "<0.1" and "no burning days" not in shown["small"][0] and re.search(r"(^|[^\d.])1 burning day(?!s)", shown["one"][0]) and "1 burning days" not in shown["one"][0],
              str(shown)[:600])
        page.select_option("#region", "portugal")
        page.wait_for_function("document.querySelector('#area-summary').textContent.includes('Portugal (whole region)')", timeout=20000)

        page.click("#unit-hot")
        page.wait_for_function("window.cedrus.state.loadedUnit === 'hot'", timeout=60000)
        page.goto(url, wait_until="commit")
        page.wait_for_function("window.cedrus", timeout=60000); page.evaluate("window.cedrus.ready")
        st = page.evaluate("() => ({ unit: window.cedrus.state.unit, pressed: document.querySelector('#unit-hot').getAttribute('aria-pressed'), note: document.querySelector('#calendar-note').textContent })")
        check("the unit is remembered for the session: after a reload the page opens in hotspots", st["unit"] == "hot" and st["pressed"] == "true"
              and "MODIS-equivalent detections" in st["note"], str(st)[:160])

        # ---- hotspots: everything the site did before, in the hotspot view
        n_cells = page.locator("#cal-grid [role=gridcell]").count()
        n_nd = page.locator("#cal-grid .cal-cell.nd").count()
        n_b = page.locator("#cal-grid .cal-cell.b").count()
        n_e = page.locator("#cal-grid .cal-cell.e").count()
        check("calendar rendered: 26 years x 12 months", n_cells == 312, f"{n_cells} cells; no-data {n_nd}, bridged {n_b}, estimated {n_e}")
        check("record = MODIS's first complete month (2000-12) to Dec 2025: no-data Jan-Nov 2000; bridged Dec 2000..Jun 2002; estimated 2022-01..2025-12",
              (n_nd, n_b, n_e) == (11, 19, 48) and json.loads((ROOT / "web/data/portugal/monthly.json").read_text(encoding="utf-8"))["months"]["first"] == "2000-12")
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
        check("hero badge in plain words: both units, both confirmed on unseen regions", page.inner_text("#data-badge").lower() == "burning days & hotspots · both confirmed on unseen regions", page.inner_text("#data-badge"))
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
        check("map cells are drawn at fill opacity 0.6", page.evaluate("window.cedrus.state.map.getPaintProperty('cells', 'fill-opacity')") == 0.6)
        page.click("#draw-rectangle")
        page.keyboard.press("Escape")
        st = page.evaluate("() => ({ drawing: window.cedrus.state.drawing, pressed: document.querySelector('#draw-rectangle').getAttribute('aria-pressed') })")
        check("Escape leaves drawing mode", st["drawing"] is None and st["pressed"] == "false", str(st))

        # ---- quiet areas: no false 2022 jump in anomaly mode
        for lat, lon, km in ((37.32, -8.55, 3), (39.6, -8.2, 25)):
            circle(page, lat, lon, km)
            anomaly_shares(page, f"{km} km circle at {lat},{lon}")
            if km == 3:
                page.locator(".history").screenshot(path=str(shots / "desktop_quiet_circle_anomaly.png"))
        page.click("#mode-anomaly")
        page.locator(".history").screenshot(path=str(shots / "desktop_quiet25_circle_anomaly.png"))
        page.click("#mode-counts")

        # ---- a shape over both regions, containing the whole of Portugal
        big = [[-10.5, 31.5], [37.5, 31.5], [37.5, 43.5], [-10.5, 43.5], [-10.5, 31.5]]
        page.evaluate("ring => window.cedrus.useRing(ring, 'polygon')", big)
        page.wait_for_function("document.querySelector('#area-summary').textContent.includes('containing all of')", timeout=120000)
        summary = page.inner_text("#area-summary")
        check("a shape over both regions says so and shows one", "spans Portugal and Lebanon — showing Portugal only; draw within one region" in summary, summary[:300])
        check("a shape containing all of Portugal is not called '100% outside'", "Most of this area is outside our data; showing all of Portugal’s detections inside it." in summary
              and "100%" not in summary and "containing all of Portugal" in summary)
        tot_shape = page.evaluate("() => window.cedrus.state.series.m.reduce((a, b) => a + b, 0)")
        tot_region = float(np.array(json.loads((ROOT / "web/data/portugal/monthly.json").read_text(encoding="utf-8"))["m"]).sum())
        check("... and its calendar holds all of Portugal's record", abs(tot_shape - tot_region) <= rounding_bound("portugal"),
              f"shape {tot_shape:.2f} vs region {tot_region:.2f}")
        page.click("#draw-clear")

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

        circle(page, 34.4, 36.1, 5)
        anomaly_shares(page, "Lebanon 5 km circle at 34.4,36.1")
        page.click("#mode-anomaly")
        page.locator(".history").screenshot(path=str(shots / "desktop_lebanon_circle_anomaly.png"))
        page.click("#mode-counts")
        page.locator("#month-panel").screenshot(path=str(shots / "desktop_lebanon_circle_panel.png"))
        info(f"Lebanon 5 km circle panel: {page.inner_text('#month-panel').replace(chr(10), ' | ')[:400]}")
        check("Lebanon 5 km circle: few-fires month in words, no % and no chance; the opening reason is stated",
              "A typical" in page.inner_text("#few-words") and "%" not in page.inner_text("#few-words")
              and "Chance it is above" not in page.inner_text("#month-panel")
              and page.inner_text("#month-eyebrow") in ("MOST RECENT MONTH WITH A FIRE NORMAL", "MOST RECENT MONTH WITH A DETECTION", "LATEST MONTH IN THE RECORD"),
              page.inner_text("#month-eyebrow"))
        page.click("#example-lebanon")
        page.wait_for_function("document.querySelector('#area-summary').textContent.includes('Lebanon (whole region)')", timeout=20000)

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
        r3 = page.inner_text("#r3-confirmation")
        check("methodology: both models in plain words, the honest history with round 3's five numbers, links, SHA-256s, credits",
              all(k in dlg for k in ("A2 + NOAA-20 via Suomi NPP (round-2 choice, frozen)", BD_MODEL,
                                     "Burning days (the default): how many days each ~1 km square had a fire detected, in MODIS-equivalent terms",
                                     "failed its sealed confirmation", "69%", "92.6%", "burning days harmonize better", "30.6%", "23.5%", "28.4%",
                                     "NOAA-20", "SHA-256", BD_SHA, "Kiln Watch", "Agun-Panjika", "Use of AI",
                                     "a small region-wide expected count per month and time of day for places where VIIRS saw nothing"))
              and all(k in r3 for k in ("confirmed", "29.7%", "36.2%", "83.8%", "1.069", "11.6%", "97.3%", "213 of 219"))
              and all(page.locator(f"#detail-dialog a[href$='/{d}']").count() == 1 for d in ("ROUND3_CONFIRMATION.md", "TOURNAMENT_RESULTS.md",
                      "ROUND2_CONFIRMATION.md", "ROUND2_SELECTION.md", "CONFIRMATION_RESULTS.md"))
              and page.inner_text("#r2-confirmation").startswith("confirmed") and "pending" not in r3
              and "Each sealed exam below was written down before it was run" in dlg and "are not exam results" in dlg
              and "equals the exact sum within rounding (≤ 0.1 per month)" in dlg and "Drawn shapes and circles are exact sums" in dlg
              and "In Lebanon, 850 of 4,142 VIIRS burning days since 2022 (21%) carry no weight" in page.inner_text("#zero-limit"), r3[:200])
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        know = readme[readme.index("## How we know it works"):readme.index("## Quick start")]
        check("README: burning days by default; round 1 failed, round 2 confirmed (hotspots), tournament, round 3 confirmed (burning days) with its five numbers; RESULTS.md earlier; MODIS C6.1; GIBS Blue Marble only",
              "The calendar opens in **burning days**" in readme and "failed its sealed confirmation" in know and "92.6%" in know and "69%" in know
              and "**Round 2 confirmed, for hotspots.**" in know and "**Round 3 confirmed, for burning days.**" in know
              and all(k in know for k in ("29.7%", "83.8%", "1.069", "11.6%", "97.3%", "213 of 219", "30.6%", "23.5%", "28.4%"))
              and all(f"docs/{d}" in know for d in ("ROUND3_CONFIRMATION.md", "TOURNAMENT_RESULTS.md", "ROUND2_CONFIRMATION.md", "ROUND2_SELECTION.md", "CONFIRMATION_RESULTS.md"))
              and "pending" not in know and "Estimates start in 2022" in readme and "Corrected values after 2012" not in readme
              and "whole-region totals equal the\nexact sum within rounding (≤ 0.1 per month)" in readme.replace("\r\n", "\n")
              and "is an earlier test of an earlier method" in readme and "MODIS Collection 6.1" in readme
              and "Basemap: NASA GIBS Blue Marble." in readme and "reference features and labels" not in readme)
        check("README: Suomi NPP stops delivering data on 2 Nov 2026", "stops delivering data on **2 Nov 2026**" in readme
              and "1 November 2026" not in readme)
        page.screenshot(path=str(shots / "desktop_methodology.png"))
        page.click(".dialog-done")
        check("unused v1 files removed", not (ROOT / "web/data/portugal.json").exists() and not (ROOT / "web/data/portugal-cells.geojson").exists())
        page.wait_for_timeout(2500)
        page.screenshot(path=str(shots / "desktop.png"), full_page=True)
        ctx.close()

        # ---- a unit whose calendar file fails: the switch does not happen, nothing is relabelled, a retry works
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        page = ctx.new_page()
        page.route("**/data/portugal/monthly.json", lambda route: route.fulfill(status=503, body="unavailable"))
        page.goto(url, wait_until="commit")
        page.wait_for_function("window.cedrus", timeout=60000); page.evaluate("window.cedrus.ready")
        snap = "() => ({ unit: window.cedrus.state.unit, loaded: window.cedrus.state.loadedUnit, note: document.querySelector('#calendar-note').textContent, value: document.querySelector('#month-value')?.textContent, title: document.querySelector('#month-title').textContent, pressed: [document.querySelector('#unit-bd').getAttribute('aria-pressed'), document.querySelector('#unit-hot').getAttribute('aria-pressed')], status: document.querySelector('#unit-status').hidden ? '' : document.querySelector('#unit-status-text').textContent, monthly: !document.querySelector('#csv-monthly').disabled })"
        before = page.evaluate(snap)
        page.click("#unit-hot")
        page.wait_for_selector("#unit-status:not([hidden])", timeout=60000)
        after = page.evaluate(snap)
        check("unit switch fails (monthly.json 503): stays on burning days with its labels and numbers, says so with a retry",
              after["status"] == "Couldn’t load hotspot counts — try again." and after["unit"] == after["loaded"] == "bd" and after["pressed"] == ["true", "false"]
              and {k: after[k] for k in ("note", "value", "title")} == {k: before[k] for k in ("note", "value", "title")} and after["monthly"], str(after)[:300])
        mpath = download(page, "#csv-monthly", dl)
        check("... and the monthly CSV is still the burning-day one", mpath.name.endswith("_monthly_burning_days.csv")
              and mpath.read_text(encoding="utf-8").startswith("# CEDRUS monthly burning days"), mpath.name)
        page.locator("#area-form").screenshot(path=str(shots / "desktop_unit_switch_failed.png"))
        page.unroute("**/data/portugal/monthly.json")
        page.click("#unit-retry")
        page.wait_for_function("window.cedrus.state.loadedUnit === 'hot' && document.querySelector('#calendar-note').textContent.includes('detections')", timeout=60000)
        st = page.evaluate(snap)
        check("... the retry switches to hotspots", st["status"] == "" and st["pressed"] == ["false", "true"], str(st)[:200])
        ctx.close()

        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
        page = ctx.new_page()
        page.route("**/data/portugal/monthly_bd.json", lambda route: route.fulfill(status=503, body="unavailable"))
        page.goto(url, wait_until="commit")
        page.wait_for_function("window.cedrus", timeout=60000); page.evaluate("window.cedrus.ready")
        page.wait_for_selector("#unit-status:not([hidden])", timeout=60000)
        st = page.evaluate('''() => ({ status: document.querySelector("#unit-status-text").textContent, retry: !!document.querySelector("#unit-retry"),
          cells: document.querySelectorAll("#cal-grid [role=gridcell]").length, note: document.querySelector("#calendar-note").textContent,
          csv: ["#csv-burning", "#csv-hotspots", "#csv-monthly"].map((b) => document.querySelector(b).disabled), badge: document.querySelector("#data-badge").textContent })''')
        check("start-up failure of monthly_bd.json: a clear error with a retry, no numbers, downloads off",
              st["status"] == "Couldn’t load burning days — try again." and st["retry"] and st["cells"] == 0 and st["note"] == st["status"]
              and st["csv"] == [True, True, True] and st["badge"] != "NO DATA", str(st)[:300])
        try:
            page.wait_for_function("document.querySelector('#map-loading').hidden || !document.querySelector('#map-loading').textContent.startsWith('Loading map')", timeout=150000)
            map_ok = True
        except Exception:
            map_ok = False
        check("... the map does not stay on 'Loading map…'", map_ok, page.inner_text("#map-loading") if page.locator("#map-loading").is_visible() else "map loaded")
        page.screenshot(path=str(shots / "desktop_startup_failed.png"), full_page=True)
        page.click("#unit-hot")
        page.wait_for_function("window.cedrus.state.loadedUnit === 'hot' && document.querySelectorAll('#cal-grid [role=gridcell]').length === 312", timeout=60000)
        st = page.evaluate("() => ({ status: document.querySelector('#unit-status').hidden, pressed: document.querySelector('#unit-hot').getAttribute('aria-pressed'), note: document.querySelector('#calendar-note').textContent })")
        check("... the Hotspots button still works", st["status"] and st["pressed"] == "true" and "detections" in st["note"], str(st)[:200])
        page.unroute("**/data/portugal/monthly_bd.json")
        page.click("#unit-bd")
        page.wait_for_function("window.cedrus.state.loadedUnit === 'bd' && document.querySelector('#calendar-note').textContent.includes('burning days')", timeout=60000)
        check("... and burning days load once the file is back", page.get_attribute("#unit-bd", "aria-pressed") == "true")
        ctx.close()

        # ---- a failed hotspot year: no numbers under the new name, downloads off, retry works
        ctx = browser.new_context(viewport={"width": 1440, "height": 900}, accept_downloads=True)
        page = ctx.new_page()
        page.route("**/data/portugal/*/2015.json", lambda route: route.fulfill(status=503, body="unavailable"))  # burning/ (the default view) and hotspots/
        page.goto(url, wait_until="commit")
        page.wait_for_function("window.cedrus", timeout=60000); page.evaluate("window.cedrus.ready")
        page.fill("#lat", "39.6"); page.fill("#lon", "-8.2"); page.fill("#radius", "25"); page.click("#circle-go")
        page.wait_for_selector("#load-error", timeout=120000)
        st = page.evaluate("""() => ({ err: document.querySelector('#load-error').textContent, label: document.querySelector('#area-summary strong').textContent,
          title: document.querySelector('#month-title').textContent, cells: document.querySelectorAll('#cal-grid [role=gridcell]').length,
          csv: [document.querySelector('#csv-hotspots').disabled, document.querySelector('#csv-monthly').disabled],
          retry: !!document.querySelector('#retry-area'), caption: document.querySelector('#map-caption').textContent })""")
        check("failed year (503): error names the year in the view's unit, offers a retry", st["err"] == "Couldn’t load burning days for 2015 — try again." and st["retry"], st["err"])
        check("failed year: no numbers shown under the new name, label and title agree, downloads disabled",
              st["cells"] == 0 and st["csv"] == [True, True] and "25 km around 39.600, -8.200" in st["label"] and st["title"] == st["label"]
              and "over http" not in st["caption"], str(st)[:300])
        stale = page.evaluate("""() => ({ progress: document.querySelector('#cal-progress').hidden, note: document.querySelector('#calendar-note').textContent,
          legend: document.querySelector('#calendar-legend').textContent, season: document.querySelector('#season-eyebrow').textContent })""")
        check("failed year: no stale texts (progress hidden, calendar note and season name the failure and the new area)",
              stale["progress"] and "2015" in stale["note"] and not stale["legend"] and "25 KM AROUND" in stale["season"], str(stale)[:240])
        page.screenshot(path=str(shots / "desktop_load_error.png"), full_page=True)
        page.unroute("**/data/portugal/*/2015.json")
        page.click("#retry-area")
        page.wait_for_function("document.querySelectorAll('#cal-grid [role=gridcell]').length === 312", timeout=120000)
        ok = page.evaluate("() => !document.querySelector('#csv-hotspots').disabled && !document.querySelector('#csv-monthly').disabled && !document.querySelector('#load-error')")
        check("retry after the failure loads the area and turns downloads back on", ok)
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
        badge = page.evaluate("(() => { const b = document.querySelector('.hero-badge'); const r = b.getBoundingClientRect(); const h = document.querySelector('.hero').getBoundingClientRect(); return { left: r.left, right: r.right, hRight: h.right, scroll: b.scrollWidth, client: b.clientWidth, text: b.innerText }; })()")
        check("mobile 390 px: hero badge not clipped", badge["right"] <= badge["hRight"] and badge["left"] >= 0 and badge["scroll"] <= badge["client"] + 1,
              f"{badge}"[:200])
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
