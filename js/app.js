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

function wasmIcon(wasmId, extraStyle) {
  const svg = WASM_ICONS[wasmId] || "";
  return svg.replace("<svg ", `<svg style="color:var(--gold);${extraStyle || ""}" `);
}

const state = {
  data: null,
  activePoet: "all",
  query: ""
};

const el = {
  subtitle: document.getElementById("site-subtitle"),
  wasmLegend: document.getElementById("wasm-legend"),
  filterPills: document.getElementById("filter-pills"),
  searchInput: document.getElementById("search-input"),
  poemsGrid: document.getElementById("poems-grid"),
  poemDetail: document.getElementById("poem-detail"),
  footerYear: document.getElementById("footer-year"),
  footerNote: document.getElementById("footer-note")
};

init();

async function init() {
  el.footerYear.textContent = new Date().getFullYear();

  try {
    const res = await fetch("data/diwan.json");
    if (!res.ok) throw new Error("HTTP " + res.status);
    state.data = await res.json();
  } catch (err) {
    el.poemsGrid.innerHTML = `<div class="empty-state">تعذّر تحميل بيانات الديوان.<br><small style="opacity:0.7">${err.message}</small></div>`;
    return;
  }

  el.subtitle.textContent = state.data.site.subtitle || "";
  if (el.footerNote) el.footerNote.textContent = state.data.site.footerNote || "";

  renderWasmLegend();
  renderFilterPills();
  bindGlobalEvents();
  handleRoute();
  window.addEventListener("hashchange", handleRoute);
}

function renderWasmLegend() {
  el.wasmLegend.innerHTML = state.data.poets.map(poet =>
    `<button class="wasm-legend-item" data-poet="${poet.id}" aria-label="عرض قصائد ${poet.name}">
      ${wasmIcon(poet.wasm)}
      <span>${poet.name}</span>
    </button>`
  ).join("");
}

function renderFilterPills() {
  const poetPills = state.data.poets.map(poet =>
    `<button class="pill" data-poet="${poet.id}">
      ${wasmIcon(poet.wasm, "width:16px;height:16px;")}
      ${poet.name}
    </button>`
  ).join("");
  el.filterPills.innerHTML = `<button class="pill active" data-poet="all">الكل</button>${poetPills}`;
}

function bindGlobalEvents() {
  document.addEventListener("click", (e) => {
    const pill = e.target.closest("[data-poet]");
    if (pill) {
      location.hash = pill.dataset.poet === "all" ? "" : `poet=${pill.dataset.poet}`;
    }
    const card = e.target.closest("[data-poem]");
    if (card) {
      location.hash = `poem=${card.dataset.poem}`;
    }
    const back = e.target.closest(".back-btn");
    if (back) {
      location.hash = back.dataset.returnTo ? `poet=${back.dataset.returnTo}` : "";
    }
  });

  el.searchInput.addEventListener("input", (e) => {
    state.query = e.target.value.trim();
    if (location.hash.startsWith("#poem=")) location.hash = "";
    renderGridView();
  });
}

function handleRoute() {
  const hash = decodeURIComponent(location.hash.replace(/^#/, ""));
  const [key, value] = hash.split("=");

  if (key === "poem" && value) {
    showPoem(value);
    return;
  }

  state.activePoet = key === "poet" && value ? value : "all";
  renderGridView();
}

function getAllPoemsFlat() {
  const out = [];
  state.data.poets.forEach(poet => {
    poet.poems.forEach(poem => out.push({ poet, poem }));
  });
  return out;
}

function renderGridView() {
  el.poemDetail.classList.add("hidden");
  el.poemsGrid.classList.remove("hidden");

  document.querySelectorAll(".pill").forEach(p => {
    p.classList.toggle("active", p.dataset.poet === state.activePoet);
  });

  let items = getAllPoemsFlat();

  if (state.activePoet !== "all") {
    items = items.filter(({ poet }) => poet.id === state.activePoet);
  }
  if (state.query) {
    const q = state.query.toLowerCase();
    items = items.filter(({ poem }) => poem.title.toLowerCase().includes(q));
  }

  const bioBanner = renderBioBanner();

  if (items.length === 0) {
    el.poemsGrid.innerHTML = bioBanner + `<div class="empty-state">لا توجد قصائد مطابقة لبحثك حتى الآن.</div>`;
    return;
  }

  const cards = items.map(({ poet, poem }) =>
    `<article class="poem-card" data-poem="${poem.id}" tabindex="0" role="button">
      <div class="poem-card-tag">${wasmIcon(poet.wasm, "width:14px;height:14px;")} ${poet.name}</div>
      <h3>${poem.title}</h3>
      <p>${poem.verses[0] ? poem.verses[0].sadr : ""}</p>
    </article>`
  ).join("");

  el.poemsGrid.innerHTML = bioBanner + cards;
}

function renderBioBanner() {
  if (state.activePoet === "all") return "";
  const poet = state.data.poets.find(p => p.id === state.activePoet);
  if (!poet) return "";
  return `<div class="poet-bio-banner">
    ${wasmIcon(poet.wasm)}
    <div>
      <h2>${poet.name}</h2>
      <p>${poet.bio}</p>
    </div>
  </div>`;
}

function showPoem(poemId) {
  const found = getAllPoemsFlat().find(({ poem }) => poem.id === poemId);
  if (!found) {
    handleRoute();
    return;
  }
  const { poet, poem } = found;

  el.poemsGrid.classList.add("hidden");
  el.poemDetail.classList.remove("hidden");

  document.querySelectorAll(".pill").forEach(p => p.classList.remove("active"));

  const versesHtml = poem.verses.map(v =>
    `<div class="verse">
      <span class="sadr">${v.sadr}</span>
      <span class="divider"></span>
      <span class="ajz">${v.ajz}</span>
    </div>`
  ).join("");

  el.poemDetail.innerHTML = `
    <button class="back-btn" data-return-to="${poet.id}">→ الرجوع إلى قصائد ${poet.name}</button>
    <div class="poem-header">
      ${wasmIcon(poet.wasm)}
      <h2>${poem.title}</h2>
      <div class="poem-meta">${poet.name}${poem.date ? " · " + poem.date : ""}${poem.meter ? " · " + poem.meter : ""}</div>
    </div>
    <div class="verses">${versesHtml}</div>`;
}
