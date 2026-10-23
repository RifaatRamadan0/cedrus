'use strict';
// CEDRUS front end. Reads what pipeline/04_export_web.py writes into web/data/.
// No build step: serve the web/ folder with any static server.

const $ = (selector) => document.querySelector(selector);
const fmt = (n) => Math.round(n).toLocaleString('en-US');
const pct = (x) => `${(x * 100).toFixed(1)}%`;
const COLORS = ['#529b6e', '#f3d363', '#ffa846', '#ff7146', '#f4434b'];

const state = { region: 'portugal', data: null, cells: null, startYear: 2001, map: null, breaks: [] };
let toastTimer;

function toast(message) {
  $('.toast').textContent = message; $('.toast').classList.add('visible');
  clearTimeout(toastTimer); toastTimer = setTimeout(() => $('.toast').classList.remove('visible'), 4200);
}

async function loadRegion(region) {
  const get = (path) => fetch(path).then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); });
  const [data, cells] = await Promise.all([get(`data/${region}.json`), get(`data/${region}-cells.geojson`)]);
  state.data = data; state.cells = cells;
  const years = data.record.years;
  $('#time-range').innerHTML = [years[0], 2005, 2010, 2015, 2020]
    .filter((y) => y >= years[0] && y < years.at(-1))
    .map((y) => `<option value="${y}">${y} – ${years.at(-1)}</option>`).join('');
  state.startYear = years[0];
  $('#data-badge').textContent = data.test.passed ? 'TEST PASSED' : 'TEST FAILED';
  renderAll();
}

// ---------- chart ----------
function renderChart() {
  const { record, region } = state.data;
  const from = record.years.indexOf(state.startYear);
  const years = record.years.slice(from);
  const combined = record.combined.slice(from);
  const corrected = record.corrected.slice(from);
  const modis = record.modis.slice(from).map((v, i) => (years[i] >= 2012 ? v : null));
  const max = Math.max(...combined, ...corrected) * 1.08;
  const step = niceStep(max / 4);
  const top = step * Math.ceil(max / step);
  const x0 = 63, y0 = 164, width = 354, height = 145;
  const X = (i) => x0 + (i / Math.max(1, years.length - 1)) * width;
  const Y = (v) => y0 - (v / top) * height;
  const line = (vals) => {
    let d = ''; let pen = false;
    vals.forEach((v, i) => {
      if (v == null) { pen = false; return; }
      d += `${pen ? 'L' : 'M'}${X(i).toFixed(1)},${Y(v).toFixed(1)} `; pen = true;
    });
    return d.trim();
  };
  let html = '';
  for (let v = 0; v <= top + 1e-9; v += step) {
    html += `<line class="chart-grid" x1="${x0}" y1="${Y(v)}" x2="${x0 + width}" y2="${Y(v)}"/><text class="chart-label" x="49" y="${Y(v) + 3}" text-anchor="end">${fmt(v)}</text>`;
  }
  years.forEach((y, i) => {
    if (i === 0 || i === years.length - 1 || (y % 5 === 0 && i > 1 && i < years.length - 2)) {
      html += `<text class="chart-label" x="${X(i)}" y="181" text-anchor="middle">${y}</text>`;
    }
  });
  const correctedPath = line(corrected);
  html += `<text class="chart-label" transform="translate(10 107) rotate(-90)" text-anchor="middle">Fire detections / year</text>`
    + `<path d="${correctedPath} L${X(years.length - 1)},${y0} L${x0},${y0} Z" fill="url(#chart-fill)"/>`
    + `<path d="${line(modis)}" fill="none" stroke="#9fb2c2" stroke-width="1.2" stroke-dasharray="4 3"/>`
    + `<path d="${line(combined)}" fill="none" stroke="#ef6d70" stroke-width="2" stroke-linejoin="round"/>`
    + `<path d="${correctedPath}" fill="none" stroke="#7bc58f" stroke-width="2.2" stroke-linejoin="round"/>`;
  $('#chart-content').innerHTML = html;
  $('#chart-title').textContent = `${region} – Corrected vs. Combined Data`;
  const clone = $('#chart-container').cloneNode(true);
  clone.removeAttribute('id');
  clone.querySelectorAll('[id]').forEach((el) => { el.id = `expanded-${el.id}`; });
  clone.querySelector('[fill="url(#chart-fill)"]').setAttribute('fill', 'url(#expanded-chart-fill)');
  $('#large-chart').replaceChildren(clone);
}

function niceStep(raw) {
  const p = 10 ** Math.floor(Math.log10(raw || 1));
  return [1, 2, 2.5, 5, 10].map((m) => m * p).find((s) => s >= raw);
}

// ---------- calendar, comparison, explanation ----------
function renderPanels() {
  const { calendar, comparison, record, test, region } = state.data;
  for (const k of ['start', 'peak', 'end']) {
    $(`#cal-${k}`).textContent = calendar[k].label;
    $(`#cal-${k}-spread`).textContent = `± ${calendar[k].spread_days} days`;
  }
  $('#calendar-basis').textContent = calendar.basis.toUpperCase();
  $('#comparison-title').textContent = `Latest Full Year (${comparison.year})`;
  const shift = comparison.middle_shift_days;
  const when = shift === 0 ? 'on time' : `${Math.abs(shift)} days ${shift < 0 ? 'early' : 'late'}`;
  $('#comparison-text').innerHTML = `Fire activity was <strong>${comparison.status}</strong> the normal range `
    + `(${fmt(comparison.total)} vs ${fmt(comparison.normal_range[0])}–${fmt(comparison.normal_range[1])}).<br>Season middle ran ${when}.`;
  const icon = $('#comparison-icon');
  icon.classList.toggle('warn', comparison.status === 'above');
  icon.querySelector('use').setAttribute('href', comparison.status === 'within' ? '#check' : '#fire');

  const i = record.years.indexOf(2012);
  const ratio = i >= 0 && record.modis[i] ? record.viirs[i] / record.modis[i] : NaN;
  $('#explanation').textContent = Number.isFinite(ratio)
    ? `In 2012 the joined record switches from MODIS to VIIRS. That year VIIRS flagged ${ratio.toFixed(1)}× as many `
      + `fire pixels as MODIS, because it sees smaller fires. The corrected record converts VIIRS to MODIS-equivalent, `
      + `so the false jump disappears. Tested by pretending MODIS ended in 2019 and rebuilding 2020–2025, cell by cell, `
      + `month by month: error ${pct(test.primary_wape.M1)}, against ${pct(test.primary_wape.F0)} for the joined record `
      + `and ${pct(test.primary_wape.F1)} for a single ratio.`
    : 'Not enough data to show the 2012 switch.';
  $('#expanded-eyebrow').textContent = region.toUpperCase();
  $('#chart-disclaimer').textContent = 'Fire detections are satellite pixels flagged as burning, not burned area. Source: NASA FIRMS.';
  $('#map-caption').textContent = `${region} · mean corrected detections per year, ${state.startYear}–${record.years.at(-1)} · NASA FIRMS`;
}

// ---------- map ----------
function cellValues() {
  const years = state.cells.years;
  const from = years.indexOf(state.startYear);
  for (const f of state.cells.features) {
    const ys = f.properties.y.slice(from);
    f.properties.v = ys.reduce((a, b) => a + b, 0) / ys.length;
  }
  const nonzero = state.cells.features.map((f) => f.properties.v).filter((v) => v > 0.05).sort((a, b) => a - b);
  const q = (p) => nonzero[Math.min(nonzero.length - 1, Math.floor(p * nonzero.length))];
  state.breaks = [0.05, q(0.4), q(0.7), q(0.9)];
  document.querySelectorAll('[data-class]').forEach((el) => {
    const c = Number(el.dataset.class);
    el.textContent = c === 4 ? `> ${state.breaks[3].toFixed(0)}` : `${state.breaks[c - 1].toFixed(c === 1 ? 1 : 0)}–${state.breaks[c].toFixed(0)}`;
  });
}

function gibs(layer, level, ext) {
  return `https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/${layer}/default/GoogleMapsCompatible_Level${level}/{z}/{y}/{x}.${ext}`;
}

function colorExpr() {
  const b = state.breaks;
  return ['step', ['get', 'v'], COLORS[0], b[0], COLORS[1], b[1], COLORS[2], b[2], COLORS[3], b[3], COLORS[4]];
}

function initMap() {
  if (!window.maplibregl) { $('#map-caption').textContent = 'Map library failed to load (offline?). Chart and calendar still work.'; return; }
  const map = new maplibregl.Map({
    container: 'map', attributionControl: { compact: true },
    style: {
      version: 8,
      // NASA GIBS: keyless, and NASA's own imagery. Blue Marble is darkened so the fire cells stand out.
      sources: {
        marble: { type: 'raster', tileSize: 256, maxzoom: 8, tiles: [gibs('BlueMarble_ShadedRelief_Bathymetry', 8, 'jpeg')],
          attribution: 'Basemap: <a href="https://earthdata.nasa.gov/gibs">NASA GIBS</a> · Fire data: NASA FIRMS' },
      },
      layers: [
        { id: 'marble', type: 'raster', source: 'marble', paint: { 'raster-brightness-max': 0.6, 'raster-saturation': -0.4, 'raster-contrast': 0.1 } },
      ],
    },
    bounds: [[-9.8, 36.8], [-6.0, 42.3]], fitBoundsOptions: { padding: 12 },
  });
  map.addControl(new maplibregl.ScaleControl({ maxWidth: 80 }), 'bottom-right');
  map.once('style.load', () => { // not 'load', which waits for every basemap tile
    map.addSource('cells', { type: 'geojson', data: state.cells });
    map.addLayer({ id: 'cells', type: 'fill', source: 'cells', paint: { 'fill-color': colorExpr(), 'fill-opacity': ['case', ['<', ['get', 'v'], 0.05], 0.12, 0.72] } });
    map.addLayer({ id: 'cells-line', type: 'line', source: 'cells', paint: { 'line-color': '#08131d', 'line-width': 0.4 } });
    map.on('click', 'cells', (e) => {
      const p = e.features[0].properties;
      const ys = typeof p.y === 'string' ? JSON.parse(p.y) : p.y;
      const years = state.cells.years; const from = years.indexOf(state.startYear);
      const shown = ys.slice(from); const peak = shown.indexOf(Math.max(...shown));
      new maplibregl.Popup().setLngLat(e.lngLat)
        .setHTML(`<strong>${Number(p.v).toFixed(1)}</strong> corrected detections / year<br>${state.startYear}–${years.at(-1)}<br>Worst year: <strong>${years[from + peak]}</strong> (${fmt(shown[peak])})`).addTo(map);
    });
    map.on('mouseenter', 'cells', () => { map.getCanvas().style.cursor = 'pointer'; });
    map.on('mouseleave', 'cells', () => { map.getCanvas().style.cursor = ''; });
  });
  state.map = map;
}

function renderMap() {
  cellValues();
  const map = state.map;
  if (map && map.getSource('cells')) {
    map.getSource('cells').setData(state.cells);
    map.setPaintProperty('cells', 'fill-color', colorExpr());
  }
}

function renderAll() { renderChart(); renderPanels(); renderMap(); if (!state.map) initMap(); }

// ---------- controls ----------
$('#filter-form').addEventListener('submit', (event) => {
  event.preventDefault();
  if (!state.data) return;
  const search = $('#location-search').value.trim();
  if (search && !'portugal'.includes(search.toLowerCase())) { toast('Only Portugal is processed so far. More regions: run the pipeline with --country.'); $('#location-search').focus(); return; }
  state.startYear = Number($('#time-range').value);
  renderAll();
  toast(`Updated: ${state.data.region}, ${state.startYear}–${state.data.record.years.at(-1)}.`);
});
$('#location-search').addEventListener('input', (event) => {
  const query = event.target.value.trim().toLowerCase(); const result = $('#search-result'); result.hidden = !query;
  result.textContent = 'portugal'.includes(query) ? 'Portugal · available' : 'Only Portugal is processed so far.';
});
function setView(view) {
  const isMap = view === 'map'; $('#map-panel').hidden = !isMap; $('#expanded-chart').hidden = isMap;
  ['map', 'chart'].forEach((name) => { const b = $(`#${name}-tab`); b.classList.toggle('selected', view === name); b.setAttribute('aria-pressed', String(view === name)); });
  if (isMap && state.map) state.map.resize();
}
$('#map-tab').addEventListener('click', () => setView('map'));
$('#chart-tab').addEventListener('click', () => setView('chart'));
$('#zoom-in').addEventListener('click', () => state.map?.zoomIn());
$('#zoom-out').addEventListener('click', () => state.map?.zoomOut());

const video = $('.hero-video'); const videoToggle = $('.video-toggle');
function syncVideo() { videoToggle.textContent = video.paused ? '▶' : 'Ⅱ'; const label = video.paused ? 'Play background video' : 'Pause background video'; videoToggle.setAttribute('aria-label', label); videoToggle.title = label; }
videoToggle.addEventListener('click', () => { if (video.paused) { video.play().catch(() => toast('Use your browser’s video playback permission to play the background.')); } else { video.pause(); } });
video.addEventListener('play', syncVideo); video.addEventListener('pause', syncVideo);
if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) { video.autoplay = false; video.pause(); } else { video.play().catch(syncVideo); }
syncVideo();

// ---------- dialogs ----------
function methodologyHtml() {
  const d = state.data; if (!d) return '<p>Data not loaded yet.</p>';
  const t = d.test; const names = { F0: 'Joined record (floor)', F1: 'One ratio (floor)', M1: 'CEDRUS' };
  const rows = ['F0', 'F1', 'M1'].map((m) => `<tr><td>${names[m]}</td><td>${pct(t.primary_wape[m])}</td><td>${t.season_date_error_days[m]}</td></tr>`).join('');
  const h = t.handover_noaa20;
  return `<p><strong>Data.</strong> ${d.provenance.source}. Filters: ${d.provenance.filters}. Unit: ${d.provenance.unit}.</p>
    <p><strong>Method.</strong> ${d.provenance.method}.</p>
    <p><strong>The MODIS retirement test</strong> <span class="verdict ${t.passed ? 'pass' : 'fail'}">${t.passed ? 'PASS' : 'FAIL'}</span><br>
    Fitted on ${t.train[0]} to ${t.train[1]}, then asked to rebuild what MODIS saw in ${t.test[0]} to ${t.test[1]} from VIIRS alone. The rules were written before the test ran.</p>
    <table class="test-table"><tr><th>Method</th><th>Cell-month error</th><th>Season dates off (days)</th></tr>${rows}</table>
    ${h ? `<p><strong>Satellite handover.</strong> Same model fed NOAA-20 instead of Suomi NPP (${h.months[0]} to ${h.months[1]}): error ${pct(h.M1_on_noaa20)} vs ${pct(h.M1_on_snpp)}.</p>` : ''}
    <p><strong>Limits.</strong></p><ul>${d.limitations.map((l) => `<li>${l}</li>`).join('')}</ul>
    <p><strong>Files used</strong> (${d.provenance.files.length}), each with its SHA-256 in <code>data/${state.region}.json</code>:</p>
    <p class="files">${d.provenance.files.map((f) => f.name).join(' · ')}</p>`;
}
const dialogs = {
  methodology: { title: 'Data &amp; Methodology', body: methodologyHtml },
  about: { title: 'Roots in Nature.<br>Data for a Safer Tomorrow.', body: () => '<p>We are <strong>CEDRUS</strong>, joining the NASA Space Apps local event in Beirut.</p><p>Our challenge: <strong>Harmonization of MODIS and VIIRS Hot Spots.</strong> MODIS is being retired, and Suomi NPP stopped delivering data on 1 November 2026. We build one fire record that survives the handover, test it honestly, and turn it into a fire calendar.</p>' },
  comparison: { title: 'Latest Year Comparison', body: () => {
    const c = state.data?.comparison; if (!c) return '<p>Data not loaded yet.</p>';
    const s = c.middle_shift_days;
    return `<p><strong>${state.data.region} · ${c.year}</strong></p><p>Corrected detections: <strong>${fmt(c.total)}</strong>. Normal range (10th–90th percentile of earlier years): ${fmt(c.normal_range[0])}–${fmt(c.normal_range[1])}.</p>`
      + `<p>The season middle (the day half the year's detections had been reached) was ${s === 0 ? 'on the usual day' : `${Math.abs(s)} days ${s < 0 ? 'earlier' : 'later'} than in the median year`}.</p>`;
  } },
};
document.querySelectorAll('[data-dialog]').forEach((button) => button.addEventListener('click', () => {
  const item = dialogs[button.dataset.dialog]; $('#dialog-title').innerHTML = item.title; $('#dialog-body').innerHTML = item.body(); $('#detail-dialog').showModal();
}));
$('.dialog-close').addEventListener('click', () => $('#detail-dialog').close()); $('.dialog-done').addEventListener('click', () => $('#detail-dialog').close());
$('#detail-dialog').addEventListener('click', (event) => { if (event.target === $('#detail-dialog')) { const r = event.target.getBoundingClientRect(); if (event.clientX < r.left || event.clientX > r.right || event.clientY < r.top || event.clientY > r.bottom) event.target.close(); } });
document.querySelectorAll('nav a').forEach((link) => link.addEventListener('click', () => { document.querySelectorAll('nav a').forEach((item) => { item.classList.toggle('active', item === link); if (item === link) item.setAttribute('aria-current', 'page'); else item.removeAttribute('aria-current'); }); }));

loadRegion(state.region).catch((err) => {
  $('#data-badge').textContent = 'NO DATA';
  $('#map-caption').textContent = `Could not load data/${state.region}.json (${err.message}). Run the pipeline, and serve web/ over http rather than opening the file directly.`;
});
