"""Do the 80% ranges of estimated months hold the true value 80% of the time?

MODIS is still a usable reference in 2020-2021, and both frozen models are fitted on 2012-02..2019-12 only. So this
script estimates 2020-2021 exactly as the product estimates 2022 onward, builds the ranges the way the website builds
them, and counts how often the observed MODIS value falls inside.

    python analysis/range_coverage/run_test.py [--work DIR]

Steps:
1. Run the real exporter (pipeline/export_v2.py) with one change, the observed era ending at 2019-12 instead of
   2021-12, into a scratch folder (--work, default: a temporary folder that is deleted afterwards). web/data/ is
   never written. The scratch files must equal the published ones for every month up to 2019-12 and from 2022-01.
2. Whole regions and blocks of 0.25 degree cells: the range of web/app.js regionSeries() (values summed, half-widths
   combined in quadrature), against observed MODIS from the published files.
3. Circles of 5-100 km: the range of web/app.js exactSeries() (record weights inside the shape, background by the
   share of each cell's area, each cell's half-widths scaled by the share of its value inside the shape).
4. Where the shortfall comes from, from the models' own moments: single rows (cell x month x day/night, Suomi NPP
   alone, the unit the sealed exams scored), the two satellites averaged as independent, and cells added as
   independent.

Area-months are grouped by the ESTIMATE, never by the observed value, so the grouping cannot favour either side.

This test was not pre-registered. It was first run on 13 November 2026, after a review found the ranges too narrow,
and is reported whatever it shows. Nothing is tuned; no model, export or published file is changed.
Writes results.json and REPORT.md next to this file.
"""
import sys
sys.dont_write_bytecode = True
import argparse
import json
import math
import tempfile
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
WEB = REPO / "web" / "data"
sys.path.insert(0, str(REPO / "pipeline"))
sys.path.insert(0, str(REPO))
import export_v2 as ex  # noqa: E402
import weights_bd  # noqa: E402
import weights_r2  # noqa: E402
from weights_r2 import moment_quantiles  # noqa: E402

warnings.filterwarnings("ignore")
TEST_OBSERVED_END = "2019-12"            # the one change: 2020-01 onward is estimated, as 2022-01 onward is published
WINDOW = ("2020-01", "2021-12")
UNITS = {"burning": ("monthly_bd.json", "burning", weights_bd), "hotspots": ("monthly.json", "hotspots", weights_r2)}
BINS = [(0.5, 3), (3, 10), (10, 30), (30, float("inf"))]
BLOCKS = (1, 2, 4, 8)
RADII_KM = (5, 10, 25, 50, 100)
CIRCLES = 120                            # centres per region and unit, drawn from 2012-2019 Suomi NPP records
SEED = 20261113
SAT_FAMILY = {"N": "snpp", "J1": "noaa20"}
REGIONS = ex.regions_with("product")


def bin_name(a, b):
    return f"{a:g}-{b:g}" if math.isfinite(b) else f"{a:g}+"


def months_of(mon):
    return [str(p) for p in pd.period_range(mon["months"]["first"], periods=mon["months"]["n"], freq="M")]


def load(base, region, name):
    return json.loads((Path(base) / region / name).read_text(encoding="utf-8"))


def count(tab, key, inside, n):
    d = tab.setdefault(key, [0, 0])
    d[0] += int(inside)
    d[1] += int(n)


# ---------------------------------------------------------------- 1. the scratch export
def scratch_export(work):
    """The real exporter, observed era ended early, written outside web/data."""
    work = Path(work).resolve()
    assert work != WEB.resolve() and WEB.resolve() not in work.parents, "the scratch folder must not be web/data"
    out0, end0 = ex.OUT, ex.OBSERVED_END
    ex.OUT, ex.OBSERVED_END = work, TEST_OBSERVED_END
    try:
        for region in REGIONS:
            ex.export(region)
    finally:
        ex.OUT, ex.OBSERVED_END = out0, end0


def same_outside_window(work):
    """Every array of the scratch export equals the published one up to 2019-12 and from 2022-01."""
    out = {}
    for region in REGIONS:
        for unit, (name, _, _) in UNITS.items():
            a, b = load(work, region, name), load(WEB, region, name)
            ms = months_of(a)
            keep = [i for i, m in enumerate(ms) if m <= TEST_OBSERVED_END or m >= "2022-01"]
            same = a["cells"] == b["cells"] and all(
                np.array_equal(np.array(a[k])[:, keep], np.array(b[k])[:, keep]) for k in ("m", "bg", "p10", "p90"))
            flags = set(a["flags"][ms.index(WINDOW[0]):ms.index(WINDOW[1]) + 1])
            out[f"{region}/{unit}"] = {"identical": bool(same), "flags_in_window": sorted(flags)}
            assert same and flags <= set("ENJ"), (region, unit, same, flags)
    return out


# ---------------------------------------------------------------- 2. whole regions and blocks of cells
def blocks(work):
    tab, by_region = {}, {}
    for unit, (name, _, _) in UNITS.items():
        for region in REGIONS:
            est, pub = load(work, region, name), load(WEB, region, name)
            ms = months_of(est)
            t = np.array([WINDOW[0] <= m <= WINDOW[1] for m in ms])
            assert {pub["flags"][i] for i in np.flatnonzero(t)} == {"O"}, "the published window must be observed MODIS"
            M, lo, hi = (np.array(est[k])[:, t] for k in ("m", "p10", "p90"))
            O = np.array(pub["m"])[:, t]
            ix, iy = np.array(est["cells"]["ix"]), np.array(est["cells"]["iy"])
            for size in BLOCKS + ("region",):
                key = np.zeros(len(ix), int) if size == "region" else (ix // size) * 100000 + (iy // size)
                agg = lambda A: pd.DataFrame(A).groupby(key).sum().to_numpy()  # noqa: E731
                m_, o_ = agg(M), agg(O)
                l_ = np.maximum(0, m_ - np.sqrt(agg((M - lo) ** 2)))   # web/app.js regionSeries()
                h_ = m_ + np.sqrt(agg((hi - M) ** 2))
                ins = (o_ >= l_) & (o_ <= h_)
                for a, b in BINS:
                    s = (m_ >= a) & (m_ < b)
                    count(tab, (unit, str(size), bin_name(a, b)), ins[s].sum(), s.sum())
                if size == "region":
                    s = m_ >= 10
                    by_region[(unit, region)] = [int(ins[s].sum()), int(s.sum())]
    return tab, by_region


# ---------------------------------------------------------------- 3. circles
def records(base, region, unit, years):
    """Year files as a table: position, 0.25 degree cell, family, weight, month index from 2020-01."""
    folder = UNITS[unit][1]
    out = []
    for y in years:
        f = json.loads((Path(base) / region / folder / f"{y}.json").read_text(encoding="utf-8"))
        c = f["cols"]
        if unit == "burning":   # a burning day sits at the centre of its 0.01 degree square (web/app.js placeBurningDays)
            fx, fy = f["x0"] + np.array(c["x"]), f["y0"] + np.array(c["y"])
            lon, lat, cx, cy = (fx + 0.5) * 0.01, (fy + 0.5) * 0.01, fx // 25, fy // 25
            fam = np.array(c["fam"])
            modis, snpp = fam == 0, fam == 1
        else:
            lon, lat = np.array(c["lon"]), np.array(c["lat"])
            cx, cy = np.floor(lon / ex.CELL).astype(int), np.floor(lat / ex.CELL).astype(int)
            sensor = np.array(c["sensor"])
            modis, snpp = sensor <= 1, sensor == 2
        month = (pd.to_datetime(f"{y}-01-01") + pd.to_timedelta(np.array(c["doy"]) - 1, unit="D")).month.to_numpy()
        out.append(pd.DataFrame({"lon": lon, "lat": lat, "cx": cx, "cy": cy, "modis": modis, "snpp": snpp,
                                 "w": np.array(c["w"], float), "j": (y - 2020) * 12 + month - 1}))
    return pd.concat(out, ignore_index=True)


def circles(work):
    rng = np.random.default_rng(SEED)
    tab, touched = {}, {}
    for unit, (name, _, _) in UNITS.items():
        for region in REGIONS:
            est = load(work, region, name)
            j0 = months_of(est).index(WINDOW[0])
            M, P10, P90, BG = (np.array(est[k])[:, j0:j0 + 24] for k in ("m", "p10", "p90", "bg"))
            cix, ciy = np.array(est["cells"]["ix"]), np.array(est["cells"]["iy"])
            cmap = {(x, y): i for i, (x, y) in enumerate(zip(cix, ciy))}
            R = records(work, region, unit, (2020, 2021))
            R["ci"] = [cmap.get(k, -1) for k in zip(R.cx, R.cy)]
            H = records(WEB, region, unit, range(2012, 2020))
            centres = H[H.snpp].sample(CIRCLES, random_state=int(rng.integers(1e9)))[["lon", "lat"]].to_numpy()
            sub = (np.arange(8) + 0.5) / 8 * ex.CELL   # 8 x 8 points per cell for its share inside the circle
            gx, gy = cix[:, None, None] * ex.CELL + sub[None, :, None], ciy[:, None, None] * ex.CELL + sub[None, None, :]
            lon, lat = R.lon.to_numpy(), R.lat.to_numpy()
            for km in RADII_KM:
                for lon0, lat0 in centres:
                    kx, ky = 111.32 * math.cos(math.radians(lat0)), 110.57   # as web/app.js circleRing()
                    Q = R[((lon - lon0) * kx) ** 2 + ((lat - lat0) * ky) ** 2 <= km ** 2]
                    obs = np.bincount(Q.j[Q.modis], minlength=24)[:24].astype(float)
                    W = np.zeros(M.shape)
                    q = Q[(Q.w > 0) & (Q.ci >= 0)]
                    np.add.at(W, (q.ci.to_numpy(), q.j.to_numpy()), q.w.to_numpy())
                    frac = ((((gx - lon0) * kx) ** 2 + ((gy - lat0) * ky) ** 2) <= km ** 2).mean(axis=(1, 2))
                    est_m = np.bincount(Q.j, weights=Q.w, minlength=24)[:24] + (BG * frac[:, None]).sum(0)
                    with np.errstate(divide="ignore", invalid="ignore"):   # web/app.js exactSeries()
                        share = np.where((M > 0) & (W > 0), np.minimum(1, W / M), 0.0)
                    lo = np.maximum(0, est_m - np.sqrt((((M - P10) * share) ** 2).sum(0)))
                    hi = est_m + np.sqrt((((P90 - M) * share) ** 2).sum(0))
                    ins = (obs >= lo) & (obs <= hi)
                    for a, b in BINS:
                        s = (est_m >= a) & (est_m < b)
                        count(tab, (unit, f"{km} km", bin_name(a, b)), ins[s].sum(), s.sum())
                    touched.setdefault((unit, km), []).append(int((frac > 0).sum()))
    return tab, {f"{u}/{km} km": int(np.median(v)) for (u, km), v in touched.items()}


# ---------------------------------------------------------------- 4. where the shortfall comes from
def decompose():
    cov, ratio, corr, cross = {}, {}, {}, {}

    def add_ratio(key, err2, var):
        d = ratio.setdefault(key, [0.0, 0.0])
        d[0] += float(err2)
        d[1] += float(var)

    for unit, (_, _, impl) in UNITS.items():
        for region in REGIONS:
            det = ex.detections(region)
            det = det[det.month <= ex.HISTORY_END]
            first = max(ex.FIRST, ex.coverage(det[det.fam == "modis"])["first"])
            det = det[det.month >= first].sort_values(["acq_date", "acq_time", "sensor"]).reset_index(drop=True)
            months = ex.month_index(first, ex.HISTORY_END)
            det["mi"] = det.month.map({m: i for i, m in enumerate(months)})
            cells = det.groupby(["ix", "iy"]).size().reset_index()[["ix", "iy"]].sort_values(["iy", "ix"]).reset_index(drop=True)
            cell_index = {(r.ix, r.iy): i for i, r in enumerate(cells.itertuples())}
            det["ci"] = [cell_index[k] for k in zip(det.ix, det.iy)]
            shape = (len(cells), len(months))
            flags = "".join("E" if m >= WINDOW[0] else "O" for m in months)
            covering = {m: list(ex.VIIRS) for m in ex.month_index(ex.DRIFT_FROM, ex.HISTORY_END)}
            model = impl.fit(det, region)
            rec = ex.burning_day_records(det) if unit == "burning" else det
            slot_share = ex.slot_share_rule(covering, impl.prior_ratio_positive(model))
            grid = ex.cell_month_grid(rec, months, shape, slot_share, flags)
            if unit == "burning":
                v = rec[rec.sensor.isin(list(ex.VIIRS))]
                for sat in ex.VIIRS:
                    for dn in ("D", "N"):
                        for k in range(4):
                            arr = np.zeros(shape)
                            sel = v[(v.sensor == sat) & (v.dn == dn) & (v.k == k)]
                            np.add.at(arr, (sel.ci.to_numpy(), sel.mi.to_numpy()), 1)
                            grid[f"V_{sat}_{dn}_f{k}"] = arr.ravel()
            t = np.array([WINDOW[0] <= m <= WINDOW[1] for m in months])
            modis = rec[rec.fam == "modis"]
            OBS = {}
            for dn in ("D", "N"):
                A = np.zeros(shape)
                s_ = modis[modis.dn == dn]
                np.add.at(A, (s_.ci.to_numpy(), s_.mi.to_numpy()), 1)
                OBS[dn] = A[:, t]
            obs = OBS["D"] + OBS["N"]
            P = {}   # (satellite, day/night) -> forecast mean, variance, share of the month
            for sat, fam in SAT_FAMILY.items():
                for dn in ("D", "N"):
                    out = impl._predictive(model, fam, grid, dn)
                    P[(sat, dn)] = (np.asarray(out[0]).reshape(shape)[:, t], np.asarray(out[1]).reshape(shape)[:, t],
                                    grid[f"share_{sat}_{dn}"].to_numpy().reshape(shape)[:, t])

            def quantiles(mean, var):
                lo, hi = moment_quantiles(mean.ravel(), var.ravel(), (0.1, 0.9))
                return lo.reshape(mean.shape), hi.reshape(mean.shape)

            # rows: cell x month x day/night, Suomi NPP alone (the unit the sealed exams scored)
            for dn in ("D", "N"):
                m_, v_, _ = P[("N", dn)]
                y = OBS[dn]
                lo, hi = quantiles(m_, v_)
                ins = (y >= lo) & (y <= hi)
                active = (y > 0) | (grid[f"V_N_{dn}"].to_numpy().reshape(shape)[:, t] > 0)
                count(cov, (unit, "row", "active rows"), ins[active].sum(), active.sum())
                add_ratio((unit, "row, Suomi NPP alone (active rows)"), ((y - m_) ** 2)[active].sum(), v_[active].sum())
                for a, b in BINS:
                    s = (m_ >= a) & (m_ < b)
                    count(cov, (unit, "row", bin_name(a, b)), ins[s].sum(), s.sum())
            # cell-months as the product: both satellites, day + night
            mean = sum(P[k][2] * P[k][0] for k in P)
            var_app = sum(P[k][2] ** 2 * P[k][1] for k in P)   # as weights_*.cell_month_moments: satellites independent
            var_dep = sum(sum(P[(s, dn)][2] * np.sqrt(P[(s, dn)][1]) for s in ex.VIIRS) ** 2 for dn in ("D", "N"))
            lo_a, hi_a = quantiles(mean, var_app)
            lo_d, hi_d = quantiles(mean, var_dep)
            r = obs - mean
            tot, o = mean.sum(0), obs.sum(0)
            big = tot >= 10
            add_ratio((unit, "cell-month, satellites independent (as published)"), (r[:, big] ** 2).sum(), var_app[:, big].sum())
            add_ratio((unit, "cell-month, satellites fully dependent"), (r[:, big] ** 2).sum(), var_dep[:, big].sum())
            add_ratio((unit, "region-month, cells and satellites independent (as published)"), ((o - tot)[big] ** 2).sum(), var_app.sum(0)[big].sum())
            add_ratio((unit, "region-month, cells independent, satellites fully dependent"), ((o - tot)[big] ** 2).sum(), var_dep.sum(0)[big].sum())
            bounds = {"cells independent, satellites independent (as published)": (np.sqrt(((mean - lo_a) ** 2).sum(0)), np.sqrt(((hi_a - mean) ** 2).sum(0))),
                      "cells independent, satellites fully dependent": (np.sqrt(((mean - lo_d) ** 2).sum(0)), np.sqrt(((hi_d - mean) ** 2).sum(0))),
                      "cells fully dependent, satellites independent": ((mean - lo_a).sum(0), (hi_a - mean).sum(0)),
                      "cells fully dependent, satellites fully dependent": ((mean - lo_d).sum(0), (hi_d - mean).sum(0))}
            for label, (l, h) in bounds.items():
                ins = (o >= np.maximum(0, tot - l)) & (o <= tot + h)
                d = cov.setdefault((unit, "bound", label), [0, 0, 0.0])
                d[0] += int(ins[big].sum())
                d[1] += int(big.sum())
                d[2] += float(((l + h) / 2 / tot)[big].sum())
            # the two satellites' errors against the same MODIS value
            eN = sum(P[("N", dn)][0] for dn in ("D", "N")) - obs
            eJ = sum(P[("J1", dn)][0] for dn in ("D", "N")) - obs
            s = mean >= 3
            corr[(unit, region)] = {"cell_months": float(np.corrcoef(eN[s], eJ[s])[0, 1]), "n_cell_months": int(s.sum()),
                                    "region_months": float(np.corrcoef(eN.sum(0)[big], eJ.sum(0)[big])[0, 1]), "n_region_months": int(big.sum())}
            # errors of different cells in the same month, standardized, by distance
            z = np.where(mean >= 1, r / np.sqrt(np.maximum(var_dep, 1e-12)), np.nan)
            ix, iy = cells.ix.to_numpy(), cells.iy.to_numpy()
            dist = np.maximum(np.abs(ix[:, None] - ix[None, :]), np.abs(iy[:, None] - iy[None, :]))
            for label, sel in (("adjacent cells", dist == 1), ("2-3 cells apart", (dist >= 2) & (dist <= 3)), ("4 or more cells apart", dist >= 4)):
                d = cross.setdefault((unit, label), [0.0, 0])
                for j in range(z.shape[1]):
                    ok = ~np.isnan(z[:, j])
                    if ok.sum() >= 2:
                        D = sel[np.ix_(ok, ok)]
                        d[0] += float(np.outer(z[ok, j], z[ok, j])[D].sum())
                        d[1] += int(D.sum())
            d = cross.setdefault((unit, "same cell"), [0.0, 0])
            d[0] += float(np.nansum(z ** 2))
            d[1] += int(np.isfinite(z).sum())
    return cov, ratio, corr, cross


# ---------------------------------------------------------------- report
def pct(d):
    return f"{d[0]} of {d[1]} ({100 * d[0] / d[1]:.0f}%)" if d[1] else "none"


def write_report(res):
    names = {"portugal": "Portugal", "lebanon": "Lebanon", "syria": "Syria", "la_rioja": "La Rioja"}
    bins = [bin_name(*b) for b in BINS]
    L = ["# Do the 80% ranges hold 80%?", "",
         f"_Generated {res['generated_at']} by `python analysis/range_coverage/run_test.py`. Do not edit by hand._", "",
         "**No.** With 2020–2021 estimated exactly as 2022 onward is, the ranges held the observed MODIS value in "
         f"{pct(res['whole_region']['burning']['pooled'])} whole-region months in burning days and "
         f"{pct(res['whole_region']['hotspots']['pooled'])} in hotspots. Single cells, blocks of cells and circles with an "
         f"estimate of 3 or more held it in {res['summary']['areas_min_pct']}–{res['summary']['areas_max_pct']}% of area-months. "
         "The estimates themselves are not affected.", "",
         "This test was not pre-registered. It was first run on 13 November 2026, after a review found the ranges too "
         "narrow, and is reported whatever it shows. Nothing is tuned; no model, export or published file is changed.", "",
         "## Method", "",
         f"- The real exporter is run into a scratch folder with one change: the observed era ends at {TEST_OBSERVED_END} "
         "instead of 2021-12, so 2020–2021 is estimated from VIIRS as 2022 onward is. Both models are fitted on 2012–2019 "
         "either way. Every other month of the scratch files equals the published files (checked).",
         "- The ranges are built as the website builds them: whole regions and blocks as `regionSeries()` in `web/app.js`, "
         "circles as `exactSeries()`.",
         "- The reference is observed MODIS in 2020–2021, taken from the published files.",
         "- Area-months are grouped by the estimate, never by the observed value.", "",
         "## Whole regions: months with an estimate of 10 or more", "",
         "| Region | Burning days | Hotspots |", "|---|---|---|"]
    for r in REGIONS:
        L.append(f"| {names.get(r, r)} | " + " | ".join(pct(res["whole_region"][u][r]) for u in UNITS) + " |")
    L.append("| **All four** | " + " | ".join(f"**{pct(res['whole_region'][u]['pooled'])}**" for u in UNITS) + " |")
    for unit in UNITS:
        L += ["", f"## By area size, {'burning days' if unit == 'burning' else 'hotspots'}", "",
              "Share of area-months in which the range held the observed value, by the estimate of the area-month.", "",
              "| Area | " + " | ".join(f"Estimate {b}" for b in bins) + " |", "|---|" + "---|" * len(bins)]
        for km in RADII_KM:
            L.append(f"| Circle, {km} km (cells touched, median: {res['circle_cells_touched'][f'{unit}/{km} km']}) | "
                     + " | ".join(pct(res["areas"][unit][f"{km} km"][b]) for b in bins) + " |")
        for size in BLOCKS:
            L.append(f"| {'One cell' if size == 1 else f'Block of {size} × {size} cells'} | "
                     + " | ".join(pct(res["areas"][unit][str(size)][b]) for b in bins) + " |")
        L.append("| Whole region | " + " | ".join(pct(res["areas"][unit]["region"][b]) for b in bins) + " |")
    L += ["", f"Circles: {CIRCLES} centres per region and unit, drawn from the positions of 2012–2019 Suomi NPP records "
          f"(seed {SEED}), each used at every radius.",
          "Sums over several cells with an estimate under 3 do badly for a separate reason: adding half-widths in "
          "quadrature puts the lower end above zero (for example an estimate of 0.4 with a range of 0.4–0.5).", "",
          "## Where the shortfall comes from", "",
          "From the models' own forecast means and variances, 2020–2021.", "",
          "### Single rows: one cell, one month, day or night, Suomi NPP alone", "",
          "This is the unit the sealed exams scored. Pooled over active rows the coverage is near 80%, as in the exams; "
          "it falls as the forecast grows, because the forecast is close to Poisson for cells with a long history.", "",
          "| Rows | Burning days | Hotspots |", "|---|---|---|",
          "| Active rows (the exams' definition) | " + " | ".join(pct(res["rows"][u]["active rows"]) for u in UNITS) + " |"]
    for b in bins:
        L.append(f"| Forecast {b} | " + " | ".join(pct(res["rows"][u][b]) for u in UNITS) + " |")
    L += ["", "### Squared error ÷ the variance the model states (1.0 = calibrated)", "",
          "| Level | Burning days | Hotspots |", "|---|---|---|"]
    for label in res["variance_ratio"]["burning"]:
        L.append(f"| {label[0].upper() + label[1:]} | " + " | ".join(f"{res['variance_ratio'][u][label]:.1f}" for u in UNITS) + " |")
    L += ["", "### The two satellites err together", "",
          "Correlation between the Suomi NPP-based and the NOAA-20-based forecast errors against the same MODIS value. "
          "The published variance averages them as if this were 0.", "",
          "| Region | Burning days: cell-months / region-months | Hotspots: cell-months / region-months |", "|---|---|---|"]
    for r in REGIONS:
        L.append(f"| {names.get(r, r)} | " + " | ".join(
            f"{res['satellite_error_correlation'][u][r]['cell_months']:.2f} / {res['satellite_error_correlation'][u][r]['region_months']:.2f}" for u in UNITS) + " |")
    L += ["", "### Neighbouring cells err together", "",
          "Mean product of standardized errors of two cells in the same month (cell-months with a forecast of 1 or more); "
          "the same-cell row is the mean squared standardized error.", "",
          "| Pair | Burning days | Hotspots |", "|---|---|---|"]
    for label in res["cross_cell"]["burning"]:
        L.append(f"| {label[0].upper() + label[1:]} | " + " | ".join(f"{res['cross_cell'][u][label]:+.2f}" for u in UNITS) + " |")
    L += ["", "### No simple assumption fixes it", "",
          "Whole-region months with a forecast of 10 or more, from the models' unrounded moments (so the first row can "
          "differ from the first table by a month). Treating everything as fully dependent holds every month, with a "
          "range too wide to use.", "",
          "| Assumption | Burning days: held | mean half-width ÷ estimate | Hotspots: held | mean half-width ÷ estimate |", "|---|---|---|---|---|"]
    for label in res["bounds"]["burning"]:
        L.append(f"| {label[0].upper() + label[1:]} | " + " | ".join(
            f"{pct(res['bounds'][u][label]['held'])} | {100 * res['bounds'][u][label]['mean_half_width']:.0f}%" for u in UNITS) + " |")
    L += ["", "## Limits of this test", "",
          "- 24 months per region, and months of one region are not independent of each other.",
          "- Portugal, Lebanon and Syria were development regions: their 2012–2019 data helped choose the models. La "
          "Rioja was not. No region's 2020–2021 data was used to fit or choose them.",
          "- MODIS is the reference, so this tests the range as a statement about the MODIS-equivalent count, not about fires.",
          "- 2022 onward cannot be tested this way: there is no MODIS reference at nominal orbits.",
          "- A calibrated range would need its spread and the dependence between cells and satellites estimated on "
          "2012–2019, frozen, and tested once. That is future work; the published ranges are unchanged."]
    (HERE / "REPORT.md").write_text("\n".join(L) + "\n", encoding="utf-8", newline="\n")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--work", type=Path, help="scratch folder for the test export (default: temporary, deleted afterwards)")
    args = ap.parse_args()
    with tempfile.TemporaryDirectory(prefix="cedrus_range_") as tmp:
        work = args.work or Path(tmp)
        work.mkdir(parents=True, exist_ok=True)
        scratch_export(work)
        same = same_outside_window(work)
        tab, by_region = blocks(work)
        ctab, touched = circles(work)
    cov, ratio, corr, cross = decompose()
    bins = [bin_name(*b) for b in BINS]
    areas = {u: {} for u in UNITS}
    for (u, size, b), d in list(tab.items()) + list(ctab.items()):
        areas[u].setdefault(size, {})[b] = d
    whole = {u: {r: by_region[(u, r)] for r in REGIONS} for u in UNITS}
    for u in UNITS:
        whole[u]["pooled"] = [sum(whole[u][r][0] for r in REGIONS), sum(whole[u][r][1] for r in REGIONS)]
    shares = [d[0] / d[1] for u in UNITS for size, row in areas[u].items() if size != "region"
              for b, d in row.items() if b != bins[0] and d[1] >= 20]
    res = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "test": {"observed_era_ends": TEST_OBSERVED_END, "window": list(WINDOW), "pre_registered": False,
                 "circles_per_region": CIRCLES, "seed": SEED, "regions": REGIONS},
        "scratch_equals_published_outside_window": same,
        "whole_region": whole,
        "areas": areas,
        "circle_cells_touched": touched,
        "summary": {"areas_min_pct": round(100 * min(shares)), "areas_max_pct": round(100 * max(shares)),
                    "areas_rule": "single cells, blocks and circles; estimate of 3 or more; at least 20 area-months"},
        "rows": {u: {k[2]: d for k, d in cov.items() if k[0] == u and k[1] == "row"} for u in UNITS},
        "bounds": {u: {k[2]: {"held": d[:2], "mean_half_width": d[2] / d[1]} for k, d in cov.items() if k[0] == u and k[1] == "bound"} for u in UNITS},
        "variance_ratio": {u: {k[1]: d[0] / d[1] for k, d in ratio.items() if k[0] == u} for u in UNITS},
        "satellite_error_correlation": {u: {r: corr[(u, r)] for r in REGIONS} for u in UNITS},
        "cross_cell": {u: {k[1]: d[0] / d[1] for k, d in cross.items() if k[0] == u} for u in UNITS},
    }
    (HERE / "results.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8", newline="\n")
    write_report(res)
    print(f"-> {HERE / 'REPORT.md'}")


if __name__ == "__main__":
    main()
