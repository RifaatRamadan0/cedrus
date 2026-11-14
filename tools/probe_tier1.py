"""Full-catalog Tier 1 checks, called by probe_site without changing legacy assertions."""
import io
import json
import math
import re
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
NEW = ("syria", "la_rioja")  # Jordan and Cyprus were removed from the app on 10 Nov 2026


def ring_for(lat, lon):
    return [[lon + 5 * math.cos(i * 2 * math.pi / 72) / (111.32 * math.cos(lat * math.pi / 180)),
             lat + 5 * math.sin(i * 2 * math.pi / 72) / 110.57] for i in range(73)]


def inside(x, y, ring):
    result = False
    for a, b in zip(ring, ring[1:] + ring[:1]):
        if (a[1] > y) != (b[1] > y) and x < (b[0]-a[0])*(y-a[1])/(b[1]-a[1])+a[0]:
            result = not result
    return result


def independent_shares(ring, catalog, unit):
    xs, ys = zip(*ring); x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    points = [(x0+(i+.5)/64*(x1-x0), y0+(j+.5)/64*(y1-y0)) for i in range(64) for j in range(64)]
    points = [(x, y) for x, y in points if inside(x, y, ring)]
    scores = []
    for meta in catalog:
        a, b, c, d = meta["bbox"]
        if not (x0 < c and x1 > a and y0 < d and y1 > b):
            continue
        mon = json.loads((ROOT / "web/data" / meta["id"] / ("monthly_bd.json" if unit == "bd" else "monthly.json")).read_text(encoding="utf-8"))
        footprint = set(zip(mon["cells"]["ix"], mon["cells"]["iy"]))
        share = sum(a <= x < c and b <= y < d and (math.floor(x/mon["cell_deg"]), math.floor(y/mon["cell_deg"])) in footprint for x, y in points)/len(points)
        scores.append({"id": meta["id"], "name": meta["name"], "share": share})
    return sorted(scores, key=lambda r: -r["share"])


OPEN_MORE = "document.querySelectorAll('details.more').forEach((d) => { d.open = true; })"  # folded sections


def download(page, selector, target):
    page.evaluate(OPEN_MORE)
    with page.expect_download(timeout=180000) as event:
        page.click(selector)
    event.value.save_as(target)
    return target


def run_checks(browser, url, shots, check, watch):
    catalog = json.loads((ROOT / "web/data/regions.json").read_text(encoding="utf-8"))["regions"]
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    page = ctx.new_page(); watch(page, "tier1 ")
    page.goto(url, wait_until="commit"); page.wait_for_function("window.cedrus", timeout=60000); page.evaluate("window.cedrus.ready")
    # Every product region in regions.json, in catalog order (was a fixed list of the four regions of 12 Nov 2026).
    check("Tier 1: full catalog loads (every product region in regions.json)", [r["id"] for r in page.evaluate("window.cedrus.state.index.regions")] == [r["id"] for r in catalog])
    out = ROOT / "analysis/tier1"; reconciliations = []; cities = []
    downloads = shots / "downloads"
    for rid in NEW:
        page.evaluate("id => window.cedrus.useRegion(id)", rid)
        for unit, filename, folder in (("bd", "monthly_bd.json", "burning"), ("hot", "monthly.json", "hotspots")):
            page.evaluate("u => window.cedrus.setUnit(u)", unit)
            label = f"Tier 1 {rid} {unit}"
            check(label+": calendar loads", page.locator("#cal-grid [role=gridcell]").count() > 0 and page.evaluate("window.cedrus.state.meta.id") == rid)
            text = page.inner_text("#region-notes")
            expected = "Counts all fires FIRMS detects, from any cause, including agricultural burning and conflict. Static heat sources (type 2) are excluded. Monthly completeness is unknown; known FIRMS data gaps are listed in the docs."
            check(label+": region notes visible", expected in text and page.locator("#region-notes").is_visible() and (rid != "la_rioja" or "Annual totals in the 2020-2021 test were above the 80% range." in text))
            # Every region states the 2022-2025 limit; Syria also states its own forward test.
            drift = "Accuracy is checked against MODIS only up to 2021."
            forward = "Forward test against MODIS, 2020–2021 (fitted on 2012–2019):"
            check(label+": accuracy notes visible", drift in text and (rid == "la_rioja" or forward in text), text)
            if rid == "syria":
                check(label+": border-cell limit visible", "Cells on Syria's borders also cover land in neighbouring countries" in text, text)
            path = download(page, "#csv-monthly", downloads / f"tier1_{rid}_{unit}.csv")
            table = pd.read_csv(path, comment="#")
            mon = json.loads((ROOT / "web/data" / rid / filename).read_text(encoding="utf-8"))
            months = pd.period_range(mon["months"]["first"], mon["months"]["last"], freq="M").astype(str).tolist()
            values = np.asarray(mon["m"]).sum(axis=0); bg = np.asarray(mon["bg"]).sum(axis=0)
            sums, counts = {m: 0.0 for m in months}, {m: 0 for m in months}
            for file in (ROOT / "web/data" / rid / folder).glob("*.json"):
                f = json.loads(file.read_text(encoding="utf-8")); c = f["cols"]
                for doy, w in zip(c["doy"], c["w"]):
                    month = (date(f["year"], 1, 1)+timedelta(days=doy-1)).isoformat()[:7]
                    sums[month] += w; counts[month] += 1
            csv_values = table.set_index("month").reindex(months).harmonized_estimate.to_numpy()
            check(label+": whole-region CSV equals monthly file sum", np.isfinite(csv_values).all() and np.max(np.abs(csv_values-values)) <= .000051)
            gaps = np.abs(csv_values - np.array([sums[m] for m in months]) - bg)
            bounds = np.array([.005*len(mon["cells"]["ix"])+.00005*counts[m]+.0001 for m in months])
            check(label+": every CSV month equals record weights plus background within serialization rounding", bool(np.all(gaps <= bounds)), f"max gap {max(gaps):.6f}")
            reconciliations.append(dict(region=rid, unit=unit, months=len(months), max_gap=float(max(gaps)), max_rounding_bound=float(max(bounds))))
            if rid == "la_rioja":
                for year in (2020, 2024):
                    page.evaluate("y => window.cedrus.selectMonth(window.cedrus.indexOf(y+1, 1))", year)
                    wanted_months = pd.period_range(f"{year}-08", f"{year+1}-02", freq="M").astype(str)
                    expected_total = sum(values[months.index(m)] for m in wanted_months)
                    shown = float(page.get_attribute("#cross-year-season", "data-total"))
                    season_path = download(page, "#csv-monthly", downloads / f"season_{year}_{unit}.csv")
                    body = season_path.read_text(encoding="utf-8"); match = re.search(r"# Season .*; total=([\d.]+);", body)
                    exported = float(match.group(1)) if match else float("nan")
                    season_rows = pd.read_csv(io.StringIO(body), comment="#")
                    month_sum = season_rows.loc[season_rows.month.isin(wanted_months), "harmonized_estimate"].sum()
                    check(label+f": Aug {year}–Feb {year+1} page and CSV equal seven-month sum", abs(shown-expected_total)<1e-8 and abs(exported-month_sum)<.0004 and len(wanted_months)==7, f"page {shown:.4f}, CSV {exported:.4f}, months {month_sum:.4f}")
            # Whole-region creative features in each unit, without changing their implementations.
            page.evaluate("window.cedrus.selectMonth(window.cedrus.indexOf(2020, 7))")
            page.click("#story-go")
            check(label+": story opens for selected region", page.locator("#story-card").is_visible() and bool(page.inner_text("#story-title")))
            page.click("#story-exit")
            page.evaluate("window.cedrus.selectMonth(window.cedrus.indexOf(2020, 7))")
            before = page.evaluate("window.cedrus.state.sel")
            page.click("#play"); page.wait_for_timeout(350); page.evaluate("window.cedrus.fx.pause()")
            check(label+": playback advances", page.evaluate("window.cedrus.state.sel") != before)
            page.evaluate(OPEN_MORE); page.click("#rings-toggle")
            check(label+": tree rings render", page.locator("#rings-svg path").count() > 0)
            page.evaluate(OPEN_MORE); page.click("#rings-toggle")
            png = download(page, "#share-card", downloads / f"fingerprint_{rid}_{unit}.png")
            check(label+": fingerprint PNG exports", png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") and png.stat().st_size > 1000)
        page.screenshot(path=str(shots / f"tier1_{rid}.png"), full_page=True)
    # Lebanon is not a Tier 1 region, but its limitation notes (forward test, shared border cells) were added later.
    page.evaluate("window.cedrus.useRegion('lebanon')")
    for unit in ("bd", "hot"):
        page.evaluate("u => window.cedrus.setUnit(u)", unit)
        text = page.inner_text("#region-notes")
        check(f"Lebanon {unit}: forward-test and border-cell notes visible",
              page.locator("#region-notes").is_visible() and "Accuracy is checked against MODIS only up to 2021." in text
              and "Forward test against MODIS, 2020–2021 (fitted on 2012–2019): failed the check" in text
              and "11 of Lebanon's 28 grid cells lie on the border" in text, text)
    # Portugal's passing result is shown with its limits, so a pass is not read as accuracy for every year or cell.
    page.evaluate("window.cedrus.useRegion('portugal')")
    for unit in ("bd", "hot"):
        page.evaluate("u => window.cedrus.setUnit(u)", unit)
        text = page.inner_text("#region-notes")
        check(f"Portugal {unit}: forward-test note visible with its limits",
              page.locator("#region-notes").is_visible() and "Accuracy is checked against MODIS only up to 2021." in text
              and "Forward test against MODIS, 2020–2021 (fitted on 2012–2019): met every pass rule" in text
              and "It does not show accuracy after 2021 or for single grid cells" in text, text)
    points = [("Beirut",33.8938,35.5018,"lebanon"), ("Damascus",33.5138,36.2765,"syria"),
              ("Homs",34.7324,36.7137,"syria")]
    for unit in ("bd", "hot"):
        page.evaluate("u => window.cedrus.setUnit(u)", unit)
        for name, lat, lon, expected in points:
            ring = ring_for(lat, lon); scores = independent_shares(ring, catalog, unit)
            page.evaluate("o => window.cedrus.useRing(o.ring, 'circle', {lat:o.lat, lon:o.lon, radius:5})", dict(ring=ring, lat=lat, lon=lon))
            picked = page.evaluate("window.cedrus.state.meta.id")
            warning = page.inner_text("#spans-warning") if page.locator("#spans-warning").count() else ""
            others = [r for r in scores if r["id"] != picked and r["share"] > .1]
            check(f"Tier 1 {name} {unit}: selects largest footprint (fixed expected region where specified)", picked == scores[0]["id"] and (expected is None or picked == expected), f"picked {picked}; shares {scores}")
            check(f"Tier 1 {name} {unit}: warning follows >10% alternative footprint rule", bool(warning)==bool(others) and all(r["name"] in warning for r in others), warning)
            cities.append(dict(city=name, lat=lat, lon=lon, radius_km=5, unit=unit, picked=picked, warning=warning, shares=scores, prescribed_expected=expected))
            if others:
                original = page.evaluate("JSON.stringify(window.cedrus.state.area.ring)")
                page.select_option("#region", others[0]["id"])
                page.wait_for_function("id => window.cedrus.state.meta.id === id && window.cedrus.state.series != null", arg=others[0]["id"], timeout=120000)
                check(f"Tier 1 {name} {unit}: picker switches same drawing", page.evaluate("JSON.stringify(window.cedrus.state.area.ring)") == original)
    for unit in ("bd", "hot"):
        page.evaluate("u => window.cedrus.setUnit(u)", unit)
        for name, lat, lon in (("Tel Aviv", 32.0853, 34.7818), ("Mediterranean", 33.5, 33.5), ("Amman", 31.9539, 35.9106),
                               ("Nicosia", 35.1856, 33.3823), ("Western Iraq", 32.4, 42.3)):
            accepted = page.evaluate("o => window.cedrus.useRing(o.ring, 'circle', {lat:o.lat, lon:o.lon, radius:5})",
                                     dict(ring=ring_for(lat, lon), lat=lat, lon=lon))
            # The western-Iraq circle is inside Syria's box but has no Syria grid cell: refused, and the toast says
            # Syria has no records there instead of "outside the regions we cover". The others touch no box.
            expected = "No fire records from Syria fall inside this area" if name == "Western Iraq" else "Outside the regions we cover"
            toast = page.inner_text(".toast")
            check(f"Tier 1 {name} {unit}: outside covered regions", accepted is False and expected in toast and page.locator(".toast").is_visible(), toast)
        for target in ("la_rioja", "syria"):
            for month in ("2025-12", "2020-07"):
                page.evaluate("window.cedrus.useRegion('lebanon')")
                page.evaluate("key => window.cedrus.selectMonth(window.cedrus.indexOf(...key.split('-').map(Number)))", month)
                for rid in (target, "lebanon"):
                    page.select_option("#region", rid)
                    page.wait_for_function("id => window.cedrus.state.meta.id === id && window.cedrus.state.series != null", arg=rid, timeout=120000)
                    snapshot = page.evaluate("""() => {
                        const s = window.cedrus.state;
                        const j = s.sel, start = s.monthly.months.first.split('-').map(Number);
                        const k = start[0]*12+start[1]-1+j;
                        return {key: `${Math.floor(k/12)}-${String(k%12+1).padStart(2,'0')}`,
                            value: s.series.m[j], sum: s.monthly.m.reduce((v,row)=>v+row[j],0),
                            finite: s.monthly.m.every(row=>Number.isFinite(row[j])),
                            caption: document.querySelector('#map-caption').textContent};
                    }""")
                    check(f"Tier 1 switch {target} <-> Lebanon {unit} {month} to {rid}: date and series/map aligned", snapshot["key"] == month and snapshot["finite"] and abs(snapshot["value"]-snapshot["sum"]) < 1e-8 and "undefined" not in snapshot["caption"])
                    other = "hot" if unit == "bd" else "bd"
                    page.evaluate("u => window.cedrus.setUnit(u)", other)
                    page.evaluate("u => window.cedrus.setUnit(u)", unit)
                    check(f"Tier 1 switch {rid} {month}: unit round trip preserves date", page.evaluate("key => window.cedrus.state.sel === window.cedrus.indexOf(...key.split('-').map(Number))", month))
    (out / "tier1_reconciliation.json").write_text(json.dumps(reconciliations, indent=2)+"\n")
    (out / "city_selection.json").write_text(json.dumps(cities, indent=2)+"\n")
    # Coverage explanations must work for existing and new regions, in both units.
    for meta in catalog:
        rid = meta["id"]
        page.evaluate("id => window.cedrus.useRegion(id)", rid)
        for unit in ("bd", "hot"):
            page.evaluate("u => window.cedrus.setUnit(u)", unit)
            prefix = f"Map clarity {rid} {unit}"
            check(prefix+": analysis extent is not labelled as a border", "analysis extent — not the country boundary" in page.inner_text("#map-extent-note"))
            check(prefix+": legend explains blank areas and unknown completeness", "Blank does not mean confirmed fire-free" in page.inner_text(".map-coverage") and "Observation completeness is unknown" in page.inner_text(".map-coverage"))
            point = page.evaluate("""() => {
                const s = window.cedrus.state, mon = s.monthly;
                for (let c=0;c<mon.m.length;c++) {
                    const j=mon.m[c].findIndex((v,j)=>v<0.005 && mon.flags[j]!=='X');
                    if (j>=0) return {j,lon:(mon.cells.ix[c]+.5)*mon.cell_deg,lat:(mon.cells.iy[c]+.5)*mon.cell_deg};
                }
                return null;
            }""")
            check(prefix+": near-zero cell fixture exists", point is not None)
            if point is not None:
                page.evaluate("j => window.cedrus.selectMonth(j)", point["j"])
                page.evaluate("p => window.cedrus.state.map.fire('click', {lngLat:{lng:p.lon,lat:p.lat}})", point)
                detail = page.inner_text("#map-cell-detail")
                check(prefix+": included near-zero cell explains estimate and uncertainty", "Included in" in detail and "Near-zero estimate" in detail and "Observation completeness unknown" in detail and meta["name"] in detail)
                check(prefix+": faint outline layer renders included quiet cells", page.evaluate("!!window.cedrus.state.map.getLayer('quiet-cells-line')") and "Near-zero estimate" in page.inner_text(".maplibregl-popup-content"))
            absent = page.evaluate("""() => {
                const features=window.cedrus.state.map.getStyle().sources['absent-cells'].data.features;
                if (!features.length) return null;
                const ring=features[0].geometry.coordinates[0];
                return {lon:(ring[0][0]+ring[2][0])/2,lat:(ring[0][1]+ring[2][1])/2};
            }""")
            # A region whose grid fills its whole box has no absent cell to click (central Spain: 160 of 160 cells).
            lon0, lat0, lon1, lat1 = meta["bbox"]
            box_cells = (math.ceil(lon1 / 0.25 - 1e-9) - math.floor(lon0 / 0.25)) * (math.ceil(lat1 / 0.25 - 1e-9) - math.floor(lat0 / 0.25))
            check(prefix+": absent-cell fixture exists, or the grid fills the whole box", absent is not None or meta["cells"] == box_cells,
                  f"no absent cell; {meta['cells']} of {box_cells} box cells in the grid" if absent is None else "")
            if absent is not None:
                page.evaluate("p => window.cedrus.state.map.fire('click', {lngLat:{lng:p.lon,lat:p.lat}})", absent)
                detail = page.inner_text("#map-cell-detail")
                check(prefix+": gap is not described as observed zero fires", "Not included in" in detail and "no qualifying fire records" in detail and "No cell estimate" in detail and "no fire observations for this location are available" in detail and "fire-free" not in detail)
                check(prefix+": gap has a separate shaded dashed layer", page.evaluate("window.cedrus.state.map.getPaintProperty('absent-cells', 'fill-opacity') > 0 && window.cedrus.state.map.getPaintProperty('absent-cells-line', 'line-dasharray').length > 0"))
            positive = page.evaluate("""() => {
                const s = window.cedrus.state, mon = s.monthly;
                for (let c=0;c<mon.m.length;c++) {
                    const j=mon.m[c].findIndex((v,j)=>v>=1 && mon.flags[j]!=='X');
                    if (j>=0) return {j,lon:(mon.cells.ix[c]+.5)*mon.cell_deg,lat:(mon.cells.iy[c]+.5)*mon.cell_deg};
                }
                return null;
            }""")
            # The drawing and the message use one limit: a cell is faint (outline, transparent fill) exactly when its
            # value rounds to zero at the displayed precision (under 0.05), and the message then says near-zero.
            band = page.evaluate("""() => {
                const s = window.cedrus.state, mon = s.monthly;
                for (let c=0;c<mon.m.length;c++) {
                    const j=mon.m[c].findIndex((v,j)=>v>=0.005 && v<0.05 && mon.flags[j]!=='X');
                    if (j>=0) return {j,v:mon.m[c][j],lon:(mon.cells.ix[c]+.5)*mon.cell_deg,lat:(mon.cells.iy[c]+.5)*mon.cell_deg};
                }
                return null;
            }""")
            if band is not None:
                page.evaluate("j => window.cedrus.selectMonth(j)", band["j"])
                drawn = page.evaluate("""() => window.cedrus.state.map.getStyle().sources.cells.data.features.map(f => [f.properties.v, f.properties.quiet, f.properties.color === 'rgba(0,0,0,0)'])""")
                page.evaluate("p => window.cedrus.state.map.fire('click', {lngLat:{lng:p.lon,lat:p.lat}})", band)
                detail = page.inner_text("#map-cell-detail")
                check(prefix+": faint cells are exactly the values under 0.05, and a 0.005-0.05 cell is faint and called near-zero",
                      all(q == (v < 0.05) and t == q for v, q, t in drawn) and "Near-zero estimate" in detail and "<0.1" in detail,
                      f"v={band['v']:.4f}; {detail[:200]}")
            if positive is not None:
                page.evaluate("j => window.cedrus.selectMonth(j)", positive["j"])
                page.evaluate("p => window.cedrus.state.map.fire('click', {lngLat:{lng:p.lon,lat:p.lat}})", positive)
                detail = page.inner_text("#map-cell-detail")
                check(prefix+": positive estimate does not repeat the generic completeness warning",
                      "harmonized estimate" in detail and "Observation completeness" not in detail and "fire-free" not in detail, detail[:240])
            page.evaluate("window.cedrus.selectMonth(window.cedrus.indexOf(2020, 7))")
            check(prefix+": changing month clears stale inspection", page.locator(".maplibregl-popup").count()==0 and page.inner_text("#map-cell-detail").startswith("Click the map"))
        if rid == "syria":
            page.locator("#map-panel").scroll_into_view_if_needed()
            page.screenshot(path=str(shots / "map_clarity_syria.png"), full_page=True)
    # Gap warnings are FIRMS-reported missing-data dates, from FIRMS's own list (web/data/firms_missing_dates.json).
    gaps = json.loads((ROOT / "web/data/firms_missing_dates.json").read_text(encoding="utf-8"))
    def click_positive(rid, year, moy):
        page.evaluate("id => window.cedrus.useRegion(id)", rid)
        page.wait_for_function(f"window.cedrus.state.meta && window.cedrus.state.meta.id === '{rid}' && window.cedrus.state.monthly && window.cedrus.state.gaps", timeout=60000)
        j = page.evaluate(f"window.cedrus.indexOf({year}, {moy})")
        page.evaluate("j => window.cedrus.selectMonth(j)", j)
        p = page.evaluate("""j => { const mon = window.cedrus.state.monthly;
            for (let c=0;c<mon.m.length;c++) if (mon.m[c][j] >= 0.05) return {lon:(mon.cells.ix[c]+.5)*mon.cell_deg,lat:(mon.cells.iy[c]+.5)*mon.cell_deg};
            return null; }""", j)
        page.evaluate("p => window.cedrus.state.map.fire('click', {lngLat:{lng:p.lon,lat:p.lat}})", p)
        return j, page.inner_text("#map-cell-detail")
    listed = [d for d in gaps["dates"]["N"] if d.startswith("2024-07")]
    _, detail = click_positive("portugal", 2024, 7)
    check("FIRMS-reported gap: Portugal July 2024 names FIRMS's listed Suomi NPP missing dates, as reported by FIRMS", len(listed) > 0
          and f"FIRMS-reported missing data: FIRMS’s missing-data list reports no standard data for Suomi NPP VIIRS on {len(listed)} days" in detail
          and "as reported by FIRMS, not outages verified independently here" in detail and "not specific to this location" in detail, detail[:400])
    _, detail = click_positive("portugal", 2019, 7)
    check("FIRMS-reported gap: a month with no FIRMS-listed date for the satellites it uses has no gap note",
          not any(d.startswith("2019-07") for s in ("T", "A") for d in gaps["dates"][s]) and "FIRMS-reported missing data" not in detail, detail[:240])
    contradicted = [d for d in gaps["contradicted"]["N"] if d.startswith("2026-05")]
    j, detail = click_positive("lebanon", 2026, 5)
    check("FIRMS-reported gap: Suomi NPP May 2026 (listed by FIRMS, but the standard files hold its detections) gives no warning",
          len(contradicted) == 31 and not any(d.startswith("2026-05") for d in gaps["dates"]["N"]) and "FIRMS-reported missing data" not in detail, detail[:240])
    # No region has a month without any VIIRS satellite, so the message is checked on a simulated one.
    page.evaluate("""j => { const m = window.cedrus.state.monthly; m._flags = m.flags; m.flags = m.flags.slice(0, j) + 'X' + m.flags.slice(j + 1); }""", j)
    p = page.evaluate("() => { const m = window.cedrus.state.monthly; return {lon:(m.cells.ix[0]+.5)*m.cell_deg, lat:(m.cells.iy[0]+.5)*m.cell_deg}; }")
    page.evaluate("p => window.cedrus.state.map.fire('click', {lngLat:{lng:p.lon,lat:p.lat}})", p)
    detail = page.inner_text("#map-cell-detail")
    page.evaluate("() => { const m = window.cedrus.state.monthly; m.flags = m._flags; delete m._flags; }")
    check("No-data month: the message says satellite observations are unavailable",
          "No satellite observations are available for May 2026" in detail and "no estimate" in detail, detail[:240])
    ctx.close()
