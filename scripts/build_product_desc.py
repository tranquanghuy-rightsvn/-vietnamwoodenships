#!/usr/bin/env python3
"""Insert the long product introductions into every product page.

    content/products/<vi-slug>.vi.html -> html/sp/<vi-slug>/index.html
    content/products/<vi-slug>.en.html -> html/product/<en-slug>/index.html

Each source file starts with

    <!--meta
    {"description": "...meta description...", "sources": ["https://...", ...]}
    -->

followed by the text (p, h3, ul, a). The text goes into a full-width
<section class="product-about"> right after the gallery / buy box, between
<!-- about:start --> and <!-- about:end --> (idempotent). The meta description
is stored on the section (data-meta) and picked up by scripts/seo.py.
Run scripts/seo.py afterwards.
"""
import html as H
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "html"
SRC = ROOT / "content" / "products"
START, END = "<!-- about:start -->", "<!-- about:end -->"
HEADING = {"vi": "Giới thiệu sản phẩm", "en": "About this product"}


def en_slugs():
    js = (SITE / "assets" / "js" / "catalog.js").read_text(encoding="utf-8")
    data = json.loads(js[js.index("{"): js.rindex("}") + 1])
    return {k: v["slug"] for k, v in data.items()}


def end_of_div(src, start):
    """Index just after the </div> closing the <div> that opens at `start`."""
    depth, i = 0, start
    for m in re.finditer(r"<div\b|</div>", src[start:]):
        depth += 1 if m.group(0) == "<div" else -1
        if depth == 0:
            return start + m.end()
    raise ValueError("unbalanced divs")


def inject(page, body, meta, lang):
    src = page.read_text(encoding="utf-8")
    src = re.sub(r"\n?[ \t]*" + re.escape(START) + r".*?" + re.escape(END), "", src, flags=re.S)
    i = src.index('<div class="row product-detail">')
    j = end_of_div(src, i)
    block = (f'\n    {START}\n'
             f'    <section class="product-about" data-meta="{H.escape(meta, quote=True)}" aria-labelledby="about-title">\n'
             f'      <h2 class="section-title" id="about-title">{HEADING[lang]}</h2>\n'
             f'      <div class="product-about-body">\n{body}\n      </div>\n'
             f'    </section>\n    {END}')
    page.write_text(src[:j] + block + src[j:], encoding="utf-8")


def main():
    en = en_slugs()
    n = 0
    for f in sorted(SRC.glob("*.html")):
        m = re.match(r"(.+)\.(vi|en)\.html$", f.name)
        if not m:
            continue
        slug, lang = m.groups()
        raw = f.read_text(encoding="utf-8")
        hm = re.match(r"\s*<!--meta\s*(\{.*?\})\s*-->", raw, re.S)
        meta = json.loads(hm.group(1)) if hm else {}
        body = raw[hm.end():].strip() if hm else raw.strip()
        page = SITE / ("sp/" + slug if lang == "vi" else "product/" + en[slug]) / "index.html"
        inject(page, body, meta.get("description", ""), lang)
        words = len(re.sub(r"<[^>]+>", " ", body).split())
        print(f"{lang} {page.parent.name:42} {words:4} words")
        n += 1
    print(n, "pages updated")


if __name__ == "__main__":
    main()
