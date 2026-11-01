"""docs/ROUND2_SELECTION.md and docs/ROUND2_CONFIRMATION.md from the round-2 results. Generated; do not edit by hand."""
from pathlib import Path

import pandas as pd

from .models import MODELS

NAMES = {"R1": "R1 one ratio per region × day/night", "Rm": "Rm one ratio per region × calendar month × day/night",
         "A2": "A2 model A, V = 0 quirk removed"}


def f3(x):
    return "n/a" if x != x else f"{x:.3f}"


def pct(x):
    return "n/a" if x != x else f"{x * 100:.1f}%"


def spct(x):
    return "n/a" if x != x else f"{x * 100:+.1f}%"


MODEL_HEAD = ["| Model | Weighted CRPS (primary) | CRPS | 80% coverage, active rows | 80% coverage, all rows (information) "
              "| Cell-month WAPE | National-month WAPE | Total bias | Predicted total |",
              "|---|---|---|---|---|---|---|---|---|"]


def model_rows(s):
    return [f"| {NAMES[m]} | {f3(s[f'wcrps_{m}'])} | {f3(s[f'crps_{m}'])} | {pct(s[f'cov_active_{m}'])} "
            f"| {pct(s[f'cov_all_{m}'])} | {pct(s[f'wape_cm_{m}'])} | {pct(s[f'wape_nm_{m}'])} | {spct(s[f'bias_{m}'])} "
            f"| {s[f'total_{m}']:,.0f} |" for m in MODELS]


def split_table(first, items):
    L = [f"| {first} | Rows | Active | MODIS (Y) | Weighted CRPS R1 | Rm | A2 | Coverage (active) R1 | Rm | A2 "
         "| Cell-month WAPE R1 | Rm | A2 | National-month WAPE R1 | Rm | A2 | Total bias R1 | Rm | A2 |",
         "|---" * 19 + "|"]
    for name, s in items:
        L.append(f"| {name} | {s['rows']:,} | {s['active_rows']:,} | {s['Y']:,} | "
                 + " | ".join(f3(s[f"wcrps_{m}"]) for m in MODELS) + " | "
                 + " | ".join(pct(s[f"cov_active_{m}"]) for m in MODELS) + " | "
                 + " | ".join(pct(s[f"wape_cm_{m}"]) for m in MODELS) + " | "
                 + " | ".join(pct(s[f"wape_nm_{m}"]) for m in MODELS) + " | "
                 + " | ".join(spct(s[f"bias_{m}"]) for m in MODELS) + " |")
    return L


def disagree_table(months, label):
    d = pd.DataFrame(months)
    d = d[d.counted & ~d.agree]
    if not len(d):
        return ["None."]
    L = [f"| Region | Month | Suomi NPP-based (80% interval) | NOAA-20-based, {label} (80% interval) | Suomi NPP count "
         "| NOAA-20 count |", "|---|---|---|---|---|---|"]
    for _, x in d.iterrows():
        L.append(f"| {x.region} | {x.ym} | {x.tot_S:,.1f} ({x.lo_S:,.1f} … {x.hi_S:,.1f}) "
                 f"| {x.tot_N:,.1f} ({x.lo_N:,.1f} … {x.hi_N:,.1f}) | {int(x.V):,} | {int(x.V20):,} |")
    return L


SELECTION_DEVIATIONS = [
    "1. **Rows** run 2012-02 … 2019-12 for fitting and scoring (Suomi NPP's first full month, as in the bake-off), and "
    "2020-01 … 2021-12 for the swap only. A region's cells are every 0.25° cell with a MODIS, Suomi NPP or NOAA-20 "
    "detection in 2012-02 … 2019-12. NOAA-20 is a VIIRS instrument, so it counts here (the bake-off read Suomi NPP "
    "only; round 1's confirmation counted NOAA-20 too). Each region's files are clipped to its box in "
    "pipeline/regions.py. The spent regions' raw folders are data/raw/chile and data/raw/south_africa. Only files for "
    "2012–2021 are read, even where later years are on disk.",
    "2. **Outage rule, stage 1**: the bake-off's own code (`pipeline.bakeoff.data.outages`), over all included "
    "regions combined. Months with an outage day are left out of every score, including A2's inner tuning. Fitting "
    "uses all months, as in the bake-off.",
    "3. **Outage rule, swap**: the plan says the swap uses no MODIS, so the bake-off rule is applied to the two "
    "satellites being compared. A Suomi NPP outage day has Suomi NPP at 0 while NOAA-20 has ≥ 50, and a NOAA-20 "
    "outage day is the reverse. Regions are combined. A region-year with a missing file is left out of this count, "
    "so the missing file cannot look like an outage. Round 1's confirmation used MODIS ≥ 50 here instead.",
    "4. **R1 / Rm ratio and b**: r = ΣY/ΣV over training rows with V > 0, per group. b = mean Y over training rows "
    "with V = 0, per group. A group with no such row falls back to region × day/night (Rm only), then to all "
    "regions × day/night, as A does. Fallback use is counted per fold below.",
    "5. **α (R1 and Rm)**: NB2 (variance μ + αμ²). It is fitted by maximum likelihood per region × day/night, with "
    "every training row's mean held at its fitted r·V or b, over log α in [−20, 6] (the bake-off's bounds). Rows with "
    "mean 0 carry no information and are dropped from that fit. Rm keeps α per region × day/night, because the plan "
    "moves only the ratio and b to calendar months. The same α applies to V = 0 rows, which are NB(b, α).",
    "6. **Var(r̂)**: the variance (ddof 1) of r over 200 year-block bootstrap resamples. The blocks are the training "
    "years of that fit: 7 in a leave-one-year-out fold, 5 in the forward check, 8 for the final fit. The same "
    "fallbacks apply inside each resample. The plan's term V²·Var(r̂) is 0 when V = 0, so rows with V = 0 carry no "
    "parameter term, and b's own uncertainty is not added.",
    "7. **R1 / Rm predictive distribution for CRPS and coverage**: the negative binomial with the row's mean μ and "
    "variance σ² = μ + αμ² + V²·Var(r̂), moment-matched as size = μ²/(σ² − μ) and p = μ/σ². If σ² ≤ μ(1 + 10⁻⁹), it "
    "is Poisson(μ). If μ = 0, all the mass is at 0. CRPS is the bake-off's exact sum.",
    "8. **A2**: \"the ratio sums\" are read as every ΣY of A: the prior r0 = ΣY/ΣV per region × calendar month × "
    "day/night, and the cell sums in the posterior shape a + ΣY. Both are taken over rows with V > 0. ΣV is "
    "unchanged. Rows with V = 0 keep A's distribution, Poisson(b_A). b_A is the same quantity as Rm's b: the mean Y "
    "over training rows with V = 0 per region × calendar month × day/night, falling back to region × day/night. "
    "Where r0 = 0 the forecast is all mass at 0, as in A. a is chosen from {10, 30, 100, 300, 1000} by inner "
    "leave-one-year-out (weighted CRPS, weights from the inner training years, ties to the smaller a). A2 is built "
    "by calling the bake-off's `fit_A` / `predict_A` on a table whose Y is 0 on V = 0 rows. b_A is taken from a "
    "second `fit_A` call on the real Y.",
    "9. **Primary score and rule**: weighted CRPS with w = 1 + the cell's mean Y over the fold's training rows. "
    "\"Pooled\" is read as the leave-one-year-out pool (2012 … 2019 held out in turn), as in the bake-off's decision. "
    "The rule \"within 2% of the best\" is weighted CRPS ≤ 1.02 × the best. The forward check is reported and does "
    "not enter the rule.",
    "10. **Reported scores**: coverage is y in [q10, q90] on active rows (Y > 0 or V > 0); all-row coverage is shown "
    "for information. Cell-month WAPE adds day and night per cell × month before taking |error|; national-month "
    "WAPE is per region × month. Both are divided by ΣY. Total bias = Σ predicted ÷ Σ observed − 1.",
    "11. **Suomi NPP fit for stage 2** is the chosen model refitted on all 2012-02 … 2019-12 rows of the development "
    "regions. If A2 were chosen, its a would come from leave-one-year-out over the eight years.",
    "12. **J-M** fits the chosen method to NOAA-20 against MODIS on 2018-04 … 2019-12. \"The same method\" is read "
    "literally, so Var(r̂) is again a year-block bootstrap, and that window has only two year-blocks (2018, 2019). "
    "J-M's parameter variance is therefore a rough estimate. A2's a would be tuned by leave-one-year-out over "
    "2018/2019.",
    "13. **J-S**: s = ΣV_SNPP/ΣV_N20 per region × day/night over every row of 2018-04 … 2019-12. Var(s) comes from "
    "200 resamples of the 21 month-blocks. The chosen Suomi NPP model is applied to s·V20 (which need not be a whole "
    "number), with the Suomi NPP fit's α.",
    "14. **Intervals of a region-month total**: mean ± 1.2816·sd (normal, not clipped at 0). sd² = the summed "
    "NB (or Poisson) variances of the rows + the bootstrap variance of the total itself. The second term is the "
    "variance over replicates of Σ k·r*·s*: r* is year-block (R1/Rm), s* is month-block (J-S), and the two are "
    "drawn independently and paired by replicate index. All rows sharing an r (or s) move together within a "
    "replicate. The plan's row formula V²·Var(r̂) does not say how rows combine in a sum. Adding each row's term "
    "separately would treat a shared parameter as independent, so it is not done. r and s are treated as "
    "independent, although both use Suomi NPP 2018–2019. With A2 there is no r bootstrap: A's posterior already "
    "sits in each row's variance.",
    "15. **Counting and agreement**: a region-month counts if both expected totals (the S-NPP-based one and that "
    "method's NOAA-20-based one) are ≥ 10. J-S and J-M are counted separately, so their counted sets can differ. "
    "It agrees if the two closed 80% intervals overlap. J-S is chosen if its share ≥ J-M's share.",
    "16. **Seeds**: every bootstrap draws from numpy's default_rng, seeded with 20261101 plus a CRC32 of its label "
    "(fold, model), so a re-run gives the same numbers.",
]


def write_selection(r, path):
    o, d, n20 = r["overall"], r["decision"], r["n20"]
    yes = lambda v: "**yes**" if v else "no"
    full = r["full_run"]
    L = ["# Round 2 selection: R1 / Rm / A2 and the NOAA-20 method (development regions only)", "",
         f"_Generated {r['generated']} by `python -m pipeline.round2.select`. Rules: [ROUND2_PLAN.md](ROUND2_PLAN.md), "
         "pre-registered at commit e7763f7 before any round-2 code. Do not edit by hand._", ""]
    if not full:
        L += ["**DEVELOPMENT SUBSET; this is not the selection.**", ""]
    L += ["```bash", "python -m pipeline.round2.select", "```", "",
          f"- Run started {r['started']} (UTC) at commit `{r['commit']}`"
          + (" with uncommitted files under pipeline/round2/ (this code is not committed yet)." if r["uncommitted_round2"]
             else "."),
          f"- **Chosen: {r['decision']['chosen']} + {n20['chosen']}.** Suomi NPP model {NAMES[d['chosen']]}; NOAA-20 "
          f"method {n20['chosen']}.",
          f"- Regions included ({len(r['regions'])}): {', '.join(r['regions'])}.",
          "- No sealed region (central_spain, southern_italy, sw_australia, s_california) was opened. Every file access "
          "goes through `pipeline.round2.data.guard`, which refuses sealed regions.",
          "- Before the first full run, the code was run once on a development subset (portugal, lebanon, turkey; "
          "`--regions`, output in data/processed/round2/selection_subset.md) to debug it. After that run, and after the "
          "first full run, only report wording and the fields written to frozen.json changed; no fitting or scoring "
          "code, rule or setting did. This file is a re-run of the same seeded code.", ""]
    if r["left_out"]:
        L += ["Left out, files incomplete: " + "; ".join(f"{k} ({', '.join(v)})" for k, v in r["left_out"].items()) + ".", ""]
    if r["missing_swap"]:
        L += ["Missing for the swap window (those region-years are not in the swap): "
              + "; ".join(f"{k}: {', '.join(v)}" for k, v in r["missing_swap"].items()) + ".", ""]

    L += ["## Deviations / interpretations", "",
          "Points where the plan was silent or open to more than one reading. Each was settled by the most literal "
          "reading while the code was written, before any score was seen.", ""] + SELECTION_DEVIATIONS + [""]

    L += ["## Decision 1: the Suomi NPP model", "",
          f"Pooled leave-one-year-out (2012 … 2019), weighted CRPS. Best: {d['best']} ({f3(o['wcrps_' + d['best']])}); "
          f"bar = 1.02 × best = {f3(d['bar'])}. Rule: the simplest candidate within 2% of the best, in the order "
          "R1 < Rm < A2.", "",
          "| Order | Candidate | Pooled weighted CRPS | ÷ best | Within 2% of best? |", "|---|---|---|---|---|"]
    for i, c in enumerate(d["clauses"], 1):
        L.append(f"| {i} | {NAMES[c['model']]} | {c['wcrps']:.4f} | {c['ratio_to_best']:.4f} | {yes(c['within'])} |")
    L += ["", f"The first candidate in the order that is within 2% is **{d['chosen']}**.", ""]

    sw = r["swap"]
    L += ["## Decision 2: the NOAA-20 method", "",
          f"Chosen Suomi NPP model ({d['chosen']}) fitted on 2012-02 … 2019-12. NOAA-20 fits use 2018-04 … 2019-12. "
          "The swap compares the region-month totals for 2020-01 … 2021-12. No MODIS is used, and the window is "
          "outside both fits. Months left out (swap outage): "
          f"{', '.join(r['swap_outages']['excluded_months']) or 'none'}.", "",
          "| Method | Region-months | Counted (both totals ≥ 10) | Agree | Share |", "|---|---|---|---|---|"]
    for k in ("J-M", "J-S"):
        s = sw[k]
        L.append(f"| {k} | {s['region_months']} | {s['counted']} | {s['agree']} | {pct(s['share'])} |")
    L += ["", f"Rule: choose J-S if its share ≥ J-M's. {pct(n20['J-S'])} ≥ {pct(n20['J-M'])}: "
          f"**{'yes' if n20['js_ge_jm'] else 'no'}** → **{n20['chosen']}**.", ""]

    L += ["## Stage 1: pooled leave-one-year-out (2012 … 2019)", "",
          f"{o['rows']:,} scored rows ({o['active_rows']:,} active), {o['Y']:,} MODIS detections.", ""] + MODEL_HEAD + model_rows(o) + [""]
    fw = r["forward"]
    ff = next(f for f in r["folds"] if f["fold"] == "forward")
    L += ["## Stage 1: forward check (fit 2012–2016, score 2017–2019)", "",
          f"A2's a = {ff['a']} (leave-one-year-out inside 2012–2016). {fw['rows']:,} scored rows "
          f"({fw['active_rows']:,} active), {fw['Y']:,} MODIS detections.", ""] + MODEL_HEAD + model_rows(fw) + [""]
    L += ["### Forward check by region", ""] + split_table("Region", r["forward_region"].items()) + [""]
    L += ["## Stage 1 by region (leave-one-year-out pool)", ""] + split_table("Region", r["per_region"].items()) + [""]
    L += ["## Stage 1 by held-out year", ""] + split_table("Year", [(str(k), v) for k, v in r["per_year"].items()]) + [""]

    L += ["## Inside each fold", "",
          "| Held out | a (A2) | Inner weighted CRPS of A2 by a | Rows on a fallback ratio R1 / Rm / A2 | Rows on a "
          "fallback b R1 / Rm | Rows with A2's r0 = 0 | Regions × day/night with α from all regions R1 / Rm | Seconds |",
          "|---|---|---|---|---|---|---|---|"]
    for f in r["folds"]:
        inner = ", ".join(f"{k}: {v:.4f}" for k, v in f["inner_A2"].items())
        L.append(f"| {f['fold']} | {f['a']} | {inner} | {f['R1_rows_r_fallback']} / {f['Rm_rows_r_fallback']} / "
                 f"{f['A2_rows_r0_fallback']} | {f['R1_rows_b_fallback']} / {f['Rm_rows_b_fallback']} "
                 f"| {f['A2_rows_r0_zero']} | {f['R1_alpha_fallback']} / {f['Rm_alpha_fallback']} | {f['seconds']} |")
    L += [""]

    L += ["## Stage 2 by region", "",
          "| Region | J-M counted | J-M agree | J-M share | J-S counted | J-S agree | J-S share |", "|---|---|---|---|---|---|---|"]
    for k, v in sw["per_region"].items():
        a, b = v["J-M"], v["J-S"]
        L.append(f"| {k} | {a['counted']} | {a['agree']} | {pct(a['share'])} | {b['counted']} | {b['agree']} | {pct(b['share'])} |")
    L += ["", "s = ΣV_SNPP / ΣV_N20 over 2018-04 … 2019-12 (sd from the month-block bootstrap):", "",
          "| Region | s day (sd) | s night (sd) |", "|---|---|---|"]
    st = {(x["region"], x["dn"]): x for x in r["s"]}
    for k in r["regions"]:
        dd, nn = st[(k, "D")], st[(k, "N")]
        L.append(f"| {k} | {dd['s']:.3f} ({dd['sd_s']:.3f}) | {nn['s']:.3f} ({nn['sd_s']:.3f}) |")
    L += [""]
    sp = r["snpp_params"]
    if "groups" in sp and not any("moy" in g for g in sp["groups"]):
        jp = {(x["region"], x["dn"]): x for x in r["jm_params"]["groups"]}
        L += [f"{d['chosen']} fitted on 2012-02 … 2019-12 (Suomi NPP) and, for J-M, on 2018-04 … 2019-12 (NOAA-20); "
              "sd from the year-block bootstrap:", "",
              "| Region | Day/night | r Suomi NPP (sd) | b | α | r NOAA-20, J-M (sd) | b J-M | α J-M |",
              "|---|---|---|---|---|---|---|---|"]
        al = {(x["region"], x["dn"]): x["alpha"] for x in sp["alpha"]}
        alj = {(x["region"], x["dn"]): x["alpha"] for x in r["jm_params"]["alpha"]}
        for g in sp["groups"]:
            j = jp[(g["region"], g["dn"])]
            L.append(f"| {g['region']} | {g['dn']} | {g['r']:.3f} ({g['sd_r']:.3f}) | {g['b']:.4f} | "
                     f"{al[(g['region'], g['dn'])]:.3f} | {j['r']:.3f} ({j['sd_r']:.3f}) | {j['b']:.4f} | "
                     f"{alj[(g['region'], g['dn'])]:.3f} |")
        L += [""]
    L += ["Counted region-months that disagree, J-M:", ""] + disagree_table(sw["jm_months"], "J-M") + [""]
    L += ["Counted region-months that disagree, J-S:", ""] + disagree_table(sw["js_months"], "J-S") + [""]

    out = r["outages"]
    L += ["## Data", "", "| Region | Cells | Rows 2012-02 … 2019-12 | MODIS (Y) | Suomi NPP (V) | NOAA-20 2018-04 … 2019-12 |",
          "|---|---|---|---|---|---|"]
    for k in r["regions"]:
        L.append(f"| {k} | {r['cover'][k]['cells']:,} | {r['rows_per_region'][k]:,} | {r['Y_per_region'][k]:,} "
                 f"| {r['V_per_region'][k]:,} | {r['V20_per_region_fit'][k]:,} |")
    L += ["", f"Rows 2012-02 … 2019-12: {r['n_rows_fit']:,}, of which {r['n_scored_fit']:,} are in scored months.", "",
          f"Stage 1 outage days (bake-off rule): MODIS {', '.join(out['modis_days']) or 'none'}; Suomi NPP "
          f"{', '.join(out['viirs_days']) or 'none'}. Months not scored: {', '.join(out['excluded_months']) or 'none'}.",
          f"Swap outage days: Suomi NPP {', '.join(r['swap_outages']['snpp']) or 'none'}; NOAA-20 "
          f"{', '.join(r['swap_outages']['noaa20']) or 'none'}.", ""]
    if r["full_run"]:
        L += ["The frozen settings are in `data/processed/round2/frozen.json` (not committed: data/ is ignored). "
              "The confirmation (`python -m pipeline.round2.confirm`) refits from them on each sealed region.", ""]
    L += ["## Timings", "", f"Laptop run, {r['jobs']} worker processes for the folds.", "", "| Stage | Seconds |", "|---|---|"]
    L += [f"| {k} | {v:.0f} |" for k, v in r["timings_s"].items()] + [""]
    Path(path).write_text("\n".join(L), encoding="utf-8")


CONFIRMATION_DEVIATIONS = [
    "1. **Rows** are the selection's: cell × month × day/night from 2012-02, for every cell with a MODIS, Suomi NPP "
    "or NOAA-20 detection in 2012-02 … 2019-12. A cell first seen after 2019 has no row, so its detections are not "
    "scored. They are counted under Data below.",
    "2. **Each region is fitted on its own rows only**, as a one-region table, so every fallback (\"all regions\") "
    "stays inside the region. The settings come from data/processed/round2/frozen.json: the model, the NOAA-20 "
    "method, a for A2 if chosen, and the bootstrap settings. Each bootstrap is seeded with 20261101 plus a CRC32 of "
    "its label (region and use).",
    "3. **Outage rule**: the bake-off rule over the included regions combined. Test 1, the seam check and the drift "
    "check leave out months with a MODIS day at 0 while Suomi NPP is ≥ 50, or the reverse. Test 2 uses no MODIS, so "
    "it leaves out months with a Suomi NPP day at 0 while NOAA-20 is ≥ 50, or the reverse (as in the selection). "
    "Fitting uses all months.",
    "4. **Test 1 (a) and (d)**: \"at most F1's + 1.0 percentage point\" means WAPE ≤ F1's WAPE + 0.010. \"Below "
    "F0's\" is strict. **(c)**: |Σ predicted ÷ Σ observed − 1| ≤ 0.10, pooled over the regions' Test 1 rows. "
    "**F1** is R1's point forecast, fitted on the region's own 2012–2019 rows: r·V when V > 0, b when V = 0. "
    "Round 1's F1 had no b term. **F0** is the raw Suomi NPP count.",
    "5. **Coverage** is y in [q10, q90] on active rows (Y > 0 or V > 0). R1 and Rm use the moment-matched negative "
    "binomial with the parameter term, as in the selection. A2 uses A's Poisson–gamma.",
    "6. **Test 2 intervals** are as in the selection: mean ± 1.2816·sd, with sd² = the summed row variances plus the "
    "bootstrap variance of the total. A region-month counts if both expected totals are ≥ 10, and it agrees if the "
    "80% intervals overlap. The share is pooled over the regions.",
    "7. **Seam check** uses Test 1's scored months. Its 80% interval includes the parameter term.",
    "8. **Drift band**: monthly observed ÷ predicted for 2012–2019. Each year is predicted by the frozen model "
    "refitted without that year. The band is the 10th–90th percentile. Only months with a predicted total ≥ 10 "
    "count, and outage months are left out.",
    "9. **Raw folders**: data/raw/spain and data/raw/italy (FIRMS country files), data/raw/australia_sw and "
    "data/raw/usa_socal (area-API box files). All four are clipped to the boxes in pipeline/regions.py.",
    "10. **Completeness**: the confirmation refuses to start unless every MODIS and Suomi NPP file for 2012–2025 and "
    "every NOAA-20 file for 2018–2025 is in each sealed region's manifest. A half-finished download therefore cannot "
    "use up the one run.",
]


def write_confirmation(r, path):
    p, s1, v1 = r["provenance"], r["test1"]["pooled"], r["test1"]["verdict"]
    s2, v2, fz = r["test2"]["pooled"], r["test2"]["verdict"], r["frozen"]
    out = r["outages"]
    yes = lambda v: "**pass**" if v else "**fail**"
    chosen, method = fz["suomi_npp_model"], fz["noaa20_method"]
    L = ["# Round 2 confirmation: the frozen pair on the four new sealed regions", "",
         f"_Generated {r['generated']} by `python -m pipeline.round2.confirm`. Rules: [ROUND2_PLAN.md](ROUND2_PLAN.md) "
         "(pre-registered at commit e7763f7); frozen pair from [ROUND2_SELECTION.md](ROUND2_SELECTION.md). "
         "Do not edit by hand._", ""]
    if not r["is_confirmation"]:
        L += ["**DEVELOPMENT RUN on development regions; this is not the confirmation.**", ""]
    params = ""
    if chosen == "A2":
        params = f" (a = {fz['a']}" + (f", J-M a = {fz['a_jm']}" if method == "J-M" else "") + ")"
    L += [f"- Frozen pair: **{chosen} + {method}**{params}. frozen.json generated {p['frozen_generated']} at commit "
          f"`{p['frozen_commit_at_run']}`.",
          f"- Run started {r['started']} (UTC) at commit `{p['commit']}`"
          + (" with uncommitted files under pipeline/round2/ (listed at the end)." if p["uncommitted_round2"] else "."),
          "- Windows: Test 1 2020–2021. Test 2 2020-01 … 2025-12. Seam 2020–2021. Drift 2022–2025 against 2012–2019.",
          f"- Invocations of this kind logged in data/processed/round2/confirm_runs.jsonl before this report: "
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
    bc = " (holds by construction: the chosen model is R1, its own floor F1)" if v1["by_construction"] else ""
    L += ["", "| Part | Needed | Got | |", "|---|---|---|---|",
          f"| Test 1 (a): cell-month WAPE ≤ F1 + 1.0 point and < F0 | ≤ {pct(s1['wape_cm_F1'] + 0.01)} and < "
          f"{pct(s1['wape_cm_F0'])} | {pct(s1['wape_cm_M'])}{bc} | {yes(v1['a'])} |",
          f"| Test 1 (b): 80% coverage on active rows | 0.70 … 0.90 | {f3(s1['cov_active_M'])} | {yes(v1['b'])} |",
          f"| Test 1 (c): pooled predicted total ÷ observed MODIS | 0.90 … 1.10 | {f3(s1['total_ratio_M'])} "
          f"({s1['total_M']:,.0f} ÷ {s1['Y']:,}) | {yes(v1['c'])} |",
          f"| Test 1 (d): national-month WAPE ≤ F1 + 1.0 point | ≤ {pct(s1['wape_nm_F1'] + 0.01)} | "
          f"{pct(s1['wape_nm_M'])}{bc} | {yes(v1['d'])} |",
          f"| Test 2: share of counted region-months whose 80% intervals overlap | ≥ 0.80 | {f3(s2['share'])} "
          f"({s2['agree']} of {s2['counted']}) | {yes(v2['pass'])} |", ""]

    L += ["## Deviations / interpretations", "",
          "Points the plan left open, settled by the most literal reading when the code was written (on development "
          "regions only, before any sealed file was read).", ""] + CONFIRMATION_DEVIATIONS + [""]

    L += ["## Test 1: accuracy against near-nominal MODIS, 2020–2021", "",
          f"Fit on 2012-02 … 2019-12, scored on 2020–2021 months without an outage day: {s1['rows']:,} rows "
          f"({s1['active_rows']:,} active), {s1['Y']:,} MODIS detections. Months left out: "
          f"{', '.join(m for m in out['months_modis_snpp'] if '2020' <= m <= '2021-12') or 'none'}.", "",
          f"| Forecast | Cell-month WAPE | National-month WAPE | Predicted total (observed {s1['Y']:,}) |",
          "|---|---|---|---|"]
    for k, name in (("M", f"{chosen}, frozen model"), ("F0", "F0 raw Suomi NPP count"), ("F1", "F1 R1's point forecast")):
        L.append(f"| {name} | {pct(s1[f'wape_cm_{k}'])} | {pct(s1[f'wape_nm_{k}'])} | {s1[f'total_{k}']:,.0f} |")
    L += ["", f"{chosen} only: weighted CRPS {f3(s1['wcrps_M'])}, 80% coverage on active rows {pct(s1['cov_active_M'])} "
          f"(all rows, for information: {pct(s1['cov_all_M'])}).", "", "By region:", "",
          "| Region | Rows | Active | MODIS (Y) | Cell-month WAPE model | F0 | F1 | National-month WAPE model | F0 | F1 "
          "| Predicted ÷ observed | Weighted CRPS | Coverage, active rows |", "|---" * 13 + "|"]
    for k, s in r["test1"]["per_region"].items():
        L.append(f"| {k} | {s['rows']:,} | {s['active_rows']:,} | {s['Y']:,} | {pct(s['wape_cm_M'])} | {pct(s['wape_cm_F0'])} "
                 f"| {pct(s['wape_cm_F1'])} | {pct(s['wape_nm_M'])} | {pct(s['wape_nm_F0'])} | {pct(s['wape_nm_F1'])} "
                 f"| {f3(s['total_ratio_M'])} | {f3(s['wcrps_M'])} | {pct(s['cov_active_M'])} |")
    L += [""]

    m2 = pd.DataFrame(r["test2"]["months"])
    L += ["## Test 2: satellite swap, 2020–2025", "",
          f"Suomi NPP: {chosen} fitted on 2012-02 … 2019-12. NOAA-20: {method} fitted on 2018-04 … 2019-12. Months left "
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
        L += ["", "Counted region-months that disagree:", ""] + disagree_table(r["test2"]["months"], method) + [""]
    if method == "J-S":
        L += ["s per region (sd from the month-block bootstrap): " + "; ".join(
            f"{k} day {v['s']['D']:.3f} ({v['sd_s']['D']:.3f}), night {v['s']['N']:.3f} ({v['sd_s']['N']:.3f})"
            for k, v in r["info"].items() if "s" in v) + ".", ""]

    L += ["## Report only: seam check, 2020 and 2021", "",
          "Harmonized (the frozen model's predicted MODIS total from Suomi NPP) ÷ observed MODIS, with the 80% interval.", "",
          "| Region | Year | Observed MODIS | Harmonized | Ratio | 80% interval of the ratio |", "|---|---|---|---|---|---|"]
    for x in r["seam"]:
        y = x["Y"]
        rat = (lambda v: f"{v / y:.3f}") if y else (lambda v: "n/a")
        L.append(f"| {x['region']} | {int(x['year'])} | {int(y):,} | {x['pred']:,.0f} | {rat(x['pred'])} "
                 f"| {rat(x['lo'])} … {rat(x['hi'])} |")
    L += [""]

    d = pd.DataFrame(r["drift"])
    L += ["## Report only: drift divergence, 2022–2025", "",
          "Monthly observed MODIS ÷ the frozen model's prediction from Suomi NPP. The 2012–2019 band is the 10th–90th "
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
          "| In cells without rows (not scored) |", "|---|---|---|---|"]
    for k in r["regions"]:
        c = r["cover"][k]
        fmt = lambda dct: " / ".join(f"{dct.get('terra', 0) + dct.get('aqua', 0):,}" if s == "modis" else
                                     f"{dct.get(s, 0):,}" for s in ("modis", "snpp", "noaa20"))
        L.append(f"| {k} | {c['cells']:,} | {fmt(c['inside'])} | {fmt(c['outside'])} |")
    L += ["", f"Outage days: MODIS {', '.join(out['modis']) or 'none'}; Suomi NPP (vs MODIS) {', '.join(out['snpp']) or 'none'}; "
          f"Suomi NPP (vs NOAA-20) {', '.join(out['snpp_vs_noaa20']) or 'none'}; NOAA-20 {', '.join(out['noaa20']) or 'none'}.", ""]
    if p["uncommitted_round2"]:
        L += ["Uncommitted under pipeline/round2/ at run time:", "", "```", p["uncommitted_round2"], "```", ""]
    L += ["Invocations of this kind logged before this report:", ""]
    L += [f"- {x['event']} {x['at']} regions {', '.join(x['regions'])}" + (f" → {x['overall']}" if "overall" in x else "")
          for x in r["runs_logged"]] or ["- none"]
    L += ["", "## Timings", "", "| Stage | Seconds |", "|---|---|"]
    L += [f"| {k} | {v:.0f} |" for k, v in r["timings_s"].items()] + [""]
    Path(path).write_text("\n".join(L), encoding="utf-8")
