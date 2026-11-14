"""Per-region forward test of the frozen models: fit 2012-02..2019-12, score against MODIS 2020-01..2021-12.

Same protocol and pass rules as analysis/tier1/la_rioja_evidence/run_validation.py, run once per region on that
region's own data. The rules below were fixed before this script was first run (10 Nov 2026); results are kept
whatever they show. Nothing is tuned and no repository model code is changed (checked by source hashes).

These regions were development regions: their 2012-2019 data helped choose the model. Their 2020+ MODIS was not
used in fitting, tuning or model choice (docs/TOURNAMENT_RESULTS.md, leakage test), so 2020-2021 is a forward test
in time, not an out-of-region test.

Usage: python analysis/tier1/region_evidence/run_validation.py syria jordan cyprus [--work DIR]
Bulky row-level CSVs go to --work (default: <this folder>/_work, not committed); results.json and REPORT.md go to
<this folder>/<region>/.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))


def hashes():
    return {str(p.relative_to(REPO)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted((REPO / "pipeline").rglob("*.py"))}


before = hashes()
import numpy as np
import pandas as pd
import scipy
from pipeline.regions import REGIONS
from pipeline.round2 import data as r2
from pipeline.round2 import confirm as c2
from pipeline.round2.validate import swap_summary
from pipeline.round3 import data as d3
from pipeline.round3 import confirm as c3

ap = argparse.ArgumentParser()
ap.add_argument("regions", nargs="+")
ap.add_argument("--work", type=Path, default=HERE / "_work")
args = ap.parse_args()

fz3, sha3 = d3.load_frozen()
frozen2 = REPO / "data/processed/round2/frozen.json"
sha2 = hashlib.sha256(frozen2.read_bytes()).hexdigest()
assert sha2 == "bedc56d5ba85b851931cd6912dfcab832dc38b26a8fe80712a72974cf46e0686", sha2
fz2 = json.loads(frozen2.read_text(encoding="utf-8"))


def pct(x):
    return f"{100*x:.1f}%"


def run(region):
    assert region in REGIONS and "sealed" not in REGIONS[region]["roles"], region
    out = HERE / region
    work = args.work / region
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    d3.OUT = work / "cache"  # keep the pixel cache out of data/processed

    folder = r2.folder(region)
    manifest = json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
    for name, meta in manifest.items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == meta["sha256"], name
    avail = r2.availability(region, 2025)
    assert not d3.complete(avail), d3.complete(avail)
    print(f"[{region}] source files and both frozen settings verified.", flush=True)

    px = d3.pixels(region)
    R, coverage = d3.rows(region, px)
    print(f"[{region}] {len(px):,} filtered detections; {coverage['cells']} training-footprint cells.", flush=True)

    use_ms = {(region, y) for y in range(2012, 2026)}
    use_sn = {(region, y) for y in range(2018, 2026)}
    outages = {}
    for label, sensor, other, first, usable in [
        ("modis", "modis", "snpp", "2012-02-01", use_ms),
        ("snpp", "snpp", "modis", "2012-02-01", use_ms),
        ("snpp_vs_noaa20", "snpp", "noaa20", "2020-01-01", use_sn),
        ("noaa20", "noaa20", "snpp", "2020-01-01", use_sn),
    ]:
        outages[label] = r2.outage_days(px, first, "2025-12-31", sensor, other, usable=usable)
    bad1 = sorted({day[:7] for label in ["modis", "snpp"] for day in outages[label]})
    bad2 = sorted({day[:7] for label in ["snpp_vs_noaa20", "noaa20"] for day in outages[label]})

    result = {
        "kind": "Per-region forward test of the frozen models (development region), not a sealed confirmation",
        "region": region, "country_file": REGIONS[region]["country"],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "box": list(REGIONS[region]["box"]),
        "fit": ["2012-02", "2019-12"], "accuracy_test": ["2020-01", "2021-12"],
        "satellite_swap_test": ["2020-01", "2025-12"],
        "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__,
                     "scipy": scipy.__version__},
        "frozen_sha256": {"burning_days": sha3, "hotspots": sha2},
        "source_manifest_sha256": hashlib.sha256((folder / "manifest.json").read_bytes()).hexdigest(),
        "source_code_sha256": before, "training_footprint": coverage,
        "outage_days": outages, "accuracy_excluded_months": bad1, "swap_excluded_months": bad2,
        "units": {},
    }
    for unit in ["burning_days", "hotspots"]:
        print(f"[{region}] testing {unit}...", flush=True)
        uwork = work / unit
        uwork.mkdir(exist_ok=True)
        if unit == "burning_days":
            T = d3.burning_days(R)
            t1, model, seam, info = c3.test1(fz3, T, avail, bad1)
            t2, swap_info = c3.test2(T, avail, bad2, model)
            summary = c3.summary1(t1)
        else:
            T = c2.prepare(R)
            t1, model, seam, info = c2.test1(fz2, T, avail, bad1)
            t2, swap_info = c2.test2(fz2, T, avail, bad2, model)
            summary = c2.summary1(t1)
        verdict = c2.verdict1(summary, "D-a" if unit == "burning_days" else "A2")
        swap = swap_summary(t2)
        swap_pass = bool(swap["counted"] > 0 and swap["share"] >= .80)
        monthly = t1.groupby("ym")[["Y", "V", "mean_M", "mean_F0", "mean_F1"]].sum()
        monthly.to_csv(out / f"{unit}_accuracy_monthly.csv")
        seam.to_csv(out / f"{unit}_accuracy_yearly.csv", index=False)
        t1.to_csv(uwork / "accuracy_rows.csv", index=False)
        t2.to_csv(uwork / "satellite_swap_monthly.csv", index=False)
        item = {"accuracy": summary, "accuracy_verdict": verdict, "swap": swap, "swap_pass": swap_pass,
                "all_checks_pass": bool(verdict["pass"] and swap_pass), "fit_info": info, "swap_fit_info": swap_info,
                "accuracy_months_scored": monthly.index.tolist(), "by_year": seam.to_dict("records")}
        if any("2020-01" <= m <= "2021-12" for m in bad1):
            # Sensitivity only; the primary result keeps the outage rule.
            if unit == "burning_days":
                full, _, _, _ = c3.test1(fz3, T, avail, [])
                item["sensitivity_no_outage_exclusion"] = c3.summary1(full)
            else:
                full, _, _, _ = c2.test1(fz2, T, avail, [])
                item["sensitivity_no_outage_exclusion"] = c2.summary1(full)
        result["units"][unit] = item
        print(json.dumps({"region": region, "unit": unit, "accuracy": summary, "verdict": verdict, "swap": swap},
                         default=float), flush=True)

    (out / "results.json").write_text(json.dumps(result, indent=2, default=float), encoding="utf-8")
    U = result["units"]
    lines = [f"# {region} forward test", "",
             "Per-region forward test of the frozen models; not a sealed confirmation.", "",
             "Fit: February 2012–December 2019. Accuracy: January 2020–December 2021 against MODIS.",
             "Satellite comparison: January 2020–December 2025. Frozen settings and existing test functions reused.", "",
             "| Check | Burning days | Hotspots |", "|---|---|---|"]
    for label, key in [("Cell-month error (WAPE)", "wape_cm_M"), ("Simple conversion cell-month error", "wape_cm_F1"),
                       ("Raw VIIRS cell-month error", "wape_cm_F0"), ("Region-month error (WAPE)", "wape_nm_M"),
                       ("Simple conversion region-month error", "wape_nm_F1"), ("80% interval coverage", "cov_active_M")]:
        lines.append(f"| {label} | " + " | ".join(pct(U[u]["accuracy"][key]) for u in U) + " |")
    lines.append("| Total bias | " + " | ".join(f"{100*(U[u]['accuracy']['total_ratio_M']-1):+.1f}%" for u in U) + " |")
    lines.append("| Satellite interval agreement | " + " | ".join(pct(U[u]["swap"]["share"]) for u in U) + " |")
    lines.append("| All existing checks | " + " | ".join("PASS" if U[u]["all_checks_pass"] else "FAIL" for u in U) + " |")
    lines += ["", "## Interpretation limits", "",
              "- This was a development region: its 2012–2019 data helped choose the model. Its 2020–2021 MODIS was not used, so this is a forward test in time, not a test on an unseen region.",
              "- The analysis box is a rectangle, not the country boundary.",
              "- Accuracy is scored only in cells seen during the training period, as in the existing runner.",
              "- MODIS after 2021 is not treated as reliable ground truth (Aqua orbital drift from 2022). The 2022–2025 comparison checks agreement between VIIRS satellites, not true fire counts.",
              f"- Months excluded from the accuracy window by the existing outage rule: {[m for m in bad1 if '2020-01' <= m <= '2021-12']}.",
              "- No model settings were tuned and no repository model code was changed."]
    (out / "REPORT.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[{region}] finished: {out / 'REPORT.md'}", flush=True)


for region in args.regions:
    run(region)
assert hashes() == before, "Repository model source changed during test"
print("Repository model source unchanged.", flush=True)
