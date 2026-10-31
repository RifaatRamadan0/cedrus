"""Candidate B steps 1-3: Suomi NPP passes, fire units, Aqua matching and the chance control.

Distances are great-circle-equivalent chords in km (points placed on a 6371 km sphere);
for the 1-3 km distances used here this equals the local projected distance.
"""
import numpy as np
import pandas as pd
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from .data import in_window

R_EARTH = 6371.0088
PASS_GAP_MIN = 30
UNIT_LINK_KM = 1.0
MATCH_DT_MIN = 60
SEPARATE = 1e4  # km between (pass or date) groups in the 4th coordinate: no pair can cross groups
DAY0 = pd.Timestamp("2011-12-31")


def xyz(lat, lon):
    la, lo = np.radians(lat), np.radians(lon)
    return np.c_[R_EARTH * np.cos(la) * np.cos(lo), R_EARTH * np.cos(la) * np.sin(lo), R_EARTH * np.sin(la)]


def day_number(dates):
    return ((pd.to_datetime(pd.Series(dates)) - DAY0).dt.days).to_numpy()


def build_units(px):
    """Suomi NPP pixels of one region -> (pixel table with unit ids, unit table)."""
    s = in_window(px)
    s = s[s.sensor == "snpp"].sort_values(["date", "dn", "tmin"]).reset_index(drop=True)
    new_group = (s.date != s.date.shift()) | (s.dn != s.dn.shift())
    new_pass = new_group | (s.tmin.diff() > PASS_GAP_MIN)
    s["pass_id"] = np.cumsum(new_pass.to_numpy()) - 1
    p = xyz(s.lat.to_numpy(), s.lon.to_numpy())
    pts = np.c_[p, s.pass_id.to_numpy() * SEPARATE]
    pairs = cKDTree(pts).query_pairs(UNIT_LINK_KM, output_type="ndarray")
    n = len(s)
    g = coo_matrix((np.ones(len(pairs)), (pairs[:, 0], pairs[:, 1])), shape=(n, n))
    _, s["unit"] = connected_components(g, directed=False)
    for i, c in enumerate("xyz"):
        s[c] = p[:, i]

    u = s.groupby("unit").agg(date=("date", "first"), dn=("dn", "first"), pass_id=("pass_id", "first"),
                              frp=("frp", "sum"), n_pix=("frp", "size"), tmin=("tmin", "mean"),
                              x=("x", "mean"), y=("y", "mean"), z=("z", "mean"))
    # a unit sits in the cell of its pixel nearest to the unit's centroid
    cx = u.loc[s.unit, ["x", "y", "z"]].to_numpy()
    s["d_centroid"] = np.linalg.norm(p - cx, axis=1)
    u["cell"] = s.loc[s.groupby("unit").d_centroid.idxmin().to_numpy(), "cell"].to_numpy()
    u["lat"] = np.degrees(np.arcsin(u.z / np.sqrt(u.x ** 2 + u.y ** 2 + u.z ** 2)))
    u["lon"] = np.degrees(np.arctan2(u.y, u.x))
    u["ym"] = u.date.str[:7]
    u["year"] = u.ym.str[:4].astype(int)
    u["moy"] = u.ym.str[5:7].astype(int)
    u["region"] = px.region.iloc[0]
    u = u.drop(columns=["x", "y", "z"]).reset_index()
    span = s.groupby("pass_id").tmin.agg(lambda t: t.max() - t.min())
    return s, u, {"passes": int(s.pass_id.nunique()), "max_pass_span_min": int(span.max()) if len(span) else 0}


def match(spix, aqua, shift_days, cross_midnight=False):
    """Number of Aqua pixels assigned to each unit, Aqua dates shifted by shift_days (0 = same date).

    cross_midnight=True is a diagnostic only (not the plan's rule): an Aqua pixel may also match a unit
    on the neighbouring UTC date when the clock times are within 60 min across midnight.
    """
    n_units = int(spix.unit.max()) + 1 if len(spix) else 0
    if not len(spix) or not len(aqua):
        return np.zeros(n_units, int)
    sk = day_number(spix.date) * 2 + (spix.dn.to_numpy() == "N")
    aday, at = day_number(aqua.date) + shift_days, aqua.tmin.to_numpy()
    aid = np.arange(len(aqua))
    if cross_midnight:
        aday, at, aid = np.r_[aday, aday + 1, aday - 1], np.r_[at, at - 1440, at + 1440], np.r_[aid, aid, aid]
    ak = aday * 2 + (aqua.dn.to_numpy()[aid] == "N")
    sp = np.c_[spix[["x", "y", "z"]].to_numpy(), sk * SEPARATE]
    ap = np.c_[xyz(aqua.lat.to_numpy()[aid], aqua.lon.to_numpy()[aid]), ak * SEPARATE]
    thr = (0.5 * np.sqrt(aqua.scan.to_numpy() ** 2 + aqua.track.to_numpy() ** 2) + 0.5)[aid]
    hits = cKDTree(ap).sparse_distance_matrix(cKDTree(sp), thr.max(), output_type="ndarray")
    i, j, d = hits["i"], hits["j"], hits["v"]
    ok = (d <= thr[i]) & (np.abs(at[i] - spix.tmin.to_numpy()[j]) <= MATCH_DT_MIN)
    i, j, d = aid[i[ok]], j[ok], d[ok]  # back to the original Aqua pixel
    order = np.lexsort((d, i))  # nearest first within each Aqua pixel
    i, j = i[order], j[order]
    first = np.r_[True, i[1:] != i[:-1]] if len(i) else np.zeros(0, bool)
    return np.bincount(spix.unit.to_numpy()[j[first]], minlength=n_units)


def units_with_matches(px):
    """Unit table with m (same date), c_minus (Aqua from date-1), c_plus (date+1) and c."""
    spix, u, info = build_units(px)
    aqua = px[px.sensor == "aqua"]  # 2012-01-01..2019-12-31: the chance control may reach one day outside the row window
    u["m"] = match(spix, aqua, 0)
    u["c_minus"] = match(spix, aqua, +1)  # Aqua on date-1, moved onto the unit's date
    u["c_plus"] = match(spix, aqua, -1)
    plus_ok = u.date < "2019-12-31"  # date+1 would be 2020: never read
    u["c"] = np.where(plus_ok, (u.c_minus + u.c_plus) / 2.0, u.c_minus)
    u["m_cross_midnight"] = match(spix, aqua, 0, cross_midnight=True)  # diagnostic only
    info["units_without_date_plus_1"] = int((~plus_ok).sum())
    info["night_units_within_60min_of_midnight"] = int(((u.dn == "N") & ((u.tmin < 60) | (u.tmin > 1380))).sum())
    info["night_units"] = int((u.dn == "N").sum())
    return u, info
