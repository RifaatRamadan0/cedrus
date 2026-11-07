// CEDRUS front end. Reads the static data contract that pipeline/export_v2.py writes into web/data/
// (layout in docs/DATA_CONTRACT.md). No build step: serve the web/ folder with any static server.
// MapLibre comes from a classic script tag; terra-draw is imported from the CDN once the map is up.
// fx.js draws the record as fire (embers, ash, smoke); every rule and number stays here.
import { createFx, EMBER, FLARE, COOL, FLARE_MIN } from './fx.js';

const $ = (selector) => document.querySelector(selector);
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONTH_NAMES = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const SHORT_FLAG = { B: 'bridged', O: 'observed', E: 'estimated', N: 'estimated · S-NPP only', J: 'estimated · NOAA-20 only', X: 'no data' };
const FLAG_TEXT = {
  B: 'Bridged: Terra alone, scaled up by Terra’s usual share of MODIS detections (2003–2011)',
  O: 'Observed by MODIS (Terra + Aqua)',
  E: 'Estimated from VIIRS: the average of the Suomi NPP and NOAA-20 estimates (MODIS drifted after 2021)',
  N: 'Estimated from Suomi NPP VIIRS alone: NOAA-20 has no complete data this month',
  J: 'Estimated from NOAA-20 VIIRS alone: Suomi NPP has no complete data this month',
  X: 'No VIIRS data this month',
};
const SENSORS = ['T', 'A', 'N', 'J1'];
const BASELINE_FIRST = 2003;
const MIN_BASE_YEARS = 5; // fewer baseline years than this: no normal, no anomaly, no trust check
const SEASON_MIN = 20;    // detections a year before a season can be dated
const FEW_FIRES = 5;      // baseline median below this: "few fires — too few to judge"
const QUIET = 0.5;        // an expected value below this counts as zero, in every era, for colour and for every comparison
const FEW_TILE = '#46525c'; // anomaly mode: months whose normal is under FEW_FIRES are drawn neutral, not compared
function asCount(v) { return v < QUIET ? 0 : v; }
const Z80 = 1.2815515655446004; // standard normal 90th percentile
// Counts are drawn on the ember scale (fx.js): monotone in lightness, so it reads in every colour-vision type and in grey.
// ColorBrewer PuOr, 11 classes: purple = fewer fires than normal, orange = more
const PUOR = ['#2d004b', '#542788', '#8073ac', '#b2abd2', '#d8daeb', '#f7f7f7', '#fee0b6', '#fdb863', '#e08214', '#b35806', '#7f3b08'];
// The two units (docs/DATA_CONTRACT.md). Burning days are the primary view: how many days each ~1 km square had a fire
// detected, in MODIS-equivalent terms (model D-a, round-3 confirmed). Hotspots are one click away: the satellites' fire
// detections in MODIS-equivalent counts (model A2, round-2 confirmed), the numbers the challenge asks for.
const UNITS = {
  bd: { id: 'burning_days', monthly: 'monthly_bd.json', drift: 'drift_bd.json', dir: 'burning', name: 'Burning days', one: 'burning day', many: 'burning days', what: 'burning days' },
  hot: { id: 'hotspots', monthly: 'monthly.json', drift: 'drift.json', dir: 'hotspots', name: 'Hotspots', one: 'detection', many: 'detections', what: 'hotspot counts' },
};
const UNIT_KEY = 'cedrus.unit'; // sessionStorage: the chosen unit is remembered for this tab's session
const FAMILY = ['MODIS', 'Suomi NPP', 'NOAA-20']; // burning/<year>.json `fam`

const state = {
  index: null, meta: null, monthly: null, drift: null, cellIndex: null, footprint: null,
  area: null, areaCells: [], series: null, sel: null, focus: null, vmax: 1, cellMax: 1,
  mode: 'counts', record: 'harmonized', ref: 'median', table: false, view: 'grid', defaultJ: null,
  unit: 'bd', loadedUnit: null, data: new Map(), loaded: new Map(), seriesCache: null, wantRegion: null,
  map: null, draw: null, drawing: null, drawnAt: -1e9, hot: new Map(),
  seasonToken: 0, regionToken: 0, areaToken: 0, selectionToken: 0, calendarShown: false,
};
let toastTimer;
let mapInspectionPopup = null;

function toast(message) {
  $('.toast').textContent = message; $('.toast').classList.add('visible');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => $('.toast').classList.remove('visible'), 4200);
}

function getJson(path) {
  return fetch(path).then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status} for ${path}`); return r.json(); });
}

// ---------- units ----------
function unit() { return UNITS[state.unit]; }
function many(v) { const s = fmt(v); return `${s} ${s === '1' ? unit().one : unit().many}`; }
// The model behind the current view: regions.json `burning_days` for burning days, the region's own fields for hotspots.
function unitMeta() { return state.unit === 'bd' ? state.meta.burning_days : state.meta; }

// ---------- numbers ----------
function fmt(v) {
  if (v == null || Number.isNaN(v)) return '–';
  if (v > 0 && v < 0.05) return '<0.1'; // not "0.0": something, but less than one decimal shows
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
function isLight(hex) { // relative luminance > 0.45: overlays on it are drawn dark
  const [r, g, b] = [1, 3, 5].map((k) => parseInt(hex.slice(k, k + 2), 16) / 255);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.45;
}
function countColor(v, vmax) { return ramp(EMBER, 0.08 + 0.92 * (Math.log10(1 + v) / Math.log10(1 + vmax))); }
// The map's cells sit in the darker half of the scale, so the embers on top of them carry the brightness.
function mapColor(v, vmax) { return ramp(EMBER, 0.06 + 0.5 * (Math.log10(1 + v) / Math.log10(1 + vmax))); }

// ---------- months and flags ----------
function monthOf(j) { // index -> {year, moy (1..12)}
  const [y0, m0] = state.monthly.months.first.split('-').map(Number);
  const k = y0 * 12 + (m0 - 1) + j;
  return { year: Math.floor(k / 12), moy: (k % 12) + 1 };
}
function indexOf(year, moy, mon = state.monthly) {
  const [y0, m0] = mon.months.first.split('-').map(Number);
  const j = (year * 12 + moy - 1) - (y0 * 12 + m0 - 1);
  return j >= 0 && j < mon.months.n ? j : -1;
}
function label(j) { const { year, moy } = monthOf(j); return `${MONTH_NAMES[moy - 1]} ${year}`; }
function iso(j) { const { year, moy } = monthOf(j); return `${year}-${String(moy).padStart(2, '0')}`; }
function years() {
  const first = Number(state.monthly.months.first.slice(0, 4)); const last = Number(state.monthly.months.last.slice(0, 4));
  return Array.from({ length: last - first + 1 }, (_, i) => first + i);
}
function flagAt(j) { return state.monthly.flags[j]; }
function flagName(f) { return state.monthly.flag_codes[f] ?? f; }
// The month's flag name plus, where the combination rule left a satellite out of a time of day, which one was used.
function slotNote(j, mon = state.monthly) { return mon.slot_notes?.[iso(j)] ?? ''; }
// Burning days only: where 10% or more of the month's contributing VIIRS burning days weigh 0 (docs/DATA_CONTRACT.md).
function zeroNote(j, mon = state.monthly) { return mon.zero_notes?.[iso(j)] ?? ''; }
function notes(j, mon = state.monthly) { return [slotNote(j, mon), zeroNote(j, mon)].filter(Boolean).join('; '); }
// mon: the calendar file whose weights a row carries (the hotspot CSV takes the hotspot file's notes in either view).
function flagLabel(j, mon = state.monthly) { const n = notes(j, mon); return `${mon.flag_codes[mon.flags[j]] ?? mon.flags[j]}${n ? ` (${n})` : ''}`; }
function flagText(f) { return f === 'B' && state.unit === 'bd' ? 'Bridged: Terra alone, scaled up by Terra’s usual share of MODIS burning days (2003–2011)' : FLAG_TEXT[f]; }
function isEstimated(f) { return f === 'E' || f === 'N' || f === 'J'; }

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
function regionsTouched(ring) {
  const [[x0, y0], [x1, y1]] = ringBounds(ring);
  return state.index.regions.filter((r) => x0 < r.bbox[2] && x1 > r.bbox[0] && y0 < r.bbox[3] && y1 > r.bbox[1]);
}
function containsBox(ring, [x0, y0, x1, y1]) { return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]].every(([x, y]) => inRing(x, y, ring)); }
async function regionForRing(ring) {
  const candidates = regionsTouched(ring);
  const scores = await Promise.all(candidates.map(async (meta) => {
    const [mon] = await unitData(meta.id, state.unit);
    const footprint = new Set(mon.cells.ix.map((x, i) => `${x}_${mon.cells.iy[i]}`));
    return { id: meta.id, name: meta.name, share: 1 - outsideShare(ring, meta, mon.cell_deg, footprint) };
  }));
  // Stable index order breaks exact ties; no counts or weights participate.
  scores.sort((a, b) => b.share - a.share);
  return { region: scores[0]?.share > 0 ? candidates.find((r) => r.id === scores[0].id) ?? null : null, scores };
}
function cellKey(lon, lat) { const d = state.monthly.cell_deg; return `${Math.floor(lon / d)}_${Math.floor(lat / d)}`; }

// Points sampled on a grid inside the ring, for area shares (outside coverage, part of a cell).
function samplePoints(ring, [[x0, y0], [x1, y1]], n = 64) {
  const pts = [];
  for (let a = 0; a < n; a += 1) {
    for (let b = 0; b < n; b += 1) {
      const lon = x0 + ((a + 0.5) / n) * (x1 - x0); const lat = y0 + ((b + 0.5) / n) * (y1 - y0);
      if (inRing(lon, lat, ring)) pts.push([lon, lat]);
    }
  }
  return pts;
}

// Exact share of a cell [x0, x0 + deg] x [y0, y0 + deg] inside the shape, on lon/lat as the inside test: the shape
// clipped to the cell (Sutherland–Hodgman; the cell is convex), its area by the shoelace formula, relative to the cell.
function cellShare(ring, x0, y0, deg) {
  let pts = ring.map(([x, y]) => [x - x0, y - y0]);
  const cutX = (a, b, x) => [x, a[1] + ((b[1] - a[1]) * (x - a[0])) / (b[0] - a[0])];
  const cutY = (a, b, y) => [a[0] + ((b[0] - a[0]) * (y - a[1])) / (b[1] - a[1]), y];
  const sides = [[(p) => p[0] >= 0, (a, b) => cutX(a, b, 0)], [(p) => p[0] <= deg, (a, b) => cutX(a, b, deg)],
    [(p) => p[1] >= 0, (a, b) => cutY(a, b, 0)], [(p) => p[1] <= deg, (a, b) => cutY(a, b, deg)]];
  for (const [inside, cut] of sides) {
    const next = [];
    for (let i = 0; i < pts.length; i += 1) {
      const a = pts[i]; const b = pts[(i + 1) % pts.length]; const ia = inside(a);
      if (ia) next.push(a);
      if (ia !== inside(b)) next.push(cut(a, b));
    }
    pts = next;
    if (!pts.length) return 0;
  }
  let s = 0;
  for (let i = 0; i < pts.length; i += 1) { const [xa, ya] = pts[i]; const [xb, yb] = pts[(i + 1) % pts.length]; s += xa * yb - xb * ya; }
  return Math.min(1, Math.abs(s) / 2 / (deg * deg));
}

// Share of the area outside this region's data: outside its box, or in a 0.25° cell where its FIRMS
// country file never had a detection (the country file stops at the border; e.g. Spain inside Portugal's box).
function outsideShare(ring, meta = state.meta, deg = state.monthly.cell_deg, footprint = state.footprint) {
  const pts = samplePoints(ring, ringBounds(ring));
  if (!pts.length) return 0;
  const [bx0, by0, bx1, by1] = meta.bbox;
  const out = pts.filter(([lon, lat]) => lon < bx0 || lon >= bx1 || lat < by0 || lat >= by1 || !footprint.has(`${Math.floor(lon / deg)}_${Math.floor(lat / deg)}`));
  return out.length / pts.length;
}

// ---------- the area and its monthly series ----------
function regionSeries(mon = state.monthly) {
  const { m, p10, p90, naive, months } = mon; const n = months.n;
  const bgs = mon.bg; // optional background term, already included in m
  const s = { m: new Float64Array(n), lo: new Float64Array(n), hi: new Float64Array(n), naive: new Float64Array(n), bg: new Float64Array(n), exact: false };
  const lw = new Float64Array(n); const hw = new Float64Array(n);
  for (let c = 0; c < m.length; c += 1) {
    const mc = m[c]; const lc = p10[c]; const hc = p90[c]; const nc = naive[c];
    for (let j = 0; j < n; j += 1) {
      s.m[j] += mc[j]; s.naive[j] += nc[j]; if (bgs) s.bg[j] += bgs[c][j];
      lw[j] += (mc[j] - lc[j]) ** 2; hw[j] += (hc[j] - mc[j]) ** 2;
    }
  }
  // Range: central values summed, each side's half-width combined in quadrature (approximate: cells treated as independent).
  for (let j = 0; j < n; j += 1) { s.lo[j] = Math.max(0, s.m[j] - Math.sqrt(lw[j])); s.hi[j] = s.m[j] + Math.sqrt(hw[j]); }
  return s;
}

// A drawn or circle area: the exact sum of the weights of the records inside the shape, month by month, plus each
// cell's background term (the model's expected count where VIIRS saw nothing) times the share of the cell inside the
// shape. A record is a detection (hotspots) or a burning day, which sits at the centre of its 0.01° square.
async function exactSeries(area, token) {
  const meta = state.meta; const mon = state.monthly; const n = mon.months.n; const bd = state.unit === 'bd';
  const yearsWanted = bd ? meta.burning_days.years : meta.hotspot_years; let done = 0; let failedYear = null;
  progress(0, yearsWanted.length);
  const files = await Promise.all(yearsWanted.map((y) => loadYear(y).catch((err) => { failedYear = failedYear ?? y; err.year = y; throw err; })
    .then((f) => { done += 1; if (token === state.areaToken && failedYear == null) progress(done, yearsWanted.length); return f; })));
  if (token !== state.areaToken) return null;
  const s = { m: new Float64Array(n), lo: new Float64Array(n), hi: new Float64Array(n), naive: new Float64Array(n), bg: new Float64Array(n), exact: true, count: 0 };
  const perCell = new Map(); // cell index -> Float64Array(n) of weights inside the shape
  const naiveSwitch = indexOf(2012, 1);
  const [[bx0, by0], [bx1, by1]] = ringBounds(area.ring);
  for (const f of files) {
    if (!f) continue;
    const c = f.cols; const moyOfDoy = [];
    for (let d = 1; d <= 366; d += 1) moyOfDoy[d] = new Date(Date.UTC(f.year, 0, d)).getUTCMonth() + 1;
    for (let i = 0; i < f.n; i += 1) {
      const lon = c.lon[i]; const lat = c.lat[i];
      if (lon < bx0 || lon > bx1 || lat < by0 || lat > by1 || !inRing(lon, lat, area.ring)) continue;
      const j = indexOf(f.year, moyOfDoy[c.doy[i]]); if (j < 0) continue;
      s.count += 1;
      if (bd) { if (c.fam[i] === 0 ? j < naiveSwitch : (c.fam[i] === 1 && j >= naiveSwitch)) s.naive[j] += 1; } else {
        const sensor = SENSORS[c.sensor[i]];
        if ((sensor === 'T' || sensor === 'A') ? j < naiveSwitch : (sensor === 'N' && j >= naiveSwitch)) s.naive[j] += 1;
      }
      if (!c.w[i]) continue;
      s.m[j] += c.w[i];
      const ci = state.cellIndex.get(c.cell ? c.cell[i] : cellKey(c.lon[i], c.lat[i]));
      if (ci == null) continue;
      if (!perCell.has(ci)) perCell.set(ci, new Float64Array(n));
      perCell.get(ci)[j] += c.w[i];
    }
  }
  // Background, by the share of each touched cell inside the shape; and which cells the shape touches.
  const touched = [];
  const deg = mon.cell_deg; const [[ax0, ay0], [ax1, ay1]] = ringBounds(area.ring);
  for (let ci = 0; ci < mon.cells.ix.length; ci += 1) {
    const x0 = mon.cells.ix[ci] * deg; const y0 = mon.cells.iy[ci] * deg;
    if (x0 + deg < ax0 || x0 > ax1 || y0 + deg < ay0 || y0 > ay1) continue;
    const frac = cellShare(area.ring, x0, y0, deg);
    if (frac <= 0 && !perCell.has(ci)) continue;
    touched.push(ci);
    if (mon.bg && frac > 0) for (let j = 0; j < n; j += 1) { const b = mon.bg[ci][j] * frac; s.bg[j] += b; s.m[j] += b; }
  }
  // Range: each cell's 80% half-widths scaled by (the area's weight in that cell / the cell's value), in quadrature.
  const lw = new Float64Array(n); const hw = new Float64Array(n);
  for (const [ci, wj] of perCell) {
    const mc = mon.m[ci]; const lc = mon.p10[ci]; const hc = mon.p90[ci];
    for (let j = 0; j < n; j += 1) {
      if (!(mc[j] > 0) || !wj[j]) continue;
      const share = Math.min(1, wj[j] / mc[j]);
      lw[j] += ((mc[j] - lc[j]) * share) ** 2; hw[j] += ((hc[j] - mc[j]) * share) ** 2;
    }
  }
  for (let j = 0; j < n; j += 1) { s.lo[j] = Math.max(0, s.m[j] - Math.sqrt(lw[j])); s.hi[j] = s.m[j] + Math.sqrt(hw[j]); }
  s.cells = touched;
  return s;
}

function progress(done, total) {
  const box = $('#cal-progress');
  box.hidden = done >= total;
  box.querySelector('span').textContent = `Reading ${unit().many} for this area: ${done} of ${total} years…`;
  box.querySelector('progress').max = total; box.querySelector('progress').value = done;
}

function value(j, record = state.record) { return record === 'naive' ? state.series.naive[j] : state.series.m[j]; }

// The baseline of a month is the same calendar month in 2003 .. the year before it. The calendar, its tooltips
// and the selected-month panel all use this one definition.
function baseline(year, moy, record = state.record) {
  const vals = [];
  for (let y = BASELINE_FIRST; y < year; y += 1) { const j = indexOf(y, moy); if (j >= 0 && flagAt(j) !== 'X') vals.push(asCount(value(j, record))); }
  const sorted = [...vals].sort((a, b) => a - b);
  return {
    years: vals.length, enough: vals.length >= MIN_BASE_YEARS, first: BASELINE_FIRST, last: year - 1, sorted,
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
  const scale = Math.max(Math.abs(asCount(state.series.m[j]) - base.median), base.iqr / 2);
  return scale > 0 ? half / scale : Infinity;
}
function trustVerdict(j, base) {
  if (!base.enough) return { key: 'none', text: 'Not enough history for a baseline', R: NaN };
  const R = trustRatio(j, base);
  if (base.median < FEW_FIRES) return { key: 'few', text: 'Few fires — too few to judge', R };
  if (R < 0.5) return { key: 'reliable', text: 'Reliable', R };
  if (R <= 1) return { key: 'care', text: 'Use with care', R };
  return { key: 'uncertain', text: 'Too uncertain', R };
}

// The month a new area opens on: the most recent one in the last three years of the record that normally has at least
// FEW_FIRES; else the most recent with at least one; else the latest month.
const DEFAULT_YEARS = 3;
function defaultMonth() {
  const last = state.monthly.months.n - 1;
  for (let j = last; j >= Math.max(0, last + 1 - 12 * DEFAULT_YEARS); j -= 1) {
    const { year, moy } = monthOf(j); const b = baseline(year, moy, 'harmonized');
    if (b.enough && b.median >= FEW_FIRES) { state.defaultWhy = 'normal'; return j; }
  }
  for (let j = last; j >= 0; j -= 1) if (state.series.m[j] >= 1) { state.defaultWhy = 'detection'; return j; }
  state.defaultWhy = 'latest';
  return last;
}
function typicalRange(b) { return [quantile(b.sorted, 0.25), quantile(b.sorted, 0.75)]; }

// ---------- calendar ----------
function cellView(j) {
  if (j < 0 || flagAt(j) === 'X') return { nd: true, text: j < 0 ? 'no data' : 'no data (no VIIRS satellite this month)' };
  const v = value(j); const { year, moy } = monthOf(j); const flag = flagAt(j);
  const b = baseline(year, moy);
  const few = b.enough && b.median < FEW_FIRES;
  let bg = null; let text; let zero = false; let anom = null; let flare = null;
  if (state.mode === 'counts') {
    // Quiet months look the same in both eras: an expected value under QUIET is drawn as "≈ zero";
    // the exact value stays in the tooltip.
    zero = v < QUIET;
    bg = zero ? null : countColor(v, state.vmax);
    // only a true zero says "no …": a small expected value (the background) is something, as the panel's "<0.1" says
    text = v <= 0 ? `no ${unit().many}` : zero ? `${v < 0.005 ? 'under 0.01' : v.toFixed(2)} ${unit().many} (≈ zero, under ${QUIET})` : many(v);
    // Flare-ups and cooled months, against the same baseline as everything else; never where a normal month has few fires.
    if (b.enough && b.median >= FLARE_MIN) {
      const r = asCount(v) / b.median;
      if (r >= FLARE) { flare = 'up'; text += `; flare-up: ${r >= 10 ? Math.round(r) : r.toFixed(1)}× the ${b.first}–${b.last} median (${fmt(b.median)})`; }
      else if (r <= COOL) { flare = 'down'; text += `; cooled: ${Math.round(r * 100)}% of the ${b.first}–${b.last} median (${fmt(b.median)})`; }
    }
  } else if (!b.enough) {
    text = `${many(v)}; not enough history for a baseline (${b.years} years)`;
  } else if (few) {
    // Few fires: no diverging colour; the count is set against the typical range in words.
    const [q1, q3] = typicalRange(b);
    bg = FEW_TILE;
    text = `few fires here, not compared: ${many(v)}${v < QUIET && v > 0 ? ' (counts as 0)' : ''}; a typical ${MONTH_NAMES[moy - 1]} has ${fmt(q1)}–${fmt(q3)}`;
  } else {
    const ref = b[state.ref]; const vc = asCount(v);
    if (ref >= 1) { // a percentage is never taken against a normal under 1
      const r = vc / ref; const t = Math.max(-2, Math.min(2, Math.log2(Math.max(r, 1e-9))));
      bg = ramp(PUOR, (t + 2) / 4); anom = t;
      text = `${signedPct(r - 1)} vs ${b.first}–${b.last} ${state.ref} (${fmt(v)} vs ${fmt(ref)})`;
    } else { bg = FEW_TILE; text = `${many(v)}; the ${state.ref} is under 1, not compared`; }
  }
  let trust = { key: 'none' };
  if (state.record === 'harmonized') {
    trust = trustVerdict(j, b);
    if (trust.key !== 'none') text += `; trust check: ${trust.text.toLowerCase()}${Number.isFinite(trust.R) && trust.R > 0 ? ` (R ${trust.R.toFixed(2)})` : ''}`;
  }
  const note = notes(j);
  return { bg, zero, few, anom, flare, text: `${text} · ${SHORT_FLAG[flag]}${note ? ` (${note})` : ''}`, flag, trust: trust.key };
}

function renderCalendar() {
  if (!state.series) return; // an area whose detections are loading or failed to load shows no numbers
  const ys = years();
  let vmax = 1; for (let j = 0; j < state.series.m.length; j += 1) vmax = Math.max(vmax, state.series.m[j], state.series.naive[j]);
  state.vmax = vmax; // one scale for both records, so the naive 2012 jump is not rescaled away
  const focus = state.focus ?? state.sel;
  let html = `<div class="cal-row cal-head" role="row"><span class="cal-corner" role="columnheader">Year</span>${MONTHS.map((m, i) => `<span role="columnheader" aria-label="${MONTH_NAMES[i]}">${m[0]}<i>${m.slice(1)}</i></span>`).join('')}</div>`;
  let rows = '';
  for (const y of ys) {
    html += `<div class="cal-row" role="row"><span class="cal-year" role="rowheader">${y}</span>`;
    rows += `<tr><th scope="row">${y}</th>`;
    for (let moy = 1; moy <= 12; moy += 1) {
      const j = indexOf(y, moy); const c = cellView(j);
      const name = `${MONTH_NAMES[moy - 1]} ${y}`;
      const cls = ['cal-cell', c.nd ? 'nd' : '', c.flag === 'B' ? 'b' : '', isEstimated(c.flag) ? 'e' : '', j >= 0 && j === state.sel ? 'sel' : '',
        !c.nd && !c.bg && !c.zero ? 'nb' : '', c.zero ? 'zero' : '', c.trust === 'care' ? 'care' : '', c.trust === 'uncertain' ? 'hz' : '', c.trust === 'few' || (c.few && state.mode === 'anomaly') ? 'few' : '',
        c.bg && isLight(c.bg) ? 'light' : '', c.flare === 'up' ? 'flare' : '', c.flare === 'down' ? 'cool' : ''].filter(Boolean).join(' ');
      const style = c.bg ? ` style="background-color:${c.bg}"` : '';
      const glyph = c.flare ? `<i aria-hidden="true">${c.flare === 'up' ? '▲' : '▽'}</i>` : '';
      // The tooltip is fx.js's ember card, from aria-label (a title attribute would show a second, native one).
      html += `<span role="gridcell" class="${cls}"${style}${c.anom != null ? ` data-anom="${c.anom.toFixed(2)}"` : ''} data-j="${j}" data-year="${y}" data-moy="${moy}" tabindex="${j >= 0 && j === focus ? 0 : -1}" aria-selected="${j >= 0 && j === state.sel}" aria-label="${name}: ${c.text}">${glyph}</span>`;
      rows += `<td>${c.nd ? '<span class="muted">no data</span>' : `${fmt(value(j))}${c.flag !== 'O' ? ` <small>${SHORT_FLAG[c.flag]}</small>` : ''}${c.trust === 'care' || c.trust === 'uncertain' || c.trust === 'few' ? ` <small>(${c.trust === 'care' ? 'use with care' : c.trust === 'few' ? 'few fires' : 'too uncertain'})</small>` : ''}`}</td>`;
    }
    html += '</div>'; rows += '</tr>';
  }
  const grid = $('#cal-grid');
  const hadFocus = grid.contains(document.activeElement);
  grid.innerHTML = html;
  grid.dataset.cells = String(grid.querySelectorAll('[role=gridcell]').length);
  if (hadFocus) grid.querySelector('[tabindex="0"]')?.focus();
  $('#calendar-table').innerHTML = `<table class="cal-table"><caption>${state.record === 'naive' ? 'Naive merge' : 'Harmonized estimate (expected value)'}: ${unit().many} per month, ${areaName()}</caption><thead><tr><th scope="col">Year</th>${MONTHS.map((m) => `<th scope="col">${m}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table>`;
  renderLegend();
  $('#calendar-note').textContent = (state.record === 'naive'
    ? `Naive merge: MODIS up to 2011, then raw Suomi NPP ${state.unit === 'bd' ? 'burning days' : 'counts'}. Watch 2012.`
    : `Harmonized estimate (expected value), in MODIS-equivalent ${unit().many}.`)
    + (state.mode === 'anomaly' ? ` Colour: each month vs the same month’s ${state.ref} in 2003 to the year before (at least ${MIN_BASE_YEARS} years).` : ` Colour: ${unit().many} per month (log scale).`)
    + (state.mode === 'anomaly' ? (state.ref === 'median' ? ' Median by default: one extreme year cannot move it.' : ' The mean is pulled up by the few worst years; the median is the sturdier normal.') : '')
    + (state.series.exact ? (state.unit === 'bd' ? ' Exact sums of the burning days inside your shape (a ~1 km square counts when its centre is inside).' : ' Exact sums of the detections inside your shape.') : ' Whole region: the sum of its 0.25° cells.');
  if (!state.calendarShown) { state.calendarShown = true; startVideo(); }
  fx.afterCalendar();
}

function renderLegend() {
  const marks = [];
  if (state.mode === 'counts') {
    const k = EMBER.length - 1;
    const stops = EMBER.map((_, i) => `${ramp(EMBER, 0.08 + 0.92 * (i / k))} ${(i / k) * 100}%`).join(',');
    const ticks = [1, 10, 100, 1000, 10000].filter((t) => t <= state.vmax).map((t) => `<span style="left:${(Math.log10(1 + t) / Math.log10(1 + state.vmax)) * 100}%">${t.toLocaleString('en-US')}</span>`).join('');
    marks.push(`<div class="ramp"><b>${unit().name} per month</b><i style="background:linear-gradient(90deg,${stops})"></i><div class="ticks">${ticks}</div></div>`);
  } else {
    const stops = PUOR.map((c, i) => `${c} ${(i / (PUOR.length - 1)) * 100}%`).join(',');
    const ticks = [[-0.75, '−75%'], [-0.5, '−50%'], [0, state.ref], [1, '+100%'], [3, '+300%']]
      .map(([p, l]) => `<span style="left:${((Math.log2(1 + p) + 2) / 4) * 100}%">${l}</span>`).join('');
    marks.push(`<div class="ramp"><b>Compared with the baseline ${state.ref}</b><i style="background:linear-gradient(90deg,${stops})"></i><div class="ticks">${ticks}</div></div>`);
  }
  marks.push(`<ul class="keys">${state.mode === 'counts' ? `<li><span class="sw zero"></span>≈ zero (under ${QUIET})</li><li><span class="sw flare">▲</span>flare-up: ${FLARE}× the median or more</li><li><span class="sw cool">▽</span>cooled: a third of the median or less (both only where a normal month has ${FLARE_MIN}+)</li>` :'<li><span class="sw nb"></span>not enough history</li><li><span class="sw fewtile"></span>few fires, not compared</li>'}<li><span class="sw nd"></span>no data</li><li><span class="sw b"></span>bridged</li><li><span class="sw e"></span>estimated</li>${state.record === 'harmonized' ? '<li><span class="sw care"></span>dashed = use with care</li><li><span class="sw hz"></span>hatched = too uncertain</li><li><span class="sw few"></span>corner = few fires, too few to judge</li>' : ''}</ul>`);
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
  if (j < 0 || flagAt(j) === 'X') { toast('No satellite data for that month.'); return; }
  fx.stop(); // a month picked by hand ends a playback
  state.sel = j; state.focus = j;
  renderCalendar(); renderMonth(); renderMapValues(); renderSeason();
}

// ---------- the selected month ----------
function renderMonth() {
  if (!state.series) return;
  const j = state.sel; const { year, moy } = monthOf(j); const flag = flagAt(j);
  const v = state.series.m[j]; const lo = state.series.lo[j]; const hi = state.series.hi[j];
  const base = baseline(year, moy, 'harmonized');
  const mn = MONTH_NAMES[moy - 1];
  const last = state.monthly.months.n - 1;
  $('#month-eyebrow').textContent = j === last ? 'LATEST MONTH IN THE RECORD'
    : j === state.defaultJ ? (state.defaultWhy === 'normal' ? 'MOST RECENT MONTH WITH A FIRE NORMAL' : 'MOST RECENT MONTH WITH A DETECTION') : 'SELECTED MONTH';
  $('#month-title').textContent = `${label(j)} · ${areaName()}`;
  const ranged = hi - lo > 1e-9;
  const rows = [];
  if (state.series.exact && state.series.count === 0) {
    rows.push(state.unit === 'bd' ? '<p class="no-detections"><strong>No burning days here.</strong> No ~1 km square with a fire detection has its centre inside this area in the whole record.</p>'
      : '<p class="no-detections"><strong>No detections here.</strong> No satellite fire detection fell inside this area in the whole record.</p>');
  }
  const rangeFrom = flag === 'B' ? 'placeholder range' : 'from the model';
  // Smoke is doubt: the trust check's verdict drawn on the number itself (hover or focus clears it; the words below stay).
  const smoke = base.enough ? fx.smokeClass(trustVerdict(j, base).key) : '';
  const plume = ranged ? `<i class="plume" aria-hidden="true" style="--lo:${(Math.min(1, lo / Math.max(hi, 1e-9)) * 100).toFixed(1)}%"></i>` : '';
  rows.push(`<p class="big-value"><strong id="month-value"${smoke ? ` class="${smoke}" tabindex="0"` : ''}>${fmt(v)}</strong> ${state.unit === 'bd' ? 'burning days (MODIS-equivalent)' : 'fire detections'}, harmonized estimate (expected value)${ranged ? ` <span>80% range ${fmt(lo)}–${fmt(hi)} (approximate, ${rangeFrom})${plume}</span>` : ''}</p>`);
  rows.push(`<p class="source-line"><span class="flag ${isEstimated(flag) ? 'estimated' : flagName(flag)}">${SHORT_FLAG[flag]}</span>${flagText(flag)}.${slotNote(j) ? ` <span class="slot-note">Exception this month (a satellite with no ratio for this month and time of day is left out): ${slotNote(j)}.</span>` : ''}${zeroNote(j) ? ` <span class="slot-note" id="zero-note">${zeroNote(j)}.</span>` : ''}</p>`);
  const two = bothUnits(j);
  if (two && two.bd > two.hot && two.bd >= QUIET) rows.push(`<p class="hint" id="two-models">Burning days and hotspots come from two separately tested models; here the burning-day estimate (${fmt(two.bd)}) is above the hotspot estimate (${fmt(two.hot)}), which can’t happen in real counts — read both as estimates within their ranges.</p>`);
  if (!base.enough) {
    rows.push(`<p class="hint" id="no-baseline"><strong>Not enough history for a baseline:</strong> ${base.years} ${mn}${base.years === 1 ? '' : 's'} before this one from 2003 on; at least ${MIN_BASE_YEARS} are needed for a normal, an anomaly or a trust check.</p>`);
  } else if (base.median < FEW_FIRES) {
    // Few fires: the count against the typical range, in words; no percentage and no chance-above-median.
    const vc = asCount(v); const [q1, q3] = typicalRange(base); const t = trustVerdict(j, base);
    const where = vc > q3 ? 'above' : vc < q1 ? 'below' : 'within';
    rows.push(`<p class="few-words" id="few-words">This month: <strong>${fmt(v)}</strong> ${v === 1 ? unit().one : unit().many}${v > 0 && v < QUIET ? ' (counts as none)' : ''}. A typical ${mn} here has <strong>${fmt(q1)}–${fmt(q3)}</strong> (the middle half of ${base.first}–${base.last}; median ${fmt(base.median)}), so this month is <strong>${where}</strong> the usual range.</p>`);
    rows.push(`<div class="trust ${t.key}" id="trust"><strong>Trust check: ${t.text}</strong><em>A normal ${mn} has fewer than ${FEW_FIRES} ${unit().many} in this area, so no percentage change or chance is given: a change here is mostly chance.</em></div>`);
  } else {
    const vc = asCount(v); // under QUIET counts as zero, in every era
    const below = base.sorted.filter((x) => x < vc).length; const ties = base.sorted.filter((x) => x === vc).length;
    const rank = ((below + ties / 2) / base.years) * 100;
    const sd = (hi - lo) / (2 * Z80);
    const pAbove = sd > 0 ? 1 - normalCdf((base.median - vc) / sd) : vc > base.median ? 1 : vc < base.median ? 0 : 0.5;
    const t = trustVerdict(j, base);
    const vs = (ref, word) => (ref >= 1 ? signedPct(vc / ref - 1) : `${word} under 1, not compared`);
    const vsMed = vs(base.median, 'median'); const vsMean = vs(base.mean, 'mean');
    rows.push(fx.ghostFlame(vc, base, mn));
    rows.push(`<dl class="stats">
      <div><dt>Normal ${mn} (median)</dt><dd>${fmt(base.median)} <span>this month ${vsMed}</span></dd></div>
      <div><dt>Multi-year mean</dt><dd>${fmt(base.mean)} <span>this month ${vsMean}</span></dd></div>
      <div><dt>Rank among baseline years</dt><dd>${Math.round(rank)}<span> percentile</span></dd></div>
      <div><dt>Chance it is above the median</dt><dd>${Math.round(pAbove * 100)}%</dd></div>
    </dl>`);
    rows.push(`<p class="hint">Baseline: ${mn} in ${base.first}–${base.last} (${base.years} years), harmonized estimates.${sd > 0 ? ' The chance uses a normal approximation of the 80% range.' : ''}</p>`);
    rows.push(`<div class="trust ${t.key}" id="trust"><strong>Trust check: ${t.text}</strong>
      <span>R = ${Number.isFinite(t.R) ? t.R.toFixed(2) : 'unbounded'}: half of this month’s 80% range (${fmt((hi - lo) / 2)}) compared with how far this month is from normal (${fmt(Math.abs(vc - base.median))} from the median), or the usual year-to-year spread of ${mn} (interquartile range ${fmt(base.iqr)} ÷ 2 = ${fmt(base.iqr / 2)}), whichever is larger. Below 0.5 reliable, 0.5–1 use with care, above 1 too uncertain.</span>
      </div>`);
  }
  if (j === state.defaultJ && j !== last) rows.push(`<p class="hint">Opened on this month because ${state.defaultWhy === 'normal' ? `it is the most recent month in the record’s last ${DEFAULT_YEARS} years that normally has at least ${FEW_FIRES} ${unit().many} in this area` : `no month in the record’s last ${DEFAULT_YEARS} years normally has ${FEW_FIRES} ${unit().many} here, and it is the most recent with at least one`}. The record runs to ${label(last)}.</p>`);
  if (Math.abs(state.series.naive[j] - v) > 0.005) rows.push(`<p class="hint">The naive merge would say ${fmt(state.series.naive[j])} for this month.</p>`);
  $('#month-body').innerHTML = rows.join('');
  renderCrossYearSeason(); fx.renderFingerprint(); fx.syncScrub();
}

// ---------- records: hotspots or burning days (loaded only when an area, a download or the season dates need them; cached) ----------
function loadYear(year, u = state.unit) {
  const meta = state.meta; const key = `${meta.id}/${u}/${year}`;
  if (!state.hot.has(key)) {
    const have = u === 'bd' ? meta.burning_days.years : meta.hotspot_years;
    const p = have.includes(year) ? getJson(`data/${meta.id}/${UNITS[u].dir}/${year}.json`).then((f) => (u === 'bd' ? placeBurningDays(f, meta) : f)) : Promise.resolve(null);
    state.hot.set(key, p.catch((err) => { state.hot.delete(key); throw err; }));
  }
  return state.hot.get(key);
}
// A burning day sits at the centre of its 0.01° square, and its 0.25° cell is found from the square by integer division
// (docs/DATA_CONTRACT.md); both are added once per file, so every reader can treat it like a hotspot.
function placeBurningDays(f, meta) {
  const fine = meta.burning_days.fine_cell_deg; const per = Math.round(0.25 / fine);
  const c = f.cols; c.lon = new Array(f.n); c.lat = new Array(f.n); c.cell = new Array(f.n);
  for (let i = 0; i < f.n; i += 1) {
    const fx = f.x0 + c.x[i]; const fy = f.y0 + c.y[i];
    c.lon[i] = (fx + 0.5) * fine; c.lat[i] = (fy + 0.5) * fine;
    c.cell[i] = `${Math.floor(fx / per)}_${Math.floor(fy / per)}`;
  }
  return f;
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
  $('#season-note').textContent = `Reading ${unit().many} for ${ys[0]}–${ys.at(-1)}…`;
  let files;
  try { files = await Promise.all(ys.map((y) => loadYear(y).catch((err) => { err.year = y; throw err; }))); } catch (err) {
    if (token === state.seasonToken) { ['start', 'peak', 'end'].forEach((k) => set(k, '–', '')); $('#season-note').textContent = `Couldn’t load ${unit().many} for ${err.year} — try again.`; }
    return;
  }
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
    $('#season-note').textContent = `Too few fires here to date a season: a typical year in ${ys[0]}–${ys.at(-1)} has ${many(medTotal)} in this area, and dating needs at least ${SEASON_MIN}.`;
    return;
  }
  ['start', 'peak', 'end'].forEach((k, q) => {
    const s = dates.map((d) => d[q]).sort((a, b) => a - b);
    const med = quantile(s, 0.5); const spread = (quantile(s, 0.75) - quantile(s, 0.25)) / 2;
    const day = new Date(Date.UTC(2001, 0, Math.round(med)));
    set(k, `${MONTHS[day.getUTCMonth()]} ${day.getUTCDate()}`, `± ${Math.round(spread)} days`);
  });
  $('#season-note').textContent = `Median day when 10%, 50% and 90% of the year’s ${unit().many} had happened, over the ${dates.length} years in ${ys[0]}–${ys.at(-1)} with at least ${SEASON_MIN} ${unit().many} in this area (individual ${unit().many} in the exact area, weighted as in the harmonized estimate). ± is half the interquartile range across years.`;
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
  $('#drift-caption').textContent = `Line: MODIS ${unit().many} actually observed ÷ MODIS ${unit().many} predicted from VIIRS (Suomi NPP and NOAA-20, averaged when both fly, as in the record), over the previous 12 months, for all of ${state.meta.name}; dots: single months with at least 10 predicted. `
    + `Band: the line's range in ${d.band.fitted[0].slice(0, 4)}–${d.band.fitted[1].slice(0, 4)}, the years the conversion was fitted. `
    + 'Terra and Aqua no longer hold their planned orbits, so in recent years they cross each place at a different time of day than in the rest of the record; that is why this record uses VIIRS from 2022. '
    + (after.length ? `Since 2022 the line is outside the band in ${out.length} of ${after.length} months${lowest ? ` (lowest ${lowest[0].toFixed(2)}, ${monthName(fy, fm, lowest[1])})` : ''}. ` : '')
    + `MODIS archive ends ${d.modis_archive_ends}; a final month without a detection in its last 3 days is left out.`;
}

// ---------- map ----------
function gibs(layer, level, ext) {
  return `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${layer}/default/GoogleMapsCompatible_Level${level}/{z}/{y}/{x}.${ext}`;
}
function cellFeatures() {
  if (!state.monthly || state.sel == null) return { type: 'FeatureCollection', features: [] };
  const { ix, iy } = state.monthly.cells; const deg = state.monthly.cell_deg;
  const inside = new Set(state.areaCells);
  return { type: 'FeatureCollection', features: ix.map((x, c) => {
    const lon0 = x * deg; const lat0 = iy[c] * deg; const lon1 = lon0 + deg; const lat1 = lat0 + deg;
    const v = state.monthly.m[c][state.sel];
    return { type: 'Feature', id: c, properties: { v, quiet: v < 0.005, inside: inside.has(c), region: state.area?.kind === 'region', color: v < 0.005 ? 'rgba(0,0,0,0)' : mapColor(v, state.cellMax) },
      geometry: { type: 'Polygon', coordinates: [[[lon0, lat0], [lon1, lat0], [lon1, lat1], [lon0, lat1], [lon0, lat0]]] } };
  }) };
}
// Display-only gaps inside the analysis box. These are not observed zero-fire cells.
function absentCellFeatures() {
  const features = [];
  if (!state.monthly || !state.meta || !state.footprint) return { type: 'FeatureCollection', features };
  const d = state.monthly.cell_deg; const [x0, y0, x1, y1] = state.meta.bbox;
  for (let x = Math.floor(x0 / d); x < Math.ceil(x1 / d); x += 1) {
    for (let y = Math.floor(y0 / d); y < Math.ceil(y1 / d); y += 1) {
      if (state.footprint.has(`${x}_${y}`)) continue;
      const box = [Math.max(x0, x * d), Math.max(y0, y * d), Math.min(x1, (x + 1) * d), Math.min(y1, (y + 1) * d)];
      features.push({ type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [bboxRing(box)] } });
    }
  }
  return { type: 'FeatureCollection', features };
}
function inspectMapPoint(lon, lat) {
  if (!state.monthly || !state.meta || state.sel == null) return;
  const c = state.cellIndex.get(cellKey(lon, lat));
  const [x0, y0, x1, y1] = state.meta.bbox;
  const inBox = lon >= x0 && lon < x1 && lat >= y0 && lat < y1;
  const month = label(state.sel);
  let detail;
  if (c != null) {
    const v = state.monthly.m[c][state.sel];
    detail = flagAt(state.sel) === 'X'
      ? `Included in ${state.meta.name}’s exported grid. No estimate available for ${month}.`
      : `Included in ${state.meta.name}’s exported grid. ${month}: ${fmt(v)} ${unit().many}, harmonized estimate for this 0.25° cell.${v < 0.005 ? ' Near-zero estimate; this cell is still included in the calculation.' : ''}`;
  } else {
    detail = inBox
      ? `Not included in ${state.meta.name}’s exported grid: no qualifying fire records for this cell in the imported record. No cell estimate is available for ${month}. The analysis box can include land outside the country.`
      : `Outside ${state.meta.name}’s exported grid and analysis extent. No cell estimate is available for ${month}.`;
  }
  detail += ' Observation completeness unknown. This does not establish that the location was fire-free.';
  $('#map-cell-detail').textContent = `${lat.toFixed(3)}, ${lon.toFixed(3)} — ${detail}`;
  mapInspectionPopup?.remove();
  mapInspectionPopup = new maplibregl.Popup().setLngLat([lon, lat]).setText(detail).addTo(state.map);
}
function areaFeature() {
  if (!state.area || !state.meta) return { type: 'FeatureCollection', features: [] };
  const ring = state.area.kind === 'region' ? bboxRing(state.meta.bbox) : state.area.ring;
  return { type: 'FeatureCollection', features: [{ type: 'Feature', properties: {}, geometry: { type: 'Polygon', coordinates: [ring] } }] };
}
function renderMapValues(opts = {}) {
  const map = state.map;
  if (map?.getSource('cells')) { map.getSource('cells').setData(cellFeatures()); map.getSource('area').setData(areaFeature()); }
  mapInspectionPopup?.remove(); mapInspectionPopup = null;
  $('#map-cell-detail').textContent = 'Click the map to inspect a location and its selected-month estimate.';
  $('#map-extent-note').textContent = state.area?.kind === 'region'
    ? 'Orange dashed outline: analysis extent — not the country boundary.'
    : 'Orange dashed outline: your drawn analysis area — not a country boundary.';
  $('#map-caption').textContent = `${areaName()} · ${state.unit === 'bd' ? 'burning days' : 'fire detections'} per 0.25° cell in ${state.sel == null ? 'no selected month' : label(state.sel)}, harmonized estimate (whole cells, for orientation; ember size = the cell’s value) · gold outlines: cells the area touches · NASA FIRMS`;
  if (state.sel != null) fx.mapMonth(opts);
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
function mapStatus(text) { const el = $('#map-loading'); el.hidden = !text; el.textContent = text || ''; }

async function initMap() {
  await mapLibrary();
  if (!window.maplibregl) {
    mapStatus('Map unavailable (the map library did not load). The calendar and the point-and-radius search still work.');
    $('#map-caption').textContent = 'Map library failed to load (offline?). The calendar and the point-and-radius search still work.';
    disableDraw('Map unavailable: use the region list or a point and radius.');
    return;
  }
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
    bounds: (state.meta ?? state.index.regions[0]).default_view.bounds, fitBoundsOptions: { padding: 16 },
  });
  map.addControl(new maplibregl.ScaleControl({ maxWidth: 80 }), 'bottom-right');
  map.once('style.load', () => { // not 'load', which waits for every basemap tile
    map.addSource('cells', { type: 'geojson', data: cellFeatures() });
    map.addSource('area', { type: 'geojson', data: areaFeature() });
    map.addSource('absent-cells', { type: 'geojson', data: absentCellFeatures() });
    map.addLayer({ id: 'absent-cells', type: 'fill', source: 'absent-cells', paint: { 'fill-color': '#71899b', 'fill-opacity': 0.22 } });
    map.addLayer({ id: 'absent-cells-line', type: 'line', source: 'absent-cells', paint: { 'line-color': '#9bb0c0', 'line-width': 0.7, 'line-opacity': 0.55, 'line-dasharray': [2, 3] } });
    map.addLayer({ id: 'cells', type: 'fill', source: 'cells', paint: { 'fill-color': ['get', 'color'], 'fill-opacity': 0.6 } });
    map.addLayer({ id: 'cells-line', type: 'line', source: 'cells', paint: { 'line-color': ['case', ['get', 'inside'], '#ffc35a', '#3a4a52'], 'line-width': ['case', ['get', 'inside'], 1.1, 0.4], 'line-opacity': ['case', ['get', 'inside'], ['case', ['get', 'region'], 0.3, 0.75], 1] } });
    map.addLayer({ id: 'quiet-cells-line', type: 'line', source: 'cells', filter: ['==', ['get', 'quiet'], true], paint: { 'line-color': '#c0cdd4', 'line-width': 0.8, 'line-opacity': 0.5 } });
    map.addLayer({ id: 'area-line', type: 'line', source: 'area', paint: { 'line-color': '#ffa846', 'line-width': 2, 'line-dasharray': [2, 1.5] } });
    fx.mapReady(map);
    map.on('click', (e) => {
      if (state.drawing || performance.now() - state.drawnAt < 400) return; // the click that finished a drawing
      inspectMapPoint(e.lngLat.lng, e.lngLat.lat);
    });
    mapStatus('Loading drawing tools…');
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
      // Drawn in fire: the outline glows like a fuse; the torch and its cooling trail are fx.js's (drawing()).
      modes: [new td.TerraDrawRectangleMode({ styles: { fillColor: '#ff7a2a', fillOpacity: 0.08, outlineColor: '#ffb04a', outlineWidth: 2 } }),
        new td.TerraDrawPolygonMode({ styles: { fillColor: '#ff7a2a', fillOpacity: 0.08, outlineColor: '#ffb04a', outlineWidth: 2,
          closingPointColor: '#fff3cf', closingPointWidth: 5, closingPointOutlineColor: '#ff8a2a', closingPointOutlineWidth: 2 } })],
    });
    draw.start();
    draw.on('finish', (id) => {
      const f = draw.getSnapshotFeature(id);
      if (!f || f.geometry.type !== 'Polygon') return;
      const ring = f.geometry.coordinates[0];
      const kind = state.drawing === 'rectangle' ? 'rectangle' : 'polygon';
      state.drawnAt = performance.now();
      stopDrawing();
      useRing(ring, kind).catch(failed);
    });
    state.draw = draw;
    document.querySelectorAll('.tool[aria-pressed]').forEach((b) => { b.disabled = false; });
    $('#draw-hint').textContent = DRAW_HINT;
    mapStatus('');
    $('#map-panel').dataset.draw = 'ready';
  } catch (err) {
    mapStatus('');
    disableDraw(`Drawing tools failed to load (${err.message}). Use the region list or a point and radius.`);
  }
}
const DRAW_HINT = 'Rectangle: click two corners. Polygon: click each corner, then click the first one again.';
function disableDraw(message) {
  document.querySelectorAll('.tool[aria-pressed]').forEach((b) => { b.disabled = true; });
  $('#draw-hint').textContent = message;
}
function startDrawing(mode) {
  if (!state.draw) return;
  if (state.drawing === mode) { stopDrawing(); return; }
  state.draw.clear(); state.draw.setMode(mode); state.drawing = mode; fx.drawing(mode);
  document.querySelectorAll('.tool[aria-pressed]').forEach((b) => b.setAttribute('aria-pressed', String(b.id === `draw-${mode}`)));
  $('#draw-hint').textContent = mode === 'rectangle' ? 'Click one corner on the map, then the opposite corner.' : 'Click each corner on the map, then click the first corner again to close.';
}
// Ends any drawing: leaves the mode, removes a half-drawn shape, releases the buttons.
function stopDrawing() {
  state.drawing = null; fx.drawing(null);
  if (state.draw) { state.draw.setMode('static'); state.draw.clear(); }
  document.querySelectorAll('.tool[aria-pressed]').forEach((b) => b.setAttribute('aria-pressed', 'false'));
  if (state.draw) $('#draw-hint').textContent = DRAW_HINT;
}

// ---------- choosing an area ----------
function areaName() {
  const a = state.area;
  if (!a) return '';
  const where = a.kind === 'region' ? `${state.meta.name} (whole region)`
    : a.kind === 'circle' ? `${a.radius} km around ${a.lat.toFixed(3)}, ${a.lon.toFixed(3)}` : `drawn ${a.kind}`;
  if (a.kind === 'region') return where;
  if (a.containsRegion) return `${where}, containing all of ${state.meta.name}`;
  return a.outside >= 0.5 ? `${where}, mostly outside ${state.meta.name}’s data`
    : a.outside >= 0.01 ? `${where}, ${Math.round(a.outside * 100)}% outside ${state.meta.name}’s data` : `${where} in ${state.meta.name}`;
}

// A region's calendar and drift files in one unit, cached.
function unitData(id, u) {
  const key = `${id}/${u}`;
  if (!state.data.has(key)) {
    const p = Promise.all([getJson(`data/${id}/${UNITS[u].monthly}`), getJson(`data/${id}/${UNITS[u].drift}`)])
      .then((d) => { state.loaded.set(key, d); return d; });
    state.data.set(key, p.catch((err) => { state.data.delete(key); throw err; }));
  }
  return state.data.get(key);
}

// Loads a region's files in a unit (the current one by default). The unit is committed only once its files are here,
// so a failed load leaves the previous unit, its labels and its numbers in place. Only the latest request may render:
// an older one that finishes later returns false.
async function loadRegion(id, u = state.unit) {
  const token = ++state.regionToken;
  state.wantRegion = id;
  if (state.meta?.id === id && state.loadedUnit === u) return true;
  const newRegion = state.meta?.id !== id;
  if (newRegion) stopDrawing();
  const meta = state.index.regions.find((r) => r.id === id);
  const [monthly, drift] = await unitData(id, u);
  if (token !== state.regionToken) return false;
  fx.stop();
  const selectedKey = state.monthly && state.sel != null ? iso(state.sel) : null;
  const focusKey = state.monthly && state.focus != null ? iso(state.focus) : null;
  const align = (key) => { const j = key ? indexOf(...key.split('-').map(Number), monthly) : -1; return j < 0 ? null : j; };
  // Rebase before any map, ramp or series reader sees the new calendar.
  state.sel = align(selectedKey); state.focus = align(focusKey);
  state.series = null;
  if (newRegion) state.seriesCache = null;
  state.areaToken += 1; // an area still loading for the previous region or unit must not render
  state.meta = meta; state.monthly = monthly; state.drift = drift; state.loadedUnit = u; state.unit = u;
  renderUnitSwitch(); $('#unit-status').hidden = true;
  state.cellIndex = new Map(monthly.cells.ix.map((x, c) => [`${x}_${monthly.cells.iy[c]}`, c]));
  state.footprint = new Set(state.cellIndex.keys());
  state.map?.getSource('absent-cells')?.setData(absentCellFeatures());
  state.cellMax = Math.max(1, ...monthly.m.map((row) => Math.max(...row)));
  if (newRegion) {
    $('#region').value = id;
    const ys = years();
    const opts = ys.map((y) => `<option value="${y}">${y}</option>`).join('');
    $('#csv-from').innerHTML = opts; $('#csv-to').innerHTML = opts;
    $('#csv-from').value = String(ys[0]); $('#csv-to').value = String(ys.at(-1));
    $('#record-end-note').textContent = `The record runs to ${label(monthly.months.n - 1)}. 2026 (to the present) needs NASA’s FIRMS near-real-time API key — pending.`;
    if (state.map) state.map.fitBounds(meta.default_view.bounds, { padding: 16, duration: 600 });
  }
  renderDrift();
  return true;
}

// The unit switch: the same region and area, the other unit's files; the selected month stays. The hotspot CSV is
// offered in both views (the challenge asks for hotspots); the burning-day CSV in the burning-day view.
function renderUnitSwitch() {
  ['bd', 'hot'].forEach((u) => $(`#unit-${u}`).setAttribute('aria-pressed', String(u === state.unit)));
  $('.unit-row').dataset.sel = state.unit; // the heat slides to the chosen unit
  $('#csv-burning').hidden = state.unit !== 'bd'; $('#csv-hotspots').hidden = false;
}
// A unit's calendar files did not load: say so with a retry; the unit in force (if any) keeps its labels and numbers.
function unitFailed(u, retry) {
  const what = `Couldn’t load ${UNITS[u].what} — try again.`;
  $('#unit-status-text').textContent = what; $('#unit-status').hidden = false;
  $('#unit-retry').onclick = () => { $('#unit-status').hidden = true; retry().catch(failed); };
  renderUnitSwitch();
  if (!state.series) {
    clearNumbers(what); $('#map-caption').textContent = what;
    const r = state.index.regions.find((x) => x.id === (state.meta?.id ?? state.wantRegion));
    if (r) {
      $('#area-summary').innerHTML = `<strong>${r.name}</strong><span class="load-error">${what}</span>`;
      if (!state.meta) { // the year lists come with a region's calendar; until then, from regions.json
        const y0 = Number(r.months.first.slice(0, 4)); const y1 = Number(r.months.last.slice(0, 4));
        const opts = Array.from({ length: y1 - y0 + 1 }, (_, i) => `<option value="${y0 + i}">${y0 + i}</option>`).join('');
        $('#csv-from').innerHTML = opts; $('#csv-to').innerHTML = opts; $('#csv-to').value = String(y1);
      }
    }
  }
}
async function setUnit(u) {
  state.selectionToken += 1;
  if (!UNITS[u]) return false;
  const id = state.meta?.id ?? state.wantRegion;
  if (!id) return false;
  $('#unit-status').hidden = true;
  const area = state.area ?? { kind: 'region' };
  const before = state.meta?.id === id ? state.loadedUnit : null;
  let ok;
  try { ok = await loadRegion(id, u); } catch { unitFailed(u, () => setUnit(u)); return false; }
  if (!ok) return false;
  if (before === u) return true; // already on screen (a click on the current unit only cancels a pending switch)
  try { sessionStorage.setItem(UNIT_KEY, u); } catch { /* storage blocked: the choice lasts for this page only */ }
  return setArea(area, { keepMonth: true });
}

// The same month in both units, where both are at hand: the whole region from either unit's calendar file once
// loaded, a drawn area once its series has been worked out in both units. Otherwise null.
function bothUnits(j) {
  const other = state.unit === 'bd' ? 'hot' : 'bd';
  let o = null;
  if (state.area?.kind === 'region') { const d = state.loaded.get(`${state.meta.id}/${other}`); if (d) o = regionSeries(d[0]); } else if (state.seriesCache?.area === state.area) o = state.seriesCache.by[other] ?? null;
  if (!o || !state.series) return null;
  const otherMon = state.loaded.get(`${state.meta.id}/${other}`)?.[0];
  if (!otherMon) return null;
  const otherJ = indexOf(...iso(j).split('-').map(Number), otherMon);
  if (otherJ < 0) return null;
  const here = state.series.m[j]; const there = o.m[otherJ];
  return state.unit === 'bd' ? { bd: here, hot: there } : { bd: there, hot: here };
}

// No numbers on screen while an area's detections are loading, or after they failed to load: the label, the
// calendar, the panel and the downloads must never show one area's numbers under another area's name.
function setDownloads(enabled) { ['#csv-burning', '#csv-hotspots', '#csv-monthly'].forEach((b) => { $(b).disabled = !enabled; }); }
function clearNumbers(message) {
  state.series = null;
  setDownloads(false);
  $('#cal-grid').innerHTML = ''; $('#cal-grid').dataset.cells = '0'; $('#calendar-table').innerHTML = '';
  $('#month-eyebrow').textContent = 'SELECTED AREA';
  $('#month-title').textContent = areaName();
  $('#month-body').innerHTML = `<p class="hint">${message}</p>`;
  $('#calendar-note').textContent = message;
  $('#calendar-legend').innerHTML = '';
  ['start', 'peak', 'end'].forEach((k) => { $(`#cal-${k}`).textContent = '–'; $(`#cal-${k}-spread`).textContent = ''; });
  $('#season-eyebrow').textContent = areaName() ? `FIRE SEASON · ${areaName().toUpperCase()}` : 'FIRE SEASON';
  $('#season-note').textContent = message;
  state.seasonToken += 1; // a season still loading for the previous area must not write here
}

async function setArea(area, opts = {}) {
  const token = ++state.areaToken;
  renderRegionNotes();
  $('#csv-status').textContent = '';
  if (!opts.keepMonth) fx.areaChanged(area); // fire runs once round the new area's edge
  if (area.kind === 'region') {
    state.area = area; state.series = regionSeries(); state.areaCells = state.monthly.cells.ix.map((_, c) => c);
    $('#area-summary').innerHTML = `<strong>${areaName()}</strong><span>${state.monthly.cells.ix.length} cells of ${state.monthly.cell_deg}°: every ${unit().one} in ${state.meta.name}’s FIRMS country file inside its box.</span>`;
  } else {
    area.outside = outsideShare(area.ring);
    area.containsRegion = containsBox(area.ring, state.meta.bbox);
    state.area = area; state.areaCells = [];
    $('#area-summary').innerHTML = `<strong>${areaName()}</strong><span>Reading the ${unit().many} inside this shape…</span>`;
    clearNumbers(`Reading the ${unit().many} inside this shape…`);
    renderMapValues();
    let s;
    try {
      s = await exactSeries(area, token);
    } catch (err) {
      if (token !== state.areaToken) return false;
      progress(1, 1); // hide the bar
      const what = err.year ? `Couldn’t load ${unit().many} for ${err.year} — try again.` : `Couldn’t load ${unit().many} — try again (${err.message}).`;
      clearNumbers(what);
      $('#area-summary').innerHTML = `<strong>${areaName()}</strong><span class="load-error" id="load-error">${what}</span> <button type="button" class="link-button" id="retry-area">Try again</button>`;
      $('#retry-area').addEventListener('click', () => setArea(area, opts).catch(failed));
      return false;
    }
    if (!s) return false; // a newer area or region took over
    state.series = s; state.areaCells = s.cells;
    const name = state.meta.name;
    const out = Math.round(area.outside * 100);
    let warn = area.containsRegion ? `Most of this area is outside our data; showing all of ${name}’s detections inside it.`
      : area.outside >= 0.5 ? `Most of this area (${out}%) is outside ${name}’s data (FIRMS country file) — fires there are not counted.`
        : area.outside >= 0.01 ? `${out}% of this area is outside ${name}’s data (FIRMS country file) — fires there are not counted.` : '';
    warn = warn ? `<em class="outside-warning" id="outside-warning">${warn}</em>` : '';
    const alternatives = area.footprintScores?.filter((r) => r.id !== state.meta.id && r.share > 0.10) ?? [];
    if (alternatives.length) warn += `<em class="outside-warning" id="spans-warning">This drawing overlaps the historical grid footprints of ${[name, ...alternatives.map((r) => r.name)].join(' and ')}. Showing ${name} only. Use the region picker to switch the same drawing. Footprints are approximate, not country boundaries.</em>`;
    else if (area.containsRegion && area.footprintScores?.length > 1) warn += `<em class="outside-warning" id="spans-warning">This area spans ${area.footprintScores.map((r) => r.name).join(' and ')} — showing ${name} only; draw within one region. These are bounding-box candidates, not country boundaries.</em>`;
    const span = `${state.monthly.months.first} to ${state.monthly.months.last}`;
    const what = state.unit === 'bd'
      ? (s.count ? `${s.count.toLocaleString('en-US')} burning days inside the shape (all satellites, ${span}; a ~1 km square counts when its centre is inside). The calendar adds up the weight of each one: an exact sum, not whole cells.`
        : `<strong class="no-det">No burning days here:</strong> no ~1 km square with a fire detection has its centre inside this shape between ${state.monthly.months.first} and ${state.monthly.months.last}.`)
      : (s.count ? `${s.count.toLocaleString('en-US')} detections inside the shape (all satellites, ${span}). The calendar adds up the weight of each one: an exact sum, not whole cells.`
        : `<strong class="no-det">No detections here:</strong> no satellite fire detection fell inside this shape between ${state.monthly.months.first} and ${state.monthly.months.last}.`);
    $('#area-summary').innerHTML = `<strong>${areaName()}</strong><span>${what}</span>${warn}`;
  }
  setDownloads(true);
  renderRegionNotes();
  if (state.seriesCache?.area !== area) state.seriesCache = { area, by: {} };
  state.seriesCache.by[state.unit] = state.series;
  if (area.kind === 'region') { // the other unit's calendar, for the two-models note; quietly, after this one rendered
    const other = state.unit === 'bd' ? 'hot' : 'bd'; const id = state.meta.id;
    unitData(id, other).then(() => { if (state.area === area && state.series && state.meta.id === id) renderMonth(); }).catch(() => {});
  }
  // A unit switch keeps the month on screen; a new area opens on its default month.
  const keep = opts.keepMonth && state.sel != null && state.sel >= 0 && state.sel < state.monthly.months.n && flagAt(state.sel) !== 'X';
  const sel = state.sel;
  state.defaultJ = defaultMonth(); state.sel = keep ? sel : state.defaultJ;
  state.focus = null;
  fx.stop();
  renderCalendar(); renderMonth(); renderMapValues(); renderSeason(); fx.seriesChanged();
  if (state.map && area.kind !== 'region' && !opts.keepMonth) state.map.fitBounds(ringBounds(area.ring), { padding: 40, duration: 600, maxZoom: 9 });
  return true;
}

function renderRegionNotes() {
  const target = $('#region-notes');
  target.replaceChildren();
  for (const note of [...(state.index.shared_notes ?? []), ...(state.meta.notes ?? [])]) {
    const p = document.createElement('p'); p.textContent = note; target.append(p);
  }
}

function seasonTotal(startYear) {
  const indices = Array.from({ length: 7 }, (_, i) => indexOf(startYear + (i >= 5 ? 1 : 0), i < 5 ? i + 8 : i - 4));
  if (!state.series || indices.some((j) => j < 0 || flagAt(j) === 'X')) return null;
  return indices.reduce((sum, j) => sum + state.series.m[j], 0);
}

function renderCrossYearSeason() {
  const el = $('#cross-year-season');
  el.hidden = state.meta.id !== 'la_rioja' || !state.series || state.sel == null;
  if (el.hidden) return;
  const { year, moy } = monthOf(state.sel); const start = year - (moy < 8 ? 1 : 0);
  const total = seasonTotal(start);
  el.dataset.startYear = start; el.dataset.total = total == null ? '' : String(total);
  el.textContent = `August ${start}–February ${start + 1}: ${total == null ? 'incomplete estimate' : many(total)}. Monthly completeness is unknown.`;
}

async function useRegion(id, { keepDrawing = false, keepMonth = false } = {}) {
  state.selectionToken += 1;
  const drawing = keepDrawing && state.area?.kind !== 'region' ? state.area : null;
  const sameArea = !!drawing || state.area?.kind === 'region';
  stopDrawing();
  if (!(await loadRegion(id))) return false;
  return setArea(drawing ?? { kind: 'region' }, { keepMonth: keepMonth && sameArea });
}

async function useRing(ring, kind, extra = {}) {
  const token = ++state.selectionToken;
  state.regionToken += 1; state.areaToken += 1;
  const { region, scores } = await regionForRing(ring);
  if (token !== state.selectionToken) return false;
  if (!region) { toast(`Outside the regions we cover (${state.index.regions.map((r) => r.name).join(', ')}).`); return false; }
  if (!(await loadRegion(region.id))) return false;
  return setArea({ kind, ring, ...extra, footprintScores: scores });
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
  const files = await Promise.all(ys.map((y) => loadYear(y, 'hot').catch((err) => { err.year = y; throw err; })));
  const [hm] = await unitData(meta.id, 'hot'); // the hotspot view's flags and notes go with the hotspot weights
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
      const s = SENSORS[c.sensor[i]]; const modis = s === 'T' || s === 'A';
      lines.push([c.lat[i], c.lon[i], modis ? c.bright[i] : '', modis ? c.bright2[i] : '', modis ? '' : c.bright[i], modis ? '' : c.bright2[i],
        c.scan[i], c.track[i], date.toISOString().slice(0, 10), String(c.time[i]).padStart(4, '0'),
        meta.satellite_field[s], meta.instrument_field[s], c.conf[i], meta.versions[c.version[i]], c.frp[i], c.dn[i] ? 'N' : 'D', 0,
        s, j >= 0 ? flagLabel(j, hm) : '', c.w[i]].map(csvCell).join(','));
      count += 1; wsum += c.w[i];
    }
  }
  download(`${fileStem()}_hotspots.csv`, `${lines.join('\n')}\n`);
  $('#csv-status').textContent = `${count.toLocaleString('en-US')} detections in the exact area, ${y0}–${y1}. Column w is each one’s share of the ${state.unit === 'bd' ? 'hotspot view’s ' : ''}harmonized estimate (total ${fmt(wsum)}${state.unit === 'bd' ? ' MODIS-equivalent detections' : ''}).`;
}

// Every burning day inside the exact area: one row per ~1 km square, day and time of day, and satellite family.
async function burningCsv() {
  const [y0, y1] = spanYears(); const area = state.area;
  $('#csv-status').textContent = `Reading burning days for ${y0}–${y1}…`;
  const ys = []; for (let y = y0; y <= y1; y += 1) ys.push(y);
  const files = await Promise.all(ys.map((y) => loadYear(y, 'bd').catch((err) => { err.year = y; throw err; })));
  const head = ['latitude', 'longitude', 'cell_x', 'cell_y', 'acq_date', 'daynight', 'family', 'detections', 'max_frp', 'frp_class', 'source_flag', 'w'];
  const lines = [head.join(',')]; let count = 0; let wsum = 0;
  for (const f of files) {
    if (!f) continue;
    const c = f.cols;
    for (let i = 0; i < f.n; i += 1) {
      if (!hotspotInArea(c, i, area)) continue;
      const date = new Date(Date.UTC(f.year, 0, c.doy[i]));
      const j = indexOf(f.year, date.getUTCMonth() + 1);
      lines.push([c.lat[i].toFixed(3), c.lon[i].toFixed(3), f.x0 + c.x[i], f.y0 + c.y[i], date.toISOString().slice(0, 10), c.dn[i] ? 'N' : 'D',
        FAMILY[c.fam[i]], c.nd[i], c.frp[i] ?? '', `f${c.k[i]}`, j >= 0 ? flagLabel(j) : '', c.w[i]].map(csvCell).join(','));
      count += 1; wsum += c.w[i];
    }
  }
  download(`${fileStem()}_burning_days.csv`, `${lines.join('\n')}\n`);
  $('#csv-status').textContent = `${count.toLocaleString('en-US')} burning days in the exact area, ${y0}–${y1}. Column w is each one’s share of the harmonized estimate (total ${fmt(wsum)}); latitude and longitude are the centre of its 0.01° square (cell_x, cell_y).`;
}

function monthlyCsv() {
  const [y0, y1] = spanYears(); const meta = state.meta; const s = state.series; const bd = state.unit === 'bd';
  const how = s.exact ? (bd ? `exact sums of the burning-day weights inside the shape (${s.count} burning days; a 0.01-degree square counts when its centre is inside)` : `exact sums of the detection weights inside the shape (${s.count} detections)`)
    : `the sum of its ${state.monthly.cells.ix.length} cells of ${state.monthly.cell_deg} deg (equal to the exact sum within rounding, bound: 0.005 × cells + 0.00005 × monthly records + 0.0001)`;
  const methods = `# CEDRUS monthly ${bd ? 'burning days (days each 0.01-degree square had a fire detected)' : 'fire detections'} in MODIS-equivalent units; harmonized_estimate is the expected value (sum of ${bd ? 'burning-day' : 'hotspot'} weights w + background). Region ${meta.name}. Area ${areaName()}: ${how}. `
    + (state.area.outside >= 0.01 ? `${Math.round(state.area.outside * 100)}% of the area is outside ${meta.name}'s FIRMS country file and not counted. ` : '')
    + `Model ${unitMeta().model}. p10/p90 approximate: cell 80% ranges scaled to the area and combined in quadrature. `
    + 'source_flag: bridged = Terra / Terra share (2000-12..2002-06); observed = MODIS Terra+Aqua (2002-07..2021-12); estimated = from VIIRS (2022-01 on: S-NPP+NOAA-20 averaged or whichever flies). '
    + 'A satellite enters the average for a calendar month and time of day only if the model has a ratio above 0 there; the flag says where one was left out. '
    + `naive = MODIS to 2011 then raw Suomi NPP ${bd ? 'burning days' : 'counts'}. Data built ${meta.generated_at} from NASA FIRMS; files and SHA-256 in data/regions.json.`;
  const lines = [methods.replace(/,/g, ';'), 'month,harmonized_estimate,p10,p90,naive,background,source_flag'];
  if (meta.id === 'la_rioja' && state.sel != null) {
    const { year, moy } = monthOf(state.sel); const start = year - (moy < 8 ? 1 : 0);
    if (y0 <= start && y1 >= start + 1) {
      const total = seasonTotal(start);
      lines.splice(1, 0, `# Season ${start}-08 to ${start + 1}-02; total=${total == null ? 'uncomputable' : total.toFixed(4)}; monthly completeness unknown`);
    }
  }
  for (let y = y0; y <= y1; y += 1) {
    for (let moy = 1; moy <= 12; moy += 1) {
      const j = indexOf(y, moy); if (j < 0) continue;
      lines.push([iso(j), s.m[j].toFixed(4), s.lo[j].toFixed(1), s.hi[j].toFixed(1), Math.round(s.naive[j]), s.bg[j].toFixed(4), csvCell(flagLabel(j))].join(','));
    }
  }
  download(`${fileStem()}_monthly_${unit().id}.csv`, `${lines.join('\n')}\n`);
  $('#csv-status').textContent = `Monthly record (${unit().many}) ${y0}–${y1} for ${areaName()} downloaded.`;
}

// ---------- controls ----------
function bindControls() {
  $('#region').addEventListener('change', (e) => useRegion(e.target.value, { keepDrawing: !!$('#spans-warning'), keepMonth: true }).catch(failed));
  ['bd', 'hot'].forEach((u) => $(`#unit-${u}`).addEventListener('click', () => setUnit(u).catch(failed))); // also cancels a pending switch
  $('#example-lebanon').addEventListener('click', () => useRegion('lebanon').catch(failed));
  $('#draw-rectangle').addEventListener('click', () => startDrawing('rectangle'));
  $('#draw-polygon').addEventListener('click', () => startDrawing('polygon'));
  $('#draw-clear').addEventListener('click', () => { stopDrawing(); setArea({ kind: 'region' }); if (state.map) state.map.fitBounds(state.meta.default_view.bounds, { padding: 16, duration: 600 }); });
  $('#area-form').addEventListener('submit', (e) => {
    e.preventDefault();
    const lat = Number($('#lat').value); const lon = Number($('#lon').value); const radius = Number($('#radius').value);
    if (!$('#lat').value || !$('#lon').value || !(Math.abs(lat) <= 90) || !(Math.abs(lon) <= 180)) { toast('Enter a latitude (−90 to 90) and a longitude (−180 to 180).'); $('#lat').focus(); return; }
    if (!(radius >= 1 && radius <= 500)) { toast('Radius must be between 1 and 500 km.'); $('#radius').focus(); return; }
    stopDrawing();
    fx.burn($('#circle-go'), () => useRing(circleRing(lat, lon, radius), 'circle', { lat, lon, radius })).catch(failed);
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
  // Three views of one calendar: the grid, the tree rings (fx.js), the table.
  const setView = (v) => {
    state.view = v; state.table = v === 'table';
    $('#table-toggle').setAttribute('aria-pressed', String(v === 'table')); $('#table-toggle').textContent = v === 'table' ? 'Show as calendar' : 'Show as table';
    $('#rings-toggle').setAttribute('aria-pressed', String(v === 'rings')); $('#rings-toggle').textContent = v === 'rings' ? 'Show as grid' : 'Show as tree rings';
    $('#cal-grid').hidden = v !== 'grid'; $('#calendar-table').hidden = v !== 'table'; $('#cal-rings').hidden = v !== 'rings';
    if (v === 'rings') fx.renderRings();
  };
  $('#table-toggle').addEventListener('click', () => setView(state.view === 'table' ? 'grid' : 'table'));
  $('#rings-toggle').addEventListener('click', () => setView(state.view === 'rings' ? 'grid' : 'rings'));
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
  // A download is a burning button: a fuse runs its edge while the file is built, embers drop into the file when it is.
  $('#csv-hotspots').addEventListener('click', () => fx.burn($('#csv-hotspots'), hotspotsCsv).catch((err) => { $('#csv-status').textContent = err.year ? `Couldn’t load detections for ${err.year} — try again.` : `Download failed: ${err.message}`; }));
  $('#csv-burning').addEventListener('click', () => fx.burn($('#csv-burning'), burningCsv).catch((err) => { $('#csv-status').textContent = err.year ? `Couldn’t load burning days for ${err.year} — try again.` : `Download failed: ${err.message}`; }));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && state.drawing) { stopDrawing(); toast('Drawing cancelled.'); } });
  $('#csv-monthly').addEventListener('click', () => fx.burn($('#csv-monthly'), monthlyCsv).catch((err) => { $('#csv-status').textContent = `Download failed: ${err.message}`; }));
  $('#zoom-in').addEventListener('click', () => state.map?.zoomIn());
  $('#zoom-out').addEventListener('click', () => state.map?.zoomOut());
}

// The hero video loads nothing until the calendar is on screen, and never plays for reduced motion or data saving.
const video = $('.hero-video'); const videoToggle = $('.video-toggle');
function syncVideo() { videoToggle.textContent = video.paused ? '▶' : 'Ⅱ'; const l = video.paused ? 'Play background video' : 'Pause background video'; videoToggle.setAttribute('aria-label', l); videoToggle.title = l; }
function startVideo() {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches || navigator.connection?.saveData) return;
  video.preload = 'auto';
  video.play().catch(syncVideo);
}
videoToggle.addEventListener('click', () => { if (video.paused) { video.play().catch(() => toast('Use your browser’s video playback permission to play the background.')); } else { video.pause(); } });
video.addEventListener('play', syncVideo); video.addEventListener('pause', syncVideo);
syncVideo();

// ---------- dialogs ----------
const DOCS = 'https://github.com/hyounes-svg/cedrus/blob/main/docs/';
function docLink(name) { return `<a href="${DOCS}${name}">docs/${name}</a>`; }
function methodologyHtml() {
  const idx = state.index; if (!idx) return '<p>Data not loaded yet.</p>';
  const SAT = { snpp: 'Suomi NPP', noaa20: 'NOAA-20' }; const FAM = { modis: 'MODIS', snpp: 'Suomi NPP', noaa20: 'NOAA-20' };
  const fitted = (detail, word) => Object.entries(detail.satellites).map(([k, v]) => `${SAT[k]} ${v.train[0]} to ${v.train[1]} (${Object.entries(v.train_detections ?? v.train_burning_days).map(([f, x]) => `${FAM[f]} ${x.toLocaleString('en-US')}`).join(', ')} ${word})`).join('; ');
  const regions = idx.regions.map((r) => {
    const b = r.burning_days;
    return `<p><strong>${r.name}</strong> · ${r.months.first} to ${r.months.last} · ${r.cells} cells · burning days: model <code>${b.model}</code>, fitted ${fitted(b.model_detail, 'burning days')}; hotspots: model <code>${r.model}</code>, fitted ${fitted(r.model_detail, 'detections')}. Data built ${r.generated_at}.</p>
      <details><summary>${r.provenance.files.length} NASA FIRMS files and their SHA-256</summary><ul class="files">${r.provenance.files.map((f) => `<li><a href="${f.url}">${f.name}</a> · ${f.rows.toLocaleString('en-US')} rows · <code>${f.sha256}</code>${f.sha256_ok ? '' : ' <strong>(file changed since download)</strong>'}</li>`).join('')}</ul></details>`;
  }).join('');
  const r0 = idx.regions[0]; const bdm = r0.burning_days.model_detail;
  // From the data: the share of VIIRS burning days since 2022 that carry no weight, per region (regions.json zero_weight).
  const zw = idx.regions.map((r) => ({ name: r.name, z: r.burning_days.zero_weight })).filter((x) => x.z?.viirs_burning_days);
  const worst = [...zw].sort((a, b) => b.z.share - a.z.share)[0];
  const zeroLimit = worst ? `<li id="zero-limit">In ${worst.name}, ${worst.z.weight_zero.toLocaleString('en-US')} of ${worst.z.viirs_burning_days.toLocaleString('en-US')} VIIRS burning days since 2022 (${Math.round(worst.z.share * 100)}%) carry no weight: their fire-power class never matched a MODIS fire in that season during 2012–2019, so the estimate rests on the others${zw.filter((x) => x !== worst).map((x) => ` (${x.name}: ${(x.z.share * 100).toFixed(1)}%)`).join('')}. A month where this is ${Math.round(worst.z.note_threshold * 100)}% or more says so in its notes.</li>` : '';
  return `<p><strong>Data.</strong> ${r0.provenance.source}. Filters: each region’s box; vegetation fires only (type 0); MODIS confidence ≥ 30; VIIRS confidence nominal or high.</p>
    <p><strong>Two ways to count, one switch.</strong> <em>Burning days</em> (the default): how many days each ~1 km square had a fire detected, in MODIS-equivalent terms. A square is 0.01° of longitude by 0.01° of latitude; it counts once per day and time of day (day or night) for each satellite family, however many detections fall in it, so a big fire seen as many overlapping pixels is not counted many times over. <em>Hotspots</em>: every satellite fire detection, in MODIS-equivalent counts — the numbers the challenge asks for. Both views use the same record, the same areas and the same checks; the hotspot CSV (every detection with its weight) can be downloaded in both views, and the burning-day CSV (every burning day with its weight) in the burning-day view; the switch is above the region list.</p>
    <p><strong>One record from three sources.</strong> December 2000 – June 2002: <em>bridged</em>, Terra alone divided by Terra’s share of MODIS (detections, or burning days in that view) in the same calendar month of 2003–2011 (each month’s share pulled toward the all-year share by 20 pseudo-counts, so a month with few fires cannot give a share of 0 or 1). July 2002 – December 2021: <em>observed</em>, MODIS Terra + Aqua. From January 2022: <em>estimated</em> from VIIRS, because Terra and Aqua have left their planned orbits: the average of the Suomi NPP and the NOAA-20 estimates when both satellites have data that month, or whichever one does, so the record carries on after Suomi NPP stops. The naive record joins MODIS to raw Suomi NPP in 2012, which creates a false jump.</p>
    <p><strong>Burning days: model <code>${r0.burning_days.model}</code>.</strong> In plain words: for every 0.25° cell, calendar month and day or night, it learns from 2012–2019, when MODIS and Suomi NPP flew together, how many MODIS burning days one Suomi NPP burning day stands for — separately for four classes of fire power (the strongest detection of that square and day: zero or missing, under 5, 5–20, and 20 MW or more), because how many of VIIRS’s fires MODIS also sees depends on how strong they are. A cell with little history leans on its region’s ratio for that month and class (${bdm.a} pseudo-burning-days of shrinkage); a cell with a long history speaks for itself. Where VIIRS saw nothing, it adds a small background. NOAA-20 is first put on Suomi NPP’s scale — one factor per time of day, measured in burning days from April 2018 to December 2019 when both flew — and then goes through the same conversion. Nothing from 2020 on is used, and the settings are frozen: the export refuses to run unless data/processed/tournament/frozen_round3.json has the SHA-256 recorded at the freeze (<code>${bdm.frozen.sha256}</code>).</p>
    <p><strong>Hotspots: model <code>${r0.model}</code>.</strong> The same idea in detections, without the fire-power classes: for every 0.25° cell, calendar month and day or night, how many MODIS detections one Suomi NPP detection stands for, learned from 2012–2019. A cell with little history leans on its region’s ratio for that month (30 pseudo-detections of shrinkage); only months in which Suomi NPP saw something enter the ratio. Where VIIRS saw nothing, it adds the background: a small region-wide expected count per month and time of day for places where VIIRS saw nothing. NOAA-20 is put on Suomi NPP’s scale the same way. The export refuses to run unless data/processed/round2/frozen.json has the SHA-256 recorded at the freeze. Where a month and time of day had no MODIS fire at all in the fitting years, detections there weigh 0.</p>
    <p><strong>What is shown.</strong> Every value is the harmonized estimate (expected value): the weights of the records (detections or burning days) plus the background. The 80% ranges of estimated months come from the model’s own predictive distribution plus the uncertainty of NOAA-20’s factor, combined for day and night and for the two satellites (approximate); bridged months keep a placeholder range (negative binomial, size 5).</p>
    <p><strong>How we know it works — including what failed.</strong> Each sealed exam below was written down before it was run, on regions the model had never seen; the figures said to come from development data are from the regions the models were chosen on, and are not exam results. Round 1’s winner, model A, failed its sealed confirmation: on new regions, one ratio per region beat it, and its NOAA-20 handover agreed only 69%. Round 2 removed A’s double-counting quirk and calibrated NOAA-20 against Suomi NPP, which raised handover agreement to 92.6% on the development data. Round-2 confirmation on four new sealed regions: <span id="r2-confirmation"><strong>confirmed</strong> on central Spain, southern Italy, southwest Australia and southern California (all five pre-registered tests passed: cell-month error 55.8% vs 60.9% for one ratio per region, totals within 3.7%, NOAA-20 handover agreement 92.1%)</span>; that is the hotspot model. A tournament of nine candidates on 17 development regions then found that burning days harmonize better than hotspot counts: skill 30.6% against 23.5% for the hotspot champion, each measured against its own one-ratio baseline (the plan needed 25.8%; an independent tester’s common footing still gives 28.4%). Its best model, D-a, was frozen and sat one sealed exam on four more regions it had never seen — northern Algeria, southern France, South Australia and northern California: <span id="r3-confirmation"><strong>confirmed</strong>, all five pre-registered tests passed: cell-month error 29.7% (one ratio per region: 36.2%); the 80% ranges held the observed value in 83.8% of active cell-months (required 70–90%); predicted total 1.069 × observed (required 0.90–1.10); national-month error 11.6% (required ≤ 21.3%); NOAA-20 handover agreement 97.3%, 213 of 219 months (required ≥ 80%)</span>. That is the burning-day model, and why burning days are the default. ${docLink('ROUND3_CONFIRMATION.md')} · ${docLink('TOURNAMENT_RESULTS.md')} · ${docLink('ROUND2_CONFIRMATION.md')} · ${docLink('ROUND2_SELECTION.md')} · ${docLink('CONFIRMATION_RESULTS.md')}</p>
    <p><strong>Areas.</strong> For a drawn shape or a circle, the calendar adds up the weight of every record inside it: an exact sum. A hotspot is inside if its position is; a burning day is inside if the centre of its ~1 km square is. Its 80% range scales each touched cell’s range by the share of that cell’s value inside the shape and combines them in quadrature (approximate); each touched cell’s background counts by the share of the cell’s area inside the shape. Drawn shapes and circles are exact sums; the whole-region view adds up its 0.25° cells, which equals the exact sum within rounding (bound: 0.005 × cells + 0.00005 × monthly records + 0.0001; Syria hotspots reached a 0.1235 monthly gap). Parts of a shape outside the region’s FIRMS country file are reported, not counted.</p>
    <p><strong>Quiet months.</strong> Any month whose expected value is under ${QUIET} counts as zero, before and after 2022, for colours and for every comparison; where a normal month has fewer than ${FEW_FIRES} detections (or burning days, in that view), the calendar does not compare it as a percentage.</p>
    <p><strong>Trust check.</strong> Needs at least ${MIN_BASE_YEARS} baseline years (the same calendar month, 2003 to the year before). R = half of the month’s 80% range ÷ the larger of (a) how far the month is from the baseline median and (b) half the interquartile range. Reliable below 0.5, use with care 0.5–1 (dashed outline in the calendar), too uncertain above 1 (hatched). When the baseline median is below ${FEW_FIRES} the verdict is “few fires — too few to judge”. Observed months have no range, so R = 0.</p>
    <p><strong>Where the record ends.</strong> A satellite file’s final month counts only if the file has a detection in that month’s last 3 days. The record runs to the last month a VIIRS satellite covers; 2026 to the present needs NASA’s FIRMS near-real-time API key, which is pending.</p>
    <p><strong>Limits.</strong></p><ul>
      <li>Neither unit is burned area: a burning day says a ~1 km square had a fire detected that day, not how much of it burned; one large fire produces many detections and many burning days.</li>
      <li>Values from 2022 are MODIS-equivalent estimates, not observations; their ranges are approximate.</li>
      <li>Ranges of bridged months (Dec 2000 – Jun 2002) are a placeholder: the models describe VIIRS, not Terra alone.</li>
      <li>Burning days whose strongest detection has no fire power (FRP 0 or less) are rare and their ratio is unstable: a known risk recorded before the round-3 exam (in the exam no region-month got more than a quarter of its total from them). In Portugal and Lebanon their fitted ratio is 0, so they add nothing.</li>
      ${zeroLimit}
      <li>Where a month, time of day and fire-power class had no MODIS fire at all in the fitting years, the models give VIIRS records there no weight.</li>
      <li>The conversions assume the MODIS-to-VIIRS ratio of a calendar month did not change after the fitting years.</li>
      <li>A region’s data footprint is the set of 0.25° cells where its country file ever had a detection; sea and neighbouring countries fall outside it.</li></ul>
    ${regions}
    <p><strong>Credits.</strong> Ideas we learned from: Kiln Watch, samuelakosa/firecal, SHIFT, Ember-Line, sagoresarker/nasa, Agun-Panjika. Basemap: NASA GIBS. Fire data: NASA FIRMS.</p>
    <p><strong>Use of AI.</strong> AI coding assistants helped write the pipeline and this website. The method, the test rules and every number shown come from the code and data in the repository and can be rebuilt from it.</p>
    <p class="files">An earlier test of a different conversion (a ratio per cell) is in docs/RESULTS.md.</p>`;
}
const dialogs = {
  methodology: { title: 'Data &amp; Methodology', body: methodologyHtml },
  about: { title: 'Roots in Nature.<br>Data for a Safer Tomorrow.', body: () => '<p>We are <strong>CEDRUS</strong>, joining the NASA Space Apps local event in Beirut.</p><p>Our challenge: <strong>Harmonization of MODIS and VIIRS Hot Spots.</strong> MODIS is being retired, and Suomi NPP stops delivering data on 2 Nov 2026. We build one fire record that survives the handover, test it honestly, and turn it into a fire calendar for any area.</p>' },
};
document.querySelectorAll('[data-dialog]').forEach((button) => button.addEventListener('click', () => {
  const item = dialogs[button.dataset.dialog]; $('#dialog-title').innerHTML = item.title; $('#dialog-body').innerHTML = item.body(); $('#detail-dialog').showModal();
}));
$('.dialog-close').addEventListener('click', () => $('#detail-dialog').close()); $('.dialog-done').addEventListener('click', () => $('#detail-dialog').close());
$('#detail-dialog').addEventListener('click', (event) => { if (event.target === $('#detail-dialog')) { const r = event.target.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) event.target.close(); } });
document.querySelectorAll('nav a').forEach((link) => link.addEventListener('click', () => { document.querySelectorAll('nav a').forEach((item) => { item.classList.toggle('active', item === link); if (item === link) item.setAttribute('aria-current', 'page'); else item.removeAttribute('aria-current'); }); }));

function failed(err) {
  $('#data-badge').textContent = 'NO DATA';
  $('#map-caption').textContent = location.protocol === 'file:'
    ? `Could not load the fire record (${err.message}). Serve web/ over http rather than opening the file directly.`
    : `Could not load the fire record (${err.message}). Reload the page to try again.`;
  console.error(err);
}

async function start() {
  state.index = await getJson('data/regions.json');
  let remembered = null;
  try { remembered = sessionStorage.getItem(UNIT_KEY); } catch { /* storage blocked: open on the default unit */ }
  state.unit = UNITS[remembered] ? remembered : (state.index.default_unit === 'hotspots' ? 'hot' : 'bd');
  renderUnitSwitch();
  $('#region').innerHTML = state.index.regions.map((r) => `<option value="${r.id}">${r.name}</option>`).join('');
  bindControls(); fx.init();
  const first = state.index.regions[0].id;
  try { await useRegion(first); } catch { const u = state.unit; unitFailed(u, () => setUnit(u)); }
  // Both models the site runs on, each confirmed on sealed regions it had never seen (the dialog names them).
  $('#data-badge').textContent = 'Burning days & hotspots · both confirmed on unseen regions';
  initMap();
}

// The creative layer reads the record only through these.
const fx = createFx({
  $, state, fmt, label, monthOf, indexOf, years, cellView, selectMonth, renderMapValues, renderMonth, baseline, asCount, quantile, countColor,
  unit, areaName, flagAt, loadYear, cellKey, bboxRing, toast, MONTHS, MONTH_NAMES, QUIET, FEW_FIRES,
});

// For tools/probe_site.py: the same entry points the controls use.
window.cedrus = { state, useRing, useRegion, setUnit, selectMonth, indexOf, seasonTotal, fx, ready: start().catch((err) => { failed(err); throw err; }) };
