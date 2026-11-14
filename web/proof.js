// "How do we know it works?": the sealed exams as a scoreboard (data/proof.json), and each region's own forward
// test (the notes in data/regions.json). Standalone: it reads two static files and draws one section.
const DOCS = document.querySelector('meta[name="cedrus-docs"]')?.content || '';
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
const cap = (s) => s.charAt(0).toUpperCase() + s.slice(1);
const day = (iso) => new Date(`${iso}T12:00:00Z`).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' });

// One gauge: where the result sits against what the plan required. Scales are chosen per test kind.
function gauge(t) {
  let lo; let hi; let ok0; let ok1;
  if (t.max != null) { lo = 0; hi = Math.max(t.got, t.max) * 1.35; ok0 = 0; ok1 = t.max; }
  else if (t.min != null) { lo = 50; hi = 100; ok0 = t.min; ok1 = 100; }
  else if (t.unit === '×') { lo = 0.7; hi = 1.3; ok0 = t.lo; ok1 = t.hi; }
  else { lo = 50; hi = 100; ok0 = t.lo; ok1 = t.hi; }
  const x = (v) => Math.max(0, Math.min(100, ((v - lo) / (hi - lo)) * 100));
  return `<span class="gauge" aria-hidden="true"><i class="ok" style="left:${x(ok0)}%;width:${x(ok1) - x(ok0)}%"></i><b class="${t.pass ? 'pass' : 'fail'}" style="--x:${x(t.got)}%"></b></span>`;
}
function fmtGot(t) { return t.unit === '×' ? `${t.got.toFixed(3)}×` : `${t.got.toFixed(1)}%`; }

function examCard(e, tests) {
  const rows = e.tests.map((t) => {
    const d = tests[t.key];
    return `<li class="${t.pass ? 'pass' : 'fail'}"><span class="t-mark" aria-hidden="true">${t.pass ? '✓' : '✗'}</span>
      <span class="t-name">${esc(d.name)}<small>${esc(d.plain)}</small></span>
      ${gauge(t)}<span class="t-num"><strong>${fmtGot(t)}</strong><small>needed ${esc(t.need)}${t.unit === '×' ? '' : ''}</small></span>
      <span class="sr-only">${t.pass ? 'passed' : 'failed'}</span></li>`;
  }).join('');
  const passed = e.tests.filter((t) => t.pass).length;
  return `<article class="exam ${e.verdict}" aria-labelledby="${e.id}-t">
    <header><p class="exam-step">${esc(e.title)}</p><span class="stamp" role="img" aria-label="${e.verdict === 'failed' ? 'Not confirmed' : 'Confirmed'}">${e.verdict === 'failed' ? 'NOT CONFIRMED' : 'CONFIRMED'}</span></header>
    <h3 id="${e.id}-t">${esc(e.model)}</h3>
    <p class="exam-when"><span>Rules written <strong>${day(e.planned)}</strong></span><span aria-hidden="true">→</span><span>sat once <strong>${day(e.run)}</strong></span></p>
    <ul class="exam-regions" aria-label="Regions it had never seen">${e.regions.map(([n, c]) => `<li>${esc(n)} <small>${esc(c)}</small></li>`).join('')}</ul>
    <ol class="exam-tests" aria-label="${passed} of ${e.tests.length} tests passed">${rows}</ol>
    <p class="exam-lesson">${esc(e.lesson)}</p>
    <p class="exam-links"><a href="${DOCS}${e.plan}">The rules (plan)</a> · <a href="${DOCS}${e.source}">Full results</a></p>
  </article>`;
}

function regionsBlock(index) {
  const rows = index.regions.map((r) => {
    const notes = (r.notes || []).filter((n) => /\btest/i.test(n)).slice(0, 2);
    return notes.length ? `<li><strong>${esc(r.name)}</strong>${notes.map((n) => `<span>${esc(cap(n.replace(/^Forward test against MODIS, 2020–2021 \(fitted on 2012–2019\): /i, '')))}</span>`).join(' ')}</li>` : '';
  }).join('');
  return rows ? `<div class="proof-regions"><h3>And every region in this app was tested on its own data</h3>
    <p class="hint">Fitted on 2012–2019, then checked against real MODIS in 2020–2021, the last years MODIS still flew on its planned orbits. Where a region does worse, the app says so in that region's notes.</p><ul>${rows}</ul></div>` : '';
}

async function render() {
  const box = $('#proof-body'); if (!box) return;
  try {
    const [proof, index] = await Promise.all(['data/proof.json', 'data/regions.json'].map((u) => fetch(u).then((r) => { if (!r.ok) throw new Error(`${u}: HTTP ${r.status}`); return r.json(); })));
    const cards = proof.exams.map((e, k) => examCard(e, proof.tests) + (k < proof.exams.length - 1 ? `<span class="exam-arrow" aria-hidden="true">${k === 0 ? 'fixed the two causes →' : 'tournament of 9 models →'}</span>` : '')).join('');
    box.innerHTML = `<div class="exams">${cards}</div>${regionsBlock(index)}`;
    const io = 'IntersectionObserver' in window ? new IntersectionObserver((es) => es.forEach((en) => { if (en.isIntersecting) { en.target.classList.add('seen'); io.unobserve(en.target); } }), { threshold: 0.25 }) : null;
    box.querySelectorAll('.exam').forEach((el) => (io ? io.observe(el) : el.classList.add('seen')));
  } catch (err) {
    box.innerHTML = `<p class="hint">Couldn’t load the exam results (${esc(err.message)}). They are in the repository’s docs folder.</p>`;
  }
}
// Fetched only when the section comes near the screen: the first view of the calendar waits for nothing extra.
const target = $('#proof');
if (target && 'IntersectionObserver' in window) {
  const near = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { near.disconnect(); render(); } }, { rootMargin: '600px 0px' });
  near.observe(target);
} else render();
