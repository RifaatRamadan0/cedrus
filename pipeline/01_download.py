"""Download NASA FIRMS yearly country archives (no key needed) into data/raw/.

    python pipeline/01_download.py                  # Portugal, all sensors, 2000-2026
    python pipeline/01_download.py --country Spain  # any FIRMS country name

Files that do not exist on FIRMS (sensor not flying that year) are skipped.
A manifest with the URL, size and SHA-256 of every file is written next to them,
so every number on the website can be traced back to the exact file it came from.
"""
import argparse
import hashlib
import json
import ssl
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = "https://firms.modaps.eosdis.nasa.gov/data/country"
# FIRMS folder name -> what it is
SENSORS = {
    "modis": "MODIS C6.1 (Terra + Aqua), 1 km",
    "viirs-snpp": "VIIRS 375 m, Suomi NPP",
    "viirs-jpss1": "VIIRS 375 m, NOAA-20",
    "viirs-jpss2": "VIIRS 375 m, NOAA-21",
}


def fetch(url, insecure):
    ctx = ssl._create_unverified_context() if insecure else None
    req = urllib.request.Request(url, headers={"User-Agent": "cedrus-space-apps/0.1"})
    with urllib.request.urlopen(req, timeout=120, context=ctx) as r:
        return r.read()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", default="Portugal")
    ap.add_argument("--start", type=int, default=2000)
    ap.add_argument("--end", type=int, default=datetime.now().year)
    ap.add_argument("--insecure", action="store_true",
                    help="skip TLS verification (some corporate networks break it)")
    args = ap.parse_args()

    out = ROOT / "data" / "raw" / args.country.lower()
    out.mkdir(parents=True, exist_ok=True)
    manifest_path = out / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    for sensor in SENSORS:
        for year in range(args.start, args.end + 1):
            name = f"{sensor}_{year}_{args.country}.csv"
            path = out / name
            url = f"{BASE}/{sensor}/{year}/{name}"
            if path.exists() and name in manifest:
                continue
            try:
                body = fetch(url, args.insecure)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    continue  # sensor not in the archive for that year
                print(f"  ! {name}: HTTP {e.code}", file=sys.stderr)
                continue
            except Exception as e:  # network trouble: report and move on
                print(f"  ! {name}: {e}", file=sys.stderr)
                continue
            path.write_bytes(body)
            manifest[name] = {
                "url": url,
                "sensor": SENSORS[sensor],
                "year": year,
                "bytes": len(body),
                "rows": body.count(b"\n") - 1,
                "sha256": hashlib.sha256(body).hexdigest(),
                "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            }
            print(f"  {name}: {len(body)/1e6:.2f} MB, {manifest[name]['rows']} detections")
            manifest_path.write_text(json.dumps(manifest, indent=1))
            time.sleep(0.3)  # be polite to FIRMS

    print(f"{len(manifest)} files in {out}")


if __name__ == "__main__":
    main()
