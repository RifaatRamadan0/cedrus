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
NEW = ("syria", "jordan", "cyprus", "la_rioja")


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
        mon = json.loads((ROOT / "web/data" / meta["id"] / ("monthly_bd.json" if unit == "bd" else "monthly.json")).read_text())
        footprint = set(zip(mon["cells"]["ix"], mon["cells"]["iy"]))
        share = sum(a <= x < c and b <= y < d and (math.floor(x/mon["cell_deg"]), math.floor(y/mon["cell_deg"])) in footprint for x, y in points)/len(points)
        scores.append({"id": meta["id"], "name": meta["name"], "share": share})
    return sorted(scores, key=lambda r: -r["share"])


def download(page, selector, target):
    with page.expect_download(timeout=180000) as event:
        page.click(selector)
    event.value.save_as(target)
    return target


def run_checks(browser, url, shots, check, watch):
    catalog = json.loads((ROOT / "web/data/regions.json").read_text())["regions"]
    ctx = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
    page = ctx.new_page(); watch(page, "tier1 ")
    page.goto(url, wait_until="commit"); page.wait_for_function("window.cedrus", timeout=60000); page.evaluate("window.cedrus.ready")
    check("Tier 1: full six-region catalog loads", len(page.evaluate("window.cedrus.state.index.regions")) == 6)
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
            path = download(page, "#csv-monthly", downloads / f"tier1_{rid}_{unit}.csv")
            table = pd.read_csv(path, comment="#")
            mon = json.loads((ROOT / "web/data" / rid / filename).read_text())
            months = pd.period_range(mon["months"]["first"], mon["months"]["last"], freq="M").astype(str).tolist()
            values = np.asarray(mon["m"]).sum(axis=0); bg = np.asarray(mon["bg"]).sum(axis=0)
            sums, counts = {m: 0.0 for m in months}, {m: 0 for m in months}
            for file in (ROOT / "web/data" / rid / folder).glob("*.json"):
                f = json.loads(file.read_text()); c = f["cols"]
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
                    body = season_path.read_text(); match = re.search(r"# Season .*; total=([\d.]+);", body)
                    exported = float(match.group(1)) if match else float("nan")
                    season_rows = pd.read_csv(io.StringIO(body), comment="#")
                    month_sum = season_rows.loc[season_rows.month.isin(wanted_months), "harmonized_estimate"].sum()
                    check(label+f": Aug {year}أ¢â‚¬â€œFeb {year+1} page and CSV equal seven-month sum", abs(shown-expected_total)<1e-8 and abs(exported-month_sum)<.0004 and len(wanted_months)==7, f"page {shown:.4f}, CSV {exported:.4f}, months {month_sum:.4f}")
            # Whole-region creative features in each unit, without changing their implementations.
            page.evaluate("window.cedrus.selectMonth(window.cedrus.indexOf(2020, 7))")
            page.click("#story-go")
            check(label+": story opens for selected region", page.locator("#story-card").is_visible() and bool(page.inner_text("#story-title")))
            page.click("#story-exit")
            page.evaluate("window.cedrus.selectMonth(window.cedrus.indexOf(2020, 7))")
            before = page.evaluate("window.cedrus.state.sel")
            page.click("#play"); page.wait_for_timeout(350); page.evaluate("window.cedrus.fx.pause()")
            check(label+": playback advances", page.evaluate("window.cedrus.state.sel") != before)
            page.click("#rings-toggle")
            check(label+": tree rings render", page.locator("#rings-svg path").count() > 0)
            page.click("#rings-toggle")
            png = download(page, "#share-card", downloads / f"fingerprint_{rid}_{unit}.png")
            check(label+": fingerprint PNG exports", png.read_bytes().startswith(b"\x89PNG\r\n\x1a\n") and png.stat().st_size > 1000)
        page.screenshot(path=str(shots / f"tier1_{rid}.png"), full_page=True)
    points = [("Beirut",33.8938,35.5018,"lebanon"), ("Damascus",33.5138,36.2765,"syria"),
              ("Homs",34.7324,36.7137,"syria"), ("Amman",31.9539,35.9106,"jordan"),
              ("Nicosia",35.1856,33.3823,"cyprus")]
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
        for name, lat, lon in (("Tel Aviv", 32.0853, 34.7818), ("Mediterranean", 33.5, 33.5)):
            accepted = page.evaluate("o => window.cedrus.useRing(o.ring, 'circle', {lat:o.lat, lon:o.lon, radius:5})",
                                     dict(ring=ring_for(lat, lon), lat=lat, lon=lon))
            # Tel Aviv's circle touches Jordan's box but no Jordan grid cell: refused, and the toast explains that
            # instead of listing Jordan among "regions we cover". The open-sea circle touches no box at all.
            expected = "No fire records from Jordan fall inside this area" if name == "Tel Aviv" else "Outside the regions we cover"
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
            check(prefix+": absent-cell fixture exists", absent is not None)
            if absent is not None:
                page.evaluate("p => window.cedrus.state.map.fire('click', {lngLat:{lng:p.lon,lat:p.lat}})", absent)
                detail = page.inner_text("#map-cell-detail")
                check(prefix+": gap is not described as observed zero fires", "Not included in" in detail and "no qualifying fire records" in detail and "No cell estimate" in detail and "Observation completeness unknown" in detail)
                check(prefix+": gap has a separate shaded dashed layer", page.evaluate("window.cedrus.state.map.getPaintProperty('absent-cells', 'fill-opacity') > 0 && window.cedrus.state.map.getPaintProperty('absent-cells-line', 'line-dasharray').length > 0"))
            page.evaluate("window.cedrus.selectMonth(window.cedrus.indexOf(2020, 7))")
            check(prefix+": changing month clears stale inspection", page.locator(".maplibregl-popup").count()==0 and page.inner_text("#map-cell-detail").startswith("Click the map"))
        if rid == "syria":
            page.locator("#map-panel").scroll_into_view_if_needed()
            page.screenshot(path=str(shots / "map_clarity_syria.png"), full_page=True)
    ctx.close()
