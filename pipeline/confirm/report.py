"""docs/CONFIRMATION_RESULTS.md from the confirmation results. Generated; do not edit by hand."""
from pathlib import Path

import numpy as np
import pandas as pd

NAMES = {"A": "A, frozen model (a = 30)", "F0": "F0 raw Suomi NPP count (floor)",
         "F1": "F1 one ratio per region × day/night (floor)"}


def pct(x):
    return "n/a" if x != x else f"{x * 100:.1f}%"


def f3(x):
    return "n/a" if x != x else f"{x:.3f}"


def write_report(r, path):
    p, s1, v1 = r["provenance"], r["test1"]["pooled"], r["test1"]["verdict"]
    s2, v2 = r["test2"]["pooled"], r["test2"]["verdict"]
    out = r["outages"]
    yes = lambda v: "**pass**" if v else "**fail**"
    unchanged = not p["bakeoff_diff_vs_frozen"]
    L = ["# Confirmation results: the frozen model on the four sealed regions", "",
         f"_Generated {r['generated']} by `python -m pipeline.confirm.run`. "
         "Rules: [CONFIRMATION_PLAN.md](CONFIRMATION_PLAN.md), pre-registered at commit 0cdcdd6 before any sealed data "
         "was downloaded. Do not edit by hand._", ""]
    if not r["is_confirmation"]:
        L += ["**DEVELOPMENT RUN on development regions; this is not the confirmation.**", ""]
    L += ["```bash", "python -m pipeline.confirm.run", "```", "",
          f"- Run started {r['started']} (UTC); repository commit `{p['commit']}`"
          + (" with uncommitted changes under pipeline/ (listed at the end)." if p["uncommitted_in_pipeline"] else "."),
          f"- Model A code in `pipeline/bakeoff/` is {'unchanged since' if unchanged else 'DIFFERENT from'} "
          f"commit f0823f9 (`git diff --stat f0823f9 -- pipeline/bakeoff` is "
          f"{'empty' if unchanged else 'not empty'}).",
          "- Test windows: Test 1 scores 2020–2021. Test 2 compares 2020–2025. "
          "Seam check: 2020–2021. Drift check: 2022–2025 against 2012–2019.",
          f"- Confirmation invocations logged in data/processed/confirm/runs.jsonl: "
          f"{sum(1 for x in r['runs_logged'] if x['event'] == 'start')} started, "
          f"{sum(1 for x in r['runs_logged'] if x['event'] == 'finish')} finished before this report was written "
          "(this run's finish line is written right after it).", ""]
    L += [f"## Overall: **{r['overall']}**", ""]
    if r["failing"]:
        L += ["Failing parts: " + "; ".join(r["failing"]) + ".", ""]
    L += [f"Regions included ({len(r['regions'])}): {', '.join(r['regions'])}."]
    if r["left_out"]:
        L.append("Left out, files incomplete when this ran: " + "; ".join(
            f"{k} ({len(v)} files missing: {', '.join(v[:6])}{' …' if len(v) > 6 else ''})"
            for k, v in sorted(r["left_out"].items())) + ".")
    L += ["", "| Part | Needed | Got | |", "|---|---|---|---|",
          f"| Test 1 (a): A's cell-month WAPE below F1's and F0's | A < {pct(s1['wape_cm_F1'])} and A < "
          f"{pct(s1['wape_cm_F0'])} | {pct(s1['wape_cm_A'])} | {yes(v1['a_wape_beats_floors'])} |",
          f"| Test 1 (b): 80% coverage on active rows | 0.70 … 0.90 | {f3(s1['cov_active_A'])} "
          f"| {yes(v1['b_active_coverage_0.70_0.90'])} |",
          f"| Test 2: share of counted region-months whose 80% intervals overlap | ≥ 0.80 | {f3(s2['share'])} "
          f"({s2['agree']} of {s2['counted']}) | {yes(v2['pass'])} |", ""]

    L += ["## Deviations / interpretations", "",
          "Points the plan left open, settled by the most literal reading before any result was seen.", "",
          "1. **Rows** are the bake-off's: cell × month × day/night from 2012-02, for every cell with a MODIS or VIIRS "
          "detection in 2012-02 … 2019-12. NOAA-20 detections in 2018–2019 count as VIIRS here. A cell first seen "
          "after 2019 has no row, so its detections are not scored. They are counted under Data below.",
          "2. **Each region is fitted on its own rows only**, as a one-region table, so A's last-resort fallback "
          "(\"all regions\") is that region itself.",
          "3. **Outage rule**: the bake-off rule per family, over the included regions combined. Test 1, the seam "
          "check and the drift check leave out months with a MODIS or Suomi NPP outage day. Test 2 does not use "
          "MODIS. It leaves out months with an outage day for Suomi NPP or for NOAA-20, where a NOAA-20 outage day "
          "means NOAA-20 had 0 while MODIS had ≥ 50 (the plan does not name a NOAA-20 rule). Fitting uses all months, "
          "as in the bake-off.",
          "4. **Test 2 intervals** are mean ± 1.2816·√(summed variance), a normal approximation, not clipped at 0. "
          "The sum covers every row of the region-month, so it includes the Poisson(b_A) rows where the VIIRS count "
          "is 0 (variance b_A) as well as the negative-binomial rows. The NOAA-20 fit uses 2018-04 … 2019-12 rows only.",
          "5. **A's V = 0 quirk is kept** (BAKEOFF_RESULTS, independent test). Every row with no VIIRS detection "
          "still predicts b_A, in Test 1 and in both Test 2 totals.",
          "6. **Coverage** is as in the bake-off: y inside [q10, q90], with q the smallest k where F(k) ≥ 0.1 or 0.9. "
          "Only active rows (Y > 0 or V > 0) count for (b). All-row coverage is shown for information.",
          "7. **F1**'s ratio is ΣY/ΣV over the 2012-02 … 2019-12 rows of the region, per day/night. "
          "**Weighted CRPS** uses w = 1 + the cell's mean Y over the same rows.",
          "8. **Seam check** uses Test 1's scored months. Its interval is the same normal 80% interval.",
          f"9. **Drift band**: monthly observed ÷ predicted for 2012–2019, each year predicted by A refitted without "
          f"that year (leave-one-year-out), so the band is out of sample like 2022–2025. Band = 10th–90th percentile. "
          f"Only months whose predicted total is ≥ {r['min_total']} are used, and outage months are left out.",
          "10. **Raw folders** for Central Chile and Western Cape are data/raw/chile and data/raw/south_africa, "
          "clipped to the boxes in pipeline/regions.py.", ""]

    L += ["## Test 1: accuracy against near-nominal MODIS, 2020–2021", "",
          f"Fit on 2012-02 … 2019-12, scored on every 2020–2021 month without an outage day: {s1['rows']:,} rows "
          f"({s1['active_rows']:,} active), {s1['Y']:,} MODIS detections. "
          f"Months left out: {', '.join(m for m in out['months_modis_snpp'] if m >= '2020') or 'none'}.", "",
          "| Model | Cell-month WAPE | National-month WAPE | Predicted total (observed " + f"{s1['Y']:,}) |",
          "|---|---|---|---|"]
    for m in ("A", "F0", "F1"):
        L.append(f"| {NAMES[m]} | {pct(s1[f'wape_cm_{m}'])} | {pct(s1[f'wape_nm_{m}'])} | {s1[f'total_{m}']:,.0f} |")
    L += ["", f"A only: weighted CRPS {f3(s1['wcrps_A'])}, CRPS {f3(s1['crps_A'])}, 80% coverage on active rows "
          f"{pct(s1['cov_active_A'])} (all rows, for information: {pct(s1['cov_all_A'])}).", "", "By region:", "",
          "| Region | Rows | Active | MODIS (Y) | Cell-month WAPE A | F0 | F1 | National-month WAPE A | F0 | F1 "
          "| Weighted CRPS A | Coverage, active rows |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for k, s in r["test1"]["per_region"].items():
        L.append(f"| {k} | {s['rows']:,} | {s['active_rows']:,} | {s['Y']:,} | {pct(s['wape_cm_A'])} "
                 f"| {pct(s['wape_cm_F0'])} | {pct(s['wape_cm_F1'])} | {pct(s['wape_nm_A'])} | {pct(s['wape_nm_F0'])} "
                 f"| {pct(s['wape_nm_F1'])} | {f3(s['wcrps_A'])} | {pct(s['cov_active_A'])} |")
    L += [""]

    m2 = pd.DataFrame(r["test2"]["months"])
    L += ["## Test 2: satellite swap, 2020–2025", "",
          "A fitted on Suomi NPP (2012-02 … 2019-12) and on NOAA-20 (2018-04 … 2019-12), each against MODIS. Each "
          "region-month gets two MODIS-equivalent totals, with 80% intervals. They agree if the intervals overlap. "
          f"A region-month is counted only if both totals are ≥ {r['min_total']}. "
          f"Months left out (outage): {', '.join(m for m in out['months_snpp_noaa20'] if m >= '2020') or 'none'}.", "",
          f"Pooled: {s2['region_months']} region-months, **{s2['counted']} counted, {s2['agree']} agree "
          f"({pct(s2['share'])})**.", "",
          "| Region | Region-months | Counted | Agree | Share | Σ Suomi NPP-based total | Σ NOAA-20-based total |",
          "|---|---|---|---|---|---|---|"]
    for k, s in r["test2"]["per_region"].items():
        g = m2[m2.region == k]
        L.append(f"| {k} | {s['region_months']} | {s['counted']} | {s['agree']} | {pct(s['share'])} "
                 f"| {g.tot_S.sum():,.0f} | {g.tot_N.sum():,.0f} |")
    L += ["", "By region and year (counted / agree):", "",
          "| Region | " + " | ".join(str(y) for y in range(2020, 2026)) + " |", "|---|" + "---|" * 6]
    m2["year"] = m2.ym.str[:4]
    for k in r["regions"]:
        g = m2[m2.region == k]
        cells = []
        for y in range(2020, 2026):
            gy = g[(g.year == str(y)) & g.counted]
            cells.append(f"{len(gy)} / {int(gy.agree.sum())}")
        L.append(f"| {k} | " + " | ".join(cells) + " |")
    dis = m2[m2.counted & ~m2.agree]
    L += ["", "Counted region-months that disagree:", ""]
    if len(dis):
        L += ["| Region | Month | Suomi NPP-based (80% interval) | NOAA-20-based (80% interval) | Suomi NPP count | NOAA-20 count |",
              "|---|---|---|---|---|---|"]
        for _, x in dis.iterrows():
            L.append(f"| {x.region} | {x.ym} | {x.tot_S:,.1f} ({x.lo_S:,.1f} … {x.hi_S:,.1f}) "
                     f"| {x.tot_N:,.1f} ({x.lo_N:,.1f} … {x.hi_N:,.1f}) | {int(x.V):,} | {int(x.V20):,} |")
    else:
        L.append("None.")
    L += [""]

    L += ["## Report only: seam check, 2020 and 2021", "",
          "Harmonized (A's predicted MODIS total from Suomi NPP) ÷ observed MODIS, per year, with the 80% interval.", "",
          "| Region | Year | Observed MODIS | Harmonized | Ratio | 80% interval of the ratio |", "|---|---|---|---|---|---|"]
    for x in r["seam"]:
        y = x["Y"]
        rat = (lambda v: f"{v / y:.3f}") if y else (lambda v: "n/a")
        L.append(f"| {x['region']} | {int(x['year'])} | {int(y):,} | {x['mean_A']:,.0f} | {rat(x['mean_A'])} "
                 f"| {rat(x['lo'])} … {rat(x['hi'])} |")
    L += [""]

    d = pd.DataFrame(r["drift"])
    L += ["## Report only: drift divergence, 2022–2025", "",
          "Monthly observed MODIS ÷ A's prediction from Suomi NPP. The 2012–2019 band is the 10th–90th percentile of "
          "the same ratio, computed leave-one-year-out.", "",
          "| Region | 2012–2019 band (median) | Year | Months used | Median ratio | Months below band | Months above band |",
          "|---|---|---|---|---|---|---|"]
    for k in r["regions"]:
        b = r["drift_band"].get(k)
        if b is None:
            L.append(f"| {k} | no 2012–2019 month with predicted ≥ {r['min_total']} | | | | | |")
            continue
        lo, med, hi = (b.get(q, b.get(str(q))) for q in (0.1, 0.5, 0.9))
        for y in range(2022, 2026):
            g = d[(d.region == k) & (d.year == y)] if len(d) else d
            if not len(g):
                L.append(f"| {k} | {lo:.2f} … {hi:.2f} ({med:.2f}) | {y} | 0 | | | |")
                continue
            L.append(f"| {k} | {lo:.2f} … {hi:.2f} ({med:.2f}) | {y} | {len(g)} | {np.median(g.ratio):.2f} "
                     f"| {int((g.ratio < lo).sum())} | {int((g.ratio > hi).sum())} |")
    L += [""]

    L += ["## Data", "", "| Region | Cells | Detections 2020–2025 in cells with rows (MODIS / Suomi NPP / NOAA-20) "
          "| Detections 2020–2025 in cells without rows (not scored) |", "|---|---|---|---|"]
    for k in r["regions"]:
        c = r["cover"][k]
        fmt = lambda dct: " / ".join(f"{dct.get('terra', 0) + dct.get('aqua', 0):,}" if s == "modis" else
                                     f"{dct.get(s, 0):,}" for s in ("modis", "snpp", "noaa20"))
        L.append(f"| {k} | {c['cells']:,} | {fmt(c['inside'])} | {fmt(c['outside'])} |")
    L += ["", f"Outage days: MODIS {', '.join(out['modis']) or 'none'}; Suomi NPP {', '.join(out['snpp']) or 'none'}; "
          f"NOAA-20 {', '.join(out['noaa20']) or 'none'}.", "",
          "Model A code fingerprints (SHA-256, first 16 hex): "
          + ", ".join(f"`{k}` {v}" for k, v in p["bakeoff_sha256"].items()) + ".", ""]
    if p["uncommitted_in_pipeline"]:
        L += ["Uncommitted under pipeline/ at run time:", "", "```", p["uncommitted_in_pipeline"], "```", ""]
    L += ["Confirmation invocations logged before this report:", ""]
    L += [f"- {x['event']} {x['at']} regions {', '.join(x['regions'])}" + (f" → {x['overall']}" if "overall" in x else "")
          for x in r["runs_logged"]] or ["- none"]
    L += ["", "## Timings", "", "| Stage | Seconds |", "|---|---|"]
    L += [f"| {k} | {v:.0f} |" for k, v in r["timings_s"].items()] + [""]
    Path(path).write_text("\n".join(L), encoding="utf-8")
