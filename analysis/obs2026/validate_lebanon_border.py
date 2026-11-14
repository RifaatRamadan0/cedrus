"""Test of the Lebanon border correction (docs/OBS2026_VALIDATION_PLAN.md, addendum of 11 Nov 2026).

    python analysis/obs2026/validate_lebanon_border.py

Decisive: 2024 (never seen while the rule was written), reference from every other country-file year.
Reported only: 2025 (the year the rule was designed on), reference without 2025; and 2024 with the outline alone.
Same metrics and unchanged thresholds as the clipping test (validate_processing.py).
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "pipeline"))
import border_rule  # noqa: E402
import validate_processing as v  # noqa: E402
from outline import load_countries  # noqa: E402

SENSORS = ("modis", "snpp", "noaa20")


def run(year, corrected):
    countries = load_countries()
    rings = countries["LBN"]["rings"]
    ref = border_rule.reference("lebanon", [y for y in range(2000, 2026) if y != year])
    keep = (lambda df: border_rule.keep("lebanon", rings, ref, df.longitude.to_numpy(), df.latitude.to_numpy())) if corrected else None
    return {s: v.clipping("lebanon", s, countries, year=year, keep=keep) for s in SENSORS}


def passed(res):
    return all(r["c1_pass"] and r["c2_pass"] and r["c3_pass"] for r in res.values())


def main():
    out = {"rule": {"edge_km": border_rule.EDGE_KM, "radius_km": border_rule.RADIUS_KM},
           "decisive_2024_corrected": run(2024, True),
           "reported_2024_outline_only": run(2024, False),
           "reported_2025_corrected": run(2025, True)}
    out["pass"] = passed(out["decisive_2024_corrected"])
    (HERE / "results_lebanon_border.json").write_text(json.dumps(out, indent=2, default=float) + "\n", encoding="utf-8", newline="\n")
    lines = ["# Lebanon border correction test", "", f"Decisive test (2024, corrected): **{'PASS' if out['pass'] else 'FAIL'}**.", "",
             "| Run | Sensor | Country file | False incl. | False excl. | C1 | Worst month (C2) | C3 | Pass |",
             "|---|---|---:|---:|---:|---:|---:|---:|---|"]
    for label, key in (("2024 corrected (decisive)", "decisive_2024_corrected"), ("2024 outline only", "reported_2024_outline_only"),
                       ("2025 corrected (design year)", "reported_2025_corrected")):
        for s, r in out[key].items():
            ok = r["c1_pass"] and r["c2_pass"] and r["c3_pass"]
            lines.append(f"| {label} | {s} | {r['country_file']:,} | {r['false_inclusions']} | {r['false_exclusions']} | "
                         f"{v.pct(r['c1_share'])} | {v.pct(r['c2_worst_month'])} | {v.pct(r['c3_share'])} | {'yes' if ok else '**no**'} |")
    (HERE / "REPORT_lebanon_border.md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
