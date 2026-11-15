// CEDRUS story stage: Yasmina's 3D scene (orbit, dive, the record as slabs), fed with the real record of the story region (Lebanon).
// Loaded by shell.js after the calendar has rendered; it reads window.__storyD (built from monthly_bd.json and regions.json).
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
// loaded with this module's own ?v so a browser never mixes old and new files
const { GEO } = await import(`./story-geo.js${new URL(import.meta.url).search}`);

const FX = (() => {
const NOISE = `
float hash(vec2 p){return fract(sin(dot(p,vec2(127.1,311.7)))*43758.5453123);}
float noise(vec2 p){vec2 i=floor(p),f=fract(p);vec2 u=f*f*(3.-2.*f);return mix(mix(hash(i),hash(i+vec2(1.,0.)),u.x),mix(hash(i+vec2(0.,1.)),hash(i+vec2(1.,1.)),u.x),u.y);}
float fbm(vec2 p){float v=0.,a=.5;for(int i=0;i<5;i++){v+=a*noise(p);p=p*2.03+vec2(1.7,9.2);a*=.5;}return v;}
`;
const flameFrag = NOISE + `
varying vec2 vUv; uniform float uTime; uniform float uSeed; uniform float uAlpha;
void main(){
  vec2 uv=vUv; float t=uTime*1.7+uSeed*17.;
  float n=fbm(vec2(uv.x*3.2+uSeed*5., uv.y*1.9-t));
  float n2=fbm(vec2(uv.x*6.5-n*1.2, uv.y*3.6-t*1.5));
  float x=(uv.x-.5)*2.;
  x+=(n-.5)*1.3*uv.y+(n2-.5)*.35*uv.y;
  float width=mix(.95,.18,uv.y);
  float shape=1.-smoothstep(0.,width,abs(x));
  float heat=shape*1.32-uv.y*1.1-n2*.8+.32;
  heat*=smoothstep(0.,.12,uv.y);
  heat=clamp(heat,0.,1.);
  vec3 col=mix(vec3(.6,.04,.0),vec3(1.,.33,.03),smoothstep(.05,.4,heat));
  col=mix(col,vec3(1.,.72,.2),smoothstep(.4,.75,heat));
  col=mix(col,vec3(1.,.95,.75),smoothstep(.82,1.,heat));
  float a=smoothstep(.02,.3,heat)*uAlpha;
  gl_FragColor=vec4(col*1.2,a);
}`;
const smokeFrag = NOISE + `
varying vec2 vUv; uniform float uTime; uniform float uSeed; uniform float uAlpha;
void main(){
  vec2 p=vUv-.5; float d=length(p)*2.;
  float n=fbm(vUv*2.6+vec2(uSeed*7.,-uTime*.25));
  float a=(1.-smoothstep(.15,1.,d+(n-.5)*.7))*n*1.5*uAlpha;
  vec3 col=mix(vec3(.42,.2,.08),vec3(.11,.11,.12),clamp(vUv.y*1.3,0.,1.));
  gl_FragColor=vec4(col,clamp(a,0.,1.));
}`;
const wallFrag = NOISE + `
varying vec2 vUv; uniform float uTime; uniform float uAmt; uniform float uAspect; uniform vec3 uC0; uniform vec3 uC1; uniform vec3 uC2; uniform vec3 uC3;
void main(){
  vec2 uv=vUv; vec2 p=vec2(uv.x*uAspect*3.2, uv.y*2.4);
  float t=uTime*1.4;
  float n=fbm(p*vec2(1.,.5)+vec2(0.,-t));
  float n2=fbm(vec2(p.x*2.2+n*1.8,p.y*1.6-t*1.8));
  float h=uAmt*1.9-.25;
  float f=(h-uv.y)*1.4-n2*.95+.45;
  float flame=smoothstep(0.,.25,f);
  vec3 col=mix(uC0,uC1,smoothstep(0.,.35,f));
  col=mix(col,uC2,smoothstep(.35,.8,f));
  col=mix(col,uC3,smoothstep(.9,1.6,f));
  gl_FragColor=vec4(col*1.15,clamp(flame,0.,1.));
}`;
const fireVert = `
attribute float aSize; attribute float aSeed; attribute float aHeat; uniform float uTime; uniform float uPx; varying float vHeat; varying float vFl;
void main(){ vec4 mv=modelViewMatrix*vec4(position,1.); float fl=.7+.3*sin(uTime*(5.+aSeed*6.)+aSeed*40.)*sin(uTime*2.1+aSeed*13.); vFl=fl; vHeat=aHeat; gl_PointSize=aSize*fl*uPx/(-mv.z); gl_Position=projectionMatrix*mv; }`;
const fireFrag = `
varying float vHeat; varying float vFl;
void main(){ vec2 c=gl_PointCoord-.5; float d=length(c)*2.; float g=exp(-d*d*5.)*(1.-smoothstep(.85,1.,d)); float core=exp(-d*d*28.); vec3 col=mix(vec3(1.,.3,.04),vec3(1.,.85,.55),clamp(core*(.4+vHeat),0.,1.)); gl_FragColor=vec4(col*(g*.9+core*.8)*(.55+vFl*.7), g); }`;
const emberVert = `
attribute float aLife; attribute float aSize; uniform float uPx; varying float vLife;
void main(){ vec4 mv=modelViewMatrix*vec4(position,1.); vLife=aLife; gl_PointSize=aSize*uPx*(.35+aLife*.65)/(-mv.z); gl_Position=projectionMatrix*mv; }`;
const emberFrag = `
varying float vLife;
void main(){ vec2 c=gl_PointCoord-.5; float d=length(c)*2.; float g=exp(-d*d*6.); vec3 col=mix(vec3(1.,.25,.03),vec3(1.,.8,.4),vLife); gl_FragColor=vec4(col*g*1.6*smoothstep(0.,.25,vLife), g*vLife); }`;
return {NOISE,flameFrag,smokeFrag,wallFrag,fireVert,fireFrag,emberVert,emberFrag};
})();

const D = { ...window.__storyD, PT: GEO.PT, LB: GEO.LB, OUT: window.__storyD.story.id === 'portugal' ? GEO.PT : GEO.LB };
const canvas = document.getElementById('gl');
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
// Effects off (the app's switch) or reduced motion: a still picture that only moves when the slide changes.
const still = () => reduce || document.documentElement.classList.contains('fx-still');
let renderer;
try {
  renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
} catch (e) {
  window.__stageFailed && window.__stageFailed(e);
  throw e;
}
const small = () => innerWidth < 760;
renderer.setPixelRatio(Math.min(devicePixelRatio, small() ? 1.5 : 1.75));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const camera = new THREE.PerspectiveCamera(38, innerWidth / innerHeight, 0.05, 300);
const V = (x, y, z) => new THREE.Vector3(x, y, z);
const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
const sm = t => t * t * (3 - 2 * t);
const ease = t => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
let seedA = 5; const rnd = () => { seedA = (seedA * 16807) % 2147483647; return seedA / 2147483647; };
const uniformsTime = { value: 0 };
const uPx = { value: 800 };
let lastT = 0, slowFrames = 0, light = false;

/* =========================================================
   SPACE: NASA Blue Marble Earth, four fire-sensing satellites
   ========================================================= */
const space = new THREE.Scene();
space.background = new THREE.Color(0x010305);
const R = 5, LON0 = 20, LAT0 = 35 * Math.PI / 180; // faces the eastern Mediterranean: Lebanon (the story) and Iberia both in view
// lon/lat → world position. The camera faces lon 8°E, lat 36°N.
function ll(lon, lat, r = R) {
  const p = lat * Math.PI / 180, l = (lon - LON0) * Math.PI / 180;
  const x = Math.cos(p) * Math.sin(l), y = Math.sin(p), z = Math.cos(p) * Math.cos(l);
  const ca = Math.cos(LAT0), sa = Math.sin(LAT0);
  return new THREE.Vector3(x * r, (y * ca - z * sa) * r, (y * sa + z * ca) * r);
}
const SUN = new THREE.Vector3(1, .3, .1).normalize();   // evening light from the west
// The stage announces itself only once the Earth images are in, so the crossfade from the poster never shows a black globe.
let texturesIn = false;
const texManager = new THREE.LoadingManager(() => { texturesIn = true; });
const texLoader = new THREE.TextureLoader(texManager);
const maxAniso = renderer.capabilities.getMaxAnisotropy();
const tex = (u, srgb) => { const t = texLoader.load(u); if (srgb) t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = Math.min(8, maxAniso); return t; };
const dayT = tex('assets/earth-day.jpg', true), nightT = tex('assets/earth-night.jpg', true), waterT = tex('assets/land-mask.png'); // NASA GIBS OSM_Land_Mask: white = water

// equirectangular texture → same frame as ll()
const earth = new THREE.Group();
earth.rotation.set(LAT0, -(LON0 + 90) * Math.PI / 180, 0, 'XYZ');
space.add(earth);
const SPHERE_V = `varying vec2 vUv; varying vec3 vN; varying vec3 vP;
void main(){ vUv=uv; vN=normalize(mat3(modelMatrix)*normal); vec4 wp=modelMatrix*vec4(position,1.); vP=wp.xyz; gl_Position=projectionMatrix*viewMatrix*wp; }`;
const globeMat = new THREE.ShaderMaterial({
  uniforms: { uDay: { value: dayT }, uNight: { value: nightT }, uWater: { value: waterT }, uSun: { value: SUN } },
  vertexShader: SPHERE_V,
  fragmentShader: `uniform sampler2D uDay; uniform sampler2D uNight; uniform sampler2D uWater; uniform vec3 uSun;
  varying vec2 vUv; varying vec3 vN; varying vec3 vP;
  void main(){
    vec3 n=normalize(vN); vec3 v=normalize(cameraPosition-vP); float sd=dot(n,uSun);
    vec3 day=texture2D(uDay,vUv).rgb; vec3 night=texture2D(uNight,vUv).rgb; float water=texture2D(uWater,vUv).r;
    float lit=smoothstep(-.1,.38,sd);
    vec3 col=day*(lit*1.2+.012);
    vec3 h=normalize(uSun+v); col+=vec3(1.,.8,.55)*pow(max(dot(n,h),0.),80.)*water*lit*.9;
    float dusk=smoothstep(-.22,0.,sd)*(1.-smoothstep(0.,.28,sd)); col+=vec3(.95,.38,.12)*dusk*.05;
    col+=night*vec3(1.,.74,.45)*1.5*(1.-smoothstep(-.18,.1,sd));
    col*=mix(vec3(1.),vec3(.8,.93,1.12),.3);
    float fr=pow(1.-max(dot(n,v),0.),2.6); col+=vec3(.25,.55,1.)*fr*(.1+.9*smoothstep(-.35,.45,sd))*.85;
    gl_FragColor=vec4(col,1.);
  }`
});
earth.add(new THREE.Mesh(new THREE.SphereGeometry(R, 160, 120), globeMat));
// (no cloud layer: no cloud imagery is shipped)
space.add(new THREE.Mesh(new THREE.SphereGeometry(R * 1.1, 96, 64), new THREE.ShaderMaterial({
  side: THREE.BackSide, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  uniforms: { uSun: { value: SUN } },
  vertexShader: `varying vec3 vN; varying vec3 vW; void main(){ vN=normalize(normalMatrix*normal); vW=normalize((modelMatrix*vec4(position,1.)).xyz); gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
  fragmentShader: `uniform vec3 uSun; varying vec3 vN; varying vec3 vW; void main(){ float i=pow(clamp(.74-dot(vN,vec3(0.,0.,1.)),0.,1.),3.);
    float s=smoothstep(-.4,.6,dot(vW,uSun)); vec3 c=mix(vec3(.1,.28,.7),vec3(.42,.72,1.),s); gl_FragColor=vec4(c*i*1.7*(.35+.65*s),i); }`
})));
{ // stars
  const n = 3200, a = new Float32Array(n * 3);
  for (let k = 0; k < n; k++) { const v = new THREE.Vector3(rnd() - .5, rnd() - .5, rnd() - .5).normalize().multiplyScalar(110 + rnd() * 40); a.set([v.x, v.y, v.z], k * 3); }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(a, 3));
  space.add(new THREE.Points(g, new THREE.PointsMaterial({ color: 0xcfe3ff, size: 1.3, sizeAttenuation: false, transparent: true, opacity: .7 })));
}
// dot-matrix land layer (Natural Earth 1:50m land mask), the mission-control look
const dotMat = new THREE.MeshBasicMaterial({ color: 0x7cc8ff, transparent: true, opacity: .22, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false });
let landMask = null;
{
  const img = new Image();
  img.onload = () => {
    const c = document.createElement('canvas'); c.width = img.width; c.height = img.height;
    const g = c.getContext('2d'); g.drawImage(img, 0, 0); const d = g.getImageData(0, 0, c.width, c.height).data;
    landMask = (lo, la) => { const x = Math.floor((lo + 180) / 360 * c.width) % c.width, y = Math.min(c.height - 1, Math.floor((90 - la) / 180 * c.height)); const p = (y * c.width + x) * 4; return d[p] < 127 && d[p + 3] > 127; }; // land is dark in the GIBS mask
    const pts = [];
    for (let la = -58; la <= 80; la += .6) {
      const step = .6 / Math.max(.2, Math.cos(la * Math.PI / 180));
      for (let lo = -80; lo <= 110; lo += step) if (landMask(lo, la)) pts.push([lo, la]);
    }
    const dots = new THREE.InstancedMesh(new THREE.CircleGeometry(.018, 6), dotMat, pts.length);
    const o = new THREE.Object3D();
    pts.forEach(([lo, la], k) => { const v = ll(lo, la, R * 1.003); o.position.copy(v); o.lookAt(v.clone().multiplyScalar(2)); o.updateMatrix(); dots.setMatrixAt(k, o.matrix); });
    space.add(dots);
  };
  img.src = 'assets/land-mask.png';
}
{ // the story region's real 0.25° cells for the story month (harmonized burning days). Nothing else is drawn as fire.
  const P = [], SZ = [], SE = [], HT = [];
  const add = (lo, la, size, heat) => { const v = ll(lo, la, R * 1.01); P.push(v.x, v.y, v.z); SZ.push(size); SE.push(rnd()); HT.push(heat); };
  D.cells.forEach((c, k) => { const v = D.cellVal(k, D.AUG); if (v > 1.5) add(c.lon, c.lat, .05 + D.cellLogn(v) * .2, D.cellLogn(v)); });
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(P, 3));
  g.setAttribute('aSize', new THREE.Float32BufferAttribute(SZ, 1));
  g.setAttribute('aSeed', new THREE.Float32BufferAttribute(SE, 1));
  g.setAttribute('aHeat', new THREE.Float32BufferAttribute(HT, 1));
  space.add(new THREE.Points(g, new THREE.ShaderMaterial({ uniforms: { uTime: uniformsTime, uPx }, vertexShader: FX.fireVert, fragmentShader: FX.fireFrag,
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending })));
}
// country outlines on the globe (Natural Earth): Portugal and Lebanon
[[D.PT, 0x7fd3a6], [D.LB, 0x7fd3a6]].forEach(([poly, col]) => {
  space.add(new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(poly.map(([lo, la]) => ll(lo, la, R * 1.012))),
    new THREE.LineBasicMaterial({ color: col, transparent: true, opacity: .9, toneMapped: false })));
});
// target rings
const ringGeo = new THREE.RingGeometry(.92, 1, 64);
// one ring per region in the catalog (the centre of its analysis box)
const ORANGE = new THREE.Color(0xff8a3d), BLUE = new THREE.Color(0x8fc9ff);
const TARGETS = D.regions.map((r) => ({ id: r.id, name: r.name, lon: (r.bbox[0] + r.bbox[2]) / 2, lat: (r.bbox[1] + r.bbox[3]) / 2, s: .24 }));
TARGETS.forEach((t) => {
  const g = new THREE.Group(); const pos = ll(t.lon, t.lat, R * 1.015); g.position.copy(pos); g.lookAt(pos.clone().multiplyScalar(2));
  t.rings = [0, 1, 2].map(j => { const m = new THREE.Mesh(ringGeo, new THREE.MeshBasicMaterial({ color: BLUE, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false, side: THREE.DoubleSide })); g.add(m); return m; });
  t.dot = new THREE.Mesh(new THREE.CircleGeometry(.05, 20), new THREE.MeshBasicMaterial({ color: BLUE, toneMapped: false })); t.dot.position.z = .002; g.add(t.dot);
  t.group = g; t.pos = pos; space.add(g);
});
// The label always names the region in focus: the story region by default, the toured region on the orbit slide.
const focusLabel = document.createElement('div'); focusLabel.className = 'geo-label'; document.getElementById('satLabels').appendChild(focusLabel);
let focus = null;
function setFocus(id, sub) {
  const t = TARGETS.find((x) => x.id === id) || TARGETS.find((x) => x.id === D.story.id); if (!t) return;
  focus = t;
  TARGETS.forEach((x) => { const on = x === t; x.s = on ? .36 : .24; x.rings.forEach((m) => m.material.color.copy(on ? ORANGE : BLUE)); x.dot.material.color.copy(on ? ORANGE : BLUE); });
  focusLabel.innerHTML = '';
  focusLabel.append(t.name); const sm2 = document.createElement('small'); sm2.textContent = sub || ''; focusLabel.append(sm2);
  focusGoal.copy(t.pos).normalize();
  dirtyStage();
}
let dirtyStage = () => {};
function updateTargets(time, show) {
  TARGETS.forEach((t, k) => {
    t.rings.forEach((m, j) => { const c = (time * .35 + j / 3 + k * .17) % 1; const sc = t.s * (.25 + c * 1.1); m.scale.set(sc, sc, 1); m.material.opacity = (1 - c) * .85; });
  });
  const vis = !!focus && show && focus.pos.clone().normalize().dot(camera.position.clone().normalize()) > .25;
  if (vis) { proj.copy(focus.pos).project(camera); focusLabel.style.transform = `translate(${((proj.x + 1) / 2 * innerWidth + 16).toFixed(1)}px, ${((1 - proj.y) / 2 * innerHeight - 22).toFixed(1)}px)`; }
  focusLabel.style.opacity = vis ? 1 : 0;
}

/* satellites: near-polar, sun-synchronous orbits, each ground track crossing the story region. Real altitudes and swaths, time-lapsed. */
const dIb = ll(D.story.lon, D.story.lat, 1).normalize();
const NORTH = ll(0, 90, 1).normalize();
const EAST = new THREE.Vector3().crossVectors(NORTH, dIb).normalize();
const NTAN = new THREE.Vector3().crossVectors(dIb, EAST).normalize();
const EARTH_KM = 6371, LAPSE = 60; // one sim orbit ≈ 60 s
const SATS = [
  { name: 'Terra', inst: 'MODIS', cls: 'modis', col: 0xffc98a, altKm: 705, periodMin: 98.8, swathKm: 2330, tilt: -14, phase: -2.3 },
  { name: 'Aqua', inst: 'MODIS', cls: 'modis', col: 0xffc98a, altKm: 705, periodMin: 98.8, swathKm: 2330, tilt: 11, phase: 1.4 },
  { name: 'Suomi NPP', inst: 'VIIRS', cls: 'viirs', col: 0x7fd3a6, altKm: 824, periodMin: 101, swathKm: 3040, tilt: -5, phase: -.75 },
  { name: 'NOAA-20', inst: 'VIIRS', cls: 'viirs', col: 0x7fd3a6, altKm: 824, periodMin: 101, swathKm: 3040, tilt: 4, phase: -.75 + Math.PI }, // half an orbit ahead of Suomi NPP
];
const labelsBox = document.getElementById('satLabels');
const goldMat = new THREE.MeshStandardMaterial({ color: 0xd2a94e, metalness: .95, roughness: .3, emissive: 0x2a1c05 });
const panelMat = new THREE.MeshStandardMaterial({ color: 0x1a2c58, metalness: .6, roughness: .25, emissive: 0x0c1a3a, side: THREE.DoubleSide });
space.add(new THREE.HemisphereLight(0x8fb8ff, 0x000000, .5));
const sunLight = new THREE.DirectionalLight(0xffffff, 2.5); sunLight.position.copy(SUN).multiplyScalar(20); space.add(sunLight);
SATS.forEach(s => {
  const axis = NORTH.clone().applyAxisAngle(dIb, s.tilt * Math.PI / 180);
  s.n = new THREE.Vector3().crossVectors(dIb, axis).normalize();
  s.u = dIb.clone(); s.v = new THREE.Vector3().crossVectors(s.n, s.u).normalize();
  s.RO = R * (1 + s.altKm / EARTH_KM);
  s.omega = Math.PI * 2 / LAPSE * (98.8 / s.periodMin);
  const half = s.swathKm / 2 / EARTH_KM * R;
  const pts = []; for (let k = 0; k <= 200; k++) { const th = k / 200 * Math.PI * 2; pts.push(s.u.clone().multiplyScalar(Math.cos(th) * s.RO).addScaledVector(s.v, Math.sin(th) * s.RO)); }
  s.orbit = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: s.col, transparent: true, opacity: .16, toneMapped: false }));
  space.add(s.orbit);
  const g = new THREE.Group();
  g.add(new THREE.Mesh(new THREE.BoxGeometry(.13, .1, .18), goldMat));
  [-1, 1].forEach(sd => { const pn = new THREE.Mesh(new THREE.PlaneGeometry(.36, .11), panelMat); pn.position.x = sd * .26; pn.rotation.x = -Math.PI / 2; g.add(pn); });
  const h = s.RO - R;
  s.cone = new THREE.Mesh(new THREE.ConeGeometry(half, h, 40, 1, true).translate(0, -h / 2, 0),
    new THREE.MeshBasicMaterial({ color: s.col, transparent: true, opacity: .07, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, toneMapped: false }));
  g.add(s.cone);
  const foot = new THREE.Mesh(new THREE.CircleGeometry(half, 48).rotateX(-Math.PI / 2),
    new THREE.MeshBasicMaterial({ color: s.col, transparent: true, opacity: .12, blending: THREE.AdditiveBlending, depthWrite: false, toneMapped: false }));
  foot.position.y = -h + .03; g.add(foot);
  const beacon = new THREE.Mesh(new THREE.SphereGeometry(.022, 8, 8), new THREE.MeshBasicMaterial({ color: s.col, toneMapped: false })); beacon.position.y = .08; g.add(beacon);
  s.group = g; space.add(g);
  s.el = document.createElement('div'); s.el.className = 'sat-label ' + s.cls; s.el.innerHTML = `${s.name}<small>${s.inst} · ${s.altKm} km</small>`; labelsBox.appendChild(s.el);
});
const mB = new THREE.Matrix4(), xA = new THREE.Vector3(), yA = new THREE.Vector3(), zA = new THREE.Vector3(), proj = new THREE.Vector3();
window.__sats = SATS.map(s => ({ name: s.name, cls: s.cls }));
function updateSats(time, show) {
  const sel = window.__selSat ?? 2;
  SATS.forEach((s, k) => {
    const th = s.phase + time * s.omega;
    const pos = s.u.clone().multiplyScalar(Math.cos(th) * s.RO).addScaledVector(s.v, Math.sin(th) * s.RO);
    yA.copy(pos).normalize();
    zA.copy(s.u).multiplyScalar(-Math.sin(th)).addScaledVector(s.v, Math.cos(th)).normalize();
    xA.crossVectors(yA, zA);
    mB.makeBasis(xA, yA, zA); s.group.quaternion.setFromRotationMatrix(mB); s.group.position.copy(pos);
    const on = k === sel;
    s.orbit.material.opacity = on ? .55 : .14; s.cone.material.opacity = on ? .12 : .06;
    const visible = show && yA.dot(camera.position.clone().normalize()) > .15;
    if (visible) { proj.copy(pos).project(camera); s.el.style.transform = `translate(${((proj.x + 1) / 2 * innerWidth + 12).toFixed(1)}px, ${((1 - proj.y) / 2 * innerHeight - 8).toFixed(1)}px)`; }
    s.el.style.opacity = visible ? 1 : 0; s.el.classList.toggle('on', on);
    // ground-relative state for the radar: distance and bearing from the story region, time to the next overhead pass
    const ang = Math.acos(clamp(yA.dot(dIb), -1, 1));
    const rem = ((Math.PI * 2 - (th % (Math.PI * 2))) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2);
    Object.assign(window.__sats[k], { distKm: ang * EARTH_KM, bearing: Math.atan2(yA.dot(EAST), yA.dot(NTAN)), mins: rem / (Math.PI * 2) * s.periodMin });
  });
}

/* =========================================================
   GROUND: the record as slabs, the hottest months on fire
   ========================================================= */
const ground = new THREE.Scene();
ground.background = new THREE.Color(0x04080a);
ground.fog = new THREE.Fog(0x04080a, 17, 42);
const pmrem = new THREE.PMREMGenerator(renderer);
ground.environment = pmrem.fromScene(new RoomEnvironment(renderer), 0.04).texture;
ground.add(new THREE.HemisphereLight(0x7aa0b8, 0x05090b, 0.26));
const sun = new THREE.DirectionalLight(0xffa868, 1.6);
sun.position.set(-8, 15, 6); sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left: -15, right: 15, top: 15, bottom: -15, near: 1, far: 50 });
sun.shadow.bias = -0.0004; sun.shadow.normalBias = 0.02;
ground.add(sun, sun.target);
const rim = new THREE.DirectionalLight(0x6fa8ff, 0.6); rim.position.set(6, 5, -10); ground.add(rim);

function canopyTexture() {
  const c = document.createElement('canvas'); c.width = c.height = 1024;
  const g = c.getContext('2d'); g.fillStyle = '#fff'; g.strokeStyle = '#fff';
  let a = 11; const r = () => { a = (a * 16807) % 2147483647; return a / 2147483647; };
  for (let k = 0; k < 22; k++) {
    const x = r() * 1024, y = r() * 1024, L = 200 + r() * 320, ang = (r() - .5) * .5, lw = 3 + r() * 4;
    const pads = []; for (let s = 0; s < L; s += 7) { const w = (1 - s / L) * 64 + 10; for (let n = 0; n < 3; n++) pads.push([s, (r() - .5) * w * .5, 5 + r() * 9, 2 + r() * 3, (r() - .5) * .6]); }
    for (const [dx, dy] of [[0, 0], [-1024, 0], [0, -1024], [-1024, -1024], [1024, 0], [0, 1024]]) {
      g.save(); g.translate(x + dx, y + dy); g.rotate(ang);
      g.lineWidth = lw; g.beginPath(); g.moveTo(0, 0); g.lineTo(L, 0); g.stroke();
      for (const p of pads) { g.beginPath(); g.ellipse(p[0], p[1], p[2], p[3], p[4], 0, Math.PI * 2); g.fill(); }
      g.restore();
    }
  }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(2.2, 2.2); return t;
}
const canopyTex = canopyTexture();
const canopy = new THREE.Mesh(new THREE.PlaneGeometry(70, 70).rotateX(-Math.PI / 2),
  new THREE.MeshBasicMaterial({ colorWrite: false, depthWrite: false, side: THREE.DoubleSide }));
canopy.position.y = 9; canopy.castShadow = true;
canopy.customDepthMaterial = new THREE.MeshDepthMaterial({ depthPacking: THREE.RGBADepthPacking, map: canopyTex, alphaTest: 0.5, side: THREE.DoubleSide });
ground.add(canopy);

const floor = new THREE.Mesh(new THREE.PlaneGeometry(90, 90).rotateX(-Math.PI / 2),
  new THREE.MeshStandardMaterial({ color: 0x111b1a, roughness: .93, metalness: 0 }));
floor.position.y = -0.16; floor.receiveShadow = true; ground.add(floor);
{
  const pts = []; for (let x = -15; x <= 15; x += .6) for (let z = -15; z <= 15; z += .6) pts.push(x, -0.15, z);
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pts, 3));
  ground.add(new THREE.Points(g, new THREE.PointsMaterial({ color: 0x2f4741, size: .035, sizeAttenuation: true })));
}
const plate = new THREE.Mesh(new RoundedBoxGeometry(8.8, 0.16, 12.4, 4, 0.3),
  new THREE.MeshPhysicalMaterial({ color: 0x0c1618, roughness: .35, metalness: .1, clearcoat: 1, clearcoatRoughness: .2 }));
plate.castShadow = plate.receiveShadow = true; ground.add(plate);

// the story region fills the plate: Lebanon is about 1.6° across, so the map scale is large
const MLON = D.story.lon, MLAT = D.story.lat, MS = 6.2 / Math.max(D.story.bbox[2] - D.story.bbox[0], D.story.bbox[3] - D.story.bbox[1]);
const CELL = 0.25 * MS * 0.9;
const mx = lon => (lon - MLON) * MS, mz = lat => -(lat - MLAT) * MS;
const land = new THREE.Mesh(new THREE.ShapeGeometry(new THREE.Shape(D.OUT.map(([lo, la]) => new THREE.Vector2(mx(lo), (la - MLAT) * MS)))).rotateX(-Math.PI / 2),
  new THREE.MeshStandardMaterial({ color: 0x18241f, roughness: .9 }));
land.receiveShadow = true; ground.add(land);
land.add(new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(D.OUT.map(([lo, la]) => new THREE.Vector3(mx(lo), 0.012, mz(la)))),
  new THREE.LineBasicMaterial({ color: 0x7fd3a6, transparent: true, opacity: .6 })));
const selRect = new THREE.Line(new THREE.BufferGeometry().setFromPoints([[35.35, 34.05], [35.85, 34.05], [35.85, 33.65], [35.35, 33.65], [35.35, 34.05]] /* a box around Beirut */.map(([lo, la]) => new THREE.Vector3(mx(lo), 0, mz(la)))),
  new THREE.LineDashedMaterial({ color: 0xff8a3d, dashSize: .2, gapSize: .13, transparent: true, toneMapped: false }));
selRect.computeLineDistances(); selRect.position.y = 1.0; ground.add(selRect);

/* slabs */
const N = D.N;
const slabMat = new THREE.MeshPhysicalMaterial({ roughness: .36, metalness: .04, clearcoat: .7, clearcoatRoughness: .25, envMapIntensity: .5 });
slabMat.onBeforeCompile = (sh) => {
  sh.fragmentShader = sh.fragmentShader.replace('#include <emissivemap_fragment>', `#include <emissivemap_fragment>
  #ifdef USE_COLOR
    float lum = dot(vColor.rgb, vec3(0.3, 0.59, 0.11));
    totalEmissiveRadiance += vColor.rgb * smoothstep(0.55, 0.85, lum) * 0.7;
  #endif`);
};
const slabs = new THREE.InstancedMesh(new RoundedBoxGeometry(1, 1, 1, 3, 0.12), slabMat, N);
slabs.castShadow = slabs.receiveShadow = true;
slabs.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
ground.add(slabs);

const colOf = (v) => { const c = new THREE.Color(); if (v == null) return c.setHex(0x1a2326); const a = D.colorFor(v); return c.setRGB(a[0] / 255, a[1] / 255, a[2] / 255, THREE.SRGBColorSpace); };
const hOf = (v) => v == null ? 0.03 : 0.06 + D.logn(v) * 2.5;
const mkState = () => ({ pos: new Float32Array(N * 3), quat: new Float32Array(N * 4), scl: new Float32Array(N * 3), col: new Float32Array(N * 3), val: new Float32Array(N), hot: [] });
const I = new THREE.Quaternion(), Q = new THREE.Quaternion();
function put(s, i, x, y, z, q, sx, sy, sz, c, v) {
  s.pos[i * 3] = x; s.pos[i * 3 + 1] = y; s.pos[i * 3 + 2] = z; q.toArray(s.quat, i * 4);
  s.scl[i * 3] = sx; s.scl[i * 3 + 1] = sy; s.scl[i * 3 + 2] = sz;
  s.col[i * 3] = c.r; s.col[i * 3 + 1] = c.g; s.col[i * 3 + 2] = c.b; s.val[i] = v == null ? 0 : v;
}
// layouts: 0 sky (falling in from the dive), 1 calendar, 2 naive bars, 3 harmonized bars, 4 map, 5 season ring
const L = [mkState(), mkState(), mkState(), mkState(), mkState(), mkState()];
const gx = m => (m - 5.5) * 0.66, gz = y => (y - (D.NY - 1) / 2) * 0.44;
const cellCol = (v) => { const c = new THREE.Color(); const a = D.cellColor(v); return c.setRGB(a[0] / 255, a[1] / 255, a[2] / 255, THREE.SRGBColorSpace); };
const HC = D.H.map(colOf), NC = D.NV.map(colOf);
const AUG25 = D.AUG, UP = new THREE.Vector3(0, 1, 0);
for (let i = 0; i < N; i++) {
  const y = Math.floor(i / 12), m = i % 12;
  Q.setFromEuler(new THREE.Euler(rnd() * 6, rnd() * 6, rnd() * 6));
  put(L[0], i, (rnd() - .5) * 18, 7 + rnd() * 9, (rnd() - .5) * 14, Q, .58, .06, .38, HC[i], D.H[i]);
  put(L[1], i, gx(m), 0.05, gz(y), I, .58, .06, .38, HC[i], D.H[i]);
  const hn = hOf(D.NV[i]); put(L[2], i, gx(m), 0.02 + hn / 2, gz(y), I, .58, hn, .38, NC[i], D.NV[i]);
  const hh = hOf(D.H[i]); put(L[3], i, gx(m), 0.02 + hh / 2, gz(y), I, .58, hh, .38, HC[i], D.H[i]);
  const th = (m + .5) / 12 * Math.PI * 2 - Math.PI / 2, r = 1.5 + y * .155, hr = 0.05 + D.logn(D.H[i]) * 1.7;
  Q.setFromAxisAngle(UP, -th - Math.PI / 2);
  put(L[5], i, Math.cos(th) * r, 0.02 + hr / 2, Math.sin(th) * r, Q, Math.min(.85, 2 * Math.PI * r / 12 * .8), hr, .12, HC[i], D.H[i]);
  if (i < D.C) {
    const c = D.cells[i], v = D.cellVal(i, AUG25), h = 0.04 + D.cellLogn(v) * 1.9;
    put(L[4], i, mx(c.lon), 0.02 + h / 2, mz(c.lat), I, CELL, h, CELL, cellCol(v), v);
  } else put(L[4], i, (rnd() - .5) * 16, -1.6, (rnd() - .5) * 12, I, .2, .02, .2, HC[i], 0);
}
// which slabs burn in each layout: the months (or cells) above a threshold, hottest first
function hotList(s, thr, cap, fMin, fMax) {
  const idx = []; for (let i = 0; i < N; i++) if (s.val[i] > thr) idx.push(i);
  idx.sort((a, b) => s.val[b] - s.val[a]);
  const top = s.val[idx[0]] || 1;
  return idx.slice(0, cap).map(i => ({ i, f: clamp(Math.log(s.val[i] / thr) / Math.log(top / thr || 2)), fMin, fMax }));
}
// thresholds scale with the region: the months above 13% of its busiest month burn, and cells above 6% of its busiest cell
const THR = D.vmax * 0.13, CTHR = D.cmax * 0.06;
L[1].hot = hotList(L[1], THR, 18, .45, 1.2);
L[2].hot = hotList(L[2], THR, 30, .5, 1.35);
L[3].hot = hotList(L[3], THR, 18, .5, 1.3);
L[4].hot = hotList(L[4], CTHR, 18, .4, 1.1);
L[5].hot = hotList(L[5], THR, 18, .35, .95);
L[0].hot = L[1].hot;
const delay = new Float32Array(N).map((_, i) => (i % 12) / 11 * .35 + Math.floor(i / 12) / (D.NY - 1) * .65);
const curPos = new Float32Array(N * 3), curH = new Float32Array(N);

/* flames: two pools so one layout's fire can hand over to the next */
const flameGeo = new THREE.PlaneGeometry(1, 1).translate(0, .5, 0);
const flameVert = `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }`;
function makePool(n) {
  const arr = [];
  for (let k = 0; k < n; k++) {
    const mat = new THREE.ShaderMaterial({
      uniforms: { uTime: uniformsTime, uSeed: { value: rnd() }, uAlpha: { value: 0 } },
      vertexShader: flameVert, fragmentShader: FX.flameFrag,
      transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, side: THREE.DoubleSide, toneMapped: false
    });
    const m = new THREE.Mesh(flameGeo, mat); m.visible = false; m.renderOrder = 5; m.frustumCulled = false;
    ground.add(m); arr.push(m);
  }
  return arr;
}
const poolA = makePool(48), poolB = makePool(48);
const smokeMats = [], smokes = [];
for (let k = 0; k < 16; k++) {
  const mat = new THREE.ShaderMaterial({ uniforms: { uTime: uniformsTime, uSeed: { value: rnd() }, uAlpha: { value: 0 } },
    vertexShader: flameVert, fragmentShader: FX.smokeFrag, transparent: true, depthWrite: false });
  const m = new THREE.Mesh(new THREE.PlaneGeometry(1, 1), mat); m.visible = false; m.renderOrder = 4; m.frustumCulled = false;
  m.userData.phase = k / 16; ground.add(m); smokes.push(m); smokeMats.push(mat);
}
const fireLights = [0, 1, 2].map(() => { const l = new THREE.PointLight(0xff7a2a, 0, 7, 1.6); ground.add(l); return l; });

/* embers rising from whatever is burning */
const EM = small() ? 220 : 520;
const emP = new Float32Array(EM * 3), emV = new Float32Array(EM * 3), emL = new Float32Array(EM), emMax = new Float32Array(EM), emS = new Float32Array(EM);
for (let k = 0; k < EM; k++) { emL[k] = 0; emS[k] = .05 + rnd() * .09; }
const emGeo = new THREE.BufferGeometry();
emGeo.setAttribute('position', new THREE.BufferAttribute(emP, 3));
emGeo.setAttribute('aLife', new THREE.BufferAttribute(new Float32Array(EM), 1));
emGeo.setAttribute('aSize', new THREE.BufferAttribute(emS, 1));
const embers = new THREE.Points(emGeo, new THREE.ShaderMaterial({ uniforms: { uPx }, vertexShader: FX.emberVert, fragmentShader: FX.emberFrag,
  transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
embers.frustumCulled = false; ground.add(embers);

/* full-screen wall of fire for the dive */
const wallMat = new THREE.ShaderMaterial({
  uniforms: { uTime: uniformsTime, uAmt: { value: 0 }, uAspect: { value: 1 }, uC0: { value: new THREE.Vector3() }, uC1: { value: new THREE.Vector3() }, uC2: { value: new THREE.Vector3() }, uC3: { value: new THREE.Vector3() } },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=vec4(position.xy,0.,1.); }`,
  fragmentShader: FX.wallFrag, transparent: true, depthTest: false, depthWrite: false
});
const overlay = new THREE.Scene(), orthoCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
const wall = new THREE.Mesh(new THREE.PlaneGeometry(2, 2), wallMat); wall.frustumCulled = false; overlay.add(wall);

/* =========================================================
   CAMERA SHOTS
   0 hero · 1 orbit · [dive 1.5] · 2–7 ground · [ascent 7.5] · 8 methodology · 9 about
   ========================================================= */
const dLb = ll(35.6, 33.9, 1).normalize();
const focusDir = dIb.clone(), focusGoal = dIb.clone(), SCAM1_OFF_P = V(2.0, 1.8, 0), SCAM1_OFF_L = V(-.6, 0, 0);
const SCAM = {
  0: { p: V(3.6, 1.2, 16.6), l: V(3.6, 1.0, 0), f: 38 },
  1: { p: dIb.clone().multiplyScalar(9.4).add(V(2.0, 1.8, 0)), l: dIb.clone().multiplyScalar(4.9).add(V(-.6, 0, 0)), f: 40 },
  dive: { p: dIb.clone().multiplyScalar(5.25).add(V(.15, .1, 0)), l: dIb.clone().multiplyScalar(4.2), f: 64 },
  rise: { p: dIb.clone().multiplyScalar(5.3), l: dIb.clone().multiplyScalar(9).add(V(0, 3, 0)), f: 70 },
  9: { p: V(-2.6, 2.6, 19.5), l: V(-4.4, -.6, 0), f: 40 },
  10: { p: dLb.clone().multiplyScalar(9.6).add(V(1.2, .2, 0)), l: dLb.clone().multiplyScalar(5).add(V(-3.1, -1.6, 0)), f: 38 },
};
const GENTRY = { p: V(0, 24, 3), l: V(0, 0, 0), f: 55, shift: 0 };
const GEXIT = { p: V(0, 28, 4), l: V(0, 0, 0), f: 62, shift: 0 };
const GCAM = {
  2: { p: V(6.5, 10, 9.5), l: V(.3, 0, .4), f: 34, shift: 1 },
  3: { p: V(-8.5, 5.4, 8.6), l: V(0, .8, 0), f: 36, shift: 1 },
  4: { p: V(8.6, 4.8, 8.2), l: V(0, .8, 0), f: 36, shift: 1 },
  5: { p: V(.6, 13.5, 7.2), l: V(0, 0, .3), f: 38, shift: 1 },
  6: { p: V(.5, 15.5, 11.5), l: V(0, .2, .6), f: 38, shift: 1 },
  7: { p: V(-6, 15, 14), l: V(0, 0, 0), f: 34, shift: 0 },
  8: { p: V(5.5, 15, 13), l: V(0, 0, 0), f: 34, shift: 0 },
};
const SHOT_LAYOUT = { 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 1, 8: 1 };
const LIFT = { '1-2': 0, '2-3': 0, '3-4': 1, '4-5': 1, '5-1': 1, '0-1': 0 };
const FIRE_PAL = [V(.5, .03, 0), V(1, .32, .03), V(1, .7, .2), V(1, .95, .8)];
const PLASMA_PAL = [V(.03, .08, .3), V(.15, .45, 1), V(.55, .85, 1), V(.95, .98, 1)];

/* post */
const composer = new EffectComposer(renderer);
const renderPass = new RenderPass(space, camera);
composer.addPass(renderPass);
const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), .62, .6, .78);
composer.addPass(bloom);
composer.addPass(new OutputPass());

function resize() {
  const w = innerWidth, h = innerHeight;
  renderer.setSize(w, h, false); composer.setSize(w, h);
  camera.aspect = w / h; camera.updateProjectionMatrix();
  bloom.enabled = w >= 700 && !light;
  wallMat.uniforms.uAspect.value = w / h;
}
addEventListener('resize', resize); resize();

/* scroll → shot progress */
const shots = [...document.querySelectorAll('[data-shot]')].sort((a, b) => a.dataset.shot - b.dataset.shot);
function scrollP() { return Math.min(6, window.__slide || 0); }
let pS = scrollP(), fovKick = 0, snap = false, fly = null;
window.__cut = () => { snap = true; };
// page-to-page flight: the camera travels through every shot between here and there
const warpEl = null;
window.__flyTo = (to, done) => {
  if (reduce) return false;
  fly = { from: pS, to, t0: performance.now(), dur: 1500 + Math.min(900, Math.abs(to - pS) * 110), done };
  return fly.dur;
};
const easeQuint = u => u < .5 ? 4 * u ** 3 : 1 - (-2 * u + 2) ** 3 / 2; // gentle in-out
let mX = 0, mY = 0, tmX = 0, tmY = 0;
addEventListener('pointermove', e => { tmX = e.clientX / innerWidth * 2 - 1; tmY = e.clientY / innerHeight * 2 - 1; });

/* loop */
const clock = new THREE.Clock();
const m4 = new THREE.Matrix4(), vP = new THREE.Vector3(), vS = new THREE.Vector3(), qA = new THREE.Quaternion(), cA = new THREE.Color();
const qBuf = new Float32Array(4), camP = new THREE.Vector3(), camL = new THREE.Vector3();
let time = 0, first = true, dirty = true;
dirtyStage = () => { dirty = true; };
// the tour on the orbit slide calls this; an unknown id falls back to the story region
window.__stageFocus = (id, sub) => setFocus(id, sub);
setFocus(D.story.id, D.storySub);
if (window.__stageFocusWanted) setFocus(...window.__stageFocusWanted);
addEventListener('resize', () => { dirty = true; });
new MutationObserver(() => { dirty = true; }).observe(document.documentElement, { attributes: true, attributeFilter: ['class'] });
const DIVE = 1.5, RISE = 8.5;

function blendLayouts(la, lb, t, lift) {
  const A = L[la], B = L[lb];
  for (let i = 0; i < N; i++) {
    const ti = la === lb ? 1 : ease(clamp(t * 1.7 - delay[i] * .7));
    const i3 = i * 3;
    vP.set(A.pos[i3] + (B.pos[i3] - A.pos[i3]) * ti, A.pos[i3 + 1] + (B.pos[i3 + 1] - A.pos[i3 + 1]) * ti + Math.sin(Math.PI * ti) * .9 * lift, A.pos[i3 + 2] + (B.pos[i3 + 2] - A.pos[i3 + 2]) * ti);
    THREE.Quaternion.slerpFlat(qBuf, 0, A.quat, i * 4, B.quat, i * 4, ti); qA.fromArray(qBuf);
    vS.set(A.scl[i3] + (B.scl[i3] - A.scl[i3]) * ti, A.scl[i3 + 1] + (B.scl[i3 + 1] - A.scl[i3 + 1]) * ti, A.scl[i3 + 2] + (B.scl[i3 + 2] - A.scl[i3 + 2]) * ti);
    m4.compose(vP, qA, vS); slabs.setMatrixAt(i, m4);
    curPos[i3] = vP.x; curPos[i3 + 1] = vP.y; curPos[i3 + 2] = vP.z; curH[i] = vS.y;
    cA.setRGB(A.col[i3] + (B.col[i3] - A.col[i3]) * ti, A.col[i3 + 1] + (B.col[i3 + 1] - A.col[i3 + 1]) * ti, A.col[i3 + 2] + (B.col[i3 + 2] - A.col[i3 + 2]) * ti);
    slabs.setColorAt(i, cA);
  }
  slabs.instanceMatrix.needsUpdate = true; slabs.instanceColor.needsUpdate = true;
}
const active = []; // flames that can spawn embers this frame: [x,y,z,strength]
function driveFlames(pool, list, alpha, layoutIdx) {
  for (let k = 0; k < pool.length; k++) {
    const m = pool[k], h = list[k];
    if (!h || alpha < .01) { m.visible = false; continue; }
    const i = h.i, i3 = i * 3;
    const flick = 1 + .08 * Math.sin(time * 9 + k * 1.7) + .06 * Math.sin(time * 13.3 + k);
    const hgt = (h.fMin + (h.fMax - h.fMin) * h.f) * flick;
    const wid = Math.min(hgt * .62, layoutIdx === 4 ? .5 : .62);
    const x = curPos[i3], y = curPos[i3 + 1] + curH[i] / 2 - .02, z = curPos[i3 + 2];
    m.position.set(x, y, z);
    m.rotation.set(0, Math.atan2(camera.position.x - x, camera.position.z - z), 0);
    m.scale.set(wid, hgt, 1);
    m.material.uniforms.uAlpha.value = alpha * (.5 + .3 * h.f);
    m.visible = true;
    active.push([x, y + hgt * .55, z, alpha * (.4 + h.f)]);
  }
}
function spawnEmber(k) {
  if (!active.length) { emL[k] = 0; return; }
  const a = active[Math.floor(rnd() * active.length)];
  if (rnd() > a[3]) { emL[k] = 0; return; }
  emP[k * 3] = a[0] + (rnd() - .5) * .3; emP[k * 3 + 1] = a[1]; emP[k * 3 + 2] = a[2] + (rnd() - .5) * .3;
  emV[k * 3] = (rnd() - .5) * .5; emV[k * 3 + 1] = .9 + rnd() * 1.6; emV[k * 3 + 2] = (rnd() - .5) * .5;
  emMax[k] = emL[k] = 1.4 + rnd() * 2.2;
}

function lerpCam(ca, cb, ct) { camL.lerpVectors(ca.l, cb.l, ct); camP.lerpVectors(ca.p, cb.p, ct); return ca.f + (cb.f - ca.f) * ct; }

function frame() {
  requestAnimationFrame(frame);
  if (document.hidden || window.__stageHidden) { clock.getDelta(); lastT = 0; return; }
  if (still() && !fly && !first && Math.abs(scrollP() - pS) < 1e-3 && !dirty && focusDir.distanceToSquared(focusGoal) < 1e-6) { clock.getDelta(); lastT = 0; return; }
  dirty = false;
  // A slow GPU gets a lighter picture: after 40 slow frames, no bloom, no shadows, one pixel per pixel.
  { const now = performance.now(); if (lastT && now - lastT > 45) slowFrames += 1; lastT = now;
    if (slowFrames > 40 && !light) { light = true; bloom.enabled = false; renderer.setPixelRatio(1); renderer.shadowMap.enabled = false; sun.castShadow = false; resize(); } }
  const dt = Math.min(clock.getDelta(), .05);
  if (!still()) time += dt;
  uniformsTime.value = time;
  let flyU = 0;
  if (fly) {
    const u = clamp((performance.now() - fly.t0) / fly.dur);
    pS = fly.from + (fly.to - fly.from) * easeQuint(u); flyU = u;
    if (u >= 1) { const f = fly; fly = null; f.done && f.done(); snap = true; }
  } else {
    const p = scrollP();
    if (snap || reduce) { pS = p; snap = false; } else pS += (p - pS) * Math.min(1, dt * 3.2);
  }
  const speed = Math.sin(Math.PI * flyU);
  if (warpEl) { warpEl.style.opacity = (speed * .85).toFixed(3); warpEl.style.transform = `scale(${(1 + flyU * .6).toFixed(3)}) rotate(${(flyU * 8).toFixed(2)}deg)`; }
  const aspect = innerWidth / innerHeight, fit = aspect < .8 ? 1.75 : aspect < 1.3 ? 1.3 : 1;
  mX += (tmX - mX) * .04; mY += (tmY - mY) * .04;
  let fov;
  const inSpace = pS < DIVE || pS >= RISE;
  updateSats(time, inSpace && (pS < 1.25 || (pS > 8.8 && pS < 9.6)));
  updateTargets(time, inSpace && pS < 1.6);
  focusDir.lerp(focusGoal, Math.min(1, dt * 3)).normalize();
  SCAM[1].p.copy(focusDir).multiplyScalar(9.4).add(SCAM1_OFF_P); SCAM[1].l.copy(focusDir).multiplyScalar(4.9).add(SCAM1_OFF_L);

  if (inSpace) {
    renderPass.scene = space; bloom.strength = .62; renderer.toneMappingExposure = 1.05;
    if (pS < 1) { fov = lerpCam(SCAM[0], SCAM[1], sm(pS)); }
    else if (pS < DIVE) { fov = lerpCam(SCAM[1], SCAM.dive, Math.pow((pS - 1) / (DIVE - 1), 1.6)); }
    else if (pS < 9) { fov = lerpCam(SCAM.rise, SCAM[9], 1 - Math.pow(1 - (pS - RISE) / (9 - RISE), 1.6)); }
    else { fov = lerpCam(SCAM[9], SCAM[10], sm(clamp(pS - 9))); }
    if (aspect < 1.1) { // portrait: centre the globe and pull back
      const k = pS < 1 ? 1 - clamp(pS) : pS >= 9 ? 1 : 0;
      camL.x -= 3.6 * k; camP.x -= 3.6 * k; camL.y -= 2.6 * k; // the globe sits behind the copy, centred
      camP.sub(camL).multiplyScalar(1 + .7 * k).add(camL);
    }
    if (!still()) { const w = pS < DIVE ? 1 - clamp(pS - 1) : clamp((pS - RISE) * 2); camP.x += mX * .5 * w; camP.y += -mY * .3 * w; }
    camera.position.copy(camP); camera.lookAt(camL);
    earth.rotation.y = -(LON0 + 90) * Math.PI / 180; 
    dotMat.opacity = .24 * clamp((camera.position.length() - 9) / 6);
  } else {
    /* ---------- GROUND ---------- */
    renderPass.scene = ground; bloom.strength = .3; renderer.toneMappingExposure = .92;
    let la, lb, t, lift, ca, cb, ct;
    if (pS < 2) {
      t = (pS - DIVE) / (2 - DIVE); la = 0; lb = 1; lift = 0; ca = GENTRY; cb = GCAM[2]; ct = sm(t);
    } else if (pS > 8) {
      t = 1; la = lb = 1; lift = 0; ca = GCAM[8]; cb = GEXIT; ct = Math.pow((pS - 8) / (RISE - 8), 1.6);
    } else {
      const a = Math.min(Math.floor(pS), 7), b = Math.min(a + 1, 8);
      t = clamp(pS - a); la = SHOT_LAYOUT[a]; lb = SHOT_LAYOUT[b];
      lift = LIFT[la + '-' + lb] ?? 1; ca = GCAM[a]; cb = GCAM[b]; ct = sm(t);
    }
    blendLayouts(la, lb, t, lift);
    const near = k => clamp(1 - Math.abs(pS - k) / .75);
    const plateVis = Math.max(clamp((pS - 1.6) / .4) * (1 - clamp((pS - 4.25) / .6)), clamp((pS - 6.3) / .7));
    plate.position.y = -0.06 - (1 - sm(plateVis)) * 1.4;
    land.position.y = -(1 - sm(near(5))) * 1.2;
    selRect.material.opacity = near(5); selRect.visible = near(5) > .01;
    canopyTex.offset.set(time * .004, Math.sin(time * .15) * .01);
    canopy.rotation.y = Math.sin(time * .12) * .02;

    active.length = 0;
    const fadeIn = clamp((pS - DIVE) / .35);
    const wA = la === lb ? 1 : 1 - sm(clamp((t - .25) / .5)), wB = la === lb ? 0 : sm(clamp((t - .25) / .5));
    driveFlames(poolA, L[la].hot, wA * fadeIn, la);
    driveFlames(poolB, la === lb ? [] : L[lb].hot, wB * fadeIn, lb);
    const lead = wA >= wB ? poolA : poolB;
    fireLights.forEach((l, k) => {
      const m = lead[k];
      if (m && m.visible) { l.position.set(m.position.x, m.position.y + m.scale.y * .45, m.position.z); l.intensity = (3.2 + 1.4 * Math.sin(time * 11 + k * 2) + .9 * Math.sin(time * 17.7 + k)) * m.material.uniforms.uAlpha.value; }
      else l.intensity = 0;
    });
    smokes.forEach((s, k) => {
      const m = lead[k % 8];
      if (!m || !m.visible) { s.visible = false; return; }
      const c = (time * .11 + s.userData.phase) % 1;
      s.position.set(m.position.x + Math.sin(time * .3 + k) * .4 * c, m.position.y + m.scale.y * .8 + c * 3.4, m.position.z);
      s.quaternion.copy(camera.quaternion);
      const sc = .9 + c * 2.6; s.scale.set(sc, sc, 1);
      s.material.uniforms.uAlpha.value = Math.sin(Math.PI * c) * .55 * m.material.uniforms.uAlpha.value;
      s.visible = true;
    });
    const lifeAttr = emGeo.attributes.aLife;
    for (let k = 0; k < EM; k++) {
      if (emL[k] <= 0) { if (rnd() < .5) spawnEmber(k); lifeAttr.array[k] = 0; continue; }
      emL[k] -= dt;
      emV[k * 3] += Math.sin(time * 1.3 + k) * dt * .6; emV[k * 3 + 2] += Math.cos(time * 1.1 + k * .7) * dt * .6;
      emP[k * 3] += emV[k * 3] * dt; emP[k * 3 + 1] += emV[k * 3 + 1] * dt; emP[k * 3 + 2] += emV[k * 3 + 2] * dt;
      lifeAttr.array[k] = clamp(emL[k] / emMax[k]);
    }
    emGeo.attributes.position.needsUpdate = true; lifeAttr.needsUpdate = true;

    const shiftX = aspect > 1.2 ? (aspect < 1.7 ? -3.8 : -2.8) : 0;
    fov = lerpCam(ca, cb, ct);
    const sh = (ca.shift + (cb.shift - ca.shift) * ct) * shiftX;
    camP.sub(camL).multiplyScalar(fit).add(camL);
    camL.x += sh; camP.x += sh;
    if (!still()) { camP.x += mX * .7 + Math.sin(time * .1) * .35; camP.y += -mY * .35; }
    camera.position.copy(camP); camera.lookAt(camL);
  }
  fovKick *= .92;
  camera.fov = fov + fovKick + speed * 4 + (aspect < .8 ? 6 : 0); camera.updateProjectionMatrix();
  uPx.value = renderer.domElement.height * .5 / Math.tan(camera.fov * Math.PI / 360);

  composer.render();
  // the two thresholds between worlds: a wall of fire going down, a plasma glow coming back up
  const wDive = .8 * sm(clamp(1 - Math.abs(pS - DIVE) / .22)), wRise = .8 * sm(clamp(1 - Math.abs(pS - RISE) / .22));
  const wa = Math.max(wDive, wRise);
  if (wa > .005) {
    const pal = wDive >= wRise ? FIRE_PAL : PLASMA_PAL;
    ['uC0', 'uC1', 'uC2', 'uC3'].forEach((k, j) => wallMat.uniforms[k].value.copy(pal[j]));
    wallMat.uniforms.uAmt.value = wa;
    renderer.autoClear = false; renderer.render(overlay, orthoCam); renderer.autoClear = true;
  }
  if (first && texturesIn) { first = false; window.__glReady && window.__glReady(); }
}
frame();


