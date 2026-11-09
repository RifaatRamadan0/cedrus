"""Pre-export gate for the proposed Tier 1 boxes; no third-party dependencies.

Downloads only explicitly selected years of the three production archive families.
Stops at the first whole-country loss and preserves every excluded source row.
This is a box/filter audit, not evidence of monthly archive completeness.
"""
import argparse
import csv
import hashlib
import importlib.util
import io
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOXES = {
    "syria": ("Syria", (35.5, 32.2, 42.5, 37.5)),
    "jordan": ("Jordan", (34.8, 29.0, 39.5, 33.5)),
    "cyprus": ("Cyprus", (32.1, 34.4, 34.8, 35.8)),
    "palestine": ("Palestine", (34.1, 31.1, 35.7, 32.7)),
    "israel": ("Israel", (34.2, 29.4, 35.95, 33.4)),
    "la_rioja": ("Argentina", (-69.7, -32.8, -65.4, -27.7)),
}


def inspect(body, box, sensor):
    reader = csv.DictReader(io.StringIO(body.decode("utf-8-sig")))
    if not {"latitude", "longitude", "confidence"}.issubset(reader.fieldnames or []):
        raise ValueError("Unexpected FIRMS schema")
    rows = list(reader)
    counts = Counter({kind: 0 for kind in ("0", "1", "2", "3", "missing", "unexpected")})
    excluded = []
    kept = 0
    for row in rows:
        kind = row.get("type", "")
        counts[kind if kind in ("0", "1", "2", "3") else "missing" if not kind else "unexpected"] += 1
        lon, lat = float(row["longitude"]), float(row["latitude"])
        inside = box[0] <= lon < box[2] and box[1] <= lat < box[3]
        if not inside:
            excluded.append(row)
        confidence = row["confidence"].lower()
        confident = float(confidence) >= 30 if sensor == "modis" else confidence[:1] in ("n", "h")
        kept += int(inside and kind == "0" and confident)
    return {"rows": len(rows), "type_field_present": "type" in reader.fieldnames,
            "box_retained": len(rows) - len(excluded),
            "box_excluded": len(excluded), "type_counts_before_filters": dict(counts),
            "retained_after_box_type0_confidence": kept,
            "monthly_completeness": "unknown"}, excluded


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--years", type=int, nargs="+", required=True)
    ap.add_argument("--regions", nargs="+", choices=BOXES, default=list(BOXES))
    ap.add_argument("--report", default="box_audit.json", help="Report filename within analysis/tier1")
    ap.add_argument("--raw-root", type=Path, default=ROOT / "data/raw", help="Existing source root, with country subdirectories")
    ap.add_argument("--offline", action="store_true", help="Verify existing files only; do not modify source folders")
    ap.add_argument("--availability", action="store_true", help="Use verified FIRMS product-start metadata to classify pre-product years")
    args = ap.parse_args()
    if Path(args.report).name != args.report:
        ap.error("--report must be a filename")
    if any(year < 2000 or year > 2025 for year in args.years):
        ap.error("Only archive years 2000–2025 are in scope")
    spec = importlib.util.spec_from_file_location("country_download", ROOT / "pipeline/01_download.py")
    downloader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(downloader)
    out = ROOT / "analysis/tier1"
    out.mkdir(parents=True, exist_ok=True)
    report = {"requested_years": args.years, "requested_regions": args.regions,
              "scope": "Box, checksum and filter audit; not evidence of monthly completeness", "files": [], "unavailable": []}
    starts = {}
    if args.availability:
        for sensor, product in (("modis", "MODIS_SP"), ("viirs-snpp", "VIIRS_SNPP_SP"), ("viirs-jpss1", "VIIRS_NOAA20_SP")):
            evidence = ROOT / "analysis/tier1/coverage_services" / f"{product}.txt"
            with evidence.open(newline="") as f:
                rows = list(csv.DictReader(f))
            assert len(rows) == 1 and rows[0]["data_id"] == product
            starts[sensor] = rows[0]["min_date"]
    def save():
        (out / args.report).write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for region in args.regions:
        country, box = BOXES[region]
        raw = args.raw_root / country.lower()
        if not args.offline:
            raw.mkdir(parents=True, exist_ok=True)
        manifest_path = raw / "manifest.json"
        manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
        for year in args.years:
            for sensor in ("modis", "viirs-snpp", "viirs-jpss1"):
                name = f"{sensor}_{year}_{country}.csv"
                if sensor in starts and year < int(starts[sensor][:4]):
                    report["unavailable"].append(dict(region=region, file=name, reason="Year precedes FIRMS standard-product date extent", product_first_date=starts[sensor]))
                    save()
                    continue
                path = raw / name
                url = f"{downloader.BASE}/{sensor}/{year}/{name}"
                started = time.monotonic()
                cached = path.exists()
                try:
                    if cached:
                        body = path.read_bytes()
                        if name not in manifest or hashlib.sha256(body).hexdigest() != manifest[name]["sha256"]:
                            raise ValueError(f"Existing file lacks a matching manifest checksum: {path}")
                    else:
                        if args.offline:
                            raise FileNotFoundError(f"Required offline source missing: {name}")
                        for attempt in range(3):
                            try:
                                body = downloader.fetch(url, False)
                                break
                            except Exception:
                                if attempt == 2:
                                    raise
                                time.sleep(attempt + 1)
                    summary, excluded = inspect(body, box, sensor)
                    elapsed = time.monotonic() - started
                    digest = hashlib.sha256(body).hexdigest()
                    if not cached:
                        with path.open("xb") as handle:
                            handle.write(body)
                        manifest[name] = {"url": url, "sensor": downloader.SENSORS[sensor], "year": year,
                                          "bytes": len(body), "rows": summary["rows"], "sha256": digest,
                                          "retrieved": datetime.now(timezone.utc).isoformat(),
                                          "download_and_audit_seconds": round(elapsed, 3)}
                        temporary = manifest_path.with_suffix(".json.tmp")
                        temporary.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
                        temporary.replace(manifest_path)
                    entry = dict(region=region, file=name, url=url, box=box, bytes=len(body),
                                 sha256=digest, cached=cached, elapsed_seconds=round(elapsed, 3), **summary)
                    entry["download_and_audit_seconds"] = manifest[name].get("download_and_audit_seconds")
                    report["files"].append(entry)
                    print(f"{name}: {summary['rows']} rows; excluded {len(excluded)}; {len(body)} bytes", flush=True)
                    if excluded and region != "la_rioja":
                        evidence = out / f"excluded_{name}"
                        with evidence.open("w", newline="", encoding="utf-8") as handle:
                            writer = csv.DictWriter(handle, fieldnames=list(excluded[0]))
                            writer.writeheader()
                            writer.writerows(excluded)
                        entry["excluded_rows_evidence"] = str(evidence.relative_to(ROOT))
                        report["status"] = "STOP: proposed whole-country box excludes source rows"
                        save()
                        return 2
                except Exception as exc:
                    report["status"] = "INCOMPLETE: source retrieval or validation failed; unavailable year not established"
                    report["error"] = {"file": name, "detail": str(exc)}
                    save()
                    return 1
                save()
    report["status"] = "Selected files pass box gate; full archive audit still required"
    save()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
