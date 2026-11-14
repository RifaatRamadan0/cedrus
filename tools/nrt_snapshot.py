"""Right now vs normal: the last complete days of NASA's live NOAA-20 fire feed, against the same calendar days in
2019-2025, for every region that has a normal (tools/nrt_normal.py).

    python tools/nrt_snapshot.py            # downloads FIRMS's keyless global 7-day NOAA-20 file (~36 MB)
    python tools/nrt_snapshot.py --csv FILE # or reads a file already downloaded

Same rules on both sides as tools/nrt_normal.py (NOAA-20; confidence n/h; burning day = 0.01-degree square x date
x day/night; static squares dropped; region box + country outline). The feed's first and last dates are partial
(it is a rolling 7 x 24 hours), so only the dates strictly between them are counted. Writes web/data/nrt.json.
Live (near-real-time) detections are not the standard-quality ones the record uses, and they are not harmonized:
this is a like-for-like NOAA-20 comparison, said so on the page.
"""
import argparse
import calendar
import io
import json
import statistics as st
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "pipeline"))
sys.path.insert(0, str(ROOT / "tools"))
from nrt_normal import FINE, OUT as NORMALS, clip, rings_for, squares  # noqa: E402
from regions import REGIONS  # noqa: E402

URL = "https://firms.modaps.eosdis.nasa.gov/data/active_fire/noaa-20-viirs-c2/csv/J1_VIIRS_C2_Global_7d.csv"
MIN_YEARS = 5


def quantile(v, q):
    v = sorted(v); i = (len(v) - 1) * q; lo = int(i); hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (i - lo)


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--csv"); a = ap.parse_args()
    raw = Path(a.csv).read_bytes() if a.csv else urllib.request.urlopen(urllib.request.Request(URL, headers={"User-Agent": "cedrus-nrt"}), timeout=300).read()
    feed = pd.read_csv(io.BytesIO(raw), usecols=["latitude", "longitude", "acq_date", "confidence", "daynight"])
    dates = sorted(feed.acq_date.unique())
    if len(dates) < 3:
        raise SystemExit(f"the feed has only {len(dates)} dates")
    full = dates[1:-1]
    feed = feed[feed.acq_date.isin(full) & feed.confidence.astype(str).str.lower().isin(["n", "h", "nominal", "high"])]
    out = {"built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ"), "source": URL, "satellite": "NOAA-20 VIIRS (near real time)",
           "window": [full[0], full[-1]], "days": len(full), "regions": {}}
    for region, meta in REGIONS.items():
        npath = NORMALS / f"{region}_daily.json"
        if "product" not in meta["roles"] or not npath.exists():
            continue
        normal = json.loads(npath.read_text(encoding="utf-8"))
        if len(normal["years"]) < MIN_YEARS:  # no fair normal yet: leave the region out rather than show a bare count
            print(f"{region}: normal has only {len(normal['years'])} years, left out"); continue
        static = {tuple(s) for s in json.loads((NORMALS / f"{region}_static.json").read_text(encoding="utf-8"))}
        df = clip(feed, region, rings_for(region))
        sx, sy = squares(df); df = df.assign(sx=sx, sy=sy)
        keep = np.array([(x, y) not in static for x, y in zip(sx, sy)], dtype=bool)  # an empty list would select columns
        df = df[keep].drop_duplicates(["sx", "sy", "acq_date", "daynight"])
        now = int(len(df))
        md = [(int(d[5:7]), int(d[8:10])) for d in full]
        per_year = {}
        for y in normal["years"]:
            days = normal["days"][str(y)]
            # 29 Feb in a year without one counts as 28 Feb, so every year sums the same number of days
            per_year[str(y)] = int(sum(days[date(y, m, 28 if (m == 2 and d == 29 and not calendar.isleap(y)) else d).timetuple().tm_yday - 1] for m, d in md))
        vals = list(per_year.values())
        entry = {"now": now, "years": per_year}
        if len(vals) >= MIN_YEARS:
            entry.update(median=st.median(vals), q1=quantile(vals, 0.25), q3=quantile(vals, 0.75), low=min(vals), high=max(vals))
        cells = df.groupby([np.floor(df.longitude / 0.25), np.floor(df.latitude / 0.25)]).size()
        entry["points"] = [[round((x + 0.5) * 0.25, 3), round((y + 0.5) * 0.25, 3), int(n)] for (x, y), n in cells.items()]
        out["regions"][region] = entry
        print(f"{region}: {now} burning days {full[0]}..{full[-1]}; normal {entry.get('median', 'n/a')} ({len(vals)} years)")
    (ROOT / "web" / "data" / "nrt.json").write_text(json.dumps(out), encoding="utf-8")


if __name__ == "__main__":
    main()
