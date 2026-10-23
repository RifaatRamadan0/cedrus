"""Turn the processed record into the files the website reads.

    python pipeline/04_export_web.py

Writes web/data/<country>.json (yearly record, fire calendar, latest-year
comparison, test results, provenance) and web/data/<country>-cells.geojson
(one square per grid cell with its corrected yearly detections).
"""
import argparse
import json
from datetime import date, timedelta

import numpy as np
import pandas as pd

from common import ROOT, cell_bounds

VIIRS_FROM = 2012  # the joined record switches to Suomi NPP from this year


def doy_label(doy):
    d = date(2001, 1, 1) + timedelta(days=int(round(doy)) - 1)
    return f"{d:%b} {d.day}"


def season(series):
    c = series.cumsum()
    if c.iloc[-1] <= 0:
        return None
    frac = c / c.iloc[-1]
    return [int(frac.index[np.argmax(frac.values >= q)].dayofyear) for q in (.1, .5, .9)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", default="Portugal")
    args = ap.parse_args()
    key = args.country.lower()
    proc = ROOT / "data" / "processed" / key
    daily = pd.read_csv(proc / "daily_cells.csv")
    results = json.loads((proc / "results.json").read_text())
    ratios = pd.read_csv(proc / "ratios.csv").set_index(["cell", "moy"]).r
    month_ratio = {int(k): v for k, v in results["month_ratio"].items()}
    manifest = json.loads((ROOT / "data" / "raw" / key / "manifest.json").read_text())

    d = daily.assign(dt=pd.to_datetime(daily.date))
    d["year"], d["moy"] = d.dt.dt.year, d.dt.dt.month
    modis = d[d.sensor.isin(["terra", "aqua"])]
    snpp = d[d.sensor == "snpp"].copy()
    idx = pd.MultiIndex.from_arrays([snpp.cell, snpp.moy])
    r = pd.Series(ratios.reindex(idx).values, index=snpp.index).fillna(snpp.moy.map(month_ratio))
    snpp["corrected"] = snpp["count"] * r

    last_year = int(d.year.max())
    years = list(range(2001, last_year + 1))  # 2000 has only Nov-Dec (Terra start)
    m_year = modis.groupby("year")["count"].sum()
    v_year = snpp.groupby("year")["count"].sum()
    c_year = snpp.groupby("year")["corrected"].sum()
    record = {
        "years": years,
        "modis": [int(m_year.get(y, 0)) for y in years],
        "viirs": [int(v_year.get(y, 0)) if y >= VIIRS_FROM else None for y in years],
        "combined": [int(m_year.get(y, 0)) if y < VIIRS_FROM else int(v_year.get(y, 0)) for y in years],
        "corrected": [int(m_year.get(y, 0)) if y < VIIRS_FROM else int(round(c_year.get(y, 0))) for y in years],
    }

    # Fire calendar from the corrected daily national record: MODIS before 2012, corrected VIIRS after.
    nat = pd.concat([
        modis[modis.year < VIIRS_FROM].groupby("dt")["count"].sum(),
        snpp[snpp.year >= VIIRS_FROM].groupby("dt")["corrected"].sum(),
    ])
    full_years = [y for y in years if y < last_year or d[d.year == y].dt.max().month == 12]
    dates = {}
    for y in full_years:
        s = nat[nat.index.year == y].reindex(pd.date_range(f"{y}-01-01", f"{y}-12-31"), fill_value=0)
        sd = season(s)
        if sd:
            dates[y] = sd
    arr = np.array(list(dates.values()))
    med = np.median(arr, axis=0)
    spread = (np.percentile(arr, 75, axis=0) - np.percentile(arr, 25, axis=0)) / 2
    calendar = {
        "basis": f"{min(dates)}-{max(dates)}, corrected record",
        "start": {"doy": float(med[0]), "label": doy_label(med[0]), "spread_days": int(round(spread[0]))},
        "peak": {"doy": float(med[1]), "label": doy_label(med[1]), "spread_days": int(round(spread[1]))},
        "end": {"doy": float(med[2]), "label": doy_label(med[2]), "spread_days": int(round(spread[2]))},
        "per_year": {int(y): v for y, v in dates.items()},
    }

    # Latest full year against the years before it.
    latest = max(dates)
    prior = [y for y in dates if y < latest]
    totals = {y: float(nat[nat.index.year == y].sum()) for y in dates}
    lo, hi = np.percentile([totals[y] for y in prior], [10, 90])
    middle_shift = dates[latest][1] - float(np.median([dates[y][1] for y in prior]))
    status = "above" if totals[latest] > hi else "below" if totals[latest] < lo else "within"
    comparison = {
        "year": latest, "total": round(totals[latest]), "normal_range": [round(lo), round(hi)],
        "status": status, "middle_shift_days": round(middle_shift),
    }

    # Map cells: corrected detections per year per cell.
    per_cell = pd.concat([
        modis[modis.year < VIIRS_FROM].groupby(["cell", "year"])["count"].sum(),
        snpp[snpp.year >= VIIRS_FROM].groupby(["cell", "year"])["corrected"].sum(),
    ])
    features = []
    for cell, s in per_cell.groupby(level=0):
        lon0, lat0, lon1, lat1 = cell_bounds(cell)
        by_year = {int(y): round(float(v), 1) for (_, y), v in s.items()}
        features.append({"type": "Feature", "properties": {"cell": int(cell), "y": [by_year.get(y, 0) for y in years]},
                         "geometry": {"type": "Polygon", "coordinates": [[[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]]}})

    out = ROOT / "web" / "data"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{key}-cells.geojson").write_text(json.dumps({"type": "FeatureCollection", "years": years, "features": features}))
    payload = {
        "region": args.country, "record": record, "calendar": calendar, "comparison": comparison,
        "test": {k: results[k] for k in ("passed", "primary_wape", "season_date_error_days", "train", "test", "k",
                                          "yearly_total_error_pct", "handover_noaa20")},
        "provenance": {
            "source": "NASA FIRMS country archive (standard products)",
            "files": [{"name": n, **{k: m[k] for k in ("url", "sensor", "rows", "sha256", "retrieved")}}
                      for n, m in sorted(manifest.items())],
            "filters": "mainland box, vegetation fires only (type 0), MODIS confidence >= 30, VIIRS nominal/high",
            "unit": "fire detections (satellite pixels flagged as burning), not burned area",
            "method": "VIIRS (Suomi NPP) scaled to MODIS-equivalent with a ratio per 0.25 deg cell and calendar month, "
                      "fitted 2012-2019; see docs/TEST_PLAN.md",
        },
        "limitations": [
            "Corrected values after 2012 are MODIS-equivalent estimates, not observations.",
            "Ratios were fitted on 2012-2019; Terra and Aqua drifted after that.",
            "Detections are not burned area: one large fire produces many detections.",
        ],
    }
    (out / f"{key}.json").write_text(json.dumps(payload, indent=1))
    print(f"-> {out / (key + '.json')}  calendar {calendar['start']['label']} / {calendar['peak']['label']} / "
          f"{calendar['end']['label']}, {latest}: {status} normal")


if __name__ == "__main__":
    main()
