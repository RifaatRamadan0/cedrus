"""Verify the supplied La Rioja crop loses no rows beyond its documented box."""
import argparse
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("raw_root", type=Path)
    args = ap.parse_args()
    original = json.loads((args.raw_root / "argentina/manifest.json").read_text())
    subset = json.loads((args.raw_root / "la_rioja/manifest.json").read_text())
    report = []
    for name, meta in original.items():
        if int(name.split("_")[1]) > 2017:
            continue
        p, q = args.raw_root / "argentina" / name, args.raw_root / "la_rioja" / name
        assert hashlib.sha256(p.read_bytes()).hexdigest() == meta["sha256"]
        assert hashlib.sha256(q.read_bytes()).hexdigest() == subset[name]["sha256"]
        assert subset[name]["source_sha256"] == meta["sha256"]
        with p.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            fields = reader.fieldnames
            kept = Counter(tuple(row[k] for k in fields) for row in reader
                           if -69.7 <= float(row["longitude"]) < -65.4 and -32.8 <= float(row["latitude"]) < -27.7)
        with q.open(newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            assert reader.fieldnames == fields
            actual = Counter(tuple(row[k] for k in fields) for row in reader)
        report.append(dict(file=name, expected_crop_rows=sum(kept.values()), actual_crop_rows=sum(actual.values()),
                           missing_rows=sum((kept-actual).values()), additional_rows=sum((actual-kept).values())))
    out = ROOT / "analysis/tier1/argentina_crop_2000_2017.json"
    out.write_text(json.dumps(report, indent=2)+"\n", encoding="utf-8")
    assert not any(row["missing_rows"] or row["additional_rows"] for row in report)
    print(f"{len(report)} original-to-crop comparisons passed; no losses beyond the intended box.")


if __name__ == "__main__":
    main()
