"""Fire-weather normal per region, for the "Fire weather outlook" card (web/forecast.js).

For each region it picks one weather point (the 0.25 deg cell of our record nearest the burning-day-weighted centre of
the region's fires, so the point sits where fires burn, not in the sea or on a summit), downloads the ERA5 daily
series for 2003-2025 from the Open-Meteo archive (keyless, one call per region, a pause between calls), and writes
web/data/weather/<region>.json with:

  point             the weather point the browser also uses for the 7-day forecast
  week_q[d]         for each of 36 ten-day periods of the year (dekads: days 1-10, 11-20, 21-end of each month), the
                    0th, 5th, ..., 100th percentiles of the 7-day mean Hot-Dry-Windy Index over all 7-day windows
                    whose middle day falls in that dekad, 2003-2025
  day_q[d]          the same for single days (used to shade each forecast day)
  link              the honest check: monthly mean HDW against our monthly harmonized burning days (whole region)
  model_vs_era5     the forecast model's recent days against ERA5 for the same days (a second call), since the
                    outlook comes from forecast models and the normal from ERA5

Hot-Dry-Windy Index (Srock et al. 2018, Atmosphere 9:279): HDW = VPD (hPa) x wind speed (m/s). Srock et al. take the
maximum over the lowest 500 m of the atmosphere; here it is the surface version, daily maximum 2 m VPD x daily
maximum 10 m wind, the same way for the forecast and for the normal.

    python tools/fire_weather_normal.py               # all regions
    python tools/fire_weather_normal.py lebanon       # one region
Weather data: Open-Meteo (https://open-meteo.com), CC BY 4.0; ERA5 (Copernicus Climate Change Service).
"""
import datetime as dt
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web" / "data"
OUT = WEB / "weather"
FIRST, LAST = 2003, 2025
PAUSE = 3.0  # seconds between calls
UA = {"User-Agent": "cedrus-space-apps/1.0 (fire weather normal)"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def get(url, params, tries=4):
    q = url + "?" + urllib.parse.urlencode(params)
    for k in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(q, headers=UA), timeout=180) as r:
                return json.loads(r.read())
        except Exception as e:  # rate limit or network: wait and retry
            print(f"  retry {k + 1}: {e}", flush=True)
            time.sleep(20 * (k + 1))
    raise SystemExit(f"failed: {q}")


def weather_point(region_id):
    m = json.loads((WEB / region_id / "monthly_bd.json").read_text(encoding="utf-8"))
    ix = np.array(m["cells"]["ix"]); iy = np.array(m["cells"]["iy"])
    tot = np.array([sum(v for v in row if v) for row in m["m"]])
    lon = (ix + 0.5) * m["cell_deg"]; lat = (iy + 0.5) * m["cell_deg"]
    cx = float((lon * tot).sum() / tot.sum()); cy = float((lat * tot).sum() / tot.sum())
    busy = tot >= np.median(tot[tot > 0])  # a cell that burns as much as a typical fire cell
    d = np.where(busy, (lon - cx) ** 2 + (lat - cy) ** 2, np.inf)
    k = int(np.argmin(d))
    return round(float(lat[k]), 3), round(float(lon[k]), 3), m


def dekad(date):
    return (date.month - 1) * 3 + min(2, (date.day - 1) // 10)


def qs(values):
    return [round(float(v), 2) for v in np.percentile(values, np.arange(0, 101, 5))]


def regional_months(m):
    """Region total of our harmonized burning days per month, keyed 'YYYY-MM'."""
    y0, m0 = map(int, m["months"]["first"].split("-"))
    arr = np.array([[v or 0 for v in row] for row in m["m"]], dtype=float).sum(axis=0)
    out = {}
    for i, v in enumerate(arr):
        k = y0 * 12 + m0 - 1 + i
        if m["flags"][i] != "X":
            out[f"{k // 12}-{k % 12 + 1:02d}"] = float(v)
    return out


def link_check(days, hdw, m):
    """Monthly mean HDW vs our monthly burning days: rank correlation, and the top-tenth-of-months ratio.
    The seasonal cycle drives both, so the same is also done on anomalies (each month against its calendar-month
    median), which asks whether a hotter-drier-windier-than-usual July has more burning than a usual July."""
    bd = regional_months(m)
    by = {}
    for d, h in zip(days, hdw):
        by.setdefault(d[:7], []).append(h)
    keys = [k for k in sorted(by) if k in bd and len(by[k]) >= 28]
    if len(keys) < 60:
        return None
    x = np.array([np.mean(by[k]) for k in keys]); y = np.array([bd[k] for k in keys])
    mo = np.array([int(k[5:]) for k in keys])

    def spearman(a, b):
        ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
        return float(np.corrcoef(ra, rb)[0, 1])

    top = x >= np.percentile(x, 90)
    rest_mean = float(y[~top].mean())
    xa = x.copy(); ya = y.copy()
    for k in range(1, 13):
        s = mo == k
        xa[s] = x[s] - np.median(x[s]); ya[s] = y[s] - np.median(y[s])
    topa = xa >= np.percentile(xa, 90)
    return {
        "months": len(keys), "first": keys[0], "last": keys[-1],
        "spearman": round(spearman(x, y), 2),
        "top_tenth_mean_bd": round(float(y[top].mean()), 1), "rest_mean_bd": round(rest_mean, 1),
        "ratio": round(float(y[top].mean()) / rest_mean, 1) if rest_mean > 0 else None,
        "anomaly_spearman": round(spearman(xa, ya), 2),
        "anomaly_top_tenth_minus_usual_bd": round(float(ya[topa].mean()), 1),
        "anomaly_rest_minus_usual_bd": round(float(ya[~topa].mean()), 1),
    }


def model_vs_era5(lat, lon, era):
    """The forecast models' last ~60 analysed days against ERA5 for the same days, at the same point."""
    end = dt.date.today() - dt.timedelta(days=7)
    f = get("https://api.open-meteo.com/v1/forecast", {
        "latitude": lat, "longitude": lon, "daily": "vapour_pressure_deficit_max,wind_speed_10m_max",
        "wind_speed_unit": "ms", "past_days": 67, "forecast_days": 1, "timezone": "auto"})
    time.sleep(PAUSE)
    e = get("https://archive-api.open-meteo.com/v1/archive", {
        "latitude": lat, "longitude": lon, "start_date": (end - dt.timedelta(days=59)).isoformat(),
        "end_date": end.isoformat(), "daily": "vapour_pressure_deficit_max,wind_speed_10m_max",
        "wind_speed_unit": "ms", "timezone": "auto", "models": "era5"})
    fd = {t: (v, w) for t, v, w in zip(f["daily"]["time"], f["daily"]["vapour_pressure_deficit_max"], f["daily"]["wind_speed_10m_max"]) if v is not None and w is not None}
    pairs = [(fd[t][0] * 10 * fd[t][1], v * 10 * w) for t, v, w in zip(e["daily"]["time"], e["daily"]["vapour_pressure_deficit_max"], e["daily"]["wind_speed_10m_max"]) if t in fd and v is not None and w is not None]
    if len(pairs) < 30:
        return None
    a = np.array(pairs)
    return {"days": len(a), "median_forecast_model": round(float(np.median(a[:, 0])), 1),
            "median_era5": round(float(np.median(a[:, 1])), 1),
            "ratio": round(float(np.median(a[:, 0]) / max(np.median(a[:, 1]), 1e-6)), 2)}


def build(region):
    rid = region["id"]
    lat, lon, m = weather_point(rid)
    print(f"{rid}: point {lat}, {lon}", flush=True)
    r = get("https://archive-api.open-meteo.com/v1/archive", {
        "latitude": lat, "longitude": lon, "start_date": f"{FIRST}-01-01", "end_date": f"{LAST}-12-31",
        "daily": "vapour_pressure_deficit_max,wind_speed_10m_max", "wind_speed_unit": "ms", "timezone": "auto", "models": "era5"})
    days = r["daily"]["time"]; vpd = r["daily"]["vapour_pressure_deficit_max"]; wind = r["daily"]["wind_speed_10m_max"]
    ok = [i for i in range(len(days)) if vpd[i] is not None and wind[i] is not None]
    days = [days[i] for i in ok]
    hdw = np.array([vpd[i] * 10 * wind[i] for i in ok])  # kPa -> hPa, times m/s
    dates = [dt.date.fromisoformat(d) for d in days]
    dk = np.array([dekad(d) for d in dates])
    week = np.convolve(hdw, np.ones(7) / 7, mode="valid")  # 7-day means, middle day = i + 3
    wk = dk[3:3 + len(week)]
    day_q = [qs(hdw[dk == k]) for k in range(36)]
    week_q = [qs(week[wk == k]) for k in range(36)]
    time.sleep(PAUSE)
    try:
        bias = model_vs_era5(lat, lon, r)
    except SystemExit:
        bias = None
    out = {
        "region": rid, "name": region["name"], "point": {"lat": lat, "lon": lon, "elevation_m": r.get("elevation"),
        "how": "the 0.25 deg cell of our record nearest the burning-day-weighted centre of the region's fires"},
        "years": [FIRST, LAST], "source": "ERA5 (models=era5, 0.25 deg) via Open-Meteo archive API (CC BY 4.0)",
        "index": "Hot-Dry-Windy Index, surface version: daily max 2 m VPD (hPa) x daily max 10 m wind (m/s) (Srock et al. 2018)",
        "quantiles": "0,5,...,100th percentile", "dekads": "36 per year: days 1-10, 11-20, 21-end of each month",
        "day_q": day_q, "week_q": week_q,
        "link": link_check(days, hdw, m), "model_vs_era5": bias,
        "built": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%MZ"),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    b = json.dumps(out, separators=(",", ":"), ensure_ascii=False).encode("utf-8") + b"\n"
    (OUT / f"{rid}.json").write_bytes(re.sub(rb"(?<!\r)\n", b"\r\n", b))
    lk = out["link"] or {}
    print(f"  {len(days)} days; link rho={lk.get('spearman')} ratio={lk.get('ratio')} anomaly rho={lk.get('anomaly_spearman')}; model/ERA5={bias and bias['ratio']}", flush=True)


def main():
    regions = json.loads((WEB / "regions.json").read_text(encoding="utf-8"))["regions"]
    want = set(sys.argv[1:])
    for i, region in enumerate(r for r in regions if not want or r["id"] in want):
        if i:
            time.sleep(PAUSE)
        build(region)


if __name__ == "__main__":
    main()
