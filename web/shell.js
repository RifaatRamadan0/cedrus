// CEDRUS shell: the story deck (Yasmina's design) in front of the app. It never changes the record; every number
// it writes into the story is computed here from data/regions.json and data/portugal/monthly_bd.json, read only
// after the calendar has rendered (the cold load waits for the calendar files alone).
import { EMBER } from './fx.js';

const $ = (s) => document.querySelector(s);
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

const ruler = $('#ruler');
ruler.innerHTML = shots.map((s, j) => `<button type="button" aria-label="Slide ${j + 1}: ${s.dataset.name}"></button>`).join('');
const rulerBtns = [...ruler.children];
function hud() {
  $('#hudNum').textContent = String(cur + 1).padStart(2, '0');
  $('#hudTot').textContent = String(shots.length).padStart(2, '0');
  $('#hudName').textContent = shots[cur].dataset.name;
  html.classList.toggle('on-first', cur === 0);
  rulerBtns.forEach((b, j) => { b.classList.toggle('on', j === cur); if (j === cur) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current'); });
  $('#prevBtn').disabled = cur === 0;
  $('#nextBtn').disabled = false; // past the last slide, "next" opens the explorer
}
function activate(n) {
  const s = shots[n]; s.classList.add('active'); s.scrollTop = 0; s.removeAttribute('inert');
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
  lock = true; const prev = shots[cur]; cur = n; window.__slide = n; hud();
  const dur = (!instant && window.__flyTo && window.__flyTo(n)) || 0;
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
  if (br > 0) { cur = best; window.__slide = best; }
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
  if (k > 0) { cur = k; window.__slide = k; }
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
function ramp(t) {
  const x = Math.min(1, Math.max(0, t)) * (EMBER.length - 1); const i = Math.min(EMBER.length - 2, Math.floor(x)); const u = x - i;
  const a = EMBER[i]; const b = EMBER[i + 1];
  return [1, 3, 5].map((k) => Math.round(parseInt(a.slice(k, k + 2), 16) + (parseInt(b.slice(k, k + 2), 16) - parseInt(a.slice(k, k + 2), 16)) * u));
}
function buildStory(index, mon) {
  const n = mon.months.n; const [fy, fm] = mon.months.first.split('-').map(Number); const [ly] = mon.months.last.split('-').map(Number);
  const H = new Array(n).fill(0); const NV = new Array(n).fill(0);
  mon.m.forEach((row, c) => { const nr = mon.naive[c]; for (let j = 0; j < n; j += 1) { H[j] += row[j]; NV[j] += nr[j]; } });
  const ym = (j) => { const t = (fm - 1) + j; return [fy + Math.floor(t / 12), (t % 12) + 1]; };
  const key = (j) => { const [y, m] = ym(j); return `${y}-${String(m).padStart(2, '0')}`; };
  // years with all twelve months in the record
  const years = {}; for (let j = 0; j < n; j += 1) { const [y] = ym(j); (years[y] ||= { y, h: 0, nv: 0, k: 0, flags: '' }); years[y].h += H[j]; years[y].nv += NV[j]; years[y].k += 1; years[y].flags += mon.flags[j]; }
  const full = Object.values(years).filter((o) => o.k === 12);
  // 1. home: burning days by year, worst months
  const mx = Math.max(...full.map((o) => o.h)); const mn = Math.max(1, Math.min(...full.map((o) => o.h))); const ROWS = 12;
  const yd = $('#ydots'); yd.style.setProperty('--ny', full.length);
  yd.innerHTML = full.map((o) => { const k = Math.max(1, Math.round(1 + (ROWS - 1) * Math.log(Math.max(o.h, 1) / mn) / Math.log(mx / mn)));
    return `<div class="col${o.h === mx ? ' hot' : ''}" title="${o.y}: ${n0(o.h)} burning days">${Array.from({ length: ROWS }, (_, j) => `<i class="${j < k ? 'f' : ''}"></i>`).join('')}</div>`; }).join('');
  const top = full.find((o) => o.h === mx);
  $('#ydFirst').textContent = full[0].y; $('#ydLast').textContent = full[full.length - 1].y; $('#ydMax').textContent = `Peak ${top.y} · ${n0(mx)}`;
  yd.setAttribute('aria-label', `Harmonized burning days per year in Portugal, ${full[0].y} to ${full[full.length - 1].y} (complete years); the peak is ${top.y} with ${n0(mx)}`);
  const order = H.map((v, j) => ({ v, j })).sort((a, b) => b.v - a.v);
  $('#worst').innerHTML = order.slice(0, 6).map((o) => `<li><span>${ymText(key(o.j))}</span><span class="bar"><i style="transform:scaleX(${(o.v / order[0].v).toFixed(3)})"></i></span><b>${n0(o.v)}</b></li>`).join('');
  // the catalogue
  const firsts = index.regions.map((r) => r.months.first).sort(); const lasts = index.regions.map((r) => r.months.last).sort();
  $('#span-all').textContent = `${ymText(firsts[0])} – ${ymText(lasts[lasts.length - 1])}`;
  $('#rec-regions').textContent = index.regions.length; $('#rec-months').textContent = n; $('#rec-cells').textContent = mon.cells.ix.length;
  document.querySelectorAll('.st-nregions').forEach((el) => { el.textContent = index.regions.length; });
  $('#about-span').textContent = `${ymText(mon.months.first)} – ${ymText(mon.months.last)} (Portugal); ${ymText(firsts[0])} – ${ymText(lasts[lasts.length - 1])} across all ${index.regions.length} regions`;
  // 2. the calendar
  $('#st-years').textContent = ly - fy + 1; $('#st-months').textContent = n; $('#st-cells').textContent = mon.cells.ix.length;
  const hottest = order.slice(0, 4).map((o) => ymText(key(o.j), true));
  $('#st-hottest').textContent = `${hottest.slice(0, -1).join(', ')} and ${hottest[hottest.length - 1]}`;
  // 3. the problem: 2012-2021, when the harmonized record is observed MODIS
  const obs = full.filter((o) => o.y >= 2012 && /^O+$/.test(o.flags));
  if (obs.length) {
    const sn = obs.reduce((a, o) => a + o.nv, 0); const sh = obs.reduce((a, o) => a + o.h, 0);
    $('#st-naive').textContent = `From ${obs[0].y} to ${obs[obs.length - 1].y}, while MODIS still flew its planned orbits, the naive merge counts ${n0(sn)} burning days in Portugal where MODIS saw ${n0(sh)}: ${Math.round((sn / sh - 1) * 100)}% more, all of it from the sharper sensor.`;
  }
  // 4. the fix: the biggest complete years
  const big = [...full].sort((a, b) => b.h - a.h).slice(0, 3);
  $('#st-topyears').textContent = big.map((o) => `${o.y} (${n0(o.h)} burning days)`).join(', ');
  // 5. any area: the story month is August 2025 if the record has it, else the record's worst month
  let aug = H.findIndex((_, j) => key(j) === '2025-08'); if (aug < 0) aug = order[0].j;
  document.querySelectorAll('.st-aug').forEach((el) => { el.textContent = ymText(key(aug), true); });
  $('#cellsChip').textContent = `${mon.cells.ix.length} cells · 0.25° · ${ymText(key(aug), true)}`;
  // 6. the season rings
  $('#st-ring0').textContent = fy; $('#st-ring1').textContent = ly;

  // the 3D stage's data: a full calendar grid (rows fy..ly), months outside the record are null
  const NY = ly - fy + 1; const N = NY * 12; const off = fm - 1;
  const at = (i) => { const j = i - off; return j >= 0 && j < n ? j : -1; };
  const vmax = Math.max(...H, ...NV, 1); const cmax = Math.max(1, ...mon.m.map((r) => r[aug]));
  const lg = (v, top2) => (v == null || v <= 0 ? 0 : Math.log10(1 + v) / Math.log10(1 + top2));
  window.__storyD = {
    Y0: fy, NY, N, MON, MONL, AUG: aug + off,
    H: Array.from({ length: N }, (_, i) => (at(i) < 0 ? null : H[at(i)])),
    NV: Array.from({ length: N }, (_, i) => (at(i) < 0 ? null : NV[at(i)])),
    cells: mon.cells.ix.map((ix, c) => ({ lon: (ix + 0.5) * mon.cell_deg, lat: (mon.cells.iy[c] + 0.5) * mon.cell_deg })),
    C: mon.cells.ix.length,
    cellVal: (c, i) => (at(i) < 0 ? 0 : mon.m[c][at(i)]),
    logn: (v) => lg(v, vmax), cellLogn: (v) => lg(v, cmax),
    colorFor: (v) => ramp(0.08 + 0.92 * lg(v, vmax)), cellColor: (v) => ramp(0.08 + 0.92 * lg(v, cmax)),
    regions: index.regions.map((r) => ({ id: r.id, bbox: r.bbox })),
  };
}

// The season slide shows the calendar's own season dates for Portugal (worked out from the daily records), so the
// story and the explorer never disagree.
function mirrorSeason() {
  const st = window.cedrus?.state;
  if (!st || st.unit !== 'bd' || st.meta?.id !== 'portugal' || st.area?.kind !== 'region') return;
  if ($('#season-dates')?.dataset.state !== 'dated') return;
  [['#ssStart', '#ssStartPm', '#cal-start', '#cal-start-spread'], ['#ssMid', '#ssMidPm', '#cal-peak', '#cal-peak-spread'], ['#ssEnd', '#ssEndPm', '#cal-end', '#cal-end-spread']]
    .forEach(([a, b, c, d]) => { $(a).textContent = $(c).textContent; $(b).textContent = $(d).textContent; });
}

async function boot() {
  try { await window.cedrus?.ready; } catch { /* the app shows its own error */ }
  if (!window.cedrus) { await new Promise((r) => { const t = setInterval(() => { if (window.cedrus) { clearInterval(t); r(); } }, 100); }); try { await window.cedrus.ready; } catch { /* shown by the app */ } }
  calendarUp = true; maybeVideo();
  new MutationObserver(mirrorSeason).observe($('#season-dates'), { subtree: true, childList: true, characterData: true, attributes: true });
  mirrorSeason();
  let index; let mon;
  try {
    [index, mon] = await Promise.all(['data/regions.json', 'data/portugal/monthly_bd.json'].map((p) => fetch(p).then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status} for ${p}`); return r.json(); })));
  } catch (err) { console.warn('Story numbers unavailable:', err.message); window.__stageFailed(); return; }
  buildStory(index, mon);
  if (!html.classList.contains('gl-ok')) return;
  import('./stage.js').catch((err) => window.__stageFailed(err));
}
boot();
