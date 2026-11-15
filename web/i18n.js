// Spanish and Arabic for the interface. English stays the source of truth: every translated text node keeps its
// English original and switching back restores it. Text the app writes later (labels that change with the state)
// is caught by a MutationObserver when it matches an entry exactly. The detailed, number-filled explanations stay
// in English (the language note says so). Terms follow NASA's own Spanish material (ARSET: "incendios activos";
// FIRMS Spanish usage: "focos de calor").
const KEY = 'cedrus.lang';
const NOTE = { es: 'Las explicaciones detalladas con cifras están en inglés.', ar: 'الشروح التفصيلية المرفقة بالأرقام متوفرة بالإنجليزية.' };

// Whole elements whose markup has line breaks or emphasis: translated as HTML, keyed by data-i18n.
const HTML = {
  'hero-h1': { es: 'Una imagen más clara<br>de los <em class="burn">incendios.</em>', ar: 'صورة أوضح<br>لحرائق <em class="burn">الغابات.</em>' },
  'hero-desc': {
    es: 'Combinando los datos de los satélites MODIS y VIIRS, corregimos el falso aumento de detecciones de incendios y ofrecemos una historia del fuego coherente de hasta 25 años, para mejores decisiones, comunidades más seguras y un planeta más sano.',
    ar: 'بدمج بيانات القمرين الصناعيين MODIS وVIIRS، نصحّح الارتفاع الزائف في رصد الحرائق ونقدّم سجلًّا متّسقًا للحرائق يمتد حتى 25 عامًا، من أجل قرارات أفضل ومجتمعات أكثر أمانًا وكوكب أكثر صحة.',
  },
  'proof-intro': {
    es: 'Como un estudiante ante un examen: escribimos las reglas y las notas para aprobar, con fecha, <strong>antes</strong> de descargar las regiones de cada examen, y el modelo lo rindió una sola vez. El primero no se aprobó, y lo publicamos. Los dos siguientes aprobaron todas las pruebas.',
    ar: 'كطالب يتقدّم لامتحان: كتبنا القواعد وعلامات النجاح مؤرّخةً <strong>قبل</strong> تنزيل مناطق كل امتحان، ثم خاض النموذج الامتحان مرة واحدة. لم ينجح في الأول، ونشرنا ذلك. ونجح في كل اختبارات الامتحانين التاليين.',
  },
  'eyes-text': {
    es: 'El mismo incendio, visto por dos ojos satelitales. MODIS ve en píxeles de unos 1 km; VIIRS (desde 2012) en píxeles de 375 m, de modo que unos siete de sus píxeles caben en uno de MODIS, y además detecta fuegos más pequeños y menos calientes. Contado en bruto, el ojo más nítido hace parecer que el fuego saltó de un día para otro. El registro traduce cada conteo a términos equivalentes a MODIS, así 25 años quedan en una misma escala.',
    ar: 'الحريق نفسه كما تراه عينان من الفضاء. يرى MODIS ببكسلات عرضها نحو 1 كم، ويرى VIIRS (منذ 2012) ببكسلات عرضها 375 م، فيتّسع بكسل MODIS الواحد لنحو سبعة من بكسلاته، كما يلتقط حرائق أصغر وأقل حرارة. إذا عُدّت الرصدات كما هي، تبدو الحرائق وكأنها قفزت فجأة. يحوّل السجلّ كل عدّ إلى ما يعادله في MODIS، فتصبح السنوات الخمس والعشرون على مقياس واحد.',
  },
};

// Exact text nodes (trimmed). Keys are the English as it appears on screen.
const T = {
  'Home': ['Inicio', 'الرئيسية'],
  'Fire Calendar': ['Calendario de incendios', 'تقويم الحرائق'],
  'How We Know': ['Cómo lo sabemos', 'كيف نعرف'],
  'Data & Methodology': ['Datos y metodología', 'البيانات والمنهجية'],
  'About': ['Acerca de', 'من نحن'],
  'Roots in Nature. Data for a Safer Tomorrow.': ['Raíces en la naturaleza. Datos para un mañana más seguro.', 'جذور في الطبيعة. بيانات لغدٍ أكثر أمانًا.'],
  'Satellite data': ['Datos satelitales', 'بيانات الأقمار الصناعية'],
  '25 years': ['25 años', '25 عامًا'],
  'Up to 25 years': ['Hasta 25 años', 'حتى 25 عامًا'],
  'MODIS – VIIRS FIRE CALENDAR': ['CALENDARIO DE INCENDIOS MODIS – VIIRS', 'تقويم الحرائق MODIS – VIIRS'],
  'Explore the Fire Calendar': ['Explora el calendario de incendios', 'استكشف تقويم الحرائق'],
  'Choose an area. The calendar shows satellite fire activity for every month since December 2000, on one consistent scale.': ['Elige un área. El calendario muestra la actividad de fuego vista por satélite para cada mes desde diciembre de 2000, en una sola escala coherente.', 'اختر منطقة. يعرض التقويم نشاط الحرائق كما رصدته الأقمار الصناعية لكل شهر منذ ديسمبر 2000، على مقياس واحد متّسق.'],
  'Count fires as': ['Contar el fuego como', 'احتساب الحرائق بـ'],
  'Burning days': ['Días con fuego', 'أيام الاشتعال'],
  'Hotspots': ['Focos de calor', 'البؤر الحرارية'],
  'Burning days: how many days each ~1 km square had a fire detected, in MODIS-equivalent terms. Hotspots: the satellites’ fire detections, the numbers the challenge asks for.': ['Días con fuego: cuántos días cada cuadro de ~1 km tuvo un fuego detectado, en términos equivalentes a MODIS. Focos de calor: las detecciones de fuego de los satélites, las cifras que pide el desafío.', 'أيام الاشتعال: عدد الأيام التي رُصد فيها حريق في كل مربع مساحته نحو 1 كم، بما يعادل MODIS. البؤر الحرارية: رصدات الأقمار الصناعية للحرائق، وهي الأرقام التي يطلبها التحدي.'],
  'Try again': ['Reintentar', 'أعد المحاولة'],
  '1. Region': ['1. Región', '1. المنطقة'],
  'Example: Lebanon': ['Ejemplo: Líbano', 'مثال: لبنان'],
  '2. Or draw an area on the map': ['2. O dibuja un área en el mapa', '2. أو ارسم منطقة على الخريطة'],
  'Rectangle': ['Rectángulo', 'مستطيل'],
  'Polygon': ['Polígono', 'مضلّع'],
  'Whole region': ['Toda la región', 'المنطقة كاملة'],
  'Drawing tools load with the map…': ['Las herramientas de dibujo se cargan con el mapa…', 'تُحمَّل أدوات الرسم مع الخريطة…'],
  'Rectangle: click two corners. Polygon: click each corner, then click the first one again.': ['Rectángulo: haz clic en dos esquinas. Polígono: haz clic en cada esquina y luego otra vez en la primera.', 'المستطيل: انقر زاويتين. المضلّع: انقر كل زاوية ثم انقر الأولى مرة أخرى.'],
  '3. Or enter a point and radius': ['3. O introduce un punto y un radio', '3. أو أدخل نقطة ونصف قطر'],
  'Latitude': ['Latitud', 'خط العرض'],
  'Longitude': ['Longitud', 'خط الطول'],
  'Radius km': ['Radio km', 'نصف القطر كم'],
  'Use this circle': ['Usar este círculo', 'استخدم هذه الدائرة'],
  '4. Download for this area': ['4. Descargar para esta área', '4. تنزيل بيانات هذه المنطقة'],
  'From': ['Desde', 'من'],
  'To': ['Hasta', 'إلى'],
  'Burning days (CSV)': ['Días con fuego (CSV)', 'أيام الاشتعال (CSV)'],
  'Hotspots (CSV)': ['Focos de calor (CSV)', 'البؤر الحرارية (CSV)'],
  'Monthly record (CSV)': ['Registro mensual (CSV)', 'السجل الشهري (CSV)'],
  'Look & sound': ['Aspecto y sonido', 'المظهر والصوت'],
  'Effects': ['Efectos', 'المؤثرات'],
  'Sound': ['Sonido', 'الصوت'],
  'Language': ['Idioma', 'اللغة'],
  '0.25° CELLS · SELECTED MONTH': ['CELDAS DE 0,25° · MES ELEGIDO', 'خلايا 0.25° · الشهر المختار'],
  'All': ['Todo', 'الكل'],
  'Day': ['Día', 'نهارًا'],
  'Night': ['Noche', 'ليلًا'],
  'Raw lens': ['Lupa sin traducir', 'عدسة البيانات الخام'],
  'Story mode': ['Modo historia', 'وضع القصة'],
  'Next': ['Siguiente', 'التالي'],
  'Finish': ['Terminar', 'إنهاء'],
  'Exit': ['Salir', 'خروج'],
  'Explore': ['Explorar', 'استكشف'],
  'Explore it yourself': ['Explóralo tú mismo', 'استكشف بنفسك'],
  'Loading NASA FIRMS record…': ['Cargando el registro de NASA FIRMS…', 'جارٍ تحميل سجل NASA FIRMS…'],
  'Counts': ['Conteos', 'الأعداد'],
  'Anomaly': ['Anomalía', 'الانحراف عن المعتاد'],
  'Naive merge': ['Fusión simple', 'الدمج الساذج'],
  'Harmonized': ['Armonizado', 'المُوحَّد'],
  'vs median': ['vs. mediana', 'مقابل الوسيط'],
  'vs mean': ['vs. media', 'مقابل المتوسط'],
  'Show as tree rings': ['Ver como anillos de árbol', 'اعرض كحلقات شجرة'],
  'Show as grid': ['Ver como cuadrícula', 'اعرض كشبكة'],
  'Show as table': ['Ver como tabla', 'اعرض كجدول'],
  'Show as calendar': ['Ver como calendario', 'اعرض كتقويم'],
  'SELECTED MONTH': ['MES ELEGIDO', 'الشهر المختار'],
  'LATEST MONTH IN THE RECORD': ['ÚLTIMO MES DEL REGISTRO', 'آخر شهر في السجل'],
  'FIRE SEASON': ['TEMPORADA DE FUEGO', 'موسم الحرائق'],
  'When the fire season runs here': ['Cuándo ocurre aquí la temporada de fuego', 'متى يكون موسم الحرائق هنا'],
  'Normal start': ['Inicio normal', 'البداية المعتادة'],
  'Middle': ['Mitad', 'المنتصف'],
  'Normal end': ['Fin normal', 'النهاية المعتادة'],
  'FIRE FINGERPRINT': ['HUELLA DEL FUEGO', 'بصمة الحرائق'],
  'Save as image (PNG)': ['Guardar como imagen (PNG)', 'حفظ كصورة (PNG)'],
  'SATELLITE CHECK': ['CONTROL DEL SATÉLITE', 'فحص القمر الصناعي'],
  'Is MODIS still seeing what it used to?': ['¿Sigue MODIS viendo lo que veía antes?', 'هل ما زال MODIS يرى ما كان يراه؟'],
  'TWO EYES, ONE FIRE': ['DOS OJOS, UN FUEGO', 'عينان، حريق واحد'],
  'Why raw satellite counts jump in 2012, and how the record fixes it': ['Por qué los conteos satelitales en bruto saltan en 2012, y cómo lo corrige el registro', 'لماذا تقفز أعداد الأقمار الصناعية الخام في 2012، وكيف يصحّح السجل ذلك'],
  'Translate': ['Traducir', 'ترجمة'],
  'raw counts': ['conteos en bruto', 'الأعداد الخام'],
  'translated': ['traducido', 'بعد الترجمة'],
  'HOW DO WE KNOW IT WORKS?': ['¿CÓMO SABEMOS QUE FUNCIONA?', 'كيف نعرف أنه يعمل؟'],
  'Three sealed exams, on regions the model had never seen': ['Tres exámenes sellados, en regiones que el modelo nunca había visto', 'ثلاثة امتحانات مختومة، في مناطق لم يرها النموذج من قبل'],
  'NOT CONFIRMED': ['NO CONFIRMADO', 'غير مؤكَّد'],
  'CONFIRMED': ['CONFIRMADO', 'مؤكَّد'],
  'Exam 1': ['Examen 1', 'الامتحان 1'], 'Exam 2': ['Examen 2', 'الامتحان 2'], 'Exam 3': ['Examen 3', 'الامتحان 3'],
  'Rules written': ['Reglas escritas', 'كُتبت القواعد'],
  'sat once': ['rendido una vez', 'أُجري مرة واحدة'],
  'Accuracy, square by square': ['Precisión, cuadro por cuadro', 'الدقة، مربعًا مربعًا'],
  'Honest ranges': ['Rangos honestos', 'نطاقات صادقة'],
  'No inflation': ['Sin inflar', 'بلا تضخيم'],
  'Accuracy for the whole region': ['Precisión para toda la región', 'الدقة للمنطقة كاملة'],
  'Satellite handover': ['Relevo de satélites', 'تسليم بين الأقمار'],
  'The rules (plan)': ['Las reglas (plan)', 'القواعد (الخطة)'],
  'Full results': ['Resultados completos', 'النتائج الكاملة'],
  'And every region in this app was tested on its own data': ['Y cada región de esta app se probó con sus propios datos', 'وكل منطقة في هذا التطبيق اختُبرت على بياناتها الخاصة'],
  'fixed the two causes →': ['corregimos las dos causas →', 'أصلحنا السببين →'],
  'tournament of 9 models →': ['torneo de 9 modelos →', 'منافسة بين 9 نماذج →'],
  'Got it': ['Entendido', 'فهمت'],
  'Pick a region or draw an area. You get every month of its record (from December 2000, or from 2012 where older files are not loaded yet), on one consistent scale.': ['Elige una región o dibuja un área. Verás cada mes de su registro (desde diciembre de 2000, o desde 2012 donde aún no se cargaron los archivos anteriores), en una misma escala.', 'اختر منطقة أو ارسم مساحة. ستحصل على كل شهر من سجلّها (منذ ديسمبر 2000، أو منذ 2012 حيث لم تُحمَّل الملفات الأقدم بعد)، على مقياس واحد متّسق.'],
  'Start here: pick a region, or draw an area on the map': ['Empieza aquí: elige una región o dibuja un área en el mapa', 'ابدأ من هنا: اختر منطقة أو ارسم مساحة على الخريطة'],
  'Or enter a point and radius': ['O introduce un punto y un radio', 'أو أدخل نقطة ونصف قطر'],
  'Download data for this area (CSV)': ['Descargar los datos de esta área (CSV)', 'تنزيل بيانات هذه المنطقة (CSV)'],
  'Effects and sound': ['Efectos y sonido', 'المؤثرات والصوت'],
  'View options': ['Opciones de vista', 'خيارات العرض'],
  'Details: source, normal, rank and trust check': ['Detalles: fuente, normal, posición y control de confianza', 'التفاصيل: المصدر، المعتاد، الترتيب، وفحص الثقة'],
  'Your turn': ['Tu turno', 'دورك'],
  'Right now': ['Ahora mismo', 'الآن'],
  'Show on map': ['Ver en el mapa', 'اعرض على الخريطة'],
  'Hide on map': ['Ocultar del mapa', 'إخفاء من الخريطة'],
  // the story deck, Method and About (Yasmina's design)
  'Lebanon is our home. The same tool covers {n} regions on {c} continents, including La Rioja, the challenge authors’ own example.': ['El Líbano es nuestro hogar. La misma herramienta cubre {n} regiones en {c} continentes, incluida La Rioja, el ejemplo de los propios autores del desafío.', 'لبنان موطننا. والأداة نفسها تغطي {n} منطقة في {c} قارات، من بينها لا ريوخا، المثال الذي اختاره واضعو التحدي أنفسهم.'],
  'Your area': ['Tu área', 'منطقتك'],
  'How the correction works': ['Cómo funciona la corrección', 'كيف يعمل التصحيح'],
  'or scroll to move through the story': ['o desplázate para recorrer la historia', 'أو مرّر لتتابع القصة'],
  'Choose an area, then click any month to see it on the map and read it below.': ['Elige un área y haz clic en un mes para verlo en el mapa y leerlo abajo.', 'اختر منطقة، ثم انقر أي شهر لتراه على الخريطة وتقرأه أدناه.'],
  'In orbit': ['En órbita', 'في المدار'],
  'Four satellites.': ['Cuatro satélites.', 'أربعة أقمار صناعية.'],
  'One fire record.': ['Un solo registro de incendios.', 'سجلّ واحد للحرائق.'],
  'Press → to dive into Lebanon': ['Pulsa → para descender sobre el Líbano', 'اضغط → للهبوط إلى لبنان'],
  'The calendar': ['El calendario', 'التقويم'],
  'Every month': ['Cada mes', 'كل شهر'],
  'since December': ['desde diciembre', 'منذ ديسمبر'],
  'The problem': ['El problema', 'المشكلة'],
  'New satellites': ['Los satélites nuevos', 'الأقمار الجديدة'],
  'see more fires.': ['ven más incendios.', 'ترى حرائق أكثر.'],
  "That isn't": ['Eso no es', 'وهذا ليس'],
  'more fire.': ['más fuego.', 'حريقًا أكثر.'],
  'The fix': ['La corrección', 'الحل'],
  'Harmonized to': ['Armonizado a', 'موحَّد على'],
  'one MODIS-': ['una escala', 'مقياس واحد'],
  'equivalent scale.': ['equivalente a MODIS.', 'مكافئ لـ MODIS.'],
  'Any area': ['Cualquier área', 'أي منطقة'],
  'Draw an area.': ['Dibuja un área.', 'ارسم منطقة.'],
  'Read it to the': ['Léela hasta la', 'واقرأها حتى'],
  '0.25° cell.': ['celda de 0,25°.', 'خلية 0.25°.'],
  'The season': ['La temporada', 'الموسم'],
  'When the fire': ['Cuándo corre la', 'متى يمتد'],
  'season runs.': ['temporada de incendios.', 'موسم الحرائق.'],
  'Burning days by year': ['Días de fuego por año', 'أيام الاحتراق حسب السنة'],
  'Launches': ['Lanzamientos', 'الإطلاقات'],
  'The fire-sensing fleet': ['La flota que detecta incendios', 'أسطول رصد الحرائق'],
  'Worst months on record': ['Los peores meses del registro', 'أسوأ الأشهر في السجل'],
  'The record we serve': ['El registro que ofrecemos', 'السجل الذي نقدّمه'],
  'regions': ['regiones', 'مناطق'],
  'months, Lebanon': ['meses, Líbano', 'شهرًا، لبنان'],
  '0.25° cells, Lebanon': ['celdas de 0,25°, Líbano', 'خلية 0.25°، لبنان'],
  'Altitude': ['Altitud', 'الارتفاع'],
  'Orbital velocity': ['Velocidad orbital', 'السرعة المدارية'],
  'Orbital period': ['Período orbital', 'الدورة المدارية'],
  'Type of orbit': ['Tipo de órbita', 'نوع المدار'],
  'Launched': ['Lanzado', 'أُطلق'],
  'Equator crossing': ['Cruce del ecuador', 'عبور خط الاستواء'],
  'Swath': ['Franja', 'عرض المسح'],
  'Calendar years': ['Años de calendario', 'سنوات تقويمية'],
  'Months': ['Meses', 'أشهر'],
  '0.25° cells': ['Celdas de 0,25°', 'خلايا 0.25°'],
  'Three steps from': ['Tres pasos desde la', 'ثلاث خطوات من'],
  'detection to calendar.': ['detección al calendario.', 'الرصد إلى التقويم.'],
  'Read every fire pixel': ['Leer cada píxel de fuego', 'قراءة كل بكسل حريق'],
  "Put VIIRS on MODIS's scale": ['Llevar VIIRS a la escala de MODIS', 'وضع VIIRS على مقياس MODIS'],
  'Count burning days per cell': ['Contar los días de fuego por celda', 'عدّ أيام الاحتراق لكل خلية'],
  'What this record is not': ['Lo que este registro no es', 'ما ليس عليه هذا السجل'],
  'Read the full methodology, limits and files': ['Leer la metodología completa, los límites y los archivos', 'اقرأ المنهجية كاملة والقيود والملفات'],
  'See the sealed exams': ['Ver los exámenes sellados', 'اطّلع على الامتحانات المختومة'],
  'Roots in nature.': ['Raíces en la naturaleza.', 'جذور في الطبيعة.'],
  'Data for a safer tomorrow.': ['Datos para un mañana más seguro.', 'بيانات لغدٍ أكثر أمانًا.'],
  'About the team': ['Sobre el equipo', 'عن الفريق'],
  'Credits, files and methodology': ['Créditos, archivos y metodología', 'الشكر والملفات والمنهجية'],
  'Fire detections': ['Detecciones de incendios', 'رصد الحرائق'],
  'Instruments': ['Instrumentos', 'الأجهزة'],
  'Satellites': ['Satélites', 'الأقمار الصناعية'],
  'Outlines': ['Contornos', 'الحدود'],
  'Record': ['Registro', 'السجل'],
};

const LANGS = ['en', 'es', 'ar'];
let lang = 'en';
const touched = new Set(); // elements given a lang attribute
const RLI = '⁧'; const PDI = '⁩'; // Arabic runs are isolated, so the English and numbers around them keep their order

function tr(en) { const row = T[en]; if (!row || lang === 'en') return null; return row[lang === 'es' ? 0 : 1]; }
// For shell.js: sentences it writes itself (the landing's typed line) are looked up here.
window.cedrusI18n = { tr: (en) => tr(en), lang: () => lang };

function wanted(node) { // what this node should read in the current language
  const key = node.__en.trim(); const out = tr(key);
  return out == null ? node.__en : node.__en.replace(key, lang === 'ar' ? RLI + out + PDI : out);
}
function translateNode(node) {
  if (node.__en == null) { const key = node.nodeValue.trim(); if (!key || !T[key]) return; node.__en = node.nodeValue; }
  const want = wanted(node);
  if (node.nodeValue !== want) node.nodeValue = want;
  // An element holding only this text says which language it is in (for screen readers).
  const el = node.parentElement;
  if (el && el.childNodes.length === 1) {
    if (lang !== 'en' && tr(node.__en.trim()) != null) { el.lang = lang; touched.add(el); } else if (touched.has(el)) { el.removeAttribute('lang'); touched.delete(el); }
  }
}
function walk(root) {
  const it = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, { acceptNode: (n) => (n.parentElement?.closest('script,style,svg,#cal-grid,.calendar-table') ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT) });
  for (let n = it.nextNode(); n; n = it.nextNode()) translateNode(n);
}
function applyHtml() {
  document.querySelectorAll('[data-i18n]').forEach((el) => {
    if (el.__en == null) el.__en = el.innerHTML;
    const row = HTML[el.dataset.i18n];
    el.innerHTML = lang === 'en' || !row ? el.__en : row[lang];
    if (lang === 'ar' && row) el.dir = 'rtl'; else el.removeAttribute('dir');
    if (lang !== 'en' && row) el.lang = lang; else el.removeAttribute('lang');
  });
}
function apply() {
  // The page stays lang="en": most numbers-and-sentences text is English; translated elements carry their own lang.
  applyHtml(); walk(document.body);
  const note = document.getElementById('lang-note'); if (note) { note.textContent = NOTE[lang] || ''; note.hidden = lang === 'en'; note.dir = lang === 'ar' ? 'rtl' : ''; }
  document.querySelectorAll('#lang-switch button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.lang === lang)));
}
function setLang(l) {
  lang = LANGS.includes(l) ? l : 'en';
  try { localStorage.setItem(KEY, lang); } catch { /* this page only */ }
  apply();
}

// Text the app writes later: translate it as it arrives (only exact matches; numbers and sentences stay English).
let queue = [];
new MutationObserver((muts) => {
  if (lang === 'en') return;
  const first = !queue.length; queue.push(...muts);
  if (!first) return; // a flush is already scheduled; it will see these records too
  requestAnimationFrame(() => {
    const batch = queue; queue = [];
    for (const m of batch) {
      if (m.type === 'characterData') { const n = m.target; if (n.__en != null && n.nodeValue !== wanted(n)) n.__en = null; translateNode(n); } // the app rewrote it
      m.addedNodes.forEach((n) => (n.nodeType === 3 ? translateNode(n) : n.nodeType === 1 && walk(n)));
    }
  });
}).observe(document.body, { subtree: true, childList: true, characterData: true });

document.querySelectorAll('#lang-switch button').forEach((b) => b.addEventListener('click', () => setLang(b.dataset.lang)));
let saved = 'en';
try { saved = localStorage.getItem(KEY) || new URLSearchParams(location.search).get('lang') || 'en'; } catch { /* default */ }
if (new URLSearchParams(location.search).get('lang')) saved = new URLSearchParams(location.search).get('lang');
setLang(saved);
