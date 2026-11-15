// Fire weather outlook: the next 7 days of weather that helps fires spread, for the region on screen, placed against
// that region's own normal. A forecast of CONDITIONS, not of fires. The 7-day forecast comes live from Open-Meteo
// (keyless); the normal (ERA5, 2003-2025) and the weather point are built offline by tools/fire_weather_normal.py
// into data/weather/<region>.json. Hot-Dry-Windy Index (Srock et al. 2018): VPD (hPa) x wind (m/s), daily maxima.
const $ = (s) => document.querySelector(s);
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
const API = 'https://api.open-meteo.com/v1/forecast';
const cache = {}; // region id -> Promise<{ normal, fc }>
let shownFor = null;

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
async function getJson(url, ms = 9000) {
  const ctl = new AbortController(); const t = setTimeout(() => ctl.abort(), ms);
  try { const r = await fetch(url, { signal: ctl.signal }); if (!r.ok) throw new Error(`HTTP ${r.status}`); return await r.json(); } finally { clearTimeout(t); }
}
async function load(id, meta) {
  const normal = await getJson(`data/weather/${id}.json?v=20261115e`, 30000).catch(() => null); // local, but queued behind the record's files
  const [x0, y0, x1, y1] = meta.bbox || [0, 0, 0, 0];
  const lat = normal?.point?.lat ?? (y0 + y1) / 2; const lon = normal?.point?.lon ?? (x0 + x1) / 2;
  const q = new URLSearchParams({ latitude: lat, longitude: lon, daily: 'temperature_2m_max,relative_humidity_2m_min,wind_speed_10m_max,precipitation_sum,vapour_pressure_deficit_max', hourly: 'soil_moisture_0_to_1cm', forecast_days: 7, timezone: 'auto', wind_speed_unit: 'ms' });
  const raw = await getJson(`${API}?${q}`);
  const d = raw.daily; const soil = {};
  (raw.hourly?.time || []).forEach((t, i) => { const v = raw.hourly.soil_moisture_0_to_1cm[i]; if (v != null) (soil[t.slice(0, 10)] ||= []).push(v); });
  const days = d.time.map((t, i) => {
    const vpd = d.vapour_pressure_deficit_max[i]; const wind = d.wind_speed_10m_max[i]; const s = soil[t];
    return { t, tmax: d.temperature_2m_max[i], rh: d.relative_humidity_2m_min[i], wind, rain: d.precipitation_sum[i], soil: s?.length ? s.reduce((a, b) => a + b, 0) / s.length : null, hdw: vpd != null && wind != null ? vpd * 10 * wind : null };
  }).filter((x) => x.hdw != null);
  if (days.length < 5) throw new Error('short forecast');
  return { normal, days, lat, lon };
}
// ten-day period of the year (0..35), as in the Python script
const dekad = (iso) => (Number(iso.slice(5, 7)) - 1) * 3 + Math.min(2, Math.floor((Number(iso.slice(8, 10)) - 1) / 10));
const dekadName = (k) => { const m = MONTHS[Math.floor(k / 3)]; return [`early ${m}`, `mid-${m}`, `late ${m}`][k % 3]; };
function pct(v, q) { // where v sits in quantiles q (0, 5, ..., 100th percentile)
  if (v <= q[0]) return 0; if (v >= q[q.length - 1]) return 100;
  for (let i = 1; i < q.length; i += 1) if (v <= q[i]) return 5 * (i - 1) + 5 * ((v - q[i - 1]) / Math.max(1e-9, q[i] - q[i - 1]));
  return 100;
}
// The forecast models ran hotter-drier-windier than ERA5 at most points over the last 60 days; compare like with like.
const scaleOf = (n) => { const r = n?.model_vs_era5?.ratio; return r && r > 0.4 && r < 3 ? r : 1; };

const MD = { Jan: 0, Feb: 1, Mar: 2, Apr: 3, May: 4, Jun: 5, Jul: 6, Aug: 7, Sep: 8, Oct: 9, Nov: 10, Dec: 11 };
function season(today) { // the app's own season dates (from our record), as shown in the Fire season card
  const a = $('#cal-start')?.textContent.trim(); const b = $('#cal-end')?.textContent.trim();
  const p = (s) => { const m = /^([A-Z][a-z]{2}) (\d{1,2})$/.exec(s || ''); return m && m[1] in MD ? [MD[m[1]], Number(m[2])] : null; };
  const s = p(a); const e = p(b); if (!s || !e) return null;
  const k = (x) => x[0] * 100 + x[1]; const t = k([Number(today.slice(5, 7)) - 1, Number(today.slice(8, 10))]);
  const inside = k(s) <= k(e) ? t >= k(s) && t <= k(e) : t >= k(s) || t <= k(e);
  return { inside, text: `${a}–${b}` };
}

function render() {
  const s = window.cedrus?.state; const box = $('#wx'); if (!s?.meta || !box) return;
  const id = s.meta.id; const seasonKey = `${$('#cal-start')?.textContent}|${$('#cal-end')?.textContent}`;
  const key = `${id}|${seasonKey}`; if (key === shownFor) return; shownFor = key;
  if (!cache[id]) cache[id] = load(id, s.meta);
  const name = s.meta.name;
  if (!box.innerHTML || box.dataset.region !== id) { box.hidden = false; box.className = 'wx loading'; box.dataset.region = id; box.innerHTML = '<p class="wx-quiet"><span>Loading the fire weather outlook…</span></p>'; }
  cache[id].then((r) => { if (!r.normal) delete cache[id]; if (window.cedrus.state.meta?.id === id) draw(box, r, name); })
    .catch(() => { delete cache[id]; if (window.cedrus.state.meta?.id !== id) return; box.className = 'wx off'; box.innerHTML = '<p class="wx-quiet"><span>Weather outlook unavailable right now</span></p>'; });
}

function draw(box, r, name) {
  const { normal, days } = r; const k = scaleOf(normal);
  const today = days[0].t; const mid = days[Math.min(3, days.length - 1)].t; const dk = dekad(mid);
  const week = days.reduce((a, x) => a + x.hdw, 0) / days.length;
  const p = normal ? pct(week / k, normal.week_q[dk]) : null;
  const level = p == null ? 'none' : p >= 90 ? 'high' : p >= 70 ? 'above' : p <= 25 ? 'low' : 'usual';
  const se = season(today);
  const yrs = normal ? `${normal.years[0]}–${normal.years[1]}` : '';
  const vs = p == null ? '' : p >= 99.5 ? `<strong class="wx-p">harsher than any</strong> ${dekadName(dk)} week in ${yrs}`
    : p <= 0.5 ? `<strong class="wx-p">milder than any</strong> ${dekadName(dk)} week in ${yrs}` : p >= 50
    ? `<strong class="wx-p">harsher than ${Math.round(p)}%</strong> of ${dekadName(dk)} weeks in ${yrs}`
    : `<strong class="wx-p">milder than ${Math.round(100 - p)}%</strong> of ${dekadName(dk)} weeks in ${yrs}`;
  const seas = se ? ` · <span>${se.inside ? 'inside the normal fire season' : 'outside the normal fire season'}</span> (${se.text})` : '';
  const top = Math.max(...days.map((x) => x.hdw), normal ? normal.day_q[dk][18] * k : 0, 1);
  const cols = days.map((x) => {
    const dp = normal ? pct(x.hdw / k, normal.day_q[dekad(x.t)]) : null;
    const c = dp == null ? '' : dp >= 90 ? ' high' : dp >= 70 ? ' above' : dp <= 25 ? ' low' : '';
    const h = Math.max(3, Math.round(34 * x.hdw / top)); const dow = DAYS[new Date(`${x.t}T12:00:00Z`).getUTCDay()];
    return `<li class="wx-day${c}" title="${x.t}: Hot-Dry-Windy Index ${Math.round(x.hdw)}${dp == null ? '' : `, higher than ${Math.round(dp)}% of ${dekadName(dekad(x.t))} days in ${yrs}`}"><i style="height:${h}px"></i><span>${dow}</span></li>`;
  }).join('');
  const f1 = (v) => (v == null ? '–' : (Math.round(v * 10) / 10).toFixed(v >= 10 || Number.isInteger(v) ? 0 : 1));
  const rows = days.map((x) => `<tr><th scope="row"><span>${DAYS[new Date(`${x.t}T12:00:00Z`).getUTCDay()]}</span> ${Number(x.t.slice(8, 10))}</th><td>${f1(x.tmax)}°</td><td>${f1(x.rh)}%</td><td>${f1(x.wind * 3.6)}</td><td>${f1(x.rain)}</td><td>${x.soil == null ? '–' : Math.round(x.soil * 100)}%</td><td>${Math.round(x.hdw)}</td></tr>`).join('');
  const lk = normal?.link; const mv = normal?.model_vs_era5;
  const link = lk ? `<p><b>Does fire weather track our record here?</b> ${esc(linkSentence(name, lk))}</p>` : '';
  const open = window.__uxOpen ? ' open' : '';
  box.className = `wx ${level}`;
  box.innerHTML = `<span class="wx-ico" aria-hidden="true"></span>
    <div class="wx-text"><p class="wx-title"><strong>Fire weather outlook</strong> · <span>next 7 days</span> · ${esc(name)}</p>
    <p class="wx-head">${p == null ? '<span>Comparison with the normal unavailable right now</span>' : `<span>Fire weather</span> ${vs}`}${seas}.</p>
    <div class="wx-foot"><span>Conditions that help fires spread, not a prediction of fires.</span>
    <details class="more info-tip wx-tip"${open}><summary aria-label="About this outlook" title="About this outlook"><span aria-hidden="true">i</span></summary><span class="tip-body">
      <p>Hot-Dry-Windy Index (HDW, Srock et al. 2018, <i>Atmosphere</i> 9:279): daily highest vapour pressure deficit (hPa) × highest wind (m/s), the surface version. It is high when air is hot, dry and windy at once. The headline compares this week’s mean HDW with every 7-day window centred in ${dekadName(dk)}, ${yrs} (ERA5), at one point where this region’s fires burn: ${r.lat.toFixed(2)}°, ${r.lon.toFixed(2)}°${normal?.point?.elevation_m != null ? `, ${Math.round(normal.point.elevation_m)} m` : ''}.${mv ? ` Forecast models ran ${mv.ratio}× ERA5’s HDW here over its last ${mv.days} analysed days, so the forecast is divided by ${mv.ratio} before comparing.` : ''} The fire season dates are our record’s (Fire season card).</p>
      ${link}<p>Weather: Open-Meteo (ECMWF/DWD/NOAA models; ERA5 for the normal), CC BY 4.0.</p></span></details> <span class="wx-src">Weather: Open-Meteo · CC BY 4.0</span></div>
    </div>
    <ol class="wx-days" aria-label="Hot-Dry-Windy Index, next 7 days">${cols}</ol>
    <details class="more wx-more"${open}><summary>Day by day</summary><div class="wx-table"><table><thead><tr><th></th><th scope="col">Hottest °C</th><th scope="col">Driest air (RH)</th><th scope="col">Wind km/h</th><th scope="col">Rain mm</th><th scope="col">Topsoil wet</th><th scope="col">HDW</th></tr></thead><tbody>${rows}</tbody></table></div></details>`;
}

function linkSentence(name, lk) {
  const span = `${lk.first.slice(0, 4)}–${lk.last.slice(0, 4)}`;
  const ratio = lk.ratio == null ? 'about the same' : lk.ratio >= 1.15 ? `${lk.ratio}× the burning days of the rest` : lk.ratio <= 0.87 ? `fewer burning days than the rest (${lk.ratio}×)` : 'about the same burning days as the rest';
  const strength = lk.anomaly_spearman >= 0.3 ? 'a moderate link' : lk.anomaly_spearman >= 0.15 ? 'a weak link' : 'little or no link';
  return `In ${name}, ${span}, the hottest-driest-windiest tenth of months (monthly mean HDW, ERA5) had ${ratio} (rank correlation ${lk.spearman}, mostly the seasons). Compared with the usual for the same calendar month, ${strength}: rank correlation ${lk.anomaly_spearman}. Weather at one point; burning days over the whole region.`;
}

async function start() {
  try { await window.cedrus?.ready; } catch { return; }
  render(); setInterval(render, 700);
}
const wait = setInterval(() => { if (window.cedrus) { clearInterval(wait); start(); } }, 200);
