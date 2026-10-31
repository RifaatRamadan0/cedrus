// CEDRUS front end. Reads the static data contract that pipeline/export_v2.py writes into web/data/
// (layout in docs/DATA_CONTRACT.md). No build step: serve the web/ folder with any static server.
// MapLibre comes from a classic script tag; terra-draw is imported from the CDN once the map is up.

const $ = (selector) => document.querySelector(selector);
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const FLAG = { B: 'bridged', O: 'observed', E: 'estimated' };
const FLAG_TEXT = {
  B: 'Bridged: Terra alone, scaled up by Terra’s usual share of MODIS detections (2003–2011)',
  O: 'Observed by MODIS (Terra + Aqua)',
  E: 'Estimated from Suomi NPP VIIRS (MODIS drifted after 2021)',
};
const BASELINE_FIRST = 2003;
const SEASON_MIN = 20; // detections a year before a season can be dated
const FEW_FIRES = 5;   // baseline median below this: "few fires here"
const Z80 = 1.2815515655446004; // standard normal 90th percentile
// cividis (Nuñez, Anderton & Renslow 2018), sampled; colour-blind safe and monotone in lightness
const CIVIDIS = ['#00204d', '#00336f', '#39486b', '#575c6d', '#707173', '#8a8779', '#a69d75', '#c4b56c', '#e4cf5b', '#ffea46'];
// ColorBrewer PuOr, 11 classes: purple = fewer fires than the mean, orange = more
const PUOR = ['#2d004b', '#542788', '#8073ac', '#b2abd2', '#d8daeb', '#f7f7f7', '#fee0b6', '#fdb863', '#e08214', '#b35806', '#7f3b08'];
const ZERO = '#c9ced3';
const PANEL = '#0c1924'; // uncertain cells fade toward the panel behind them

const state = {
  index: null, meta: null, monthly: null, drift: null,
  area: null, areaCells: [], series: null, sel: null, focus: null, vmax: 1, cellMax: 1,
  mode: 'counts', record: 'harmonized', ref: 'median', table: false, defaultJ: null,
  map: null, draw: null, drawing: null, drawnAt: -1e9, hot: new Map(), seasonToken: 0,
};
let toastTimer;

function toast(message) {
  $('.toast').textContent = message; $('.toast').classList.add('visible');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => $('.toast').classList.remove('visible'), 4200);
}

function getJson(path) {
  return fetch(path).then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status} for ${path}`); return r.json(); });
}

// ---------- numbers ----------
function fmt(v) {
  if (v == null || Number.isNaN(v)) return '–';
  if (Math.abs(v) < 10 && Math.abs(v - Math.round(v)) > 0.005) return v.toFixed(1);
  return Math.round(v).toLocaleString('en-US');
}
function signedPct(x) {
  if (x == null || !Number.isFinite(x)) return '–';
  const p = Math.round(x * 100);
  return `${p > 0 ? '+' : ''}${p}%`;
}
function quantile(sorted, q) {
  if (!sorted.length) return NaN;
  const i = (sorted.length - 1) * q; const lo = Math.floor(i); const hi = Math.ceil(i);
  return sorted[lo] + (sorted[hi] - sorted[lo]) * (i - lo);
}
function normalCdf(x) { // Abramowitz & Stegun 7.1.26, |error| < 1.5e-7
  const t = 1 / (1 + 0.3275911 * Math.abs(x) / Math.SQRT2);
  const y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * Math.exp(-x * x / 2);
  return x >= 0 ? (1 + y) / 2 : (1 - y) / 2;
}
function mix(a, b, t) {
  const pa = [1, 3, 5].map((k) => parseInt(a.slice(k, k + 2), 16));
  const pb = [1, 3, 5].map((k) => parseInt(b.slice(k, k + 2), 16));
  return `#${pa.map((v, k) => Math.round(v + (pb[k] - v) * t).toString(16).padStart(2, '0')).join('')}`;
}
function ramp(colors, t) {
  const x = Math.min(1, Math.max(0, t)) * (colors.length - 1);
  const i = Math.min(colors.length - 2, Math.floor(x));
  return mix(colors[i], colors[i + 1], x - i);
}
function countColor(v, vmax) { return v < 0.005 ? ZERO : ramp(CIVIDIS, 0.12 + 0.88 * (Math.log10(1 + v) / Math.log10(1 + vmax))); }

// ---------- months ----------
function monthOf(j) { // index -> {year, moy (1..12)}
  const [y0, m0] = state.monthly.months.first.split('-').map(Number);
  const k = y0 * 12 + (m0 - 1) + j;
  return { year: Math.floor(k / 12), moy: (k % 12) + 1 };
}
function indexOf(year, moy) {
  const [y0, m0] = state.monthly.months.first.split('-').map(Number);
  const j = (year * 12 + moy - 1) - (y0 * 12 + m0 - 1);
  return j >= 0 && j < state.monthly.months.n ? j : -1;
}
function label(j) { const { year, moy } = monthOf(j); return `${MONTH_NAMES[moy - 1]} ${year}`; }
function iso(j) { const { year, moy } = monthOf(j); return `${year}-${String(moy).padStart(2, '0')}`; }
function years() {
  const first = Number(state.monthly.months.first.slice(0, 4)); const last = Number(state.monthly.months.last.slice(0, 4));
  return Array.from({ length: last - first + 1 }, (_, i) => first + i);
}

// ---------- geometry ----------
function inRing(lon, lat, ring) { // ray casting on lon/lat; fine at the scale of a country
  let inside = false;
  for (let i = 0, k = ring.length - 1; i < ring.length; k = i++) {
    const [xi, yi] = ring[i]; const [xk, yk] = ring[k];
    if ((yi > lat) !== (yk > lat) && lon < ((xk - xi) * (lat - yi)) / (yk - yi) + xi) inside = !inside;
  }
  return inside;
}
function circleRing(lat, lon, km, steps = 72) {
  const ring = [];
  for (let i = 0; i <= steps; i += 1) {
    const a = (i / steps) * 2 * Math.PI;
    ring.push([lon + (km * Math.cos(a)) / (111.32 * Math.cos((lat * Math.PI) / 180)), lat + (km * Math.sin(a)) / 110.57]);
  }
  return ring;
}
function bboxRing([x0, y0, x1, y1]) { return [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]; }
function ringBounds(ring) {
  const xs = ring.map((p) => p[0]); const ys = ring.map((p) => p[1]);
  return [[Math.min(...xs), Math.min(...ys)], [Math.max(...xs), Math.max(...ys)]];
}
function regionForRing(ring) {
  const [[x0, y0], [x1, y1]] = ringBounds(ring);
  const cx = (x0 + x1) / 2; const cy = (y0 + y1) / 2;
  const regions = state.index.regions;
  return regions.find((r) => cx >= r.bbox[0] && cx <= r.bbox[2] && cy >= r.bbox[1] && cy <= r.bbox[3])
    || regions.find((r) => x0 < r.bbox[2] && x1 > r.bbox[0] && y0 < r.bbox[3] && y1 > r.bbox[1]) || null;
}

// ---------- the area and its monthly series ----------
function areaCells(area) {
  const { ix, iy } = state.monthly.cells; const deg = state.monthly.cell_deg;
  const out = [];
  for (let c = 0; c < ix.length; c += 1) {
    if (area.kind === 'region' || inRing((ix[c] + 0.5) * deg, (iy[c] + 0.5) * deg, area.ring)) out.push(c);
  }
  return out;
}

function buildSeries(cells) {
  const { m, p10, p90, naive, months } = state.monthly; const n = months.n;
  const bgs = state.monthly.bg; // optional background term, already included in m
  const s = { m: new Float64Array(n), lo: new Float64Array(n), hi: new Float64Array(n), naive: new Float64Array(n), bg: new Float64Array(n) };
  const lw = new Float64Array(n); const hw = new Float64Array(n);
  for (const c of cells) {
    const mc = m[c]; const lc = p10[c]; const hc = p90[c]; const nc = naive[c];
    for (let j = 0; j < n; j += 1) {
      s.m[j] += mc[j]; s.naive[j] += nc[j]; if (bgs) s.bg[j] += bgs[c][j];
      lw[j] += (mc[j] - lc[j]) ** 2; hw[j] += (hc[j] - mc[j]) ** 2;
    }
  }
  // Area range: central values summed, each side's half-width combined in quadrature (approximate: cells treated as independent).
  for (let j = 0; j < n; j += 1) { s.lo[j] = Math.max(0, s.m[j] - Math.sqrt(lw[j])); s.hi[j] = s.m[j] + Math.sqrt(hw[j]); }
  return s;
}

function value(j, record = state.record) { return record === 'naive' ? state.series.naive[j] : state.series.m[j]; }

function baseline(selYear, moy, record = state.record) {
  const vals = [];
  for (let y = BASELINE_FIRST; y < selYear; y += 1) { const j = indexOf(y, moy); if (j >= 0) vals.push(value(j, record)); }
  const sorted = [...vals].sort((a, b) => a - b);
  return {
    years: vals.length, first: BASELINE_FIRST, last: selYear - 1, sorted,
    mean: vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : NaN,
    median: quantile(sorted, 0.5), iqr: quantile(sorted, 0.75) - quantile(sorted, 0.25),
  };
}

// R = half-width of the month's 80% range / max(|estimate - baseline median|, baseline IQR / 2):
// a month far from normal is judged against that distance, a near-normal one against the usual spread.
// No range (observed months) -> 0.
function trustRatio(j, base) {
  const half = (state.series.hi[j] - state.series.lo[j]) / 2;
  if (half <= 1e-9) return 0;
  const scale = Math.max(Math.abs(state.series.m[j] - base.median), base.iqr / 2);
  return scale > 0 ? half / scale : Infinity;
}

// The month a new area opens on: the most recent one that normally has at least FEW_FIRES detections.
function defaultMonth() {
  const last = state.monthly.months.n - 1;
  for (let j = last; j >= 0; j -= 1) {
    const { year, moy } = monthOf(j); const b = baseline(year, moy, 'harmonized');
    if (b.years && b.median >= FEW_FIRES) return j;
  }
  return last;
}

// ---------- calendar ----------
function cellView(j, bases) {
  if (j < 0) return { bg: null, text: 'no data', nd: true };
  const v = value(j); const { moy } = monthOf(j); const flag = state.monthly.flags[j];
  let bg; let text;
  if (state.mode === 'counts') {
    bg = countColor(v, state.vmax);
    text = `${fmt(v)} detections`;
  } else {
    const b = bases[moy]; const ref = b[state.ref];
    if (!b.years) { bg = null; text = `${fmt(v)} detections, no baseline`; } else if (ref > 0) {
      const r = v / ref; const t = Math.max(-2, Math.min(2, Math.log2(Math.max(r, 1e-9))));
      bg = ramp(PUOR, (t + 2) / 4); text = `${signedPct(r - 1)} vs ${b.first}–${b.last} ${state.ref} (${fmt(v)} vs ${fmt(ref)})`;
    } else { bg = v > 0 ? PUOR[10] : PUOR[5]; text = v > 0 ? `${fmt(v)} detections where the ${state.ref} is 0` : `0, and the ${state.ref} is 0`; }
  }
  let trust = ''; let hatch = false;
  if (state.record === 'harmonized' && bg && bases[moy].years) {
    const R = trustRatio(j, bases[moy]);
    if (R > 0) {
      bg = mix(bg, PANEL, 0.65 * Math.min(1, Math.max(0, R - 0.5))); // opacity 1 -> 0.35 as R goes 0.5 -> 1.5
      hatch = R > 1;
      trust = `, trust ratio ${Number.isFinite(R) ? R.toFixed(2) : 'unbounded'} (${R < 0.5 ? 'reliable' : R <= 1 ? 'use with care' : 'too uncertain'})`;
    }
  }
  return { bg, hatch, text: `${text} · ${FLAG[flag]}${trust}`, flag };
}

function renderCalendar() {
  const ys = years(); const selYear = monthOf(state.sel).year;
  const bases = {}; for (let moy = 1; moy <= 12; moy += 1) bases[moy] = baseline(selYear, moy);
  let vmax = 1; for (let j = 0; j < state.series.m.length; j += 1) vmax = Math.max(vmax, state.series.m[j], state.series.naive[j]);
  state.vmax = vmax; // one scale for both records, so the naive 2012 jump is not rescaled away
  const focus = state.focus ?? state.sel;
  let html = `<div class="cal-row cal-head" role="row"><span class="cal-corner" role="columnheader">Year</span>${MONTHS.map((m, i) => `<span role="columnheader" aria-label="${MONTH_NAMES[i]}">${m[0]}<i>${m.slice(1)}</i></span>`).join('')}</div>`;
  let rows = '';
  for (const y of ys) {
    html += `<div class="cal-row" role="row"><span class="cal-year" role="rowheader">${y}</span>`;
    rows += `<tr><th scope="row">${y}</th>`;
    for (let moy = 1; moy <= 12; moy += 1) {
      const j = indexOf(y, moy); const c = cellView(j, bases);
      const name = `${MONTH_NAMES[moy - 1]} ${y}`;
      const cls = ['cal-cell', c.nd ? 'nd' : '', c.flag === 'B' ? 'b' : '', c.flag === 'E' ? 'e' : '', j >= 0 && j === state.sel ? 'sel' : '', !c.nd && !c.bg ? 'nb' : '', c.hatch ? 'hz' : ''].filter(Boolean).join(' ');
      const style = c.bg ? ` style="background-color:${c.bg}"` : '';
      html += `<span role="gridcell" class="${cls}"${style} data-j="${j}" data-year="${y}" data-moy="${moy}" tabindex="${j >= 0 && j === focus ? 0 : -1}" aria-selected="${j >= 0 && j === state.sel}" aria-label="${name}: ${c.text}" title="${name}: ${c.text}"></span>`;
      rows += `<td>${c.nd ? '<span class="muted">no data</span>' : `${fmt(value(j))}${c.flag !== 'O' ? ` <small>${FLAG[c.flag]}</small>` : ''}`}</td>`;
    }
    html += '</div>'; rows += '</tr>';
  }
  const grid = $('#cal-grid');
  const hadFocus = grid.contains(document.activeElement);
  grid.innerHTML = html;
  grid.dataset.cells = String(grid.querySelectorAll('[role=gridcell]').length);
  if (hadFocus) grid.querySelector('[tabindex="0"]')?.focus();
  $('#calendar-table').innerHTML = `<table class="cal-table"><caption>${state.record === 'naive' ? 'Naive merge' : 'Harmonized estimate (expected value)'}: detections per month, ${areaName()}</caption><thead><tr><th scope="col">Year</th>${MONTHS.map((m) => `<th scope="col">${m}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table>`;
  renderLegend();
  const b = bases[1];
  $('#calendar-note').textContent = (state.record === 'naive'
    ? 'Naive merge: MODIS up to 2011, then raw Suomi NPP counts. Watch 2012.'
    : 'Harmonized estimate (expected value), in MODIS-equivalent detections.')
    + (state.mode === 'anomaly' ? (b.years ? ` Colour: each month vs its ${b.first}–${b.last} ${state.ref}.` : ' No baseline years before the selected month: pick 2004 or later.') : ' Colour: detections per month (log scale).')
    + (state.mode === 'anomaly' && b.years ? (state.ref === 'median' ? ' Median by default: one extreme year cannot move it.' : ' The mean is pulled up by the few worst years; the median is the sturdier normal.') : '')
    + ' Cell-level approximation, 0.25°.';
}

function renderLegend() {
  const marks = [];
  if (state.mode === 'counts') {
    const k = CIVIDIS.length - 1;
    const stops = CIVIDIS.map((_, i) => `${ramp(CIVIDIS, 0.12 + 0.88 * (i / k))} ${(i / k) * 100}%`).join(',');
    const ticks = [1, 10, 100, 1000, 10000].filter((t) => t <= state.vmax).map((t) => `<span style="left:${(Math.log10(1 + t) / Math.log10(1 + state.vmax)) * 100}%">${t.toLocaleString('en-US')}</span>`).join('');
    marks.push(`<div class="ramp"><b>Detections per month</b><i style="background:linear-gradient(90deg,${stops})"></i><div class="ticks">${ticks}</div></div>`);
  } else {
    const stops = PUOR.map((c, i) => `${c} ${(i / (PUOR.length - 1)) * 100}%`).join(',');
    const ticks = [[-0.75, '−75%'], [-0.5, '−50%'], [0, state.ref], [1, '+100%'], [3, '+300%']]
      .map(([p, l]) => `<span style="left:${((Math.log2(1 + p) + 2) / 4) * 100}%">${l}</span>`).join('');
    marks.push(`<div class="ramp"><b>Compared with the baseline ${state.ref}</b><i style="background:linear-gradient(90deg,${stops})"></i><div class="ticks">${ticks}</div></div>`);
  }
  marks.push(`<ul class="keys">${state.mode === 'counts' ? '<li><span class="sw zero"></span>zero</li>' : ''}<li><span class="sw nd"></span>no data</li><li><span class="sw b"></span>bridged</li><li><span class="sw e"></span>estimated</li>${state.record === 'harmonized' ? '<li><span class="sw faded"></span>faded = use with care</li><li><span class="sw hz"></span>faded + hatched = too uncertain</li>' : ''}</ul>`);
  $('#calendar-legend').innerHTML = marks.join('');
}

function moveFocus(cell, dYear, dMonth) {
  const y = Number(cell.dataset.year) + dYear; const moy = Number(cell.dataset.moy) + dMonth;
  const next = $(`#cal-grid [data-year="${y}"][data-moy="${moy}"]`);
  if (!next) return;
  cell.tabIndex = -1; next.tabIndex = 0; next.focus();
  state.focus = Number(next.dataset.j);
}

function selectMonth(j) {
  if (j < 0) { toast('No satellite data for that month.'); return; }
  state.sel = j; state.focus = j;
  renderCalendar(); renderMonth(); renderMapValues(); renderSeason();
}

// ---------- the selected month ----------
function renderMonth() {
  const j = state.sel; const { year, moy } = monthOf(j); const flag = state.monthly.flags[j];
  const v = state.series.m[j]; const lo = state.series.lo[j]; const hi = state.series.hi[j];
  const base = baseline(year, moy, 'harmonized');
  const mn = MONTH_NAMES[moy - 1];
  const last = state.monthly.months.n - 1;
  $('#month-eyebrow').textContent = j === last ? 'LATEST MONTH IN THE RECORD' : j === state.defaultJ ? 'MOST RECENT MONTH WITH A FIRE NORMAL' : 'SELECTED MONTH';
  $('#month-title').textContent = `${label(j)} · ${areaName()}`;
  const ranged = hi - lo > 1e-9;
  const rows = [];
  rows.push(`<p class="big-value"><strong id="month-value">${fmt(v)}</strong> fire detections, harmonized estimate (expected value)${ranged ? ` <span>80% range ${fmt(lo)}–${fmt(hi)} (approximate)</span>` : ''}</p>`);
  rows.push(`<p class="source-line"><span class="flag ${FLAG[flag]}">${FLAG[flag]}</span>${FLAG_TEXT[flag]}.</p>`);
  if (!base.years) {
    rows.push('<p class="hint">No baseline years before this month (the baseline starts in 2003). Pick a month in 2004 or later to compare.</p>');
  } else {
    const below = base.sorted.filter((x) => x < v).length; const ties = base.sorted.filter((x) => x === v).length;
    const rank = ((below + ties / 2) / base.years) * 100;
    const sd = (hi - lo) / (2 * Z80);
    const pAbove = sd > 0 ? 1 - normalCdf((base.median - v) / sd) : v > base.median ? 1 : v < base.median ? 0 : 0.5;
    const R = trustRatio(j, base);
    const verdict = R < 0.5 ? ['reliable', 'Reliable'] : R <= 1 ? ['care', 'Use with care'] : ['uncertain', 'Too uncertain'];
    const vsMed = base.median > 0 ? signedPct(v / base.median - 1) : v > 0 ? 'above (median is 0)' : 'same (median is 0)';
    const vsMean = base.mean > 0 ? signedPct(v / base.mean - 1) : v > 0 ? 'above (mean is 0)' : 'same (mean is 0)';
    rows.push(`<dl class="stats">
      <div><dt>Normal ${mn} (median)</dt><dd>${fmt(base.median)} <span>this month ${vsMed}</span></dd></div>
      <div><dt>Multi-year mean</dt><dd>${fmt(base.mean)} <span>this month ${vsMean}</span></dd></div>
      <div><dt>Rank among baseline years</dt><dd>${Math.round(rank)}<span> percentile</span></dd></div>
      <div><dt>Chance it is above the median</dt><dd>${Math.round(pAbove * 100)}%</dd></div>
    </dl>`);
    rows.push(`<p class="hint">Baseline: ${mn} in ${base.first}–${base.last} (${base.years} years), harmonized estimates.${sd > 0 ? ' The chance uses a normal approximation of the 80% range.' : ''}</p>`);
    rows.push(`<div class="trust ${verdict[0]}" id="trust"><strong>Trust check: ${verdict[1]}</strong>
      <span>R = ${Number.isFinite(R) ? R.toFixed(2) : 'unbounded'}: half of this month’s 80% range (${fmt((hi - lo) / 2)}) compared with how far this month is from normal (${fmt(Math.abs(v - base.median))} from the median), or the usual year-to-year spread of ${mn} (interquartile range ${fmt(base.iqr)} ÷ 2 = ${fmt(base.iqr / 2)}), whichever is larger. Below 0.5 reliable, 0.5–1 use with care, above 1 too uncertain.</span>
      ${base.median < FEW_FIRES ? `<em>Few fires here: a normal ${mn} has fewer than ${FEW_FIRES} detections in this area, so small changes are mostly chance.</em>` : ''}</div>`);
  }
  if (j === state.defaultJ && j !== last) rows.push(`<p class="hint">Opened on this month because it is the most recent one that normally has at least ${FEW_FIRES} detections in this area. The record runs to ${label(last)}.</p>`);
  if (Math.abs(state.series.naive[j] - v) > 0.005) rows.push(`<p class="hint">The naive merge would say ${fmt(state.series.naive[j])} for this month.</p>`);
  $('#month-body').innerHTML = rows.join('');
}

// ---------- hotspots (loaded only when a download or the season dates need them) ----------
function loadYear(year) {
  const key = `${state.meta.id}/${year}`;
  if (!state.hot.has(key)) {
    const p = state.meta.hotspot_years.includes(year) ? getJson(`data/${state.meta.id}/hotspots/${year}.json`) : Promise.resolve(null);
    state.hot.set(key, p.catch((err) => { state.hot.delete(key); throw err; }));
  }
  return state.hot.get(key);
}
function hotspotInArea(cols, i, area) { return area.kind === 'region' || inRing(cols.lon[i], cols.lat[i], area.ring); }

async function renderSeason() {
  const token = ++state.seasonToken;
  const selYear = monthOf(state.sel).year;
  const ys = []; for (let y = BASELINE_FIRST; y < selYear; y += 1) ys.push(y);
  const set = (k, a, b) => { $(`#cal-${k}`).textContent = a; $(`#cal-${k}-spread`).textContent = b; };
  ['start', 'peak', 'end'].forEach((k) => set(k, '…', ''));
  $('#season-eyebrow').textContent = `FIRE SEASON · ${areaName().toUpperCase()}`;
  if (!ys.length) { ['start', 'peak', 'end'].forEach((k) => set(k, '–', '')); $('#season-note').textContent = 'No baseline years before the selected month.'; return; }
  $('#season-note').textContent = `Reading detections for ${ys[0]}–${ys.at(-1)}…`;
  let files;
  try { files = await Promise.all(ys.map(loadYear)); } catch (err) { if (token === state.seasonToken) $('#season-note').textContent = `Could not load detections (${err.message}).`; return; }
  if (token !== state.seasonToken) return;
  const area = state.area; const totals = []; const dates = [];
  for (const f of files) {
    const daily = new Float64Array(367);
    if (f) { const c = f.cols; for (let i = 0; i < f.n; i += 1) if (c.w[i] > 0 && hotspotInArea(c, i, area)) daily[c.doy[i]] += c.w[i]; }
    const total = daily.reduce((a, b) => a + b, 0); totals.push(total);
    if (total >= SEASON_MIN) {
      let cum = 0; const d = [];
      for (let doy = 1; doy <= 366 && d.length < 3; doy += 1) { cum += daily[doy]; while (d.length < 3 && cum >= [0.1, 0.5, 0.9][d.length] * total - 1e-9) d.push(doy); }
      dates.push(d);
    }
  }
  const medTotal = quantile([...totals].sort((a, b) => a - b), 0.5);
  $('#season-dates').dataset.state = medTotal < SEASON_MIN || !dates.length ? 'too-few' : 'dated';
  if (medTotal < SEASON_MIN || !dates.length) {
    ['start', 'peak', 'end'].forEach((k) => set(k, '–', ''));
    $('#season-note').textContent = `Too few fires here to date a season: a typical year in ${ys[0]}–${ys.at(-1)} has ${fmt(medTotal)} detections in this area, and dating needs at least ${SEASON_MIN}.`;
    return;
  }
  ['start', 'peak', 'end'].forEach((k, q) => {
    const s = dates.map((d) => d[q]).sort((a, b) => a - b);
    const med = quantile(s, 0.5); const spread = (quantile(s, 0.75) - quantile(s, 0.25)) / 2;
    const day = new Date(Date.UTC(2001, 0, Math.round(med)));
    set(k, `${MONTHS[day.getUTCMonth()]} ${day.getUTCDate()}`, `± ${Math.round(spread)} days`);
  });
  $('#season-note').textContent = `Median day when 10%, 50% and 90% of the year’s detections had happened, over the ${dates.length} years in ${ys[0]}–${ys.at(-1)} with at least ${SEASON_MIN} detections in this area (individual detections in the exact area, weighted as in the harmonized estimate). ± is half the interquartile range across years.`;
}

// ---------- drift ----------
function monthName(fy, fm, i) { const k = fy * 12 + fm - 1 + i; return `${MONTHS[k % 12]} ${Math.floor(k / 12)}`; }

function renderDrift() {
  const d = state.drift; const svg = $('#drift-chart');
  const n = d.months.n; const [fy, fm] = d.months.first.split('-').map(Number);
  const x0 = 34; const x1 = 420; const y0 = 140; const y1 = 12;
  const lo = 0.4; const hi = 1.6;
  const X = (i) => x0 + (i / Math.max(1, n - 1)) * (x1 - x0);
  const Y = (v) => y0 - ((Math.min(hi, Math.max(lo, v)) - lo) / (hi - lo)) * (y0 - y1);
  const iOf = (y, m) => (y * 12 + m) - (fy * 12 + fm);
  let html = '';
  if (d.band.range) html += `<rect class="drift-band" x="${x0}" width="${x1 - x0}" y="${Y(d.band.range[1])}" height="${Y(d.band.range[0]) - Y(d.band.range[1])}"/>`;
  for (const v of [0.5, 1, 1.5]) html += `<line class="chart-grid${v === 1 ? ' one' : ''}" x1="${x0}" x2="${x1}" y1="${Y(v)}" y2="${Y(v)}"/><text class="chart-label" x="${x0 - 5}" y="${Y(v) + 3}" text-anchor="end">${v}</text>`;
  for (let y = fy + 1; y <= fy + Math.ceil(n / 12); y += 2) { const i = iOf(y, 1); if (i >= 0 && i < n) html += `<text class="chart-label" x="${X(i)}" y="156" text-anchor="middle">${y}</text>`; }
  const i22 = iOf(2022, 1);
  if (i22 > 0 && i22 < n) html += `<line class="drift-mark" x1="${X(i22)}" x2="${X(i22)}" y1="${y1}" y2="${y0}"/><text class="chart-label" x="${X(i22) - 4}" y="${y1 + 8}" text-anchor="end">record uses VIIRS from 2022</text>`;
  d.observed_modis.forEach((o, i) => { const p = d.predicted_modis[i]; if (p >= 10) html += `<circle class="drift-dot" cx="${X(i)}" cy="${Y(o / p)}" r="1.6"><title>${monthName(fy, fm, i)}: observed ${o}, predicted ${fmt(p)}</title></circle>`; });
  let path = ''; let pen = false;
  d.trailing12_ratio.forEach((r, i) => { if (r == null) { pen = false; return; } path += `${pen ? 'L' : 'M'}${X(i).toFixed(1)},${Y(r).toFixed(1)} `; pen = true; });
  html += `<path class="drift-line" d="${path.trim()}"/>`;
  html += '<text class="chart-label" transform="translate(9 76) rotate(-90)" text-anchor="middle">observed ÷ predicted</text>';
  svg.innerHTML = html;
  const after = d.trailing12_ratio.map((r, i) => [r, i]).filter(([r, i]) => r != null && i >= i22);
  const out = d.band.range ? after.filter(([r]) => r < d.band.range[0] || r > d.band.range[1]) : [];
  const lowest = after.length ? after.reduce((a, b) => (b[0] < a[0] ? b : a)) : null;
  $('#drift-eyebrow').textContent = `SATELLITE CHECK · ${state.meta.name.toUpperCase()}`;
  $('#drift-caption').textContent = `Line: MODIS detections actually observed ÷ MODIS detections predicted from Suomi NPP VIIRS, over the previous 12 months, for all of ${state.meta.name}; dots: single months with at least 10 predicted. `
    + `Band: the line's range in ${d.band.fitted[0].slice(0, 4)}–${d.band.fitted[1].slice(0, 4)}, the years the conversion was fitted. `
    + 'Terra and Aqua no longer hold their planned orbits, so in recent years they cross each place at a different time of day than in the rest of the record; that is why this record uses VIIRS from 2022. '
    + (after.length ? `Since 2022 the line is outside the band in ${out.length} of ${after.length} months${lowest ? ` (lowest ${lowest[0].toFixed(2)}, ${monthName(fy, fm, lowest[1])})` : ''}. ` : '')
    + `MODIS archive ends ${d.modis_archive_ends}; its last, incomplete month is left out.`;
}

// ---------- map ----------
function gibs(layer, level, ext) {
  return `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${layer}/default/GoogleMapsCompatible_Level${level}/{z}/{y}/{x}.${ext}`;
}
function cellFeatures() {
  const { ix, iy } = state.monthly.cells; const deg = state.monthly.cell_deg;
  const inside = new Set(state.areaCells);
  return { type: 'FeatureCollection', features: ix.map((x, c) => {
    const lon0 = x * deg; const lat0 = iy[c] * deg; const lon1 = lon0 + deg; const lat1 = lat0 + deg;
    const v = state.monthly.m[c][state.sel];
    return { type: 'Feature', id: c, properties: { v, inside: inside.has(c), color: v < 0.005 ? 'rgba(0,0,0,0)' : countColor(v, state.cellMax) },
      geometry: { type: 'Polygon', coordinates: [[[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]] } };
  }) };
}
function areaFeature() {
  const ring = state.area.kind === 'region' ? bboxRing(state.meta.bbox) : state.area.ring;
  return { type: 'FeatureCollection', features: [{ type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [ring] } }] };
}
function renderMapValues() {
  const map = state.map;
  if (map?.getSource('cells')) { map.getSource('cells').setData(cellFeatures()); map.getSource('area').setData(areaFeature()); }
  $('#map-caption').textContent = `${areaName()} · fire detections per 0.25° cell in ${label(state.sel)}, harmonized estimate (same colours as the calendar, per cell) · green outlines: cells counted in the area · NASA FIRMS`;
}

// app.js runs async, so the calendar does not wait for MapLibre; the map waits for its script instead.
function mapLibrary() {
  if (window.maplibregl) return Promise.resolve();
  return new Promise((resolve) => {
    const script = $('#maplibre-js');
    script.addEventListener('load', resolve); script.addEventListener('error', resolve);
    if (document.readyState === 'complete') resolve(); else window.addEventListener('load', resolve);
  });
}

async function initMap() {
  await mapLibrary();
  if (!window.maplibregl) { $('#map-caption').textContent = 'Map library failed to load (offline?). The calendar and the point-and-radius search still work.'; disableDraw('Map unavailable.'); return; }
  const map = new maplibregl.Map({
    container: 'map', attributionControl: { compact: true },
    style: {
      version: 8,
      // NASA GIBS: keyless, and NASA's own imagery. Blue Marble is darkened so the fire cells stand out.
      sources: {
        marble: { type: 'raster', tileSize: 256, maxzoom: 8, tiles: [gibs('BlueMarble_ShadedRelief_Bathymetry', 8, 'jpeg')],
          attribution: 'Basemap: <a href="https://earthdata.nasa.gov/gibs">NASA GIBS</a> · Fire data: NASA FIRMS' },
      },
      layers: [{ id: 'marble', type: 'raster', source: 'marble', paint: { 'raster-brightness-max': 0.6, 'raster-saturation': -0.4, 'raster-contrast': 0.1 } }],
    },
    bounds: state.meta.default_view.bounds, fitBoundsOptions: { padding: 16 },
  });
  map.addControl(new maplibregl.ScaleControl({ maxWidth: 80 }), 'bottom-right');
  map.once('style.load', () => { // not 'load', which waits for every basemap tile
    map.addSource('cells', { type: 'geojson', data: cellFeatures() });
    map.addSource('area', { type: 'geojson', data: areaFeature() });
    map.addLayer({ id: 'cells', type: 'fill', source: 'cells', paint: { 'fill-color': ['get', 'color'], 'fill-opacity': 0.75 } });
    map.addLayer({ id: 'cells-line', type: 'line', source: 'cells', paint: { 'line-color': ['case', ['get', 'inside'], '#93d9b1', '#3a5160'], 'line-width': ['case', ['get', 'inside'], 1.2, 0.4] } });
    map.addLayer({ id: 'area-line', type: 'line', source: 'area', paint: { 'line-color': '#ffa846', 'line-width': 2, 'line-dasharray': [2, 1.5] } });
    map.on('click', 'cells', (e) => {
      if (state.drawing || performance.now() - state.drawnAt < 400) return; // the click that finished a drawing
      const p = e.features[0].properties;
      new maplibregl.Popup().setLngLat(e.lngLat).setHTML(`<strong>${fmt(Number(p.v))}</strong> detections in ${label(state.sel)}<br>this 0.25° cell, harmonized estimate`).addTo(map);
    });
    initDraw(map);
  });
  state.map = map;
}

async function initDraw(map) {
  try {
    // Both URLs pin the same terra-draw build: the adapter's own bundle imports terra-draw@1.37.0.
    const td = await import('https://cdn.jsdelivr.net/npm/terra-draw@1.37.0/+esm');
    const { TerraDrawMapLibreGLAdapter } = await import('https://cdn.jsdelivr.net/npm/terra-draw-maplibre-gl-adapter@1.5.0/+esm');
    const draw = new td.TerraDraw({
      adapter: new TerraDrawMapLibreGLAdapter({ map }),
      modes: [new td.TerraDrawRectangleMode(), new td.TerraDrawPolygonMode()],
    });
    draw.start();
    draw.on('finish', (id) => {
      const f = draw.getSnapshotFeature(id);
      if (!f || f.geometry.type !== 'Polygon') return;
      const ring = f.geometry.coordinates[0];
      const kind = state.drawing === 'rectangle' ? 'rectangle' : 'polygon';
      state.drawnAt = performance.now();
      draw.clear(); stopDrawing();
      useRing(ring, kind).catch(failed);
    });
    state.draw = draw;
    document.querySelectorAll('.tool[aria-pressed]').forEach((b) => { b.disabled = false; });
    $('#map-panel').dataset.draw = 'ready';
  } catch (err) {
    disableDraw(`Drawing tools failed to load (${err.message}). Use the region list or a point and radius.`);
  }
}
function disableDraw(message) {
  document.querySelectorAll('.tool[aria-pressed]').forEach((b) => { b.disabled = true; });
  $('#draw-hint').textContent = message;
}
function startDrawing(mode) {
  if (!state.draw) return;
  if (state.drawing === mode) { stopDrawing(); return; }
  state.draw.clear(); state.draw.setMode(mode); state.drawing = mode;
  document.querySelectorAll('.tool[aria-pressed]').forEach((b) => b.setAttribute('aria-pressed', String(b.id === `draw-${mode}`)));
  $('#draw-hint').textContent = mode === 'rectangle' ? 'Click one corner on the map, then the opposite corner.' : 'Click each corner on the map, then click the first corner again to close.';
}
function stopDrawing() {
  state.drawing = null;
  if (state.draw) state.draw.setMode('static');
  document.querySelectorAll('.tool[aria-pressed]').forEach((b) => b.setAttribute('aria-pressed', 'false'));
  $('#draw-hint').textContent = 'Rectangle: click two corners. Polygon: click each corner, then click the first one again.';
}

// ---------- choosing an area ----------
function areaName() {
  const a = state.area;
  if (!a) return '';
  if (a.kind === 'region') return `${state.meta.name} (whole region)`;
  if (a.kind === 'circle') return `${a.radius} km around ${a.lat.toFixed(3)}, ${a.lon.toFixed(3)}`;
  return `drawn ${a.kind} in ${state.meta.name}`;
}

async function loadRegion(id) {
  if (state.meta?.id === id) return;
  const meta = state.index.regions.find((r) => r.id === id);
  const [monthly, drift] = await Promise.all([getJson(`data/${id}/monthly.json`), getJson(`data/${id}/drift.json`)]);
  state.meta = meta; state.monthly = monthly; state.drift = drift;
  state.cellMax = Math.max(1, ...monthly.m.map((row) => Math.max(...row)));
  $('#region').value = id;
  const ys = years();
  const opts = ys.map((y) => `<option value="${y}">${y}</option>`).join('');
  $('#csv-from').innerHTML = opts; $('#csv-to').innerHTML = opts;
  $('#csv-from').value = String(ys[0]); $('#csv-to').value = String(ys.at(-1));
  if (state.sel == null || state.sel >= monthly.months.n) state.sel = monthly.months.n - 1;
  renderDrift();
  if (state.map) state.map.fitBounds(meta.default_view.bounds, { padding: 16, duration: 600 });
}

function setArea(area) {
  state.area = area;
  state.areaCells = areaCells(area);
  state.series = buildSeries(state.areaCells);
  state.sel = defaultMonth(); state.defaultJ = state.sel;
  state.focus = null;
  $('#csv-status').textContent = '';
  $('#area-summary').innerHTML = `<strong>${areaName()}</strong><span>${state.areaCells.length} of ${state.monthly.cells.ix.length} cells of ${state.monthly.cell_deg}° with their centre inside the area. `
    + 'The calendar adds up whole cells (a cell-level approximation); the hotspot download uses the exact area.</span>';
  renderCalendar(); renderMonth(); renderMapValues(); renderSeason();
  if (state.map && area.kind !== 'region') state.map.fitBounds(ringBounds(area.ring), { padding: 40, duration: 600, maxZoom: 9 });
}

async function useRegion(id) {
  await loadRegion(id);
  setArea({ kind: 'region' });
}

async function useRing(ring, kind, extra = {}) {
  const region = regionForRing(ring);
  if (!region) { toast(`Outside the regions we cover (${state.index.regions.map((r) => r.name).join(', ')}).`); return false; }
  await loadRegion(region.id);
  const area = { kind, ring, ...extra };
  if (!areaCells(area).length) { toast('No 0.25° cell has its centre inside that area. Draw a larger area.'); return false; }
  setArea(area);
  return true;
}

// ---------- CSV ----------
function csvCell(v) { const s = v == null ? '' : String(v); return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s; }
function download(name, text) {
  const url = URL.createObjectURL(new Blob([text], { type: 'text/csv;charset=utf-8' }));
  const a = document.createElement('a'); a.href = url; a.download = name; document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}
function spanYears() {
  let a = Number($('#csv-from').value); let b = Number($('#csv-to').value);
  if (a > b) [a, b] = [b, a];
  return [a, b];
}
function fileStem() {
  const [y0, y1] = spanYears();
  return `cedrus_${state.meta.id}_${state.area.kind === 'region' ? 'region' : state.area.kind}_${y0}-${y1}`;
}

async function hotspotsCsv() {
  const [y0, y1] = spanYears(); const meta = state.meta; const area = state.area;
  $('#csv-status').textContent = `Reading detections for ${y0}–${y1}…`;
  const ys = []; for (let y = y0; y <= y1; y += 1) ys.push(y);
  const files = await Promise.all(ys.map(loadYear));
  const sensors = ['T', 'A', 'N', 'J1'];
  const head = ['latitude', 'longitude', 'brightness', 'bright_t31', 'bright_ti4', 'bright_ti5', 'scan', 'track', 'acq_date', 'acq_time',
    'satellite', 'instrument', 'confidence', 'version', 'frp', 'daynight', 'type', 'sensor', 'source_flag', 'w'];
  const lines = [head.join(',')]; let count = 0; let wsum = 0;
  for (const f of files) {
    if (!f) continue;
    const c = f.cols;
    for (let i = 0; i < f.n; i += 1) {
      if (!hotspotInArea(c, i, area)) continue;
      const date = new Date(Date.UTC(f.year, 0, c.doy[i]));
      const j = indexOf(f.year, date.getUTCMonth() + 1);
      const s = sensors[c.sensor[i]]; const modis = s === 'T' || s === 'A';
      lines.push([c.lat[i], c.lon[i], modis ? c.bright[i] : '', modis ? c.bright2[i] : '', modis ? '' : c.bright[i], modis ? '' : c.bright2[i],
        c.scan[i], c.track[i], date.toISOString().slice(0, 10), String(c.time[i]).padStart(4, '0'),
        meta.satellite_field[s], meta.instrument_field[s], c.conf[i], meta.versions[c.version[i]], c.frp[i], c.dn[i] ? 'N' : 'D', 0,
        s, j >= 0 ? FLAG[state.monthly.flags[j]] : '', c.w[i]].map(csvCell).join(','));
      count += 1; wsum += c.w[i];
    }
  }
  download(`${fileStem()}_hotspots.csv`, `${lines.join('\n')}\n`);
  $('#csv-status').textContent = `${count.toLocaleString('en-US')} detections in the exact area, ${y0}–${y1}. Column w is each one’s share of the harmonized estimate (total ${fmt(wsum)}).`;
}

function monthlyCsv() {
  const [y0, y1] = spanYears(); const meta = state.meta; const s = state.series;
  const methods = `# CEDRUS monthly fire detections in MODIS-equivalent units; harmonized_estimate is the expected value (sum of hotspot weights w + background). Region ${meta.name}. Area ${areaName()}: `
    + `${state.areaCells.length} cells of ${state.monthly.cell_deg} deg whose centre is inside the area (cell-level approximation). `
    + `Model ${meta.model} (replaced by the bake-off winner). p10/p90 approximate: cell 80% ranges combined in quadrature. `
    + 'source_flag: bridged = Terra / Terra share (2000-11..2002-06); observed = MODIS Terra+Aqua (2002-07..2021-12); estimated = from Suomi NPP VIIRS (2022-01 on). '
    + `naive = MODIS to 2011 then raw Suomi NPP counts. Data built ${meta.generated_at} from NASA FIRMS; files and SHA-256 in data/regions.json.`;
  const lines = [methods.replace(/,/g, ';'), 'month,harmonized_estimate,p10,p90,naive,background,source_flag'];
  for (let y = y0; y <= y1; y += 1) {
    for (let moy = 1; moy <= 12; moy += 1) {
      const j = indexOf(y, moy); if (j < 0) continue;
      lines.push([iso(j), s.m[j].toFixed(2), s.lo[j].toFixed(1), s.hi[j].toFixed(1), Math.round(s.naive[j]), s.bg[j].toFixed(2), FLAG[state.monthly.flags[j]]].join(','));
    }
  }
  download(`${fileStem()}_monthly.csv`, `${lines.join('\n')}\n`);
  $('#csv-status').textContent = `Monthly record ${y0}–${y1} for ${areaName()} downloaded.`;
}

// ---------- controls ----------
function bindControls() {
  $('#region').addEventListener('change', (e) => useRegion(e.target.value).catch(failed));
  $('#example-lebanon').addEventListener('click', () => useRegion('lebanon').catch(failed));
  $('#draw-rectangle').addEventListener('click', () => startDrawing('rectangle'));
  $('#draw-polygon').addEventListener('click', () => startDrawing('polygon'));
  $('#draw-clear').addEventListener('click', () => { stopDrawing(); setArea({ kind: 'region' }); if (state.map) state.map.fitBounds(state.meta.default_view.bounds, { padding: 16, duration: 600 }); });
  $('#area-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const lat = Number($('#lat').value); const lon = Number($('#lon').value); const radius = Number($('#radius').value);
    if (!$('#lat').value || !$('#lon').value || !(Math.abs(lat) <= 90) || !(Math.abs(lon) <= 180)) { toast('Enter a latitude (−90 to 90) and a longitude (−180 to 180).'); $('#lat').focus(); return; }
    if (!(radius >= 1 && radius <= 500)) { toast('Radius must be between 1 and 500 km.'); $('#radius').focus(); return; }
    useRing(circleRing(lat, lon, radius), 'circle', { lat, lon, radius }).catch(failed);
  });
  ['counts', 'anomaly'].forEach((m) => $(`#mode-${m}`).addEventListener('click', () => {
    state.mode = m;
    ['counts', 'anomaly'].forEach((k) => { $(`#mode-${k}`).classList.toggle('selected', k === m); $(`#mode-${k}`).setAttribute('aria-pressed', String(k === m)); });
    $('#ref-switch').hidden = m !== 'anomaly';
    renderCalendar();
  }));
  ['median', 'mean'].forEach((r) => $(`#ref-${r}`).addEventListener('click', () => {
    state.ref = r;
    ['median', 'mean'].forEach((k) => { $(`#ref-${k}`).classList.toggle('selected', k === r); $(`#ref-${k}`).setAttribute('aria-pressed', String(k === r)); });
    renderCalendar();
  }));
  ['naive', 'harmonized'].forEach((r) => $(`#rec-${r}`).addEventListener('click', () => {
    state.record = r;
    ['naive', 'harmonized'].forEach((k) => { $(`#rec-${k}`).classList.toggle('selected', k === r); $(`#rec-${k}`).setAttribute('aria-pressed', String(k === r)); });
    renderCalendar();
  }));
  $('#table-toggle').addEventListener('click', (e) => {
    state.table = !state.table;
    e.currentTarget.setAttribute('aria-pressed', String(state.table)); e.currentTarget.textContent = state.table ? 'Show as calendar' : 'Show as table';
    $('#cal-grid').hidden = state.table; $('#calendar-table').hidden = !state.table;
  });
  const grid = $('#cal-grid');
  grid.addEventListener('click', (e) => { const cell = e.target.closest('[role=gridcell]'); if (cell) selectMonth(Number(cell.dataset.j)); });
  grid.addEventListener('keydown', (e) => {
    const cell = e.target.closest('[role=gridcell]'); if (!cell) return;
    const moves = { ArrowLeft: [0, -1], ArrowRight: [0, 1], ArrowUp: [-1, 0], ArrowDown: [1, 0] };
    if (moves[e.key]) { e.preventDefault(); moveFocus(cell, ...moves[e.key]); return; }
    if (e.key === 'Home') { e.preventDefault(); moveFocus(cell, 0, 1 - Number(cell.dataset.moy)); return; }
    if (e.key === 'End') { e.preventDefault(); moveFocus(cell, 0, 12 - Number(cell.dataset.moy)); return; }
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); selectMonth(Number(cell.dataset.j)); }
  });
  $('#csv-hotspots').addEventListener('click', () => hotspotsCsv().catch((err) => { $('#csv-status').textContent = `Download failed: ${err.message}`; }));
  $('#csv-monthly').addEventListener('click', monthlyCsv);
  $('#zoom-in').addEventListener('click', () => state.map?.zoomIn());
  $('#zoom-out').addEventListener('click', () => state.map?.zoomOut());
}

const video = $('.hero-video'); const videoToggle = $('.video-toggle');
function syncVideo() { videoToggle.textContent = video.paused ? '▶' : 'Ⅱ'; const l = video.paused ? 'Play background video' : 'Pause background video'; videoToggle.setAttribute('aria-label', l); videoToggle.title = l; }
videoToggle.addEventListener('click', () => { if (video.paused) { video.play().catch(() => toast('Use your browser’s video playback permission to play the background.')); } else { video.pause(); } });
video.addEventListener('play', syncVideo); video.addEventListener('pause', syncVideo);
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { video.autoplay = false; video.pause(); } else { video.play().catch(syncVideo); }
syncVideo();

// ---------- dialogs ----------
function methodologyHtml() {
  const idx = state.index; if (!idx) return '<p>Data not loaded yet.</p>';
  const regions = idx.regions.map((r) => {
    const d = r.model_detail;
    return `<p><strong>${r.name}</strong> · ${r.months.first} to ${r.months.last} · ${r.cells} cells · model <code>${r.model}</code>, fitted ${d.train[0]} to ${d.train[1]} on ${d.train_detections.modis.toLocaleString('en-US')} MODIS and ${d.train_detections.snpp.toLocaleString('en-US')} Suomi NPP detections. Data built ${r.generated_at}.</p>
      <details><summary>${r.provenance.files.length} NASA FIRMS files and their SHA-256</summary><ul class="files">${r.provenance.files.map((f) => `<li><a href="${f.url}">${f.name}</a> · ${f.rows.toLocaleString('en-US')} rows · <code>${f.sha256}</code>${f.sha256_ok ? '' : ' <strong>(file changed since download)</strong>'}</li>`).join('')}</ul></details>`;
  }).join('');
  const r0 = idx.regions[0];
  return `<p><strong>Data.</strong> ${r0.provenance.source}. Filters: each region’s box; vegetation fires only (type 0); MODIS confidence ≥ 30; VIIRS confidence nominal or high. Unit: ${r0.provenance.unit}.</p>
    <p><strong>One record from three sources.</strong> November 2000 – June 2002: <em>bridged</em>, Terra alone divided by Terra’s share of MODIS detections in the same calendar month of 2003–2011 (each month’s share pulled toward the all-year share by 20 pseudo-detections, so a month with few fires cannot give a share of 0 or 1). July 2002 – December 2021: <em>observed</em>, MODIS Terra + Aqua. From January 2022: <em>estimated</em> from Suomi NPP VIIRS, because Terra and Aqua have left their planned orbits. The naive record joins MODIS to raw Suomi NPP counts in 2012, which creates a false jump.</p>
    <p><strong>Model: <code>${r0.model}</code>.</strong> Each Suomi NPP detection counts as the ratio of MODIS to Suomi NPP detections for its region, calendar month and day/night, fitted on 2012–2019 only and pulled toward the region’s all-year day or night ratio by 30 Suomi NPP pseudo-detections. Every value shown is the harmonized estimate (expected value): the sum of each detection’s weight. The 80% ranges of estimated and bridged months are an <em>interim placeholder</em>: the 10th–90th percentile of a negative binomial with the estimate as mean and size 5, not fitted to data. Both will be replaced by the winner of the pre-registered bake-off (docs/BAKEOFF_PLAN.md).</p>
    <p><strong>Areas.</strong> The calendar adds up whole 0.25° cells whose centre is inside your area (cell-level approximation). Area ranges add the cells’ ranges in quadrature, as if cells were independent (approximate). The hotspot download and the season dates use individual detections inside the exact area.</p>
    <p><strong>Trust check.</strong> R = half of the month’s 80% range ÷ the larger of (a) how far the month is from the baseline median and (b) half the interquartile range of the same calendar month over the baseline years (2003 to the year before). Reliable below 0.5, use with care 0.5–1, too uncertain above 1. Observed months have no range, so R = 0. In the calendar, cells fade toward the background from R = 0.5 and are hatched above 1.</p>
    <p><strong>Where the record ends.</strong> A sensor file’s final month is left out unless it has detections on at least 20 different days, because the archive may stop part-way through it.</p>
    <p><strong>Limits.</strong></p><ul>
      <li>Detections are not burned area: one large fire produces many detections.</li>
      <li>Values from 2022 are MODIS-equivalent estimates, not observations, and their ranges are a placeholder.</li>
      <li>Ranges of bridged months (Nov 2000 – Jun 2002) are the same placeholder as for estimated months.</li>
      <li>The conversion was fitted on 2012–2019 and assumes the MODIS-to-VIIRS ratio of a calendar month did not change after.</li>
      <li>Cell-level areas include or leave out whole 0.25° cells (about 25 km across).</li></ul>
    ${regions}
    <p><strong>Credits.</strong> Ideas we learned from: Kiln Watch, samuelakosa/firecal, SHIFT, Ember-Line, sagoresarker/nasa, Agun-Panjika. Basemap: NASA GIBS. Fire data: NASA FIRMS.</p>
    <p><strong>Use of AI.</strong> AI coding assistants helped write the pipeline and this website. The method, the test rules and every number shown come from the code and data in the repository and can be rebuilt from it.</p>
    <p class="files">An earlier test of a different conversion (a ratio per cell) is in docs/RESULTS.md.</p>`;
}
const dialogs = {
  methodology: { title: 'Data &amp; Methodology', body: methodologyHtml },
  about: { title: 'Roots in Nature.<br>Data for a Safer Tomorrow.', body: () => '<p>We are <strong>CEDRUS</strong>, joining the NASA Space Apps local event in Beirut.</p><p>Our challenge: <strong>Harmonization of MODIS and VIIRS Hot Spots.</strong> MODIS is being retired, and Suomi NPP stopped delivering data on 1 November 2026. We build one fire record that survives the handover, test it honestly, and turn it into a fire calendar for any area.</p>' },
};
document.querySelectorAll('[data-dialog]').forEach((button) => button.addEventListener('click', () => {
  const item = dialogs[button.dataset.dialog]; $('#dialog-title').innerHTML = item.title; $('#dialog-body').innerHTML = item.body(); $('#detail-dialog').showModal();
}));
$('.dialog-close').addEventListener('click', () => $('#detail-dialog').close()); $('.dialog-done').addEventListener('click', () => $('#detail-dialog').close());
$('#detail-dialog').addEventListener('click', (event) => { if (event.target === $('#detail-dialog')) { const r = event.target.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) event.target.close(); } });
document.querySelectorAll('nav a').forEach((link) => link.addEventListener('click', () => { document.querySelectorAll('nav a').forEach((item) => { item.classList.toggle('active', item === link); if (item === link) item.setAttribute('aria-current', 'page'); else item.removeAttribute('aria-current'); }); }));

function failed(err) {
  $('#data-badge').textContent = 'NO DATA';
  $('#map-caption').textContent = `Could not load the fire record (${err.message}). Serve web/ over http rather than opening the file directly.`;
  console.error(err);
}

async function start() {
  state.index = await getJson('data/regions.json');
  $('#region').innerHTML = state.index.regions.map((r) => `<option value="${r.id}">${r.name}</option>`).join('');
  bindControls();
  await useRegion(state.index.regions[0].id);
  $('#data-badge').textContent = `MODEL: ${state.meta.model.toUpperCase()}`;
  initMap();
}

// For tools/probe_site.py: the same entry points the controls use.
window.cedrus = { state, useRing, useRegion, selectMonth, indexOf, ready: start().catch((err) => { failed(err); throw err; }) };
