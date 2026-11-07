"""Verify protected exports, catalog entries and frozen models without modifying them."""
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    baseline = json.loads((ROOT / "analysis/tier1/baseline.json").read_text(encoding="utf-8"))
    committed = json.loads(subprocess.check_output(
        ["git", "show", "HEAD:web/data/regions.json"], cwd=ROOT
    ).decode("utf-8"))
    current = json.loads((ROOT / "web/data/regions.json").read_text(encoding="utf-8"))
    current_by_id = {r["id"]: r for r in current["regions"]}
    changed_exports = [f for f, v in baseline["preserved_exports"].items()
                       if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != v["sha256"]]
    changed_models = [f for f, expected in baseline["frozen"].items()
                      if hashlib.sha256((ROOT / f).read_bytes()).hexdigest() != expected]
    changed_entries = [r["id"] for r in committed["regions"]
                       if r["id"] in ("portugal", "lebanon") and current_by_id.get(r["id"]) != r]
    result = {
        "preserved_export_count": len(baseline["preserved_exports"]),
        "all_preserved_exports_unchanged": not changed_exports,
        "existing_region_entries_unchanged": not changed_entries,
        "frozen_models_unchanged": not changed_models,
        "changed_exports": changed_exports,
        "changed_catalog_entries": changed_entries,
        "changed_models": changed_models,
        "env_ignored": subprocess.run(["git", "check-ignore", "-q", ".env"], cwd=ROOT).returncode == 0,
        "deferred_exports_absent": all(not (ROOT / "web/data" / r).exists() for r in ("israel", "palestine")),
        "deferred_raw_retained": all((ROOT / "data/raw" / r).is_dir() for r in ("israel", "palestine")),
    }
    result["passed"] = all(result[k] for k in (
        "all_preserved_exports_unchanged", "existing_region_entries_unchanged", "frozen_models_unchanged",
        "env_ignored", "deferred_exports_absent", "deferred_raw_retained"))
    report = json.dumps(result, indent=2) + "\n"
    (ROOT / "analysis/tier1/scope_revision_preservation.json").write_text(report, encoding="utf-8")
    print(report, end="")
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
