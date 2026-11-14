"""Builds 'Fire, made visible' — the creative-ideas booklet — from the app's real monthly data.

python build.py  ->  creative-ideas.html  (then Chrome --print-to-pdf)
"""
import json, math, statistics as st, pathlib

ROOT = pathlib.Path(r"C:\Users\hussein\Downloads\cedrus\web\data")
OUT = pathlib.Path(__file__).with_name("creative-ideas.html")

def load(region):
    d = json.load(open(ROOT / region / "monthly_bd.json", encoding="utf-8"))
    n = d["months"]["n"]
    tot = [sum(row[j] for row in d["m"]) for j in range(n)]
    naive = [sum(row[j] for row in d["naive"]) for j in range(n)]
    return d, tot, naive

def ym(j):  # index 0 = 2000-12
    return 2000 + (11 + j) // 12, (11 + j) % 12 + 1

def idx(y, mo):
    return (y - 2000) * 12 + mo - 12

PT, PT_TOT, PT_NAIVE = load("portugal")
LB, LB_TOT, LB_NAIVE = load("lebanon")

def typical(tot, y, mo):
    """Median of the same calendar month, 2003-2025, leaving the year itself out."""
    vals = [tot[idx(yy, mo)] for yy in range(2003, 2026) if yy != y]
    return st.median(vals)

def month_medians(tot):
    return [st.median([tot[idx(y, mo)] for y in range(2003, 2026)]) for mo in range(1, 13)]

MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONTH_FULL = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]

# ---------------------------------------------------------------- colour
EMBER = [(0, "#1f1511"), (0.12, "#3d1710"), (0.3, "#842312"), (0.5, "#cf4a1b"), (0.68, "#f0812b"),
         (0.84, "#f9bf4f"), (1, "#fff3cf")]

def hex2rgb(h):
    h = h.lstrip("#"); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

def rgb2hex(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, round(v))) for v in c)

def ramp(t, stops=EMBER):
    t = max(0.0, min(1.0, t))
    for (a, ca), (b, cb) in zip(stops, stops[1:]):
        if t <= b:
            u = (t - a) / (b - a) if b > a else 0
            A, B = hex2rgb(ca), hex2rgb(cb)
            return rgb2hex([A[i] + (B[i] - A[i]) * u for i in range(3)])
    return stops[-1][1]

def lt(v, vmax):
    return math.log1p(max(v, 0)) / math.log1p(vmax)

# ---------------------------------------------------------------- svg helpers
def f(x):
    return f"{x:.1f}".rstrip("0").rstrip(".")

def flame(x, by, h, w, lean=0.0):
    t = x + lean * w
    return (f"M{f(t)},{f(by-h)} C{f(x+.2*w)},{f(by-.7*h)} {f(x+.52*w)},{f(by-.48*h)} {f(x+.5*w)},{f(by-.22*h)} "
            f"C{f(x+.48*w)},{f(by-.03*h)} {f(x+.28*w)},{f(by)} {f(x)},{f(by)} "
            f"C{f(x-.28*w)},{f(by)} {f(x-.48*w)},{f(by-.03*h)} {f(x-.5*w)},{f(by-.22*h)} "
            f"C{f(x-.52*w)},{f(by-.48*h)} {f(x-.16*w)},{f(by-.66*h)} {f(t)},{f(by-h)} Z")

def flame_group(x, by, h, w, lean=0.0, op=1.0):
    return (f'<g opacity="{op}"><path d="{flame(x,by,h,w,lean)}" fill="url(#gFlameOuter)" filter="url(#glow)"/>'
            f'<path d="{flame(x,by-1,h*.66,w*.62,lean*1.2)}" fill="url(#gFlameMid)"/>'
            f'<path d="{flame(x,by-2,h*.34,w*.32,lean)}" fill="#fff6d8"/></g>')

def sector(cx, cy, r0, r1, a0, a1):
    def p(r, a):
        return cx + r * math.sin(a), cy - r * math.cos(a)
    x0, y0 = p(r1, a0); x1, y1 = p(r1, a1); x2, y2 = p(r0, a1); x3, y3 = p(r0, a0)
    large = 1 if a1 - a0 > math.pi else 0
    return (f"M{f(x0)},{f(y0)} A{f(r1)},{f(r1)} 0 {large} 1 {f(x1)},{f(y1)} L{f(x2)},{f(y2)} "
            f"A{f(r0)},{f(r0)} 0 {large} 0 {f(x3)},{f(y3)} Z")

def smooth_closed(pts):
    """Catmull-Rom through closed points -> cubic bezier path."""
    n = len(pts); d = f"M{f(pts[0][0])},{f(pts[0][1])} "
    for i in range(n):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f"C{f(c1[0])},{f(c1[1])} {f(c2[0])},{f(c2[1])} {f(p2[0])},{f(p2[1])} "
    return d + "Z"

DEFS = """
<svg width="0" height="0" style="position:absolute" aria-hidden="true"><defs>
 <filter id="glow" x="-60%" y="-60%" width="220%" height="220%"><feGaussianBlur stdDeviation="2.4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
 <filter id="glowBig" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="6" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
 <filter id="soft"><feGaussianBlur stdDeviation="1.4"/></filter>
 <filter id="haze1" x="-10%" y="-30%" width="120%" height="160%"><feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="2" seed="4" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="3"/><feGaussianBlur stdDeviation="0.9"/></filter>
 <filter id="haze2" x="-10%" y="-30%" width="120%" height="160%"><feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="3" seed="7" result="n"/><feDisplacementMap in="SourceGraphic" in2="n" scale="9"/><feGaussianBlur stdDeviation="2.6"/></filter>
 <filter id="smoke" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.018 0.03" numOctaves="4" seed="11"/><feColorMatrix values="0 0 0 0 .52  0 0 0 0 .49  0 0 0 0 .47  0 0 0 1.5 -.42"/><feGaussianBlur stdDeviation="1.6"/></filter>
 <filter id="smokeThick" x="0" y="0" width="100%" height="100%"><feTurbulence type="fractalNoise" baseFrequency="0.016 0.028" numOctaves="4" seed="3"/><feColorMatrix values="0 0 0 0 .5  0 0 0 0 .47  0 0 0 0 .45  0 0 0 2.0 -.4"/><feGaussianBlur stdDeviation="1.4"/></filter>
 <radialGradient id="gEmber"><stop offset="0" stop-color="#fff6d6"/><stop offset=".25" stop-color="#ffd171"/><stop offset=".55" stop-color="#f0722a" stop-opacity=".9"/><stop offset="1" stop-color="#9b2410" stop-opacity="0"/></radialGradient>
 <radialGradient id="gEmberDim"><stop offset="0" stop-color="#f6a142"/><stop offset=".5" stop-color="#b8401a" stop-opacity=".7"/><stop offset="1" stop-color="#5c1a0e" stop-opacity="0"/></radialGradient>
 <radialGradient id="gAsh"><stop offset="0" stop-color="#9a8f88" stop-opacity=".7"/><stop offset="1" stop-color="#4b4440" stop-opacity="0"/></radialGradient>
 <radialGradient id="gHalo"><stop offset="0" stop-color="#ff9a3c" stop-opacity=".55"/><stop offset="1" stop-color="#ff6a1c" stop-opacity="0"/></radialGradient>
 <linearGradient id="gFlameOuter" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#e5481a"/><stop offset=".55" stop-color="#f27a26"/><stop offset="1" stop-color="#ffb347" stop-opacity=".85"/></linearGradient>
 <linearGradient id="gFlameMid" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="#ffb84a"/><stop offset="1" stop-color="#ffe08a"/></linearGradient>
 <linearGradient id="gBtnHeat" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1c1613"/><stop offset=".65" stop-color="#241a15"/><stop offset="1" stop-color="#5a2412"/></linearGradient>
 <linearGradient id="gBtnHot" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#24180f"/><stop offset=".5" stop-color="#4a1f0f"/><stop offset="1" stop-color="#c2481a"/></linearGradient>
 <linearGradient id="gWood" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#d8b07a"/><stop offset="1" stop-color="#a77a45"/></linearGradient>
 <linearGradient id="gFuse" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#3a302b"/><stop offset="1" stop-color="#57463d"/></linearGradient>
 <pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="5" height="5" fill="none"/><line x1="0" y1="0" x2="0" y2="5" stroke="#9c948e" stroke-width="1.4" opacity=".55"/></pattern>
</defs></svg>
"""

# ---------------------------------------------------------------- Portugal cell map
def cell_map(d, values, *, W=170, pad=6, vmax=None, rings=0, ring_scale=1.0, land="#2a221e", show_land=True,
             max_r=None, extra="", poly=None):
    ix, iy = d["cells"]["ix"], d["cells"]["iy"]
    lons = [i * .25 + .125 for i in ix]; lats = [j * .25 + .125 for j in iy]
    k = math.cos(math.radians(sum(lats) / len(lats)))
    x0, x1 = min(lons) - .2, max(lons) + .2; y0, y1 = min(lats) - .2, max(lats) + .2
    s = (W - 2 * pad) / ((x1 - x0) * k); H = (y1 - y0) * s + 2 * pad
    P = lambda lo, la: (pad + (lo - x0) * k * s, pad + (y1 - la) * s)
    cw, ch = .25 * k * s, .25 * s
    vmax = vmax or max(values) or 1
    max_r = max_r or cw * 1.6
    out = []
    if show_land:
        for lo, la in zip(lons, lats):
            x, y = P(lo, la)
            out.append(f'<rect x="{f(x-cw/2+.3)}" y="{f(y-ch/2+.3)}" width="{f(cw-.6)}" height="{f(ch-.6)}" rx=".8" fill="{land}"/>')
    order = sorted(range(len(values)), key=lambda i: values[i])
    for i in order:
        v = values[i]
        if v < .5: continue
        x, y = P(lons[i], lats[i]); r = max_r * math.sqrt(v / vmax)
        r = max(r, 1.1)
        out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r*1.9)}" fill="url(#gHalo)"/>')
        out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r)}" fill="url(#gEmber)"/>')
    top = sorted(range(len(values)), key=lambda i: -values[i])[:rings]
    for i in top:
        x, y = P(lons[i], lats[i]); r = max_r * math.sqrt(values[i] / vmax) * ring_scale
        for m, op in ((1.6, .85), (2.4, .45), (3.3, .2)):
            out.append(f'<circle cx="{f(x)}" cy="{f(y)}" r="{f(r*m)}" fill="none" stroke="#ffcf7a" stroke-width="{f(1.3/m*1.6)}" opacity="{op}"/>')
    return W, H, "".join(out) + extra, P

def cells_month(d, y, mo):
    j = idx(y, mo); return [row[j] for row in d["m"]]

# ---------------------------------------------------------------- pages
pages = []
def page(html, cls=""):
    pages.append(f'<section class="page {cls}">{html}<div class="folio"><span>Fire, made visible</span><span>{len(pages)+1:02d}</span></div></section>')

def idea(num, cat, title, pitch, see, tells, build, effort, wow, visual, note=""):
    chips = f'<div class="chips"><span class="chip">Effort · {effort}</span><span class="chip hot">Wow · {wow}</span></div>'
    left = (f'<div class="left"><div class="kicker">Idea {num:02d} · {cat}</div><h2>{title}</h2><p class="pitch">{pitch}</p>'
            f'<h4>What you see</h4><p>{see}</p><h4>What it tells you</h4><p>{tells}</p>'
            f'<h4>How to build it</h4><p class="build">{build}</p>{chips}{note}</div>')
    page(left + f'<div class="right">{visual}</div>', "idea")

# ---------- cover
def tree_rings(tot, *, R=150, r0=26, cx=None, cy=None, labels=True, years=range(2001, 2026), vmax=None, gap=.012, mark=True):
    cx = cx if cx is not None else R + 34; cy = cy if cy is not None else R + 34
    yl = list(years); dr = (R - r0) / len(yl)
    vmax = vmax or max(tot)
    out = []
    for k, y in enumerate(yl):
        a_r0 = r0 + k * dr + .35; a_r1 = r0 + (k + 1) * dr - .35
        for mo in range(1, 13):
            v = tot[idx(y, mo)]; a0 = (mo - 1) / 12 * 2 * math.pi + gap; a1 = mo / 12 * 2 * math.pi - gap
            t = lt(v, vmax)
            out.append(f'<path d="{sector(cx,cy,a_r0,a_r1,a0,a1)}" fill="{ramp(t)}"/>')
    glow = "".join(o for o in out)
    s = f'<g filter="url(#glow)">{glow}</g>'
    if mark:
        k22 = yl.index(2022) if 2022 in yl else None
        if k22 is not None:
            rr = r0 + k22 * dr
            s += f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{f(rr)}" fill="none" stroke="#9fd3ff" stroke-width=".9" stroke-dasharray="2 2.5" opacity=".85"/>'
    if labels:
        for mo in range(12):
            a = (mo + .5) / 12 * 2 * math.pi
            x = cx + (R + 12) * math.sin(a); y = cy - (R + 12) * math.cos(a) + 3.2
            s += f'<text x="{f(x)}" y="{f(y)}" text-anchor="middle" class="svgl">{MON[mo]}</text>'
    return s

cover_rings = tree_rings(PT_TOT, R=200, r0=34, cx=240, cy=240, labels=True)
page(f"""
<div class="cover-wrap">
  <div class="cover-text">
    <div class="kicker light">Creative directions · interface &amp; motion</div>
    <h1>Fire,<br>made visible</h1>
    <p class="lede">Ideas for a 25-year fire calendar people actually <em>feel</em>. Embers that ignite, buttons that burn,
    tree rings that hold fire scars, smoke that shows doubt.</p>
    <p class="cover-note">Every chart in this booklet is drawn from real satellite fire records for Portugal and Lebanon,
    December 2000 to December 2025. Interface mockups use example numbers.</p>
    <div class="cover-legend"><span class="sw" style="background:{ramp(.15)}"></span>quiet month
      <span class="sw" style="background:{ramp(.55)}"></span>active
      <span class="sw" style="background:{ramp(.95)}"></span>extreme</div>
  </div>
  <div class="cover-art"><svg viewBox="0 0 480 480">{cover_rings}
    <text x="240" y="236" text-anchor="middle" class="svgc">Portugal</text>
    <text x="240" y="250" text-anchor="middle" class="svgs">2001 at the centre</text>
    <text x="240" y="262" text-anchor="middle" class="svgs">2025 on the rim</text></svg>
    <div class="cap light">Twenty-five years of Portugal's fire, one ring per year, one wedge per month. Idea 03.</div></div>
</div>""", "cover")

# ---------- principles + index
IDEAS = [
    ("Ignition rings", "Map", "Each place lights up with a spark, a shock-ring and an ember sized by its fire.", True),
    ("Burning buttons", "Controls", "Buttons heat on hover; on press a fuse runs round the edge.", True),
    ("Fire tree rings", "Calendar", "Years as tree rings, months as wedges: fire scars you can read.", True),
    ("The ember quilt", "Calendar", "The month × year grid as glowing tiles; flare-ups throw sparks.", False),
    ("Draw a firebreak", "Drawing", "Your pen is a torch; closing the shape lights the area up.", True),
    ("Two eyes, one fire", "Explainer", "Show why old and new satellites disagree, then translate.", True),
    ("The ghost flame", "This month", "This month's flame beside the ghost of a normal one.", False),
    ("Smoke means unsure", "Trust", "Uncertain numbers sit in smoke; certain ones are crisp.", False),
    ("25 years in 25 seconds", "Playback", "Press play: the map breathes with every fire season.", False),
    ("Fire fingerprints", "Compare", "Every place has a seasonal shape. Compare them at a glance.", False),
    ("Story mode", "Guided", "A guided tour of the biggest months in the record.", False),
    ("Small delights", "Details", "Loading fuse, cold-ground empty state, ember tooltips…", False),
]
idx_rows = "".join(
    f'<div class="ix-row"><span class="ix-n">{i+1:02d}</span><span class="ix-t">{t}{" <b class=star>★</b>" if s else ""}</span>'
    f'<span class="ix-c">{c}</span><span class="ix-d">{dsc}</span></div>' for i, (t, c, dsc, s) in enumerate(IDEAS))

def mini_icon(kind):
    if kind == "ember":
        return '<svg viewBox="0 0 60 60"><circle cx="30" cy="30" r="24" fill="url(#gHalo)"/><circle cx="30" cy="30" r="12" fill="url(#gEmber)"/></svg>'
    if kind == "ash":
        return '<svg viewBox="0 0 60 60"><circle cx="30" cy="30" r="16" fill="url(#gAsh)"/><circle cx="30" cy="30" r="16" fill="none" stroke="#8a807a" stroke-width="1.2" stroke-dasharray="2 3"/><circle cx="22" cy="20" r="1.2" fill="#a59c96"/><circle cx="40" cy="38" r="1" fill="#a59c96"/></svg>'
    return '<svg viewBox="0 0 60 60"><rect width="60" height="60" fill="none"/><rect x="2" y="6" width="56" height="48" filter="url(#smoke)" opacity=".9"/><text x="30" y="37" text-anchor="middle" font-size="16" font-weight="700" fill="#f3e6d8" filter="url(#haze1)">412</text></svg>'

page(f"""
<div class="two">
 <div class="col-a">
  <div class="kicker">The big idea</div>
  <h2>Treat fire as a material, not a colour</h2>
  <p>Most fire maps paint red dots on a grey map. Here the interface itself behaves like fire. It heats, glows,
  burns, cools to ash and gives off smoke, and each of those behaviours stands for one fact in the data.
  People read it in a second, without a legend.</p>
  <div class="mat">
   <div class="matc">{mini_icon('ember')}<div><b>Ember = activity</b><span>Brighter and bigger means more burning. Glow is never decoration.</span></div></div>
   <div class="matc">{mini_icon('ash')}<div><b>Ash = the past, or below normal</b><span>Months that are over, or quieter than usual, cool to grey.</span></div></div>
   <div class="matc">{mini_icon('smoke')}<div><b>Smoke = doubt</b><span>The less sure a number is, the more smoke sits over it.</span></div></div>
  </div>
  <h4>Four rules for every idea</h4>
  <ol class="rules">
   <li><b>Every animation carries a fact.</b> If the motion means nothing, cut it.</li>
   <li><b>Calm by default.</b> Motion plays once when something changes, then settles. Nothing loops forever.</li>
   <li><b>Never colour alone.</b> Every colour has a shape, number or word beside it.</li>
   <li><b>Respect "reduce motion".</b> If the device asks for less motion, every effect becomes a still image.</li>
  </ol>
 </div>
 <div class="col-b">
  <div class="kicker">Twelve ideas · <b class="star">★</b> the five to build first</div>
  <div class="ix">{idx_rows}</div>
 </div>
</div>""")

# ---------- idea 1: ignition rings
def life_frame(stage):
    c = 45
    if stage == 0:
        g = (f'<circle cx="{c}" cy="{c}" r="10" fill="url(#gHalo)"/><circle cx="{c}" cy="{c}" r="2.6" fill="#fff8e0" filter="url(#glow)"/>'
             + "".join(f'<line x1="{f(c+6*math.cos(a))}" y1="{f(c+6*math.sin(a))}" x2="{f(c+11*math.cos(a))}" y2="{f(c+11*math.sin(a))}" stroke="#ffd98a" stroke-width="1" stroke-linecap="round"/>' for a in [.3, 1.4, 2.6, 3.7, 5.1]))
    elif stage == 1:
        g = (f'<circle cx="{c}" cy="{c}" r="20" fill="none" stroke="#ffd27a" stroke-width="3" filter="url(#glow)" opacity=".95"/>'
             f'<circle cx="{c}" cy="{c}" r="6" fill="url(#gEmber)"/>')
    elif stage == 2:
        g = (f'<circle cx="{c}" cy="{c}" r="36" fill="none" stroke="#ffcf7a" stroke-width="1.2" opacity=".35"/>'
             f'<circle cx="{c}" cy="{c}" r="28" fill="none" stroke="#ffcf7a" stroke-width="2" opacity=".6"/>'
             f'<circle cx="{c}" cy="{c}" r="24" fill="url(#gHalo)"/><circle cx="{c}" cy="{c}" r="15" fill="url(#gEmber)" filter="url(#glow)"/>')
    elif stage == 3:
        g = (f'<circle cx="{c}" cy="{c}" r="26" fill="url(#gHalo)"/><circle cx="{c}" cy="{c}" r="14" fill="url(#gEmber)"/>'
             f'<circle cx="{c}" cy="{c}" r="14" fill="none" stroke="#ffcf7a" stroke-width=".8" stroke-dasharray="1.5 2.5" opacity=".8"/>')
    else:
        g = (f'<circle cx="{c}" cy="{c}" r="14" fill="url(#gAsh)"/><circle cx="{c}" cy="{c}" r="14" fill="none" stroke="#8a807a" stroke-width="1" stroke-dasharray="2 2.6"/>'
             f'<circle cx="{c}" cy="{c}" r="3" fill="#c0531f" opacity=".7"/>')
    return f'<svg viewBox="0 0 90 90">{g}</svg>'

life_caps = [("0.0 s", "Spark"), ("0.2 s", "Shock-ring"), ("0.5 s", "Flare"), ("1.0 s", "Settles: size = burning days"), ("later", "Past months cool to ash")]
strip = "".join(f'<div class="fr">{life_frame(i)}<div class="frc"><b>{a}</b>{b}</div></div>' for i, (a, b) in enumerate(life_caps))
vals = cells_month(PT, 2025, 8)
W, H, body, _ = cell_map(PT, vals, W=230, rings=5, max_r=9)
idea(1, "Map", "Ignition rings",
     "Instead of static dots, each place <em>ignites</em> when its month appears: a spark, a shock-ring, a flare, then a steady ember whose size is its fire.",
     "Pick a month and the map lights up in order, biggest fires first, like a ripple of ignitions across the country. "
     "Each ember settles to a size set by its burning days. When you move on, past months fade to grey ash rings, so you can still see where fire was.",
     "Where the fire was, how much, and in what order of size, before you read a single number. "
     "The ring colour can also say <em>compared with normal</em>: gold for above normal, pale grey-blue for below.",
     "A MapLibre circle layer with radius and opacity driven by a 1-second animation clock. Sort cells by size to stagger the start times by 15 ms each. "
     "The shock-ring is a second circle layer whose radius grows while its opacity falls.",
     "medium", "very high",
     f'<div class="fstrip">{strip}</div><div class="mapbox"><svg viewBox="0 0 {f(W)} {f(H)}" class="map">{body}</svg>'
     f'<div class="mapside"><div class="big">August 2025</div><p>Portugal, real data. The five largest embers still carry their shock-rings: '
     f'the first places to ignite when the month opens.</p><p class="small">Ember area ∝ burning days in each ¼° square. Faint squares are the region\'s land grid.</p></div></div>')

# ---------- idea 2: burning buttons
def rr_point(x, y, w, h, t):
    per = 2 * (w + h); d = t * per
    if d < w: return x + d, y
    d -= w
    if d < h: return x + w, y + d
    d -= h
    if d < w: return x + w - d, y + h
    d -= w; return x, y + h - d

def button(state, label, x=10, y=18, w=160, h=42):
    rect = f'M{x+8},{y} H{x+w-8} Q{x+w},{y} {x+w},{y+8} V{y+h-8} Q{x+w},{y+h} {x+w-8},{y+h} H{x+8} Q{x},{y+h} {x},{y+h-8} V{y+8} Q{x},{y} {x+8},{y} Z'
    txt = f'<text x="{x+w/2}" y="{y+h/2+4.5}" text-anchor="middle" class="btnt">{label}</text>'
    if state == "rest":
        return f'<path d="{rect}" fill="url(#gBtnHeat)" stroke="#4d3226" stroke-width="1.2"/>' + txt
    if state == "hover":
        shimmer = "".join(f'<path d="M{x+w*a},{y-3} q3,-4 0,-8 q-3,-4 0,-8" fill="none" stroke="#f0a050" stroke-width=".9" opacity=".5"/>' for a in (.3, .5, .7))
        return shimmer + f'<path d="{rect}" fill="url(#gBtnHot)" stroke="#f08a33" stroke-width="1.6" filter="url(#glow)"/>' + txt
    if state == "press":
        hx, hy = rr_point(x, y, w, h, .58)
        return (f'<path d="{rect}" fill="url(#gBtnHot)" stroke="#e8a46a" stroke-width="1.6" opacity=".95"/>'
                f'<path d="{rect}" fill="none" stroke="#2b221e" stroke-width="3" pathLength="100" stroke-dasharray="58 100"/>'
                f'<circle cx="{f(hx)}" cy="{f(hy)}" r="9" fill="url(#gHalo)"/><circle cx="{f(hx)}" cy="{f(hy)}" r="3.2" fill="#fff4c8" filter="url(#glowBig)"/>'
                + "".join(f'<circle cx="{f(hx+dx)}" cy="{f(hy+dy)}" r="1" fill="#ffd27a"/>' for dx, dy in ((6, -7), (-5, -9), (9, 3), (-8, 4)))
                + txt)
    # done
    wisp = f'<path d="M{x+w-22},{y-2} c-5,-6 6,-9 0,-15 c-5,-5 4,-9 1,-14" fill="none" stroke="#9b918b" stroke-width="2.2" opacity=".45" filter="url(#soft)"/>'
    flecks = "".join(f'<circle cx="{f(px)}" cy="{f(py)}" r="1.3" fill="#ff8a3a" filter="url(#glow)"/>' for px, py in ((x + 30, y + h), (x + w, y + 14), (x + 92, y)))
    return (wisp + f'<path d="{rect}" fill="#1c1715" stroke="#3a2f2a" stroke-width="2.6"/>' + flecks
            + f'<text x="{x+w/2}" y="{y+h/2+4.5}" text-anchor="middle" class="btnt">✓ {label}</text>')

states = [("rest", "At rest: a cooled coal"), ("hover", "Hover: heat rises"), ("press", "Press: a fuse runs the edge"), ("done", "Done: charred, one wisp")]
btns = "".join(f'<div class="bt"><svg viewBox="0 0 180 72">{button(s, "Show calendar")}</svg><div class="frc">{c}</div></div>' for s, c in states)

match_off = ('<svg viewBox="0 0 120 54"><rect x="10" y="20" width="96" height="16" rx="8" fill="#2a221e" stroke="#4a3a32"/>'
             '<rect x="18" y="25.5" width="44" height="5" rx="2" fill="url(#gWood)"/><circle cx="20" cy="28" r="7" fill="#7a2418" stroke="#4a140c"/>'
             '<text x="60" y="50" text-anchor="middle" class="svgs">off</text></svg>')
match_on = ('<svg viewBox="0 0 120 54"><rect x="10" y="20" width="96" height="16" rx="8" fill="#3a1d12" stroke="#d0652a" filter="url(#glow)"/>'
            '<rect x="52" y="25.5" width="44" height="5" rx="2" fill="url(#gWood)"/><circle cx="96" cy="28" r="7" fill="#c2401a"/>'
            + flame_group(97, 26, 22, 11, .1) + '<text x="60" y="50" text-anchor="middle" class="svgs">on: the match is lit</text></svg>')
unit_sw = ('<svg viewBox="0 0 250 64"><rect x="6" y="12" width="238" height="38" rx="19" fill="#1a1411" stroke="#4a3a32"/>'
           '<rect x="9" y="15" width="120" height="32" rx="16" fill="url(#gBtnHot)" stroke="#f08a33" filter="url(#glow)"/>'
           '<text x="69" y="35.5" text-anchor="middle" class="btnt">Burning days</text><text x="186" y="35.5" text-anchor="middle" class="btnt dim">Hotspots</text>'
           '<path d="M150,31 h-12" stroke="#f0a050" stroke-width="1.2" stroke-dasharray="2 2"/><text x="125" y="62" text-anchor="middle" class="svgs">the heat slides to your choice</text></svg>')
emb = "".join(f'<circle cx="{f(cx)}" cy="{f(cy)}" r="{r}" fill="#ffb24a" opacity="{o}" filter="url(#glow)"/>' for cx, cy, r, o in
              ((132, 18, 1.8, .9), (140, 30, 1.4, .8), (128, 40, 1.2, .6), (146, 12, 1, .7), (137, 50, 1.6, .9)))
dl = ('<svg viewBox="0 0 250 72"><rect x="6" y="16" width="112" height="38" rx="9" fill="url(#gBtnHot)" stroke="#f08a33"/>'
      '<text x="62" y="39.5" text-anchor="middle" class="btnt">Download CSV</text>' + emb +
      '<path d="M168,10 h36 l12,12 v40 h-48 Z" fill="#241c18" stroke="#a46a3e"/><path d="M204,10 v12 h12" fill="none" stroke="#a46a3e"/>'
      '<text x="192" y="46" text-anchor="middle" class="svgc" style="font-size:11px">CSV</text>'
      '<circle cx="192" cy="58" r="10" fill="url(#gHalo)"/><text x="125" y="70" text-anchor="middle" class="svgs">embers fall into the file</text></svg>')
idea(2, "Controls", "Burning buttons",
     "Controls feel like hot coals. Hover heats them, and pressing one sends a little fuse burning round its edge. When the job is done the button is charred, with one wisp of smoke.",
     "Four states of the same button, plus a family built on it. A <b>match-stick toggle</b> that lights when switched on. "
     "A <b>unit switch</b> where the glow slides to the chosen side. A <b>download button</b> that drops embers into the file.",
     "The fuse doubles as a progress bar. While the calendar loads, the fuse burns; when it completes the loop, the data is ready. "
     "The charred edge stays as a quiet reminder of what you have already looked at.",
     "Pure CSS: a <code>conic-gradient</code> border animated with <code>@property</code> for the fuse, "
     "<code>box-shadow</code> for the heat, and one tiny SVG for the smoke wisp. Keyboard focus uses the same glow ring, so focus is easy to see.",
     "small", "high",
     f'<div class="btgrid">{btns}</div><div class="family"><div><h5>Match-stick toggle</h5><div class="pair">{match_off}{match_on}</div></div>'
     f'<div><h5>Unit switch</h5>{unit_sw}</div><div><h5>Download</h5>{dl}</div></div>')

# ---------- idea 3: tree rings
pt_r = tree_rings(PT_TOT, R=150, r0=24, cx=190, cy=190)
lb_r = tree_rings(LB_TOT, R=82, r0=14, cx=110, cy=110)
k17 = 2017 - 2001; dr = (150 - 24) / 25
oct_a = (9.5) / 12 * 2 * math.pi; rr = 24 + (k17 + .5) * dr
ax, ay = 190 + rr * math.sin(oct_a), 190 - rr * math.cos(oct_a)
ann = (f'<circle cx="{f(ax)}" cy="{f(ay)}" r="7" fill="none" stroke="#fff" stroke-width="1.2"/>'
       f'<line x1="{f(ax-7)}" y1="{f(ay)}" x2="22" y2="{f(ay-46)}" stroke="#fff" stroke-width=".7"/>'
       f'<text x="4" y="{f(ay-60)}" class="svga">October 2017</text><text x="4" y="{f(ay-50)}" class="svgs">fire after the season</text>')
idea(3, "Calendar", "Fire tree rings",
     "A tree records every fire in its rings. Here each year is a ring and each month a wedge, so the whole 25-year record becomes one object you can read at a glance.",
     "A radial calendar, 2001 at the centre and 2025 on the rim, with January at the top running clockwise. Bright wedges are fire scars. "
     "The summer arc glows every year, and the outliers jump out: Portugal's October 2017 burns where October is usually cool. "
     "A dashed blue ring marks 2022, where the newer satellite takes over, and nothing jumps there because the record is harmonized.",
     "Seasonality (where the bright arc sits), trends (are outer rings brighter?) and one-off disasters, all in one shape. "
     "Hover a ring to see its year; hover a wedge to light up that month across all 25 years.",
     "One SVG with 300 path wedges (25 × 12), coloured from the same scale as the grid calendar. "
     "It offers the same data as the table view, with a toggle between them. It grows ring by ring on first load (about 1.5 seconds).",
     "medium", "very high",
     f'<div class="rings2"><div><svg viewBox="0 0 380 380">{pt_r}{ann}<text x="190" y="188" text-anchor="middle" class="svgc">Portugal</text><text x="190" y="200" text-anchor="middle" class="svgs">burning days</text></svg></div>'
     f'<div class="rside"><svg viewBox="0 0 220 220">{lb_r}<text x="110" y="113" text-anchor="middle" class="svgc" style="font-size:9px">Lebanon</text></svg>'
     f'<p class="small">Lebanon has a different clock: its fire arc sits in <b>September–October</b>, after the harvest, while Portugal\'s peaks in <b>August</b>. The shapes alone tell the story.</p>'
     f'<div class="leg">{"".join(f"<span style=background:{ramp(t)}></span>" for t in [i/10 for i in range(11)])}</div><div class="legl"><span>none</span><span>record month</span></div>'
     f'<p class="small"><span class="dash"></span> 2022: newer satellite, same scale</p></div></div>')

# ---------- idea 4: ember quilt
def quilt(tot, *, cw=13.2, ch=14.5, vmax=None):
    vmax = vmax or max(tot); out = []; ox, oy = 30, 14
    for c, y in enumerate(range(2001, 2026)):
        if y % 4 == 1 or y == 2025:
            out.append(f'<text x="{f(ox+c*cw+cw/2)}" y="{f(oy+12*ch+11)}" text-anchor="middle" class="svgs">{y}</text>')
        for mo in range(1, 13):
            v = tot[idx(y, mo)]; x = ox + c * cw; yy = oy + (mo - 1) * ch
            out.append(f'<rect x="{f(x+.6)}" y="{f(yy+.6)}" width="{f(cw-1.2)}" height="{f(ch-1.2)}" rx="2" fill="{ramp(lt(v,vmax))}"/>')
            med = typical(tot, y, mo)
            if med >= 20 and v >= 2.5 * med:
                cx, cy = x + cw / 2, yy + ch / 2
                out.append(f'<rect x="{f(x+.6)}" y="{f(yy+.6)}" width="{f(cw-1.2)}" height="{f(ch-1.2)}" rx="2" fill="none" stroke="#fff3c4" stroke-width="1.1" filter="url(#glow)"/>')
                out.append(f'<text x="{f(cx)}" y="{f(cy+3)}" text-anchor="middle" class="tri">▲</text>')
            elif med >= 20 and v <= .35 * med:
                cx, cy = x + cw / 2, yy + ch / 2
                out.append(f'<text x="{f(cx)}" y="{f(cy+3)}" text-anchor="middle" class="tri ash">▽</text>')
    for mo in range(12):
        out.append(f'<text x="{ox-4}" y="{f(oy+mo*ch+ch/2+3)}" text-anchor="end" class="svgs">{MON[mo]}</text>')
    x22 = ox + (2022 - 2001) * cw
    out.append(f'<line x1="{f(x22)}" y1="{oy-6}" x2="{f(x22)}" y2="{f(oy+12*ch+2)}" stroke="#9fd3ff" stroke-width=".9" stroke-dasharray="2 2"/>')
    return "".join(out), ox + 25 * cw + 6, oy + 12 * ch + 18

q, qw, qh = quilt(PT_TOT)
idea(4, "Calendar", "The ember quilt",
     "The month × year calendar, but every tile is a little ember. Months far above normal throw sparks; months far below normal have cooled to ash.",
     "A grid of 25 years by 12 months. Tile brightness is the amount of fire. "
     "A <b>▲ with a hot outline</b> marks a month at least 2.5× its normal; a <b>▽ in ash grey</b> marks one at a third of normal or less. "
     "Hovering a tile draws a soft crosshair of heat along its row and column.",
     "The calendar the brief asks for, with the anomalies already circled for you. Real data: Portugal's 2003, 2005 and 2017 seasons, and the dead-quiet summer of 2014.",
     "A CSS grid of 300 buttons (keyboard reachable), each with a background from the colour scale. Sparks are a 3-frame sprite that plays once on load and on hover only.",
     "small", "high",
     f'<svg viewBox="0 0 {f(qw)} {f(qh)}" class="quilt">{q}</svg>'
     f'<div class="qleg"><span class="lg"><span class="tri">▲</span> ≥ 2.5× a normal month</span><span class="lg"><span class="tri ash">▽</span> ≤ ⅓ of normal</span>'
     f'<span class="lg"><span class="dash"></span> newer satellite from 2022</span><span class="lg">Normal = median of the same month in other years, 2003–2025. Marked only where a normal month has 20+ burning days, to keep the example readable.</span></div>')

# ---------- idea 5: firebreak
POLY = [(-8.75, 40.55), (-7.75, 40.95), (-7.15, 40.25), (-7.55, 39.55), (-8.45, 39.4), (-8.95, 39.9)]
def pip(x, y, poly):
    c = False; n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]; x2, y2 = poly[(i + 1) % n]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1: c = not c
    return c

def poly_point(pts, t):
    segs = [(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))]
    L = [math.dist(a, b) for a, b in segs]; d = t * sum(L)
    for (a, b), l in zip(segs, L):
        if d <= l: u = d / l; return a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u
        d -= l
    return pts[0]

v17 = cells_month(PT, 2017, 8)
ix, iy = PT["cells"]["ix"], PT["cells"]["iy"]
inside = [pip(i * .25 + .125, j * .25 + .125, POLY) for i, j in zip(ix, iy)]

def fb_frame(stage):
    vals = [v if (stage == 3 and inside[k]) else 0 for k, v in enumerate(v17)]
    W, H, body, P = cell_map(PT, vals, W=128, max_r=7, vmax=max(v17))
    pts = [P(lo, la) for lo, la in POLY]
    d = "M" + " L".join(f"{f(x)},{f(y)}" for x, y in pts) + " Z"
    extra = ""
    if stage == 0:
        x, y = pts[0]
        extra = f'<circle cx="{f(x)}" cy="{f(y)}" r="8" fill="url(#gHalo)"/><circle cx="{f(x)}" cy="{f(y)}" r="2.4" fill="#fff4c8" filter="url(#glowBig)"/>'
    elif stage == 1:
        hx, hy = poly_point(pts, .62)
        extra = (f'<path d="{d}" fill="none" stroke="#3b302b" stroke-width="2.2" pathLength="100" stroke-dasharray="0 100" />'
                 f'<path d="{d}" fill="none" stroke="#5a4036" stroke-width="2" pathLength="100" stroke-dasharray="50 100"/>'
                 f'<path d="{d}" fill="none" stroke="#ff9a3c" stroke-width="2.2" pathLength="100" stroke-dasharray="0 50 12 100" filter="url(#glow)"/>'
                 f'<circle cx="{f(hx)}" cy="{f(hy)}" r="8" fill="url(#gHalo)"/><circle cx="{f(hx)}" cy="{f(hy)}" r="2.4" fill="#fff4c8" filter="url(#glowBig)"/>')
    elif stage == 2:
        extra = (f'<path d="{d}" fill="#ff7a2a" fill-opacity=".07" stroke="#ffb04a" stroke-width="2.4" filter="url(#glowBig)"/>'
                 + "".join(f'<circle cx="{f(poly_point(pts, t)[0])}" cy="{f(poly_point(pts, t)[1])}" r="1.6" fill="#fff0b8"/>' for t in (.05, .21, .37, .55, .7, .88)))
    else:
        extra = f'<path d="{d}" fill="none" stroke="#e98a43" stroke-width="1.1" stroke-dasharray="3 2" opacity=".8"/>'
    yc = P(-8, 38.9)[1]
    return f'<svg viewBox="0 0 {f(W)} {f(yc)}">{body}{extra}</svg>'

fb_caps = [("1", "Your cursor is a torch"), ("2", "The line burns behind it, glowing then cooling"), ("3", "Close the shape: fire runs the edge"), ("4", "Inside lights up with its real fires")]
fb = "".join(f'<div class="fbf">{fb_frame(i)}<div class="frc"><b>{a}</b> {b}</div></div>' for i, (a, b) in enumerate(fb_caps))
tot_in = sum(v for v, k in zip(v17, inside) if k)
idea(5, "Drawing", "Draw a firebreak",
     "Drawing your own area is the heart of the tool, so make it an event. The pen is a torch, the line is a burning fuse, and closing the shape sets the area alight.",
     "While you draw, a bright head moves with your cursor and the trail behind it cools from orange to charcoal. "
     "When the loop closes, a ring of fire races once round the edge, and then only the fires <em>inside</em> your shape ignite (idea 01). "
     "The calendar for your area slides in from the side.",
     f"Exactly which area you are asking about, and that the answer belongs to it. Frame 4 is real: August 2017 inside this shape, "
     f"{round(tot_in):,} burning days.",
     "Use terra-draw's freehand or polygon mode as the base. The trail is the drawn line with a gradient set along its length; the edge race is a dash-offset animation on the closed polygon. "
     "A circle (centre + radius) gets the same treatment, with fire running round the rim.",
     "medium", "very high", f'<div class="fbstrip">{fb}</div>')

# ---------- idea 6: two eyes
def pixel_eye(fine):
    out = ['<rect x="0" y="0" width="150" height="150" rx="10" fill="#14100e"/>']
    blob = "M48,62 C58,40 92,36 104,54 C116,70 108,96 88,104 C68,112 40,98 42,80 C43,72 44,68 48,62 Z"
    n = 12 if fine else 4; s = 150 / n
    lit = 0
    for i in range(n):
        for j in range(n):
            cx, cy = i * s + s / 2, j * s + s / 2
            # crude inside test against the blob's ellipse
            inside_b = ((cx - 76) / 33) ** 2 + ((cy - 72) / 34) ** 2 < 1
            hot = inside_b and (fine or ((cx - 76) / 33) ** 2 + ((cy - 72) / 34) ** 2 < .6)
            if hot: lit += 1
            out.append(f'<rect x="{f(i*s+.8)}" y="{f(j*s+.8)}" width="{f(s-1.6)}" height="{f(s-1.6)}" rx="{1.5 if fine else 4}" '
                       f'fill="{"#f2832c" if hot else "none"}" fill-opacity="{.85 if hot else 0}" stroke="#3a2e28" stroke-width=".8"/>')
    out.insert(1, f'<path d="{blob}" fill="#ff5a1c" opacity=".35" filter="url(#glowBig)"/>')
    return "".join(out), lit

old, n_old = pixel_eye(False); new, n_new = pixel_eye(True)

def line_chart(tot, naive, *, W=420, H=200):
    ys = list(range(2001, 2026))
    a = [sum(tot[idx(y, m)] for m in range(1, 13)) for y in ys]
    b = [sum(naive[idx(y, m)] for m in range(1, 13)) for y in ys]
    vmax = max(b) * 1.08; ox, oy, w, h = 34, 14, W - 50, H - 40
    X = lambda i: ox + i / (len(ys) - 1) * w; Y = lambda v: oy + h - v / vmax * h
    pa = " ".join(f"{f(X(i))},{f(Y(v))}" for i, v in enumerate(a)); pb = " ".join(f"{f(X(i))},{f(Y(v))}" for i, v in enumerate(b))
    x12 = X(ys.index(2012))
    g = [f'<rect x="{f(x12)}" y="{oy}" width="{f(ox+w-x12)}" height="{h}" fill="#ff6a1c" opacity=".06"/>']
    for t in (0, 200, 400, 600, 800):
        if t < vmax:
            g.append(f'<line x1="{ox}" x2="{ox+w}" y1="{f(Y(t))}" y2="{f(Y(t))}" stroke="#3a2f2a" stroke-width=".6"/><text x="{ox-5}" y="{f(Y(t)+3)}" text-anchor="end" class="svgs">{t}</text>')
    for i, y in enumerate(ys):
        if y in (2001, 2006, 2012, 2018, 2025):
            g.append(f'<text x="{f(X(i))}" y="{oy+h+13}" text-anchor="middle" class="svgs">{y}</text>')
    g.append(f'<polyline points="{pb}" fill="none" stroke="#ff6a5c" stroke-width="1.8" stroke-dasharray="4 3"/>')
    g.append(f'<polyline points="{pa}" fill="none" stroke="#ffc35a" stroke-width="2.6" filter="url(#glow)"/>')
    i12 = ys.index(2012)
    g.append(f'<text x="{f(x12+6)}" y="{oy+12}" class="svga" style="fill:#ff8a7c">raw counts: ×{b[i12]/a[i12]:.0f} overnight in 2012</text>')
    g.append(f'<text x="{f(x12+6)}" y="{oy+23}" class="svgs">the newer, sharper eye switches on, not more fire</text>')
    g.append(f'<text x="{f(X(len(ys)-1))}" y="{f(Y(a[-1])+16)}" text-anchor="end" class="svga" style="fill:#ffc35a">translated: one steady scale</text>')
    return f'<svg viewBox="0 0 {W} {H}">{"".join(g)}</svg>'

idea(6, "Explainer", "Two eyes, one fire",
     "The whole problem in one picture: the old satellite eye sees in big blocks, the new one in fine detail, so the same fire gets counted very differently. Then show the fix.",
     f"Left: one fire seen by the older eye (big pixels, {n_old} lit) and by the newer eye (small pixels, {n_new} lit). "
     "A <b>Translate</b> switch below the chart animates the jagged raw line folding down onto the steady translated line. "
     "A magnifier lens you can drag over the map shows both eyes' view of the same spot.",
     "Why a raw count lies, and why the calendar can be trusted across 25 years. Real data, Lebanon: raw counts jump about sevenfold in 2012 when the sharper eye arrives. The translated record does not.",
     "The pixel grids are a small SVG; the chart is the app's own naive and harmonized records (both are already in the data). "
     "The morph interpolates between the two lines over 1.2 seconds. The lens is a circular clip mask over two stacked map layers.",
     "medium", "high (and it explains the science)",
     f'<div class="eyes"><div><h5>Older eye · 1 km pixels</h5><svg viewBox="0 0 150 150">{old}</svg><div class="frc">{n_old} squares lit</div></div>'
     f'<div class="eq">same<br>fire</div><div><h5>Newer eye · 375 m pixels</h5><svg viewBox="0 0 150 150">{new}</svg><div class="frc">{n_new} squares lit</div></div></div>'
     f'<div class="chartbox"><h5>Lebanon, burning days per year</h5>{line_chart(LB_TOT, LB_NAIVE)}'
     f'<div class="switchrow"><span class="pill-sw"><span class="knob"></span></span> <b>Translate</b> <span class="small">· raw <span style="color:#ff8a7c">- - -</span> vs translated <span style="color:#ffc35a">———</span></span></div></div>')

# ---------- idea 7: ghost flame
augs = {y: PT_TOT[idx(y, 8)] for y in range(2003, 2026)}
quiet_y = min(augs, key=augs.get); big_y = 2025
normal_y = min(augs, key=lambda y: abs(augs[y] - typical(PT_TOT, y, 8)) if y not in (quiet_y, big_y) else 1e9)
def ghost(y, mo, label):
    v = PT_TOT[idx(y, mo)]; med = typical(PT_TOT, y, mo)
    vals = sorted(PT_TOT[idx(yy, mo)] for yy in range(2003, 2026) if yy != y)
    q1, q3 = vals[len(vals) // 4], vals[(3 * len(vals)) // 4]
    top = max(augs.values()); Hmax = 150; by = 175
    hh = lambda x: Hmax * math.sqrt(x / top)
    y3, y1 = by - hh(q3), by - hh(q1)
    band = (f'<path d="M24,{f(y3)} h-4 V{f(y1)} h4" fill="none" stroke="#a8998e" stroke-width=".9"/>'
            f'<text x="17" y="{f((y1+y3)/2+2.5)}" text-anchor="middle" class="svgs" transform="rotate(-90 17 {f((y1+y3)/2)})">usual</text>')
    gh = f'<path d="{flame(70,by,hh(med),hh(med)*.55+8)}" fill="none" stroke="#d8cfc8" stroke-width="1.3" stroke-dasharray="3 3" opacity=".8"/>'
    fl = flame_group(70, by, hh(v), hh(v) * .55 + 8, .04)
    ratio = v / med if med else 0
    word = f"{ratio:.1f}× a normal {MONTH_FULL[mo-1]}" if ratio >= 1.15 else (f"{(1-ratio)*100:.0f}% below normal" if ratio <= .85 else "about normal")
    return (f'<div class="gf"><svg viewBox="0 0 140 190">{band}{fl}{gh}<line x1="14" x2="126" y1="{by}" y2="{by}" stroke="#4a3a32"/></svg>'
            f'<div class="gfc"><b>{label}</b><span class="gfn">{round(v):,}</span><span class="small">burning days · normal {round(med):,}</span><span class="gfw">{word}</span></div></div>')
gf = ghost(quiet_y, 8, f"August {quiet_y}") + ghost(normal_y, 8, f"August {normal_y}") + ghost(big_y, 8, f"August {big_y}")
idea(7, "This month", "The ghost flame",
     "The brief asks for <em>this month against the historical median</em>. Show it as two flames: the real one, and the dashed ghost of a normal year standing behind it.",
     "A living flame whose height is this month's fire, with a pale dashed ghost flame at the height of a normal month. A bracket at the side marks the usual range "
     "(the middle half of past years). Taller than the ghost: above normal. Shorter: below. One plain sentence underneath says by how much.",
     "Current month vs normal, with zero chart literacy needed. Real Portugal Augusts: the quietest, a typical one, and 2025.",
     "An SVG flame path (three nested shapes) whose height eases to the value. A gentle 2–3 Hz flicker (scale ±2%), switched off under reduced motion. Height uses a square-root scale so huge months still fit.",
     "small", "high",
     f'<div class="gfrow">{gf}</div><p class="small center">Dashed outline = the ghost of a normal August (median of other years). Bracket = the usual range (middle half of past Augusts).</p>')

# ---------- idea 8: smoke
def smoke_card(level, num, rng, verdict, sub):
    filt = {"ok": "", "care": 'filter="url(#haze1)"', "bad": 'filter="url(#haze2)"'}[level]
    smoke = {"ok": "", "care": '<rect x="0" y="0" width="200" height="120" filter="url(#smoke)" opacity=".55"/>',
             "bad": '<rect x="0" y="0" width="200" height="120" filter="url(#smokeThick)" opacity=".9"/>'}[level]
    lo, hi = rng
    # range as a plume: wider plume = wider range
    pw = {"ok": 18, "care": 60, "bad": 140}[level]
    plume = f'<ellipse cx="100" cy="96" rx="{pw/2}" ry="6" fill="#bdb3ab" opacity="{.25 if level!="ok" else .5}" filter="url(#soft)"/><line x1="{100-pw/2}" x2="{100+pw/2}" y1="96" y2="96" stroke="#d8cfc8" stroke-width="1.2"/>'
    return (f'<div class="sc {level}"><svg viewBox="0 0 200 120"><rect width="200" height="120" rx="12" fill="#17120f"/>{plume}'
            f'<text x="100" y="68" text-anchor="middle" class="scn" {filt}>{num}</text>{smoke}'
            f'<text x="100" y="112" text-anchor="middle" class="svgs">likely between {lo} and {hi}</text></svg>'
            f'<div class="scv"><b>{verdict}</b><span>{sub}</span></div></div>')
sc = (smoke_card("ok", "412", (396, 428), "Reliable", "crisp number, thin range")
      + smoke_card("care", "37", (22, 55), "Use with care", "light haze, wider range")
      + smoke_card("bad", "9", (1, 31), "Too uncertain", "thick smoke; hover to clear it"))
idea(8, "Trust", "Smoke means unsure",
     "Every estimate has an honesty check. Instead of a small label nobody reads, let uncertainty <em>look</em> like smoke: the less sure the number, the hazier it is.",
     "Three levels from the app's own trust check. <b>Reliable</b> numbers are sharp. <b>Use with care</b> numbers shimmer behind light haze. "
     "<b>Too uncertain</b> numbers sit in thick smoke. Underneath, a smoke plume as wide as the likely range. Hovering or tapping blows the smoke away and explains why.",
     "Which numbers to lean on and which to treat with caution, felt before read. The same smoke texture can lie over calendar tiles, map embers and the CSV preview.",
     "An SVG turbulence filter (one per level) over the number, with plume width from the 80% range. The word label always stays visible, so colour and blur are never the only signal.",
     "small", "high (honesty made visible)",
     f'<div class="scrow">{sc}</div><p class="small center">Example numbers. The verdicts are the trust-check rules already in the app (reliable · use with care · too uncertain · few fires to judge).</p>')

# ---------- idea 9: time-lapse
tl_frames = ""
for mo in (6, 8, 10, 12):
    vals = cells_month(PT, 2017, mo)
    W, H, body, _ = cell_map(PT, vals, W=110, max_r=8, vmax=max(cells_month(PT, 2017, 10)))
    tl_frames += f'<div class="tlf"><svg viewBox="0 0 {f(W)} {f(H)}">{body}</svg><div class="frc"><b>{MONTH_FULL[mo-1]} 2017</b> {round(PT_TOT[idx(2017, mo)]):,} burning days</div></div>'

def fuse_timeline(tot, W=640, H=78, upto=(2017, 10)):
    n = 300; vmax = max(tot)
    X = lambda j: 10 + (j - 1) / (n - 1) * (W - 20)
    ju = idx(*upto)
    bars = []
    for j in range(1, 301):
        v = tot[j]; h = 34 * math.sqrt(v / vmax); x = X(j)
        col = ramp(lt(v, vmax)) if j <= ju else "#3b322d"
        bars.append(f'<rect x="{f(x-.7)}" y="{f(44-h)}" width="1.4" height="{f(h)}" fill="{col}"/>')
    hx = X(ju)
    fuse = (f'<line x1="10" x2="{f(hx)}" y1="54" y2="54" stroke="#2a221e" stroke-width="3" stroke-linecap="round"/>'
            f'<line x1="{f(hx)}" x2="{W-10}" y1="54" y2="54" stroke="url(#gWood)" stroke-width="3" stroke-linecap="round"/>'
            f'<circle cx="{f(hx)}" cy="54" r="10" fill="url(#gHalo)"/><circle cx="{f(hx)}" cy="54" r="3.4" fill="#fff4c8" filter="url(#glowBig)"/>')
    ticks = "".join(f'<text x="{f(X(idx(y,1)))}" y="72" class="svgs" text-anchor="middle">{y}</text>' for y in (2001, 2005, 2010, 2015, 2020, 2025))
    return f'<svg viewBox="0 0 {W} {H}">{"".join(bars)}{fuse}{ticks}</svg>'

idea(9, "Playback", "25 years in 25 seconds",
     "One play button turns the whole record into a short film: the map pulses every summer, and the big seasons flash across the country.",
     "Embers ignite and cool month by month at one month per 80 ms. The time slider is a <b>burning fuse</b>: the part already played is charred, and the glowing head is \"now\". "
     "Above it, a strip of every month's fire shows what is coming. Pause anywhere to drop into that month.",
     "The rhythm of fire seasons, whether they are getting stronger or longer, and the outliers, in under half a minute. Real frames: Portugal through 2017, including the October that should have been quiet.",
     "Reuse the idea 01 layer and step its month on a timer. The fuse is a styled range input. "
     "A soft crackle sound whose volume follows the amount of fire is optional and off by default.",
     "medium", "very high (great for demos)",
     f'<div class="tlrow">{tl_frames}</div><div class="fusebox"><h5>The fuse scrubber · every month 2001–2025, played up to October 2017</h5>{fuse_timeline(PT_TOT)}'
     f'<div class="ctl"><span class="play">❚❚</span><span>Oct 2017</span><span class="small">speed 1 month / 80 ms · space bar pauses · arrow keys step</span></div></div>')

# ---------- idea 10: fingerprints
def fingerprint(vals, *, cx=90, cy=90, R=70, fill=True, col="#f0812b", dash=False, vmax=None):
    vmax = vmax or max(vals) or 1
    pts = []
    for mo in range(12):
        a = mo / 12 * 2 * math.pi; r = 6 + (R - 6) * math.sqrt(max(vals[mo], 0) / vmax)
        pts.append((cx + r * math.sin(a), cy - r * math.cos(a)))
    d = smooth_closed(pts)
    if dash:
        return f'<path d="{d}" fill="none" stroke="#d8cfc8" stroke-width="1.3" stroke-dasharray="3 3"/>'
    return f'<path d="{d}" fill="{col}" fill-opacity=".55" stroke="#ffc35a" stroke-width="1.6" filter="url(#glow)"/>'

def fp_axes(cx=90, cy=90, R=70):
    s = f'<circle cx="{cx}" cy="{cy}" r="{R}" fill="none" stroke="#2f2622"/><circle cx="{cx}" cy="{cy}" r="{R/2}" fill="none" stroke="#2a221e"/>'
    for mo in range(12):
        a = mo / 12 * 2 * math.pi
        s += f'<line x1="{cx}" y1="{cy}" x2="{f(cx+R*math.sin(a))}" y2="{f(cy-R*math.cos(a))}" stroke="#2a221e" stroke-width=".6"/>'
        if mo % 3 == 0:
            s += f'<text x="{f(cx+(R+9)*math.sin(a))}" y="{f(cy-(R+9)*math.cos(a)+3)}" text-anchor="middle" class="svgs">{MON[mo]}</text>'
    return s

pt_med = month_medians(PT_TOT); lb_med = month_medians(LB_TOT)
pt17 = [PT_TOT[idx(2017, m)] for m in range(1, 13)]; lb24 = [LB_TOT[idx(2024, m)] for m in range(1, 13)]
fp1 = f'<svg viewBox="0 0 180 180">{fp_axes()}{fingerprint(pt_med)}</svg>'
fp2 = f'<svg viewBox="0 0 180 180">{fp_axes()}{fingerprint(lb_med)}</svg>'
vm = max(max(pt17), max(pt_med))
fp3 = f'<svg viewBox="0 0 180 180">{fp_axes()}{fingerprint(pt17, vmax=vm)}{fingerprint(pt_med, vmax=vm, dash=True)}</svg>'
vm2 = max(max(lb24), max(lb_med))
fp4 = f'<svg viewBox="0 0 180 180">{fp_axes()}{fingerprint(lb24, vmax=vm2)}{fingerprint(lb_med, vmax=vm2, dash=True)}</svg>'
idea(10, "Compare", "Fire fingerprints",
     "Every place has a fire rhythm. Draw it as a petal-shaped glyph, its fingerprint, and comparing places or years becomes as easy as comparing two shapes.",
     "A 12-spoke shape: the further a petal reaches, the more fire that month usually has. Portugal's fingerprint points straight at August; Lebanon's leans to September–October. "
     "Lay one year over the normal dashed outline and the odd year shows itself immediately.",
     "Season timing (when to prepare), its length and its shift, for any area you draw. It also makes a beautiful, shareable card: \"my area's fire fingerprint\".",
     "Twelve monthly medians drawn as a smooth closed SVG path (square-root radius). The overlay uses the same function with a dashed outline.",
     "small", "high",
     f'<div class="fpgrid"><div>{fp1}<div class="frc"><b>Portugal</b> · a normal year</div></div><div>{fp2}<div class="frc"><b>Lebanon</b> · a normal year</div></div>'
     f'<div>{fp3}<div class="frc"><b>Portugal 2017</b> over normal: the October bulge</div></div><div>{fp4}<div class="frc"><b>Lebanon 2024</b> over normal: autumn far outside the outline</div></div></div>'
     f'<p class="small center">Real data. Normal = median of each calendar month, 2003–2025. Each glyph is scaled to its own largest month.</p>')

# ---------- idea 11: story mode
def story(region, tot, y, mo, line):
    v = tot[idx(y, mo)]; med = typical(tot, y, mo); r = v / med if med else float("inf")
    hmax = 60; h1 = hmax; h0 = hmax * med / v if v else 0
    bar = (f'<svg viewBox="0 0 70 70"><rect x="10" y="{f(66-h0)}" width="20" height="{f(h0)}" fill="none" stroke="#d8cfc8" stroke-dasharray="2 2"/>'
           f'<rect x="38" y="{f(66-h1)}" width="20" height="{f(h1)}" fill="url(#gFlameOuter)" filter="url(#glow)"/></svg>')
    return (f'<div class="st">{bar}<div><div class="stk">{region}</div><div class="stt">{MONTH_FULL[mo-1]} {y}</div>'
            f'<div class="stn">{round(v):,} <span>burning days</span></div><div class="stm">{r:.0f}× a normal {MONTH_FULL[mo-1]} ({round(med):,})</div><p class="small">{line}</p></div></div>')
cards = (story("Portugal", PT_TOT, 2005, 8, "The biggest month in the whole record.")
         + story("Portugal", PT_TOT, 2017, 10, "Fire in the month the rains usually arrive.")
         + story("Portugal", PT_TOT, 2024, 9, "A September far beyond any normal year.")
         + story("Lebanon", LB_TOT, 2024, 10, "Lebanon's biggest month in 25 years."))
steps = "".join(f'<div class="step"><span>{i}</span>{t}</div>' for i, t in enumerate(["Fly to the place", "Embers ignite (idea 01)", "Ghost flame comparison (07)", "One sentence: what happened", "\"Explore it yourself\" hands over control"], 1))
idea(11, "Guided", "Story mode",
     "A first-time visitor doesn't know where to look. Story mode is a 60-second guided tour of the record's biggest months, and then it hands over the controls.",
     "Cards for standout months, picked automatically as the largest jumps above normal. Each plays a short, five-step scene: fly to the place, ignite, compare with the ghost, "
     "a plain sentence, then \"explore it yourself\".",
     "Why the tool matters, shown with real events, and how to use it, learned by watching. Every number on these cards is real.",
     "A list of scenes (camera position, month, caption), each step tied to a click on Next or to the scroll position. Scenes are generated from the data, so a new area gets its own tour.",
     "medium", "high",
     f'<div class="stgrid">{cards}</div><div class="steps">{steps}</div>')

# ---------- idea 12: small delights
def tile(svg, title, txt):
    return f'<div class="dl"><div class="dlv">{svg}</div><b>{title}</b><span>{txt}</span></div>'
load_fuse = ('<svg viewBox="0 0 200 70"><line x1="14" x2="110" y1="35" y2="35" stroke="#2a221e" stroke-width="4" stroke-linecap="round"/>'
             '<line x1="110" x2="186" y1="35" y2="35" stroke="url(#gWood)" stroke-width="4" stroke-linecap="round"/>'
             '<circle cx="110" cy="35" r="12" fill="url(#gHalo)"/><circle cx="110" cy="35" r="3.6" fill="#fff4c8" filter="url(#glowBig)"/>'
             '<text x="100" y="62" text-anchor="middle" class="svgs">Loading 25 years… 58%</text></svg>')
cold = ('<svg viewBox="0 0 200 70"><rect x="20" y="8" width="160" height="44" rx="8" fill="#16120f" stroke="#3a302b" stroke-dasharray="3 3"/>'
        + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#a59c96" opacity="{o}"/>' for x, y, r, o in ((48, 20, 1.3, .6), (90, 30, 1, .4), (130, 18, 1.4, .5), (156, 38, 1, .4), (70, 42, 1.2, .5)))
        + '<text x="100" y="34" text-anchor="middle" class="svgs" style="font-size:9px">Cold ground. No fires here this month.</text></svg>')
o17 = [r[idx(2017,10)] for r in PT["m"]]
def in_poly_tot(y, mo): return sum(r[idx(y, mo)] for r, k in zip(PT["m"], inside) if k)
tip_v = in_poly_tot(2017, 8); tip_n = st.median([in_poly_tot(y, 8) for y in range(2003, 2026) if y != 2017])
tip = ('<svg viewBox="0 0 200 70"><circle cx="40" cy="44" r="12" fill="url(#gHalo)"/><circle cx="40" cy="44" r="5" fill="url(#gEmber)"/>'
       '<path d="M56,14 h124 a6,6 0 0 1 6,6 v26 a6,6 0 0 1 -6,6 h-110 l-10,8 v-8 h-4 a6,6 0 0 1 -6,-6 v-26 a6,6 0 0 1 6,-6 Z" fill="#1d1612" stroke="#f08a33" filter="url(#glow)"/>'
       f'<text x="66" y="30" class="svga">Your area · Aug 2017</text><text x="66" y="43" class="svgs">{round(tip_v):,} burning days · {tip_v/tip_n:.0f}× normal</text></svg>')
intro = ('<svg viewBox="0 0 200 70"><rect x="10" y="6" width="180" height="58" rx="8" fill="#07090b"/>'
         + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#gEmber)" opacity="{o}"/>' for x, y, r, o in ((40, 30, 4, .9), (62, 44, 3, .7), (90, 24, 2.4, .5), (120, 40, 5, 1), (150, 28, 3, .6), (168, 48, 2, .4), (100, 52, 2, .3)))
         + '<text x="100" y="60" text-anchor="middle" class="svgs">the map starts dark, then lights up</text></svg>')
night = ('<svg viewBox="0 0 200 70"><rect x="10" y="10" width="86" height="50" rx="8" fill="#2b2c2a"/><rect x="104" y="10" width="86" height="50" rx="8" fill="#05070a"/>'
         '<circle cx="28" cy="24" r="6" fill="#f3d363"/><path d="M178,20 a7,7 0 1 1 -7,-7 a5,5 0 0 0 7,7 Z" fill="#cfd7e6"/>'
         + "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="url(#gEmber)"/>' for x, y, r in ((52, 40, 3), (70, 32, 2.4), (130, 42, 3.4), (150, 30, 2.2), (166, 46, 2.6)))
         + '<text x="53" y="58" text-anchor="middle" class="svgs">day passes</text><text x="147" y="58" text-anchor="middle" class="svgs">night passes</text></svg>')
cursor = ('<svg viewBox="0 0 200 70"><path d="M30,50 C60,20 90,60 120,30 S170,40 176,22" fill="none" stroke="#ff9a3c" stroke-width="2" opacity=".25" filter="url(#glow)"/>'
          '<path d="M120,30 S170,40 176,22" fill="none" stroke="#ffb04a" stroke-width="2" opacity=".7"/>'
          '<path d="M176,22 l10,4 -5,2 3,6 -3,1 -3,-6 -4,4 Z" fill="#f3e6d8"/>'
          '<text x="100" y="64" text-anchor="middle" class="svgs">over a burning cell the cursor leaves a faint heat trail</text></svg>')
share = ('<svg viewBox="0 0 200 70"><rect x="40" y="6" width="120" height="58" rx="8" fill="#16110e" stroke="#4a3a32"/>'
         + fingerprint(pt_med, cx=72, cy=35, R=24).replace('filter="url(#glow)"', '')
         + '<text x="104" y="28" class="svga" style="font-size:8px">My area\'s</text><text x="104" y="39" class="svga" style="font-size:8px">fire fingerprint</text><text x="104" y="51" class="svgs" style="font-size:6.5px">peak: August</text></svg>')
sound = ('<svg viewBox="0 0 200 70"><rect x="60" y="20" width="80" height="30" rx="15" fill="#1a1411" stroke="#4a3a32"/>'
         '<text x="80" y="40" class="svgs" style="font-size:12px">🔈</text>'
         + "".join(f'<rect x="{96+i*7}" y="{f(35-h/2)}" width="4" height="{h}" rx="2" fill="#f0812b" opacity=".8"/>' for i, h in enumerate((6, 12, 18, 10, 5)))
         + '<text x="100" y="64" text-anchor="middle" class="svgs">soft crackle · off by default</text></svg>')
tiles = (tile(load_fuse, "Loading fuse", "The progress bar is a fuse burning down. Its spark is the percent.")
         + tile(cold, "Cold ground", "No fires? Say so warmly: drifting ash and a clear sentence, never an empty chart.")
         + tile(tip, "Ember tooltips", "Hover cards glow at the edge in the colour of the fire they describe.")
         + tile(intro, "First light", "On first visit the map starts black, and 25 years of fire flicker on in about 3 seconds.")
         + tile(night, "Day and night passes", "Satellites pass by day and by night. Toggle to see the night-time fires glow like city lights.")
         + tile(cursor, "Heat trail", "Over active cells the cursor leaves a short warm trail, a hint that something is here.")
         + tile(share, "Shareable card", "One click makes an image of your area's fingerprint and calendar, ready to post.")
         + tile(sound, "Optional sound", "A soft crackle that follows the amount of fire during playback. Never on by default."))
page(f"""<div class="kicker">Idea 12 · Details</div><h2>Small delights</h2>
<p class="pitch wide">The moments between the big features: loading, empty results, tooltips, the first second on the page. Each takes an hour or two and makes the whole tool feel finished and alive.</p>
<div class="dlgrid">{tiles}</div>""")

# ---------- colour & care
def lin(c):
    c = c / 255; return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4
def unlin(c):
    c = max(0, min(1, c)); return 255 * (12.92 * c if c <= .0031308 else 1.055 * c ** (1 / 2.4) - .055)
MAT = {"Deuteranopia": [[0.367322, 0.860646, -0.227968], [0.280085, 0.672501, 0.047413], [-0.011820, 0.042940, 0.968881]],
       "Protanopia": [[0.152286, 1.052583, -0.204868], [0.114503, 0.786281, 0.099216], [-0.003882, -0.048116, 1.051998]],
       "Tritanopia": [[1.255528, -0.076749, -0.178779], [-0.078411, 0.930809, 0.147602], [0.004733, 0.691367, 0.303900]]}
def sim(hexc, m):
    r, g, b = (lin(v) for v in hex2rgb(hexc))
    return rgb2hex([unlin(m[i][0] * r + m[i][1] * g + m[i][2] * b) for i in range(3)])
def grey(hexc):
    r, g, b = (lin(v) for v in hex2rgb(hexc)); y = .2126 * r + .7152 * g + .0722 * b; return rgb2hex([unlin(y)] * 3)
N = 24; base = [ramp(i / (N - 1)) for i in range(N)]
def bar(cols):
    return "".join(f'<span style="background:{c}"></span>' for c in cols)
rows = [("As designed", base)] + [(k, [sim(c, m) for c in base]) for k, m in MAT.items()] + [("Greyscale print", [grey(c) for c in base])]
cvd = "".join(f'<div class="cvr"><span class="cvl">{k}</span><div class="ramp">{bar(c)}</div></div>' for k, c in rows)
DIV = [(0, "#2f6f9a"), (.35, "#8fb3c9"), (.5, "#4a4440"), (.65, "#f0a24a"), (1, "#ff5a1c")]
div = [ramp(i / (N - 1), DIV) for i in range(N)]
page(f"""<div class="two">
<div class="col-a"><div class="kicker">Colour &amp; care</div><h2>Beautiful, and readable by everyone</h2>
<p>The brief asks for accessible colour ramps. The ember scale gets steadily lighter from dark to bright, so it still reads correctly
for the three common types of colour blindness and in black-and-white print (right). Anomalies use a separate scale, cool ash-blue to hot orange,
always paired with ▲/▽ symbols.</p>
<h4>Motion safety</h4>
<ul class="tight">
<li><b>No flashing faster than 3 times a second</b> (the international web accessibility guideline for seizure safety). Flicker is a slow, gentle wobble, never a strobe.</li>
<li><b>Reduce motion respected:</b> with the device setting on, ignitions become a still ember, fuses become a normal bar, and smoke becomes a dotted outline plus its word.</li>
<li><b>One-shot animations:</b> motion plays when something changes, then stops. Nothing loops in the corner of your eye.</li>
</ul>
<h4>Never colour alone</h4>
<ul class="tight">
<li>Every tile and ember has a number on hover and focus, and a ▲/▽ symbol when it's unusual.</li>
<li>Trust levels always show their word (Reliable · Use with care · Too uncertain).</li>
<li>Text contrast of at least 4.5 : 1 on the dark background; every glow effect sits <em>behind</em> the text, never on it.</li>
<li>Every control works by keyboard; the focus ring is the same warm glow as hover.</li>
</ul></div>
<div class="col-b"><h5>The ember scale under colour-vision simulation (Machado 2009)</h5>{cvd}
<div class="legl"><span>no fire</span><span>record</span></div>
<h5 style="margin-top:6mm">Anomaly scale: below normal ← → above normal</h5><div class="cvr"><span class="cvl">As designed</span><div class="ramp">{bar(div)}</div></div>
<div class="cvr"><span class="cvl">Deuteranopia</span><div class="ramp">{bar([sim(c, MAT['Deuteranopia']) for c in div])}</div></div>
<div class="legl"><span>▽ ash: quieter</span><span>normal</span><span>▲ ember: hotter</span></div>
<div class="note">Both scales stay in order (dark→light, blue→orange) in every simulation. That is the property that keeps them readable.</div>
</div></div>""")

# ---------- where to start
DOTS = [("01 Ignition rings", 2, 9.3), ("02 Burning buttons", 1, 7.8), ("03 Tree rings", 2.1, 9.5), ("04 Ember quilt", 1.2, 7.2),
        ("05 Firebreak", 2.4, 8.8), ("06 Two eyes", 2.3, 8.3), ("07 Ghost flame", 1.1, 7.6), ("08 Smoke", 1.3, 7.4),
        ("09 25 in 25", 2.6, 8.6), ("10 Fingerprints", 1.4, 6.9), ("11 Story mode", 2.8, 7.7), ("12 Delights", .9, 6.2)]
star = {"01 Ignition rings", "02 Burning buttons", "03 Tree rings", "05 Firebreak", "06 Two eyes"}
def mx(e): return 60 + (e - .5) / 2.6 * 330
def my(w): return 250 - (w - 5.8) / 4 * 230
dots = ""
for name, e, w in DOTS:
    x, y = mx(e), my(w); s = name in star; gl = 'filter="url(#glow)"' if s else ''
    dots += (f'<circle cx="{f(x)}" cy="{f(y)}" r="{9 if s else 6}" fill="url(#gHalo)"/><circle cx="{f(x)}" cy="{f(y)}" r="{4.5 if s else 3}" fill="{"#ffd27a" if s else "#c8643a"}" {gl}/>'
             f'<text x="{f(x+8)}" y="{f(y+3.5)}" class="{"svga" if s else "svgs"}">{name}</text>')
chart = (f'<svg viewBox="0 0 470 290" class="bigtext"><rect x="60" y="20" width="330" height="230" fill="none" stroke="#3a2f2a"/>'
         f'<rect x="60" y="20" width="150" height="110" fill="#ff7a2a" opacity=".05"/>'
         f'<text x="66" y="34" class="svgs">sweet spot: big wow, modest effort</text>'
         f'<text x="70" y="264" class="svgs">small</text><text x="225" y="264" text-anchor="middle" class="svgs">medium</text><text x="380" y="264" text-anchor="end" class="svgs">big</text><text x="225" y="282" text-anchor="middle" class="svga">effort  →</text><text x="20" y="135" class="svgs" transform="rotate(-90 20 135)" text-anchor="middle">wow + meaning  →</text>{dots}</svg>')
order = [
    ("Burning buttons + loading fuse", "Every screen gets the look straight away, mostly CSS. Do first: it sets the visual language."),
    ("Ignition rings", "The signature moment on the map. Reused by firebreak, playback and stories."),
    ("Fire tree rings", "The memorable image; it doubles as the logo of the tool and the cover of any presentation."),
    ("Draw a firebreak", "Turns the tool's core action, choosing an area, into an event people remember."),
    ("Two eyes, one fire", "Explains the science in ten seconds, so the rest of the magic is trusted."),
]
ol = "".join(f'<li><b>{a}.</b> {b}</li>' for a, b in order)
page(f"""<div class="two"><div class="col-a"><div class="kicker">Where to start</div><h2>Build order</h2>
<p>All twelve fit one visual language, so they reinforce each other. If time is short, these five give the most wonder per hour,
and each one reuses the last.</p><ol class="order">{ol}</ol>
<p class="small">Then, as time allows: the ghost flame and smoke (they upgrade existing panels), playback, fingerprints, story mode, and the small delights.</p>
<div class="note">Rule of thumb for any new idea: <b>if you can't say what fact the motion carries, it doesn't ship.</b></div></div>
<div class="col-b" style="display:flex;flex-direction:column;justify-content:center">{chart}<p class="small center">Rough placement, for planning. ★ ideas glow.</p></div></div>""")

CSS = r"""
@page { size: 297mm 210mm; margin: 0; }
:root{--bg:#0d0b0a;--bg2:#15110f;--ink:#f3e9df;--mut:#b3a69b;--line:#2f2622;--fire:#f0812b;--gold:#ffc35a;--ash:#8fb3c9}
*{box-sizing:border-box}
html,body{margin:0;padding:0;background:var(--bg);color:var(--ink);font-family:Inter,"Segoe UI",Arial,sans-serif;font-size:9.6pt;line-height:1.45;-webkit-print-color-adjust:exact;print-color-adjust:exact}
h1,h2{font-family:Fraunces,Georgia,serif;font-weight:700;margin:0;letter-spacing:-.01em}
h2{font-size:22pt;line-height:1.08;margin-bottom:3mm;color:#fff3e4}
h4{font:700 8pt Inter,sans-serif;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);margin:4mm 0 1.2mm}
h5{font:600 8pt Inter,sans-serif;letter-spacing:.08em;text-transform:uppercase;color:var(--mut);margin:0 0 2mm}
p{margin:0 0 2mm}
em{color:#ffd9a8;font-style:normal}
code{font-family:Consolas,monospace;font-size:8.4pt;color:#ffd9a8;background:#211a16;padding:0 1mm;border-radius:3px}
.page{width:297mm;height:210mm;padding:13mm 15mm 14mm;position:relative;page-break-after:always;overflow:hidden;
  background:radial-gradient(ellipse at 100% 0%,#24140c 0%,transparent 45%),radial-gradient(ellipse at 0% 100%,#141b20 0%,transparent 45%),var(--bg)}
.page:last-child{page-break-after:auto}
.folio{position:absolute;bottom:6mm;left:15mm;right:15mm;display:flex;justify-content:space-between;font-size:7.4pt;color:#7d7068;border-top:1px solid var(--line);padding-top:2mm}
.kicker{font:700 7.6pt Inter,sans-serif;letter-spacing:.2em;text-transform:uppercase;color:var(--fire);margin-bottom:2.5mm}
.kicker.light{color:#ffb070}
.pitch{font:500 11pt/1.42 Fraunces,Georgia,serif;color:#ffe6c8;margin-bottom:3mm}
.pitch.wide{max-width:200mm}
.small{font-size:8pt;color:var(--mut)} .center{text-align:center}
.build{color:#d9cdc2}
.chips{display:flex;gap:2mm;margin-top:3.5mm;flex-wrap:wrap}
.chip{border:1px solid #4a3a32;border-radius:99px;padding:.6mm 2.6mm;font:600 7.6pt Inter,sans-serif;color:var(--mut)}
.chip.hot{border-color:#a8551f;color:#ffc58a;background:#2a160c}
.idea{display:grid;grid-template-columns:96mm 1fr;gap:9mm}
.idea .right{display:flex;flex-direction:column;justify-content:center;gap:4mm;min-width:0}
.star{color:var(--gold);font-weight:700}
svg{display:block;width:100%;height:auto}
.svgl{font:600 10px Inter,sans-serif;fill:#c9b9ab}
.svgs{font:500 7.5px Inter,sans-serif;fill:#a8998e}
.svga{font:700 8.5px Inter,sans-serif;fill:#fff3e4}
.svgc{font:700 13px Fraunces,Georgia,serif;fill:#fff3e4}
.btnt{font:600 12px Inter,sans-serif;fill:#f6e8da}.btnt.dim{fill:#8d7f75}
.tri{font:700 7px Inter,sans-serif;fill:#2a120a}.tri.ash{fill:#d7e6f0}
.scn{font:700 40px Fraunces,Georgia,serif;fill:#fff3e4}
.cap{font-size:8pt;color:var(--mut);text-align:center;margin-top:2mm}.cap.light{color:#c9b3a2}
/* cover */
.cover{padding:0;background:radial-gradient(ellipse at 72% 50%,#2c140a 0%,transparent 55%),radial-gradient(ellipse at 0% 100%,#0e1820 0%,transparent 50%),#090706}
.cover-wrap{display:grid;grid-template-columns:120mm 1fr;height:100%;align-items:center;padding:0 16mm 0 20mm}
.cover h1{font-size:54pt;line-height:.98;color:#fff3e4;margin:2mm 0 6mm}
.lede{font:500 13pt/1.45 Fraunces,Georgia,serif;color:#ffd9b0;max-width:108mm}
.cover-note{font-size:8.6pt;color:var(--mut);max-width:100mm;margin-top:6mm}
.cover-legend{display:flex;align-items:center;gap:2mm;font-size:8pt;color:var(--mut);margin-top:4mm}
.sw{display:inline-block;width:5mm;height:3mm;border-radius:1mm;margin-left:2mm}
.cover-art svg{width:150mm;margin:0 auto}
/* principles */
.two{display:grid;grid-template-columns:1fr 1fr;gap:12mm;height:100%}
.mat{display:flex;flex-direction:column;gap:2.5mm;margin:3mm 0}
.matc{display:grid;grid-template-columns:15mm 1fr;gap:3mm;align-items:center;background:var(--bg2);border:1px solid var(--line);border-radius:3mm;padding:2mm 3mm}
.matc b{display:block;color:#fff3e4}.matc span{color:var(--mut);font-size:8.6pt}
.rules{margin:0;padding-left:5mm}.rules li{margin-bottom:1.4mm}
.ix{display:flex;flex-direction:column;gap:1.2mm}
.ix-row{display:grid;grid-template-columns:9mm 44mm 20mm 1fr;gap:2mm;align-items:baseline;border-bottom:1px solid var(--line);padding:1.5mm 0}
.ix-n{font:700 13pt Fraunces,Georgia,serif;color:var(--fire)}.ix-t{font-weight:700;color:#fff3e4}
.ix-c{font-size:7.4pt;letter-spacing:.1em;text-transform:uppercase;color:var(--mut)}.ix-d{font-size:8.4pt;color:#d6c9bd}
/* frames */
.fstrip{display:grid;grid-template-columns:repeat(5,1fr);gap:2mm;background:var(--bg2);border:1px solid var(--line);border-radius:3mm;padding:2mm}
.fr svg{background:#0f0c0b;border-radius:2mm}
.frc{font-size:7.6pt;color:var(--mut);text-align:center;margin-top:1mm;line-height:1.3}.frc b{color:#fff3e4;display:block}
.mapbox{display:grid;grid-template-columns:62mm 1fr;gap:5mm;align-items:center}
.mapbox .map{background:#0b0908;border:1px solid var(--line);border-radius:3mm}
.big{font:700 18pt Fraunces,Georgia,serif;color:#ffc35a;margin-bottom:2mm}
/* buttons */
.btgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm;background:var(--bg2);border:1px solid var(--line);border-radius:3mm;padding:3mm}
.family{display:grid;grid-template-columns:1fr 1.5fr;grid-template-rows:auto auto;gap:4mm}
.family>div:first-child{grid-row:span 2}
.family>div{background:var(--bg2);border:1px solid var(--line);border-radius:3mm;padding:3mm}
.pair{display:grid;grid-template-columns:1fr;gap:1mm}
/* rings */
.rings2{display:grid;grid-template-columns:1.45fr 1fr;gap:5mm;align-items:center}
.rside{display:flex;flex-direction:column;gap:2mm}
.leg{display:flex;height:3mm;border-radius:1mm;overflow:hidden}.leg span{flex:1}
.legl{display:flex;justify-content:space-between;font-size:7.4pt;color:var(--mut);margin-top:.6mm}
.dash{display:inline-block;width:8mm;border-top:1.4px dashed #9fd3ff;vertical-align:middle;margin-right:1mm}
/* quilt */
.quilt{background:#0b0908;border:1px solid var(--line);border-radius:3mm;padding:1mm}
.qleg{display:flex;flex-wrap:wrap;gap:2mm 5mm;font-size:8pt;color:var(--mut)}
.qleg .tri{font-size:9pt;color:#2a120a;background:#f6b24a;border-radius:1mm;padding:0 1mm}.qleg .tri.ash{color:#d7e6f0;background:#3a3532}
/* firebreak */
.fbstrip{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm}
.fbf{background:#0b0908;border:1px solid var(--line);border-radius:3mm;padding:2mm}
/* eyes */
.eyes{display:grid;grid-template-columns:1fr 18mm 1fr;gap:3mm;align-items:center}
.eyes svg{max-width:52mm;margin:0 auto}
.eq{font:700 11pt Fraunces,Georgia,serif;text-align:center;color:var(--gold)}
.chartbox{background:var(--bg2);border:1px solid var(--line);border-radius:3mm;padding:3mm}
.switchrow{display:flex;align-items:center;gap:2mm;margin-top:1mm}
.pill-sw{width:10mm;height:5mm;border-radius:3mm;background:#3a1d12;border:1px solid #f08a33;position:relative;display:inline-block;box-shadow:0 0 6px #f0812b}
.pill-sw .knob{position:absolute;right:.5mm;top:.5mm;width:3.6mm;height:3.6mm;border-radius:50%;background:#ffd27a}
/* ghost */
.gfrow{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm}
.gf{background:var(--bg2);border:1px solid var(--line);border-radius:3mm;padding:3mm}
.gf svg{max-width:50mm;margin:0 auto}
.gfc{display:flex;flex-direction:column;align-items:center;text-align:center}
.gfc b{color:#fff3e4}.gfn{font:700 20pt Fraunces,Georgia,serif;color:var(--gold);line-height:1.1}
.gfw{margin-top:1mm;font-weight:700;color:#ffd9a8}
/* smoke */
.scrow{display:grid;grid-template-columns:repeat(3,1fr);gap:4mm}
.sc{background:var(--bg2);border:1px solid var(--line);border-radius:3mm;padding:2mm}
.scv{text-align:center;margin-top:1.5mm}.scv b{display:block}.scv span{font-size:8pt;color:var(--mut)}
.sc.ok b{color:#9fe0b0}.sc.care b{color:#ffd27a}.sc.bad b{color:#ff9a8a}
/* timelapse */
.tlrow{display:grid;grid-template-columns:repeat(4,1fr);gap:3mm}
.tlf{background:#0b0908;border:1px solid var(--line);border-radius:3mm;padding:2mm}
.fusebox{background:var(--bg2);border:1px solid var(--line);border-radius:3mm;padding:3mm}
.ctl{display:flex;gap:4mm;align-items:center;font-size:8.4pt;color:#fff3e4}
.play{display:inline-grid;place-items:center;width:7mm;height:7mm;border-radius:50%;background:#3a1d12;border:1px solid #f08a33;font-size:7pt;color:#ffd27a}
/* fingerprints */
.fpgrid{display:grid;grid-template-columns:repeat(2,1fr);gap:3mm}
.fpgrid svg{max-width:62mm;margin:0 auto}
.fpgrid>div{background:var(--bg2);border:1px solid var(--line);border-radius:3mm;padding:2mm}
/* stories */
.stgrid{display:grid;grid-template-columns:1fr 1fr;gap:3mm}
.st{display:grid;grid-template-columns:20mm 1fr;gap:3mm;background:var(--bg2);border:1px solid var(--line);border-radius:3mm;padding:3mm}
.stk{font-size:7.4pt;letter-spacing:.12em;text-transform:uppercase;color:var(--fire)}
.stt{font:700 12pt Fraunces,Georgia,serif;color:#fff3e4}
.stn{font:700 16pt Fraunces,Georgia,serif;color:var(--gold)}.stn span{font:500 8pt Inter,sans-serif;color:var(--mut)}
.stm{font-weight:700;color:#ffd9a8;font-size:8.6pt;margin-bottom:1mm}
.steps{display:grid;grid-template-columns:repeat(5,1fr);gap:2mm}
.step{background:#1b1411;border:1px solid #4a3a32;border-radius:2mm;padding:2mm;font-size:8pt;color:#e6d8cc}
.step span{display:block;font:700 12pt Fraunces,Georgia,serif;color:var(--fire)}
/* delights */
.dlgrid{display:grid;grid-template-columns:repeat(4,1fr);gap:4mm;margin-top:4mm}
.dl{background:var(--bg2);border:1px solid var(--line);border-radius:3mm;padding:3mm;display:flex;flex-direction:column;gap:1mm}
.dlv{background:#0b0908;border-radius:2mm;margin-bottom:1.5mm}
.dl b{color:#fff3e4}.dl span{font-size:8.2pt;color:var(--mut)}
/* colour */
.cvr{display:grid;grid-template-columns:30mm 1fr;gap:3mm;align-items:center;margin-bottom:1.6mm}
.cvl{font-size:8pt;color:var(--mut)}
.ramp{display:flex;height:6mm;border-radius:1.5mm;overflow:hidden}.ramp span{flex:1}
.tight{margin:0;padding-left:5mm}.tight li{margin-bottom:1.2mm}
.note{margin-top:4mm;background:#1d140f;border:1px solid #5a3a22;border-left:4px solid var(--fire);border-radius:2mm;padding:2.5mm 3.5mm;font-size:8.6pt}
.bigtext .svgs{font-size:10px}.bigtext .svga{font-size:11px}
.order{padding-left:5mm}.order li{margin-bottom:2mm}
"""

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Fire, made visible</title>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,700&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>{DEFS}{"".join(pages)}</body></html>"""
OUT.write_text(html, encoding="utf-8")
print("pages:", len(pages), "->", OUT, "| quiet Aug", quiet_y, "normal Aug", normal_y)
