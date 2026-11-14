"""Download FIRMS standard (SP) detections for a lon/lat box through the FIRMS area API.

    python pipeline/01b_download_area.py --country South_Africa --box 17.5,-35,24,-31 --start 2012 --end 2025

Needs FIRMS_API_KEY in .env (free key: https://firms.modaps.eosdis.nasa.gov/api/map_key/).
Writes per-year CSVs named like the country archive (modis_<year>_<Country>.csv, ...) into
data/raw/<country lower>/, with the same columns, plus a manifest recording that the rows came from
the area API for that box (not the whole country file). Downstream steps clip to the region box anyway.
"""
import argparse
import hashlib
import io
import json
import ssl
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{src}/{box}/5/{day}"
SOURCES = {"modis": "MODIS_SP", "viirs-snpp": "VIIRS_SNPP_SP", "viirs-jpss1": "VIIRS_NOAA20_SP"}
FIRST = {"modis": date(2000, 11, 1), "viirs-snpp": date(2012, 1, 20), "viirs-jpss1": date(2018, 4, 1)}


def key():
    for line in (ROOT / ".env").read_text().splitlines():
        if line.startswith("FIRMS_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("FIRMS_API_KEY missing from .env")


def fetch(url, tries=6):
    """FIRMS allows 5000 transactions per 10 minutes (a 5-day request costs several), so on the
    limit message we wait out the window instead of failing."""
    ctx = ssl._create_unverified_context()
    i = 0
    while True:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "cedrus-space-apps/0.2"})
            try:
                with urllib.request.urlopen(req, timeout=90, context=ctx) as r:
                    text = r.read().decode()
            except urllib.error.HTTPError as e:
                text = e.read().decode(errors="replace")
            if text.startswith("latitude,"):
                time.sleep(0.5)
                return text
            if "transaction limit" in text.lower():
                print("  rate limit reached, waiting 10 minutes", flush=True)
                time.sleep(610)
                continue
            raise RuntimeError(text[:120])
        except Exception:  # network blip: back off and retry
            i += 1
            if i >= tries:
                raise
            time.sleep(5 * i)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", required=True)
    ap.add_argument("--box", required=True, help="west,south,east,north")
    ap.add_argument("--start", type=int, required=True)
    ap.add_argument("--end", type=int, required=True)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()
    k = key()
    out = ROOT / "data" / "raw" / args.country.lower()
    out.mkdir(parents=True, exist_ok=True)
    mpath = out / "manifest.json"
    manifest = json.loads(mpath.read_text()) if mpath.exists() else {}

    for stem, src in SOURCES.items():
        for year in range(args.start, args.end + 1):
            name = f"{stem}_{year}_{args.country}.csv"
            if name in manifest:
                continue
            d0, d1 = max(date(year, 1, 1), FIRST[stem]), date(year, 12, 31)
            if d0 > d1:
                continue
            days = []
            d = d0
            while d <= d1:
                days.append(d)
                d += timedelta(days=5)
            urls = [API.format(key=k, src=src, box=args.box, day=x.isoformat()) for x in days]
            with ThreadPoolExecutor(args.workers) as pool:
                parts = list(pool.map(fetch, urls))
            header = parts[0].splitlines()[0]
            rows = [ln for p in parts for ln in p.splitlines()[1:] if ln.strip()]
            # windows can overlap the year end; keep this year's rows only, drop exact duplicates
            rows = sorted({r for r in rows if r.split(",")[5].startswith(str(year))})
            body = (header + "\n" + "\n".join(rows) + ("\n" if rows else "")).encode()
            (out / name).write_bytes(body)
            manifest[name] = {
                "url": API.format(key="<MAP_KEY>", src=src, box=args.box, day=f"{year}-*") ,
                "sensor": src, "year": year, "bytes": len(body), "rows": len(rows),
                "sha256": hashlib.sha256(body).hexdigest(),
                "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "via": f"FIRMS area API, box {args.box}, {len(urls)} five-day requests",
            }
            mpath.write_text(json.dumps(manifest, indent=1))
            print(f"  {name}: {len(rows)} detections ({len(urls)} requests)", flush=True)


if __name__ == "__main__":
    main()
