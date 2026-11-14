"""docs/TOURNAMENT_RESULTS.md from data/processed/tournament/results.json. Generated; do not edit by hand."""
from .candidates import CANDIDATES, NAMES, SIMPLICITY


def f3(x):
    return "n/a" if x != x else f"{x:.3f}"


def f4(x):
    return "n/a" if x != x else f"{x:.4f}"


def pct(x):
    return "n/a" if x != x else f"{x * 100:.1f}%"


def spct(x):
    return "n/a" if x != x else f"{x * 100:+.1f}%"


DEVIATIONS = [
    "1. **Rows** are round 2's (`pipeline.round2.data.rows`): cell × month × day/night from 2012-02, for every 0.25° "
    "cell with a MODIS, Suomi NPP or NOAA-20 detection in 2012-02 … 2019-12, in the 17 regions with role \"dev\" in "
    "pipeline/regions.py, each clipped to its box. Only files for 2012–2021 are read. Round 2's pixel cache keeps no "
    "FRP or scan, so the same files are read again through round 2's guard and the bake-off's filters; the pixel "
    "counts Y, V and V20 are round 2's own function's output.",
    "2. **Outage rule**: the bake-off's own code over the 17 regions combined. Months with an outage day are left out "
    "of every score, inner tuning included; fitting uses all months. The swap window uses round 2's swap rule "
    "(Suomi NPP at 0 while NOAA-20 ≥ 50, or the reverse). **Turkey 2020 is not in the swap**: its NOAA-20 file "
    "(viirs-jpss1_2020_Turkey.csv) is missing, so that region-year is left out of the swap rows and of the swap "
    "outage count.",
    "3. **Primary score**: weighted CRPS with w = 1 + the cell's mean Y over the fold's training rows (in the unit "
    "being scored). \"Pooled\" is the leave-one-year-out pool (2012 … 2019 held out in turn), as in round 2. The "
    "forward check is reported and does not enter any rule. \"Within 2%\" is weighted CRPS ≤ 1.02 × the best.",
    "4. **C0** is round 2's A2 code with a = 30 fixed (the frozen setting), not re-tuned. **C1 / C2** are round 2's "
    "R1 / Rm code unchanged (shared α, the year-block parameter term). All three are fitted on one table of the 17 "
    "regions, as round 2 fitted its 13.",
    "5. **C3 / C4 classes**: C3 has four FRP classes, FRP ≤ 0, 0 < FRP < 5, 5 ≤ FRP < 20 and FRP ≥ 20 MW. C4 has "
    "the plan's three scan classes, scan < 0.5, 0.5 ≤ scan ≤ 0.65 and scan > 0.65 km (the 0.5 and 0.65 values, "
    "which occur because scan is given to 2 decimals, fall in the middle class). The FRP ≤ 0 class is C3's only; "
    "in C4 such a detection stays in its scan class.",
    "6. **C3 / C4 ratios**: MODIS is not split by class, so \"each class with its own A2-style ratio\" needs the class "
    "share of Y. It is allocated in proportion to V_k × the class's current posterior mean and iterated to a fixed "
    "point: one step of the map changes the class means by less than 10⁻⁷ of the largest, at most 3,000 map "
    "evaluations. The plain iteration needed 1,300–2,250 steps on one development fold (60–130 s per fit), so it is "
    "accelerated by SQUAREM (Varadhan and Roland 2008, scheme S3), which reaches the same fixed point under the same "
    "stopping rule. With one class this is A2 exactly. Per class: prior "
    "r0_k = ΣY_k/ΣV_k per region × calendar month × day/night (fallback region × day/night, then all regions × "
    "day/night), posterior shape a + ΣY_k and rate a/r0_k + ΣV_k per cell × calendar month × day/night, sums over "
    "training rows with V > 0. A row's forecast is the sum over its classes of NB(shape_k, rate_k/(rate_k + V_k)), "
    "moment-matched to one negative binomial. V = 0 rows: Poisson(b_A) as A2. a is chosen from {10, 30, 100, 300, "
    "1000} by inner leave-one-year-out, ties to the smaller a. The allocated class sums are treated as observed in "
    "the posterior (a plug-in, not a full posterior over the allocation).",
    "7. **C5**: the 3 × 3 neighbourhood includes the cell itself and only cells of the same region that have rows. "
    "Neighbourhood ratio r_nb = (a_n + ΣY_nb)/(a_n/r0 + ΣV_nb) per cell × calendar month × day/night with A2's r0; "
    "cell posterior shape a + ΣY, rate a/r_nb + ΣV. Both strengths come from A2's grid, the 25 pairs chosen by inner "
    "leave-one-year-out (ties to the smaller a, then the smaller a_n). As a_n grows, C5 becomes A2.",
    "8. **C6**: log μ = log(Σ_k β_k V_k + b) + γ[calendar month × day/night] + δ[region], with all seven class "
    "counts (four FRP, three scan). Both class sets add up to V, so the β have one flat direction; μ does not. β ≥ 0 "
    "(β = e^θ). b is fixed at 1: with γ free, a free b would only rescale (β, b) against γ. \"Region terms\" are one "
    "per region (not region × day/night). Region effects are centred (their mean moved into γ) and shrunk as the "
    "bake-off's B: τ² = max(0, var(δ̂) − mean(se²)), δ* = δ̂ · τ²/(τ² + se²), with se from the expected information. "
    "α is not refitted after shrinking. Forecast NB2(μ*, α). Fitted by maximum likelihood (L-BFGS-B, analytic "
    "gradient) on all training rows; nothing tuned.",
    "9. **C7**: backend **{backend}**. LightGBM was not importable at first; it was installed with pip (4.7.0) into the "
    "interpreter on PATH, so no substitution was needed. Features: the seven class counts, day/night, calendar "
    "month (numeric), region (categorical) and the cell's history ratio ΣY/ΣV over the fold's training rows with "
    "V > 0 (missing where the cell has none). The ratio is computed on the training years and used for training "
    "and scored rows alike, so a training row's own Y is inside its feature (the literal reading). Settings are "
    "fixed, not tuned: Poisson objective, 300 trees, learning rate 0.05, 31 leaves, at least 100 rows per leaf, "
    "deterministic, one thread. α per region × day/night by maximum likelihood on the residuals of inner "
    "leave-one-year-out fits (each training year predicted by trees fitted on the other training years, scored "
    "months only); a region × day/night with no informative row takes all regions' α for that day/night.",
    "10. **C8**: per region × day/night, pooled over cells and months of the training rows. Each distinct Suomi NPP "
    "count v maps to the mean MODIS count over the same quantile band (rows sorted by V; Y sorted on its own), so "
    "the map is monotone and keeps the training total. Zero-aware: V = 0 maps to the mean of the lowest P(V = 0) "
    "share of Y, which is 0 whenever MODIS has at least as many zero rows. Frozen rules between and beyond the "
    "training values: linear between neighbouring values (from (0, 0) if 0 was never seen); above the largest, "
    "proportional, m(v) = m(v_max)·v/v_max. Forecast: negative binomial with that mean and α per region × day/night "
    "by maximum likelihood on the training rows (as R1); rows with mean 0 are all mass at 0.",
    "11. **Burning days**: a 0.01° cell (floor(lon/0.01), floor(lat/0.01)) counts once per date and day/night if "
    "it has any detection of the family; MODIS is Terra and Aqua together. The cell-day counts are summed per 0.25° "
    "cell × month × day/night on the same rows. For class counts a burning day takes the FRP and scan classes of "
    "its largest-FRP detection, so its classes still add up to its total. Weights use the training-mean burning "
    "days. s for J-S is refitted in this unit. **D-a and D-b are the two lowest pooled weighted CRPS among C0–C8** "
    "(not the selection rule's choice); each is refitted from scratch in this unit, its tuning redone there.",
    "12. **Coverage** is y in [q10, q90] on active rows (Y > 0 or V > 0). For information it is split into active "
    "rows with V > 0 and active rows with V = 0 (MODIS-only rows).",
    "13. **Swap stability**: each candidate is fitted on all 2012-02 … 2019-12 rows (tuned candidates by inner "
    "leave-one-year-out over 2012–2019; C0 keeps a = 30). s = ΣV_SNPP/ΣV_N20 per region × day/night over 2018-04 … "
    "2019-12 (round 2's fit_s). The candidate is applied to Suomi NPP and to s × NOAA-20, every class count "
    "multiplied by the same s. Each region-month total is the sum of the rows' predictive means. The median "
    "|log(NOAA-20-based ÷ Suomi NPP-based)| is taken over the region-months where both totals are > 0. The same "
    "median over region-months where both are ≥ 10 (round 2's counting rule) is shown for information.",
    "14. **Headroom floor**: per row, Σ_k F(k)(1 − F(k)) with F the Poisson CDF at the champion's predictive mean. "
    "This is the expected CRPS when y really is Poisson with that mean, using the same summed CRPS as the scores. "
    "It is weighted and pooled like the primary score, over the leave-one-year-out pool. **It is an optimistic "
    "lower bound**: it ignores real extra-Poisson variability, and its mean is the champion's own, not the truth.",
    "15. **Burning-days rule**: (i) \"exceeds by at least 10% in relative terms\" is SS_bd ≥ 1.10 × SS_pixel, with "
    "SS = 1 − weighted CRPS ÷ that unit's R1 weighted CRPS on the leave-one-year-out pool; (ii) \"at least as good\" "
    "is median |log| ≤ the pixel champion's; (iii) active-row coverage in [0.70, 0.90], inclusive. The burning-days "
    "candidate tested is the one of D-a / D-b with the higher skill.",
    "16. **Seeds**: every bootstrap (R1/Rm year blocks, s month blocks) draws from numpy's default_rng seeded with "
    "20261101 plus a CRC32 of its label (unit, fold, candidate).",
]


def leaderboard(s, sw, cands, names, ref_label):
    L = ["| Candidate | Pooled weighted CRPS | ÷ best | Skill vs " + ref_label + " | CRPS | Coverage, active rows "
         "| Coverage, active V > 0 | Coverage, active V = 0 | Cell-month WAPE | National-month WAPE | Total bias "
         "| Swap median abs log (both > 0) | Swap median abs log (both ≥ 10) |",
         "|---" * 13 + "|"]
    best = min(s[f"wcrps_{c}"] for c in cands)
    for c in sorted(cands, key=lambda c: s[f"wcrps_{c}"]):
        L.append(f"| {names[c]} | {f4(s[f'wcrps_{c}'])} | {s[f'wcrps_{c}'] / best:.4f} | {spct(s[f'skill_{c}'])} "
                 f"| {f4(s[f'crps_{c}'])} | {pct(s[f'cov_active_{c}'])} | {pct(s[f'cov_vpos_{c}'])} "
                 f"| {pct(s[f'cov_vzero_{c}'])} | {pct(s[f'wape_cm_{c}'])} | {pct(s[f'wape_nm_{c}'])} "
                 f"| {spct(s[f'bias_{c}'])} | {f4(sw[c]['median_abs_log'])} | {f4(sw[c]['median_abs_log_ge10'])} |")
    return L


def per_table(first, items, cands, key, fmt):
    L = [f"| {first} | Rows | Active | Y | " + " | ".join(cands) + " |", "|---" * (4 + len(cands)) + "|"]
    for name, s in items:
        L.append(f"| {name} | {s['rows']:,} | {s['active_rows']:,} | {s['Y']:,.0f} | "
                 + " | ".join(fmt(s[f"{key}_{c}"]) for c in cands) + " |")
    return L


def write_results(r, path):
    px, bd, d, ud = r["px"], r["bd"], r["decision"], r["unit_decision"]
    o = px["overall"]
    yes = lambda v: "**yes**" if v else "no"
    pxn = {c: f"{c} {NAMES[c]}" for c in CANDIDATES}
    bdn = {c: f"{r['bd_names'][c]} ({c} {NAMES[c]})" for c in r["bd_names"]}
    champ = d["chosen"]
    hr = r["headroom"]
    L = ["# Tournament results: the best harmonizer on development data", "",
         "_Generated " + r["generated"] + " by `python -m pipeline.tournament.run`. Rules: "
         "[TOURNAMENT_PLAN.md](TOURNAMENT_PLAN.md), pre-registered at commit fa2c956 before any tournament code. "
         "Do not edit by hand._", "",
         "```bash", "python -m pipeline.tournament.run", "python -m pipeline.tournament.test_tournament", "```", "",
         f"- Run started {r['started']} (UTC) at commit `{r['commit']}`"
         + (" with uncommitted files under pipeline/tournament/ (this code is not committed yet)." if r["uncommitted"]
            else "."),
         f"- Development regions ({len(r['regions'])}): {', '.join(r['regions'])}. No sealed region was opened: every "
         "file access goes through `pipeline.round2.data.guard`, which refuses role \"sealed\".",
         f"- Fitting and tuning on 2012-02 … 2019-12 ({r['n_rows_fit']:,} rows, {r['n_scored_fit']:,} in scored "
         f"months). Swap stability on 2020-01 … 2021-12 ({r['n_swap_rows']:,} rows), no MODIS.",
         f"- Missing files: " + ("; ".join(f"{k}: {', '.join(v)}" for k, v in r["missing_files"].items()) or "none")
         + ".", ""]

    L += ["## Deviations / interpretations", "",
          "Points the plan left open, settled by the most literal reading while the code was written. They were "
          "fixed before the full run.", ""]
    L += [x.replace("{backend}", r["gbm_backend"]) for x in DEVIATIONS] + [""]

    L += ["## Decision", "",
          "### 1. Pixel champion", "",
          f"Pooled leave-one-year-out weighted CRPS. Best: {d['best']} ({f4(o['wcrps_' + d['best']])}); bar = 1.02 × "
          f"best = {f4(d['bar'])}. Rule: the simplest candidate within 2% of the best, in the order "
          + " < ".join(SIMPLICITY) + ".", "",
          "| Order | Candidate | Pooled weighted CRPS | ÷ best | Within 2% of best? |", "|---|---|---|---|---|"]
    for i, c in enumerate(d["clauses"], 1):
        L.append(f"| {i} | {pxn[c['model']]} | {c['wcrps']:.4f} | {c['ratio_to_best']:.4f} | {yes(c['within'])} |")
    L += ["", f"The first candidate in the order that is within 2% is **{champ}** ({NAMES[champ]}).", ""]

    L += ["### 2. Burning days as the primary unit?", "",
          f"Best two pixel candidates (lowest pooled weighted CRPS): {r['best_two'][0]} → D-a, {r['best_two'][1]} → "
          f"D-b; R1 → D-R1. The burning-days candidate tested is **{ud['best_bd']}** (the higher skill).", "",
          "| Clause | Needed | Got | |", "|---|---|---|---|",
          f"| (i) skill at least 10% above the pixel champion's | ≥ {spct(ud['needed_skill'])} "
          f"(pixel champion {spct(ud['px_skill'])}) | {spct(ud['bd_skill'])} | {yes(ud['i_skill'])} |",
          f"| (ii) swap stability at least as good (median abs log) | ≤ {f4(ud['px_swap'])} | {f4(ud['bd_swap'])} "
          f"| {yes(ud['ii_swap'])} |",
          f"| (iii) active-row coverage in 0.70 … 0.90 | 0.70 … 0.90 | {f3(ud['bd_cov_active'])} | {yes(ud['iii_coverage'])} |",
          "", f"→ Primary unit: **{ud['primary']}**."
          + (" Burning days may be offered as a secondary view; \"number of hotspots\" stays primary."
             if ud["primary"] != "burning days" else
             f" **Open, not decided by this run:** the plan does not say which model sits round 3 when burning days "
             f"become primary: the pixel champion of rule 1 ({champ}, in hotspots) or the burning-days model whose "
             f"skill passed rule 2 ({ud['best_bd']}). Both are recorded in champion.json."), ""]

    L += ["### 3. Headroom and the stopping rule", "",
          f"Champion {champ}: pooled weighted CRPS {f4(hr['wcrps'])}; Poisson counting-noise floor {f4(hr['floor'])} "
          f"(an optimistic lower bound). **Headroom = ({f4(hr['wcrps'])} − {f4(hr['floor'])}) ÷ {f4(hr['wcrps'])} = "
          f"{pct(hr['headroom'])}.** Stop rule: stop searching when headroom < 15% or on 9 Nov 2026. "
          + ("Headroom is below 15%: **stop**." if r["stop"]["stop_now"] else
             "Headroom is not below 15%: by this rule the search **may continue** until 9 Nov 2026."), "",
          "### 4. Freeze", "",
          f"The champion's settings are in `data/processed/tournament/champion.json`. The plan requires the champion "
          f"to be frozen (code and settings committed) before round 3's sealed regions are downloaded; this run does "
          f"not commit anything.", ""]

    L += ["## Spot check: C0 against round 2", "",
          f"C0 restricted to round 2's 13 development regions: pooled leave-one-year-out weighted CRPS "
          f"**{f4(r['spot_check']['wcrps_C0'])}** on {r['spot_check']['rows']:,} rows; round 2's A2: "
          f"{r['spot_check']['round2']} on {r['spot_check']['round2_rows']:,} rows. "
          + ("Reproduced to four decimals." if r["spot_check"]["matches"] else "**Not reproduced to four decimals.**"),
          ""]

    L += ["## Leaderboard: pixel unit (hotspots), pooled leave-one-year-out 2012 … 2019", "",
          f"{o['rows']:,} scored rows ({o['active_rows']:,} active: {o['active_vpos']:,} with V > 0, "
          f"{o['active_vzero']:,} MODIS-only), {o['Y']:,.0f} MODIS detections. Skill = 1 − weighted CRPS ÷ C1's. "
          "Sorted by the primary score.", ""] + leaderboard(o, px["swap"], CANDIDATES, pxn, "C1 (R1)") + [""]
    fw = px["forward"]
    L += ["### Forward check (fit 2012–2016, score 2017–2019), for information", "",
          f"{fw['rows']:,} scored rows ({fw['active_rows']:,} active).", ""] + \
         leaderboard(fw, px["swap"], CANDIDATES, pxn, "C1 (R1)") + [""]

    bo = bd["overall"]
    bc = list(r["bd_names"])
    L += ["## Leaderboard: burning-day unit, pooled leave-one-year-out 2012 … 2019", "",
          f"{bo['rows']:,} scored rows ({bo['active_rows']:,} active), {bo['Y']:,.0f} MODIS burning days. "
          "Skill = 1 − weighted CRPS ÷ D-R1's. Raw CRPS is not comparable across units; skill is.", ""] + \
         leaderboard(bo, bd["swap"], bc, bdn, "D-R1") + [""]
    bf = bd["forward"]
    L += ["### Forward check, burning days", ""] + leaderboard(bf, bd["swap"], bc, bdn, "D-R1") + [""]

    L += ["## Headroom of every candidate (information)", "",
          "| Unit | Candidate | Pooled weighted CRPS | Poisson floor | Headroom | Floor on V > 0 rows only |",
          "|---|---|---|---|---|---|"]
    for unit, res, names, cs in (("pixels", px, pxn, CANDIDATES), ("burning days", bd, bdn, bc)):
        for c in cs:
            h = res["overall"][f"headroom_{c}"]
            L.append(f"| {unit} | {names[c]} | {f4(h['wcrps'])} | {f4(h['floor'])} | {pct(h['headroom'])} "
                     f"| {f4(h['floor_vpos'])} |")
    L += [""]

    L += ["## Pixel unit by region (leave-one-year-out pool): weighted CRPS", ""] + \
         per_table("Region", px["per_region"].items(), CANDIDATES, "wcrps", f3) + [""]
    L += ["## Pixel unit by region: active-row coverage", ""] + \
         per_table("Region", px["per_region"].items(), CANDIDATES, "cov_active", pct) + [""]
    L += ["## Pixel unit by held-out year: weighted CRPS", ""] + \
         per_table("Year", [(str(k), v) for k, v in px["per_year"].items()], CANDIDATES, "wcrps", f3) + [""]
    L += ["## Burning-day unit by region: weighted CRPS", ""] + \
         per_table("Region", bd["per_region"].items(), bc, "wcrps", f3) + [""]

    L += ["## Swap stability by region (median abs log, both totals > 0), pixel unit", "",
          "| Region | " + " | ".join(CANDIDATES) + " |", "|---" * (1 + len(CANDIDATES)) + "|"]
    for reg in r["regions"]:
        L.append(f"| {reg} | " + " | ".join(f3(px["swap_region"][c][reg]["median_abs_log"])
                                              if reg in px["swap_region"][c] else "n/a" for c in CANDIDATES) + " |")
    L += ["", "Region-months in the swap: " + f"{px['swap']['C0']['region_months']} (used, both > 0: "
          + ", ".join(f"{c} {px['swap'][c]['used']}" for c in CANDIDATES) + ").", ""]

    L += ["## Inside each fold (tuned settings)", "",
          "| Unit | Candidate | " + " | ".join(str(f["fold"]).split(":", 1)[1] for f in px["folds"]["C0"]) + " |",
          "|---" * (2 + len(px["folds"]["C0"])) + "|"]
    for unit, res, cs in (("pixels", px, CANDIDATES), ("burning days", bd, bc)):
        for c in cs:
            if c not in ("C3", "C4", "C5"):
                continue
            L.append(f"| {unit} | {c} | " + " | ".join(str(f["setting"]) for f in res["folds"][c]) + " |")
    L += ["", "C3 / C4: a. C5: (a, a_n). Other candidates have no tuned setting (C0: a = 30 frozen; C7: fixed tree "
          "settings, α from inner residuals).", ""]
    L += ["| Unit | Candidate | Fold | Detail |", "|---|---|---|---|"]
    for unit, res, cs in (("pixels", px, CANDIDATES), ("burning days", bd, bc)):
        for c in cs:
            if c not in ("C3", "C4", "C6"):
                continue
            for f in res["folds"][c]:
                det = f["detail"]
                if c == "C6":
                    txt = (f"converged {det['converged']}, max abs gradient {det['max_abs_grad']:.2g}, α "
                           f"{det['alpha']:.3f}, τ² {det['tau2']:.4f}, β "
                           + ", ".join(f"{k} {v:.3g}" for k, v in det["beta"].items()))
                else:
                    txt = (f"a {det['a']}, map evaluations {det['em_iterations']}, last relative change {det['em_delta']:.1e}, "
                           f"converged {det['em_converged']}")
                L.append(f"| {unit} | {c} | {str(f['fold']).split(':', 1)[1]} | {txt} |")
    L += [""]

    L += ["## Data", "",
          "| Region | Cells | Rows 2012-02 … 2019-12 | MODIS (Y) | Suomi NPP (V) | NOAA-20 | MODIS burning days | "
          "Suomi NPP burning days | NOAA-20 burning days |", "|---|---|---|---|---|---|---|---|---|"]
    for reg, x in r["data"].items():
        L.append(f"| {reg} | {x['cells']} | {x['rows']:,} | {x['Y']:,} | {x['V']:,} | {x['V20']:,} | {x['Yb']:,} "
                 f"| {x['Vb']:,} | {x['V20b']:,} |")
    out = r["outages"]
    L += ["", f"Outage days (bake-off rule, 17 regions combined): MODIS {', '.join(out['modis_days']) or 'none'}; "
          f"Suomi NPP {', '.join(out['viirs_days']) or 'none'}. Months not scored: "
          f"{', '.join(out['excluded_months']) or 'none'}. Swap outage months: "
          f"{', '.join(r['swap_outages']['excluded_months']) or 'none'}.", "",
          "s = ΣV_SNPP / ΣV_N20 over 2018-04 … 2019-12 (sd from the month-block bootstrap):", "",
          "| Region | s day, pixels (sd) | s night, pixels (sd) | s day, burning days (sd) | s night, burning days (sd) |",
          "|---|---|---|---|---|"]
    sp, sb = r["s"]["px"], r["s"]["bd"]
    for i in range(0, len(sp), 2):
        L.append(f"| {sp[i]['region']} | {sp[i]['s']:.3f} ({sp[i]['sd_s']:.3f}) | {sp[i + 1]['s']:.3f} "
                 f"({sp[i + 1]['sd_s']:.3f}) | {sb[i]['s']:.3f} ({sb[i]['sd_s']:.3f}) | {sb[i + 1]['s']:.3f} "
                 f"({sb[i + 1]['sd_s']:.3f}) |")
    L += ["", "Per-row scores: data/processed/tournament/rows_{px,bd}_{loyo,forward}.pkl; swap totals: "
          "swap_{px,bd}.pkl; everything above: results.json; the champion's refit settings: champion.json "
          "(data/ is not committed).", "",
          "## Timings", "", f"Laptop run, {r['jobs']} worker processes. Each fitted fold is cached, keyed by a hash "
          "of the fitting code, so a re-run that changes only the report refits nothing. Jobs fitted by this "
          f"invocation: pixels {r['jobs_fitted_now']['px']}, burning days {r['jobs_fitted_now']['bd']}.", "",
          f"Seconds per fitted job, summed (as fitted, {r['jobs']} jobs at a time): pixel unit "
          f"{r['job_seconds']['px']:,.0f}, burning-day unit {r['job_seconds']['bd']:,.0f}.", "",
          "This invocation:", "", "| Stage | Seconds |", "|---|---|"]
    L += [f"| {k} | {v:.0f} |" for k, v in r["timings_s"].items()]
    path.write_text("\n".join(L) + "\n", encoding="utf-8")
