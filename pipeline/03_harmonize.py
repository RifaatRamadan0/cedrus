"""The MODIS retirement test, exactly as written in docs/TEST_PLAN.md.

    python pipeline/03_harmonize.py

Fits on 2012-02..2019-12, scores on 2020-01..2025-12, compares CEDRUS (M1)
with the two floors (F0 joined record, F1 one ratio). Writes
    data/processed/<country>/ratios.csv   r(cell, month-of-year) for the website
    data/processed/<country>/results.json
    docs/RESULTS.md
"""
import argparse
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from common import ROOT

TRAIN = ("2012-02", "2019-12")
TEST = ("2020-01", "2025-12")
K_GRID = [10, 30, 100, 300]


def monthly_table(daily):
    d = daily.assign(month=daily.date.str[:7])
    t = d.pivot_table(index=["cell", "month"], columns="sensor", values="count",
                      aggfunc="sum", fill_value=0).reset_index()
    for s in ["terra", "aqua", "snpp", "noaa20", "noaa21"]:
        if s not in t:
            t[s] = 0
    t["modis"] = t.terra + t.aqua
    t["moy"] = t.month.str[5:7].astype(int)
    t["year"] = t.month.str[:4].astype(int)
    return t


def between(t, span):
    return t[(t.month >= span[0]) & (t.month <= span[1])]


def fit_m1(train, k, v="snpp"):
    """r(cell, moy) shrunk towards the national ratio for that calendar month."""
    nat = train.groupby("moy")[["modis", v]].sum()
    r_m = (nat.modis / nat[v].replace(0, np.nan)).fillna(1.0)
    cm = train.groupby(["cell", "moy"])[["modis", v]].sum().reset_index()
    cm["r"] = (cm.modis + k * cm.moy.map(r_m)) / (cm[v] + k)
    return r_m, cm.set_index(["cell", "moy"]).r


def predict_m1(rows, r_m, r_cm, v="snpp"):
    idx = pd.MultiIndex.from_arrays([rows.cell, rows.moy])
    r = pd.Series(r_cm.reindex(idx).values, index=rows.index)
    r = r.fillna(rows.moy.map(r_m))  # cells never seen in training get the national ratio
    return rows[v] * r


def wape(pred, truth):
    return float(np.abs(pred - truth).sum() / truth.sum())


def season_dates(daily_counts):
    """Day-of-year when 10 / 50 / 90 % of the year's detections are reached."""
    out = {}
    for year, s in daily_counts.groupby(daily_counts.index.year):
        c = s.sort_index().cumsum()
        if c.iloc[-1] <= 0:
            continue
        frac = c / c.iloc[-1]
        out[year] = [int(frac.index[np.argmax(frac.values >= q)].dayofyear) for q in (.1, .5, .9)]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--country", default="Portugal")
    args = ap.parse_args()
    proc = ROOT / "data" / "processed" / args.country.lower()
    daily = pd.read_csv(proc / "daily_cells.csv")
    t = monthly_table(daily)
    train, test = between(t, TRAIN), between(t, TEST)

    # --- choose k by leave-one-year-out inside the training years only
    loyo = {}
    for k in K_GRID:
        err = tot = 0.0
        for y in sorted(train.year.unique()):
            r_m, r_cm = fit_m1(train[train.year != y], k)
            held = train[train.year == y]
            err += np.abs(predict_m1(held, r_m, r_cm) - held.modis).sum()
            tot += held.modis.sum()
        loyo[k] = float(err / tot)
    k = min(loyo, key=loyo.get)

    # --- fit on all training years, score on held-out years
    r_m, r_cm = fit_m1(train, k)
    r_one = train.modis.sum() / train.snpp.sum()
    preds = {
        "F0": test.snpp.astype(float),
        "F1": test.snpp * r_one,
        "M1": predict_m1(test, r_m, r_cm),
    }
    primary = {m: wape(p, test.modis) for m, p in preds.items()}

    yearly = {}
    for m, p in preds.items():
        g = pd.DataFrame({"p": p, "y": test.year, "t": test.modis}).groupby("y").sum()
        yearly[m] = {int(y): round(float((r.p - r.t) / r.t * 100), 1) for y, r in g.iterrows()}
    nat_monthly = {}
    for m, p in preds.items():
        g = pd.DataFrame({"p": p, "mo": test.month, "t": test.modis}).groupby("mo").sum()
        nat_monthly[m] = wape(g.p, g.t)

    # --- season dates from daily national counts
    d = daily.assign(date=pd.to_datetime(daily.date))
    nat_daily = d.pivot_table(index="date", columns="sensor", values="count", aggfunc="sum", fill_value=0)
    nat_daily = nat_daily.reindex(pd.date_range(TEST[0] + "-01", "2025-12-31"), fill_value=0)
    truth_d = nat_daily.get("terra", 0) + nat_daily.get("aqua", 0)
    v_d = nat_daily["snpp"]
    pred_d = {"F0": v_d, "F1": v_d * r_one, "M1": v_d * v_d.index.month.map(r_m).values}
    true_dates = season_dates(truth_d)
    season = {}
    for m, p in pred_d.items():
        pd_dates = season_dates(p)
        diffs = [abs(a - b) for y in true_dates if y in pd_dates for a, b in zip(true_dates[y], pd_dates[y])]
        season[m] = round(float(np.mean(diffs)), 1)

    # --- Terra and Aqua separately: detections per Suomi NPP detection, by year
    yr = t.groupby("year")[["terra", "aqua", "snpp", "noaa20"]].sum()
    drift = {int(y): {"terra_per_snpp": round(r.terra / r.snpp, 3) if r.snpp else None,
                      "aqua_per_snpp": round(r.aqua / r.snpp, 3) if r.snpp else None}
             for y, r in yr.iterrows() if y >= 2012}

    # --- secondary: same model, NOAA-20 instead of Suomi NPP
    both = test[(test.noaa20 > 0) | (test.snpp > 0)]
    n20_months = sorted(set(daily[daily.sensor == "noaa20"].date.str[:7]))
    handover = None
    if n20_months:
        rows = both[both.month.isin(n20_months)]
        handover = {
            "months": [n20_months[0], n20_months[-1]],
            "M1_on_snpp": wape(predict_m1(rows, r_m, r_cm, "snpp"), rows.modis),
            "M1_on_noaa20": wape(predict_m1(rows, r_m, r_cm.rename(None), "noaa20"), rows.modis),
            "noaa20_per_snpp": round(float(rows.noaa20.sum() / rows.snpp.sum()), 3),
        }

    passed = primary["M1"] < primary["F0"] and primary["M1"] < primary["F1"]
    results = {
        "generated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "plan": "docs/TEST_PLAN.md", "train": TRAIN, "test": TEST,
        "k_loyo": loyo, "k": k, "one_ratio": round(float(r_one), 4),
        "month_ratio": {int(m): round(float(v), 4) for m, v in r_m.items()},
        "primary_wape": primary, "national_monthly_wape": nat_monthly,
        "yearly_total_error_pct": yearly, "season_date_error_days": season,
        "sensor_drift": drift, "handover_noaa20": handover, "passed": passed,
        "train_detections": {"modis": int(train.modis.sum()), "snpp": int(train.snpp.sum())},
        "test_detections": {"modis": int(test.modis.sum()), "snpp": int(test.snpp.sum())},
    }
    (proc / "results.json").write_text(json.dumps(results, indent=1))
    r_cm.rename("r").reset_index().to_csv(proc / "ratios.csv", index=False)
    write_report(results)
    print(json.dumps({k_: results[k_] for k_ in ("k", "primary_wape", "season_date_error_days", "passed")}, indent=1))


def write_report(r):
    pct = lambda x: f"{x * 100:.1f}%"
    names = {"F0": "F0 joined record (floor)", "F1": "F1 one ratio (floor)", "M1": "M1 CEDRUS"}
    years = sorted(next(iter(r["yearly_total_error_pct"].values())))
    lines = [
        "# Results — the MODIS retirement test", "",
        f"_Generated {r['generated']} by `pipeline/03_harmonize.py`. Rules: [TEST_PLAN.md](TEST_PLAN.md)._", "",
        f"**Verdict: {'PASS' if r['passed'] else 'FAIL'}** — M1 must beat both floors on the primary score.", "",
        f"Trained on {r['train'][0]}..{r['train'][1]} ({r['train_detections']['modis']:,} MODIS, "
        f"{r['train_detections']['snpp']:,} Suomi NPP detections). Scored on {r['test'][0]}..{r['test'][1]} "
        f"({r['test_detections']['modis']:,} MODIS detections to rebuild). k = {r['k']} (chosen on training years).", "",
        "| Model | Cell-month error (primary) | National monthly error | Season dates off by (days) |",
        "|---|---|---|---|",
    ]
    for m in ("F0", "F1", "M1"):
        lines.append(f"| {names[m]} | {pct(r['primary_wape'][m])} | {pct(r['national_monthly_wape'][m])} "
                     f"| {r['season_date_error_days'][m]} |")
    lines += ["", "## Yearly national total, % error (predicted vs real MODIS)", "",
              "| Model | " + " | ".join(map(str, years)) + " |", "|---|" + "---|" * len(years)]
    for m in ("F0", "F1", "M1"):
        lines.append(f"| {m} | " + " | ".join(f"{r['yearly_total_error_pct'][m][y]:+.1f}" for y in years) + " |")
    lines += ["", "## Terra and Aqua drift — MODIS detections per Suomi NPP detection", "",
              "| Year | Terra | Aqua |", "|---|---|---|"]
    for y, v in r["sensor_drift"].items():
        lines.append(f"| {y} | {v['terra_per_snpp']} | {v['aqua_per_snpp']} |")
    h = r["handover_noaa20"]
    lines += ["", "## Satellite handover — same model fed NOAA-20 instead of Suomi NPP", ""]
    if h:
        lines += [f"Months with NOAA-20 in the archive: {h['months'][0]}..{h['months'][1]}. "
                  f"NOAA-20 makes {h['noaa20_per_snpp']} detections per Suomi NPP detection.", "",
                  f"- Cell-month error fed Suomi NPP: {pct(h['M1_on_snpp'])}",
                  f"- Cell-month error fed NOAA-20: {pct(h['M1_on_noaa20'])}"]
    else:
        lines.append("No NOAA-20 data in the archive for the held-out years.")
    lines += ["", "## Notes", "",
              "- Season-date scores for F0 and F1 are identical by construction: multiplying a record by one "
              "number does not move the dates when 10/50/90 % of the year's fires are reached.",
              "- Numbers are fire *detections* (satellite pixels flagged as burning), not burned area.", ""]
    (ROOT / "docs" / "RESULTS.md").write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    main()
