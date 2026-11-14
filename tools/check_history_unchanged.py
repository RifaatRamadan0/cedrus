"""2000-2025 must stay exactly as published when later months are added (docs/OBS2026_VALIDATION_PLAN.md).

    python tools/check_history_unchanged.py [--data web/data] [--ref 4e33960]

Compares every product region's exported files with the same files at --ref, the last commit whose record ends
in 2025. Passes only if, for every region:
- year files (hotspots/<year>.json, burning/<year>.json) up to HISTORY_END are byte-identical;
- monthly.json and monthly_bd.json keep the same first month and the same grid (cells, in order), and every
  array (m, bg, p10, p90, naive), flag and note is identical for every month up to HISTORY_END;
- drift.json and drift_bd.json are identical for every month up to HISTORY_END;
- both frozen models are unchanged (analysis/tier1/baseline.json).
Writes analysis/obs2026/history_check.json.
"""
import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
HISTORY_END = "2025-12"
REF = "4e33960"  # docs(tier1): record per-region test results and the four-region scope; record ends 2025


def at_ref(ref, path):
    out = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True)
    return out.stdout if out.returncode == 0 else None


def month_list(first, n):
    y, m = map(int, first.split("-"))
    out = []
    for _ in range(n):
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def check_monthly(old, new):
    problems = []
    if old["months"]["first"] != new["months"]["first"]:
        problems.append("first month changed")
    if old["cells"] != new["cells"]:
        problems.append("grid changed")
    months = month_list(old["months"]["first"], old["months"]["n"])
    k = sum(m <= HISTORY_END for m in months)
    if new["flags"][:k] != old["flags"][:k]:
        problems.append("flags changed")
    for key in ("m", "bg", "p10", "p90", "naive"):
        if key in old and any(a[:k] != b[:k] for a, b in zip(old[key], new[key])):
            problems.append(f"{key} changed")
    for key in ("slot_notes", "zero_notes"):
        if key in old:
            o = {m: v for m, v in old[key].items() if m <= HISTORY_END}
            n = {m: v for m, v in new.get(key, {}).items() if m <= HISTORY_END}
            if o != n:
                problems.append(f"{key} changed")
    return problems, k


def check_drift(old, new):
    months = month_list(old["months"]["first"], old["months"]["n"])
    k = sum(m <= HISTORY_END for m in months)
    if new["months"]["first"] != old["months"]["first"]:
        return ["first month changed"]
    problems = [key for key in ("observed_modis", "predicted_modis", "trailing12_ratio") if old[key][:k] != new[key][:k]]
    if old.get("band") != new.get("band"):
        problems.append("band")
    return [f"{p} changed" for p in problems]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="web/data")
    ap.add_argument("--ref", default=REF)
    args = ap.parse_args()
    data = (ROOT / args.data).resolve()
    catalog = json.loads(at_ref(args.ref, "web/data/regions.json").decode("utf-8"))
    result = {"ref": args.ref, "history_end": HISTORY_END, "regions": {}}
    for entry in catalog["regions"]:
        rid = entry["id"]
        r = {"problems": []}
        for name, check in (("monthly.json", check_monthly), ("monthly_bd.json", check_monthly),
                            ("drift.json", check_drift), ("drift_bd.json", check_drift)):
            old = json.loads(at_ref(args.ref, f"web/data/{rid}/{name}").decode("utf-8"))
            new = json.loads((data / rid / name).read_text(encoding="utf-8"))
            res = check(old, new)
            problems = res[0] if isinstance(res, tuple) else res
            r["problems"] += [f"{name}: {p}" for p in problems]
            if name == "monthly.json":
                r["months"] = {"before": old["months"]["last"], "after": new["months"]["last"]}
        listing = subprocess.run(["git", "ls-tree", "-r", "--name-only", args.ref, f"web/data/{rid}/"], cwd=ROOT,
                                 capture_output=True, text=True).stdout.split()
        years = [p for p in listing if p.split("/")[-2] in ("hotspots", "burning")]
        changed = [p for p in years if int(Path(p).stem) <= int(HISTORY_END[:4])
                   and at_ref(args.ref, p) != (data / Path(p).relative_to("web/data")).read_bytes()]
        r["year_files_compared"] = len(years)
        r["problems"] += [f"{p}: not byte-identical" for p in changed]
        r["pass"] = not r["problems"]
        result["regions"][rid] = r
    baseline = json.loads((ROOT / "analysis/tier1/baseline.json").read_text(encoding="utf-8"))
    result["frozen_models_unchanged"] = all(hashlib.sha256((ROOT / f).read_bytes()).hexdigest() == h
                                            for f, h in baseline["frozen"].items())
    result["pass"] = result["frozen_models_unchanged"] and all(r["pass"] for r in result["regions"].values())
    (ROOT / "analysis/obs2026").mkdir(exist_ok=True)
    if args.data == "web/data":
        (ROOT / "analysis/obs2026/history_check.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
