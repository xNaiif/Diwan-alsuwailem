---
name: homepage-redesign
description: Audit and redesign the Diwan Al-Suwailem homepage/landing page for a minimal, professional, non-distracting UX, unify the poet-avatar visual treatment site-wide, and measure before/after performance. Use when asked to redesign, declutter, or polish the homepage/landing page, or to unify how poet photos/icons/placeholders look across the site.
---

# Homepage & poet-avatar redesign

This site (`diwan-alswilem.com`) renders every page twice — once statically via
`scripts/generate_pages.py` (Python) for SEO, and once client-side via
`js/app.js` (the homepage SPA). **Any visual/behavioral change must be applied
identically in both paths**, or the two will drift (a recurring bug class in
this repo's history).

## 1. Audit first

Before touching anything, read and note:
- `index.html` — homepage skeleton (hero, filter bar, grid).
- `css/style.css` — search for `.hero`, `.filter-bar`, `.filter-pills`,
  `.pill`, `.poem-card`, `.poems-grid`, `.poet-photo`,
  `.poet-photo-placeholder`.
- `js/app.js` — `poetMark()` (poet avatar renderer, ~line 29), `WASM_ICONS`
  (geometric monogram fallback for founding poets without a photo),
  `renderHeroStats()`, `buildNormalView`/`buildChainView`/`poemInfoHtml`.
- `scripts/generate_pages.py` — `poet_icon_html()` (static-page avatar
  renderer) and the two duplicate inline `poet-photo-placeholder` blocks in
  `build_poet_page`/`build_poets_index_page` — check whether they've drifted
  from `poet_icon_html()`.
- Design tokens already established this session (reuse, don't invent new
  ones unless there's a real gap): `--bg:#15110d --surface:#211a13
  --ember:#d9803f --gold:#c9a227 --sage:#6f9a78 --sky:#5b8fa8`, display font
  Amiri, body font IBM Plex Sans Arabic, data/mono font IBM Plex Mono, dark
  theme only, RTL.

## 2. Known concrete defect: poet avatar has three inconsistent looks

1. Real photo — static pages: `border-radius:50%;object-fit:cover` (circular
   crop). SPA (`css/style.css` `.poet-photo`): `object-fit:contain`, **no**
   border-radius (rectangular, uncropped). These must match.
2. Founding poets without a photo but with a `wasm` field — a small
   geometric SVG monogram (`WASM_ICONS`), no circular frame/ring.
3. Anyone with neither — a dashed-border circle with a "▲" placeholder glyph.

Design ONE avatar component (a fixed-size circular frame with a subtle
border/ring in the site's palette) that wraps all three cases consistently —
photo, wasm icon, and placeholder should read as "the same kind of object at
different fill states," not three different UI patterns. Apply it in:
`poetMark()` (app.js), `poet_icon_html()` (generate_pages.py), and the two
inline duplicate blocks in `build_poet_page`/`build_poets_index_page` — or
better, make those two call `poet_icon_html()` instead of duplicating markup,
removing the drift risk permanently. Update `.poet-photo` /
`.poet-photo-placeholder` CSS to match.

For poets with only a placeholder, consider a nicer fallback than "▲" (e.g.
the poet's first initial letter) — confirm with visual judgment, not a hunch.

## 3. Redesign scope

Minimal, professional, non-distracting landing page. Concretely look at:
- Hero section spacing/hierarchy (already has real stat counters — don't
  duplicate poet-selection UI here, that belongs to the filter bar only).
- Filter bar: on mobile it currently stacks ~9 poet pills vertically before
  the search box, which reads as cluttered/long. Consider a more compact
  mobile pattern (e.g. horizontal scroll strip, or a collapsed
  "اختر شاعر ▾" control) while keeping desktop as-is if it already works.
- Visual rhythm between hero → filter bar → grid → footer (avoid uniform
  flat background across all sections if it reads as monotonous).
- Poem card design consistency with the unified avatar component above.

Do not add new sections, features, or content — this is a layout/visual
pass, not a new-feature pass (those are tracked separately in the roadmap).

## 4. Implementation discipline (repo-specific, do not skip)

- CSP is strict (`script-src 'self'`, no `unsafe-inline` for scripts) — all
  static-page JS must live in `js/site-common.js`; the SPA logic stays in
  `js/app.js`. Never add inline `<script>` to generated pages.
- Bump `CSS_VERSION` in `scripts/generate_pages.py` and the matching
  `css/style.css?v=` in `index.html` for any CSS change. Bump the
  `js/app.js?v=` query param in `index.html` for any JS change.
- Regenerate after any `data/diwan.json`, template, or CSS/JS content
  change: `python3 scripts/generate_pages.py` — it runs `validate_data()`
  first and will `sys.exit()` loudly on duplicate IDs or broken
  `mujarat.respondingToId` refs. Never bypass or silence this.
- Syntax-check JS: `node -c js/app.js`.
- If editing poet photos, work only on the `assets/poets/poet-N-thumb.webp`
  files (already the ones referenced by `data/diwan.json`) — keep the
  original `poet-N.jpg` files untouched as source-of-truth backups. Use PIL;
  reasonable non-destructive enhancement only (sharpen/contrast/levels) —
  never fabricate detail, never upscale beyond the source resolution in a
  way that invents texture.

## 5. Test before handing back

- `python3 -m http.server` locally (do NOT trust direct Playwright
  navigation to the live `diwan-alswilem.com` domain from this sandbox — it
  hits proxy connection resets; always mirror-and-serve locally, or serve
  the local working tree directly, then point Playwright at
  `http://127.0.0.1:<port>`).
- Screenshot the homepage at desktop (~1280px) and mobile (~390px) widths,
  before and after your changes, for comparison.
- Check the browser console for CSP violations / JS errors on the homepage
  and at least one poem page and one poet page.
- Confirm real numbers still render correctly in the hero stat counters.

## 6. Measure performance (before vs after)

Capture and report:
- Transferred bytes for `index.html` + `css/style.css` + `js/app.js` +
  `data/diwan-index.json` (the initial paint's critical path) — before your
  changes (from the git history / a clean checkout of the prior commit) vs
  after.
- Request count on initial homepage load.
- Playwright-measured timing: use the Navigation Timing API
  (`performance.timing` or `performance.getEntriesByType("navigation")`) for
  a rough load/DOMContentLoaded delta, before vs after, on the same local
  server setup for a fair comparison.

Write a short report (numbers + 3-5 sentence summary, in Arabic) to a file
in the caller-provided scratchpad location — don't invent a location.

## 7. Handoff

Do not push to `origin/main` yourself. Leave the finished, tested,
regenerated, committed state in your working tree/branch and report back
with: what changed, the before/after screenshots' file paths, and the
performance numbers. The orchestrating session reviews the diff and handles
the final rebase + push (this repo has concurrent writers — a tool and CI —
so pushes are centralized to avoid races).
