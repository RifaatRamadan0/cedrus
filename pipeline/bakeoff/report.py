"""docs/BAKEOFF_RESULTS.md from results.json. Generated; do not edit by hand."""
from pathlib import Path

NAMES = {"A": "A shrinkage ratio", "B": "B learned detection response"}


def f3(x):
    return "n/a" if x != x else f"{x:.3f}"


def pct(x):
    return "n/a" if x != x else f"{x * 100:.1f}%"


def model_rows(s):
    return [f"| {NAMES[m]} | {f3(s[f'wcrps_{m}'])} | {f3(s[f'crps_{m}'])} | {pct(s[f'cov_{m}'])} "
            f"| {pct(s[f'wape_cm_{m}'])} | {pct(s[f'wape_nm_{m}'])} | {pct(s[f'wape_row_{m}'])} "
            f"| {pct(s[f'cov_active_{m}'])} |" for m in ("A", "B")]


MODEL_HEAD = ["| Model | Weighted CRPS (primary) | CRPS | 80% coverage | Cell-month WAPE | National-month WAPE "
              "| Row WAPE (cell x month x day/night) | Coverage on active rows (information only) |",
              "|---|---|---|---|---|---|---|---|"]


def split_head(first):
    return [f"| {first} | Rows | MODIS (Y) | Weighted CRPS A | Weighted CRPS B | B ÷ A | CRPS A | CRPS B "
            "| Coverage A | Coverage B | Cell-month WAPE A | Cell-month WAPE B | National-month WAPE A "
            "| National-month WAPE B |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]


def split_row(name, s):
    return (f"| {name} | {s['rows']:,} | {s['Y']:,} | {f3(s['wcrps_A'])} | {f3(s['wcrps_B'])} | {f3(s['ratio'])} "
            f"| {f3(s['crps_A'])} | {f3(s['crps_B'])} | {pct(s['cov_A'])} | {pct(s['cov_B'])} | {pct(s['wape_cm_A'])} | {pct(s['wape_cm_B'])} "
            f"| {pct(s['wape_nm_A'])} | {pct(s['wape_nm_B'])} |")


def write_report(r, path):
    d, o, b = r["decision"], r["overall"], r["bootstrap"]
    ui = r["unit_info"]
    yes = lambda v: "**pass**" if v else "**fail**"
    folds = [f for f in r["folds"] if f["fold"] != "forward"]
    fwd_fold = next(f for f in r["folds"] if f["fold"] == "forward")
    out = r["outages"]
    midnight = {k: (v["night_units_within_60min_of_midnight"], v["night_units"]) for k, v in ui.items()}
    xmid = r.get("cross_midnight", {})
    A_fb = sum(f["A_rows_r0_fallback"] for f in folds)
    A_zero = sum(f["A_rows_r0_zero"] for f in folds)
    A_bfb = sum(f["A_rows_bA_fallback"] for f in folds)
    L = [
        "# Bake-off results: shrinkage ratio A vs learned detection response B", "",
        f"_Generated {r['generated']} by `python -m pipeline.bakeoff.run`. "
        "Rules: [BAKEOFF_PLAN.md](BAKEOFF_PLAN.md), committed before any of this code existed. Do not edit by hand._", "",
        "Re-run from the repo root:", "", "```bash", "python -m pipeline.bakeoff.run", "```", "",
        f"**Chosen: {NAMES[d['winner']]}.**", "",
        f"Regions included ({len(r['regions'])}): {', '.join(r['regions'])}.",
    ]
    if r["left_out"]:
        L.append("Regions left out because their 2012–2019 MODIS or Suomi NPP files were not complete when this "
                 "ran: " + "; ".join(f"{k} ({len(v)} of 16 files missing)" for k, v in sorted(r["left_out"].items()))
                 + ".")
    if r["not_requested"]:
        L.append("DEVELOPMENT SUBSET ONLY (--regions): not requested in this run: " + ", ".join(r["not_requested"]) + ".")
    if not r["left_out"] and not r["not_requested"]:
        L.append("No development region was left out.")
    L += ["Sealed regions (Morocco, Tunisia, central Chile, Western Cape) were not read.", "",
          "## Decision", "",
          f"Pooled leave-one-year-out (2012…2019), weighted CRPS of B ÷ A = **{o['ratio']:.3f}**; "
          f"90% paired block-bootstrap interval {b['lo']:.3f} … {b['hi']:.3f} "
          f"({b['resamples']} resamples, held-out years as blocks, seed {b['seed']}).", "",
          "| Clause | Needed | Got | |", "|---|---|---|---|",
          f"| (i) weighted CRPS ratio B ÷ A | ≤ 0.95 | {o['ratio']:.3f} | {yes(d['i_ratio_le_0.95'])} |",
          f"| (ii) upper end of the 90% bootstrap interval | < 1.00 | {b['hi']:.3f} | {yes(d['ii_boot_upper_lt_1'])} |",
          f"| (iii) B's 80% coverage | 0.75 … 0.85 | {o['cov_B']:.3f} | {yes(d['iii_B_coverage_0.75_0.85'])} |",
          "", f"B is chosen only if all three pass. Result: **{NAMES[d['winner']]}**."]
    if d["coverage_miss_only"]:
        L.append("B passed (i) and (ii) but missed the coverage band (iii); by the plan's tie-to-simplicity rule A is chosen.")
    L += ["", f"The winner refit on all of 2012–2019 is in `{r['frozen']}` (not committed: data/ is ignored).", ""]

    L += ["## Deviations / interpretations", "",
          "Points where the plan was silent, ambiguous or could not be applied word for word. Each was settled by the "
          "most literal reading; none was chosen by looking at scores.", "",
          "1. **Window starts Feb 2012.** The plan says 2012–2019 with \"Suomi NPP from 2012-02\"; rows run 2012-02 … "
          "2019-12 (as in TEST_PLAN.md). January 2012 detections are used only as the date − 1 chance control for "
          "units on 1 Feb 2012. Nothing from 2020 on is read: for units on 31 Dec 2019 the date + 1 control would be "
          f"2020, so c = the date − 1 count alone ({sum(v['units_without_date_plus_1'] for v in ui.values())} units).",
          "2. **\"Same date\" is FIRMS `acq_date` (UTC).** East of about 25°E the Suomi NPP and Aqua night passes fall "
          "around midnight UTC, so a fire seen by both can carry two different dates and is then not matched. "
          "Night units within 60 min of midnight: "
          + ", ".join(f"{k} {a:,} of {n:,}" for k, (a, n) in midnight.items()) + ". "
          "For information only (not used anywhere in the models), matching that allows the date to cross midnight "
          "would give these mean matched counts per night unit: "
          + ", ".join(f"{k} {v['N_same_date']:.3f} → {v['N_cross']:.3f}" for k, v in xmid.items()) + ".",
          "3. **Pass** = Suomi NPP detections with one date and day/night, chained while consecutive `acq_time` "
          f"values are ≤ 30 min apart (longest pass found: {max(v['max_pass_span_min'] for v in ui.values())} min).",
          "4. **Matching time window** is checked pixel to pixel: an Aqua pixel can match a Suomi NPP pixel with the "
          "same date and day/night and |Δt| ≤ 60 min. Its nearest unit is the unit holding its nearest such pixel; "
          "it is matched if that distance is within its own ½·√(scan² + track²) + 0.5 km.",
          "5. **Distances** are chords between points on a 6371 km sphere (in a cKDTree) rather than an "
          "equirectangular projection; at 1–3 km the two agree to well under a metre.",
          "6. **A unit's row**: the cell of the unit's pixel nearest its centroid (a unit can straddle a cell edge), "
          "with the month and day/night of its pass. Unit FRP ≤ 0 sets the indicator and log FRP to 0; when no "
          "training unit has FRP ≤ 0 the indicator's coefficient is 0.",
          "7. **Outage rule**: the two families are MODIS (Terra + Aqua) and Suomi NPP, counted per UTC date over all "
          f"included regions. Outage days: MODIS {len(out['modis_days'])}, Suomi NPP {len(out['viirs_days'])}; "
          f"months not scored: {', '.join(out['excluded_months']) or 'none'}. These months are left out of every score "
          "(inner tuning and outer); fitting uses all months, because the plan restricts scoring only. "
          "Days with zero Terra (or zero Aqua) while Suomi NPP had ≥ 50 are not part of the rule; they are listed "
          f"below for information (Terra {len(out['single_satellite_zero_days']['terra'])}, "
          f"Aqua {len(out['single_satellite_zero_days']['aqua'])}).",
          "8. **Inner leave-one-year-out criterion** is the primary score (weighted mean CRPS, weights from the inner "
          "training years), pooled over the inner held-out years. A tie would go to the smaller grid value.",
          "9. **A where the prior ratio is undefined.** If a region × month × day/night had no Suomi NPP detection in "
          "training, r0 falls back to the region × day/night ratio, then to all regions × day/night "
          f"({A_fb:,} scored rows over the eight folds). Where r0 = 0 the posterior rate a/r0 is infinite and the "
          f"forecast is all mass at 0 ({A_zero:,} scored rows). Where a region × month × day/night had no training row "
          f"with V = 0, b_A falls back to the region × day/night mean ({A_bfb:,} scored rows).",
          "10. **B's region effects** are fitted with one reference region, then centred per day/night (their mean moved "
          "into the month terms, which leaves the fit unchanged), so shrinking towards 0 means towards the average "
          "region. τ² and the shrinkage are computed per day/night; var(β̂) is the population variance (ddof 0) of the "
          "centred effects; se comes from the expected Fisher information. α stays at its maximum-likelihood value.",
          "11. **Coverage** counts y inside [q10, q90], with q the smallest k where F(k) ≥ 0.1 or 0.9, unweighted over "
          "scored rows. Most rows have y = 0 and a forecast whose 90th percentile is 0, which counts as covered. "
          "Coverage on active rows (Y > 0 or V > 0) is shown for information; the rule uses all rows.",
          "12. **WAPE**: cell-month adds day and night before taking |error| (cell × month, as in TEST_PLAN.md); "
          "national-month is region × month. Row-level WAPE (cell × month × day/night) is shown too.",
          "13. **CRPS** sums k = 0 … K with K = max(0.9999 quantile, y + 50).",
          "14. **Bootstrap** interval is the 5th–95th percentile of the resampled ratios.",
          "15. **Border cells**: rows are per region, so a cell on a border has a row in each country file it "
          "appears in, each counting only that file's detections.",
          "16. **Frozen refit**: its tuning value is chosen by leave-one-year-out over all eight years.", ""]

    L += ["## Overall: pooled leave-one-year-out", "",
          f"{o['rows']:,} scored rows, {o['Y']:,} MODIS detections.", ""] + MODEL_HEAD + model_rows(o) + [""]
    fw = r["forward"]
    L += ["## Forward check: fit 2012–2016, score 2017–2019", "",
          f"a = {fwd_fold['a']}, b = {fwd_fold['b']} (chosen by leave-one-year-out inside 2012–2016). "
          f"Weighted CRPS ratio B ÷ A = **{fw['ratio']:.3f}**. {fw['rows']:,} scored rows, {fw['Y']:,} MODIS detections.",
          ""] + MODEL_HEAD + model_rows(fw) + ["", "By region:", ""] + split_head("Region") + \
        [split_row(k, v) for k, v in r["forward_region"].items()] + [""]
    L += ["## Per region (leave-one-year-out pool)", ""] + split_head("Region") + \
        [split_row(k, v) for k, v in r["per_region"].items()] + [""]
    L += ["## Per held-out year", ""] + split_head("Year") + \
        [split_row(str(k), v) for k, v in r["per_year"].items()] + [""]
    L += ["## Tuning inside each fold", "",
          "| Held out | a (A) | b (B) | Inner weighted CRPS, A by a | Inner weighted CRPS, B by b | α | τ² day | τ² night | NB converged | Seconds |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for f in folds + [fwd_fold]:
        ia = ", ".join(f"{k}: {v:.4f}" for k, v in f["inner_A"].items())
        ib = ", ".join(f"{k}: {v:.4f}" for k, v in f["inner_B"].items())
        L.append(f"| {f['fold']} | {f['a']} | {f['b']} | {ia} | {ib} | {f['alpha']:.3f} | {f['tau2']['D']:.4f} "
                 f"| {f['tau2']['N']:.4f} | {f['nb_converged']} | {f['seconds']} |")
    L += [""]

    L += ["## The learned response g(FRP)", "",
          "Fitted on every unit of 2012–2019. m = Aqua pixels matched to the unit on its own date; c = the same with "
          "Aqua from date − 1 and date + 1 (chance). ĝ are the two Poisson fits; g = max(ĝ_match − ĝ_chance, 0.001). "
          "Bin values are means over the units in the bin.", ""]
    for dn in ("D", "N"):
        gf = r["g_fit"][dn]
        L += [f"**{'Day' if dn == 'D' else 'Night'}** ({gf['units']:,} units). log ĝ_match = "
              f"{gf['match'][0]:.3f} + {gf['match'][1]:.3f}·log FRP + {gf['match'][2]:.3f}·1[FRP ≤ 0]; "
              f"log ĝ_chance = {gf['chance'][0]:.3f} + {gf['chance'][1]:.3f}·log FRP + {gf['chance'][2]:.3f}·1[FRP ≤ 0].", "",
              "| Unit FRP (MW) | Units | Median FRP | Matched m (observed) | Chance c (observed) | ĝ_match | ĝ_chance | g |",
              "|---|---|---|---|---|---|---|---|"]
        for t in [t for t in r["g_table"] if t["dn"] == dn]:
            L.append(f"| {t['bin']} | {t['units']:,} | {t['median_frp']:.1f} | {t['m_mean']:.3f} | {t['c_mean']:.3f} "
                     f"| {t['g_match']:.3f} | {t['g_chance']:.3f} | {t['g']:.3f} |")
        L.append("")

    L += ["## Data", "",
          "| Region | Cells | Rows | MODIS detections (Y) | Suomi NPP detections (V) | Fire units | Suomi NPP passes |",
          "|---|---|---|---|---|---|---|"]
    for k in r["regions"]:
        L.append(f"| {k} | {r['cells_per_region'][k]:,} | {r['rows_per_region'][k]:,} | {r['Y_per_region'][k]:,} "
                 f"| {r['V_per_region'][k]:,} | {r['units_per_region'].get(k, 0):,} | {ui[k]['passes']:,} |")
    L += ["", f"Rows: {r['n_rows']:,}, of which {r['n_scored_rows']:,} are in scored months. "
          "Rows are 2012-02 … 2019-12 × day/night for every cell with a detection.", "",
          f"Outage days, MODIS: {', '.join(out['modis_days']) or 'none'}. Suomi NPP: {', '.join(out['viirs_days']) or 'none'}.",
          "", f"Information only — zero-Terra days: {', '.join(out['single_satellite_zero_days']['terra']) or 'none'}; "
          f"zero-Aqua days: {', '.join(out['single_satellite_zero_days']['aqua']) or 'none'}.", ""]

    L += ["## Timings", "", f"Laptop run, {r['jobs']} worker processes for the folds.", "",
          "| Stage | Seconds |", "|---|---|"]
    L += [f"| {k} | {v:.0f} |" for k, v in r["timings_s"].items()]
    L += [""]
    Path(path).write_text("\n".join(L), encoding="utf-8")
