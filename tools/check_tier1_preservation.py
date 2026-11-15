"""Verify protected exports, catalog entries and frozen models without modifying them.

Since 2026 was added (docs/OBS2026_VALIDATION_PLAN.md), Portugal's and Lebanon's four whole-record files (monthly,
monthly_bd, drift, drift_bd) grow by the new months. They are no longer compared byte for byte; instead
tools/check_history_unchanged.py must pass, which requires every 2000-2025 value in them to be identical. Their
year files up to 2025 are still compared byte for byte. Catalog entries are compared with a
fixed reference commit (the last one ending in 2025), not with HEAD, so the check still means something after a commit.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tools"))
from check_history_unchanged import REF  # noqa: E402
from regions import REGIONS  # noqa: E402

GROWING_FILES = {f"web/data/{r}/{n}" for r in ("portugal", "lebanon")
                 for n in ("monthly.json", "monthly_bd.json", "drift.json", "drift_bd.json")}
# Catalog fields that describe the record's extent, or totals over the whole record, and so change when months are
# added. Anything else in a protected entry (models, fits, policy rules, boxes, names) must stay identical.
GROWING_FIELDS = {
    "generated_at", "hotspot_years", "months.last", "policy.estimated", "provenance.files", "provenance.source",
    "detections.T", "detections.A", "detections.N", "detections.J1",
    "record_end.after", "record_end.detections_outside_grid",
    "record_end.modis.last", "record_end.modis.last_detection", "record_end.noaa20.last",
    "record_end.noaa20.last_detection", "record_end.suomi_npp.last", "record_end.suomi_npp.last_detection",
    "model_detail.check.background_total", "burning_days.model_detail.check.background_total",
    "burning_days.records.modis", "burning_days.records.snpp", "burning_days.records.noaa20", "burning_days.years",
    "burning_days.zero_weight.share", "burning_days.zero_weight.viirs_burning_days",
    # Totals over 2022..last month, like the two above (Lebanon's 2026 months add to them; Portugal's did not).
    # The per-month notes are in monthly_bd.json, whose 2000-2025 notes check_history_unchanged.py compares.
    "burning_days.zero_weight.weight_zero", "burning_days.zero_weight.months_noted",
}


def changed_fields(a, b, path=""):
    out = []
    for k in sorted(set(a) | set(b)):
        if a.get(k) != b.get(k):
            if isinstance(a.get(k), dict) and isinstance(b.get(k), dict):
                out += changed_fields(a[k], b[k], path + k + ".")
            else:
                out.append(path + k)
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--published-only", action="store_true",
                        help="Check distributed artifacts; report raw-input retention as not checked")
    args = parser.parse_args()
    baseline = json.loads((ROOT / "analysis/tier1/baseline.json").read_text(encoding="utf-8"))
    reference = json.loads(subprocess.check_output(["git", "show", f"{REF}:web/data/regions.json"], cwd=ROOT).decode("utf-8"))
    current = json.loads((ROOT / "web/data/regions.json").read_text(encoding="utf-8"))
    current_by_id = {r["id"]: r for r in current["regions"]}
    changed_exports = [f for f, v in baseline["preserved_exports"].items() if f not in GROWING_FILES
                       and hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != v["sha256"]]
    changed_models = [f for f, expected in baseline["frozen"].items()
                      if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != expected]
    history = subprocess.run([sys.executable, str(ROOT / "tools/check_history_unchanged.py")], cwd=ROOT,
                             capture_output=True, text=True, encoding="utf-8")
    history_ok = history.returncode == 0
    # Notes are display text from pipeline/regions.py, so they are compared with that file instead.
    changed_entries = {}
    for r in reference["regions"]:
        rid = r["id"]
        if rid not in ("portugal", "lebanon"):
            continue
        cur = current_by_id.get(rid, {})
        allowed = GROWING_FIELDS
        bad = [f for f in changed_fields(r, cur) if f != "notes" and f not in allowed]
        if cur.get("notes", []) != REGIONS[rid].get("notes", []):
            bad.append("notes (differ from regions.py)")
        if bad:
            changed_entries[rid] = bad
    result = {
        "reference_commit": REF,
        "preserved_export_count": len(baseline["preserved_exports"]),
        "byte_compared_exports": len(baseline["preserved_exports"]) - len(GROWING_FILES),
        "all_preserved_exports_unchanged": not changed_exports,
        "history_2000_2025_unchanged": history_ok,
        "existing_region_entries_unchanged": not changed_entries,
        "frozen_models_unchanged": not changed_models,
        "changed_exports": changed_exports,
        "changed_catalog_entries": changed_entries,
        "changed_models": changed_models,
        "env_ignored": subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT).returncode == 0,
        "deferred_exports_absent": all(not (ROOT / "web/data" / r).exists() for r in ("israel", "palestine")),
        "deferred_raw_retained": None if args.published_only else all(
            (ROOT / "data/raw" / r).is_dir() for r in ("israel", "palestine")),
        "scope": "published artifacts" if args.published_only else "published artifacts and local raw inputs",
    }
    result["passed"] = all(result[k] for k in (
        "all_preserved_exports_unchanged", "history_2000_2025_unchanged", "existing_region_entries_unchanged",
        "frozen_models_unchanged", "env_ignored", "deferred_exports_absent"))
    if not args.published_only:
        result["passed"] = result["passed"] and result["deferred_raw_retained"]
    report = json.dumps(result, indent=2) + "\n"
    (ROOT / "analysis/tier1/scope_revision_preservation.json").write_text(report, encoding="utf-8", newline="\n")
    print(report, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
