#!/usr/bin/env python3
"""Build the localised site from content/*.json + templates/.

    python3 tools/build-pages.py

English is published at the site root so existing URLs keep working; every other
language lands in a subfolder:

    site/index.html          site/de/index.html       site/es/index.html
    site/references.html     site/de/references.html  site/es/references.html
    site/contact.html        site/de/contact.html     site/es/contact.html

Output is committed, the same way tools/build-logo-assets.py works — there is no
build step in the deploy workflow, which only uploads ./site.
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT = os.path.join(ROOT, "content")
TEMPLATES = os.path.join(ROOT, "templates")
OUT = os.path.join(ROOT, "site")

SITE_URL = "https://axomislabs.com"
DEFAULT_LANG = "en"                       # published at the root
LANGS = ["en", "de", "es"]                # order shown in the switcher
PAGES = ["index", "references", "contact"]
OG_LOCALE = {"en": "en_GB", "de": "de_DE", "es": "es_ES"}


def load(name):
    with open(os.path.join(TEMPLATES, name), encoding="utf-8") as f:
        return f.read()


def fill(template, values):
    """Replace {{key}} with values[key]. Unknown keys are left in place so a
    missing translation shows up loudly rather than silently emptying a page."""
    def sub(m):
        key = m.group(1)
        return str(values[key]) if key in values else m.group(0)
    return re.sub(r"\{\{(\w+)\}\}", sub, template)


def indent(html, spaces):
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in html.split("\n"))


# ── Repeated blocks ────────────────────────────────────────────────────────
# Built here rather than in the templates: a {{key}} substitution can't loop.

def cards(items):
    out = []
    for i, c in enumerate(items, 1):
        out.append(
            f'<li class="card reveal">\n'
            f'  <span class="card-num">{i:02d}</span>\n'
            f'  <h3>{c["title"]}</h3>\n'
            f'  <p>\n    {c["body"]}\n  </p>\n'
            f'</li>')
    return indent("\n".join(out), 8)


def steps(items):
    out = [f'<li><span>{s["title"]}</span><p>{s["body"]}</p></li>' for s in items]
    return indent("\n".join(out), 8)


def values(items):
    out = [f'<li class="reveal"><h3>{v["title"]}</h3><p>{v["body"]}</p></li>' for v in items]
    return indent("\n".join(out), 8)


def prose(paragraphs):
    out = [f"<p>\n  {p}\n</p>" for p in paragraphs]
    return indent("\n".join(out), 8)


def tiles(items):
    out = []
    for t in items:
        out.append(
            f'<li class="reveal">\n'
            f'  <h3>{t["title"]}</h3>\n'
            f'  <p>\n    {t["body"]}\n  </p>\n'
            f'</li>')
    return indent("\n".join(out), 8)


def products(items):
    out = []
    for p in items:
        cls = "reveal tile-soft" if p.get("soft") else "reveal"
        meta = f'\n  <p class="meta">{p["meta"]}</p>' if p.get("meta") else ""
        link = ""
        if p.get("link"):
            link = (f'\n  <p class="ref-link"><a href="{p["link"]}" target="_blank" '
                    f'rel="noopener">{p["link_label"]}</a></p>')
        out.append(
            f'<li class="{cls}">\n'
            f'  <div class="ref-head">\n'
            f'    <h3>{p["title"]}</h3>\n'
            f'    <span class="{p["status_class"]}">{p["status"]}</span>\n'
            f'  </div>{meta}\n'
            f'  <p>\n    {p["body"]}\n  </p>{link}\n'
            f'</li>')
    return indent("\n".join(out), 8)


# ── Per-language link helpers ──────────────────────────────────────────────

def base_for(lang):
    """Prefix for links between pages of the same language."""
    return "" if lang == DEFAULT_LANG else ""


def root_for(lang):
    """Prefix back to site/ for shared assets."""
    return "" if lang == DEFAULT_LANG else "../"


def url_for(lang, page):
    slug = "" if page == "index" else page + ".html"
    if lang == DEFAULT_LANG:
        return f"{SITE_URL}/{slug}" if slug else f"{SITE_URL}/"
    return f"{SITE_URL}/{lang}/{slug}" if slug else f"{SITE_URL}/{lang}/"


def href_between(from_lang, to_lang, page):
    """Relative href from a page in from_lang to the same page in to_lang."""
    up = "" if from_lang == DEFAULT_LANG else "../"
    target = "" if to_lang == DEFAULT_LANG else to_lang + "/"
    return f"{up}{target}{page}.html"


def hreflang_block(page):
    lines = [f'<link rel="alternate" hreflang="{l}" href="{url_for(l, page)}">' for l in LANGS]
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{url_for(DEFAULT_LANG, page)}">')
    return "\n".join(lines)


def lang_links(current, page, all_content):
    out = []
    for l in LANGS:
        c = all_content[l]
        mark = ' aria-current="true"' if l == current else ""
        out.append(f'            <li><a href="{href_between(current, l, page)}" '
                   f'hreflang="{l}" lang="{l}"{mark}>{c["label"]}</a></li>')
    return "\n".join(out)


# ── Build ──────────────────────────────────────────────────────────────────

def main():
    missing = [l for l in LANGS if not os.path.exists(os.path.join(CONTENT, l + ".json"))]
    if missing:
        sys.exit("missing content files: " + ", ".join(missing))

    all_content = {}
    for l in LANGS:
        with open(os.path.join(CONTENT, l + ".json"), encoding="utf-8") as f:
            all_content[l] = json.load(f)

    base_tpl = load("base.html")
    contact_partial = load("_contact.html")
    body_tpl = {p: load(p + ".html") for p in PAGES}

    written = []
    for lang in LANGS:
        c = all_content[lang]
        ui, nav, contact = c["ui"], c["nav"], c["contact"]
        outdir = OUT if lang == DEFAULT_LANG else os.path.join(OUT, lang)
        os.makedirs(outdir, exist_ok=True)

        shared = {
            "lang": c["lang"],
            "lang_code": c["code"],
            "base": base_for(lang),
            "root": root_for(lang),
            "og_locale": OG_LOCALE.get(lang, "en_GB"),
            "contact_eyebrow": contact["eyebrow"],
            "contact_heading": contact["heading"],
            "contact_lead": contact["lead"],
            "contact_email": contact["email"],
        }
        shared.update({"ui_" + k: v for k, v in ui.items()})
        shared.update({"nav_" + k: v for k, v in nav.items()})

        contact_section = fill(contact_partial, shared)

        for page in PAGES:
            src = c["contact_page"] if page == "contact" else c[page]
            v = dict(shared)
            v.update({
                "title": src["title"],
                "description": src["description"],
                "og_title": src["og_title"],
                "og_description": src["og_description"],
                "canonical": url_for(lang, page),
                "hreflang": hreflang_block(page),
                "lang_links": lang_links(lang, page, all_content),
                "contact_section": contact_section,
                "self_href": page + ".html",
            })

            if page == "index":
                v.update({
                    "hero_eyebrow": src["hero_eyebrow"],
                    "hero_h1": src["hero_h1"],
                    "hero_lead": src["hero_lead"],
                    "hero_cta_primary": src["hero_cta_primary"],
                    "hero_cta_secondary": src["hero_cta_secondary"],
                    "work_eyebrow": src["work_eyebrow"],
                    "work_h2": src["work_h2"],
                    "work_intro": src["work_intro"],
                    "work_cards": cards(src["work_cards"]),
                    "philosophy_eyebrow": src["philosophy_eyebrow"],
                    "philosophy_pull": src["philosophy_pull"],
                    "philosophy_steps": steps(src["philosophy_steps"]),
                    "philosophy_closing": src["philosophy_closing"],
                    "values_eyebrow": src["values_eyebrow"],
                    "values_h2": src["values_h2"],
                    "values": values(src["values"]),
                })
            elif page == "references":
                v.update({
                    "experience_eyebrow": src["experience_eyebrow"],
                    "experience_h1": src["experience_h1"],
                    "experience_prose": prose(src["experience_prose"]),
                    "experience_tiles": tiles(src["experience_tiles"]),
                    "experience_note": src["experience_note"],
                    "products_eyebrow": src["products_eyebrow"],
                    "products_h2": src["products_h2"],
                    "products_intro": src["products_intro"],
                    "products": products(src["products"]),
                    "consulting_eyebrow": src["consulting_eyebrow"],
                    "consulting_h2": src["consulting_h2"],
                    "consulting_intro": src["consulting_intro"],
                    "consulting_tiles": tiles(src["consulting_tiles"]),
                    "consulting_note": src["consulting_note"],
                })

            html = fill(base_tpl, dict(v, main=fill(body_tpl[page], v)))

            leftover = set(re.findall(r"\{\{(\w+)\}\}", html))
            if leftover:
                sys.exit(f"unresolved placeholders in {lang}/{page}: {sorted(leftover)}")

            path = os.path.join(outdir, page + ".html")
            with open(path, "w", encoding="utf-8") as f:
                f.write(html)
            written.append(os.path.relpath(path, ROOT))

    # ── Sitemap ────────────────────────────────────────────────────────────
    urls = []
    for lang in LANGS:
        for page in PAGES:
            pri = "1.0" if (lang == DEFAULT_LANG and page == "index") else "0.8"
            urls.append(f"  <url>\n    <loc>{url_for(lang, page)}</loc>\n"
                        f"    <changefreq>monthly</changefreq>\n"
                        f"    <priority>{pri}</priority>\n  </url>")
    sitemap = ('<?xml version="1.0" encoding="UTF-8"?>\n'
               '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
               + "\n".join(urls) + "\n</urlset>\n")
    with open(os.path.join(OUT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(sitemap)
    written.append("site/sitemap.xml")

    for p in written:
        print("  " + p)
    print(f"\n{len(written)} files written")


if __name__ == "__main__":
    main()
