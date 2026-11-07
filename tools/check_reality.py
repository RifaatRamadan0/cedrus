"""Reality check: does our fire calendar agree with what officially happened on the ground?

Compares the app's own data (web/data/<region>/monthly_bd.json and monthly.json, exactly what the website shows)
with two sheets a person fills in from official sources:

  analysis/reality/official_yearly.csv  one row per country and year: officially reported burned area
  analysis/reality/known_fires.csv      one row per documented big fire: where, when, how big, the source

    python tools/check_reality.py

It writes analysis/reality/REPORT.md and charts in analysis/reality/figures/. Nothing here depends on how the
harmonization works: re-run it after any change to the data and the report updates itself.
Rules it uses are the app's own: the normal month is the median of the same calendar month from 2003 to the
year before (at least 5 years); a flare-up is at least 2.5x that median where the median is at least 20.
"""
import argparse
import csv
import json
import math
import statistics as st
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web" / "data"
UNITS = {"burning days": "monthly_bd.json", "hotspots": "monthly.json"}
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
BASELINE_FIRST, MIN_YEARS, FLARE, FLARE_MIN = 2003, 5, 2.5, 20


def load_regions():
    idx = json.loads((WEB / "regions.json").read_text(encoding="utf-8"))
    aliases = {}
    for region in idx["regions"]:
        for alias in (region["id"], region["name"]):
            key = alias.strip().casefold()
            if key in aliases and aliases[key]["id"] != region["id"]:
                raise ValueError(f"Ambiguous region alias: {alias}")
            aliases[key] = region
    return aliases


def capture_report(fires, regions, out):
    """Exact record capture within explicit scratch date/box windows; no anomaly test."""
    results = []
    for event in fires:
        meta = regions[event["country"].strip().casefold()]
        start, end = date.fromisoformat(event["start_date"]), date.fromisoformat(event["end_date"])
        box = [float(event[k]) for k in ("lon_min", "lat_min", "lon_max", "lat_max")]
        if not event.get("source_url") or start > end or box[0] >= box[2] or box[1] >= box[3]:
            raise ValueError("Capture input needs source, ordered dates and an explicit valid box")
        result = dict(region=meta["id"], place=event["place"], start=str(start), end=str(end),
                      box=box, source_url=event["source_url"], notes=event.get("notes", ""), units={})
        for unit, folder in (("hotspots", "hotspots"), ("burning_days", "burning")):
            n = 0; weight = 0.; dates = set(); sensors = {}
            for year in range(start.year, end.year+1):
                path = WEB / meta["id"] / folder / f"{year}.json"
                if not path.exists():
                    raise ValueError(f"Missing input for capture: {path}")
                data = json.loads(path.read_text()); c = data["cols"]
                for i in range(data["n"]):
                    day = date(year,1,1)+timedelta(days=c["doy"][i]-1)
                    if not start <= day <= end: continue
                    lon, lat = ((data["x0"]+c["x"][i]+.5)*.01, (data["y0"]+c["y"][i]+.5)*.01) if unit=="burning_days" else (c["lon"][i],c["lat"][i])
                    if box[0] <= lon < box[2] and box[1] <= lat < box[3]:
                        n += 1; weight += c["w"][i]; dates.add(str(day))
                        sensor = (["MODIS", "Suomi NPP", "NOAA-20"][c["fam"][i]] if unit=="burning_days" else ["Terra", "Aqua", "Suomi NPP", "NOAA-20"][c["sensor"][i]])
                        sensors[sensor] = sensors.get(sensor,0)+1
            result["units"][unit] = dict(records=n, weight_sum=weight, dates=sorted(dates), by_sensor=sensors, capture=n>0)
        results.append(result)
    (out / "capture.json").write_text(json.dumps(results,indent=2)+"\n",encoding="utf-8")
    lines = ["# Known-event capture check", "", "Capture only: records in explicit analyst-selected date/box windows. These boxes are not official fire perimeters. Overlap supports capture but does not attribute every detection to that event or validate estimated intensity. Weights exclude background. No flare-up test or burned-area equivalence is asserted.", "",
             "| Event | Dates checked | Hotspot records | Burning-day records | Capture |", "|---|---|---:|---:|---|"]
    for r in results:
        lines.append(f"| {r['place']} | {r['start']}–{r['end']} | {r['units']['hotspots']['records']} | {r['units']['burning_days']['records']} | {'Yes' if r['units']['hotspots']['capture'] else 'No'} |")
    lines += ["", "## Windows and sources", ""]
    for r in results:
        lines += [f"- **{r['place']}**: lon/lat box {r['box']}. [Verified event source]({r['source_url']}). {r['notes']}"]
    (out / "REPORT.md").write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(f"Wrote capture-only report: {out / 'REPORT.md'}")


class Record:
    """One region's monthly record in one unit, as the website has it."""

    def __init__(self, region_id, unit):
        d = json.loads((WEB / region_id / UNITS[unit]).read_text(encoding="utf-8"))
        self.y0, self.m0 = map(int, d["months"]["first"].split("-"))
        self.n = d["months"]["n"]
        self.cells = list(zip(d["cells"]["ix"], d["cells"]["iy"]))
        self.deg = d["cell_deg"]
        self.cell_m = d["m"]
        self.total = [sum(row[j] for row in d["m"]) for j in range(self.n)]
        self.naive = [sum(row[j] for row in d["naive"]) for j in range(self.n)]
        self.flags = d["flags"]

    def j(self, year, month):
        k = (year * 12 + month - 1) - (self.y0 * 12 + self.m0 - 1)
        return k if 0 <= k < self.n else None

    def year_total(self, year, naive=False):
        vals = [self.j(year, m) for m in range(1, 13)]
        if any(v is None or self.flags[v] == "X" for v in vals):
            return None  # only whole years are compared
        src = self.naive if naive else self.total
        return sum(src[v] for v in vals)

    def normal(self, year, month):
        vals = [self.total[k] for y in range(BASELINE_FIRST, year) if (k := self.j(y, month)) is not None and self.flags[k] != "X"]
        vals = [0 if v < 0.5 else v for v in vals]  # under 0.5 counts as zero, as in the app
        return (st.median(vals), len(vals)) if len(vals) >= MIN_YEARS else (None, len(vals))

    def rank(self, k):
        return 1 + sum(1 for v in self.total if v > self.total[k])

    def cell_at(self, lat, lon):
        key = (math.floor(lon / self.deg), math.floor(lat / self.deg))
        return self.cells.index(key) if key in self.cells else None


def read_sheet(path):
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f) if any((v or "").strip() for v in r.values())]
    return [{k.strip(): (v or "").strip() for k, v in r.items()} for r in rows]


def num(s):
    s = (s or "").replace(",", "").replace(" ", "")
    try:
        return float(s)
    except ValueError:
        return None


def spearman(a, b):
    def ranks(x):
        order = sorted(range(len(x)), key=lambda i: x[i]); r = [0.0] * len(x); i = 0
        while i < len(x):
            k = i
            while k + 1 < len(x) and x[order[k + 1]] == x[order[i]]:
                k += 1
            for t in range(i, k + 1):
                r[order[t]] = (i + k) / 2 + 1
            i = k + 1
        return r
    return pearson(ranks(a), ranks(b))


def pearson(a, b):
    ma, mb = st.mean(a), st.mean(b)
    sa = math.sqrt(sum((x - ma) ** 2 for x in a)); sb = math.sqrt(sum((y - mb) ** 2 for y in b))
    return sum((x - ma) * (y - mb) for x, y in zip(a, b)) / (sa * sb) if sa and sb else float("nan")


def words(r):
    a = abs(r)
    return "very strong" if a >= 0.8 else "strong" if a >= 0.6 else "moderate" if a >= 0.4 else "weak"


def chart_years(name, years, official, ours, naive, unit, out):
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return None
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.bar(years, official, color="#c9c2bb", label="Official burned area (ha)")
    ax.set_ylabel("Official burned area (hectares)")
    ax2 = ax.twinx()
    ax2.plot(years, ours, color="#e2622a", lw=2.5, marker="o", label=f"Our record ({unit})")
    ax2.plot(years, naive, color="#7a7a7a", lw=1.3, ls="--", label=f"Raw joined record ({unit})")
    ax2.set_ylabel(f"{unit} per year")
    ax.set_title(f"{name}: official burned area vs our fire calendar")
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    fig.legend(h1 + h2, l1 + l2, loc="lower center", ncol=3, fontsize=8, frameon=False)
    fig.tight_layout(rect=(0, 0.07, 1, 1))
    path = out / f"{name.lower().replace(' ', '_')}_{unit.replace(' ', '_')}_yearly.png"
    fig.savefig(path, dpi=130); plt.close(fig)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--official", default=str(ROOT / "analysis/reality/official_yearly.csv"))
    ap.add_argument("--fires", default=str(ROOT / "analysis/reality/known_fires.csv"))
    ap.add_argument("--capture-only", action="store_true", help="Scratch event date/box capture, without flare-up assessment")
    ap.add_argument("--out", default=str(ROOT / "analysis/reality"))
    a = ap.parse_args()
    out = Path(a.out); figs = out / "figures"; figs.mkdir(parents=True, exist_ok=True)
    regions = load_regions()
    official = read_sheet(Path(a.official)); fires = read_sheet(Path(a.fires))
    if a.capture_only:
        capture_report(fires, regions, out)
        return
    lines = [f"# Reality check: our fire calendar vs official records", "",
             f"Generated by `python tools/check_reality.py` on {date.today().isoformat()} from the website's own data files. "
             "Do not edit by hand: change the two sheets in this folder and run it again.", "",
             "Burning days and hotspots are not burned area: a burning day says a ~1 km square had a fire seen that day. "
             "So we expect them to **rise and fall together** with burned area, not to be equal.", ""]
    problems = []

    # ---- part 1: official yearly burned area vs our yearly totals
    lines += ["## 1. Years: do our big years match the official big years?", ""]
    by_country = {}
    for i, r in enumerate(official, start=2):
        c = r.get("country", "").strip().casefold(); y = num(r.get("year")); ha = num(r.get("burned_area_ha"))
        if c not in regions:
            problems.append(f"official_yearly.csv line {i}: country '{r.get('country')}' is not one of {', '.join(x.title() for x in regions)}"); continue
        if y is None or ha is None:
            problems.append(f"official_yearly.csv line {i}: year or burned_area_ha is not a number"); continue
        if not r.get("source_url"):
            problems.append(f"official_yearly.csv line {i}: no source_url (every number needs its source)")
        by_country.setdefault(regions[c]["id"].casefold(), {})[int(y)] = ha
    if not by_country:
        lines += ["_No rows yet in `official_yearly.csv`._", ""]
    for c, rows in by_country.items():
        name = regions[c]["name"]
        lines += [f"### {name}", ""]
        for unit in UNITS:
            rec = Record(regions[c]["id"], unit)
            ys = sorted(y for y in rows if rec.year_total(y) is not None)
            if len(ys) < 5:
                lines += [f"Only {len(ys)} usable years: at least 5 are needed for a comparison.", ""]; break
            off = [rows[y] for y in ys]; ours = [rec.year_total(y) for y in ys]; raw = [rec.year_total(y, naive=True) for y in ys]
            rs, rr = spearman(off, ours), spearman(off, raw)
            lines += [f"**{unit.title()}** ({len(ys)} years, {ys[0]}–{ys[-1]}): rank agreement with official burned area "
                      f"**{rs:.2f}** ({words(rs)}) for our record; {rr:.2f} for the raw joined record.", ""]
            top_off = sorted(ys, key=lambda y: -rows[y])[:5]; top_ours = sorted(ys, key=lambda y: -rec.year_total(y))[:5]
            both = [y for y in top_off if y in top_ours]
            lines += [f"Official top-5 years: {', '.join(map(str, top_off))}. Ours: {', '.join(map(str, top_ours))}. "
                      f"In both: {len(both)} of 5 ({', '.join(map(str, both)) or 'none'}).", ""]
            p = chart_years(name, ys, off, ours, raw, unit, figs)
            if p:
                lines += [f"![{name} {unit}](figures/{p.name})", ""]
            if unit == "burning days":
                lines += ["| Year | Official burned area (ha) | Our burning days | Raw joined record |", "|---|---:|---:|---:|"]
                lines += [f"| {y} | {rows[y]:,.0f} | {rec.year_total(y):,.0f} | {rec.year_total(y, naive=True):,.0f} |" for y in ys]
                lines += [""]

    # ---- part 2: documented big fires: did the calendar flag them?
    lines += ["## 2. Known big fires: did the calendar see them?", ""]
    if not fires:
        lines += ["_No rows yet in `known_fires.csv`._", ""]
    else:
        lines += ["| Fire | Month | Our burning days (whole region) | Normal for that month | × normal | Rank among all 301 months | Flagged ▲ | The fire's own 0.25° cell |",
                  "|---|---|---:|---:|---:|---:|:-:|---|"]
        flagged = 0; judged = 0
        for i, r in enumerate(fires, start=2):
            c = r.get("country", "").strip().casefold()
            if c not in regions:
                problems.append(f"known_fires.csv line {i}: country '{r.get('country')}' is not one of {', '.join(x.title() for x in regions)}"); continue
            try:
                d0 = date.fromisoformat(r.get("start_date", ""))
            except ValueError:
                problems.append(f"known_fires.csv line {i}: start_date must look like 2017-10-15"); continue
            if not r.get("source_url"):
                problems.append(f"known_fires.csv line {i}: no source_url (every fire needs its source)")
            rec = Record(regions[c]["id"], "burning days"); k = rec.j(d0.year, d0.month)
            if k is None:
                problems.append(f"known_fires.csv line {i}: {d0} is outside our record ({rec.y0}-{rec.m0:02d} to the end of 2025)"); continue
            v = rec.total[k]; med, n_years = rec.normal(d0.year, d0.month)
            ratio = v / med if med else None
            flag = "–" if med is None or med < FLARE_MIN else ("▲" if ratio >= FLARE else "no")
            if flag != "–":
                judged += 1; flagged += flag == "▲"
            cell = "–"
            lat, lon = num(r.get("lat")), num(r.get("lon"))
            if lat is not None and lon is not None:
                ci = rec.cell_at(lat, lon)
                if ci is None:
                    cell = "outside our grid"
                else:
                    month_vals = [row[k] for row in rec.cell_m]
                    cr = 1 + sum(1 for x in month_vals if x > month_vals[ci])
                    cell = f"{month_vals[ci]:,.0f} burning days, #{cr} of {len(month_vals)} cells that month"
            label = f"{r.get('place', '?')} ({regions[c]['name']}, {d0.isoformat()})"
            lines.append(f"| {label} | {MONTHS[d0.month - 1]} {d0.year} | {v:,.0f} | {'too few years' if med is None else f'{med:,.0f}'} | "
                         f"{'–' if ratio is None else f'{ratio:.1f}'} | {rec.rank(k)} | {flag} | {cell} |")
        lines += ["", f"Flagged as a flare-up: **{flagged} of {judged}** fires that could be judged "
                  f"(a fire can be judged when its month has at least {MIN_YEARS} earlier years from {BASELINE_FIRST} and a normal of {FLARE_MIN}+). "
                  "A big fire in an already-busy month may not be 2.5× the normal; the rank and the cell columns show whether it still stands out.", ""]

    lines += ["## 3. Sheet problems", ""] + ([f"- {p}" for p in problems] or ["None."]) + [""]
    lines += ["## Sources", "", "Every official number and every fire above comes from the `source_url` column of the two sheets.", ""]
    (out / "REPORT.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out / 'REPORT.md'}" + (f" ({len(problems)} sheet problem(s): see section 3)" if problems else ""))


if __name__ == "__main__":
    main()
