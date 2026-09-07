/* ====================================================
   ديوان آل السويلم — المنطق
   ==================================================== */

const WASM_ICONS = {
  "wasm-1": `<svg viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"> <line x1="20" y1="6" x2="20" y2="34" /> <line x1="11" y1="11" x2="29" y2="11" /> </svg>`,
  "wasm-2": `<svg viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"> <circle cx="20" cy="20" r="9" /> <line x1="5" y1="20" x2="35" y2="20" /> </svg>`,
  "wasm-3": `<svg viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"> <line x1="9" y1="9" x2="31" y2="31" /> <line x1="9" y1="31" x2="31" y2="9" /> <circle cx="20" cy="20" r="3.2" fill="currentColor" stroke="none" /> </svg>`,
  "wasm-4": `<svg viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"> <polygon points="20,7 33,30 7,30" /> </svg>`,
  "wasm-5": `<svg viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"> <polyline points="6,28 14,12 20,28 26,12 34,28" /> </svg>`
};

/* تنقية أي نص قبل حقنه بالـ HTML — يمنع تنفيذ أي وسم/سكربت مخفي داخل عنوان أو بيت شعري */
function esc(str) {
  if (str === null || str === undefined) return "";
  return String(str)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}

function wasmIcon(wasmId, extraStyle) {
  const svg = WASM_ICONS[wasmId] || "";
  return svg.replace("<svg ", `<svg style="color:var(--gold);${extraStyle || ""}" `);
}

function poetMark(poet, sizeStyle) {
  const style = sizeStyle || "width:34px;height:34px;";
  if (poet.photo) {
    return `<img src="${esc(poet.photo)}" class="poet-photo" style="${style}" alt="${esc(poet.name)}" loading="lazy" decoding="async" />`;
  }
  return wasmIcon(poet.wasm, style);
}

const ROLE_LABELS = {
  "بدع":    { text: "بدع",          cls: "role-badge role-بدع"    },
  "رد":     { text: "ردّ",          cls: "role-badge role-رد"     },
  "مجاراة": { text: "مجاراة",       cls: "role-badge role-مجاراة" }
};

function roleBadge(role) {
  if (!role || !ROLE_LABELS[role]) return "";
  const r = ROLE_LABELS[role];
  return `<span class="${r.cls}">${r.text}</span>`;
}

const state = { data: null, activePoet: "all", query: "", responsesMap: {} };

const el = {
  subtitle:    document.getElementById("site-subtitle"),
  wasmLegend:  document.getElementById("wasm-legend"),
  filterPills: document.getElementById("filter-pills"),
  searchInput: document.getElementById("search-input"),
  poemsGrid:   document.getElementById("poems-grid"),
  poemDetail:  document.getElementById("poem-detail"),
  footerYear:  document.getElementById("footer-year"),
  footerNote:  document.getElementById("footer-note")
};

init();

async function init() {
  el.footerYear.textContent = new Date().getFullYear();
  try {
    const res = await fetch("data/diwan.json");
    if (!res.ok) throw new Error("HTTP " + res.status);
    state.data = await res.json();
  } catch (err) {
    el.poemsGrid.innerHTML = `<div class="empty-state">تعذّر تحميل بيانات الديوان.<br><small style="opacity:0.7">${esc(err.message)}</small></div>`;
    return;
  }
  el.subtitle.textContent = state.data.site.subtitle || "";
  if (el.footerNote) el.footerNote.textContent = state.data.site.footerNote || "";
  state.responsesMap = buildResponsesMap();
  renderWasmLegend();
  renderFilterPills();
  bindGlobalEvents();
  handleRoute();
  window.addEventListener("hashchange", handleRoute);
  initBackToTop();
  initCompactFilterBar();
  initVerseExport();
}

/* شريط الفلاتر يصغّر تلقائياً وأنت تنزل بالصفحة — كل الأزرار تضل ظاهرة وقابلة للضغط، بدون أي إخفاء أو ضغطة إضافية */
function initCompactFilterBar() {
  const bar = document.querySelector(".filter-bar");
  if (!bar) return;
  window.addEventListener("scroll", () => {
    bar.classList.toggle("compact", window.scrollY > 60);
  });
}

/* زر عائم يرجّع لأعلى الصفحة — التنسيق كامل مضمّن هنا (مو بملف CSS منفصل)
   عشان يشتغل دايماً بغض النظر عن تحديث style.css */
function initBackToTop() {
  const btn = document.createElement("button");
  btn.id = "back-to-top";
  btn.setAttribute("aria-label", "الرجوع لأعلى الصفحة");
  btn.innerHTML = "↑";
  btn.style.cssText = [
    "position:fixed", "bottom:22px", "left:22px", "z-index:9999",
    "width:46px", "height:46px", "border-radius:50%",
    "background:var(--ember,#d9803f)", "color:#1a120b", "border:none",
    "font-size:1.35rem", "line-height:1", "cursor:pointer",
    "display:flex", "align-items:center", "justify-content:center",
    "opacity:0", "pointer-events:none", "transform:translateY(12px)",
    "transition:opacity .25s ease,transform .25s ease",
    "box-shadow:0 4px 16px rgba(0,0,0,.4)"
  ].join(";");
  btn.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
  document.body.appendChild(btn);
  window.addEventListener("scroll", () => {
    const show = window.scrollY > 420;
    btn.style.opacity = show ? "1" : "0";
    btn.style.pointerEvents = show ? "auto" : "none";
    btn.style.transform = show ? "translateY(0)" : "translateY(12px)";
  });
}

/* ====================================================
   تصدير بيت أو بيتين كصورة قابلة للمشاركة
   ==================================================== */
const verseSelection = { els: [] };

function toggleVerseSelect(el) {
  const idx = verseSelection.els.indexOf(el);
  if (idx !== -1) {
    verseSelection.els.splice(idx, 1);
    el.classList.remove("selected");
  } else {
    // لو المحدد حالياً من قصيدة ثانية، ابدأ تحديد جديد
    if (verseSelection.els.length && verseSelection.els[0].dataset.poemTitle !== el.dataset.poemTitle) {
      verseSelection.els.forEach(e => e.classList.remove("selected"));
      verseSelection.els = [];
    }
    if (verseSelection.els.length >= 2) return; // الحد الأقصى بيتين بالصورة الواحدة
    verseSelection.els.push(el);
    el.classList.add("selected");
  }
  updateVerseExportButton();
}

function resetVerseSelection() {
  verseSelection.els.forEach(e => e.classList.remove("selected"));
  verseSelection.els = [];
  updateVerseExportButton();
}

function updateVerseExportButton() {
  const btn = document.getElementById("verse-export-btn");
  if (!btn) return;
  const show = verseSelection.els.length > 0;
  btn.style.opacity = show ? "1" : "0";
  btn.style.pointerEvents = show ? "auto" : "none";
  btn.style.transform = show ? "translateY(0)" : "translateY(12px)";
}

/* زر عائم يظهر بس وأنت محدد بيت أو بيتين — نفس أسلوب back-to-top (تنسيق مضمّن). */
function initVerseExport() {
  const btn = document.createElement("button");
  btn.id = "verse-export-btn";
  btn.setAttribute("aria-label", "تحميل الأبيات المحددة كصورة");
  btn.innerHTML = "🖼️ حمّل كصورة";
  btn.style.cssText = [
    "position:fixed", "bottom:22px", "right:22px", "z-index:9999",
    "padding:12px 20px", "border-radius:999px",
    "background:var(--gold,#c9a227)", "color:#1a120b", "border:none",
    "font-size:.92rem", "font-weight:600", "font-family:inherit", "cursor:pointer",
    "opacity:0", "pointer-events:none", "transform:translateY(12px)",
    "transition:opacity .25s ease,transform .25s ease",
    "box-shadow:0 4px 16px rgba(0,0,0,.4)"
  ].join(";");
  btn.addEventListener("click", exportSelectedVersesAsImage);
  document.body.appendChild(btn);
}

function wrapCanvasText(ctx, text, maxWidth) {
  const words = String(text || "").split(" ").filter(Boolean);
  if (words.length === 0) return [""];
  const lines = [];
  let current = words[0];
  for (let i = 1; i < words.length; i++) {
    const test = current + " " + words[i];
    if (ctx.measureText(test).width <= maxWidth) current = test;
    else { lines.push(current); current = words[i]; }
  }
  lines.push(current);
  return lines;
}

/* خلفية بسيطة بتدرّج هادئ بنفس هوية الموقع (زي توهج ember-glow) — بدون أي صورة أو
   نص إضافي عليها، عشان البيت المُصدَّر يبقى واضح تماماً بدون أي تداخل بصري. */
function drawGradientBackground(ctx, size) {
  ctx.fillStyle = "#15110d";
  ctx.fillRect(0, 0, size, size);
  const glow = ctx.createRadialGradient(size * 0.5, size * 0.08, 10, size * 0.5, size * 0.4, size * 0.75);
  glow.addColorStop(0, "rgba(217,128,63,.16)");
  glow.addColorStop(1, "rgba(217,128,63,0)");
  ctx.fillStyle = glow;
  ctx.fillRect(0, 0, size, size);
  const glow2 = ctx.createRadialGradient(size * 0.85, size * 0.28, 10, size * 0.85, size * 0.28, size * 0.5);
  glow2.addColorStop(0, "rgba(201,162,39,.08)");
  glow2.addColorStop(1, "rgba(201,162,39,0)");
  ctx.fillStyle = glow2;
  ctx.fillRect(0, 0, size, size);
}

async function exportSelectedVersesAsImage() {
  if (verseSelection.els.length === 0) return;
  const verses = verseSelection.els.map(el => ({ sadr: el.dataset.sadr, ajz: el.dataset.ajz }));
  const poetName = verseSelection.els[0].dataset.poetName || "";
  const poemTitle = verseSelection.els[0].dataset.poemTitle || "";

  const btn = document.getElementById("verse-export-btn");
  const originalLabel = btn ? btn.innerHTML : "";
  if (btn) { btn.innerHTML = "⏳ جاري التجهيز…"; btn.style.pointerEvents = "none"; }

  try {
    const size = 1080;
    const canvas = document.createElement("canvas");
    canvas.width = size; canvas.height = size;
    const ctx = canvas.getContext("2d");

    drawGradientBackground(ctx, size);
    try {
      await document.fonts.load('700 56px "Thmanyah Serif Display"');
      await document.fonts.load('500 48px "Thmanyah Serif Text"');
      await document.fonts.load('500 26px "Thmanyah Sans"');
      await document.fonts.load('700 30px "Thmanyah Sans"');
    } catch { /* الخط الاحتياطي بالمتصفح يكفي لو تعذّر */ }

    ctx.direction = "rtl";
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";

    // شعار الديوان أعلى الصورة — بخط ثمانية Serif Display بنفس معالجة عنوان الموقع
    ctx.fillStyle = "#ede3d3";
    ctx.font = '700 58px "Thmanyah Serif Display", serif';
    ctx.fillText("آل السويلـم", size / 2, 110);

    ctx.strokeStyle = "rgba(201,162,39,.5)";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(size / 2 - 40, 168);
    ctx.lineTo(size / 2 + 40, 168);
    ctx.stroke();

    ctx.fillStyle = "#f2ead9";
    const verseFontSize = verses.length > 1 ? 46 : 54;
    ctx.font = `500 ${verseFontSize}px "Thmanyah Serif Text", serif`;
    const maxTextWidth = size - 160;
    const lineHeight = verseFontSize * 1.55;

    const allLines = [];
    verses.forEach((v, i) => {
      allLines.push(...wrapCanvasText(ctx, v.sadr, maxTextWidth));
      allLines.push(...wrapCanvasText(ctx, v.ajz, maxTextWidth));
      if (i < verses.length - 1) allLines.push("");
    });

    const middleY = 168 + (size - 168 - 150) / 2 + 40;
    const totalHeight = allLines.length * lineHeight;
    let y = middleY - totalHeight / 2 + lineHeight / 2;
    allLines.forEach(line => {
      if (line) ctx.fillText(line, size / 2, y);
      y += lineHeight;
    });

    ctx.fillStyle = "rgba(237,227,211,.8)";
    ctx.font = '500 26px "Thmanyah Sans", sans-serif';
    ctx.fillText(poetName, size / 2, size - 150);

    ctx.strokeStyle = "rgba(201,162,39,.3)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(size / 2 - 200, size - 108);
    ctx.lineTo(size / 2 + 200, size - 108);
    ctx.stroke();

    ctx.fillStyle = "#c9a227";
    ctx.font = '700 30px "Thmanyah Sans", sans-serif';
    ctx.fillText("diwan-alswilem.com", size / 2, size - 66);

    const blob = await new Promise(resolve => canvas.toBlob(resolve, "image/png"));
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    const safeName = (poemTitle || "بيت-من-قصيدة").replace(/[\\/:*?"<>|]/g, "").trim().slice(0, 60) || "بيت-من-قصيدة";
    a.href = url;
    a.download = `${safeName}.png`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 4000);
  } catch (err) {
    alert("تعذّر إنشاء الصورة: " + err.message);
  } finally {
    if (btn) { btn.innerHTML = originalLabel; btn.style.pointerEvents = ""; updateVerseExportButton(); }
  }
}

function getAllPoemsFlat() {
  const out = [];
  state.data.poets.forEach(poet => {
    poet.poems.forEach(poem => out.push({ poet, poem, isExternal: false }));
  });
  (state.data.externalPoets || []).forEach(poet => {
    poet.poems.forEach(poem => out.push({ poet, poem, isExternal: true }));
  });
  return out;
}

function findPoem(poemId) {
  return getAllPoemsFlat().find(({ poem }) => poem.id === poemId) || null;
}

function buildResponsesMap() {
  const map = {};
  getAllPoemsFlat().forEach(({ poem }) => {
    const targetId = poem.mujarat?.respondingToId;
    if (targetId) {
      if (!map[targetId]) map[targetId] = [];
      map[targetId].push(poem.id);
    }
  });
  return map;
}

function renderWasmLegend() {
  el.wasmLegend.innerHTML = state.data.poets.map(poet =>
    `<button class="wasm-legend-item" data-poet="${esc(poet.id)}" aria-label="عرض قصائد ${esc(poet.name)}">
      ${poetMark(poet, "width:40px;height:40px;")}
      <span>${esc(poet.name)}</span>
    </button>`
  ).join("");
}

function renderFilterPills() {
  const poetPills = state.data.poets.map(poet =>
    `<button class="pill" data-poet="${esc(poet.id)}">
      ${poetMark(poet, "width:16px;height:16px;")}
      ${esc(poet.name)}
    </button>`
  ).join("");
  const respondentsPill = (state.data.externalPoets || []).length
    ? `<a class="pill" href="/respondents.html">شعراء تجاوبوا مع الديوان</a>`
    : "";
  el.filterPills.innerHTML = `<button class="pill active" data-poet="all">الكل</button>${poetPills}${respondentsPill}`;
}

function bindGlobalEvents() {
  document.addEventListener("click", (e) => {
    const verseEl = e.target.closest(".verse-selectable");
    if (verseEl) {
      toggleVerseSelect(verseEl);
      return;
    }
    const mujaratBtn = e.target.closest(".mujarat-goto");
    if (mujaratBtn) {
      location.hash = `poem=${mujaratBtn.dataset.poemId}`;
      return;
    }
    const pill = e.target.closest("[data-poet]");
    if (pill) {
      location.hash = pill.dataset.poet === "all" ? "" : `poet=${pill.dataset.poet}`;
    }
    const card = e.target.closest("[data-poem]");
    if (card) location.hash = `poem=${card.dataset.poem}`;
    const back = e.target.closest(".back-btn");
    if (back) location.hash = back.dataset.returnTo ? `poet=${back.dataset.returnTo}` : "";
  });
  document.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const card = e.target.closest('[role="button"][data-poem]');
    if (!card) return;
    e.preventDefault();
    location.hash = `poem=${card.dataset.poem}`;
  });
  el.searchInput.addEventListener("input", (e) => {
    state.query = e.target.value.trim();
    if (location.hash.startsWith("#poem=")) location.hash = "";
    renderGridView();
  });
}

function handleRoute() {
  resetVerseSelection();
  const hash = decodeURIComponent(location.hash.replace(/^#/, ""));
  const [key, value] = hash.split("=");
  if (key === "poem" && value) { showPoem(value); return; }
  state.activePoet = key === "poet" && value ? value : "all";
  renderGridView();
}

/* يوحّد النص العربي قبل المقارنة — يشيل التشكيل ويوحّد أشكال الألف/التاء المربوطة/الألف المقصورة
   عشان البحث يتطابق حتى لو نص القصيدة فيه تشكيل والمستخدم كتب بدونه */
function normalizeArabic(str) {
  return String(str || "")
    .replace(/[\u064B-\u065F\u0670]/g, "")
    .replace(/[إأآا]/g, "ا")
    .replace(/ة/g, "ه")
    .replace(/ى/g, "ي")
    .toLowerCase();
}

function renderGridView() {
  el.poemDetail.classList.add("hidden");
  el.poemsGrid.classList.remove("hidden");
  document.querySelectorAll(".pill").forEach(p => {
    p.classList.toggle("active", p.dataset.poet === state.activePoet);
  });

  let items = getAllPoemsFlat().filter(({ isExternal }) => !isExternal);
  if (state.activePoet !== "all") items = items.filter(({ poet }) => poet.id === state.activePoet);
  if (state.query) {
    const q = normalizeArabic(state.query);
    items = items.filter(({ poem }) => {
      if (normalizeArabic(poem.title).includes(q)) return true;
      return (poem.verses || []).some(v =>
        normalizeArabic(v.sadr).includes(q) ||
        normalizeArabic(v.ajz).includes(q)
      );
    });
  }

  const poemOfDay = renderPoemOfDay();
  const recentSection = renderRecentSection();
  const bioBanner = renderBioBanner();
  if (items.length === 0) {
    el.poemsGrid.innerHTML = poemOfDay + recentSection + bioBanner + `<div class="empty-state">لا توجد قصائد مطابقة لبحثك حتى الآن.</div>`;
    return;
  }

  const cards = items.map(({ poet, poem }) => buildPoemCard(poet, poem)).join("");
  el.poemsGrid.innerHTML = poemOfDay + recentSection + bioBanner + cards;
}

function buildPoemCard(poet, poem) {
  const hasResponses = !!state.responsesMap[poem.id];
  return `<article class="poem-card" data-poem="${esc(poem.id)}" tabindex="0" role="button">
      <div class="poem-card-tag">
        ${poetMark(poet, "width:14px;height:14px;")} ${esc(poet.name)}
        ${roleBadge(poem.role)}
        ${hasResponses ? `<span class="role-badge role-responded">تمت مجاراتها</span>` : ""}
      </div>
      <h3>${esc(poem.title)}</h3>
      <p>${poem.verses?.[0] ? esc(poem.verses[0].sadr) : ""}</p>
    </article>`;
}

/* قصيدة اليوم — اختيار عشوائي (لكن ثابت لنفس اليوم لكل الزوار) من كل قصائد الديوان
   بما فيها قصائد الشعراء الخارجيين. اليوم يتغيّر عند الساعة ١٢:٠٠ ظهراً بتوقيت السعودية
   (UTC+3) بدل منتصف الليل — عشان "يوم القصيدة" يبدأ مع بداية النهار الفعلي. */
function dailyHash(str) {
  let h = 0;
  for (let i = 0; i < str.length; i++) h = (h * 31 + str.charCodeAt(i)) >>> 0;
  return h;
}
function riyadhDayKey() {
  // UTC+3 (توقيت السعودية) ناقص ١٢ ساعة (نقطة التحول) = إزاحة صافية -٩ ساعات عن UTC
  const shifted = new Date(Date.now() - 9 * 3600 * 1000);
  return shifted.toISOString().slice(0, 10);
}
function renderPoemOfDay() {
  if (state.activePoet !== "all" || state.query) return "";
  const all = getAllPoemsFlat();
  if (all.length === 0) return "";
  const idx = dailyHash(riyadhDayKey()) % all.length;
  const { poet, poem } = all[idx];
  const versesHtml = (poem.verses || []).slice(0, 2).map(v =>
    `<div class="verse"><span class="sadr">${esc(v.sadr)}</span><span class="divider"></span><span class="ajz">${esc(v.ajz)}</span></div>`
  ).join("");
  return `<div class="poem-of-day" data-poem="${esc(poem.id)}" tabindex="0" role="button" aria-label="اقرأ قصيدة اليوم كاملة">
    <div class="poem-of-day-badge">✨ قصيدة اليوم</div>
    <div class="poem-of-day-tag">${poetMark(poet, "width:18px;height:18px;")} ${esc(poet.name)}</div>
    <h3>${esc(poem.title)}</h3>
    ${versesHtml ? `<div class="verses poem-of-day-verses">${versesHtml}</div>` : ""}
  </div>`;
}

/* قصائد أُضيفت حديثاً — تظهر بس بعرض "الكل" بدون بحث، وبس لو فيه قصائد عندها تاريخ إضافة حقيقي.
   قصائد قديمة بدون هذا التاريخ ما تدخل بالحساب، فالقسم يختفي تلقائياً لو ما فيه شي حديث كفاية. */
function renderRecentSection() {
  if (state.activePoet !== "all" || state.query) return "";
  const dated = getAllPoemsFlat()
    .filter(({ isExternal, poem }) => !isExternal && poem.addedAt)
    .sort((a, b) => (b.poem.addedAt || "").localeCompare(a.poem.addedAt || ""))
    .slice(0, 10);
  if (dated.length === 0) return "";
  const cards = dated.map(({ poet, poem }) => buildPoemCard(poet, poem)).join("");
  return `<h2 class="recent-heading">أضيف حديثاً</h2>${cards}<div class="recent-divider"></div>`;
}

function renderBioBanner() {
  if (state.activePoet === "all") return "";
  const poet = state.data.poets.find(p => p.id === state.activePoet);
  if (!poet) return "";
  return `<div class="poet-bio-banner">
    ${poetMark(poet, "width:52px;height:52px;")}
    <div><h2>${esc(poet.name)}</h2><p>${esc(poet.bio)}</p></div>
  </div>`;
}

function showPoem(poemId) {
  const found = findPoem(poemId);
  if (!found) { handleRoute(); return; }
  const { poet, poem, isExternal } = found;

  el.poemsGrid.classList.add("hidden");
  el.poemDetail.classList.remove("hidden");
  document.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));

  const backBtn = isExternal
    ? `<button class="back-btn" onclick="history.back()">← رجوع</button>`
    : `<button class="back-btn" data-return-to="${esc(poet.id)}">← الرجوع إلى قصائد ${esc(poet.name)}</button>`;

  const responseIds = state.responsesMap[poemId] || [];
  let responsesSection = "";
  if (responseIds.length > 0) {
    const links = responseIds.map(rid => {
      const r = findPoem(rid);
      if (!r) return "";
      return `<button class="mujarat-goto" data-poem-id="${esc(r.poem.id)}">
        ${r.isExternal ? "" : poetMark(r.poet, "width:13px;height:13px;")}
        ${esc(r.poet.name)} — ${esc(r.poem.title)} ${roleBadge(r.poem.role)}
      </button>`;
    }).join("");
    responsesSection = `
      <div class="mujarat-section" style="margin-top:24px">
        <span class="mujarat-label">ردود ومجاراات على هذه القصيدة</span>
        <div class="mujarat-responses">${links}</div>
      </div>`;
  }

  const isChain = (poem.role === "رد" || poem.role === "مجاراة") && poem.mujarat?.respondingToId;
  const originalFound = isChain ? findPoem(poem.mujarat.respondingToId) : null;

  if (isChain && originalFound) {
    el.poemDetail.innerHTML = buildChainView(backBtn, originalFound, { poet, poem }, responsesSection);
  } else {
    el.poemDetail.innerHTML = buildNormalView(backBtn, poet, poem, isExternal, responsesSection);
  }
}

/* exportCtx = {poet, title} يفعّل إمكانية تحديد البيت لتصديره كصورة — يُمرَّر فقط لأبيات
   القصيدة المعروضة حالياً (مو لوحة القصيدة الأصلية بعرض الرد/المجاراة، لأنها أصلاً قابلة
   للضغط للانتقال لصفحتها، وتحديد بيت فيها بيتعارض مع فتحها). */
function buildVerses(verses, exportCtx) {
  return (verses || []).map(v => {
    if (!exportCtx) {
      return `<div class="verse"><span class="sadr">${esc(v.sadr)}</span><span class="divider"></span><span class="ajz">${esc(v.ajz)}</span></div>`;
    }
    return `<div class="verse verse-selectable" data-sadr="${esc(v.sadr)}" data-ajz="${esc(v.ajz)}" data-poet-name="${esc(exportCtx.poet)}" data-poem-title="${esc(exportCtx.title)}">
      <span class="verse-check" aria-hidden="true"></span>
      <span class="sadr">${esc(v.sadr)}</span>
      <span class="divider"></span>
      <span class="ajz">${esc(v.ajz)}</span>
    </div>`;
  }).join("");
}

function buildChainView(backBtn, origFound, resp, responsesSection) {
  const { poet: origPoet, poem: origPoem, isExternal: origIsExternal } = origFound;
  const { poet: respPoet, poem: respPoem } = resp;
  const origVerses = buildVerses(origPoem.verses);
  const respVerses = buildVerses(respPoem.verses, { poet: respPoet.name, title: respPoem.title });

  return `
    ${backBtn}
    <div class="poem-chain">
      <div class="chain-poem chain-poem-clickable" data-poem="${esc(origPoem.id)}" tabindex="0" role="button" aria-label="افتح قصيدة ${esc(origPoem.title)} كاملة">
        <div class="chain-poet-label">
          ${roleBadge(origPoem.role || "بدع")} ${esc(origPoet.name)}
          ${origPoem.date ? `<span class="poem-meta">· ${esc(origPoem.date)}</span>` : ""}
        </div>
        <h3 class="chain-title">${esc(origPoem.title)}</h3>
        ${origVerses
          ? `<div class="verses chain-verses">${origVerses}</div>`
          : `<p class="chain-no-verses">لم تُحفظ أبيات هذه القصيدة في الديوان</p>`}
        <span class="chain-open-hint">افتح القصيدة كاملة ←</span>
      </div>

      <div class="chain-divider">
        <span>${respPoem.role === "رد" ? "ردّ " + esc(respPoet.name) : "مجاراة " + esc(respPoet.name)}</span>
      </div>

      <div class="chain-poem">
        <div class="chain-poet-label">
          ${roleBadge(respPoem.role)}
          ${poetMark(respPoet, "width:16px;height:16px;")}
          ${esc(respPoet.name)}
          ${respPoem.date ? `<span class="poem-meta">· ${esc(respPoem.date)}</span>` : ""}
        </div>
        <h3 class="chain-title">${esc(respPoem.title)}</h3>
        <div class="verses chain-verses">${respVerses}</div>
      </div>
    </div>
    ${responsesSection}`;
}

function buildNormalView(backBtn, poet, poem, isExternal, responsesSection) {
  const versesHtml = buildVerses(poem.verses, { poet: poet.name, title: poem.title });
  return `
    ${backBtn}
    <div class="poem-header">
      ${isExternal
        ? `<span class="role-badge role-بدع" style="font-size:1rem;padding:4px 14px">بدع</span>`
        : poetMark(poet, "width:44px;height:44px;")}
      <h2>${esc(poem.title)}</h2>
      <div class="poem-meta">${esc(poet.name)}${poem.date ? " · " + esc(poem.date) : ""}${poem.meter ? " · " + esc(poem.meter) : ""}</div>
      ${roleBadge(poem.role)}
    </div>
    <div class="verses">${versesHtml}</div>
    ${responsesSection}`;
}
