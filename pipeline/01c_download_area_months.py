"""Download FIRMS area-API detections for a product region's box, one CSV per source and month.

    python pipeline/01c_download_area_months.py --region syria --sources VIIRS_SNPP_SP,VIIRS_NOAA20_SP,MODIS_SP \
        --start 2025-01 --end 2025-12

Used for 2026, which has no FIRMS country file yet (docs/OBS2026_VALIDATION_PLAN.md). The area API returns every
detection inside the box, from any country, so the files written here are NOT clipped to the country; that is a
separate, tested step.

Writes data/raw/area_api/<region>/<SOURCE>_<YYYY-MM>.csv plus manifest.json (URL with the key removed, rows,
bytes, SHA-256, time). A month already in the manifest is skipped, so the run can be resumed; pass --refresh to
fetch it again (NRT months are replaced by standard data later). The key is read from .env (FIRMS_MAP_KEY, or the
older FIRMS_API_KEY) and is never printed or written.
"""
import argparse
import hashlib
import json
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
from regions import REGIONS  # noqa: E402

API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{src}/{box}/{days}/{day}"
WINDOW = 5  # days per request


def key():
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        for name in ("FIRMS_MAP_KEY=", "FIRMS_API_KEY="):
            if line.startswith(name):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise SystemExit("FIRMS_MAP_KEY missing from .env")


def fetch(url, secret, tries=6):
    """One request. FIRMS allows a limited number of transactions per 10 minutes: on the limit message we wait
    the window out. Errors never include the key."""
    for attempt in range(1, tries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "cedrus-space-apps/0.3"})
            try:
                with urllib.request.urlopen(req, timeout=180) as r:
                    text = r.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                text = e.read().decode("utf-8", errors="replace")
            if text.startswith("latitude,"):
                return text
            if "transaction limit" in text.lower() or "exceeding" in text.lower():
                print("  rate limit reached, waiting 10 minutes", flush=True)
                time.sleep(610)
                continue
            raise RuntimeError(text[:160].replace(secret, "<KEY>"))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt == tries:
                raise RuntimeError(str(e).replace(secret, "<KEY>")) from None
            time.sleep(5 * attempt)
    raise RuntimeError("gave up after repeated rate limits")


def months(start, end):
    y, m = map(int, start.split("-"))
    y1, m1 = map(int, end.split("-"))
    while (y, m) <= (y1, m1):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", required=True, choices=sorted(r for r, c in REGIONS.items() if c.get("box")))
    ap.add_argument("--sources", required=True, help="comma-separated FIRMS sources, e.g. VIIRS_SNPP_SP,MODIS_NRT")
    ap.add_argument("--start", required=True, help="YYYY-MM")
    ap.add_argument("--end", required=True, help="YYYY-MM")
    ap.add_argument("--until", help="last day to request (YYYY-MM-DD), for a month still in progress")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--refresh", action="store_true")
    args = ap.parse_args()
    secret = key()
    lon0, lat0, lon1, lat1 = REGIONS[args.region]["box"]
    box = f"{lon0},{lat0},{lon1},{lat1}"
    out = ROOT / "data" / "raw" / "area_api" / args.region
    out.mkdir(parents=True, exist_ok=True)
    mpath = out / "manifest.json"
    manifest = json.loads(mpath.read_text(encoding="utf-8")) if mpath.exists() else {}
    until = date.fromisoformat(args.until) if args.until else None

    for src in args.sources.split(","):
        for y, m in months(args.start, args.end):
            name = f"{src}_{y}-{m:02d}.csv"
            if name in manifest and not args.refresh:
                continue
            first = date(y, m, 1)
            last = (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1))
            if until:
                last = min(last, until)
            if last < first:
                continue
            starts = [first + timedelta(days=i) for i in range(0, (last - first).days + 1, WINDOW)]
            spans = [min(WINDOW, (last - s).days + 1) for s in starts]
            urls = [API.format(key=secret, src=src, box=box, days=n, day=s.isoformat()) for s, n in zip(starts, spans)]
            with ThreadPoolExecutor(args.workers) as pool:
                parts = list(pool.map(lambda u: fetch(u, secret), urls))
            header = parts[0].splitlines()[0]
            day_col = header.split(",").index("acq_date")
            prefix = f"{y}-{m:02d}"
            rows = sorted({r for p in parts for r in p.splitlines()[1:]
                           if r.strip() and r.split(",")[day_col].startswith(prefix)
                           and r.split(",")[day_col] <= last.isoformat()})
            body = (header + "\n" + "\n".join(rows) + ("\n" if rows else "")).encode("utf-8")
            (out / name).write_bytes(body)
            manifest[name] = {
                "url": API.format(key="<MAP_KEY>", src=src, box=box, days=WINDOW, day=f"{prefix}-*"),
                "source": src, "month": prefix, "through": last.isoformat(), "rows": len(rows), "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "retrieved": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "via": f"FIRMS area API, box {box} (not clipped to the country), {len(urls)} requests",
            }
            mpath.write_text(json.dumps(manifest, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
            print(f"  {args.region} {name}: {len(rows)} detections ({len(urls)} requests)", flush=True)


if __name__ == "__main__":
    main()
