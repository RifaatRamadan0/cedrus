"""Read-only web-file inventory and La Rioja demo diagnostics."""
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "analysis/tier1"
NEW = ("syria", "jordan", "cyprus", "la_rioja")


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)


def main():
    files = [ROOT / "web/data/regions.json"] + [p for r in NEW for p in sorted((ROOT / "web/data" / r).rglob("*.json"))]
    inventory = [{"file": str(p.relative_to(ROOT)).replace("\\", "/"), "bytes": p.stat().st_size,
                  "decimal_MB": p.stat().st_size/1e6, "over_3_MB": p.stat().st_size > 3000000,
                  "sha256": hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    write_csv(OUT / "web_file_inventory.csv", inventory)
    index = json.loads((ROOT / "web/data/regions.json").read_text())
    meta = {r["id"]: r for r in index["regions"]}
    units = {}
    zero = {}
    for rid in ("la_rioja", "lebanon"):
        for unit, folder, filename in (("hotspots", "hotspots", "monthly.json"), ("burning_days", "burning", "monthly_bd.json")):
            mon = json.loads((ROOT / "web/data" / rid / filename).read_text())
            y0, m0 = map(int, mon["months"]["first"].split("-"))
            months = [f"{(y0*12+m0-1+j)//12}-{(y0*12+m0-1+j)%12+1:02d}" for j in range(mon["months"]["n"])]
            flags = dict(zip(months, mon["flags"])); counts = Counter(); zero_count = used = 0
            for path in (ROOT / "web/data" / rid / folder).glob("*.json"):
                f = json.loads(path.read_text()); c = f["cols"]
                for i in range(f["n"]):
                    month = (date(f["year"], 1, 1)+timedelta(days=c["doy"][i]-1)).isoformat()[:7]
                    counts[month] += 1
                    if unit == "burning_days" and month >= "2022-01":
                        sats = {"E": [1,2], "N": [1], "J": [2]}.get(flags[month], [])
                        allowed = meta[rid]["burning_days"]["combination"]["slots_when_both_cover"][month[5:]+("N" if c["dn"][i] else "D")]
                        positive = [s for s in sats if ("snpp" if s==1 else "noaa20") in allowed]
                        if c["fam"][i] in (positive or sats):
                            used += 1; zero_count += c["w"][i] == 0
            if unit == "burning_days":
                zero[rid] = dict(contributing_viirs_burning_days=used, zero_weight=zero_count, share=zero_count/used)
                assert used == meta[rid]["burning_days"]["zero_weight"]["viirs_burning_days"]
                assert zero_count == meta[rid]["burning_days"]["zero_weight"]["weight_zero"]
            if rid != "la_rioja": continue
            rows = [{"month": month, "exported_records_all_satellites": counts[month],
                     "harmonized_estimate": sum(row[j] for row in mon["m"]) if flags[month] != "X" else None,
                     "source_flag": flags[month], "monthly_completeness": "unknown"} for j, month in enumerate(months)]
            write_csv(OUT / f"la_rioja_monthly_{unit}.csv", rows)
            yearly = []
            for year in sorted(set(m[:4] for m in months)):
                group = [r for r in rows if r["month"].startswith(year)]
                yearly.append(dict(year=int(year), months_in_record=len(group), records_all_satellites=sum(r["exported_records_all_satellites"] for r in group),
                                   harmonized_estimate=sum(r["harmonized_estimate"] for r in group) if all(r["harmonized_estimate"] is not None for r in group) else None,
                                   complete_calendar_year=len(group)==12, monthly_completeness="unknown"))
            write_csv(OUT / f"la_rioja_yearly_{unit}.csv", yearly)
            units[unit] = dict(records=sum(counts.values()), empty_record_months=[m for m in months if counts[m]==0],
                busiest_record_months=sorted(rows,key=lambda r:-r["exported_records_all_satellites"])[:10],
                busiest_estimate_months=sorted([r for r in rows if r["harmonized_estimate"] is not None],key=lambda r:-r["harmonized_estimate"])[:10])
    report = dict(file_count=len(inventory), total_bytes=sum(f["bytes"] for f in inventory),
                  files_over_3_MB=[f for f in inventory if f["over_3_MB"]], record=meta["la_rioja"]["months"],
                  units=units, zero_weight_comparison=zero,
                  definition="Counts are satellite detections or family/square/date/day-night burning-day records, not distinct incidents. Estimates are MODIS-equivalent. No direct accuracy validation after 2021.")
    (OUT / "la_rioja_demo.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:report[k] for k in ("file_count","total_bytes","files_over_3_MB","zero_weight_comparison")},indent=2))


if __name__ == "__main__": main()
