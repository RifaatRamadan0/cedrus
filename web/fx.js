// CEDRUS creative layer: fire as a material (docs/design/Fire_Made_Visible.pdf). Embers are activity, ash is the past,
// smoke is doubt. Every effect carries one fact from the record; motion plays once when something changes, then
// settles; nothing flashes faster than 3 times a second; with "reduce motion" (or Effects off) every effect is still.
// app.js owns the data and the rules; this module only draws them, through the api it is handed.

// Ember scale: luminance rises monotonically (0.014 → 0.90), so it reads in every colour-vision type and in grey print.
export const EMBER = ['#3a120c', '#5c170e', '#842312', '#a8321a', '#cf4a1b', '#e2622a', '#f0812b', '#f6a03d', '#f9bf4f', '#fcd98a', '#fff3cf'];
export const FLARE = 2.5;   // a month at least this many times its baseline median is a flare-up (▲)
export const COOL = 1 / 3;  // a month at most this share of its baseline median has cooled to ash (▽)
export const FLARE_MIN = 20; // ▲/▽ only where a normal month has at least this many: rarer, so each mark means something

const NS = 'http://www.w3.org/2000/svg';
const clamp01 = (x) => Math.max(0, Math.min(1, x));
const EMPTY = { type: 'FeatureCollection', features: [] };

export function createFx(api) {
  const { $, state } = api;
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)');
  let effects = true;
  try { effects = localStorage.getItem('cedrus.effects') !== 'off'; } catch { /* storage blocked: effects on */ }
  let sound = false; // never on by default, never remembered
  const motion = () => effects && !reduce.matches;
  const timer = (ms) => new Promise((r) => setTimeout(r, ms));

  // ---------------------------------------------------------------- tooltip (ember card)
  const tip = document.createElement('div'); tip.className = 'fx-tip'; tip.setAttribute('aria-hidden', 'true'); document.body.append(tip);
  function showTip(el, text, color) {
    const r = el.getBoundingClientRect();
    tip.textContent = text; tip.style.setProperty('--glow', color || '#f0812b'); tip.classList.add('on');
    const w = tip.offsetWidth; const h = tip.offsetHeight;
    let x = r.left + r.width / 2 - w / 2; let y = r.top - h - 10;
    if (y < 8) y = r.bottom + 10;
    x = Math.max(8, Math.min(window.innerWidth - w - 8, x));
    tip.style.transform = `translate(${Math.round(x)}px, ${Math.round(y)}px)`;
  }
  function hideTip() { tip.classList.remove('on'); }
  window.addEventListener('scroll', hideTip, { passive: true });

  // ---------------------------------------------------------------- calendar: first light, crosshair, flare tooltip
  let firstLight = false;
  function afterCalendar() {
    const grid = $('#cal-grid');
    if (!firstLight && grid.querySelector('[role=gridcell]')) {
      firstLight = true;
      if (motion()) {
        grid.classList.add('first-light');
        grid.querySelectorAll('.cal-row').forEach((row, k) => { row.style.animationDelay = `${k * 75}ms`; });
        setTimeout(() => grid.classList.remove('first-light'), 2800);
      }
    } else grid.classList.remove('first-light');
    if (state.view === 'rings') renderRings();
  }
  function bindCalendar() {
    const grid = $('#cal-grid');
    const clear = () => grid.querySelectorAll('.xh').forEach((c) => c.classList.remove('xh'));
    const over = (cell) => {
      clear();
      grid.querySelectorAll(`[data-year="${cell.dataset.year}"],[data-moy="${cell.dataset.moy}"]`).forEach((c) => c.classList.add('xh'));
      showTip(cell, cell.getAttribute('aria-label'), cell.style.backgroundColor);
    };
    grid.addEventListener('mouseover', (e) => { const cell = e.target.closest('[role=gridcell]'); if (cell) over(cell); });
    grid.addEventListener('mouseleave', () => { clear(); hideTip(); });
    grid.addEventListener('focusin', (e) => { const cell = e.target.closest('[role=gridcell]'); if (cell) over(cell); });
    grid.addEventListener('focusout', () => { clear(); hideTip(); });
  }

  // ---------------------------------------------------------------- fire tree rings (the calendar as a cross-section)
  const RC = 200; const RR = 166; const R0 = 24;
  let ringsFocus = null; let ringsGrown = false;
  function wedge(r0, r1, a0, a1) {
    const p = (r, a) => `${(RC + r * Math.sin(a)).toFixed(2)},${(RC - r * Math.cos(a)).toFixed(2)}`;
    return `M${p(r1, a0)} A${r1},${r1} 0 0 1 ${p(r1, a1)} L${p(r0, a1)} A${r0},${r0} 0 0 0 ${p(r0, a0)} Z`;
  }
  function renderRings() {
    const svg = $('#rings-svg'); if (!svg || !state.series) return;
    const ys = api.years(); const dr = (RR - R0) / ys.length; const gap = 0.014;
    let g = '<defs><pattern id="rings-hatch" width="4" height="4" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="4" height="4" fill="#121d26"/><line x1="0" y1="0" x2="0" y2="4" stroke="#3a4c58" stroke-width="1.2"/></pattern></defs>';
    let sel = '';
    ys.forEach((y, k) => {
      const r0 = R0 + k * dr + 0.3; const r1 = R0 + (k + 1) * dr - 0.3;
      g += `<g class="ring" style="animation-delay:${k * 45}ms">`;
      for (let moy = 1; moy <= 12; moy += 1) {
        const j = api.indexOf(y, moy); const c = api.cellView(j);
        const a0 = ((moy - 1) / 12) * 2 * Math.PI + gap; const a1 = (moy / 12) * 2 * Math.PI - gap;
        const fill = c.nd ? 'url(#rings-hatch)' : c.bg || (c.zero ? '#070b0e' : '#0f1a22'); // zero: darkest, clearly apart from the lowest colour
        const d = wedge(r0, r1, a0, a1);
        g += `<path d="${d}" fill="${fill}" data-j="${j}" data-year="${y}" data-moy="${moy}" class="${c.flare === 'up' ? 'flare' : ''}" data-tip="${api.MONTH_NAMES[moy - 1]} ${y}: ${c.text.replace(/"/g, '&quot;')}"/>`;
        if (j >= 0 && j === state.sel) sel = `<path class="ring-sel" d="${wedge(r0 - 0.6, r1 + 0.6, a0 - 0.01, a1 + 0.01)}"/>`;
        if (j >= 0 && j === ringsFocus) sel += `<path class="ring-focus" d="${wedge(r0 - 1, r1 + 1, a0 - 0.012, a1 + 0.012)}"/>`;
      }
      g += '</g>';
    });
    const mark = state.record === 'naive' ? 2012 : 2022; const km = ys.indexOf(mark);
    if (km > 0) {
      const rr = R0 + km * dr;
      g += `<circle class="ring-mark" cx="${RC}" cy="${RC}" r="${rr.toFixed(1)}"/>`;
    }
    for (let m = 0; m < 12; m += 1) {
      const a = ((m + 0.5) / 12) * 2 * Math.PI;
      g += `<text class="ring-month" x="${(RC + (RR + 14) * Math.sin(a)).toFixed(1)}" y="${(RC - (RR + 14) * Math.cos(a) + 4).toFixed(1)}" text-anchor="middle">${api.MONTHS[m]}</text>`;
    }
    g += `<text class="ring-year" x="${RC}" y="${RC + 4}" text-anchor="middle">${ys[0]}</text><text class="ring-note" x="${RC}" y="${RC + 15}" text-anchor="middle">centre</text>`;
    g += `<text class="ring-note" x="${RC}" y="${(RC + RR + 32).toFixed(0)}" text-anchor="middle">${ys.at(-1)} on the rim · click a wedge to open that month</text>`;
    if (km > 0) g += `<text class="ring-mark-label" x="${RC}" y="${(RC + RR + 43).toFixed(0)}" text-anchor="middle">dashed ring: ${mark}, ${state.record === 'naive' ? 'raw Suomi NPP counts start (watch the jump)' : 'the newer satellite takes over, on the same scale'}</text>`;
    svg.innerHTML = g + sel;
    svg.classList.toggle('grow', motion() && !ringsGrown); ringsGrown = true;
  }
  function bindRings() {
    const svg = $('#rings-svg');
    svg.addEventListener('click', (e) => { const p = e.target.closest('path[data-j]'); if (p && Number(p.dataset.j) >= 0) api.selectMonth(Number(p.dataset.j)); });
    svg.addEventListener('mouseover', (e) => { const p = e.target.closest('path[data-j]'); if (p) showTip(p, p.dataset.tip, p.getAttribute('fill').startsWith('#') ? p.getAttribute('fill') : '#3a4c58'); });
    svg.addEventListener('mouseleave', hideTip);
    svg.addEventListener('keydown', (e) => {
      const moves = { ArrowLeft: [0, -1], ArrowRight: [0, 1], ArrowUp: [1, 0], ArrowDown: [-1, 0] }; // up = outward = later year
      if (ringsFocus == null) ringsFocus = state.sel;
      const { year, moy } = api.monthOf(ringsFocus);
      if (moves[e.key]) {
        e.preventDefault();
        let y = year + moves[e.key][0]; let m = moy + moves[e.key][1];
        if (m < 1) { m = 12; y -= 1; } if (m > 12) { m = 1; y += 1; }
        const j = api.indexOf(y, m); if (j < 0) return;
        ringsFocus = j; renderRings();
        const p = svg.querySelector(`path[data-j="${j}"]`); $('#rings-live').textContent = p ? p.dataset.tip : '';
      } else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); api.selectMonth(ringsFocus); }
    });
    svg.addEventListener('focus', () => { ringsFocus = state.sel; renderRings(); const p = svg.querySelector(`path[data-j="${ringsFocus}"]`); $('#rings-live').textContent = p ? p.dataset.tip : ''; });
    svg.addEventListener('blur', () => { ringsFocus = null; renderRings(); });
  }

  // ---------------------------------------------------------------- map: embers, ignition rings, ash
  let map = null; let lastKey = ''; let lastCtx = ''; let lastArea = null; let lastFc = null; let ashFc = EMPTY;
  let dayNight = 'all'; let dnValues = null; let dnToken = 0; let dnPending = '';
  let lensOn = false;
  const CORE = ['+', 0.1, ['*', 0.5, ['get', 'r']]]; // ember radius, as a share of a 0.25° cell
  function cellPx(f) { // f × a 0.25° cell in pixels, at every zoom (web mercator: 256 px per 360° at zoom 0)
    const at = (z) => 0.25 * (256 / 360) * 2 ** z;
    return ['interpolate', ['exponential', 2], ['zoom'], 2, ['*', f, at(2)], 13, ['*', f, at(13)]];
  }
  function points(vals) {
    const { ix, iy } = state.monthly.cells; const deg = state.monthly.cell_deg; const max = state.cellMax || 1;
    const inside = new Set(state.areaCells); const region = state.area?.kind === 'region';
    const order = [];
    for (let c = 0; c < vals.length; c += 1) if (vals[c] >= api.QUIET) order.push(c);
    order.sort((a, b) => vals[b] - vals[a]);
    return { type: 'FeatureCollection', features: order.map((c, k) => ({ type: 'Feature',
      properties: { v: vals[c], r: Math.sqrt(Math.min(1, vals[c] / max)), rank: order.length > 1 ? k / (order.length - 1) : 0, ins: region || inside.has(c) ? 1 : 0 },
      geometry: { type: 'Point', coordinates: [(ix[c] + 0.5) * deg, (iy[c] + 0.5) * deg] } })) };
  }
  function dnKey() { return `${state.meta.id}/${state.loadedUnit}/${state.sel}/${dayNight}`; }
  function cellValues() {
    const j = state.sel;
    if (dayNight !== 'all') return dnValues?.key === dnKey() ? dnValues.v : null;
    return state.monthly.m.map((row) => row[j]);
  }
  function paintAt(t, S, D, steady = false) {
    // steady (playback): embers stay lit between months, so nothing blinks; only a faint ring marks each step
    const appear = steady ? 1 : ['max', 0, ['min', 1, ['/', ['-', t, ['*', ['get', 'rank'], S]], 0.22]]];
    const local = ['max', 0, ['min', 1, ['/', ['-', t, ['+', 0.05, ['*', ['get', 'rank'], S]]], D]]];
    const dim = ['case', ['==', ['get', 'ins'], 1], 1, 0.28];
    map.setPaintProperty('ember-core', 'circle-opacity', ['*', 0.95, appear, dim]);
    map.setPaintProperty('ember-halo', 'circle-opacity', ['*', 0.42, appear, dim]);
    map.setPaintProperty('ember-ring', 'circle-stroke-opacity', ['*', steady ? 0.35 : 0.85, ['-', 1, local], ['case', ['>', local, 0], 1, 0], ['get', 'ins']]);
    map.setPaintProperty('ember-ring', 'circle-radius', cellPx(['*', CORE, ['+', 1.15, ['*', 2.6, local]]]));
  }
  let igniteRaf = 0;
  function ignite(fast) {
    cancelAnimationFrame(igniteRaf);
    const S = fast ? 0 : 0.6; const D = fast ? 0.3 : 0.9; const total = S + D + 0.1;
    if (!motion()) { paintAt(1e3, S, D); return; }
    const t0 = performance.now();
    const step = (now) => {
      const t = (now - t0) / 1000;
      if (t >= total) { paintAt(1e3, S, D, fast); return; }
      paintAt(t, S, D, fast); igniteRaf = requestAnimationFrame(step);
    };
    paintAt(0, S, D, fast); igniteRaf = requestAnimationFrame(step);
  }
  function mapReady(m) {
    map = m;
    map.addSource('ash', { type: 'geojson', data: EMPTY });
    map.addSource('embers', { type: 'geojson', data: EMPTY });
    map.addSource('embers-raw', { type: 'geojson', data: EMPTY });
    map.addSource('rim', { type: 'geojson', lineMetrics: true, data: EMPTY });
    map.addSource('lens', { type: 'geojson', data: EMPTY });
    map.addLayer({ id: 'ash', type: 'circle', source: 'ash', paint: { 'circle-radius': cellPx(CORE), 'circle-color': '#8f8580', 'circle-opacity': 0.22, 'circle-blur': 0.35, 'circle-stroke-color': '#8f8580', 'circle-stroke-width': 0.8, 'circle-stroke-opacity': 0.35 } });
    map.addLayer({ id: 'ember-halo', type: 'circle', source: 'embers', paint: { 'circle-radius': cellPx(['*', 2.1, CORE]), 'circle-color': '#ff7a26', 'circle-blur': 1, 'circle-opacity': 0.42 } });
    map.addLayer({ id: 'ember-core', type: 'circle', source: 'embers', paint: { 'circle-radius': cellPx(CORE), 'circle-blur': 0.55, 'circle-opacity': 0.95,
      'circle-color': ['interpolate', ['linear'], ['get', 'r'], 0, '#b8401a', 0.35, '#f0812b', 0.7, '#fcd98a', 1, '#fff3cf'] } });
    map.addLayer({ id: 'ember-ring', type: 'circle', source: 'embers', paint: { 'circle-radius': cellPx(CORE), 'circle-opacity': 0, 'circle-stroke-color': '#ffcf7a', 'circle-stroke-width': 1.6, 'circle-stroke-opacity': 0 } });
    map.addLayer({ id: 'raw-halo', type: 'circle', source: 'embers-raw', layout: { visibility: 'none' }, paint: { 'circle-radius': cellPx(['*', 2.1, CORE]), 'circle-color': '#ff4d5a', 'circle-blur': 1, 'circle-opacity': 0.45 } });
    map.addLayer({ id: 'raw-core', type: 'circle', source: 'embers-raw', layout: { visibility: 'none' }, paint: { 'circle-radius': cellPx(CORE), 'circle-blur': 0.5, 'circle-opacity': 0.95,
      'circle-color': ['interpolate', ['linear'], ['get', 'r'], 0, '#a8203a', 0.5, '#ff5a5a', 1, '#ffd2d2'] } });
    map.addLayer({ id: 'lens-line', type: 'line', source: 'lens', paint: { 'line-color': '#fff3e4', 'line-width': 1.4, 'line-dasharray': [2, 2] } });
    map.addLayer({ id: 'rim', type: 'line', source: 'rim', layout: { 'line-cap': 'round', 'line-join': 'round' },
      paint: { 'line-width': 4, 'line-blur': 1.2, 'line-opacity': 0, 'line-gradient': ['interpolate', ['linear'], ['line-progress'], 0, 'rgba(0,0,0,0)', 1, 'rgba(0,0,0,0)'] } });
    initHeat(); initLens();
    mapMonth();
    if (state.area) rim(state.area.kind === 'region' ? api.bboxRing(state.meta.bbox) : state.area.ring);
  }
  // Called whenever the map's month, area, region or unit is drawn (app.js renderMapValues).
  function mapMonth({ fast = false } = {}) {
    coldGround();
    if (!map?.getSource('embers') || !state.monthly || state.sel == null || !state.meta) return;
    const key = dnKey(); const ctx = `${state.meta.id}/${state.loadedUnit}`;
    const vals = cellValues();
    if (dayNight !== 'all' && !vals) { if (dnPending !== key) { dnPending = key; loadDayNight(); } return; }
    const fc = points(vals);
    const monthChanged = key !== lastKey;
    if (ctx !== lastCtx) ashFc = EMPTY; else if (monthChanged && lastFc) ashFc = lastFc; // the month before cools to ash
    map.getSource('ash').setData(ashFc);
    map.getSource('embers').setData(fc);
    map.getSource('embers-raw').setData(points(state.monthly.naive.map((row) => row[state.sel])));
    if (monthChanged || lastArea !== state.area) ignite(fast);
    lastKey = key; lastCtx = ctx; lastArea = state.area; lastFc = fc;
    dnBadge();
  }

  // ---------------------------------------------------------------- day and night passes
  async function loadDayNight() {
    const token = ++dnToken; const key = dnKey(); const { year, moy } = api.monthOf(state.sel);
    $('#map-dn-note').textContent = `Reading ${dayNight}-time ${api.unit().many} for ${api.label(state.sel)}…`; $('#map-dn-note').hidden = false;
    let f = null;
    try { f = await api.loadYear(year); } catch { if (token === dnToken) { dnPending = ''; $('#map-dn-note').textContent = `Couldn’t load ${year} — try again.`; } return; }
    if (token !== dnToken) return;
    const v = new Array(state.monthly.m.length).fill(0);
    if (f) {
      const c = f.cols; const want = dayNight === 'night' ? 1 : 0; const moyOf = [];
      for (let d = 1; d <= 366; d += 1) moyOf[d] = new Date(Date.UTC(year, 0, d)).getUTCMonth() + 1;
      for (let i = 0; i < f.n; i += 1) {
        if (c.dn[i] !== want || !(c.w[i] > 0) || moyOf[c.doy[i]] !== moy) continue;
        const ci = state.cellIndex.get(c.cell ? c.cell[i] : api.cellKey(c.lon[i], c.lat[i]));
        if (ci != null) v[ci] += c.w[i];
      }
    }
    dnValues = { key, v }; dnPending = ''; mapMonth();
  }
  function dnBadge() {
    const note = $('#map-dn-note');
    if (dayNight === 'all') { note.hidden = true; return; }
    const tot = (dnValues?.v ?? []).reduce((a, b) => a + b, 0);
    note.hidden = false;
    note.textContent = `${dayNight === 'night' ? 'Night' : 'Day'} passes, ${api.label(state.sel)}: ${api.fmt(tot)} ${api.unit().many} (record weights only, no background), whole cells`;
  }
  function setDayNight(v) {
    dayNight = v;
    document.querySelectorAll('#map-dn button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.dn === v)));
    $('#map-panel').classList.toggle('night', v === 'night');
    mapMonth();
  }

  // ---------------------------------------------------------------- the raw lens (two eyes, one fire)
  function initLens() {
    const panel = $('#map-panel'); const label = $('#lens-label');
    const off = () => { map.setFilter('ember-core', null); map.setFilter('ember-halo', null); map.setFilter('ember-ring', null); map.getSource('lens').setData(EMPTY); label.hidden = true;
      ['raw-core', 'raw-halo'].forEach((l) => map.setLayoutProperty(l, 'visibility', 'none')); };
    panel.addEventListener('pointermove', (e) => {
      if (!lensOn) return;
      const r = map.getCanvas().getBoundingClientRect(); const x = e.clientX - r.left; const y = e.clientY - r.top; const R = 72;
      if (x < 0 || y < 0 || x > r.width || y > r.height) return;
      const ring = []; for (let k = 0; k <= 48; k += 1) { const a = (k / 48) * 2 * Math.PI; const p = map.unproject([x + R * Math.cos(a), y + R * Math.sin(a)]); ring.push([p.lng, p.lat]); }
      const poly = { type: 'Polygon', coordinates: [ring] };
      ['ember-core', 'ember-halo', 'ember-ring'].forEach((l) => map.setFilter(l, ['!', ['within', poly]]));
      ['raw-core', 'raw-halo'].forEach((l) => { map.setLayoutProperty(l, 'visibility', 'visible'); map.setFilter(l, ['within', poly]); });
      map.getSource('lens').setData({ type: 'Feature', properties: {}, geometry: poly });
      label.hidden = false; label.style.transform = `translate(${Math.round(x)}px, ${Math.round(y - R - 20)}px) translateX(-50%)`;
      const j = state.sel; const yr = api.monthOf(j).year;
      label.textContent = yr < 2012 ? 'raw = MODIS itself before 2012' : 'raw Suomi NPP count, untranslated';
    });
    panel.addEventListener('pointerleave', () => { if (lensOn) off(); });
    $('#lens-toggle').addEventListener('click', () => {
      lensOn = !lensOn; $('#lens-toggle').setAttribute('aria-pressed', String(lensOn)); panel.classList.toggle('lens-on', lensOn);
      if (!lensOn) off(); else api.toast('Raw lens: move over the map. Inside the circle, untranslated counts; outside, the harmonized record.');
    });
  }

  // ---------------------------------------------------------------- heat trail and the torch
  let drawingNow = false;
  function initHeat() {
    const panel = $('#map-panel'); const cv = document.createElement('canvas'); cv.className = 'map-heat'; cv.setAttribute('aria-hidden', 'true');
    panel.append(cv);
    const ctx = cv.getContext('2d'); let pts = []; let head = null; let raf = 0; let last = null;
    const size = () => { const r = panel.getBoundingClientRect(); const d = window.devicePixelRatio || 1; cv.width = r.width * d; cv.height = r.height * d; ctx.setTransform(d, 0, 0, d, 0, 0); };
    new ResizeObserver(size).observe(panel); size();
    const draw = () => {
      raf = 0; const now = performance.now(); const r = panel.getBoundingClientRect();
      ctx.clearRect(0, 0, r.width, r.height);
      pts = pts.filter((p) => now - p.t < p.life);
      for (let k = 1; k < pts.length; k += 1) {
        const a = pts[k - 1]; const b = pts[k]; if (a.kind !== 'draw' || b.kind !== 'draw' || b.t - a.t > 120) continue;
        const age = clamp01((now - b.t) / b.life);
        const col = age < 0.18 ? `rgba(255,243,207,${1 - age})` : age < 0.5 ? `rgba(255,${Math.round(150 - 90 * age)},42,${0.95 - age})` : `rgba(58,47,42,${(1 - age) * 1.2})`;
        ctx.strokeStyle = col; ctx.lineWidth = 3.2 - age * 1.6; ctx.lineCap = 'round';
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      }
      for (const p of pts) {
        if (p.kind !== 'hot') continue;
        const age = clamp01((now - p.t) / p.life);
        ctx.fillStyle = `rgba(255,140,50,${(1 - age) * 0.3})`; ctx.beginPath(); ctx.arc(p.x, p.y, 2 + 7 * (1 - age), 0, 2 * Math.PI); ctx.fill();
      }
      if (head && drawingNow) {
        const g = ctx.createRadialGradient(head.x, head.y, 0, head.x, head.y, 14);
        g.addColorStop(0, 'rgba(255,248,224,1)'); g.addColorStop(0.3, 'rgba(255,190,90,0.9)'); g.addColorStop(1, 'rgba(255,110,30,0)');
        ctx.fillStyle = g; ctx.beginPath(); ctx.arc(head.x, head.y, 14, 0, 2 * Math.PI); ctx.fill();
      }
      if (pts.length || (head && drawingNow)) raf = requestAnimationFrame(draw);
    };
    const kick = () => { if (!raf) raf = requestAnimationFrame(draw); };
    panel.addEventListener('pointermove', (e) => {
      if (!motion() || lensOn) return;
      const r = panel.getBoundingClientRect(); const x = e.clientX - r.left; const y = e.clientY - r.top;
      if (drawingNow) { head = { x, y }; if (!last || Math.hypot(x - last.x, y - last.y) > 2) { pts.push({ x, y, t: performance.now(), life: 1400, kind: 'draw' }); last = { x, y }; } kick(); return; }
    });
    panel.addEventListener('pointerleave', () => { head = null; last = null; kick(); });
  }
  function drawing(mode) {
    drawingNow = !!mode;
    $('#map-panel').classList.toggle('torch', drawingNow && motion());
  }

  // ---------------------------------------------------------------- the rim race (fire runs round a new area once)
  let rimRaf = 0;
  function rimColor(d) {
    if (d < 0) return 'rgba(255,140,50,0)';
    if (d < 0.015) return 'rgba(255,243,207,1)';
    if (d < 0.32) { const u = d / 0.32; return `rgba(255,${Math.round(176 - 96 * u)},${Math.round(70 - 40 * u)},${(1 - 0.55 * u).toFixed(3)})`; }
    return 'rgba(58,47,42,0.6)';
  }
  function rimGradient(p) {
    const e = ['interpolate', ['linear'], ['line-progress']];
    for (let k = 0; k <= 60; k += 1) { const x = k / 60; e.push(x, rimColor(p - x)); }
    return e;
  }
  function rim(ring) {
    if (!map?.getSource('rim') || !ring) return;
    cancelAnimationFrame(rimRaf);
    map.getSource('rim').setData({ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: ring } });
    if (!motion()) { map.setPaintProperty('rim', 'line-opacity', 0); return; }
    const t0 = performance.now(); const T = 1.25; const F = 0.8;
    const step = (now) => {
      const t = (now - t0) / 1000;
      map.setPaintProperty('rim', 'line-gradient', rimGradient(Math.min(1.33, (t / T) * 1.33)));
      map.setPaintProperty('rim', 'line-opacity', t < T ? 1 : Math.max(0, 1 - (t - T) / F));
      if (t < T + F) rimRaf = requestAnimationFrame(step);
    };
    rimRaf = requestAnimationFrame(step);
  }
  function areaChanged(area) { if (area) rim(area.kind === 'region' ? api.bboxRing(state.meta.bbox) : area.ring); }

  // ---------------------------------------------------------------- cold ground (an honest empty state)
  function coldGround() {
    const box = $('#cold-ground'); if (!box) return;
    const quiet = state.series && state.sel != null && state.series.m[state.sel] < api.QUIET && api.flagAt(state.sel) !== 'X';
    box.hidden = !quiet;
    if (quiet) box.querySelector('span').textContent = `Cold ground: no ${api.unit().many} in ${api.areaName()} in ${api.label(state.sel)}.`;
  }

  // ---------------------------------------------------------------- the ghost flame (this month vs a normal one)
  function flamePath(x, by, h, w, lean = 0) {
    const t = x + lean * w; const f = (v) => v.toFixed(1);
    return `M${f(t)},${f(by - h)} C${f(x + 0.2 * w)},${f(by - 0.7 * h)} ${f(x + 0.52 * w)},${f(by - 0.48 * h)} ${f(x + 0.5 * w)},${f(by - 0.22 * h)} `
      + `C${f(x + 0.48 * w)},${f(by - 0.03 * h)} ${f(x + 0.28 * w)},${f(by)} ${f(x)},${f(by)} C${f(x - 0.28 * w)},${f(by)} ${f(x - 0.48 * w)},${f(by - 0.03 * h)} ${f(x - 0.5 * w)},${f(by - 0.22 * h)} `
      + `C${f(x - 0.52 * w)},${f(by - 0.48 * h)} ${f(x - 0.16 * w)},${f(by - 0.66 * h)} ${f(t)},${f(by - h)} Z`;
  }
  // v: this month (counted: under QUIET is 0); base: app.js baseline(); returns markup or ''.
  function ghostFlame(v, base, monthName) {
    const [q1, q3] = [api.quantile(base.sorted, 0.25), api.quantile(base.sorted, 0.75)];
    const top = Math.max(v, base.sorted.at(-1) ?? 0, q3, 1); const H = 118; const by = 132;
    const hh = (x) => Math.max(3, H * Math.sqrt(Math.max(0, x) / top));
    const h = hh(v); const hm = hh(base.median); const w = (z) => z * 0.55 + 10;
    const r = v / base.median;
    const word = r >= 1.15 ? `${r >= 10 ? Math.round(r) : r.toFixed(1)}× a normal ${monthName}` : r <= 0.85 ? `${Math.round((1 - r) * 100)}% below a normal ${monthName}` : `about a normal ${monthName}`;
    const flame = v < api.QUIET ? `<circle cx="70" cy="${by - 3}" r="3" fill="#6f6560"/>`
      : `<g class="flame${motion() ? ' flicker' : ''}"><path d="${flamePath(70, by, h, w(h), 0.04)}" fill="url(#fx-flame-outer)"/><path d="${flamePath(70, by - 1, h * 0.66, w(h) * 0.62, 0.05)}" fill="url(#fx-flame-mid)"/><path d="${flamePath(70, by - 2, h * 0.34, w(h) * 0.32, 0.04)}" fill="#fff6d8"/></g>`;
    const y3 = by - hh(q3); const y1 = by - hh(q1);
    return `<div class="ghost" id="ghost-flame"><svg viewBox="0 0 140 142" role="img" aria-label="This month as a flame beside the dashed ghost of a normal ${monthName}: ${word}">
      <defs><linearGradient id="fx-flame-outer" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#e5481a"/><stop offset=".55" stop-color="#f27a26"/><stop offset="1" stop-color="#ffb347" stop-opacity=".85"/></linearGradient>
      <linearGradient id="fx-flame-mid" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#ffb84a"/><stop offset="1" stop-color="#ffe08a"/></linearGradient></defs>
      <path d="M26,${y3.toFixed(1)} h-5 V${y1.toFixed(1)} h5" fill="none" stroke="#a8998e" stroke-width="1"/><text x="13" y="${((y1 + y3) / 2).toFixed(1)}" class="ghost-usual" transform="rotate(-90 13 ${((y1 + y3) / 2).toFixed(1)})" text-anchor="middle">usual</text>
      ${flame}<path d="${flamePath(70, by, hm, w(hm))}" fill="none" stroke="#e6ddd6" stroke-width="1.3" stroke-dasharray="3 3" opacity=".85"/>
      <line x1="18" x2="122" y1="${by}" y2="${by}" stroke="#4a3a32"/></svg>
      <p><span>Flame: this month. Dashed ghost: the normal ${monthName} (median ${api.fmt(base.median)}). Bracket: the usual range, the middle half of ${base.first}–${base.last} (${api.fmt(q1)}–${api.fmt(q3)}).</span></p></div>`;
  }

  // ---------------------------------------------------------------- fire fingerprint (a place's seasonal shape)
  function smoothClosed(pts) {
    const n = pts.length; let d = `M${pts[0][0].toFixed(1)},${pts[0][1].toFixed(1)} `;
    for (let i = 0; i < n; i += 1) {
      const p0 = pts[(i - 1 + n) % n]; const p1 = pts[i]; const p2 = pts[(i + 1) % n]; const p3 = pts[(i + 2) % n];
      d += `C${(p1[0] + (p2[0] - p0[0]) / 6).toFixed(1)},${(p1[1] + (p2[1] - p0[1]) / 6).toFixed(1)} ${(p2[0] - (p3[0] - p1[0]) / 6).toFixed(1)},${(p2[1] - (p3[1] - p1[1]) / 6).toFixed(1)} ${p2[0].toFixed(1)},${p2[1].toFixed(1)} `;
    }
    return `${d}Z`;
  }
  function fingerprintData() {
    const s = state.series; const ys = api.years();
    const complete = (y) => [...Array(12).keys()].every((m) => { const j = api.indexOf(y, m + 1); return j >= 0 && api.flagAt(j) !== 'X'; });
    const last = ys.filter(complete).at(-1); // the normal uses complete years only
    const med = []; for (let moy = 1; moy <= 12; moy += 1) {
      const v = []; for (let y = 2003; y <= last; y += 1) { const j = api.indexOf(y, moy); if (j >= 0 && api.flagAt(j) !== 'X') v.push(api.asCount(s.m[j])); }
      v.sort((a, b) => a - b); med.push(v.length ? api.quantile(v, 0.5) : 0);
    }
    const year = api.monthOf(state.sel).year;
    const cur = []; for (let moy = 1; moy <= 12; moy += 1) { const j = api.indexOf(year, moy); cur.push(j >= 0 && api.flagAt(j) !== 'X' ? api.asCount(s.m[j]) : null); }
    return { med, cur, year, last, partial: cur.some((v) => v == null) };
  }
  function petal(vals, max, cx, cy, R) {
    const pt = (v, m) => { const a = (m / 12) * 2 * Math.PI; const r = 5 + (R - 5) * Math.sqrt(Math.max(0, v ?? 0) / max); return [cx + r * Math.sin(a), cy - r * Math.cos(a)]; };
    if (vals.every((v) => v != null)) return smoothClosed(vals.map(pt));
    // a year still in progress: only its recorded months, as a fan from the centre (missing months are not zero)
    const pts = vals.map((v, m) => (v == null ? null : pt(v, m))).filter(Boolean);
    return `M${cx},${cy} ${pts.map((p) => `L${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')} Z`;
  }
  function renderFingerprint() {
    const svg = $('#fp-svg'); if (!svg || !state.series) return;
    const { med, cur, year, last, partial } = fingerprintData();
    const max = Math.max(...med, ...cur.map((v) => v ?? 0));
    const cx = 110; const cy = 110; const R = 86;
    let g = `<circle cx="${cx}" cy="${cy}" r="${R}" class="fp-axis"/><circle cx="${cx}" cy="${cy}" r="${R / 2}" class="fp-axis"/>`;
    for (let m = 0; m < 12; m += 1) {
      const a = (m / 12) * 2 * Math.PI;
      g += `<line x1="${cx}" y1="${cy}" x2="${(cx + R * Math.sin(a)).toFixed(1)}" y2="${(cy - R * Math.cos(a)).toFixed(1)}" class="fp-spoke"/>`;
      if (m % 3 === 0) g += `<text x="${(cx + (R + 11) * Math.sin(a)).toFixed(1)}" y="${(cy - (R + 11) * Math.cos(a) + 3.5).toFixed(1)}" text-anchor="middle" class="fp-label">${api.MONTHS[m]}</text>`;
    }
    if (max < api.QUIET) {
      svg.innerHTML = g; $('#fp-caption').textContent = 'Too few fires here for a fingerprint.'; return;
    }
    g += `<path d="${petal(cur, max, cx, cy, R)}" class="fp-year"/><path d="${petal(med, max, cx, cy, R)}" class="fp-normal"/>`;
    svg.innerHTML = g;
    const peak = med.indexOf(Math.max(...med)); const yrMax = cur.reduce((b, v, m) => (v != null && v > (cur[b] ?? -1) ? m : b), 0);
    $('#fp-caption').innerHTML = `<strong>Normal peak: ${api.MONTH_NAMES[peak]}.</strong> Dashed: a normal year (median of each month, 2003–${last}). Filled: ${year}${partial ? ` (recorded months only: the record runs to ${api.MONTH_NAMES[cur.findLastIndex((v) => v != null)]})` : ''}, whose biggest month was ${api.MONTH_NAMES[yrMax]} (${api.fmt(cur[yrMax] ?? 0)} ${api.unit().many}).`;
  }

  // ---------------------------------------------------------------- two eyes, one fire (why raw counts jump)
  let translated = true; let eyesRaf = 0; let eyesPts = null;
  function yearly() {
    const s = state.series; const out = [];
    for (const y of api.years()) {
      let a = 0; let b = 0; let full = true;
      for (let moy = 1; moy <= 12; moy += 1) { const j = api.indexOf(y, moy); if (j < 0 || api.flagAt(j) === 'X') { full = false; break; } a += s.m[j]; b += s.naive[j]; }
      if (full) out.push({ y, h: a, n: b });
    }
    return out;
  }
  function renderEyes(animate = false) {
    const svg = $('#eyes-chart'); if (!svg || !state.series) return;
    const rows = yearly(); if (rows.length < 2) { svg.innerHTML = ''; return; }
    const W = 520; const H = 210; const ox = 40; const oy = 14; const w = W - ox - 12; const h = H - oy - 30;
    const vmax = Math.max(1, ...rows.map((r) => Math.max(r.h, r.n))) * 1.08;
    const X = (i) => ox + (i / (rows.length - 1)) * w; const Y = (v) => oy + h - (v / vmax) * h;
    const P = (key) => rows.map((r, i) => [X(i), Y(r[key])]);
    const pathOf = (pts) => pts.map((p, i) => `${i ? 'L' : 'M'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ');
    let g = '';
    const step = vmax > 4000 ? 2000 : vmax > 2000 ? 1000 : vmax > 800 ? 200 : vmax > 400 ? 100 : vmax > 80 ? 20 : 5;
    for (let t = 0; t < vmax; t += step) g += `<line x1="${ox}" x2="${ox + w}" y1="${Y(t).toFixed(1)}" y2="${Y(t).toFixed(1)}" class="eyes-gl"/><text x="${ox - 5}" y="${(Y(t) + 3).toFixed(1)}" text-anchor="end" class="eyes-tick">${t.toLocaleString('en-US')}</text>`;
    const i12 = rows.findIndex((r) => r.y === 2012);
    if (i12 > 0) g += `<rect x="${X(i12).toFixed(1)}" y="${oy}" width="${(ox + w - X(i12)).toFixed(1)}" height="${h}" class="eyes-band"/><text x="${(X(i12) + 5).toFixed(1)}" y="${oy + 11}" class="eyes-note">from 2012 the raw record is Suomi NPP’s sharper eye</text>`;
    rows.forEach((r, i) => { if (r.y % 5 === 0 || i === 0 || i === rows.length - 1) g += `<text x="${X(i).toFixed(1)}" y="${oy + h + 14}" text-anchor="middle" class="eyes-tick">${r.y}</text>`; });
    const from = translated ? P('n') : P('h'); const to = translated ? P('h') : P('n');
    g += `<path d="${pathOf(translated ? P('n') : P('h'))}" class="eyes-ghost ${translated ? 'raw' : 'harm'}"/><path id="eyes-main" d="${pathOf(animate ? from : to)}" class="eyes-main ${translated ? 'harm' : 'raw'}"/>`;
    svg.innerHTML = g;
    cancelAnimationFrame(eyesRaf);
    if (animate && motion()) {
      const t0 = performance.now(); const el = svg.querySelector('#eyes-main');
      const ease = (u) => 1 - (1 - u) ** 3;
      const tick = (now) => { const u = ease(clamp01((now - t0) / 1200)); el.setAttribute('d', pathOf(from.map((p, k) => [p[0], p[1] + (to[k][1] - p[1]) * u]))); if (u < 1) eyesRaf = requestAnimationFrame(tick); };
      eyesRaf = requestAnimationFrame(tick);
    } else svg.querySelector('#eyes-main').setAttribute('d', pathOf(to));
    const r11 = rows.find((r) => r.y === 2011); const r12 = rows.find((r) => r.y === 2012);
    const x = (a, b) => (a > 0 ? `×${(b / a).toFixed(1)}` : '–');
    $('#eyes-caption').innerHTML = r11 && r12
      ? `${api.areaName()}, ${api.unit().many} per year. From 2011 to 2012 the raw record jumps <strong class="raw-t">${x(r11.n, r12.n)}</strong> as the sharper satellite takes over; the translated record changes <strong class="harm-t">${x(r11.h, r12.h)}</strong>.`
      : `${api.areaName()}, ${api.unit().many} per year.`;
    eyesPts = rows;
  }
  function eyesPixels() {
    const grid = (n, fine) => {
      const s = 140 / n; let out = `<rect width="140" height="140" rx="10" class="px-bg"/><ellipse cx="72" cy="70" rx="30" ry="31" class="px-fire"/>`; let lit = 0;
      for (let i = 0; i < n; i += 1) for (let k = 0; k < n; k += 1) {
        const cx = i * s + s / 2; const cy = k * s + s / 2; const d = ((cx - 72) / 30) ** 2 + ((cy - 70) / 31) ** 2;
        const hot = fine ? d < 1 : d < 0.62; if (hot) lit += 1;
        out += `<rect x="${(i * s + 0.8).toFixed(1)}" y="${(k * s + 0.8).toFixed(1)}" width="${(s - 1.6).toFixed(1)}" height="${(s - 1.6).toFixed(1)}" rx="${fine ? 1.4 : 4}" class="${hot ? 'px-hot' : 'px-off'}"/>`;
      }
      return [out, lit];
    };
    const [a, na] = grid(4, false); const [b, nb] = grid(11, true); // 1 km / 375 m = 2.7 per side, about 7 per pixel
    $('#eyes-pixels').innerHTML = `<figure><svg viewBox="0 0 140 140" role="img" aria-label="Older eye: big pixels, ${na} lit">${a}</svg><figcaption><strong>Older eye</strong> MODIS · 1 km pixels · ${na} lit</figcaption></figure>
      <span class="eyes-eq">same<br>fire</span>
      <figure><svg viewBox="0 0 140 140" role="img" aria-label="Newer eye: small pixels, ${nb} lit">${b}</svg><figcaption><strong>Newer eye</strong> VIIRS · 375 m pixels · ${nb} lit</figcaption></figure>`;
  }

  // ---------------------------------------------------------------- smoke (doubt) on the month's number
  function smokeClass(key) { return key === 'care' || key === 'uncertain' ? `smoke ${key}` : ''; }

  // ---------------------------------------------------------------- burning buttons
  function burn(btn, work) {
    const p = Promise.resolve().then(work);
    if (!btn) return p;
    btn.classList.remove('charred'); btn.classList.add('burning'); const t0 = performance.now();
    const done = async (ok) => {
      if (motion()) await timer(Math.max(0, 650 - (performance.now() - t0)));
      btn.classList.remove('burning');
      if (!ok) return;
      btn.classList.add('charred');
      if (btn.classList.contains('download') && motion()) embersToFile(btn);
      setTimeout(() => btn.classList.remove('charred'), 2600);
    };
    p.then((r) => done(r !== false), () => done(false));
    return p;
  }
  function embersToFile(btn) {
    const file = document.createElement('span'); file.className = 'fx-file'; file.setAttribute('aria-hidden', 'true'); btn.append(file);
    for (let k = 0; k < 7; k += 1) {
      const s = document.createElement('span'); s.className = 'fx-spark'; s.setAttribute('aria-hidden', 'true');
      s.style.setProperty('--x0', `${20 + Math.random() * 50}%`); s.style.setProperty('--d', `${k * 70}ms`); btn.append(s);
    }
    setTimeout(() => btn.querySelectorAll('.fx-file,.fx-spark').forEach((e) => e.remove()), 1500);
  }

  // ---------------------------------------------------------------- playback: 25 years in 25 seconds, the fuse scrubber
  let playing = false; let playTimer = 0; let full = 0;
  function seriesChanged() {
    const scrub = $('#scrub'); if (!scrub || !state.series) return;
    scrub.max = String(state.series.m.length - 1);
    renderEyes(); renderFingerprint(); syncScrub();
  }
  function syncScrub() {
    const scrub = $('#scrub'); if (!scrub || !state.series || state.sel == null) return;
    scrub.value = String(state.sel);
    scrub.style.setProperty('--p', `${(state.sel / Math.max(1, state.series.m.length - 1)) * 100}%`);
    scrub.setAttribute('aria-valuetext', api.label(state.sel));
    $('#play-label').textContent = `${api.label(state.sel)} · ${api.fmt(state.series.m[state.sel])} ${api.unit().many}`;
    drawStrip();
  }
  function drawStrip() {
    const cv = $('#fuse-strip'); if (!cv || !state.series) return;
    const r = cv.getBoundingClientRect(); if (!r.width) return;
    const d = window.devicePixelRatio || 1; cv.width = r.width * d; cv.height = r.height * d;
    const ctx = cv.getContext('2d'); ctx.setTransform(d, 0, 0, d, 0, 0);
    const m = state.series.m; const n = m.length; const max = Math.max(1, ...m); const bw = r.width / n;
    for (let j = 0; j < n; j += 1) {
      const v = m[j]; if (v < api.QUIET) continue; const h = Math.max(1, (r.height - 2) * Math.sqrt(v / max));
      ctx.fillStyle = j <= state.sel ? api.countColor(v, max) : '#3b322d';
      ctx.fillRect(j * bw, r.height - h, Math.max(1, bw - 0.4), h);
    }
  }
  function lightSelect(j) {
    if (j < 0 || api.flagAt(j) === 'X') return false;
    state.sel = j; state.focus = j;
    const grid = $('#cal-grid');
    grid.querySelectorAll('.cal-cell.sel').forEach((c) => { c.classList.remove('sel'); c.setAttribute('aria-selected', 'false'); c.tabIndex = -1; });
    const cell = grid.querySelector(`[data-j="${j}"]`); if (cell) { cell.classList.add('sel'); cell.setAttribute('aria-selected', 'true'); cell.tabIndex = 0; }
    if (state.view === 'rings') renderRings();
    api.renderMapValues({ fast: true }); api.renderMonth(); syncScrub();
    crackle(Math.sqrt(state.series.m[j] / Math.max(1, ...state.series.m)));
    return true;
  }
  function play() {
    if (!state.series || playing) return;
    const n = state.series.m.length; let j = state.sel >= n - 1 ? 0 : state.sel + 1;
    playing = true; full = 0; $('#play').setAttribute('aria-pressed', 'true'); $('#play').setAttribute('aria-label', 'Pause'); $('#play').classList.add('on');
    const every = motion() ? 80 : 350; // still mode: under 3 changes a second
    const tick = () => {
      if (!playing) return;
      while (j < n && !lightSelect(j)) j += 1;
      j += 1;
      if (j >= n) { pause(); return; }
      playTimer = setTimeout(tick, every);
    };
    tick();
  }
  function pause() {
    if (!playing) return;
    playing = false; clearTimeout(playTimer); quiet();
    $('#play').setAttribute('aria-pressed', 'false'); $('#play').setAttribute('aria-label', 'Play every year of the record'); $('#play').classList.remove('on');
    api.selectMonth(state.sel);
  }
  function bindPlayback() {
    $('#play').addEventListener('click', () => (playing ? pause() : play()));
    const scrub = $('#scrub');
    scrub.addEventListener('input', () => {
      if (playing) { playing = false; clearTimeout(playTimer); $('#play').setAttribute('aria-pressed', 'false'); $('#play').classList.remove('on'); }
      lightSelect(Number(scrub.value)); clearTimeout(full); full = setTimeout(() => api.selectMonth(state.sel), 350);
    });
    scrub.addEventListener('keydown', (e) => { if (e.key === ' ') { e.preventDefault(); if (playing) pause(); else play(); } });
    window.addEventListener('resize', drawStrip);
  }

  // ---------------------------------------------------------------- story mode: the record's biggest months
  let story = null;
  function pickScenes() {
    const s = state.series; const cand = [];
    for (let j = 0; j < s.m.length; j += 1) {
      if (api.flagAt(j) === 'X') continue;
      const { year, moy } = api.monthOf(j); const b = api.baseline(year, moy, 'harmonized'); const v = api.asCount(s.m[j]);
      cand.push({ j, v, b, ratio: b.enough && b.median >= api.FEW_FIRES ? v / b.median : NaN });
    }
    if (!cand.length) return [];
    const biggest = cand.reduce((a, b) => (b.v > a.v ? b : a));
    if (biggest.v < api.FEW_FIRES) return [];
    const scenes = [biggest];
    for (const c of cand.filter((x) => Number.isFinite(x.ratio) && x.ratio >= 1.5 && x.j !== biggest.j).sort((a, b) => b.ratio - a.ratio)) {
      if (scenes.length >= 4) break;
      if (scenes.every((x) => Math.abs(x.j - c.j) > 3)) scenes.push(c);
    }
    const monthMed = []; for (let moy = 1; moy <= 12; moy += 1) monthMed.push(api.quantile(cand.filter((c) => api.monthOf(c.j).moy === moy).map((c) => c.v).sort((a, b) => a - b), 0.5));
    const peakMed = Math.max(...monthMed);
    return scenes.sort((a, b) => a.j - b.j).map((c) => {
      const { moy } = api.monthOf(c.j); const mn = api.MONTH_NAMES[moy - 1];
      const x = (r) => (r >= 10 ? Math.round(r) : r.toFixed(1));
      const lines = [];
      if (c === biggest) lines.push(`The biggest month in this area’s whole record.`);
      if (Number.isFinite(c.ratio)) lines.push(`${x(c.ratio)}× a normal ${mn} here (median ${api.fmt(c.b.median)}, ${c.b.first}–${c.b.last}).`);
      else lines.push(`Too few earlier years (${c.b.years}) for a normal ${mn} to compare with.`);
      if (monthMed[moy - 1] < 0.25 * peakMed) lines.push(`Fire in a month that is usually quiet here.`);
      return { ...c, text: lines.join(' ') };
    });
  }
  function storyStart() {
    if (!state.series) return;
    pause();
    const scenes = pickScenes();
    if (!scenes.length) { api.toast('Too few fires in this area for a story.'); return; }
    story = { scenes, k: 0 };
    $('#story-card').hidden = false; storyShow();
  }
  function storyShow() {
    const card = $('#story-card'); const { scenes, k } = story;
    if (k >= scenes.length) {
      $('#story-step').textContent = 'Your turn';
      $('#story-title').textContent = 'Explore it yourself';
      $('#story-num').textContent = '';
      $('#story-text').textContent = 'Pick any month in the calendar, draw your own area on the map, or press play to watch every year of the record.';
      $('#story-next').textContent = 'Explore';
      $('#story-next').focus(); return;
    }
    const c = scenes[k];
    api.selectMonth(c.j);
    flyToFires(c.j);
    $('#story-step').textContent = `Story ${k + 1} of ${scenes.length}`;
    $('#story-title').textContent = api.label(c.j);
    $('#story-num').innerHTML = `<strong>${api.fmt(state.series.m[c.j])}</strong> ${api.unit().many}`;
    $('#story-text').textContent = c.text;
    $('#story-next').textContent = k === scenes.length - 1 ? 'Finish' : 'Next';
    card.classList.remove('in'); void card.offsetWidth; card.classList.add('in');
    $('#story-next').focus();
    crackle(Math.sqrt(state.series.m[c.j] / Math.max(1, ...state.series.m))); setTimeout(quiet, 1800);
  }
  function flyToFires(j) {
    if (!map) return;
    const mon = state.monthly; const deg = mon.cell_deg; const cells = state.areaCells.length ? state.areaCells : mon.cells.ix.map((_, c) => c);
    const vals = cells.map((c) => mon.m[c][j]); const top = Math.max(...vals);
    if (!(top > 0)) return;
    let x0 = Infinity; let y0 = Infinity; let x1 = -Infinity; let y1 = -Infinity;
    cells.forEach((c, k) => { if (vals[k] >= 0.3 * top) { const x = mon.cells.ix[c] * deg; const y = mon.cells.iy[c] * deg; x0 = Math.min(x0, x); y0 = Math.min(y0, y); x1 = Math.max(x1, x + deg); y1 = Math.max(y1, y + deg); } });
    map.fitBounds([[x0 - deg, y0 - deg], [x1 + deg, y1 + deg]], { padding: 70, duration: motion() ? 1400 : 0, maxZoom: 8 });
  }
  function storyEnd() { story = null; $('#story-card').hidden = true; quiet(); $('#story-go').focus(); }
  function bindStory() {
    $('#story-go').addEventListener('click', storyStart);
    $('#story-next').addEventListener('click', () => { if (!story) return; story.k += 1; if (story.k > story.scenes.length) storyEnd(); else storyShow(); });
    $('#story-exit').addEventListener('click', storyEnd);
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && story) storyEnd(); });
  }

  // ---------------------------------------------------------------- shareable card (an image of the area's fire)
  function shareCard() {
    if (!state.series) return false;
    if (Math.max(...state.series.m) < api.QUIET) { api.toast('Too few fires in this area for a fingerprint card.'); return false; }
    const W = 1200; const H = 630; const cv = document.createElement('canvas'); cv.width = W; cv.height = H; const ctx = cv.getContext('2d');
    const bg = ctx.createRadialGradient(900, 120, 50, 900, 120, 900); bg.addColorStop(0, '#2c140a'); bg.addColorStop(1, '#090706');
    ctx.fillStyle = bg; ctx.fillRect(0, 0, W, H);
    ctx.fillStyle = '#f0812b'; ctx.font = '700 18px Arial'; ctx.fillText('FIRE FINGERPRINT', 60, 70);
    ctx.fillStyle = '#fff3e4'; ctx.font = '700 40px Arial'; ctx.fillText(api.areaName().slice(0, 48), 60, 118);
    const { med, cur, year, partial } = fingerprintData(); const max = Math.max(1e-9, ...med, ...cur.map((v) => v ?? 0));
    const cx = 270; const cy = 360; const R = 190;
    ctx.strokeStyle = '#2f2622'; ctx.lineWidth = 1; [R, R / 2].forEach((r) => { ctx.beginPath(); ctx.arc(cx, cy, r, 0, 2 * Math.PI); ctx.stroke(); });
    const poly = (vals) => { const p = new Path2D(petal(vals, max, cx, cy, R)); return p; };
    ctx.shadowColor = '#ff8a2a'; ctx.shadowBlur = 24; ctx.fillStyle = 'rgba(240,129,43,0.6)'; ctx.fill(poly(cur)); ctx.shadowBlur = 0;
    ctx.strokeStyle = '#ffc35a'; ctx.lineWidth = 2.5; ctx.stroke(poly(cur));
    ctx.setLineDash([6, 6]); ctx.strokeStyle = '#e6ddd6'; ctx.lineWidth = 2; ctx.stroke(poly(med)); ctx.setLineDash([]);
    ctx.fillStyle = '#a8998e'; ctx.font = '600 15px Arial'; ctx.textAlign = 'center';
    ['Jan', 'Apr', 'Jul', 'Oct'].forEach((t, k) => { const a = (k / 4) * 2 * Math.PI; ctx.fillText(t, cx + (R + 22) * Math.sin(a), cy - (R + 22) * Math.cos(a) + 5); });
    ctx.textAlign = 'left';
    // the calendar quilt
    const ys = api.years(); const qx = 560; const qy = 170; const cw = 22; const ch = 15; const vmax = Math.max(1, ...state.series.m);
    ys.forEach((y, k) => { for (let moy = 1; moy <= 12; moy += 1) { const j = api.indexOf(y, moy); if (j < 0 || api.flagAt(j) === 'X') continue; const v = state.series.m[j];
      ctx.fillStyle = v < api.QUIET ? '#13202a' : api.countColor(v, vmax); ctx.fillRect(qx + (moy - 1) * cw, qy + k * ch, cw - 2, ch - 2); } });
    ctx.fillStyle = '#a8998e'; ctx.font = '13px Arial'; ctx.fillText(String(ys[0]), qx - 44, qy + 11); ctx.fillText(String(ys.at(-1)), qx - 44, qy + (ys.length - 1) * ch + 11);
    ['J', 'F', 'M', 'A', 'M', 'J', 'J', 'A', 'S', 'O', 'N', 'D'].forEach((t, m) => ctx.fillText(t, qx + m * cw + 6, qy - 8));
    const big = state.series.m.reduce((b, v, j) => (v > state.series.m[b] ? j : b), 0);
    const peak = med.indexOf(Math.max(...med));
    ctx.fillStyle = '#fff3e4'; ctx.font = '700 22px Arial';
    ctx.fillText(`Normal peak: ${api.MONTH_NAMES[peak]}`, 860, 210);
    ctx.fillText(`Record month: ${api.label(big)}`, 860, 250);
    ctx.fillStyle = '#ffc35a'; ctx.font = '700 46px Arial'; ctx.fillText(api.fmt(state.series.m[big]), 860, 312);
    ctx.fillStyle = '#a8998e'; ctx.font = '17px Arial'; ctx.fillText(`${api.unit().many}, MODIS-equivalent`, 860, 340);
    ctx.fillText(`Filled shape: ${year}${partial ? ' (months recorded so far)' : ''}. Dashed: a normal year.`, 860, 390);
    ctx.fillStyle = '#7d7068'; ctx.font = '15px Arial';
    ctx.fillText(`One harmonized MODIS–VIIRS fire record, ${api.label(0)} – ${api.label(state.series.m.length - 1)} · data: NASA FIRMS · CEDRUS`, 60, 600);
    cv.toBlob((blob) => {
      const url = URL.createObjectURL(blob); const a = document.createElement('a'); a.href = url;
      a.download = `cedrus_${state.meta.id}_${state.area.kind}_fire_fingerprint.png`; document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 2000);
    }, 'image/png');
    return true;
  }

  // ---------------------------------------------------------------- sound: a soft crackle, off by default
  let actx = null; let bed = null; let popBuf = null;
  function audio() {
    if (actx) return actx;
    actx = new (window.AudioContext || window.webkitAudioContext)();
    const len = 2 * actx.sampleRate; const buf = actx.createBuffer(1, len, actx.sampleRate); const d = buf.getChannelData(0); let b = 0;
    for (let i = 0; i < len; i += 1) { b = (b + 0.02 * (Math.random() * 2 - 1)) / 1.02; d[i] = b * 3.2; } // brown noise: a low, soft bed
    const src = actx.createBufferSource(); src.buffer = buf; src.loop = true;
    const lp = actx.createBiquadFilter(); lp.type = 'lowpass'; lp.frequency.value = 700;
    bed = actx.createGain(); bed.gain.value = 0; src.connect(lp).connect(bed).connect(actx.destination); src.start();
    const pl = Math.round(0.03 * actx.sampleRate); popBuf = actx.createBuffer(1, pl, actx.sampleRate); const pd = popBuf.getChannelData(0);
    for (let i = 0; i < pl; i += 1) pd[i] = (Math.random() * 2 - 1) * Math.exp(-i / (pl / 6));
    return actx;
  }
  function crackle(level) {
    if (!sound || !actx || !(level > 0)) return;
    const now = actx.currentTime; bed.gain.setTargetAtTime(0.045 * level, now, 0.2);
    const n = Math.round(level * 5);
    for (let k = 0; k < n; k += 1) {
      const t = now + Math.random() * 0.08; const s = actx.createBufferSource(); s.buffer = popBuf;
      const f = actx.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 1800 + Math.random() * 900;
      const g = actx.createGain(); g.gain.value = 0.05 * level * (0.4 + Math.random() * 0.6);
      s.connect(f).connect(g).connect(actx.destination); s.start(t);
    }
  }
  function quiet() { if (actx && bed) bed.gain.setTargetAtTime(0, actx.currentTime, 0.25); }

  // ---------------------------------------------------------------- the match-stick toggles: effects, sound
  function syncToggles() {
    const e = $('#fx-effects'); const s = $('#fx-sound');
    e.setAttribute('aria-checked', String(motion())); e.disabled = reduce.matches;
    s.setAttribute('aria-checked', String(sound));
    $('#fx-hint').textContent = reduce.matches ? 'Your device asks for reduced motion, so every effect is a still image.'
      : `${motion() ? 'Effects on: embers ignite, buttons burn, the calendar lights up.' : 'Effects off: every effect is a still image.'} Sound plays only during playback and stories.`;
    document.documentElement.classList.toggle('fx-still', !motion());
  }
  function bindToggles() {
    $('#fx-effects').addEventListener('click', () => {
      effects = !effects; try { localStorage.setItem('cedrus.effects', effects ? 'on' : 'off'); } catch { /* this page only */ }
      if (!motion()) { cancelAnimationFrame(igniteRaf); cancelAnimationFrame(rimRaf); if (map?.getLayer('ember-core')) { paintAt(1e3, 0.6, 0.9); map.setPaintProperty('rim', 'line-opacity', 0); } drawing(null); }
      syncToggles();
    });
    $('#fx-sound').addEventListener('click', () => {
      sound = !sound;
      if (sound) { try { audio().resume(); } catch { sound = false; api.toast('Sound is not available in this browser.'); } } else quiet();
      syncToggles();
    });
    reduce.addEventListener?.('change', syncToggles);
    syncToggles();
  }

  // First visit: one line pointing at where to start, gone after the first real interaction.
  function startHint() {
    const el = $('#start-hint'); if (!el) return;
    let seen = false; try { seen = localStorage.getItem('cedrus.started') === '1'; } catch { /* show it */ }
    if (seen || window.__uxOpen) return;
    el.hidden = false;
    const done = () => { el.hidden = true; try { localStorage.setItem('cedrus.started', '1'); } catch { /* this page only */ } };
    ['#region', '#draw-rectangle', '#draw-polygon', '#cal-grid', '#map'].forEach((s) => $(s)?.addEventListener('pointerdown', done, { once: true }));
    $('#region')?.addEventListener('change', done, { once: true });
  }
  function init() {
    startHint();
    bindCalendar(); bindRings(); bindPlayback(); bindStory(); bindToggles(); eyesPixels();
    $('#translate').addEventListener('click', () => { translated = !translated; $('#translate').setAttribute('aria-checked', String(translated)); renderEyes(true); });
    document.querySelectorAll('#map-dn button').forEach((b) => b.addEventListener('click', () => setDayNight(b.dataset.dn)));
    $('#share-card').addEventListener('click', () => burn($('#share-card'), shareCard));
  }

  function stop() { if (!playing) return; playing = false; clearTimeout(playTimer); quiet(); $('#play').setAttribute('aria-pressed', 'false'); $('#play').setAttribute('aria-label', 'Play every year of the record'); $('#play').classList.remove('on'); }
  return { init, stop, motion, afterCalendar, renderRings, mapReady, mapMonth, areaChanged, drawing, ghostFlame, smokeClass, burn, seriesChanged, syncScrub, renderFingerprint, isPlaying: () => playing, pause };
}
