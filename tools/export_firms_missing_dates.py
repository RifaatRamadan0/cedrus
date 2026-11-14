"""Write web/data/firms_missing_dates.json: the dates FIRMS itself lists as missing standard data, per satellite.

    python tools/export_firms_missing_dates.py

Source: the snapshot of FIRMS's missing-data service saved by tools/query_firms_coverage.py
(analysis/tier1/coverage_services/missing_data.txt). Only the standard-data columns are used; the near-real-time
columns are not. The list is global per satellite: it says FIRMS's database lacks standard data for that satellite
on that date, not which places are affected, and a date that is not listed is not proof of complete coverage.
The map names these dates, as FIRMS-reported missing data rather than independently verified outages, in a month
whose value relies on that satellite (web/app.js, gapNote).

FIRMS's list is the only trigger: an empty day in our own detection files is never treated as an outage. The files are
used only the other way round, as a consistency check. A listed date on which our standard files for that satellite
hold detections (in any region we have) contradicts the list, so it is kept in the output under `contradicted` and
does not produce a warning. On 6 November 2026 that was Suomi NPP, 1-31 May 2026: listed as missing, while the
standard files hold a full month of Suomi NPP detections (version 2, distinct from NOAA-20's).
"""
import hashlib
import json
import sys
from glob import glob
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from summarize_firms_coverage import OUT as SNAPSHOTS, Table  # noqa: E402

SATELLITE = {"Terra (MODIS)": "T", "Aqua (MODIS)": "A", "Suomi NPP (VIIRS)": "N", "NOAA-20 (VIIRS)": "J1"}
STEM = {"T": "modis", "A": "modis", "N": "viirs-snpp", "J1": "viirs-jpss1"}


def detections_on(sat, dates):
    """{date: detections} in every standard country file we hold (data/raw/<region>/), for the listed dates only."""
    want, out = set(dates), {}
    for year in sorted({d[:4] for d in dates}):
        for f in glob(str(ROOT / "data/raw" / "*" / f"{STEM[sat]}_{year}_*.csv")):
            df = pd.read_csv(f, usecols=lambda c: c in ("acq_date", "satellite"), dtype=str)
            if sat in ("T", "A"):
                df = df[df.satellite.str.upper().str[0] == sat[0]]
            for d, n in df.acq_date[df.acq_date.isin(want)].value_counts().items():
                out[d] = out.get(d, 0) + int(n)
    return out


def main():
    path = SNAPSHOTS / "missing_data.txt"
    raw = path.read_bytes()
    sha = hashlib.sha256(raw).hexdigest()
    request = next(r for r in json.loads((SNAPSHOTS / "requests.json").read_text(encoding="utf-8"))
                   if r["service"] == "missing_data")
    if request.get("sha256") != sha:
        raise SystemExit("missing_data.txt differs from the snapshot recorded in requests.json")
    response = json.loads(raw.decode("utf-8"))
    table = Table()
    table.feed(response["html"])
    if not response["success"] or len(table.rows) != response["rowCount"]:
        raise SystemExit("unexpected missing-data response")
    dates = {k: set() for k in SATELLITE.values()}
    for row in table.rows:
        if len(row) != 4:
            raise SystemExit(f"unexpected row {row}")
        # First pair: standard data (used). Second pair: near-real-time data (not used).
        if row[0] and row[1] in SATELLITE:
            dates[SATELLITE[row[1]]].add(row[0])
    contradicted = {}
    for sat in dates:
        seen = detections_on(sat, dates[sat])
        contradicted[sat] = {d: seen[d] for d in sorted(seen)}
        dates[sat] -= set(seen)
    out = {
        "source": "NASA FIRMS missing-data service, standard-data columns only",
        "service": "https://firms.modaps.eosdis.nasa.gov/api/missing_data/",
        "retrieved": request["retrieved"],
        "snapshot": "analysis/tier1/coverage_services/missing_data.txt",
        "snapshot_sha256": sha,
        "scope": "global per satellite: FIRMS lacks standard data for that satellite on that date; not specific to "
                 "any place, and an unlisted date does not certify complete coverage",
        "satellites": {"T": "Terra MODIS", "A": "Aqua MODIS", "N": "Suomi NPP VIIRS", "J1": "NOAA-20 VIIRS"},
        "dates": {k: sorted(v) for k, v in dates.items()},
        "contradicted_note": "listed by FIRMS, but our standard files for that satellite hold detections on that date "
                             "(count shown); not used for warnings",
        "contradicted": contradicted,
    }
    dest = ROOT / "web/data/firms_missing_dates.json"
    dest.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"{dest.relative_to(ROOT)}: " + ", ".join(f"{k} {len(v)}" for k, v in out["dates"].items())
          + f" dates used (snapshot {request['retrieved'][:10]}); contradicted: "
          + ", ".join(f"{k} {len(v)}" for k, v in contradicted.items()))


if __name__ == "__main__":
    main()
