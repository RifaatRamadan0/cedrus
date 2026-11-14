// Right now vs normal (data/nrt.json, written daily by tools/nrt_snapshot.py): NOAA-20's last complete days for the
// region on screen, against the same calendar days in 2019-2025. Small counts are placed in the usual range, never
// turned into percentages. Loaded after the calendar, so the first view waits for nothing extra.
const $ = (s) => document.querySelector(s);
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const FEW = 5; // as the app: a normal under 5 is too few to judge
let data = null; let shownFor = null; let onMap = false;

const d = (iso) => `${Number(iso.slice(8, 10))} ${MONTHS[Number(iso.slice(5, 7)) - 1]}`;
function verdict(r) {
  if (r.median == null) return { key: 'none', text: 'its normal for these days is not built yet' };
  if (r.median < FEW && r.now < FEW) return { key: 'few', text: 'few fires, as usual for these days' };
  if (r.now > r.high) return { key: 'hot', text: `more than on these days in any year since ${Object.keys(r.years)[0]}` };
  if (r.now > r.q3) return { key: 'hot', text: 'busier than usual for these days' };
  if (r.now < r.q1) return { key: 'cool', text: 'quieter than usual for these days' };
  return { key: 'normal', text: 'within the usual range for these days' };
}
function bars(r) {
  const ys = Object.entries(r.years); const max = Math.max(r.now, ...ys.map(([, v]) => v), 1);
  const h = (v) => Math.max(2, Math.round(30 * Math.sqrt(v / max)));
  return `<span class="live-bars" aria-hidden="true">${ys.map(([y, v]) => `<i title="${y}: ${v}" style="height:${h(v)}px"></i>`).join('')}<b style="height:${h(r.now)}px"></b></span>`;
}
function render() {
  const s = window.cedrus?.state; const box = $('#live'); if (!s?.meta || !box || !data) return;
  const id = s.meta.id; if (id === shownFor) return; shownFor = id;
  const r = data.regions[id];
  if (!r) { box.hidden = false; box.className = 'live none'; box.innerHTML = `<span class="live-dot" aria-hidden="true"></span><p><strong>Right now</strong> · ${s.meta.name}: the live comparison isn’t built for this region yet.</p>`; mapLayer(); return; }
  const v = verdict(r); const win = `${d(data.window[0])}–${d(data.window[1])} ${data.window[1].slice(0, 4)}`;
  box.hidden = false; box.className = `live ${v.key}`;
  box.innerHTML = `<span class="live-dot" aria-hidden="true"></span>
    <p><strong>Right now</strong> · ${s.meta.name}, ${win} (${data.days} complete days): <strong class="live-n">${r.now}</strong> burning days seen by NOAA-20, <strong>${v.text}</strong>${r.median != null ? ` (normal ${fmt(r.median)}, usual range ${fmt(r.q1)}–${fmt(r.q3)}, same days ${Object.keys(r.years)[0]}–${Object.keys(r.years).at(-1)})` : ''}.
    <span class="live-note">${stale()}Live NASA FIRMS feed, built ${data.built.replace('T', ' ')} UTC and updated daily; like-for-like NOAA-20 counts, not the harmonized record.</span></p>
    ${r.median != null ? bars(r) : ''}<button type="button" class="map-lens" id="live-map" aria-pressed="${onMap}">${onMap ? 'Hide' : 'Show'} on map</button>`;
  $('#live-map').addEventListener('click', () => { onMap = !onMap; shownFor = null; render(); mapLayer(); });
  mapLayer();
}
// A snapshot older than two days says so: a failed daily job must never pass for "right now".
function stale() {
  const age = (Date.now() - Date.parse(data.built.replace('Z', ':00Z'))) / 864e5;
  return age > 2 ? `<strong class="live-stale">This snapshot is ${Math.floor(age)} days old. </strong>` : '';
}
function fmt(v) { return Number.isInteger(v) ? String(v) : v.toFixed(1); }
function mapLayer() {
  const map = window.cedrus?.state?.map; if (!map) return;
  // isStyleLoaded() is false while tiles load; wait for the map to settle instead of giving up
  if (!map.getSource('cells')) { map.once('idle', mapLayer); return; }
  const id = window.cedrus.state.meta?.id; const r = data?.regions?.[id];
  const fc = { type: 'FeatureCollection', features: onMap && r ? r.points.map(([x, y, n]) => ({ type: 'Feature', properties: { n }, geometry: { type: 'Point', coordinates: [x, y] } })) : [] };
  if (!map.getSource('live')) {
    map.addSource('live', { type: 'geojson', data: fc });
    map.addLayer({ id: 'live-halo', type: 'circle', source: 'live', paint: { 'circle-radius': ['+', 9, ['*', 3, ['sqrt', ['get', 'n']]]], 'circle-color': '#ffffff', 'circle-opacity': 0.18, 'circle-blur': 1 } });
    map.addLayer({ id: 'live-dot', type: 'circle', source: 'live', paint: { 'circle-radius': ['+', 3, ['sqrt', ['get', 'n']]], 'circle-color': '#fff7e0', 'circle-stroke-color': '#ff9a3c', 'circle-stroke-width': 1.5 } });
  } else map.getSource('live').setData(fc);
  if (onMap && r?.points.length) { // bring the live fires into view
    const xs = r.points.map((p) => p[0]); const ys = r.points.map((p) => p[1]);
    map.fitBounds([[Math.min(...xs) - 0.4, Math.min(...ys) - 0.4], [Math.max(...xs) + 0.4, Math.max(...ys) + 0.4]], { padding: 60, maxZoom: 8, duration: 800 });
  }
}
async function start() {
  try { await window.cedrus?.ready; } catch { return; }
  try { const r = await fetch('data/nrt.json'); if (!r.ok) return; data = await r.json(); } catch { return; }
  render(); setInterval(() => { if (window.cedrus?.state?.meta?.id !== shownFor) render(); }, 600);
}
const wait = setInterval(() => { if (window.cedrus) { clearInterval(wait); start(); } }, 200);
