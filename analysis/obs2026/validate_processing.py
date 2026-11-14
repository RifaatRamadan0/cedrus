"""Tests for the two new 2026 processing steps, exactly as fixed in docs/OBS2026_VALIDATION_PLAN.md.

    python analysis/obs2026/validate_processing.py

Step 1 (country clipping): 2025 area-API standard data, clipped to the Natural Earth outline, against the 2025
FIRMS country files. Step 2 (static-source mask): Jan-Jul 2026 standard area data, masked as if it had no
`type`, against its real `type`. Writes results.json and REPORT.md next to this file. Reads only; no export,
model or catalog file is touched.
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from regions import REGIONS  # noqa: E402
from outline import edge_km, inside, load_countries, which_country  # noqa: E402

AREA = ROOT / "data/raw/area_api"
ISO = {"portugal": "PRT", "lebanon": "LBN", "syria": "SYR", "la_rioja": "ARG"}
RAW = {"portugal": "portugal", "lebanon": "lebanon", "syria": "syria", "la_rioja": "la_rioja"}
SENSORS = {"modis": "MODIS_SP", "snpp": "VIIRS_SNPP_SP", "noaa20": "VIIRS_NOAA20_SP"}
STEMS = {"modis": "modis", "snpp": "viirs-snpp", "noaa20": "viirs-jpss1"}
FINE = 0.01
# Thresholds, fixed in the plan before any validation data was downloaded.
C1, C2, C3, BORDER_KM, MIN_MONTH = 0.02, 0.05, 0.01, 10.0, 20
M1, M2, M3 = 0.95, 0.01, 0.05


# ---------- geometry: pipeline/outline.py (the same code the 2026 build uses) ----------


# ---------- records ----------
def tidy(df, sensor, box):
    """The pipeline's own filters (pipeline/bakeoff/data.py _read), keeping `type` for the mask test."""
    lon0, lat0, lon1, lat1 = box
    df = df[(df.longitude >= lon0) & (df.longitude < lon1) & (df.latitude >= lat0) & (df.latitude < lat1)].copy()
    if sensor == "modis":
        df = df[pd.to_numeric(df.confidence, errors="coerce") >= 30]
    else:
        df = df[df.confidence.astype(str).str.lower().str[0].isin(["n", "h"])]
    df = df[df.daynight.astype(str).str.upper().str[0].isin(["D", "N"])]
    df["key"] = (df.latitude.round(4).map("{:.4f}".format) + "," + df.longitude.round(4).map("{:.4f}".format) + ","
                 + df.acq_date.astype(str) + "," + pd.to_numeric(df.acq_time).astype(int).astype(str))
    df["ym"] = df.acq_date.astype(str).str[:7]
    return df.drop_duplicates("key")


def area_months(region, sensor, first, last):
    parts = []
    for ym in pd.period_range(first, last, freq="M").astype(str):
        path = AREA / region / f"{SENSORS[sensor]}_{ym}.csv"
        if not path.exists():
            raise SystemExit(f"missing {path}; run pipeline/01c_download_area_months.py first")
        parts.append(pd.read_csv(path, dtype={"acq_time": str}, low_memory=False))
    return pd.concat(parts, ignore_index=True)


def country_file(region, sensor, year):
    cfg = REGIONS[region]
    path = ROOT / "data/raw" / RAW[region] / f"{STEMS[sensor]}_{year}_{cfg['country']}.csv"
    return pd.read_csv(path, dtype={"acq_time": str}, low_memory=False)


def cell_of(lon, lat):
    return np.floor(np.asarray(lon) / 0.25).astype(int).astype(str) + "_" + np.floor(np.asarray(lat) / 0.25).astype(int).astype(str)


# ---------- step 1 ----------
def clipping(region, sensor, countries, year=2025, keep=None):
    """keep(df) -> bool array decides which area-API detections are the region's; default: the outline alone."""
    box, rings = REGIONS[region]["box"], countries[ISO[region]]["rings"]
    arc = tidy(country_file(region, sensor, year), sensor, box)
    arc = arc[arc["type"] == 0]
    api = tidy(area_months(region, sensor, f"{year}-01", f"{year}-12"), sensor, box)
    api = api[api["type"] == 0]
    api["kept"] = keep(api) if keep else inside(rings, api.longitude.to_numpy(), api.latitude.to_numpy())
    arc_keys, api_keys = set(arc.key), set(api.key)
    kept = api[api.kept]
    extra = kept[~kept.key.isin(arc_keys)].copy()
    extra["km"] = edge_km(rings, extra.longitude.to_numpy(), extra.latitude.to_numpy())
    false_incl = extra[extra.km <= BORDER_KM]
    inner_diff = extra[extra.km > BORDER_KM]
    dropped = api[~api.kept & api.key.isin(arc_keys)].copy()
    missing = arc[~arc.key.isin(api_keys)]
    n = len(arc)
    monthly = pd.DataFrame({"country_file": arc.groupby("ym").size(), "clipped_api": kept.groupby("ym").size()}).fillna(0)
    monthly["diff_share"] = (monthly.clipped_api - monthly.country_file) / monthly.country_file.where(monthly.country_file > 0)
    scored = monthly[monthly.country_file >= MIN_MONTH]
    worst = float(scored.diff_share.abs().max()) if len(scored) else 0.0
    report = {
        "country_file": n, "api_in_box": len(api), "api_kept": int(api.kept.sum()),
        "false_inclusions": len(false_incl), "false_exclusions": len(dropped),
        "source_missing_from_api": len(missing), "source_extra_inside": len(inner_diff),
        "c1_share": (len(false_incl) + len(dropped)) / n if n else 0.0,
        "c3_share": (len(missing) + len(inner_diff)) / n if n else 0.0,
        "c2_worst_month": worst, "c2_months_scored": int(len(scored)),
        "monthly": {m: {"country_file": int(r.country_file), "clipped_api": int(r.clipped_api)} for m, r in monthly.iterrows()},
    }
    report["c1_pass"] = report["c1_share"] <= C1
    report["c2_pass"] = worst <= C2
    report["c3_pass"] = report["c3_share"] <= C3
    if len(false_incl):
        report["false_inclusions_in"] = pd.Series(which_country(countries, false_incl.longitude.to_numpy(),
                                                                false_incl.latitude.to_numpy())).value_counts().to_dict()
        report["false_inclusion_km"] = [round(float(x), 2) for x in np.percentile(false_incl.km, [50, 90, 100])]
    if len(dropped):
        report["false_exclusions_in"] = pd.Series(which_country(countries, dropped.longitude.to_numpy(),
                                                                dropped.latitude.to_numpy())).value_counts().to_dict()
        dropped["km"] = edge_km(rings, dropped.longitude.to_numpy(), dropped.latitude.to_numpy())
        report["false_exclusion_km"] = [round(float(x), 2) for x in np.percentile(dropped.km, [50, 90, 100])]
    mism = pd.concat([false_incl.assign(kind="incl"), dropped.assign(kind="excl")])
    if len(mism):
        cells = pd.Series(cell_of(mism.longitude, mism.latitude)).value_counts()
        report["mismatch_cells_top"] = cells.head(8).to_dict()
        report["mismatch_cells"] = int(len(cells))
    return report


# ---------- step 2 ----------
def mask_for(region, box):
    fine = set()
    for sensor in STEMS:
        for year in range(2012, 2026):
            try:
                df = country_file(region, sensor, year)
            except FileNotFoundError:
                continue
            lon0, lat0, lon1, lat1 = box
            df = df[(df.longitude >= lon0) & (df.longitude < lon1) & (df.latitude >= lat0) & (df.latitude < lat1)]
            bad = df[df["type"] != 0]
            fine.update(zip(np.floor(bad.longitude / FINE).astype(int), np.floor(bad.latitude / FINE).astype(int)))
    return fine


def masked(df, fine, neighbours):
    fx, fy = np.floor(df.longitude / FINE).astype(int).to_numpy(), np.floor(df.latitude / FINE).astype(int).to_numpy()
    offsets = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1)] if neighbours else [(0, 0)]
    return np.array([any((x + dx, y + dy) in fine for dx, dy in offsets) for x, y in zip(fx, fy)], dtype=bool)


def mask_test(region, sensor, countries, fine):
    box, rings = REGIONS[region]["box"], countries[ISO[region]]["rings"]
    df = tidy(area_months(region, sensor, "2026-01", "2026-07"), sensor, box)
    df = df[inside(rings, df.longitude.to_numpy(), df.latitude.to_numpy())]
    static = df["type"] != 0
    out = {"detections": len(df), "type_1_3": int(static.sum()), "type_0": int((~static).sum())}
    for label, nb in (("primary_3x3", True), ("sensitivity_1x1", False)):
        hit = masked(df, fine, nb)
        recall = float((hit & static).sum() / static.sum()) if static.sum() else 1.0
        false_removal = float((hit & ~static).sum() / (~static).sum()) if (~static).sum() else 0.0
        by = pd.DataFrame({"ym": df.ym, "truth": ~static, "kept": ~hit})
        monthly = by.groupby("ym").agg(type0=("truth", "sum"), masked_count=("kept", "sum"))
        scored = monthly[monthly.type0 >= MIN_MONTH]
        worst = float(((scored.masked_count - scored.type0) / scored.type0).abs().max()) if len(scored) else 0.0
        res = {"recall": recall, "false_removal": false_removal, "m3_worst_month": worst,
               "m3_months_scored": int(len(scored)),
               "static_left_in": int((~hit & static).sum()), "type0_removed": int((hit & ~static).sum()),
               "monthly": {m: {"type0": int(r.type0), "masked_count": int(r.masked_count)} for m, r in monthly.iterrows()}}
        res.update({"m1_pass": recall >= M1, "m2_pass": false_removal <= M2, "m3_pass": worst <= M3})
        out[label] = res
    return out


def pct(x):
    return f"{100 * x:.2f}%"


def main():
    countries = load_countries()
    results = {"plan": "docs/OBS2026_VALIDATION_PLAN.md", "thresholds": {"C1": C1, "C2": C2, "C3": C3, "M1": M1, "M2": M2, "M3": M3},
               "clipping": {}, "mask": {}}
    for region in ISO:
        results["clipping"][region] = {}
        for sensor in SENSORS:
            print(f"clipping {region} {sensor}", flush=True)
            results["clipping"][region][sensor] = clipping(region, sensor, countries)
        fine = mask_for(region, REGIONS[region]["box"])
        results["mask"][region] = {"mask_squares": len(fine)}
        for sensor in SENSORS:
            print(f"mask {region} {sensor}", flush=True)
            results["mask"][region][sensor] = mask_test(region, sensor, countries, fine)
    clip_ok = all(r[k] for reg in results["clipping"].values() for r in reg.values() for k in ("c1_pass", "c2_pass", "c3_pass"))
    mask_ok = all(s["primary_3x3"][k] for reg in results["mask"].values() for name, s in reg.items() if name in SENSORS
                  for k in ("m1_pass", "m2_pass", "m3_pass"))
    results["clipping_pass"], results["mask_pass"] = clip_ok, mask_ok
    (HERE / "results.json").write_text(json.dumps(results, indent=2, default=float) + "\n", encoding="utf-8", newline="\n")

    lines = ["# 2026 processing validation", "", f"Rules: [plan](../../docs/OBS2026_VALIDATION_PLAN.md). Clipping: **{'PASS' if clip_ok else 'FAIL'}**. "
             f"Mask: **{'PASS' if mask_ok else 'FAIL'}**.", "", "## Step 1: country clipping (2025)", "",
             "| Region | Sensor | Country file | False incl. | False excl. | C1 | Worst month (C2) | Source diff. (C3) | Pass |",
             "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for region, reg in results["clipping"].items():
        for sensor, r in reg.items():
            ok = r["c1_pass"] and r["c2_pass"] and r["c3_pass"]
            lines.append(f"| {region} | {sensor} | {r['country_file']:,} | {r['false_inclusions']:,} | {r['false_exclusions']:,} | "
                         f"{pct(r['c1_share'])} | {pct(r['c2_worst_month'])} | {pct(r['c3_share'])} | {'yes' if ok else '**no**'} |")
    lines += ["", "## Step 2: static-source mask (Jan–Jul 2026, primary 3×3 rule)", "",
              "| Region | Sensor | Type 1–3 | Type 0 | Removed static (M1) | Removed type 0 (M2) | Worst month (M3) | Pass | 1×1 recall / false removal |",
              "|---|---|---:|---:|---:|---:|---:|---|---|"]
    for region, reg in results["mask"].items():
        for sensor in SENSORS:
            s = reg[sensor]; p = s["primary_3x3"]; q = s["sensitivity_1x1"]
            ok = p["m1_pass"] and p["m2_pass"] and p["m3_pass"]
            lines.append(f"| {region} | {sensor} | {s['type_1_3']:,} | {s['type_0']:,} | {pct(p['recall'])} | {pct(p['false_removal'])} | "
                         f"{pct(p['m3_worst_month'])} | {'yes' if ok else '**no**'} | {pct(q['recall'])} / {pct(q['false_removal'])} |")
    (HERE / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
