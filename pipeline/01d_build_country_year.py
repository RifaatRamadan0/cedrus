"""Build a country-file-style CSV for a year FIRMS has not published per country yet (2026), from standard data.

    python pipeline/01d_build_country_year.py --region portugal --year 2026 --through 2026-07

Joins the region's monthly area-API standard-processing files (pipeline/01c_download_area_months.py), keeps the
detections inside the country's Natural Earth outline (pipeline/outline.py; tested against the 2025 country files,
docs/OBS2026_VALIDATION_PLAN.md; Lebanon uses the 30 August 2021 outline, LEBANON_2021), and writes
data/raw/<region>/<stem>_<year>_<Country>.csv with the country files' own columns, plus a manifest entry so the
exporter's checksum gate covers it.

Only *_SP (standard) sources are accepted: near-real-time data has no `type` field and the static-source mask that
would replace it failed validation. Months after --through are not written.
"""
import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from outline import BOUNDARIES, BOUNDARIES_SHA256, LEBANON_2021, inside, load_countries, load_lebanon_2021  # noqa: E402
from regions import REGIONS  # noqa: E402

SOURCES = {"modis": "MODIS_SP", "viirs-snpp": "VIIRS_SNPP_SP", "viirs-jpss1": "VIIRS_NOAA20_SP"}
# Same sensor descriptions as the country-file manifests written by pipeline/01_download.py.
SENSOR_TEXT = {"modis": "MODIS C6.1 (Terra + Aqua), 1 km", "viirs-snpp": "VIIRS 375 m, Suomi NPP",
               "viirs-jpss1": "VIIRS 375 m, NOAA-20"}
ISO = {"portugal": "PRT", "lebanon": "LBN", "syria": "SYR", "la_rioja": "ARG"}
# Regions whose country assignment passed its test. Lebanon passed only with the 30 August 2021 Natural Earth
# outline (the current file failed on its southern line), so it uses that outline and nothing else does.
VALIDATED = {"portugal", "syria", "la_rioja", "lebanon"}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", required=True, choices=sorted(ISO))
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--through", required=True, help="last month to include, YYYY-MM")
    args = ap.parse_args()
    if args.region not in VALIDATED:
        raise SystemExit(f"{args.region}: country assignment not validated (docs/OBS2026_VALIDATION_PLAN.md)")
    if sha256(BOUNDARIES) != BOUNDARIES_SHA256:
        raise SystemExit("Natural Earth file differs from the one validated; refusing")
    cfg = REGIONS[args.region]
    country = cfg["country"]
    raw = ROOT / "data" / "raw" / args.region
    area = ROOT / "data" / "raw" / "area_api" / args.region
    area_manifest = json.loads((area / "manifest.json").read_text(encoding="utf-8"))
    if args.region == "lebanon":
        rings = load_lebanon_2021()
        outline_text = (f"the Natural Earth 1:10m outline of LBN as of commit {LEBANON_2021['commit'][:10]} "
                        f"({LEBANON_2021['date']}; pipeline/outline.py LEBANON_2021, shp sha256 "
                        f"{LEBANON_2021['sha256']['shp'][:12]})")
    else:
        rings = load_countries()[ISO[args.region]]["rings"]
        outline_text = (f"the Natural Earth 1:10m outline of {ISO[args.region]} (pipeline/outline.py, boundaries "
                        f"sha256 {BOUNDARIES_SHA256[:12]})")
    months = [str(p) for p in pd.period_range(f"{args.year}-01", args.through, freq="M")]
    mpath = raw / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8"))

    for stem, src in SOURCES.items():
        names = [f"{src}_{m}.csv" for m in months]
        for n in names:
            entry = area_manifest.get(n)
            if entry is None or sha256(area / n) != entry["sha256"]:
                raise SystemExit(f"{args.region}/{n}: missing or checksum mismatch")
        text = [(area / n).read_text(encoding="utf-8") for n in names]
        header = text[0].splitlines()[0]
        df = pd.concat([pd.read_csv(area / n, dtype=str, keep_default_na=False) for n in names], ignore_index=True)
        if list(df.columns) != header.split(",") or "type" not in df.columns:
            raise SystemExit(f"{args.region} {src}: unexpected columns {list(df.columns)}")
        keep = inside(rings, df.longitude.astype(float), df.latitude.astype(float))
        out = df[keep].sort_values(["acq_date", "acq_time"], kind="stable")
        name = f"{stem}_{args.year}_{country}.csv"
        body = out.to_csv(index=False, lineterminator="\n").encode("utf-8")
        (raw / name).write_bytes(body)
        built = datetime.now(timezone.utc).isoformat(timespec="seconds")
        manifest[name] = {
            "url": f"derived: FIRMS area API {src}, {months[0]}..{months[-1]} (monthly files in data/raw/area_api/{args.region})",
            "sensor": SENSOR_TEXT[stem], "year": args.year, "retrieved": built,
            "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(), "rows": int(len(out)),
            "rows_in_box": int(len(df)), "through": months[-1],
            "via": f"area-API standard data clipped to {outline_text}; not a FIRMS country file",
            "sources": {n: area_manifest[n]["sha256"] for n in names},
        }
        print(f"  {args.region} {name}: {len(out)} of {len(df)} box detections inside the outline", flush=True)
    mpath.write_text(json.dumps(manifest, indent=1) + "\n", encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
