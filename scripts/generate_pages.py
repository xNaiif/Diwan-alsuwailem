#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مولّد صفحات ثابتة لديوان آل السويلم — يقرأ data/diwan.json ويبني:
  - صفحة HTML كاملة لكل قصيدة تحت /poems/
  - صفحة HTML لكل شاعر تحت /poets/
  - صفحة فهرس الشعراء /poets/
  - صفحة 404 مخصّصة
  - sitemap.xml
  - robots.txt
يشتغل تلقائياً عبر GitHub Actions عند أي دفعة (push) — لا يحتاج أي شي يدوي.
"""

import json
import html
import datetime
from pathlib import Path

SITE_URL = "https://diwan-alswilem.com"
SITE_NAME = "ديوان آل السويلم"
ROOT = Path(__file__).resolve().parent.parent  # جذر المستودع
DATA_PATH = ROOT / "data" / "diwan.json"
POEMS_DIR = ROOT / "poems"
POETS_DIR = ROOT / "poets"

ROLE_LABELS = {"بدع": "بدع (أصلية)", "رد": "ردّ", "مجاراة": "مجاراة"}


def esc(s):
    return html.escape(str(s or ""), quote=True)


def load_data():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def flat_poems(data):
    """كل القصائد (داخلية وخارجية) بشكل مسطّح، مع علم isExternal."""
    out = []
    for poet in data.get("poets", []):
        for poem in poet.get("poems", []):
            out.append({"poet": poet, "poem": poem, "isExternal": False})
    for poet in data.get("externalPoets", []):
        for poem in poet.get("poems", []):
            out.append({"poet": poet, "poem": poem, "isExternal": True})
    return out


def find_poem(all_poems, poem_id):
    for item in all_poems:
        if item["poem"]["id"] == poem_id:
            return item
    return None


def build_responses_map(all_poems):
    """poemId -> [قصائد ترد عليها]"""
    m = {}
    for item in all_poems:
        target = (item["poem"].get("mujarat") or {}).get("respondingToId")
        if target:
            m.setdefault(target, []).append(item["poem"]["id"])
    return m


def render_verses(verses):
    if not verses:
        return ""
    rows = []
    for v in verses:
        rows.append(
            f'<div class="verse"><span class="sadr">{esc(v.get("sadr"))}</span>'
            f'<span class="divider"></span>'
            f'<span class="ajz">{esc(v.get("ajz"))}</span></div>'
        )
    return "\n".join(rows)


SITE_CSP = (
    "default-src 'self'; img-src 'self' data:; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; script-src 'self'; connect-src 'self'; "
    "base-uri 'self'; form-action 'self'"
)


def organization_dict():
    return {"@type": "Organization", "name": SITE_NAME, "url": f"{SITE_URL}/"}


# ---------------------------------------------------------------------------
# مسار التنقّل (Breadcrumbs) — مصدر واحد يُستخدم لبناء الشريط المرئي وJSON-LD معاً
# ---------------------------------------------------------------------------

def poem_breadcrumb_items(poet, poem, is_external, canonical_url):
    items = [{"name": SITE_NAME, "url": f"{SITE_URL}/"}]
    if is_external:
        items.append({"name": "شعراء تجاوبوا مع الديوان", "url": f"{SITE_URL}/respondents.html"})
    else:
        items.append({"name": "الشعراء", "url": f"{SITE_URL}/poets/"})
        items.append({"name": poet.get("name"), "url": f"{SITE_URL}/poets/{poet['id']}.html"})
    items.append({"name": poem.get("title"), "url": canonical_url})
    return items


def poet_breadcrumb_items(poet, canonical_url):
    return [
        {"name": SITE_NAME, "url": f"{SITE_URL}/"},
        {"name": "الشعراء", "url": f"{SITE_URL}/poets/"},
        {"name": poet.get("name"), "url": canonical_url},
    ]


def simple_breadcrumb_items(label, canonical_url):
    return [
        {"name": SITE_NAME, "url": f"{SITE_URL}/"},
        {"name": label, "url": canonical_url},
    ]


def breadcrumb_html(items):
    parts = []
    last_index = len(items) - 1
    for i, it in enumerate(items):
        if i > 0:
            parts.append('<span class="crumb-sep" aria-hidden="true">/</span>')
        if i == last_index:
            parts.append(f'<span aria-current="page">{esc(it["name"])}</span>')
        else:
            parts.append(f'<a href="{esc(it["url"])}">{esc(it["name"])}</a>')
    return f'<nav class="breadcrumbs" aria-label="مسار التنقل">{"".join(parts)}</nav>'


def breadcrumb_json_ld(items):
    elements = [
        {"@type": "ListItem", "position": i + 1, "name": it["name"], "item": it["url"]}
        for i, it in enumerate(items)
    ]
    return {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": elements}


def ld_scripts(*blocks):
    return "\n".join(f'<script type="application/ld+json">{json.dumps(b, ensure_ascii=False)}</script>' for b in blocks)


# ---------------------------------------------------------------------------
# القالب الأساسي
# ---------------------------------------------------------------------------

def page_shell(title, description, canonical_url, body_html, json_ld="", robots="index, follow"):
    """القالب الأساسي المشترك لأي صفحة ثابتة، يعيد استخدام نفس css/style.css."""
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}" />
<meta name="robots" content="{esc(robots)}" />
<link rel="canonical" href="{esc(canonical_url)}" />
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml" />
<link rel="icon" href="/assets/favicon-32.png" sizes="32x32" type="image/png" />
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png" />
<link rel="manifest" href="/manifest.webmanifest" />

<meta property="og:type" content="article" />
<meta property="og:title" content="{esc(title)}" />
<meta property="og:description" content="{esc(description)}" />
<meta property="og:url" content="{esc(canonical_url)}" />
<meta property="og:image" content="{SITE_URL}/assets/og-image.jpg" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:locale" content="ar_SA" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{esc(title)}" />
<meta name="twitter:description" content="{esc(description)}" />
<meta name="twitter:image" content="{SITE_URL}/assets/og-image.jpg" />
<meta name="theme-color" content="#15110d" />
<meta http-equiv="Content-Security-Policy" content="{SITE_CSP}" />

<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Amiri:ital,wght@0,400;0,700;1,400;1,700&family=IBM+Plex+Sans+Arabic:wght@300;400;500;600;700&display=swap" rel="stylesheet" />
<link rel="stylesheet" href="/css/style.css" />
{json_ld}
</head>
<body>
<div class="ember-glow" aria-hidden="true"></div>
<header class="hero" style="padding:32px 20px 20px">
  <div class="hero-inner">
    <a href="/" style="text-decoration:none">
      <p class="hero-eyebrow">ديوان أسرة</p>
      <p class="hero-title" style="font-size:clamp(1.8rem,6vw,2.6rem)">آل السويلم</p>
    </a>
  </div>
</header>
<main id="main-view">
{body_html}
</main>
<footer class="site-footer">
  <p>{SITE_NAME} — © {esc(str(datetime.date.today().year))}
    <span class="footer-note">هذه صفحة ثابتة لتسهيل الوصول والفهرسة — <a href="/" style="color:var(--gold)">تصفّح الديوان كامل من هنا</a></span>
  </p>
</footer>
</body>
</html>"""


def poem_json_ld(poet, poem, canonical_url, is_external):
    verses_text = " / ".join(
        f'{v.get("sadr","")} … {v.get("ajz","")}' for v in (poem.get("verses") or [])
    )
    creative_work = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": poem.get("title"),
        "author": {"@type": "Person", "name": poet.get("name")},
        "publisher": organization_dict(),
        "inLanguage": "ar",
        "genre": "شعر نبطي",
        "url": canonical_url,
    }
    if poem.get("date"):
        creative_work["dateCreated"] = poem["date"]
    if verses_text:
        creative_work["text"] = verses_text[:2000]

    breadcrumb = breadcrumb_json_ld(poem_breadcrumb_items(poet, poem, is_external, canonical_url))
    return ld_scripts(creative_work, breadcrumb)


def poet_json_ld(poet, canonical_url):
    data = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": poet.get("name"),
        "url": canonical_url,
        "description": poet.get("bio") or None,
        "image": f"{SITE_URL}{poet['photo']}" if poet.get("photo") else None,
    }
    data = {k: v for k, v in data.items() if v is not None}
    breadcrumb = breadcrumb_json_ld(poet_breadcrumb_items(poet, canonical_url))
    return ld_scripts(data, breadcrumb)


def poem_info_html(poet, poem):
    """كتلة دلالية (dl) بمعلومات القصيدة — تعرض فقط الحقول المتوفرة فعلياً، بدون أي اختلاق بيانات."""
    fields = [
        ("الشاعر", poet.get("name")),
        ("التاريخ", poem.get("date")),
        ("البحر/الوزن", poem.get("meter")),
        ("النوع", ROLE_LABELS.get(poem.get("role"))),
        ("المصدر", poem.get("source")),
    ]
    rows = "".join(
        f'<div><dt>{esc(label)}:</dt><dd>{esc(value)}</dd></div>'
        for label, value in fields if value
    )
    return f'<dl class="poem-info">{rows}</dl>' if rows else ""


def related_poems_html(poet, poem, is_external):
    others = [p for p in poet.get("poems", []) if p.get("id") != poem.get("id")]
    if not others:
        return ""
    items = "".join(
        f'<li><a href="/poems/{esc(p["id"])}.html">{esc(p["title"])}</a></li>' for p in others[:3]
    )
    poet_link = (
        "" if is_external else
        f'<p style="margin-top:10px"><a href="/poets/{esc(poet["id"])}.html" style="color:var(--gold)">كل قصائد {esc(poet["name"])} ←</a></p>'
    )
    return (
        f'<div class="related-poems"><span class="section-label" style="margin:0">'
        f'قصائد أخرى لـ{esc(poet["name"])}</span><ul>{items}</ul>{poet_link}</div>'
    )


def build_poem_page(item, all_poems, responses_map):
    poet, poem, is_external = item["poet"], item["poem"], item["isExternal"]
    canonical = f"{SITE_URL}/poems/{poem['id']}.html"
    description = poem.get("verses", [{}])[0].get("sadr", poem["title"]) if poem.get("verses") else poem["title"]
    title = f'{poem["title"]} — {poet["name"]} | {SITE_NAME}'

    breadcrumb_nav = breadcrumb_html(poem_breadcrumb_items(poet, poem, is_external, canonical))
    info_html = poem_info_html(poet, poem)
    related_html = related_poems_html(poet, poem, is_external)

    is_chain = poem.get("role") in ("رد", "مجاراة") and (poem.get("mujarat") or {}).get("respondingToId")
    original = find_poem(all_poems, poem["mujarat"]["respondingToId"]) if is_chain else None

    responses_html = ""
    resp_ids = responses_map.get(poem["id"], [])
    if resp_ids:
        links = []
        for rid in resp_ids:
            r = find_poem(all_poems, rid)
            if not r:
                continue
            links.append(
                f'<a class="mujarat-goto" href="/poems/{esc(r["poem"]["id"])}.html">'
                f'{esc(r["poet"]["name"])} — {esc(r["poem"]["title"])}</a>'
            )
        responses_html = (
            '<div class="mujarat-section" style="margin-top:24px">'
            '<span class="mujarat-label">ردود ومجاراات على هذه القصيدة</span>'
            f'<div class="mujarat-responses">{"".join(links)}</div></div>'
        )

    if is_chain and original:
        orig_poet, orig_poem = original["poet"], original["poem"]
        orig_verses = render_verses(orig_poem.get("verses"))
        resp_verses = render_verses(poem.get("verses"))
        role_word = "ردّ" if poem.get("role") == "رد" else "مجاراة"
        body = f"""
{breadcrumb_nav}
<div class="poem-chain">
  <div class="chain-poem">
    <div class="chain-poet-label">{esc(orig_poet["name"])}
      {f'<span class="poem-meta">· {esc(orig_poem.get("date"))}</span>' if orig_poem.get("date") else ""}
    </div>
    <h2 class="chain-title">{esc(orig_poem["title"])}</h2>
    {f'<div class="verses chain-verses">{orig_verses}</div>' if orig_verses else '<p class="chain-no-verses">لم تُحفظ أبيات هذه القصيدة في الديوان</p>'}
  </div>
  <div class="chain-divider"><span>{role_word} {esc(poet["name"])}</span></div>
  <div class="chain-poem">
    <div class="chain-poet-label">{esc(poet["name"])}
      {f'<span class="poem-meta">· {esc(poem.get("date"))}</span>' if poem.get("date") else ""}
    </div>
    <h1 class="chain-title">{esc(poem["title"])}</h1>
    <div class="verses chain-verses">{resp_verses}</div>
  </div>
</div>
{info_html}
{responses_html}
{related_html}"""
    else:
        verses_html = render_verses(poem.get("verses"))
        body = f"""
{breadcrumb_nav}
<div class="poem-header">
  <h1>{esc(poem["title"])}</h1>
  <div class="poem-meta">{esc(poet["name"])}{f' · {esc(poem.get("date"))}' if poem.get("date") else ""}{f' · {esc(poem.get("meter"))}' if poem.get("meter") else ""}</div>
</div>
{f'<div class="verses">{verses_html}</div>' if verses_html else '<p style="text-align:center;color:var(--text-faint)">لم تُحفظ أبيات هذه القصيدة في الديوان بعد</p>'}
{info_html}
{responses_html}
{related_html}"""

    html_doc = page_shell(title, description, canonical, body, poem_json_ld(poet, poem, canonical, is_external))
    return poem["id"] + ".html", html_doc


def build_poet_page(poet):
    canonical = f"{SITE_URL}/poets/{poet['id']}.html"
    title = f'قصائد {poet["name"]} | {SITE_NAME}'
    description = poet.get("bio") or f'كل قصائد {poet["name"]} في {SITE_NAME}'
    breadcrumb_nav = breadcrumb_html(poet_breadcrumb_items(poet, canonical))

    cards = []
    for poem in poet.get("poems", []):
        first_verse = poem.get("verses", [{}])[0].get("sadr", "") if poem.get("verses") else ""
        cards.append(f"""
<a href="/poems/{esc(poem['id'])}.html" class="poem-card" style="display:block;text-decoration:none;margin-bottom:14px">
  <h2>{esc(poem["title"])}</h2>
  <p>{esc(first_verse)}</p>
</a>""")

    photo_html = (
        f'<img src="{esc(poet["photo"])}" alt="{esc("صورة الشاعر " + poet["name"])}" width="52" height="52" '
        f'style="width:52px;height:52px;border-radius:50%;object-fit:cover" loading="lazy" decoding="async" />'
        if poet.get("photo") else ""
    )
    bio_section = (
        f'<span class="section-label">نبذة عن الشاعر</span><p style="max-width:680px;margin:0 auto;color:var(--text-muted)">{esc(poet["bio"])}</p>'
        if poet.get("bio") else ""
    )
    body = f"""
{breadcrumb_nav}
<div class="poet-bio-banner">
  {photo_html}
  <div><h1>{esc(poet["name"])}</h1></div>
</div>
{bio_section}
<span class="section-label">قصائد الشاعر ({len(poet.get("poems", []))})</span>
<div class="poems-grid">{"".join(cards)}</div>
<p style="text-align:center;margin-top:20px"><a href="/poets/" style="color:var(--gold)">تصفّح كل شعراء الديوان ←</a></p>"""

    return poet["id"] + ".html", page_shell(title, description, canonical, body, poet_json_ld(poet, canonical))


def build_poets_index_page(data):
    """صفحة فهرس الشعراء — 'المستودع الرئيسي للشعراء' اللي تطلبه هيكلة SEO
    (الرئيسية → الشعراء → شاعر). رابط ثابت ومباشر لكل شعراء الديوان."""
    canonical = f"{SITE_URL}/poets/"
    title = f"شعراء {SITE_NAME}"
    description = f"فهرس كامل بشعراء أسرة آل السويلم في {SITE_NAME}، مع نبذة عن كل شاعر وعدد قصائده."
    breadcrumb_nav = breadcrumb_html(simple_breadcrumb_items("الشعراء", canonical))

    poets = data.get("poets", [])
    cards = []
    for poet in poets:
        photo_html = (
            f'<img src="{esc(poet["photo"])}" alt="{esc("صورة الشاعر " + poet["name"])}" loading="lazy" decoding="async" />'
            if poet.get("photo") else ""
        )
        bio_snippet = esc(poet.get("bio", ""))
        count = len(poet.get("poems", []))
        cards.append(f"""
<a href="/poets/{esc(poet['id'])}.html" class="poets-index-card">
  {photo_html}
  <div><h2>{esc(poet["name"])}</h2><p>{bio_snippet}{" — " if bio_snippet else ""}{count} قصيدة</p></div>
</a>""")

    respondents_link = (
        '<p style="text-align:center;margin-top:24px"><a href="/respondents.html" style="color:var(--gold)">شعراء من خارج آل السويلم تجاوبوا مع الديوان ←</a></p>'
        if data.get("externalPoets") else ""
    )

    body = f"""
{breadcrumb_nav}
<div class="poet-bio-banner">
  <div><h1>شعراء {SITE_NAME}</h1><p>{esc(description)}</p></div>
</div>
<div class="poets-index-grid">{"".join(cards)}</div>
{respondents_link}"""

    item_list = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": f"شعراء {SITE_NAME}",
        "itemListElement": [
            {
                "@type": "ListItem", "position": i + 1,
                "item": {"@type": "Person", "name": p["name"], "url": f"{SITE_URL}/poets/{p['id']}.html"},
            }
            for i, p in enumerate(poets)
        ],
    }
    breadcrumb = breadcrumb_json_ld(simple_breadcrumb_items("الشعراء", canonical))
    json_ld = ld_scripts(item_list, breadcrumb)

    return page_shell(title, description, canonical, body, json_ld)


def build_external_poets_page(data):
    """صفحة واحدة تجمع كل الشعراء من خارج آل السويلم اللي تجاوبوا مع الديوان عبر الزمن —
    كل قصيدة تربط لصفحتها المستقلة الموجودة أصلاً (نفس صفحات /poems/ العادية)."""
    canonical = f"{SITE_URL}/respondents.html"
    title = f"شعراء تجاوبوا مع الديوان | {SITE_NAME}"
    description = "شعراء من خارج آل السويلم شاركوا في مساجلات ومجاراة مع شعراء الديوان عبر الزمن."
    breadcrumb_nav = breadcrumb_html(simple_breadcrumb_items("شعراء تجاوبوا مع الديوان", canonical))

    sections = []
    for poet in data.get("externalPoets", []):
        items = "\n".join(
            f'<li><a href="/poems/{esc(poem["id"])}.html">{esc(poem["title"])}</a></li>'
            for poem in poet.get("poems", [])
        )
        sections.append(f"""
<div class="respondent-block">
  <h2>{esc(poet["name"])}</h2>
  <ul class="respondent-list">{items}</ul>
</div>""")

    body = f"""
{breadcrumb_nav}
<div class="poet-bio-banner">
  <div><h1>شعراء تجاوبوا مع الديوان</h1><p>{esc(description)}</p></div>
</div>
<div class="respondents-wrap">{"".join(sections)}</div>
<p style="text-align:center;margin-top:20px"><a href="/poets/" style="color:var(--gold)">تصفّح شعراء الديوان الأساسيين ←</a></p>"""

    breadcrumb = breadcrumb_json_ld(simple_breadcrumb_items("شعراء تجاوبوا مع الديوان", canonical))
    return "respondents.html", page_shell(title, description, canonical, body, ld_scripts(breadcrumb))


def build_404_page():
    canonical = f"{SITE_URL}/404.html"
    title = f"الصفحة غير موجودة | {SITE_NAME}"
    description = "الصفحة اللي تبحث عنها مو موجودة أو انتقلت مكان ثاني."
    body = f"""
<div class="not-found">
  <p class="code">404</p>
  <h1>الصفحة غير موجودة</h1>
  <p>يمكن الرابط قديم أو انكتب غلط. جرّب تتصفّح الديوان من الروابط تحت.</p>
  <div class="actions">
    <a href="/">الصفحة الرئيسية</a>
    <a href="/poets/">كل الشعراء</a>
  </div>
</div>"""
    return page_shell(title, description, canonical, body, robots="noindex, follow")


def build_sitemap(entries):
    """entries: قائمة (url, lastmod_or_None) — lastmod يُكتب فقط لو متوفر فعلياً، بدون اختلاق تواريخ."""
    rows = []
    for url, lastmod in entries:
        if lastmod:
            rows.append(f"  <url><loc>{esc(url)}</loc><lastmod>{esc(lastmod)}</lastmod></url>")
        else:
            rows.append(f"  <url><loc>{esc(url)}</loc></url>")
    entries_xml = "\n".join(rows)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries_xml}\n</urlset>\n'


def build_robots(sitemap_url):
    return f"User-agent: *\nAllow: /\n\nSitemap: {sitemap_url}\n"


INDEX_PATH = ROOT / "index.html"


def update_index_links(data):
    """يحدّث روابط الشعراء الحقيقية بالصفحة الرئيسية تلقائياً — يعطي جوجل مساراً حقيقياً
    من الصفحة الرئيسية إلى كل صفحات القصائد، بدون أي تأثير على تجربة الموقع التفاعلية."""
    if not INDEX_PATH.exists():
        return
    html_doc = INDEX_PATH.read_text(encoding="utf-8")
    start_marker = "<!-- SEO-LINKS-START -->"
    end_marker = "<!-- SEO-LINKS-END -->"
    if start_marker not in html_doc or end_marker not in html_doc:
        return
    links = '<a href="/poets/">كل الشعراء</a>\n    ' + "\n    ".join(
        f'<a href="/poets/{esc(p["id"])}.html">{esc(p["name"])}</a>'
        for p in data.get("poets", [])
    )
    if data.get("externalPoets"):
        links += '\n    <a href="/respondents.html">شعراء تجاوبوا مع الديوان</a>'

    block = (
        f'{start_marker}\n  <nav class="footer-links" aria-label="روابط سريعة لصفحات الشعراء">\n'
        f'    {links}\n  </nav>\n  {end_marker}'
    )
    before = html_doc.split(start_marker)[0]
    after = html_doc.split(end_marker)[1]
    INDEX_PATH.write_text(before + block + after, encoding="utf-8")


def clean_stale_pages(directory, expected_filenames):
    """يحذف أي صفحة HTML متبقية من قصائد/شعراء أُزيلوا من data/diwan.json —
    يمنع بقاء صفحات يتيمة مهجورة على الاستضافة وبفهرسة جوجل."""
    if not directory.exists():
        return
    for existing in directory.glob("*.html"):
        if existing.name not in expected_filenames:
            existing.unlink()
            print(f"✓ removed stale page {existing}")


def main():
    data = load_data()
    all_poems = flat_poems(data)
    responses_map = build_responses_map(all_poems)

    update_index_links(data)

    POEMS_DIR.mkdir(exist_ok=True)
    POETS_DIR.mkdir(exist_ok=True)

    sitemap_entries = [(SITE_URL + "/", None)]
    poem_filenames = set()
    poet_filenames = {"index.html"}  # فهرس الشعراء موجود بنفس مجلد poets/ ولازم ما يُحذف كصفحة "يتيمة"

    for item in all_poems:
        fname, html_doc = build_poem_page(item, all_poems, responses_map)
        (POEMS_DIR / fname).write_text(html_doc, encoding="utf-8")
        poem_filenames.add(fname)
        lastmod = item["poem"].get("addedAt")
        sitemap_entries.append((f"{SITE_URL}/poems/{fname}", lastmod))

    for poet in data.get("poets", []):
        fname, html_doc = build_poet_page(poet)
        (POETS_DIR / fname).write_text(html_doc, encoding="utf-8")
        poet_filenames.add(fname)
        sitemap_entries.append((f"{SITE_URL}/poets/{fname}", None))

    (POETS_DIR / "index.html").write_text(build_poets_index_page(data), encoding="utf-8")
    sitemap_entries.append((f"{SITE_URL}/poets/", None))

    clean_stale_pages(POEMS_DIR, poem_filenames)
    clean_stale_pages(POETS_DIR, poet_filenames)

    respondents_path = ROOT / "respondents.html"
    if data.get("externalPoets"):
        fname, html_doc = build_external_poets_page(data)
        (ROOT / fname).write_text(html_doc, encoding="utf-8")
        sitemap_entries.append((f"{SITE_URL}/{fname}", None))
    elif respondents_path.exists():
        respondents_path.unlink()

    (ROOT / "404.html").write_text(build_404_page(), encoding="utf-8")

    (ROOT / "sitemap.xml").write_text(build_sitemap(sitemap_entries), encoding="utf-8")
    (ROOT / "robots.txt").write_text(build_robots(f"{SITE_URL}/sitemap.xml"), encoding="utf-8")

    print(f"✓ built {len(all_poems)} poem pages, {len(data.get('poets', []))} poet pages + poets index + 404")
    print(f"✓ sitemap.xml with {len(sitemap_entries)} URLs")


if __name__ == "__main__":
    main()
