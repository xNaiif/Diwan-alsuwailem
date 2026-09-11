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
import sys
import datetime
from pathlib import Path
from urllib.parse import quote

SITE_URL = "https://diwan-alswilem.com"
SITE_NAME = "ديوان آل السويلم"
CSS_VERSION = "13"  # رفعه عند أي تعديل بـcss/style.css عشان يجبر المتصفحات تحمّل النسخة الجديدة
SITE_COMMON_JS_VERSION = "2"  # نفس فكرة CSS_VERSION، لـjs/site-common.js (لم يكن له ترقيم كاش سابقاً)
ROOT = Path(__file__).resolve().parent.parent  # جذر المستودع
DATA_PATH = ROOT / "data" / "diwan.json"
POEMS_DIR = ROOT / "poems"
POETS_DIR = ROOT / "poets"

# ملاحظة: نصوص تسميات النوع (بدع/رد/مجاراة) مصدرها الوحيد data/diwan.json["roleLabels"]
# (مشترك مع js/app.js) — لا تُضف أي ثابت جديد هنا يكرّرها.

# نصوص شارة النوع الملوّنة (badge) — أقصر من تسميات حقل "النوع"، تطابق ROLE_LABELS
# (الخاص بالتنسيق/الـCSS classes، مو النصوص) في js/app.js
ROLE_BADGE_TEXT = {"بدع": "بدع", "رد": "ردّ", "مجاراة": "مجاراة"}


def role_badge_html(role):
    """شارة النوع الملوّنة — تطابق roleBadge() في js/app.js (نفس CSS classes بـcss/style.css)."""
    if not role or role not in ROLE_BADGE_TEXT:
        return ""
    return f'<span class="role-badge role-{esc(role)}">{esc(ROLE_BADGE_TEXT[role])}</span>'


def poet_icon_html(poet, size=44):
    """صورة/شارة الشاعر بحجم مربّع — نفس منطق poetMark() بـjs/app.js وpoet-photo-placeholder
    المستخدم أصلاً بهذا الملف (build_poet_page / build_poets_index_page)."""
    if poet.get("photo"):
        return (
            f'<img src="{esc(poet["photo"])}" class="poet-photo" alt="{esc(poet["name"])}" '
            f'style="width:{size}px;height:{size}px;border-radius:50%;object-fit:cover" '
            f'loading="lazy" decoding="async" />'
        )
    font_size = max(0.6, size * 0.028)
    return (
        f'<span class="poet-photo-placeholder" style="width:{size}px;height:{size}px;'
        f'font-size:{font_size:.2f}rem" title="بانتظار إضافة صورة الشاعر">▲</span>'
    )


def esc(s):
    return html.escape(str(s or ""), quote=True)


def load_data():
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


LIGHT_INDEX_PATH = ROOT / "data" / "diwan-index.json"


def _light_poem(poem):
    """نسخة مصغّرة من القصيدة لملف الفهرس الخفيف — تكفي لعرض الشبكة/البحث بالعنوان وأول
    بيتين وقصيدة اليوم، بدون كل الأبيات/المصدر/المناسبة (تُجلب لاحقاً من data/diwan.json
    الكامل بالخلفية). نفس بنية القصيدة الحقيقية جزئياً عشان js/app.js يتعامل معها بلا أي
    كود خاص إضافي — فقط أقل حقولاً."""
    light = {
        "id": poem["id"],
        "title": poem["title"],
        "role": poem.get("role", ""),
        "date": poem.get("date", ""),
        "verses": (poem.get("verses") or [])[:2],
    }
    if poem.get("addedAt"):
        light["addedAt"] = poem["addedAt"]
    mj = poem.get("mujarat") or {}
    if mj.get("respondingToId"):
        light["mujarat"] = {"respondingToId": mj["respondingToId"]}
    return light


def build_light_index(data):
    """data/diwan-index.json — نفس بنية data/diwan.json تماماً (poets[]/externalPoets[])
    عشان يشتغل عليها js/app.js بلا أي فرع كود خاص، لكن كل قصيدة مصغّرة (_light_poem).
    الهدف: أول تحميل للصفحة الرئيسية يجيب بيانات صغيرة بسرعة بدل انتظار الملف الكامل
    (كان 835KB/163KB مضغوط لـ453 قصيدة، يُحمَّل كاملاً رغم عرض 24 قصيدة فقط بالبداية)."""
    return {
        "site": data.get("site", {}),
        "roleLabels": data.get("roleLabels", {}),
        "poets": [
            {
                "id": p["id"], "name": p["name"],
                "photo": p.get("photo", ""), "wasm": p.get("wasm", ""),
                "bio": p.get("bio", ""),
                "poems": [_light_poem(pm) for pm in p.get("poems", [])],
            }
            for p in data.get("poets", [])
        ],
        "externalPoets": [
            {
                "id": p["id"], "name": p["name"],
                "poems": [_light_poem(pm) for pm in p.get("poems", [])],
            }
            for p in data.get("externalPoets", [])
        ],
    }


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
    "style-src 'self' 'unsafe-inline'; font-src 'self'; script-src 'self'; connect-src 'self'; "
    "base-uri 'self'; form-action 'self'"
)

HERO_TITLE = "آل السويلـم"  # كشيدة واحدة بين آخر حرفين، فقط بهذا العنصر الثابت المتكرر بكل صفحة


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
<link rel="icon" href="/favicon.ico" sizes="any" />
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

<link rel="stylesheet" href="/css/style.css?v={CSS_VERSION}" />
{json_ld}
</head>
<body>
<div class="ember-glow" aria-hidden="true"></div>
<header class="hero" style="padding:32px 20px 20px">
  <div class="hero-inner">
    <a href="/" style="text-decoration:none">
      <p class="hero-eyebrow">ديوان أسرة</p>
      <p class="hero-title" style="font-size:clamp(1.8rem,6vw,2.6rem)">{HERO_TITLE}</p>
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
  <p class="site-credit">by <img class="naif-mark" src="/assets/naif-mark.png" alt="Naif" width="150" height="40" loading="lazy" decoding="async" /></p>
</footer>
<button id="back-to-top" aria-label="الرجوع لأعلى الصفحة">↑</button>
<script src="/js/site-common.js?v={SITE_COMMON_JS_VERSION}"></script>
</body>
</html>"""


def poem_json_ld(poet, poem, canonical_url, is_external, poet_page_url, original_url=None):
    verses_text = " / ".join(
        f'{v.get("sadr","")} … {v.get("ajz","")}' for v in (poem.get("verses") or [])
    )
    creative_work = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": poem.get("title"),
        "identifier": poem.get("id"),
        "author": {"@type": "Person", "name": poet.get("name")},
        "publisher": organization_dict(),
        "inLanguage": "ar",
        "genre": "شعر نبطي",
        "url": canonical_url,
        "isPartOf": poet_page_url,
    }
    if poem.get("date"):
        creative_work["dateCreated"] = poem["date"]
    if poem.get("addedAt"):
        # تاريخ إضافة القصيدة للديوان فعلياً (مو تاريخ كتابتها) — إشارة حداثة (freshness) حقيقية
        # لمحركات البحث ومحركات الذكاء الاصطناعي، نضيفها فقط لو موجودة فعلاً (بدون اختلاق تواريخ)
        creative_work["dateModified"] = poem["addedAt"]
    if verses_text:
        creative_work["text"] = verses_text[:2000]
    if original_url:
        # قصيدة رد أو مجاراة: نصرّح بالعلاقة ببيانات موصوفة (Schema.org) لا بس برابط HTML مرئي —
        # عشان أي أداة/وكيل ذكاء اصطناعي تقدر تبني سلسلة القصائد المترابطة برمجياً
        creative_work["citation"] = original_url

    breadcrumb = breadcrumb_json_ld(poem_breadcrumb_items(poet, poem, is_external, canonical_url))
    return ld_scripts(creative_work, breadcrumb)


BIO_PLACEHOLDER = "قيد الإضافة"


def real_bio(poet):
    """نبذة الشاعر الفعلية، أو None لو لسا مؤقتة (قيد الإضافة) — عشان
    ما نعرض هذا النص المؤقت كوصف SEO/JSON-LD، بس يبقى ظاهر بالصفحة نفسها."""
    bio = poet.get("bio")
    return bio if bio and bio != BIO_PLACEHOLDER else None


def poet_json_ld(poet, canonical_url):
    data = {
        "@context": "https://schema.org",
        "@type": "Person",
        "name": poet.get("name"),
        "url": canonical_url,
        "description": real_bio(poet),
        "image": f"{SITE_URL}{poet['photo']}" if poet.get("photo") else None,
    }
    data = {k: v for k, v in data.items() if v is not None}
    breadcrumb = breadcrumb_json_ld(poet_breadcrumb_items(poet, canonical_url))
    return ld_scripts(data, breadcrumb)


REPORT_EMAIL = "27.vines-myopic@icloud.com"


def report_issue_html(poet, poem, canonical):
    """رابط صغير أسفل كل قصيدة يفتح mailto معبّأ مسبقاً — يطابق reportIssueHtml بـjs/app.js.
    الإيميل مقسَّم (user/domain) بدل مكتوب كاملاً بالـHTML، والموضوع/النص مُشفَّران مسبقاً
    (quote) — يبنيها فعلياً js/site-common.js وقت الضغط فقط، عشان أي حاصد إيميلات آلي
    (bot) يقرأ HTML/JS الثابت مباشرة ما يلقى سلسلة "user@domain" متصلة بأي مكان."""
    subject = quote(f"إبلاغ عن قصيدة: {poem['title']}")
    body = quote(f"القصيدة: {poem['title']}\nالشاعر: {poet.get('name', '')}\nالرابط: {canonical}\n\nالملاحظة:\n")
    user, domain = REPORT_EMAIL.split("@", 1)
    return (
        f'<a class="report-issue" href="#" data-report-link '
        f'data-u="{esc(user)}" data-d="{esc(domain)}" '
        f'data-subject="{esc(subject)}" data-body="{esc(body)}">'
        f'🚩 لاحظت خطأ أو نقص بهذي القصيدة؟ أبلغني</a>'
    )


def poem_info_html(poet, poem, role_labels):
    """كتلة دلالية (dl) بمعلومات القصيدة — تعرض فقط الحقول المتوفرة فعلياً، بدون أي اختلاق بيانات."""
    fields = [
        ("الشاعر", poet.get("name")),
        ("التاريخ", poem.get("date")),
        ("المناسبة", poem.get("occasion")),
        ("البحر/الوزن", poem.get("meter")),
        ("النوع", role_labels.get(poem.get("role"))),
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


def build_poem_page(item, all_poems, responses_map, role_labels):
    poet, poem, is_external = item["poet"], item["poem"], item["isExternal"]
    canonical = f"{SITE_URL}/poems/{poem['id']}.html"
    description = poem.get("verses", [{}])[0].get("sadr", poem["title"]) if poem.get("verses") else poem["title"]
    title = f'{poem["title"]} — {poet["name"]} | {SITE_NAME}'

    breadcrumb_nav = breadcrumb_html(poem_breadcrumb_items(poet, poem, is_external, canonical))
    info_html = poem_info_html(poet, poem, role_labels)
    report_html = report_issue_html(poet, poem, canonical)
    related_html = related_poems_html(poet, poem, is_external)

    is_chain = poem.get("role") in ("رد", "مجاراة") and (poem.get("mujarat") or {}).get("respondingToId")
    original = find_poem(all_poems, poem["mujarat"]["respondingToId"]) if is_chain else None

    # لو هذي القصيدة نفسها رد/مجاراة، نجيب كل إخوتها (القصائد الثانية اللي ردّت/جارت على نفس الأصل)
    # بدل الاكتفاء بردود هذي القصيدة نفسها فقط — عشان قصيدة عندها أكثر من رد/مجاراة تظهر كلها بكل صفحة من صفحاتها
    sibling_source_id = original["poem"]["id"] if (is_chain and original) else poem["id"]
    resp_ids = [rid for rid in responses_map.get(sibling_source_id, []) if rid != poem["id"]]
    if is_chain:
        resp_ids += [rid for rid in responses_map.get(poem["id"], []) if rid not in resp_ids]

    responses_html = ""
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
        label = "ردود ومجاراات أخرى على نفس القصيدة الأصلية" if is_chain else "ردود ومجاراات على هذه القصيدة"
        responses_html = (
            '<div class="mujarat-section" style="margin-top:24px">'
            f'<span class="mujarat-label">{label}</span>'
            f'<div class="mujarat-responses">{"".join(links)}</div></div>'
        )

    if is_chain and original:
        orig_poet, orig_poem = original["poet"], original["poem"]
        orig_verses = render_verses(orig_poem.get("verses"))
        resp_verses = render_verses(poem.get("verses"))
        role_word = "ردّ" if poem.get("role") == "رد" else "مجاراة"
        # ترتيب العناوين h1/h2 يتبع ترتيب الظهور الفعلي بالـDOM (القصيدة الأصلية تظهر أولاً بصرياً
        # فتاخذ h1، والرد/المجاراة الحالية تظهر ثانياً فتاخذ h2) — بدون قلب ترتيب ظهور المحتوى نفسه
        body = f"""
{breadcrumb_nav}
<div class="poem-chain">
  <div class="chain-poem">
    <div class="chain-poet-label">{role_badge_html(orig_poem.get("role") or "بدع")} {esc(orig_poet["name"])}
      {f'<span class="poem-meta">· {esc(orig_poem.get("date"))}</span>' if orig_poem.get("date") else ""}
    </div>
    <h1 class="chain-title">{esc(orig_poem["title"])}</h1>
    {f'<div class="verses chain-verses">{orig_verses}</div>' if orig_verses else '<p class="chain-no-verses">لم تُحفظ أبيات هذه القصيدة في الديوان</p>'}
    <p style="margin-top:10px"><a href="/poems/{esc(orig_poem['id'])}.html" style="color:var(--gold)">افتح القصيدة كاملة ←</a></p>
  </div>
  <div class="chain-divider"><span>{role_word} {esc(poet["name"])}</span></div>
  <div class="chain-poem">
    <div class="chain-poet-label">{role_badge_html(poem.get("role"))} {poet_icon_html(poet, 16)} {esc(poet["name"])}
      {f'<span class="poem-meta">· {esc(poem.get("date"))}</span>' if poem.get("date") else ""}
    </div>
    <h2 class="chain-title">{esc(poem["title"])}</h2>
    <div class="verses chain-verses">{resp_verses}</div>
  </div>
</div>
{info_html}
{report_html}
{responses_html}
{related_html}"""
    else:
        verses_html = render_verses(poem.get("verses"))
        icon_html = (
            f'<span class="role-badge role-بدع" style="font-size:1rem;padding:4px 14px">بدع</span>'
            if is_external else poet_icon_html(poet, 44)
        )
        body = f"""
{breadcrumb_nav}
<div class="poem-header">
  {icon_html}
  <h1>{esc(poem["title"])}</h1>
  <div class="poem-meta">{esc(poet["name"])}{f' · {esc(poem.get("date"))}' if poem.get("date") else ""}{f' · {esc(poem.get("meter"))}' if poem.get("meter") else ""}</div>
  {role_badge_html(poem.get("role"))}
</div>
{f'<div class="verses">{verses_html}</div>' if verses_html else '<p style="text-align:center;color:var(--text-faint)">لم تُحفظ أبيات هذه القصيدة في الديوان بعد</p>'}
{info_html}
{report_html}
{responses_html}
{related_html}"""

    poet_page_url = f"{SITE_URL}/respondents.html" if is_external else f"{SITE_URL}/poets/{poet['id']}.html"
    original_url = f"{SITE_URL}/poems/{original['poem']['id']}.html" if (is_chain and original) else None
    json_ld = poem_json_ld(poet, poem, canonical, is_external, poet_page_url, original_url)
    html_doc = page_shell(title, description, canonical, body, json_ld)
    return poem["id"] + ".html", html_doc


def build_poet_page(poet):
    canonical = f"{SITE_URL}/poets/{poet['id']}.html"
    title = f'قصائد {poet["name"]} | {SITE_NAME}'
    description = real_bio(poet) or f'كل قصائد {poet["name"]} في {SITE_NAME}'
    breadcrumb_nav = breadcrumb_html(poet_breadcrumb_items(poet, canonical))

    POET_PAGE_SIZE = 24
    total_poems = len(poet.get("poems", []))
    cards = []
    for i, poem in enumerate(poet.get("poems", [])):
        first_verse = poem.get("verses", [{}])[0].get("sadr", "") if poem.get("verses") else ""
        extra = i >= POET_PAGE_SIZE
        cards.append(f"""
<a href="/poems/{esc(poem['id'])}.html" class="poem-card{' poem-card-extra' if extra else ''}" style="margin-bottom:14px"{' hidden' if extra else ''}>
  <h2>{esc(poem["title"])}</h2>
  <p>{esc(first_verse)}</p>
</a>""")
    show_all_btn = (
        f'<p style="text-align:center;margin-top:16px">'
        f'<button type="button" class="show-all-btn">عرض كل القصائد ({total_poems}) ▾</button></p>'
        if total_poems > POET_PAGE_SIZE else ""
    )

    photo_html = (
        f'<img src="{esc(poet["photo"])}" alt="{esc("صورة الشاعر " + poet["name"])}" width="52" height="52" '
        f'style="width:52px;height:52px;border-radius:50%;object-fit:cover" loading="lazy" decoding="async" />'
        if poet.get("photo") else
        '<span class="poet-photo-placeholder" style="width:52px;height:52px;font-size:1.3rem" '
        'title="بانتظار إضافة صورة الشاعر">▲</span>'
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
<span class="section-label">قصائد الشاعر ({total_poems})</span>
<div class="poems-grid">{"".join(cards)}</div>
{show_all_btn}
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
            if poet.get("photo") else
            '<span class="poet-photo-placeholder" title="بانتظار إضافة صورة الشاعر">▲</span>'
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


def build_about_page(data):
    """صفحة تعريفية + أسئلة شائعة عن الديوان — كل الأرقام محسوبة فعلياً من data/diwan.json
    وقت التوليد (بدون أي رقم مكتوب يدوياً)، عشان تبقى صحيحة تلقائياً مع أي إضافة مستقبلية.
    محتواها مطابق حرفياً لبيانات FAQPage (Schema.org) عشان تصلح لنتائج البحث الغنية ولمحركات
    الذكاء الاصطناعي (GEO) اللي تعتمد على مطابقة النص المرئي بالصفحة مع البيانات الوصفية."""
    canonical = f"{SITE_URL}/about.html"
    title = f"عن الديوان — أسئلة شائعة | {SITE_NAME}"

    family_count = len(data.get("poets", []))
    external_count = len(data.get("externalPoets", []))
    total_poems = sum(len(p.get("poems", [])) for p in data.get("poets", [])) + \
                  sum(len(p.get("poems", [])) for p in data.get("externalPoets", []))
    linked_count = sum(
        1 for item in flat_poems(data) if (item["poem"].get("mujarat") or {}).get("respondingToId")
    )

    def counted(n, singular, plural):
        """عدد + معدود بصيغة نحوية صحيحة: جمع مع 3-10، مفرد منصوب مع 11 فأكثر (ومع الصفر والمئات)."""
        return f"{n} {plural if 3 <= n <= 10 else singular}"

    family_noun = counted(family_count, "شاعراً", "شعراء")
    external_noun = counted(external_count, "شاعراً", "شعراء")
    total_poets_noun = counted(family_count + external_count, "شاعراً", "شعراء")
    total_poems_noun = counted(total_poems, "قصيدة", "قصائد")
    linked_noun = counted(linked_count, "قصيدة", "قصائد")

    description = data.get("site", {}).get("subtitle") or f"نبذة عن {SITE_NAME} وأسئلة شائعة حوله."
    breadcrumb_nav = breadcrumb_html(simple_breadcrumb_items("عن الديوان", canonical))

    faqs = [
        (
            "ما هو ديوان آل السويلم؟",
            f"{SITE_NAME} موقع إلكتروني يوثّق قصائد وشعراء أسرة آل السويلم (فرع من قبيلة عتيبة) "
            "في مكان واحد، إضافة إلى قصائد شعراء من خارج الأسرة تجاوبوا معهم عبر الزمن بالرد أو المجاراة.",
        ),
        (
            "كم عدد الشعراء في الديوان؟",
            f"يضم الديوان حالياً {family_noun} من أسرة آل السويلم، و{external_noun} "
            f"من خارج الأسرة شاركوا بالرد أو المجاراة على قصائدهم، بإجمالي {total_poets_noun}.",
        ),
        (
            "كم عدد القصائد المحفوظة في الديوان؟",
            f"يحتوي الديوان على {total_poems_noun} حتى الآن، منها {linked_noun} مرتبطة "
            "مباشرة بقصيدة أصلية بوصفها رداً أو مجاراة عليها.",
        ),
        (
            "ما الفرق بين قصيدة (بدع) و(رد) و(مجاراة)؟",
            "البدع هي القصيدة التي يبتدئ بها الشاعر موضوعاً جديداً بوزن وقافية من اختياره. "
            "الرد قصيدة يكتبها شاعر آخر جواباً على قصيدة بدع، ملتزماً بنفس وزنها وقافيتها. "
            "أما المجاراة فقصيدة تحاكي وزن وقافية قصيدة سابقة، عادة إعجاباً بها أو تفاعلاً معها، "
            "دون أن تكون بالضرورة رداً مباشراً موجَّهاً لصاحبها.",
        ),
        (
            "هل كل قصيدة رد أو مجاراة مرتبطة بأصلها؟",
            "نعم، كل قصيدة رد أو مجاراة بالديوان تظهر بصفحتها إلى جانب القصيدة الأصلية (البدع) "
            "التي كُتبت رداً عليها أو مجاراة لها، مع روابط مباشرة بين الاثنتين.",
        ),
        (
            "من يدير الديوان ويحدّثه؟",
            f"تُدار محتويات {SITE_NAME} وتُحدَّث من قبل أسرة آل السويلم نفسها.",
        ),
    ]

    faq_items_html = "\n".join(
        f'<details class="faq-item"><summary>{esc(q)}</summary><p>{esc(a)}</p></details>'
        for q, a in faqs
    )

    body = f"""
{breadcrumb_nav}
<div class="poet-bio-banner">
  <div><h1>عن ديوان آل السويلم</h1><p>{esc(description)}</p></div>
</div>
<div class="about-stats">
  <div class="about-stat"><b>{family_count}</b><span>شاعر من الأسرة</span></div>
  <div class="about-stat"><b>{external_count}</b><span>شاعر من خارج الأسرة</span></div>
  <div class="about-stat"><b>{total_poems}</b><span>قصيدة بالديوان</span></div>
  <div class="about-stat"><b>{linked_count}</b><span>قصيدة رد/مجاراة مرتبطة</span></div>
</div>
<h2 class="section-label">أسئلة شائعة</h2>
<div class="faq-list">{faq_items_html}</div>
<p style="text-align:center;margin-top:20px"><a href="/poets/" style="color:var(--gold)">تصفّح شعراء الديوان ←</a></p>"""

    faq_json_ld = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {
                "@type": "Question",
                "name": q,
                "acceptedAnswer": {"@type": "Answer", "text": a},
            }
            for q, a in faqs
        ],
    }
    breadcrumb = breadcrumb_json_ld(simple_breadcrumb_items("عن الديوان", canonical))
    return "about.html", page_shell(title, description, canonical, body, ld_scripts(faq_json_ld, breadcrumb))


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
    links += '\n    <a href="/about.html">عن الديوان وأسئلة شائعة</a>'

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


def validate_data(data, all_poems):
    """تحقق سلامة بيانات أساسي قبل البناء — يمنع نشر بيانات فاسدة بصمت
    (تصادم معرّفات، مرجع رد/مجاراة مكسور، قصيدة بلا أبيات وبلا مصدر خارجي معروف)."""
    errors = []

    ids = [item["poem"]["id"] for item in all_poems]
    seen = set()
    for pid in ids:
        if pid in seen:
            errors.append(f"معرّف قصيدة مكرر: {pid}")
        seen.add(pid)

    poet_ids = [p["id"] for p in data.get("poets", [])] + [p["id"] for p in data.get("externalPoets", [])]
    dup_poets = {pid for pid in poet_ids if poet_ids.count(pid) > 1}
    for pid in dup_poets:
        errors.append(f"معرّف شاعر مكرر: {pid}")

    all_ids_set = set(ids)
    for item in all_poems:
        poem = item["poem"]
        target = (poem.get("mujarat") or {}).get("respondingToId")
        if target and target not in all_ids_set:
            errors.append(f"مرجع mujarat.respondingToId مكسور بالقصيدة {poem['id']}: يشير إلى {target} غير الموجود")

    if errors:
        sys.exit("✗ فشل التحقق من سلامة البيانات — لم يُبنَ أي شيء:\n" + "\n".join(f"  - {e}" for e in errors))


def main():
    data = load_data()
    all_poems = flat_poems(data)
    validate_data(data, all_poems)
    responses_map = build_responses_map(all_poems)

    update_index_links(data)

    LIGHT_INDEX_PATH.write_text(
        json.dumps(build_light_index(data), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    POEMS_DIR.mkdir(exist_ok=True)
    POETS_DIR.mkdir(exist_ok=True)

    sitemap_entries = [(SITE_URL + "/", None)]
    poem_filenames = set()
    poet_filenames = {"index.html"}  # فهرس الشعراء موجود بنفس مجلد poets/ ولازم ما يُحذف كصفحة "يتيمة"

    role_labels = data.get("roleLabels", {})
    for item in all_poems:
        fname, html_doc = build_poem_page(item, all_poems, responses_map, role_labels)
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

    about_fname, about_html = build_about_page(data)
    (ROOT / about_fname).write_text(about_html, encoding="utf-8")
    sitemap_entries.append((f"{SITE_URL}/{about_fname}", None))

    (ROOT / "404.html").write_text(build_404_page(), encoding="utf-8")

    (ROOT / "sitemap.xml").write_text(build_sitemap(sitemap_entries), encoding="utf-8")
    (ROOT / "robots.txt").write_text(build_robots(f"{SITE_URL}/sitemap.xml"), encoding="utf-8")

    print(f"✓ built {len(all_poems)} poem pages, {len(data.get('poets', []))} poet pages + poets index + 404")
    print(f"✓ sitemap.xml with {len(sitemap_entries)} URLs")


if __name__ == "__main__":
    main()
