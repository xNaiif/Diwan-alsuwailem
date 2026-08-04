#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
مولّد صفحات ثابتة لديوان آل السويلم — يقرأ data/diwan.json ويبني:
  - صفحة HTML كاملة لكل قصيدة تحت /poems/
  - صفحة HTML لكل شاعر تحت /poets/
  - sitemap.xml
  - robots.txt
يشتغل تلقائياً عبر GitHub Actions عند أي دفعة (push) — لا يحتاج أي شي يدوي.
"""

import json
import html
import os
from pathlib import Path

SITE_URL = "https://diwan-alswilem.com"
DEFAULT_OG_IMAGE = f"{SITE_URL}/assets/og-image.jpg"
ROOT = Path(__file__).resolve().parent.parent  # جذر المستودع
DATA_PATH = ROOT / "data" / "diwan.json"
POEMS_DIR = ROOT / "poems"
POETS_DIR = ROOT / "poets"


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


def page_shell(title, description, canonical_url, body_html, json_ld="", og_image=None):
    """القالب الأساسي المشترك لأي صفحة ثابتة، يعيد استخدام نفس css/style.css."""
    image = og_image or DEFAULT_OG_IMAGE
    return f"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}" />
<link rel="canonical" href="{esc(canonical_url)}" />

<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml" />
<link rel="icon" href="/assets/favicon-32.png" sizes="32x32" type="image/png" />
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png" />
<meta name="theme-color" content="#15110d" />

<meta property="og:type" content="article" />
<meta property="og:site_name" content="ديوان آل السويلم" />
<meta property="og:title" content="{esc(title)}" />
<meta property="og:description" content="{esc(description)}" />
<meta property="og:url" content="{esc(canonical_url)}" />
<meta property="og:image" content="{esc(image)}" />
<meta property="og:image:width" content="1200" />
<meta property="og:image:height" content="630" />
<meta property="og:locale" content="ar_SA" />

<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{esc(title)}" />
<meta name="twitter:description" content="{esc(description)}" />
<meta name="twitter:image" content="{esc(image)}" />

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
      <p class="hero-title" style="font-size:clamp(1.8rem,6vw,2.6rem);margin:0">آل السويلم</p>
    </a>
  </div>
</header>
<main id="main-view">
{body_html}
</main>
<footer class="site-footer">
  <p>ديوان آل السويلم — © {esc(str(__import__("datetime").date.today().year))}
    <span class="footer-note">هذه صفحة ثابتة لتسهيل الوصول والفهرسة — <a href="/" style="color:var(--gold)">تصفّح الديوان كامل من هنا</a></span>
  </p>
</footer>
</body>
</html>"""


def poem_json_ld(poet, poem, canonical_url):
    verses_text = " / ".join(
        f'{v.get("sadr","")} … {v.get("ajz","")}' for v in (poem.get("verses") or [])
    )
    data = {
        "@context": "https://schema.org",
        "@type": "CreativeWork",
        "name": poem.get("title"),
        "author": {"@type": "Person", "name": poet.get("name")},
        "inLanguage": "ar",
        "genre": "شعر نبطي",
        "url": canonical_url,
    }
    if poem.get("date"):
        data["dateCreated"] = poem["date"]
    if verses_text:
        data["text"] = verses_text[:2000]
    return f'<script type="application/ld+json">{json.dumps(data, ensure_ascii=False)}</script>'


def build_poem_page(item, all_poems, responses_map):
    poet, poem, is_external = item["poet"], item["poem"], item["isExternal"]
    canonical = f"{SITE_URL}/poems/{poem['id']}.html"
    description = poem.get("verses", [{}])[0].get("sadr", poem["title"]) if poem.get("verses") else poem["title"]
    title = f'{poem["title"]} — {poet["name"]} | ديوان آل السويلم'

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
{responses_html}
<p style="text-align:center;margin-top:28px">
  <a href="/poets/{esc(poet['id'])}.html" style="color:var(--gold)">قصائد أخرى لـ{esc(poet['name'])} ←</a>
</p>"""
    else:
        verses_html = render_verses(poem.get("verses"))
        body = f"""
<div class="poem-header">
  <h1>{esc(poem["title"])}</h1>
  <div class="poem-meta">{esc(poet["name"])}{f' · {esc(poem.get("date"))}' if poem.get("date") else ""}{f' · {esc(poem.get("meter"))}' if poem.get("meter") else ""}</div>
</div>
{f'<div class="verses">{verses_html}</div>' if verses_html else '<p style="text-align:center;color:var(--text-faint)">لم تُحفظ أبيات هذه القصيدة في الديوان بعد</p>'}
{responses_html}
<p style="text-align:center;margin-top:28px">
  <a href="/poets/{esc(poet['id'])}.html" style="color:var(--gold)">قصائد أخرى لـ{esc(poet['name'])} ←</a>
</p>"""

    html_doc = page_shell(title, description, canonical, body, poem_json_ld(poet, poem, canonical))
    return poem["id"] + ".html", html_doc


def build_poet_page(poet):
    canonical = f"{SITE_URL}/poets/{poet['id']}.html"
    title = f'قصائد {poet["name"]} | ديوان آل السويلم'
    description = poet.get("bio") or f'كل قصائد {poet["name"]} في ديوان آل السويلم'

    cards = []
    for poem in poet.get("poems", []):
        first_verse = poem.get("verses", [{}])[0].get("sadr", "") if poem.get("verses") else ""
        cards.append(f"""
<a href="/poems/{esc(poem['id'])}.html" class="poem-card" style="display:block;text-decoration:none;margin-bottom:14px">
  <div data-nosnippet>
    <h3>{esc(poem["title"])}</h3>
    <p>{esc(first_verse)}</p>
  </div>
</a>""")

    body = f"""
<div class="poet-bio-banner">
  <div><h1>{esc(poet["name"])}</h1><p>{esc(poet.get("bio", ""))}</p></div>
</div>
<div class="poems-grid">{"".join(cards)}</div>
<p style="text-align:center;margin-top:20px"><a href="/" style="color:var(--gold)">تصفّح كل شعراء الديوان ←</a></p>"""

    return poet["id"] + ".html", page_shell(title, description, canonical, body)


def build_sitemap(urls):
    entries = "\n".join(f"  <url><loc>{esc(u)}</loc></url>" for u in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{entries}\n</urlset>\n'


def build_robots(sitemap_url):
    return f"User-agent: *\nAllow: /\n\nSitemap: {sitemap_url}\n"


def validate_diwan(all_poems):
    """يتأكد أن كل معرّف قصيدة فريد قبل البناء. لو تكرر معرّف بين قصيدتين، فإن
    build_poem_page لهما بيكتب على نفس اسم الملف — يعني وحدة راح تطمس الثانية
    بصمت (بدون أي خطأ ظاهر)، وهذا بالضبط اللي صار مع poet-1-poem-31 سابقاً.
    نوقف البناء فوراً هنا بدل ما ننشر موقع فيه قصيدة ضايعة."""
    seen = {}
    dup_errors = []
    for item in all_poems:
        pid = item["poem"]["id"]
        title = item["poem"].get("title", "?")
        owner = item["poet"].get("name", "?")
        if pid in seen:
            dup_errors.append(f'  - المعرّف "{pid}" مستخدم لقصيدتين: "{seen[pid]}" و"{title}" ({owner})')
        else:
            seen[pid] = title

    if dup_errors:
        print("✗ توجد معرّفات قصائد مكرّرة في data/diwan.json — صحّحها قبل البناء:")
        print("\n".join(dup_errors))
        raise SystemExit(1)

    all_ids = set(seen.keys())
    dangling = []
    for item in all_poems:
        mj = item["poem"].get("mujarat") or {}
        target = mj.get("respondingToId")
        if target and target not in all_ids:
            dangling.append(
                f'  - "{item["poem"].get("title","?")}" ({item["poet"].get("name","?")}) '
                f"يشير لمعرّف غير موجود: {target}"
            )
    if dangling:
        print("⚠ تنبيه: روابط رد/مجاراة تشير لمعرّفات غير موجودة (البناء يكمل، لكن راجعها):")
        print("\n".join(dangling))


def main():
    data = load_data()
    all_poems = flat_poems(data)
    validate_diwan(all_poems)
    responses_map = build_responses_map(all_poems)

    POEMS_DIR.mkdir(exist_ok=True)
    POETS_DIR.mkdir(exist_ok=True)

    urls = [SITE_URL + "/"]

    for item in all_poems:
        fname, html_doc = build_poem_page(item, all_poems, responses_map)
        (POEMS_DIR / fname).write_text(html_doc, encoding="utf-8")
        urls.append(f"{SITE_URL}/poems/{fname}")

    for poet in data.get("poets", []):
        fname, html_doc = build_poet_page(poet)
        (POETS_DIR / fname).write_text(html_doc, encoding="utf-8")
        urls.append(f"{SITE_URL}/poets/{fname}")

    (ROOT / "sitemap.xml").write_text(build_sitemap(urls), encoding="utf-8")
    (ROOT / "robots.txt").write_text(build_robots(f"{SITE_URL}/sitemap.xml"), encoding="utf-8")

    print(f"✓ built {len(all_poems)} poem pages, {len(data.get('poets', []))} poet pages")
    print(f"✓ sitemap.xml with {len(urls)} URLs")


if __name__ == "__main__":
    main()
