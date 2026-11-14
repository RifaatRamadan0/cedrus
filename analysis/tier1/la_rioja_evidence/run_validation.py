"""Isolated La Rioja diagnostic; reuses repository models without modifying them."""
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPO = Path(r"C:\Users\rifaa\Desktop\NASA Space Apps\cedrus")
sys.path.insert(0, str(REPO))
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)

def hashes():
    return {str(p.relative_to(REPO)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in (REPO / "pipeline").rglob("*.py")}

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

# Runtime-only configuration: neither region definitions nor model code are edited.
REGIONS["la_rioja"] = {"country": "Argentina", "box": (-69.7, -32.8, -65.4, -27.7), "roles": {"dev"}}
r2.folder = lambda region: ROOT / "data/raw/la_rioja"
d3.OUT = OUT / "cache"

manifest = json.loads((r2.folder("la_rioja") / "manifest.json").read_text())
for name, meta in manifest.items():
    assert hashlib.sha256((r2.folder("la_rioja") / name).read_bytes()).hexdigest() == meta["sha256"], name
avail = r2.availability("la_rioja", 2025)
assert not d3.complete(avail), d3.complete(avail)
fz3, sha3 = d3.load_frozen()
frozen2 = REPO / "data/processed/round2/frozen.json"
sha2 = hashlib.sha256(frozen2.read_bytes()).hexdigest()
assert sha2 == "bedc56d5ba85b851931cd6912dfcab832dc38b26a8fe80712a72974cf46e0686"
fz2 = json.loads(frozen2.read_text())
print("Source files and both frozen settings verified.", flush=True)
px = d3.pixels("la_rioja")
R, coverage = d3.rows("la_rioja", px)
print(f"Loaded {len(px):,} filtered detections; {coverage['cells']} training-footprint cells.", flush=True)

use_ms = {("la_rioja", y) for y in range(2012, 2026)}
use_sn = {("la_rioja", y) for y in range(2018, 2026)}
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
    "kind": "Exploratory La Rioja diagnostic, not a sealed confirmation",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "box": list(REGIONS["la_rioja"]["box"]),
    "fit": ["2012-02", "2019-12"], "accuracy_test": ["2020-01", "2021-12"],
    "satellite_swap_test": ["2020-01", "2025-12"],
    "versions": {"python": platform.python_version(), "numpy": np.__version__, "pandas": pd.__version__, "scipy": scipy.__version__},
    "frozen_sha256": {"burning_days": sha3, "hotspots": sha2},
    "source_manifest_sha256": hashlib.sha256((r2.folder("la_rioja") / "manifest.json").read_bytes()).hexdigest(),
    "source_code_sha256": before, "training_footprint": coverage,
    "outage_days": outages, "accuracy_excluded_months": bad1, "swap_excluded_months": bad2,
    "units": {},
}
for unit in ["burning_days", "hotspots"]:
    print(f"Testing {unit}...", flush=True)
    folder = OUT / unit
    folder.mkdir(exist_ok=True)
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
    monthly.to_csv(folder / "accuracy_monthly.csv")
    t1.to_csv(folder / "accuracy_rows.csv", index=False)
    t2.to_csv(folder / "satellite_swap_monthly.csv", index=False)
    seam.to_csv(folder / "accuracy_yearly.csv", index=False)
    item = {"accuracy": summary, "accuracy_verdict": verdict, "swap": swap, "swap_pass": swap_pass,
            "all_checks_pass": bool(verdict["pass"] and swap_pass), "fit_info": info, "swap_fit_info": swap_info,
            "accuracy_months_scored": monthly.index.tolist(), "by_year": seam.to_dict("records")}
    if any("2020-01" <= m <= "2021-12" for m in bad1):
        # Sensitivity only; no tuning or change to primary criteria.
        if unit == "burning_days":
            full, _, _, _ = c3.test1(fz3, T, avail, [])
            item["sensitivity_no_outage_exclusion"] = c3.summary1(full)
        else:
            full, _, _, _ = c2.test1(fz2, T, avail, [])
            item["sensitivity_no_outage_exclusion"] = c2.summary1(full)
    result["units"][unit] = item
    print(json.dumps({"unit": unit, **item}, default=float), flush=True)

assert hashes() == before, "Repository model source changed during test"
result["repository_model_source_unchanged"] = True
(OUT / "results.json").write_text(json.dumps(result, indent=2, default=float), encoding="utf-8")
lines = ["# La Rioja model diagnostic", "", "Exploratory test; not a new sealed confirmation.", "",
         "Fit: February 2012–December 2019. Accuracy: January 2020–December 2021.",
         "Satellite comparison: January 2020–December 2025. Frozen settings and existing test functions reused.", "",
         "| Check | Burning days | Hotspots |", "|---|---|---|"]
def pct(x):
    return f"{100*x:.1f}%"
for label, key in [("Cell-month error (WAPE)", "wape_cm_M"), ("Simple conversion cell-month error", "wape_cm_F1"),
                   ("Raw VIIRS cell-month error", "wape_cm_F0"), ("Region-month error (WAPE)", "wape_nm_M"),
                   ("Simple conversion region-month error", "wape_nm_F1"), ("80% interval coverage", "cov_active_M")]:
    lines.append(f"| {label} | " + " | ".join(pct(result["units"][u]["accuracy"][key]) for u in result["units"]) + " |")
lines.append("| Total bias | " + " | ".join(f"{100*(result['units'][u]['accuracy']['total_ratio_M']-1):+.1f}%" for u in result["units"]) + " |")
lines.append("| Satellite interval agreement | " + " | ".join(pct(result["units"][u]["swap"]["share"]) for u in result["units"]) + " |")
lines.append("| All existing checks | " + " | ".join("PASS" if result["units"][u]["all_checks_pass"] else "FAIL" for u in result["units"]) + " |")
lines += ["", "## Interpretation limits", "",
          "- The box includes parts of neighbouring provinces; it is not the exact provincial boundary.",
          "- Accuracy is scored only in cells seen during the training period, as in the existing runner. New cells are not validated by that score.",
          "- Day and night are separate burning-day observations. Values do not measure burned area or distinct incidents.",
          "- MODIS after 2021 is not treated as reliable ground truth. The 2022–2025 comparison checks agreement between VIIRS satellites, not true fire counts.",
          "- Satellite agreement means overlapping uncertainty intervals, not equal point estimates.",
          f"- Existing outage rule excludes these accuracy-window months: {[m for m in bad1 if '2020-01' <= m <= '2021-12']}. Sensitivity results are in results.json where applicable.",
          "- Frozen checksums, dependencies, source hashes, exclusions, yearly totals, and test verdicts are recorded in results.json.",
          "- No model settings were tuned, and no application or repository source files were changed."]
(OUT / "REPORT.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
print(f"Finished. Report: {OUT / 'REPORT.md'}", flush=True)
