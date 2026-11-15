// CEDRUS shell: the story deck (Yasmina's design) in front of the app. It never changes the record; every number
// it writes into the story is computed here from data/regions.json and data/lebanon/*.json, read only
// after the calendar has rendered (the cold load waits for the calendar files alone).
import { EMBER } from './fx.js';

const $ = (s) => document.querySelector(s);
// this module's ?v, passed on to the modules it loads later, so a browser never mixes old and new files
const V = new URL(import.meta.url).search;
const tr = (en) => window.cedrusI18n?.tr?.(en) || en;
const langNow = () => window.cedrusI18n?.lang?.() || 'en';
const html = document.documentElement;
const deck = $('#deck');
const shots = [...document.querySelectorAll('.deck .shot')];
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const MONL = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
const n0 = (v) => Math.round(v).toLocaleString('en-US');
const ymText = (ym, long) => { const [y, m] = ym.split('-').map(Number); return `${(long ? MONL : MON)[m - 1]} ${y}`; };

// ---------- deck or stacked ----------
// Wide screens: one full-screen slide at a time (arrow keys, wheel, the rail). Narrow or short screens: the slides
// are ordinary sections you scroll through. Either way the explorer, the exams, Method and About follow as a page.
const deckMQ = matchMedia('(min-width: 861px) and (min-height: 600px)');
let deckMode = deckMQ.matches;
let cur = 0; let lock = false;
window.__slide = 0;
const stageOf = (n) => Number(shots[n]?.dataset.stage ?? n);

const ruler = $('#ruler');
ruler.innerHTML = shots.map((s, j) => `<button type="button" aria-label="Slide ${j + 1}: ${s.dataset.name}"></button>`).join('');
const rulerBtns = [...ruler.children];
function hud() {
  $('#hudNum').textContent = String(cur + 1).padStart(2, '0');
  $('#hudTot').textContent = String(shots.length).padStart(2, '0');
  $('#hudName').textContent = shots[cur].dataset.name;
  html.classList.toggle('on-first', stageOf(cur) === 0);
  rulerBtns.forEach((b, j) => { b.classList.toggle('on', j === cur); if (j === cur) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current'); });
  $('#prevBtn').disabled = cur === 0;
  $('#nextBtn').disabled = false; // past the last slide, "next" opens the explorer
}
function activate(n) {
  const s = shots[n]; const fastP = s.querySelector('.typed-para.fast'); if (fastP) typeFast(fastP); if (s.id === 'orbit') setTimeout(typeOrbit, reduce ? 0 : 500); if (s.id !== 'orbit') leaveTour(); s.classList.add('active'); s.scrollTop = 0; s.removeAttribute('inert');
  void s.offsetWidth; s.classList.add('in'); // a style flush between the two, so the reveal transitions run
}
function setDeckMode(on) {
  deckMode = on; html.classList.toggle('deck-mode', on);
  shots.forEach((s, j) => {
    s.classList.toggle('active', !on || j === cur); s.classList.remove('leaving');
    s.classList.toggle('in', !on || j === cur);
    if (on && j !== cur) s.setAttribute('inert', ''); else s.removeAttribute('inert');
  });
  hud();
}
function go(n, { instant = false } = {}) {
  n = Math.max(0, Math.min(shots.length - 1, n));
  if (!deckMode) { shots[n].scrollIntoView({ behavior: reduce || instant ? 'auto' : 'smooth' }); return; }
  if (n === cur || lock) return;
  lock = true; const prev = shots[cur]; cur = n; window.__slide = stageOf(n); hud();
  const dur = (!instant && window.__flyTo && stageOf(n) !== stageOf(shots.indexOf(prev)) && window.__flyTo(stageOf(n))) || 0;
  if (instant) window.__cut && window.__cut();
  prev.classList.add('leaving'); prev.classList.remove('active'); prev.setAttribute('inert', '');
  const enterAt = reduce || instant ? 0 : Math.max(450, dur * 0.55);
  setTimeout(() => { prev.classList.remove('leaving', 'in'); activate(n); }, enterAt);
  setTimeout(() => { lock = false; }, reduce || instant ? 50 : Math.max(700, dur * 0.8));
  try { history.replaceState(null, '', `#${shots[n].id}`); } catch { /* file:// */ }
}
const sections = { home: deck, explore: $('#explore'), proof: $('#proof'), method: $('#method'), about: $('#about') };
function toPage(key) {
  const el = sections[key]; if (!el) return;
  el.scrollIntoView({ behavior: reduce ? 'auto' : 'smooth', block: 'start' });
  try { history.replaceState(null, '', `#${key === 'home' ? 'home' : el.id}`); } catch { /* file:// */ }
}
function nextFromLast() { toPage('explore'); }

document.querySelectorAll('[data-go]').forEach((a) => a.addEventListener('click', (e) => {
  const key = a.dataset.go; e.preventDefault();
  if (key === 'home') { window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' }); if (deckMode) go(0); else shots[0].scrollIntoView(); return; }
  const k = shots.findIndex((s) => s.id === key);
  if (k >= 0) { if (deckMode) { window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' }); go(k); } else go(k); return; }
  toPage(key);
}));
rulerBtns.forEach((b, j) => b.addEventListener('click', () => go(j)));
$('#prevBtn').addEventListener('click', () => go(cur - 1));
$('#nextBtn').addEventListener('click', () => (cur === shots.length - 1 ? nextFromLast() : go(cur + 1)));

const atTop = () => window.scrollY < 2;
const typing = (e) => e.target.closest?.('input,select,textarea,[contenteditable],dialog,.page,[role=grid],[role=application]');
const dialogOpen = () => !!document.querySelector('dialog[open]');
function canScroll(el, dy) {
  for (let n = el; n && n !== deck && n !== document.body; n = n.parentElement) {
    const cs = getComputedStyle(n);
    if (/(auto|scroll)/.test(cs.overflowY) && n.scrollHeight > n.clientHeight + 2) {
      if (dy > 0 && n.scrollTop + n.clientHeight < n.scrollHeight - 2) return true;
      if (dy < 0 && n.scrollTop > 2) return true;
    }
  }
  return false;
}
function step(dir) {
  if (dir > 0) { if (cur === shots.length - 1) nextFromLast(); else go(cur + 1); } else go(cur - 1);
}
addEventListener('keydown', (e) => {
  if ((e.key === ' ' || e.key === 'Enter') && e.target.closest?.('button,a,summary')) return;
  if (!deckMode || !atTop() || dialogOpen() || typing(e) || e.metaKey || e.ctrlKey || e.altKey) return;
  if (['ArrowDown', 'ArrowRight', 'PageDown', ' '].includes(e.key)) { e.preventDefault(); step(1); }
  else if (['ArrowUp', 'ArrowLeft', 'PageUp'].includes(e.key)) { e.preventDefault(); step(-1); }
  else if (e.key === 'Home') { e.preventDefault(); go(0); }
});
let wAcc = 0; let wT = 0;
addEventListener('wheel', (e) => {
  if (!deckMode || !atTop() || dialogOpen() || !deck.contains(e.target)) return;
  if (canScroll(e.target, e.deltaY)) return;
  if (e.deltaY > 0 && cur === shots.length - 1) return; // the page scrolls on into the explorer
  if (e.deltaY < 0 && cur === 0) return;
  e.preventDefault();
  const now = performance.now(); if (now - wT > 260) wAcc = 0; wT = now; wAcc += e.deltaY;
  if (Math.abs(wAcc) > 60 && !lock) { step(wAcc > 0 ? 1 : -1); wAcc = 0; }
}, { passive: false });
let tY = null; let tX = null;
deck.addEventListener('touchstart', (e) => { tY = e.touches[0].clientY; tX = e.touches[0].clientX; }, { passive: true });
deck.addEventListener('touchend', (e) => {
  if (!deckMode || tY == null) return;
  const dy = tY - e.changedTouches[0].clientY; const dx = tX - e.changedTouches[0].clientX; tY = null;
  if (Math.abs(dy) > 60 && Math.abs(dy) > Math.abs(dx) * 1.3 && !canScroll(e.target, dy)) step(dy > 0 ? 1 : -1);
}, { passive: true });

// Stacked mode: the slide most in view drives the 3D camera.
const seen = new Map();
const io = new IntersectionObserver((entries) => {
  entries.forEach((en) => seen.set(en.target, en.intersectionRatio));
  if (deckMode) return;
  let best = cur; let br = -1; shots.forEach((s, j) => { const r = seen.get(s) ?? 0; if (r > br) { br = r; best = j; } });
  if (br > 0) { cur = best; window.__slide = stageOf(best); hud(); }
  if ((seen.get($('#orbit')) ?? 0) >= 0.5) typeOrbit();
  shots.forEach((sh) => { const p = sh.querySelector('.typed-para.fast'); if (!p) return; const r = seen.get(sh) ?? 0; if (r >= 0.5 && !p.dataset.inView) { p.dataset.inView = '1'; typeFast(p); } else if (r === 0) delete p.dataset.inView; });
}, { threshold: [0, 0.25, 0.5, 0.75, 1] });
shots.forEach((s) => io.observe(s));

// Past the story: the stage stops drawing, the bar turns solid, the nav follows the section in view.
const navLinks = [...document.querySelectorAll('.tb-nav a')];
function onScroll() {
  const past = deck.getBoundingClientRect().bottom < 90;
  html.classList.toggle('past-deck', past); window.__stageHidden = past;
  let key = 'home';
  for (const k of ['explore', 'proof', 'method', 'about']) { const el = k === 'proof' ? sections.proof.parentElement : sections[k]; if (el.getBoundingClientRect().top < window.innerHeight * 0.4) key = k; }
  navLinks.forEach((a) => { const on = a.dataset.go === key; a.classList.toggle('on', on); if (on) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
}
addEventListener('scroll', onScroll, { passive: true }); addEventListener('resize', onScroll);
deckMQ.addEventListener('change', (e) => { setDeckMode(e.matches); onScroll(); });

// Start: on the slide the link names, if any.
{
  const h = location.hash.slice(1); const k = h ? shots.findIndex((s) => s.id === h) : -1;
  if (k > 0) { cur = k; window.__slide = stageOf(k); }
  setDeckMode(deckMode);
  if (k > 0 && !deckMode) shots[k].scrollIntoView();
  onScroll();
}

// ---------- the satellite card (published mission facts) ----------
const SATINFO = [
  { name: 'Terra', inst: 'MODIS · 1 km fire pixels', alt: 705, vel: '7.50', per: '98.8', orb: 'Polar SSO', launch: '18 Dec 1999', cross: '10:30 am', swath: '2,330 km', note: 'Morning satellite. It no longer keeps its orbit, so its crossing time drifts; the record treats MODIS from 2022 as estimated from VIIRS.' },
  { name: 'Aqua', inst: 'MODIS · 1 km fire pixels', alt: 705, vel: '7.50', per: '98.8', orb: 'Polar SSO', launch: '4 May 2002', cross: '1:30 pm', swath: '2,330 km', note: 'Afternoon satellite. Like Terra it drifts from its planned orbit; the drift chart in the explorer checks what MODIS still sees.' },
  { name: 'Suomi NPP', inst: 'VIIRS · 375 m fire pixels', alt: 824, vel: '7.44', per: '101', orb: 'Polar SSO', launch: '28 Oct 2011', cross: '1:30 pm', swath: '3,040 km', note: 'First VIIRS. Its 375 m fire pixels catch fires too small for MODIS, which is why naive merges climb after 2012. It stops delivering data on 2 Nov 2026.' },
  { name: 'NOAA-20', inst: 'VIIRS · 375 m fire pixels', alt: 824, vel: '7.44', per: '101', orb: 'Polar SSO', launch: '18 Nov 2017', cross: '1:30 pm', swath: '3,040 km', note: 'Flies the same orbit as Suomi NPP, about half an orbit (some 50 minutes) apart; the record ties it in through Suomi NPP.' },
];
function showSat(k) {
  window.__selSat = k; const s = SATINFO[k];
  document.querySelectorAll('.sc-tabs button').forEach((b) => b.setAttribute('aria-selected', String(Number(b.dataset.sat) === k)));
  $('#scName').textContent = s.name; $('#scInst').textContent = s.inst; $('#scAlt').textContent = s.alt; $('#scVel').textContent = s.vel; $('#scPer').textContent = s.per;
  $('#scOrb').textContent = s.orb; $('#scLaunch').textContent = s.launch; $('#scCross').textContent = s.cross; $('#scSwath').textContent = s.swath; $('#scNote').textContent = s.note;
}
document.querySelectorAll('.sc-tabs button').forEach((b) => b.addEventListener('click', () => showSat(Number(b.dataset.sat))));
showSat(2);

// ---------- the hero video: only where the 3D stage cannot run, only after the calendar ----------
let calendarUp = false;
function maybeVideo() {
  const v = $('.hero-video');
  if (!v || !calendarUp || !html.classList.contains('no-gl') || reduce || navigator.connection?.saveData) return;
  v.preload = 'auto'; v.play().catch(() => {});
}
window.__stageFailed = (err) => { html.classList.remove('gl-ok', 'gl-live'); html.classList.add('no-gl'); maybeVideo(); if (err) console.warn('3D story stage unavailable:', err.message || err); };
window.__glReady = () => html.classList.add('gl-live');

// ---------- story numbers, from the record ----------
// The story features Lebanon, the team's home region. Every figure below is computed from its files.
const STORY = 'lebanon';
const CONTINENT = { portugal: 'Europe', central_spain: 'Europe', southern_italy: 'Europe', southern_france: 'Europe', greece: 'Europe',
  lebanon: 'Asia', syria: 'Asia', turkey: 'Asia', morocco: 'Africa', tunisia: 'Africa', northern_algeria: 'Africa', western_cape: 'Africa',
  la_rioja: 'South America', central_chile: 'South America', s_california: 'North America', n_california: 'North America',
  sw_australia: 'Australia', south_australia: 'Australia' };
const WORDS = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine'];
const n1 = (v) => (v < 10 ? (Math.round(v * 10) / 10).toLocaleString('en-US') : n0(v));
function ramp(t) {
  const x = Math.min(1, Math.max(0, t)) * (EMBER.length - 1); const i = Math.min(EMBER.length - 2, Math.floor(x)); const u = x - i;
  const a = EMBER[i]; const b = EMBER[i + 1];
  return [1, 3, 5].map((k) => Math.round(parseInt(a.slice(k, k + 2), 16) + (parseInt(b.slice(k, k + 2), 16) - parseInt(a.slice(k, k + 2), 16)) * u));
}
const median = (a) => { const s = [...a].sort((x, y) => x - y); const m = (s.length - 1) / 2; return s.length ? (s[Math.floor(m)] + s[Math.ceil(m)]) / 2 : NaN; };
function buildStory(index, mon) {
  const meta = index.regions.find((r) => r.id === STORY); const name = meta.name;
  const n = mon.months.n; const [fy, fm] = mon.months.first.split('-').map(Number); const [ly] = mon.months.last.split('-').map(Number);
  const H = new Array(n).fill(0); const NV = new Array(n).fill(0);
  mon.m.forEach((row, c) => { const nr = mon.naive[c]; for (let j = 0; j < n; j += 1) { H[j] += row[j]; NV[j] += nr[j]; } });
  const ym = (j) => { const t = (fm - 1) + j; return [fy + Math.floor(t / 12), (t % 12) + 1]; };
  const key = (j) => { const [y, m] = ym(j); return `${y}-${String(m).padStart(2, '0')}`; };
  const est = (j) => /[ENJ]/.test(mon.flags[j]);
  // years with all twelve months in the record
  const years = {}; for (let j = 0; j < n; j += 1) { const [y] = ym(j); (years[y] ||= { y, h: 0, nv: 0, k: 0, flags: '' }); years[y].h += H[j]; years[y].nv += NV[j]; years[y].k += 1; years[y].flags += mon.flags[j]; }
  const full = Object.values(years).filter((o) => o.k === 12);
  // 1. home: burning days by year, worst months
  const mx = Math.max(...full.map((o) => o.h)); const mn = Math.max(1, Math.min(...full.map((o) => o.h))); const ROWS = 12;
  const yd = $('#ydots'); yd.style.setProperty('--ny', full.length);
  yd.innerHTML = full.map((o) => { const k = Math.max(1, Math.round(1 + (ROWS - 1) * Math.log(Math.max(o.h, 1) / mn) / Math.log(mx / mn)));
    return `<div class="col${o.h === mx ? ' hot' : ''}" title="${o.y}: ${n0(o.h)} burning days${/[ENJ]/.test(o.flags) ? ' (estimated)' : ''}">${Array.from({ length: ROWS }, (_, j) => `<i class="${j < k ? 'f' : ''}"></i>`).join('')}</div>`; }).join('');
  const top = full.find((o) => o.h === mx);
  $('#ydFirst').textContent = full[0].y; $('#ydLast').textContent = full[full.length - 1].y; $('#ydMax').textContent = `Peak ${top.y} · ${n0(mx)}`;
  yd.setAttribute('aria-label', `Harmonized burning days per year in ${name}, ${full[0].y} to ${full[full.length - 1].y} (complete years); the peak is ${top.y} with ${n0(mx)}`);
  const order = H.map((v, j) => ({ v, j })).sort((a, b) => b.v - a.v);
  $('#worst').innerHTML = order.slice(0, 6).map((o) => `<li><span>${ymText(key(o.j))}</span><span class="bar"><i style="transform:scaleX(${(o.v / order[0].v).toFixed(3)})"></i></span><b>${n0(o.v)}</b></li>`).join('');
  // the catalogue
  const firsts = index.regions.map((r) => r.months.first).sort(); const lasts = index.regions.map((r) => r.months.last).sort();
  const nCont = new Set(index.regions.map((r) => CONTINENT[r.id]).filter(Boolean)).size;
  $('#span-all').textContent = `${ymText(firsts[0])} – ${ymText(lasts[lasts.length - 1])}`;
  $('#rec-regions').textContent = index.regions.length; $('#rec-months').textContent = n; $('#rec-cells').textContent = mon.cells.ix.length;
  document.querySelectorAll('.st-nregions').forEach((el) => { el.textContent = index.regions.length; });
  document.querySelectorAll('.st-ncont').forEach((el) => { el.textContent = WORDS[nCont] || nCont; });
  $('#about-span').textContent = `${ymText(firsts[0])} – ${ymText(lasts[lasts.length - 1])} across ${index.regions.length} regions on ${WORDS[nCont] || nCont} continents (${name}: ${ymText(mon.months.first)} – ${ymText(mon.months.last)})`;
  // 2. the calendar
  $('#st-years').textContent = ly - fy + 1; $('#st-months').textContent = n; $('#st-cells').textContent = mon.cells.ix.length;
  const typical = median(full.map((o) => o.h));
  SHORT.cal = { first: [fm, fy], top: ym(order[0].j), n: order[0].v, typical };
  SHORT.region = name; SHORT.nRegions = index.regions.length;
  $('#st-small').textContent = `its busiest month on record, ${ymText(key(order[0].j), true)}, has ${n0(order[0].v)} burning days, and a typical year about ${n0(typical)}, so one large fire stands out.`;
  const hottest = order.slice(0, 4).map((o) => ymText(key(o.j), true));
  $('#st-hottest').textContent = `${hottest.slice(0, -1).join(', ')} and ${hottest[hottest.length - 1]}`;
  // 3. the problem: 2012-2021, when the harmonized record is observed MODIS
  const obs = full.filter((o) => o.y >= 2012 && /^O+$/.test(o.flags));
  if (obs.length) {
    const sn = obs.reduce((a, o) => a + o.nv, 0); const sh = obs.reduce((a, o) => a + o.h, 0); const r = sn / sh;
    SHORT.prob = { y0: obs[0].y, y1: obs[obs.length - 1].y, r, sn, sh };
    $('#st-naive').textContent = `From ${obs[0].y} to ${obs[obs.length - 1].y}, while MODIS still flew its planned orbits, the naive merge counts ${n0(sn)} burning days in ${name} where MODIS saw ${n0(sh)}: ${r >= 2 ? `${n1(r)} times as many` : `${Math.round((r - 1) * 100)}% more`}. Small fires are exactly what the sharper sensor adds, and ${name}'s fires are mostly small.`;
  }
  // 4. the fix: the biggest complete years, and the honest caveat for estimated years
  const big = [...full].sort((a, b) => b.h - a.h).slice(0, 3);
  $('#st-topyears').textContent = big.map((o) => `${o.y} (${n0(o.h)}${/[ENJ]/.test(o.flags) ? ', estimated' : ''})`).join(', ');
  const zw = meta.burning_days?.zero_weight;
  if (zw?.viirs_burning_days) $('#st-zero').textContent = `One caution for ${name}: since 2022, ${n0(zw.weight_zero)} of its ${n0(zw.viirs_burning_days)} VIIRS burning days (${Math.round(zw.share * 100)}%) carry no weight, because their kind of fire never matched a MODIS fire in that season during 2012–2019, so its estimates from 2022 rest on the others.`;
  // 5. any area: the busiest month of the last three years in the record
  let aug = -1; for (let j = 0; j < n; j += 1) if (ym(j)[0] >= ly - 2 && (aug < 0 || H[j] > H[aug])) aug = j;
  document.querySelectorAll('.st-aug').forEach((el) => { el.textContent = ymText(key(aug), true); });
  $('#cellsChip').textContent = `${mon.cells.ix.length} cells · 0.25° · ${ymText(key(aug), true)} · ${n0(H[aug])} burning days${est(aug) ? ' (estimated)' : ''}`;
  // 6. the season rings
  $('#st-ring0').textContent = fy; $('#st-ring1').textContent = ly;

  // the 3D stage's data: a full calendar grid (rows fy..ly), months outside the record are null
  const NY = ly - fy + 1; const N = NY * 12; const off = fm - 1;
  const at = (i) => { const j = i - off; return j >= 0 && j < n ? j : -1; };
  const vmax = Math.max(...H, ...NV, 1); const cmax = Math.max(1, ...mon.m.map((r) => r[aug]));
  const lg = (v, top2) => (v == null || v <= 0 ? 0 : Math.log10(1 + v) / Math.log10(1 + top2));
  const bb = meta.bbox;
  window.__storyD = {
    Y0: fy, NY, N, MON, MONL, AUG: aug + off, vmax, cmax, story: { id: STORY, name, lon: (bb[0] + bb[2]) / 2, lat: (bb[1] + bb[3]) / 2, bbox: bb },
    H: Array.from({ length: N }, (_, i) => (at(i) < 0 ? null : H[at(i)])),
    NV: Array.from({ length: N }, (_, i) => (at(i) < 0 ? null : NV[at(i)])),
    cells: mon.cells.ix.map((ix, c) => ({ lon: (ix + 0.5) * mon.cell_deg, lat: (mon.cells.iy[c] + 0.5) * mon.cell_deg })),
    C: mon.cells.ix.length,
    cellVal: (c, i) => (at(i) < 0 ? 0 : mon.m[c][at(i)]),
    logn: (v) => lg(v, vmax), cellLogn: (v) => lg(v, cmax),
    colorFor: (v) => ramp(0.08 + 0.92 * lg(v, vmax)), cellColor: (v) => ramp(0.08 + 0.92 * lg(v, cmax)),
    regions: index.regions.map((r) => ({ id: r.id, name: r.name, bbox: r.bbox })),
    storySub: tr('The story region · Beirut, team home'),
  };
}

// The season slide: the same computation as the Fire Calendar's season panel (app.js renderSeason) for the whole
// region, from the story region's daily burning-day records (2003 to the last complete year).
async function storySeason(index) {
  const meta = index.regions.find((r) => r.id === STORY);
  const last = Number(meta.months.last.slice(0, 4)) - (meta.months.last.endsWith('-12') ? 0 : 1);
  const have = meta.burning_days?.years || [];
  const ys = []; for (let y = 2003; y <= last; y += 1) if (!have.length || have.includes(y)) ys.push(y);
  const files = await Promise.all(ys.map((y) => fetch(`data/${STORY}/burning/${y}.json`).then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })));
  const totals = []; const dates = [];
  for (const f of files) {
    const daily = new Float64Array(367); const c = f.cols;
    for (let i = 0; i < f.n; i += 1) if (c.w[i] > 0) daily[c.doy[i]] += c.w[i];
    const total = daily.reduce((a, b) => a + b, 0); totals.push(total);
    if (total >= 20) { let cum = 0; const d = []; for (let doy = 1; doy <= 366 && d.length < 3; doy += 1) { cum += daily[doy]; while (d.length < 3 && cum >= [0.1, 0.5, 0.9][d.length] * total - 1e-9) d.push(doy); } dates.push(d); }
  }
  const q = (a, p) => { const s = [...a].sort((x, y) => x - y); const i = (s.length - 1) * p; const lo = Math.floor(i); return s[lo] + (s[Math.ceil(i)] - s[lo]) * (i - lo); };
  if (median(totals) < 20 || !dates.length) {
    ['#ssStart', '#ssMid', '#ssEnd'].forEach((a) => { $(a).textContent = '–'; });
    $('#st-season-note').textContent = `A typical year here has too few burning days (${n0(median(totals))}) to date a season.`; return;
  }
  SHORT.season = { k: dates.length, days: [0, 1, 2].map((k) => Math.round(q(dates.map((d) => d[k]), 0.5))) }; renderShort();
  [['#ssStart', '#ssStartPm'], ['#ssMid', '#ssMidPm'], ['#ssEnd', '#ssEndPm']].forEach(([a, b], k) => {
    const s = dates.map((d) => d[k]); const day = new Date(Date.UTC(2001, 0, Math.round(q(s, 0.5))));
    $(a).textContent = `${MON[day.getUTCMonth()]} ${day.getUTCDate()}`; $(b).textContent = `± ${Math.round((q(s, 0.75) - q(s, 0.25)) / 2)} days`;
  });
  $('#st-season-note').textContent = `Over the ${dates.length} years in ${ys[0]}–${ys[ys.length - 1]} with at least 20 burning days; ± is half the spread across years.`;
}

// The landing's one-line aside: typed once the hero has settled, held, then faded so the page stays light on words.
// Counts come from the catalogue. Screen readers get the whole sentence once; reduced motion or Effects off: no typing.
const TYPE_EN = 'Lebanon is our home. The same tool covers {n} regions on {c} continents, including La Rioja, the challenge authors’ own example.';
function typeLine(index) {
  const el = $('#typeline'); const sr = $('#typeline-sr'); if (!el) return;
  const nCont = new Set(index.regions.map((r) => CONTINENT[r.id]).filter(Boolean)).size;
  const lang = window.cedrusI18n?.lang?.() || 'en';
  const tpl = window.cedrusI18n?.tr?.(TYPE_EN) || TYPE_EN;
  const text = tpl.replace('{n}', index.regions.length).replace('{c}', lang === 'en' ? (WORDS[nCont] || nCont) : nCont);
  if (lang === 'ar') el.dir = 'rtl'; else el.removeAttribute('dir');
  if (lang !== 'en') el.lang = lang; else el.removeAttribute('lang');
  sr.textContent = text;
  const still = reduce || html.classList.contains('fx-still');
  const hide = () => { el.classList.add('gone'); setTimeout(() => { el.textContent = ''; el.classList.remove('typing'); }, still ? 0 : 900); };
  if (still) { el.textContent = text; setTimeout(hide, 4000); return; }
  let k = 0; el.classList.add('typing');
  const tick = () => { k += 1; el.textContent = text.slice(0, k); if (k < text.length) setTimeout(tick, text[k - 1] === '.' ? 260 : 26); else { el.classList.remove('typing'); setTimeout(hide, 2500); } };
  tick();
}

// ---------- the orbit slide: its paragraph types at reading speed, the first time the slide is shown ----------
// The full text stays in the page (transparent while typing) so the layout never moves and screen readers get it
// whole; the typed copy on top is hidden from them. Reduced motion or Effects off: shown at once. Click to finish.
let orbitTyped = false;
function typeOrbit() {
  if (orbitTyped) return; orbitTyped = true;
  const p = $('#orbit-lede'); if (!p) return;
  const src = p.querySelector('.tp-src'); const out = p.querySelector('.tp-type');
  if (reduce || html.classList.contains('fx-still')) return;
  const text = src.textContent; let k = 0; let timer = 0;
  out.dir = langNow() === 'ar' ? 'rtl' : '';
  p.classList.add('typing');
  const finish = () => { clearTimeout(timer); p.classList.remove('typing'); out.textContent = ''; p.removeEventListener('click', finish); };
  p.addEventListener('click', finish);
  const tick = () => {
    k += 1; out.textContent = text.slice(0, k);
    if (k >= text.length) { finish(); return; }
    const c = text[k - 1]; timer = setTimeout(tick, c === '.' || c === ';' ? 320 : c === ',' ? 120 : 30);
  };
  tick();
}

// ---------- slides 2-6: one or two short lines each, typed fast (about 3 s) every time the slide is shown ----------
// The detail they replace sits word for word under Data & Methodology ("Behind the story").
const SHORT = {};
function phaseOf(doy) {
  const d = new Date(Date.UTC(2001, 0, doy)); const day = d.getUTCDate(); const m = d.getUTCMonth() + 1; const lang = langNow();
  const month = monthName(m);
  const ph = day <= 10 ? 0 : day <= 20 ? 1 : 2;
  if (lang === 'es') return [`a principios de ${month}`, `a mediados de ${month}`, `a finales de ${month}`][ph];
  if (lang === 'ar') return [`في أوائل ${month}`, `في منتصف ${month}`, `في أواخر ${month}`][ph];
  return [`early ${month}`, `mid-${month}`, `late ${month}`][ph];
}
function setShort(key, text) {
  const p = document.getElementById(`lede-${key}`); if (!p || !text) return;
  const src = p.querySelector('.tp-src'); if (src.textContent === text) return;
  src.textContent = text; p.dir = langNow() === 'ar' ? 'rtl' : ''; if (langNow() !== 'en') p.lang = langNow(); else p.removeAttribute('lang');
}
function renderShort() {
  const R = SHORT.region; if (!R) return;
  const fill = (tpl, o) => Object.entries(o).reduce((t, [k, v]) => t.split(`{${k}}`).join(v), tr(tpl));
  if (SHORT.cal) {
    const c = SHORT.cal;
    setShort('cal', fill('One tile is one month of fire over {region} since {first}. The brightest is {top}: {n} burning days, when a normal year has about {typical}.',
      { region: R, first: monthName(c.first[0], true, c.first[1]), top: monthName(c.top[1], true, c.top[0]), n: n0(c.n), typical: n0(c.typical) }));
  }
  if (SHORT.prob) {
    const b = SHORT.prob;
    setShort('prob', fill('Newer satellites see small fires that MODIS misses. Merge them naively and {region}’s {y0}–{y1} looks {r}× worse than it was: {sn} burning days instead of {sh}.',
      { region: R, y0: b.y0, y1: b.y1, r: n1(b.r), sn: n0(b.sn), sh: n0(b.sh) }));
  }
  setShort('why', tr("2025 was the EU's worst fire year on record: 1,079,538 hectares burned. The UN expects extreme fires to rise 30% by 2050 — and countries plan budgets, crews and fire seasons from the satellite record."));
  setShort('fix', tr('We learn how VIIRS translates into MODIS from the years both flew (2012–2019), then apply it after MODIS fades. The false climb flattens, and real fire years still stand out.'));
  setShort('area', fill('Pick one of {n} regions, or draw any shape, and read its fire record down to a single 0.25° cell (about 25 km).', { n: SHORT.nRegions }));
  if (SHORT.season) {
    const z = SHORT.season;
    setShort('season', fill('{region}’s fire season, worked out from {k} years of daily records: it normally starts {start}, peaks {mid} and ends {end}.',
      { region: R, k: z.k, start: phaseOf(z.days[0]), mid: phaseOf(z.days[1]), end: phaseOf(z.days[2]) }));
  }
}
function typeFast(p) {
  const src = p.querySelector('.tp-src'); const out = p.querySelector('.tp-type');
  clearTimeout(p._timer); p.classList.remove('typing'); out.textContent = '';
  const text = src.textContent;
  if (!text || reduce || html.classList.contains('fx-still')) return;
  const step = Math.max(8, Math.min(30, 3000 / text.length)); let k = 0;
  out.dir = langNow() === 'ar' ? 'rtl' : '';
  p.classList.add('typing');
  const tick = () => { k += 1; out.textContent = text.slice(0, k); if (k >= text.length) { p.classList.remove('typing'); out.textContent = ''; return; } p._timer = setTimeout(tick, step); };
  p._timer = setTimeout(tick, 350);
}

// ---------- region tour (orbit slide): every region in the catalogue, in plain words ----------
// Each card is computed from that region's monthly_bd.json, fetched only when the tour reaches it.
const tourCache = new Map();
let tourIndex = null; let tourK = 0; let tourToken = 0;
function monthName(m, withYear, y) {
  const lang = langNow(); const d = new Date(Date.UTC(y || 2001, m - 1, 15));
  try { return new Intl.DateTimeFormat(lang === 'en' ? 'en-GB' : lang, withYear ? { month: 'long', year: 'numeric', timeZone: 'UTC' } : { month: 'long', timeZone: 'UTC' }).format(d); } catch { return `${MONL[m - 1]}${withYear ? ` ${y}` : ''}`; }
}
function regionFacts(r, mon) {
  const n = mon.months.n; const [fy, fm] = mon.months.first.split('-').map(Number);
  const H = new Array(n).fill(0); mon.m.forEach((row) => { for (let j = 0; j < n; j += 1) H[j] += row[j]; });
  const ym = (j) => { const t = (fm - 1) + j; return [fy + Math.floor(t / 12), (t % 12) + 1]; };
  const years = {}; for (let j = 0; j < n; j += 1) { const [y, m] = ym(j); (years[y] ||= { y, tot: 0, k: 0, m: new Array(12).fill(0) }); years[y].tot += H[j]; years[y].k += 1; years[y].m[m - 1] = H[j]; }
  const full = Object.values(years).filter((o) => o.k === 12).sort((a, b) => a.y - b.y);
  const lines = [];
  // when the season peaks: the calendar month with the highest median over the complete years
  const med = Array.from({ length: 12 }, (_, m) => median(full.map((o) => o.m[m])));
  const peak = med.indexOf(Math.max(...med));
  lines.push(med[peak] < 1 ? tr('Fires are rare here in every month.') : tr('In a typical year, fires here are most frequent in {month}.').replace('{month}', monthName(peak + 1)));
  // the biggest month on record
  let jMax = 0; for (let j = 1; j < n; j += 1) if (H[j] > H[jMax]) jMax = j;
  const [wy, wm] = ym(jMax);
  lines.push(tr('Its worst month on record was {monthyear} ({n} burning days).').replace('{monthyear}', monthName(wm, true, wy)).replace('{n}', n0(H[jMax])));
  // the latest complete year against a typical (median) complete year before it
  const last = full[full.length - 1]; const before = full.slice(0, -1).map((o) => o.tot);
  if (last && before.length >= 5) {
    const ratio = last.tot / Math.max(1e-9, median(before));
    const key = ratio > 1.2 ? '{year} was busier than a typical year.' : ratio < 0.83 ? '{year} was quieter than a typical year.' : '{year} was about a typical year.';
    lines.push(tr(key).replace('{year}', last.y));
  }
  // one honest caveat, from the region's own forward-test note
  const test = (r.notes || []).filter((x) => /\btest/i.test(x)).join(' ');
  const cellErr = [...test.matchAll(/(?:grid-cell|single-square|single cells?)[^.]*?(\d+)(?:[–-](\d+))?%/gi)].flatMap((m) => [Number(m[1]), Number(m[2] || 0)]);
  let caveat = null;
  if (/not reliable|above the 100% limit/i.test(test) || Math.max(0, ...cellErr) >= 100) caveat = tr('Single small areas are less reliable here; the whole-region totals are the stronger figures.');
  else if (/burning days failed|failed the check/i.test(test) && !/burning days passed every check/i.test(test)) caveat = tr('Its own accuracy test (2020–2021) missed a pass mark, so read its totals with care.');
  const span = tr('Record: {span} · {cells} cells of 0.25°').replace('{span}', `${ymText(r.months.first)} – ${ymText(r.months.last)}`).replace('{cells}', mon.cells.ix.length);
  return { lines, caveat, span };
}
function renderTour(r, facts) {
  const card = $('#tour-card');
  card.dir = langNow() === 'ar' ? 'rtl' : ''; if (langNow() !== 'en') card.lang = langNow(); else card.removeAttribute('lang');
  $('#tour-name').textContent = r.name;
  $('#tour-count').textContent = tr('Region {k} of {n}').replace('{k}', tourK + 1).replace('{n}', tourIndex.regions.length);
  const ul = $('#tour-lines'); ul.textContent = '';
  if (!facts) { const li = document.createElement('li'); li.textContent = tr('Loading this region…'); ul.append(li); card.setAttribute('aria-busy', 'true'); $('#tour-span').textContent = ''; return; }
  card.removeAttribute('aria-busy');
  facts.lines.forEach((t) => { const li = document.createElement('li'); li.textContent = t; ul.append(li); });
  if (facts.caveat) { const li = document.createElement('li'); li.className = 'caveat'; li.textContent = facts.caveat; ul.append(li); }
  $('#tour-span').textContent = facts.span;
}
async function showRegion(k) {
  const regions = tourIndex.regions; tourK = (k + regions.length) % regions.length; const r = regions[tourK];
  const token = ++tourToken;
  const sub = r.id === STORY ? tr('The story region · Beirut, team home') : tr('Region {k} of {n}').replace('{k}', tourK + 1).replace('{n}', regions.length);
  window.__stageFocusWanted = [r.id, sub]; window.__stageFocus?.(r.id, sub);
  if (!tourCache.has(r.id)) {
    renderTour(r, null);
    tourCache.set(r.id, fetch(`data/${r.id}/monthly_bd.json`).then((x) => { if (!x.ok) throw new Error(`HTTP ${x.status}`); return x.json(); }));
  }
  try { const mon = await tourCache.get(r.id); if (token === tourToken) renderTour(r, regionFacts(r, mon)); } catch (err) { tourCache.delete(r.id); if (token === tourToken) { renderTour(r, { lines: [`${r.name}: ${err.message}`], caveat: null, span: '' }); } }
}
function leaveTour() { if (tourIndex && tourIndex.regions[tourK]?.id !== STORY) { const k = tourIndex.regions.findIndex((x) => x.id === STORY); showRegion(k); } }
function initTour(index, mon) {
  tourIndex = index; tourK = index.regions.findIndex((x) => x.id === STORY);
  tourCache.set(STORY, Promise.resolve(mon));
  showRegion(tourK);
  $('#tour-next').addEventListener('click', () => showRegion(tourK + 1));
  $('#tour-prev').addEventListener('click', () => showRegion(tourK - 1));
  $('#tour').addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') { e.preventDefault(); e.stopPropagation(); showRegion(tourK + 1); }
    else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') { e.preventDefault(); e.stopPropagation(); showRegion(tourK - 1); }
  });
  // a language switch rewrites the card in the new language
  document.querySelectorAll('#lang-switch button').forEach((b) => b.addEventListener('click', () => setTimeout(() => showRegion(tourK), 0)));
}

async function boot() {
  try { await window.cedrus?.ready; } catch { /* the app shows its own error */ }
  if (!window.cedrus) { await new Promise((r) => { const t = setInterval(() => { if (window.cedrus) { clearInterval(t); r(); } }, 100); }); try { await window.cedrus.ready; } catch { /* shown by the app */ } }
  calendarUp = true; maybeVideo();
  let index; let mon;
  try {
    [index, mon] = await Promise.all(['data/regions.json', `data/${STORY}/monthly_bd.json`].map((p) => fetch(p).then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status} for ${p}`); return r.json(); })));
  } catch (err) { console.warn('Story numbers unavailable:', err.message); window.__stageFailed(); return; }
  buildStory(index, mon);
  renderShort();
  initTour(index, mon);
  document.querySelectorAll('#lang-switch button').forEach((b) => b.addEventListener('click', () => setTimeout(renderShort, 0)));
  setTimeout(() => typeLine(index), reduce ? 300 : 1400);
  if (html.classList.contains('gl-ok')) import(`./stage.js${V}`).catch((err) => window.__stageFailed(err));
  storySeason(index).catch((err) => { $('#st-season-note').textContent = `Season dates unavailable (${err.message}).`; });
}
boot();
