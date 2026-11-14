"""Monthly evidence ledger; global date metadata does not certify country coverage."""
import calendar
import csv
import json
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis/tier1/coverage_services"


class Table(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows = []; self.row = []; self.cell = None
    def handle_starttag(self, tag, attrs):
        if tag == "tr": self.row = []
        if tag == "td": self.cell = ""
    def handle_data(self, data):
        if self.cell is not None: self.cell += data
    def handle_endtag(self, tag):
        if tag == "td": self.row.append(self.cell.strip()); self.cell = None
        if tag == "tr": self.rows.append(self.row)


def main():
    response = json.loads((OUT / "missing_data.txt").read_text())
    assert response["success"]
    table = Table(); table.feed(response["html"])
    assert len(table.rows) == response["rowCount"]
    dates = {}
    for row in table.rows:
        assert len(row) == 4
        # First pair is standard data. The second pair is NRT, deliberately excluded.
        if row[0]: dates.setdefault(row[1], set()).add(row[0])
    mapping = {"Terra (MODIS)": "MODIS_SP", "Aqua (MODIS)": "MODIS_SP",
               "Suomi NPP (VIIRS)": "VIIRS_SNPP_SP", "NOAA-20 (VIIRS)": "VIIRS_NOAA20_SP"}
    spans = {}
    for dataset in set(mapping.values()):
        with (OUT / f"{dataset}.txt").open(newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1 and rows[0]["data_id"] == dataset
        spans[dataset] = rows[0]
    result = []
    for satellite, dataset in mapping.items():
        lo, hi = spans[dataset]["min_date"], spans[dataset]["max_date"]
        for year in range(2000, 2026):
            for month in range(1, 13):
                ym = f"{year}-{month:02d}"
                first, last = ym+"-01", ym+f"-{calendar.monthrange(year, month)[1]:02d}"
                relation = "outside" if last < lo or first > hi else "partial_date_span" if first < lo or last > hi else "inside"
                missing = sorted(d for d in dates.get(satellite, ()) if d.startswith(ym))
                result.append(dict(satellite=satellite, product=dataset, month=ym,
                    product_min_date=lo, product_max_date=hi, product_date_span_relation=relation,
                    global_missing_standard_dates=";".join(missing), global_missing_day_count=len(missing),
                    global_gap_evidence="known_missing_data" if missing else "no_listed_gap",
                    country_month_completeness="unknown",
                    evidence_limitation="Global product extent and missing-day table do not certify spatial completeness of country archives; MODIS extent combines Terra and Aqua."))
    with (OUT / "satellite_month_evidence.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(result[0])); writer.writeheader(); writer.writerows(result)
    summary = {"products": spans, "monthly_rows": len(result), "country_month_completeness": "unknown",
               "standard_table_rows": sum(len(v) for v in dates.values()), "satellites": {}}
    for satellite in mapping:
        relevant = [d for d in dates.get(satellite, ()) if "2000-01-01" <= d <= "2025-12-31"]
        summary["satellites"][satellite] = {"missing_dates_2000_2025": len(relevant), "months": dict(sorted(Counter(d[:7] for d in relevant).items()))}
    (OUT / "summary.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
