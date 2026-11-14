"""docs/ROUND3_CONFIRMATION.md from the round-3 results. Generated; do not edit by hand."""
from pathlib import Path

import pandas as pd

from pipeline.round2.report import disagree_table, f3, pct


CONFIRMATION_DEVIATIONS = [
    "1. **Entrant**: D-a, the tournament's C3 (FRP-class A2-style ratios) in the burning-day unit, as ruled in "
    "TOURNAMENT_PLAN.md (ruling added 1 Nov 2026). It is read from data/processed/tournament/frozen_round3.json, and "
    "the run refuses to start unless that file's SHA-256 is the one recorded at the freeze in "
    "TOURNAMENT_RESULTS.md. a is the file's frozen setting. The refit is "
    "`pipeline.tournament.candidates.fit(\"C3\", …, setting=a)`. Nothing is tuned.",
    "2. **Rows** are round 2's: cell × month × day/night from 2012-02, for every cell with a MODIS, Suomi NPP or "
    "NOAA-20 detection in 2012-02 … 2019-12. A cell first seen after 2019 has no row, so its detections are not "
    "scored. They are counted under Data below. **Unit**: the tournament's burning days. A 0.01° cell counts once per "
    "date and day/night if it has any detection of the family (MODIS = Terra and Aqua together). The cell-day counts "
    "are summed per row. A burning day takes the FRP class of its largest-FRP detection. Y, V and V20 and the class "
    "counts are all burning days.",
    "3. **Each region is fitted on its own rows only**, as a one-region table, so every fallback (\"all regions\") "
    "stays inside the region. D-a is fitted on 2012-02 … 2019-12. s for J-S is fitted on 2018-04 … 2019-12 in "
    "burning days. Each bootstrap is seeded with 20261101 plus a CRC32 of its label (\"round3\", region, use).",
    "4. **Outage rule**: round 2's. It is the bake-off rule over the included regions combined, on detections (the "
    "unit does not change which days are outages). Test 1, the seam check and the drift check leave out months with "
    "a MODIS day at 0 while Suomi NPP is ≥ 50, or the reverse. Test 2 uses no MODIS, so it leaves out months with a "
    "Suomi NPP day at 0 while NOAA-20 is ≥ 50, or the reverse. Fitting uses all months.",
    "5. **Test 1 (a)–(d)**: round 2's pass rules, with every quantity in burning days. \"At most F1's + 1.0 "
    "percentage point\" means WAPE ≤ F1's WAPE + 0.010. \"Below F0's\" is strict. **(c)**: |Σ predicted ÷ Σ observed "
    "MODIS burning days − 1| ≤ 0.10, pooled over the regions' Test 1 rows. **F0** is the raw Suomi NPP burning-day "
    "count. **F1** is R1's point forecast (round 2's `fit_ratio`, unchanged) fitted on the region's own 2012–2019 "
    "rows in burning days: r·V when V > 0, b when V = 0.",
    "6. **Coverage** is y in [q10, q90] on active rows (Y > 0 or V > 0). D-a's forecast is the sum of its class "
    "negative binomials, moment-matched to one negative binomial. V = 0 rows use Poisson(b_A). The split into "
    "active rows with V > 0 and with V = 0 (MODIS-only rows) is reported only.",
    "7. **Test 2 intervals** are round 2's: mean ± 1.2816·sd, with sd² = the summed row predictive variances plus "
    "the bootstrap variance of the total from s. D-a has no bootstrap of its own, as A2 in round 2. A region-month "
    "counts if both expected totals are ≥ 10 (burning days), and it agrees if the 80% intervals overlap. The share "
    "is pooled over the regions.",
    "8. **Seam check** uses Test 1's scored months. Its 80% interval is the summed row predictive variance.",
    "9. **Drift band**: monthly observed ÷ predicted MODIS burning days for 2012–2019. Each year is predicted by D-a "
    "refitted without that year, with the same a. The band is the 10th–90th percentile. Only months with a "
    "predicted total ≥ 10 count, and outage months are left out.",
    "10. **Swap metrics** (report only): |log(NOAA-20-based total ÷ Suomi NPP-based total)| over Test 2's "
    "region-months where both totals are > 0, as in the tournament. The median and the 90th percentile are "
    "reported, the 90th by numpy's linear interpolation. The same is shown where both are ≥ 10, and for the "
    "2020–2021 months alone (the tournament's window).",
    "11. **f0 check** (report only): a row's f0 part is the FRP ≤ 0 class's own term of D-a's class sum, "
    "V_f0·(a + SY_f0) ÷ (a ÷ r0_f0 + SV_f0); V = 0 rows have none. Summed per region-month, it is listed where it "
    "is more than 25% of the predicted total (total > 0). This is done on Test 1's rows (Suomi NPP) and on Test 2's "
    "rows (Suomi NPP-based and NOAA-20-based).",
    "12. **Raw folders**: data/raw/algeria and data/raw/france (FIRMS country files), data/raw/australia_sa and "
    "data/raw/usa_norcal (area-API box files). All four are clipped to the boxes in pipeline/regions.py.",
    "13. **Completeness**: the confirmation refuses to start unless every MODIS and Suomi NPP file for 2012–2025 and "
    "every NOAA-20 file for 2018–2025 is in each sealed region's manifest. A half-finished download therefore cannot "
    "use up the one run.",
]


def write_confirmation(r, path):
    p, s1, v1 = r["provenance"], r["test1"]["pooled"], r["test1"]["verdict"]
    s2, v2 = r["test2"]["pooled"], r["test2"]["verdict"]
    out = r["outages"]
    yes = lambda v: "**pass**" if v else "**fail**"
    L = ["# Round 3 confirmation: D-a (burning days) on the four round-3 sealed regions", "",
         f"_Generated {r['generated']} by `python -m pipeline.round3.confirm`. Rules: [TOURNAMENT_PLAN.md]"
         "(TOURNAMENT_PLAN.md) (pre-registered at commit fa2c956; the round-3 entrant by the ruling added 1 Nov 2026), "
         "with round 2's tests and pass rules ([ROUND2_PLAN.md](ROUND2_PLAN.md)) applied in burning days; entrant "
         "frozen in [TOURNAMENT_RESULTS.md](TOURNAMENT_RESULTS.md). Do not edit by hand._", ""]
    if not r["is_confirmation"]:
        L += ["**DEVELOPMENT RUN on development regions; this is not the confirmation.**", ""]
    same = "same as at the freeze" if p["code_hash_now"] == p["code_hash_frozen"] else "**differs from the freeze**"
    L += [f"- Entrant: **D-a + J-S** (C3, FRP-class A2-style ratios, in burning days; a = {r['frozen_a']}). "
          f"frozen_round3.json SHA-256 `{p['frozen_sha256']}` (checked); its tournament run "
          f"{p['frozen_generated']} at commit `{p['frozen_commit_at_run']}`.",
          f"- Tournament code hash now `{p['code_hash_now']}`, at the freeze `{p['code_hash_frozen']}` ({same}).",
          f"- Run started {r['started']} (UTC) at commit `{p['commit']}`"
          + (" with uncommitted files under pipeline/ (listed at the end)." if p["uncommitted"] else "."),
          "- Unit: burning days, for the model, MODIS, F0 and F1. Windows: Test 1 2020–2021. Test 2 2020-01 … 2025-12. "
          "Seam 2020–2021. Drift 2022–2025 against 2012–2019.",
          f"- Invocations of this kind logged in data/processed/round3/confirm_runs.jsonl before this report: "
          f"{sum(1 for x in r['runs_logged'] if x['event'] == 'start')} started, "
          f"{sum(1 for x in r['runs_logged'] if x['event'] == 'finish')} finished (this run's finish line is written "
          "right after the report).", "",
          f"## Overall: **{r['overall']}**", ""]
    if r["failing"]:
        L += ["Failing parts: " + "; ".join(r["failing"]) + ".", ""]
    L += [f"Regions included ({len(r['regions'])}): {', '.join(r['regions'])}."]
    if r["left_out"]:
        L.append("Left out, 2012–2019 files incomplete: "
                 + "; ".join(f"{k} ({', '.join(v[:6])})" for k, v in r["left_out"].items()) + ".")
    if r["missing"] and not r["is_confirmation"]:
        L.append("Files not on disk (those region-years are left out of the tests that need them): "
                 + "; ".join(f"{k}: {len(v)}" for k, v in r["missing"].items()) + ".")
    L += ["", "| Part | Needed | Got | |", "|---|---|---|---|",
          f"| Test 1 (a): cell-month WAPE ≤ F1 + 1.0 point and < F0 | ≤ {pct(s1['wape_cm_F1'] + 0.01)} and < "
          f"{pct(s1['wape_cm_F0'])} | {pct(s1['wape_cm_M'])} | {yes(v1['a'])} |",
          f"| Test 1 (b): 80% coverage on active rows | 0.70 … 0.90 | {f3(s1['cov_active_M'])} | {yes(v1['b'])} |",
          f"| Test 1 (c): pooled predicted total ÷ observed MODIS burning days | 0.90 … 1.10 | "
          f"{f3(s1['total_ratio_M'])} ({s1['total_M']:,.0f} ÷ {s1['Y']:,}) | {yes(v1['c'])} |",
          f"| Test 1 (d): national-month WAPE ≤ F1 + 1.0 point | ≤ {pct(s1['wape_nm_F1'] + 0.01)} | "
          f"{pct(s1['wape_nm_M'])} | {yes(v1['d'])} |",
          f"| Test 2: share of counted region-months whose 80% intervals overlap | ≥ 0.80 | {f3(s2['share'])} "
          f"({s2['agree']} of {s2['counted']}) | {yes(v2['pass'])} |", ""]

    L += ["## Deviations / interpretations", "",
          "Points the plan left open, settled by the most literal reading when the code was written (on development "
          "regions only, before any sealed file was read).", ""] + CONFIRMATION_DEVIATIONS + [""]

    L += ["## Test 1: accuracy against near-nominal MODIS, 2020–2021, in burning days", "",
          f"Fit on 2012-02 … 2019-12, scored on 2020–2021 months without an outage day: {s1['rows']:,} rows "
          f"({s1['active_rows']:,} active), {s1['Y']:,} MODIS burning days. Months left out: "
          f"{', '.join(m for m in out['months_modis_snpp'] if '2020' <= m <= '2021-12') or 'none'}.", "",
          f"| Forecast | Cell-month WAPE | National-month WAPE | Predicted total (observed {s1['Y']:,}) |",
          "|---|---|---|---|"]
    for k, name in (("M", "D-a, frozen model"), ("F0", "F0 raw Suomi NPP burning days"),
                    ("F1", "F1 R1's point forecast, burning days")):
        L.append(f"| {name} | {pct(s1[f'wape_cm_{k}'])} | {pct(s1[f'wape_nm_{k}'])} | {s1[f'total_{k}']:,.0f} |")
    L += ["", f"D-a only: weighted CRPS {f3(s1['wcrps_M'])}, 80% coverage on active rows {pct(s1['cov_active_M'])} "
          f"(all rows, for information: {pct(s1['cov_all_M'])}).", "",
          "Report only, coverage of active rows split by Suomi NPP:", "",
          "| Active rows | Rows | 80% coverage |", "|---|---|---|",
          f"| V > 0 | {s1['active_vpos']:,} | {pct(s1['cov_vpos_M'])} |",
          f"| V = 0 (MODIS only) | {s1['active_vzero']:,} | {pct(s1['cov_vzero_M'])} |", "", "By region:", "",
          "| Region | Rows | Active | MODIS (Y) | Cell-month WAPE model | F0 | F1 | National-month WAPE model | F0 | F1 "
          "| Predicted ÷ observed | Weighted CRPS | Coverage, active rows | Coverage, active V > 0 | Coverage, active V = 0 |",
          "|---" * 15 + "|"]
    for k, s in r["test1"]["per_region"].items():
        L.append(f"| {k} | {s['rows']:,} | {s['active_rows']:,} | {s['Y']:,} | {pct(s['wape_cm_M'])} | {pct(s['wape_cm_F0'])} "
                 f"| {pct(s['wape_cm_F1'])} | {pct(s['wape_nm_M'])} | {pct(s['wape_nm_F0'])} | {pct(s['wape_nm_F1'])} "
                 f"| {f3(s['total_ratio_M'])} | {f3(s['wcrps_M'])} | {pct(s['cov_active_M'])} | {pct(s['cov_vpos_M'])} "
                 f"| {pct(s['cov_vzero_M'])} |")
    L += ["", "D-a's fit per region: " + "; ".join(
        f"{k} a {v['a']}, map evaluations {v['em_iterations']}, last relative change {v['em_delta']:.1e}, converged "
        f"{v['em_converged']}, r0 groups on fallback {v['r0_groups_on_fallback']}" for k, v in r["info"].items()) + ".",
        "", "F1 per region (r day / night; b day / night): " + "; ".join(
        f"{k} {v['F1_r']['D']:.3f} / {v['F1_r']['N']:.3f}; {v['F1_b']['D']:.3f} / {v['F1_b']['N']:.3f}"
        for k, v in r["info"].items()) + ".", ""]

    m2 = pd.DataFrame(r["test2"]["months"])
    L += ["## Test 2: satellite swap, 2020–2025, in burning days", "",
          "Suomi NPP: D-a fitted on 2012-02 … 2019-12. NOAA-20: J-S, s fitted on 2018-04 … 2019-12. Months left "
          f"out (outage): {', '.join(out['months_swap']) or 'none'}.", "",
          f"Pooled: {s2['region_months']} region-months, **{s2['counted']} counted, {s2['agree']} agree "
          f"({pct(s2['share'])})**.", "",
          "| Region | Region-months | Counted | Agree | Share | Σ Suomi NPP-based | Σ NOAA-20-based |",
          "|---|---|---|---|---|---|---|"]
    for k, s in r["test2"]["per_region"].items():
        g = m2[m2.region == k] if len(m2) else m2
        tS = g.tot_S.sum() if len(g) else 0.0
        tN = g.tot_N.sum() if len(g) else 0.0
        L.append(f"| {k} | {s['region_months']} | {s['counted']} | {s['agree']} | {pct(s['share'])} | {tS:,.0f} | {tN:,.0f} |")
    if len(m2):
        m2["year"] = m2.ym.str[:4]
        L += ["", "By region and year (counted / agree):", "",
              "| Region | " + " | ".join(str(y) for y in range(2020, 2026)) + " |", "|---|" + "---|" * 6]
        for k in r["regions"]:
            g = m2[m2.region == k]
            cells = []
            for y in range(2020, 2026):
                gy = g[(g.year == str(y)) & g.counted]
                cells.append(f"{len(gy)} / {int(gy.agree.sum())}")
            L.append(f"| {k} | " + " | ".join(cells) + " |")
        L += ["", "Counted region-months that disagree (counts are burning days):", ""] \
            + disagree_table(r["test2"]["months"], "J-S") + [""]
    L += ["s per region, burning days (sd from the month-block bootstrap): " + "; ".join(
        f"{k} day {v['s']['D']:.3f} ({v['sd_s']['D']:.3f}), night {v['s']['N']:.3f} ({v['sd_s']['N']:.3f})"
        for k, v in r["info"].items() if "s" in v) + ".", ""]

    sm = r["swap_metrics"]
    L += ["## Report only: swap metrics, |log(NOAA-20-based ÷ Suomi NPP-based)|", "",
          "Per region-month of Test 2. On development data (2020–2021, both totals > 0), D-a's median was 0.108 "
          "(TOURNAMENT_RESULTS.md, burning-day leaderboard) and its 90th percentile 0.46 (same file, independent "
          "test).", "",
          "| Regions | Window | Both > 0 | Median | 90th percentile | Maximum | Both ≥ 10 | Median | 90th percentile |",
          "|---|---|---|---|---|---|---|---|---|"]
    for lab, s in [("all regions", sm["all"]), ("all regions", sm["2020-2021"])] + list(sm["per_region"].items()):
        win = "2020–2021" if s is sm["2020-2021"] else "2020–2025"
        L.append(f"| {lab} | {win} | {s['used_pos']} | {f3(s['median_pos'])} | {f3(s['p90_pos'])} | {f3(s['max_pos'])} "
                 f"| {s['used_ge10']} | {f3(s['median_ge10'])} | {f3(s['p90_ge10'])} |")
    L += [""]

    f0 = r["f0"]
    fl = pd.DataFrame(f0["flagged"])
    L += ["## Report only: the f0 (FRP ≤ 0) tail risk", "",
          "The independent test recorded that the FRP ≤ 0 class has an unstable ratio, and that one such burning day "
          "inside a big fire can add a lot to a row. This lists the region-months where the f0 part is more than "
          f"{f0['threshold']:.0%} of D-a's predicted total. Test 1, pooled: the f0 part is {pct(f0['test1_share'])} of "
          "the predicted total.", "",
          "Region-months with a predicted total > 0: " + "; ".join(f"{k} {v}" for k, v in f0["region_months"].items())
          + ".", ""]
    if not len(fl):
        L += ["None.", ""]
    else:
        L += ["| Where | Region | Month | Predicted total | f0 part | Share | Observed MODIS | Satellite burning days | of which FRP ≤ 0 |",
              "|---|---|---|---|---|---|---|---|---|"]
        for _, x in fl.iterrows():
            obs = "" if x.Y != x.Y else f"{int(x.Y):,}"
            L.append(f"| {x.source} | {x.region} | {x.ym} | {x.pred:,.1f} | {x.f0:,.1f} | {pct(x.share)} | {obs} "
                     f"| {x.V:,.1f} | {x.class_f0:,.1f} |")
        L += [""]

    L += ["## Report only: seam check, 2020 and 2021", "",
          "Harmonized (D-a's predicted MODIS burning days from Suomi NPP) ÷ observed MODIS burning days, with the 80% "
          "interval.", "",
          "| Region | Year | Observed MODIS | Harmonized | Ratio | 80% interval of the ratio |", "|---|---|---|---|---|---|"]
    for x in r["seam"]:
        y = x["Y"]
        rat = (lambda v: f"{v / y:.3f}") if y else (lambda v: "n/a")
        L.append(f"| {x['region']} | {int(x['year'])} | {int(y):,} | {x['pred']:,.0f} | {rat(x['pred'])} "
                 f"| {rat(x['lo'])} … {rat(x['hi'])} |")
    L += [""]

    d = pd.DataFrame(r["drift"])
    L += ["## Report only: drift divergence, 2022–2025", "",
          "Monthly observed MODIS burning days ÷ D-a's prediction from Suomi NPP. The 2012–2019 band is the 10th–90th "
          "percentile of the same ratio, leave-one-year-out.", "",
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
            L.append(f"| {k} | {lo:.2f} … {hi:.2f} ({med:.2f}) | {y} | {len(g)} | {g.ratio.median():.2f} "
                     f"| {int((g.ratio < lo).sum())} | {int((g.ratio > hi).sum())} |")
    L += [""]

    L += ["## Data", "", "| Region | Cells | Detections 2020–2025 in cells with rows (MODIS / Suomi NPP / NOAA-20) "
          "| Burning days 2020–2025 on rows (MODIS / Suomi NPP / NOAA-20) | Detections in cells without rows (not scored) |",
          "|---|---|---|---|---|"]
    for k in r["regions"]:
        c, b = r["cover"][k], r["bd_cover"][k]
        fmt = lambda dct: " / ".join(f"{dct.get('terra', 0) + dct.get('aqua', 0):,}" if s == "modis" else
                                     f"{dct.get(s, 0):,}" for s in ("modis", "snpp", "noaa20"))
        L.append(f"| {k} | {c['cells']:,} | {fmt(c['inside'])} | {b['Yb']:,} / {b['Vb']:,} / {b['V20b']:,} "
                 f"| {fmt(c['outside'])} |")
    L += ["", f"Outage days: MODIS {', '.join(out['modis']) or 'none'}; Suomi NPP (vs MODIS) {', '.join(out['snpp']) or 'none'}; "
          f"Suomi NPP (vs NOAA-20) {', '.join(out['snpp_vs_noaa20']) or 'none'}; NOAA-20 {', '.join(out['noaa20']) or 'none'}.", ""]
    if p["uncommitted"]:
        L += ["Uncommitted under pipeline/round3/, tournament/, round2/ or bakeoff/ at run time:", "", "```",
              p["uncommitted"], "```", ""]
    L += ["Invocations of this kind logged before this report:", ""]
    L += [f"- {x['event']} {x['at']} regions {', '.join(x['regions'])}" + (f" → {x['overall']}" if "overall" in x else "")
          for x in r["runs_logged"]] or ["- none"]
    L += ["", "## Timings", "", "| Stage | Seconds |", "|---|---|"]
    L += [f"| {k} | {v:.0f} |" for k, v in r["timings_s"].items()] + [""]
    Path(path).write_text("\n".join(L), encoding="utf-8")
