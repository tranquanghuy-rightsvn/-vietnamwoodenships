#!/usr/bin/env python3
"""Render the site from data/ (written by the CMS) — see GAS.md.

    python3 scripts/build.py

Python stdlib only; runs locally and in GitHub Actions (.github/workflows/build.yml).
Idempotent: running it twice in a row changes nothing.

  data/products.json + data/products/<slug>.json
      -> html/sp/<slug>/              (Vietnamese product page)
      -> html/product/<slugEn>/       (English product page, only when nameEn is set)
      -> product grids on /, /home/, /san-pham/, /products/, /danh-muc/*/, /category/*/
      -> html/assets/data/products(-en).json (search) + html/assets/js/catalog.js (cart EN names)
  data/news.json + data/news/<slug>.json (+ data/news-images.json, photo credits)
      -> html/tin-tuc/<slug>/, html/news/<slugEn>/ (when titleEn is set)
      -> article cards on /tin-tuc/ and /news/, "Bài viết mới" on /404.html
  data/settings.json (CMS "Cài đặt chung": logo, favicon, hero slider, phone, email, address,
        map, footer text) -> header/footer of every page, home slider, contact/about pages
  then: delete pages of products/articles that no longer exist or are hidden,
        and run scripts/seo.py (meta, canonical, hreflang, JSON-LD, sitemap, robots).

Page shells come from templates/*.html (edit those to change the design). Listing pages are
hand-made pages; only the regions between <!-- build:NAME --> and <!-- /build:NAME --> are
rewritten.
"""
import html as H
import json
import unicodedata
import re
import shutil
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "html"
DATA = ROOT / "data"
TPL = ROOT / "templates"
BRAND = "Vietnam Wooden Ships"

# (vi slug, vi name, en slug, en name) — fixed list, must match CATEGORIES in gas/Code.js (GAS.md II.2)
CATEGORIES = [
    ("tau-du-lich-du-thuyen", "Tàu Du Lịch – Du Thuyền", "cruise-ships-yachts", "Cruise Ships – Yachts"),
    ("tau-cho-hang", "Tàu Chở Hàng", "cargo-ships", "Cargo Ships"),
    ("thuyen-buom", "Thuyền Buồm", "sailing-boats", "Sailing Boats"),
    ("thuyen-dung-di-dao", "Thuyền (Dùng đi dạo)", "leisure-boats", "Boats (For Leisure)"),
    ("du-thuyen-hien-dai", "Du Thuyền Hiện Đại", "modern-yachts", "Modern Yachts"),
    ("noi-that", "Nội Thất", "furniture", "Furniture"),
    ("san-pham-khac", "Sản Phẩm Khác", "other-products", "Other Products"),
]
CAT = {c[0]: c for c in CATEGORIES}

# Home page: 6 hand-picked sections (order chosen in the original shop). Products added
# through the CMS later appear first in the section of their category; removed/hidden
# products drop out. 8 cards max per section.
HOME_LIMIT = 8
HOME_SECTIONS = [
    (("tau-du-lich-du-thuyen", "du-thuyen-hien-dai"),
     ["mo-hinh-thuen", "mo-hinh-tau-thuyen", "mo-hinh-tau-asuka-ll", "mo-hinh-tau-mississippi",
      "lagoon-450-yacht-model", "laustrl-mo-hinh-tau", "mo-hinh-tau-erzherzog-franz-ferdinand", "mo-hinh-tau-astor"]),
    (("tau-cho-hang",), ["batterses-mo-hinh-thuyen", "star-1-mo-hinh-thuyen", "anteo", "american-sconut"]),
    (("thuyen-buom",),
     ["mo-hinh-thuyen-buom-2", "mo-hinh-thuyen-buom", "victory", "model-ships-thorsen-axel-1810-na-uy",
      "thuyen-my-nghe", "christian-radich-model", "mo-hinh-thuyen-batavia", "mo-hinh-thuyen"]),
    (("thuyen-dung-di-dao",), ["xuong-go", "mo-hinh-thuyen-buom"]),
    (("noi-that",), ["ban-hoc-sinh", "noi-that-go-tram", "tu-go", "quay-ba", "ban-hinh-thuyen", "ban-go"]),
    (("san-pham-khac",), ["cannon", "tranh-thuyen-2", "tranh-thuyen", "ky-niem-chuong"]),
]
# every product that existed when the CMS took over; anything else counts as "new" on the home page
HOME_KNOWN = {s for _, lst in HOME_SECTIONS for s in lst} | {"silver-dee"}

NEWS_TAG_EN = {"Kiến thức": "Knowledge", "Sản phẩm": "Products", "Hướng dẫn": "Guides"}

L = {
    "vi": dict(home="/", home_label="Trang chủ", cat_base="/danh-muc/", prod_base="/sp/",
               code="Mã sản phẩm", size="Kích thước", price="Giá", contact="Liên hệ",
               thumbs="Ảnh sản phẩm", desc="Mô tả", about="Giới thiệu sản phẩm",
               related="Sản phẩm tương tự", add="Thêm {} vào giỏ hàng", view_all="Xem tất cả ({})",
               count="{} sản phẩm", empty="Chưa có sản phẩm nào trong danh mục này.",
               news="Tin tức", news_base="/tin-tuc/", toc="Mục lục bài viết", toc_label="Mục lục",
               minutes="{} phút đọc", rel_news="Bài viết liên quan", more="Đọc tiếp", read="Đọc bài: {}",
               photo="Ảnh"),
    "en": dict(home="/home/", home_label="Home", cat_base="/category/", prod_base="/product/",
               code="Product code", size="Size", price="Price", contact="Contact us",
               thumbs="Product images", desc="Description", about="About this product",
               related="Related products", add="Add {} to cart", view_all="View all ({})",
               count="{} products", empty="No products in this category yet.",
               news="News", news_base="/news/", toc="Table of contents", toc_label="Table of contents",
               minutes="{} min read", rel_news="Related articles", more="Read more", read="Read: {}",
               photo="Photo"),
}

TAG = re.compile(r"<[^>]+>")


def e(s):
    return H.escape(s or "", quote=True)


def text(s):
    return re.sub(r"\s+", " ", H.unescape(TAG.sub(" ", s or ""))).strip()


def read(p):
    return Path(p).read_text(encoding="utf-8")


def write(p, s):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    if not p.exists() or p.read_text(encoding="utf-8") != s:
        p.write_text(s, encoding="utf-8")


def load(p):
    return json.loads(read(p))


def fill(tpl, **kw):
    for k, v in kw.items():
        tpl = tpl.replace("{{" + k + "}}", v)
    left = re.findall(r"\{\{[A-Z_]+\}\}", tpl)
    if left:
        raise SystemExit(f"template placeholder(s) not filled: {sorted(set(left))}")
    return tpl


def patch(path, name, content, required=True):
    """Replace the region between <!-- build:name --> and <!-- /build:name --> in a page."""
    p = SITE / path
    s = read(p)
    a, b = f"<!-- build:{name} -->", f"<!-- /build:{name} -->"
    if a not in s:
        if required:
            raise SystemExit(f"{path}: marker {a} not found — restore it (see templates/README in build.py)")
        print(f"warning: {path}: marker {a} not found, skipped")
        return
    i, j = s.index(a) + len(a), s.index(b)
    write(p, s[:i] + content + s[j:])


# ------------------------------------------------------------------ image size (no deps)
_sizes = {}


def img_size(src):
    """(width, height) of a site image, read from the file header. None if unknown."""
    if src in _sizes:
        return _sizes[src]
    wh = None
    p = SITE / src.lstrip("/").split("?")[0]
    try:
        with open(p, "rb") as f:
            head = f.read(32)
            if head[:6] in (b"GIF87a", b"GIF89a"):
                wh = struct.unpack("<HH", head[6:10])
            elif head[:8] == b"\x89PNG\r\n\x1a\n":
                wh = struct.unpack(">II", head[16:24])
            elif head[:4] == b"RIFF" and head[8:12] == b"WEBP":
                f.seek(12)
                chunk = f.read(30)
                kind = chunk[:4]
                if kind == b"VP8X":
                    w = int.from_bytes(chunk[12:15], "little") + 1
                    h = int.from_bytes(chunk[15:18], "little") + 1
                    wh = (w, h)
                elif kind == b"VP8 ":
                    w, h = struct.unpack("<HH", chunk[18:22])
                    wh = (w & 0x3FFF, h & 0x3FFF)
                elif kind == b"VP8L":
                    b = chunk[9:13]
                    w = 1 + (((b[1] & 0x3F) << 8) | b[0])
                    h = 1 + (((b[3] & 0xF) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
                    wh = (w, h)
            elif head[:2] == b"\xff\xd8":
                f.seek(2)
                while True:
                    marker = f.read(2)
                    if len(marker) < 2 or marker[0] != 0xFF:
                        break
                    if marker[1] in (0xD8, 0x01) or 0xD0 <= marker[1] <= 0xD7:
                        continue
                    seg = struct.unpack(">H", f.read(2))[0]
                    if marker[1] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                        f.read(1)
                        h, w = struct.unpack(">HH", f.read(4))
                        wh = (w, h)
                        break
                    f.seek(seg - 2, 1)
    except (OSError, struct.error):
        wh = None
    _sizes[src] = tuple(wh) if wh else None
    return _sizes[src]


# ------------------------------------------------------------------ products
def price_text(p, lang):
    return f"{p['price']:,} (vnd)" if isinstance(p.get("price"), int) else L[lang]["contact"]


def prod_url(p, lang):
    return f"/sp/{p['slug']}/" if lang == "vi" else f"/product/{p['slugEn']}/"


def prod_name(p, lang):
    return p["nameVi"] if lang == "vi" else p["nameEn"]


def cat_url(cat, lang):
    c = CAT[cat]
    return f"/danh-muc/{c[0]}/" if lang == "vi" else f"/category/{c[2]}/"


def cat_name(cat, lang):
    c = CAT[cat]
    return c[1] if lang == "vi" else c[3]


def card(p, lang):
    url, name = prod_url(p, lang), prod_name(p, lang)
    back = (f'\n        <img class="img-back" src="{e(p["image2"])}" alt="" loading="lazy" decoding="async">'
            if p.get("image2") else "")
    price = str(p["price"]) if isinstance(p.get("price"), int) else ""
    return f'''<div class="col">
  <article class="product-card">
    <div class="product-media">
      <a href="{url}" aria-label="{e(name)}">
        <img src="{e(p["image"])}" alt="{e(name)}" loading="lazy" decoding="async">{back}
      </a>
      <div class="product-tools">
        <button class="cart-icon" type="button" data-card-add data-slug="{e(p["slug"])}" data-name="{e(name)}"
                data-img="{e(p["image"])}" data-price-text="{e(price_text(p, lang))}" data-price="{price}"
                aria-label="{e(L[lang]["add"].format(name))}"><strong>+</strong></button>
      </div>
    </div>
    <div class="product-body">
      <p class="product-name"><a href="{url}">{e(name)}</a></p>
    </div>
  </article>
</div>'''


def cards(items, lang):
    return "".join(card(p, lang) for p in items)


def first_sentence(html_text, limit=160):
    t = text(html_text)
    if len(t) <= limit:
        return t
    cut = t[:limit]
    dot = cut.rfind(". ")
    return cut[:dot + 1] if dot > 60 else cut.rsplit(" ", 1)[0] + "…"


def product_page(p, lang, tpl, related):
    T = L[lang]
    name = prod_name(p, lang)
    images = p.get("images") or ([p["image"]] if p.get("image") else [])
    main_img = images[0] if images else p.get("image", "")
    thumbs = "".join(
        f'<button type="button" role="tab" aria-selected="{"true" if i == 0 else "false"}" data-full="{e(src)}" '
        f'data-alt="{e(name)}"><img src="{e(src)}" alt="" loading="lazy"></button>'
        for i, src in enumerate(images))
    gallery = (f'<div class="gallery-main"><img src="{e(main_img)}" alt="{e(name)}"></div>\n'
               f'        <div class="gallery-thumbs" role="tablist" aria-label="{T["thumbs"]}">{thumbs}</div>')
    specs = []
    if p.get("sku"):
        specs.append((T["code"], p["sku"]))
    if p.get("size"):
        specs.append((T["size"], p["size"]))
    specs.append((T["price"], price_text(p, lang)))
    spec_html = '<dl class="spec-list">' + "".join(f"<div><dt>{a}</dt><dd>{e(b)}</dd></div>" for a, b in specs) + "</dl>"

    note = p.get("priceNoteVi" if lang == "vi" else "priceNoteEn") or ""
    lines = [l.strip() for l in note.splitlines() if l.strip()]
    desc = (f'<div class="product-desc"><h2 class="section-title" style="display:inline-block">{T["desc"]}</h2>'
            f'<div style="margin-top:16px">' + "".join(f"<p>{e(l)}</p>" for l in lines) + "</div></div>") if lines else ""

    intro = drop_empty_paragraphs(p.get("introVi" if lang == "vi" else "introEn") or "")
    if not has_text(intro) and "<img" not in intro:
        intro = ""   # only blank lines: no "Giới thiệu sản phẩm" section at all (an image alone still shows)
    if intro:
        intro = fix_images(intro, {}, lang)
    meta = (p.get("metaVi" if lang == "vi" else "metaEn") or "").strip() or (first_sentence(intro) if intro else "")
    if not meta:
        meta = f"{name} — {cat_name(p['cat'], lang)}." + (f" {p['size']}." if p.get("size") else "")
    about = ""
    if intro:
        about = (f'<!-- about:start -->\n'
                 f'    <section class="product-about" data-meta="{e(meta)}" aria-labelledby="about-title">\n'
                 f'      <h2 class="section-title" id="about-title">{T["about"]}</h2>\n'
                 f'      <div class="product-about-body">\n{intro}\n      </div>\n'
                 f'    </section>\n    <!-- about:end -->')
    rel = ""
    if related:
        rel = (f'<section class="row row-small" style="margin-top:30px">\n  <div class="col">\n'
               f'    <div class="section-head"><h2 class="section-title">{T["related"]}</h2></div>\n  </div>\n'
               f'  <div class="col"><div class="row row-small grid-products">{cards(related, lang)}</div></div>\n</section>')

    has_en = bool(p.get("nameEn") and p.get("slugEn"))
    url_vi = prod_url(p, "vi")
    url_en = prod_url(p, "en") if has_en else "/products/"
    head = [f'<meta name="description" content="{e(meta)}">',
            f'<link rel="alternate" hreflang="vi" href="{url_vi}">']
    if has_en:
        head.append(f'<link rel="alternate" hreflang="en" href="{url_en}">')
    price = str(p["price"]) if isinstance(p.get("price"), int) else ""
    return fill(tpl, TITLE=e(f"{name} - {BRAND}"), HEAD="\n".join(head), URL_VI=url_vi, URL_EN=url_en,
                HOME_URL=T["home"], HOME_LABEL=T["home_label"], CAT_URL=cat_url(p["cat"], lang),
                CAT_NAME=e(cat_name(p["cat"], lang)), NAME=e(name), NAME_ATTR=e(name), GALLERY=gallery,
                SPECS=spec_html, CART_SLUG=e(p["slug"]), IMAGE=e(main_img or p.get("image", "")),
                PRICE_TEXT_ATTR=e(price_text(p, lang)), PRICE=price, DESC=desc, ABOUT=about, RELATED=rel)


def all_section(cat, items, lang):
    T, url = L[lang], cat_url(cat, lang)
    return f'''<section class="row row-small">
  <div class="col">
    <div class="section-head">
      <h2 class="section-title"><a href="{url}">{e(cat_name(cat, lang))}</a></h2>
      <div class="section-links"><a href="{url}">{T["view_all"].format(len(items))}</a></div>
    </div>
  </div>
  <div class="col"><div class="row row-small grid-products">{cards(items, lang)}</div></div>
</section>'''


def category_section(cat, items, lang):
    T = L[lang]
    empty = f'<p class="empty-note">{T["empty"]}</p>' if not items else ""
    return f'''<section class="row row-small">
    <div class="col">
      <div class="section-head">
        <h1 class="section-title">{e(cat_name(cat, lang))}</h1>
        <div class="section-links">{T["count"].format(len(items))}</div>
      </div>
    </div>
    <div class="col">
      <div class="row row-small grid-products">{cards(items, lang)}</div>
      {empty}
    </div>
  </section>'''


def home_items(cats, curated, pool, by_slug):
    new = [p for p in pool if p["cat"] in cats and p["slug"] not in HOME_KNOWN]   # newest first, like the index
    old = [by_slug[s] for s in curated if s in by_slug]
    return (new + old)[:HOME_LIMIT]


def build_products():
    index = load(DATA / "products.json")
    full = []
    for row in index:
        f = DATA / "products" / f"{row['slug']}.json"
        rec = load(f) if f.exists() else {}
        rec.update(row)          # the index is written last by the CMS: it wins on shared fields
        full.append(rec)
    pub = [p for p in full if p.get("status", "published") == "published" and p.get("cat") in CAT]
    pools = {"vi": pub, "en": [p for p in pub if p.get("nameEn") and p.get("slugEn")]}
    tpl = {"vi": read(TPL / "product-vi.html"), "en": read(TPL / "product-en.html")}

    for lang in ("vi", "en"):
        pool = pools[lang]
        by_slug = {p["slug"]: p for p in pool}
        for p in pool:
            related = [q for q in pool if q["cat"] == p["cat"] and q["slug"] != p["slug"]][:4]
            base = "sp" if lang == "vi" else "product"
            slug = p["slug"] if lang == "vi" else p["slugEn"]
            write(SITE / base / slug / "index.html", product_page(p, lang, tpl[lang], related))
        # listing regions
        home = "index.html" if lang == "vi" else "home/index.html"
        for n, (cats, curated) in enumerate(HOME_SECTIONS, 1):
            patch(home, f"home{n}", cards(home_items(cats, curated, pool, by_slug), lang))
        all_page = "san-pham/index.html" if lang == "vi" else "products/index.html"
        sections = [all_section(c[0], [p for p in pool if p["cat"] == c[0]], lang) for c in CATEGORIES]
        sections = [s for s, c in zip(sections, CATEGORIES) if any(p["cat"] == c[0] for p in pool)]
        patch(all_page, "all", "\n".join(sections))
        for c in CATEGORIES:
            page = f"danh-muc/{c[0]}/index.html" if lang == "vi" else f"category/{c[2]}/index.html"
            if (SITE / page).exists():
                patch(page, "category", category_section(c[0], [p for p in pool if p["cat"] == c[0]], lang))
            else:
                print(f"warning: missing category page {page}")

    # search data + EN names for the cart
    def row(p, lang):
        return {"slug": p["slug"] if lang == "vi" else p["slugEn"], "name": prod_name(p, lang),
                "sku": p.get("sku", ""), "size": p.get("size", ""), "price": price_text(p, lang),
                "priceNum": p["price"] if isinstance(p.get("price"), int) else None,
                "category": cat_name(p["cat"], lang),
                "categorySlug": CAT[p["cat"]][0] if lang == "vi" else CAT[p["cat"]][2],
                "thumb": (p.get("image") or "").lstrip("/"), **({"cartSlug": p["slug"]} if lang == "en" else {})}
    write(SITE / "assets/data/products.json", json.dumps([row(p, "vi") for p in pools["vi"]], ensure_ascii=False, indent=1))
    write(SITE / "assets/data/products-en.json", json.dumps([row(p, "en") for p in pools["en"]], ensure_ascii=False, indent=1))
    cat_js = {p["slug"]: {"name": p["nameEn"], "slug": p["slugEn"]} for p in pools["en"]}
    write(SITE / "assets/js/catalog.js",
          "/* generated by scripts/build.py - English names / URLs of the products,\n"
          "   keyed by the Vietnamese slug the cart stores. */\n"
          "window.HTY_CATALOG = " + json.dumps(cat_js, ensure_ascii=False, indent=1) + ";\n")
    return {p["slug"] for p in pools["vi"]}, {p["slugEn"] for p in pools["en"]}


# ------------------------------------------------------------------ news
def slugify(s):
    s = unicodedata.normalize("NFD", text(s).replace("đ", "d").replace("Đ", "D"))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "muc"


def heading_ids(body):
    """Give every <h2> a stable id (CMS editors cannot set ids) — needed by the table of contents."""
    used = set(re.findall(r'<h2[^>]*\sid="([^"]+)"', body))

    def add(m):
        attrs, inner = m.group(1), m.group(2)
        if re.search(r'\sid="', attrs):
            return m.group(0)
        base = slugify(inner)
        slug, n = base, 2
        while slug in used:
            slug, n = f"{base}-{n}", n + 1
        used.add(slug)
        return f'<h2{attrs} id="{slug}">{inner}</h2>'

    return re.sub(r"<h2(\b[^>]*)>(.*?)</h2>", add, body, flags=re.S)


EMPTY_P = re.compile(r"<p>(?:\s|&nbsp;|&#160;|\u00a0|<br\s*/?>)*</p>\s*", re.I)


def drop_empty_paragraphs(html):
    """TinyMCE leaves <p>&nbsp;</p> for every blank line typed in the CMS - never publish them."""
    return EMPTY_P.sub("", html or "").strip()


def has_text(html):
    return bool(re.sub(r"(?:&nbsp;|&#160;|\s)+", "", re.sub(r"<[^>]+>", "", html or "")))


def fix_images(body, credits, lang):
    def img(m):
        tag = m.group(0)
        src = re.search(r'src="([^"]+)"', tag)
        attrs = ""
        if src and "width=" not in tag:
            wh = img_size(src.group(1))
            if wh:
                attrs += f' width="{wh[0]}" height="{wh[1]}"'
        if "loading=" not in tag:
            attrs += ' loading="lazy" decoding="async"'
        return tag[:-1].rstrip("/").rstrip() + attrs + ">"

    body = re.sub(r"<img\b[^>]*>", img, body)

    def credit(m):
        fig = m.group(0)
        src = re.search(r'<img[^>]*src="([^"]+)"', fig)
        c = credits.get(Path(src.group(1)).stem) if src and "/assets/img/news/" in src.group(1) else None
        if not c or 'class="credit"' in fig:
            return fig
        span = (f' <span class="credit">{L[lang]["photo"]}: <a href="{e(c["page"])}" rel="nofollow noopener" target="_blank">'
                f'{e(c["author"])}</a> / Wikimedia Commons, {e(c["license"])}</span>')
        if "</figcaption>" in fig:
            return fig.replace("</figcaption>", span + "</figcaption>", 1)
        return fig.replace("</figure>", f"<figcaption>{span.strip()}</figcaption></figure>", 1)

    body = re.sub(r"<figure\b.*?</figure>", credit, body, flags=re.S)
    body = re.sub(r'<a href="(https?://[^"]+)"(?![^>]*rel=)', r'<a href="\1" rel="noopener" target="_blank"', body)
    return body


def toc(body, lang):
    items = re.findall(r'<h2[^>]*\sid="([^"]+)"[^>]*>(.*?)</h2>', body, re.S)
    if len(items) < 3:
        return ""
    lis = "".join(f'<li><a href="#{i}">{e(text(t))}</a></li>' for i, t in items)
    T = L[lang]
    return f'<nav class="toc" aria-label="{T["toc_label"]}"><p class="toc-title">{T["toc"]}</p><ol>{lis}</ol></nav>'


def news_url(a, lang):
    return f"/tin-tuc/{a['slug']}/" if lang == "vi" else f"/news/{a['slugEn']}/"


def news_title(a, lang):
    return a["titleVi"] if lang == "vi" else a["titleEn"]


def news_desc(a, lang):
    return a.get("descVi" if lang == "vi" else "descEn") or ""


def news_tag(a, lang):
    return a["tag"] if lang == "vi" else NEWS_TAG_EN.get(a["tag"], a["tag"])


def news_card(a, lang):
    T, url, title = L[lang], news_url(a, lang), news_title(a, lang)
    return (f'<article class="news-card">\n'
            f'      <a class="news-media" href="{url}"><img src="{e(a["cover"])}" alt="{e(title)}" loading="lazy" decoding="async"></a>\n'
            f'      <div class="news-body">\n'
            f'        <span class="news-tag">{e(news_tag(a, lang))}</span>\n'
            f'        <h3><a href="{url}">{e(title)}</a></h3>\n'
            f'        <p>{e(news_desc(a, lang))}</p>\n'
            f'        <a class="news-more" href="{url}" aria-label="{e(T["read"].format(title))}">{T["more"]}</a>\n'
            f'      </div>\n'
            f'    </article>')


def show_date(d, lang):
    y, m, dd = d.split("-")
    return f"{dd}/{m}/{y}" if lang == "vi" else f"{y}-{m}-{dd}"


def page_title(title):
    full = f"{title} | {BRAND}"
    return full if len(full) <= 65 else title


def news_page(a, lang, tpl, related, credits):
    T = L[lang]
    title = news_title(a, lang)
    body = fix_images(heading_ids(drop_empty_paragraphs(a.get("contentVi" if lang == "vi" else "contentEn") or "")), credits, lang)
    cover = a.get("cover", "")
    cover_caption = ""
    for fig in re.findall(r"<figure\b.*?</figure>", body, flags=re.S):
        if cover and f'src="{cover}"' in fig:
            cap = re.search(r"<figcaption>.*?</figcaption>", fig, re.S)
            cover_caption = cap.group(0) if cap else ""
            body = body.replace(fig, "", 1)
            break
    if not cover_caption and cover and "/assets/img/news/" in cover and Path(cover).stem in credits:
        tmp = fix_images(f'<figure><img src="{cover}" alt=""></figure>', credits, lang)
        cover_caption = re.search(r"<figcaption>.*?</figcaption>", tmp, re.S).group(0)
    minutes = max(1, round(len(text(body).split()) / 220))
    wh = img_size(cover) if cover else None
    dim = f' width="{wh[0]}" height="{wh[1]}"' if wh else ""
    cover_html = (f'<figure class="article-cover"><img src="{e(cover)}" alt="{e(title)}"{dim} fetchpriority="high" '
                  f'decoding="async">{cover_caption}</figure>') if cover else ""
    rel = "\n    ".join(news_card(r, lang) for r in related)
    aside = (f'''
  <aside class="related" aria-labelledby="related-title">
    <h2 class="related-title" id="related-title">{T["rel_news"]}</h2>
    <div class="news-grid">
    {rel}
    </div>
  </aside>''') if related else ""
    main = f'''<main id="main">
<div class="page-wrap"><div class="container article-wrap">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="{T["home"]}">{T["home_label"]}</a><span>/</span><a href="{T["news_base"]}">{T["news"]}</a><span>/</span>{e(title)}</nav>
  <article class="article">
    <header class="article-head">
      <span class="news-tag">{e(news_tag(a, lang))}</span>
      <h1>{e(title)}</h1>
      <p class="article-meta"><span>{BRAND}</span><span aria-hidden="true">·</span><time datetime="{a["date"]}">{show_date(a["date"], lang)}</time><span aria-hidden="true">·</span><span>{T["minutes"].format(minutes)}</span></p>
    </header>
    {cover_html}
    {toc(body, lang)}
    <div class="article-body">
{body}
    </div>
  </article>{aside}
</div></div>
</main>'''
    has_en = bool(a.get("titleEn") and a.get("slugEn"))
    url_vi = news_url(a, "vi")
    url_en = news_url(a, "en") if has_en else "/news/"
    modified = (a.get("updatedAt") or a["date"])[:10]
    head = [f'<meta name="description" content="{e(news_desc(a, lang))}">',
            f'<meta property="article:published_time" content="{a["date"]}">',
            f'<meta property="article:modified_time" content="{max(modified, a["date"])}">',
            f'<meta property="article:section" content="{e(news_tag(a, lang))}">',
            f'<link rel="alternate" hreflang="vi" href="{url_vi}">']
    if has_en:
        head.append(f'<link rel="alternate" hreflang="en" href="{url_en}">')
    return fill(tpl, TITLE=e(page_title(title)), HEAD="\n".join(head), URL_VI=url_vi, URL_EN=url_en, MAIN=main)


def build_news():
    index = load(DATA / "news.json")
    credits = load(DATA / "news-images.json") if (DATA / "news-images.json").exists() else {}
    full = []
    for row in index:
        f = DATA / "news" / f"{row['slug']}.json"
        rec = load(f) if f.exists() else {}
        rec.update(row)
        full.append(rec)
    pub = [a for a in full if a.get("status", "published") == "published"]
    order = {a["slug"]: i for i, a in enumerate(pub)}
    pub.sort(key=lambda a: (-int(a["date"].replace("-", "")), order[a["slug"]]))   # newest first, stable
    pools = {"vi": pub, "en": [a for a in pub if a.get("titleEn") and a.get("slugEn")]}
    tpl = {"vi": read(TPL / "news-vi.html"), "en": read(TPL / "news-en.html")}

    for lang in ("vi", "en"):
        pool = pools[lang]
        for n, a in enumerate(pool):
            same = [x for x in pool if x is not a and x["tag"] == a["tag"]]
            others = [pool[(n + k) % len(pool)] for k in range(1, len(pool))]
            related = (same + [o for o in others if o not in same])[:3]
            base = "tin-tuc" if lang == "vi" else "news"
            slug = a["slug"] if lang == "vi" else a["slugEn"]
            write(SITE / base / slug / "index.html", news_page(a, lang, tpl[lang], related, credits))
    patch("tin-tuc/index.html", "news",
          '<div class="news-grid">' + "".join(news_card(a, "vi") for a in pools["vi"]) + "</div>")
    # no English article -> the original hand-made cards (templates/news-en-empty.html)
    patch("news/index.html", "news",
          '<div class="news-grid">' + "".join(news_card(a, "en") for a in pools["en"]) + "</div>"
          if pools["en"] else read(TPL / "news-en-empty.html"))
    patch("404.html", "latest-news",
          "<ul>" + "".join(f'<li><a href="{news_url(a, "vi")}">{e(a["titleVi"])}</a></li>' for a in pools["vi"][:6]) + "</ul>")
    return {a["slug"] for a in pools["vi"]}, {a["slugEn"] for a in pools["en"]}


# ------------------------------------------------------------------ general settings
# data/settings.json (CMS tab "Cài đặt chung", GAS.md mục V-c) -> every page. Regions between
# <!-- set:NAME --> and <!-- /set:NAME --> are rewritten (scripts/add_settings_markers.py put
# them there); links with data-set="phone" / data-set="email" get the main phone / email.
ICON_PHONE = '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M20 15.5c-1.25 0-2.45-.2-3.57-.57a1 1 0 0 0-1.02.24l-2.2 2.2a15.05 15.05 0 0 1-6.59-6.59l2.2-2.2a1 1 0 0 0 .25-1.02A11.36 11.36 0 0 1 8.5 4a1 1 0 0 0-1-1H4a1 1 0 0 0-1 1c0 9.39 7.61 17 17 17a1 1 0 0 0 1-1v-3.5a1 1 0 0 0-1-1z"/></svg>'
ICON_MAIL = '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M20 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2zm0 4-8 5-8-5V6l8 5 8-5v2z"/></svg>'
ICON_PIN = '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M12 2a7 7 0 0 0-7 7c0 5.25 7 13 7 13s7-7.75 7-13a7 7 0 0 0-7-7zm0 9.5A2.5 2.5 0 1 1 12 6.5a2.5 2.5 0 0 1 0 5z"/></svg>'
ICON_PREV = '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M14.5 18.5 8 12l6.5-6.5L15.9 6.9 10.8 12l5.1 5.1z"/></svg>'
ICON_NEXT = '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false"><path d="M9.5 5.5 16 12l-6.5 6.5L8.1 17.1 13.2 12 8.1 6.9z"/></svg>'
FAVICON = "/assets/img/2023/06/cropped-logo-32x32.jpg"
TOUCH_ICON = "/assets/img/2023/06/cropped-logo-180x180.jpg"

SL = {
    "vi": dict(contact="Thông tin liên hệ", about="Giới thiệu", map="Bản đồ Vietnam Wooden Ships",
               prev="Ảnh trước", next="Ảnh sau", choose="Chọn ảnh", image="Ảnh {}",
               workshop="Địa chỉ xưởng", phone="Điện thoại", address="Địa chỉ"),
    "en": dict(contact="Contact information", about="About us", map="Vietnam Wooden Ships map",
               prev="Previous image", next="Next image", choose="Choose image", image="Image {}",
               workshop="Workshop address", phone="Phone", address="Address"),
}


def load_settings():
    p = DATA / "settings.json"
    return load(p) if p.exists() else None


def tel(phone):
    """'0908 062 685' -> '0908062685', '+84 908…' -> '+84908…'."""
    return re.sub(r"[^\d+]", "", phone or "")


def tr(st, key, lang):
    """Bilingual field: keyVi / keyEn, English falls back to Vietnamese."""
    v = st.get(key + ("En" if lang == "en" else "Vi")) or ""
    return v or st.get(key + "Vi") or ""


def settings_regions(st, lang):
    t = SL[lang]
    phone, email = st.get("phone", ""), st.get("email", "")
    phone2, email2 = st.get("phone2", ""), st.get("email2", "")
    note2 = tr(st, "phone2Note", lang)
    company, address = tr(st, "company", lang), tr(st, "address", lang)
    home = L[lang]["home"]
    alt = tr(st, "logoAlt", lang) or st.get("siteName", BRAND)
    out = {}

    li = []
    if phone:
        li.append(f'          <li><span class="topbar-text">{ICON_PHONE} {e(phone)}</span></li>')
    if email:
        li.append(f'          <li><a href="mailto:{e(email)}">{ICON_MAIL} {e(email)}</a></li>')
    out["topbar"] = "\n".join(li)
    out["topbar-m"] = li[0] if phone else ""

    logo = st.get("logo") or "/assets/img/2023/06/logo.jpg"
    wh = img_size(logo)
    w, h = (round(wh[0] * 100 / wh[1]), 100) if wh and wh[1] else (200, 100)
    out["logo"] = (f'          <a href="{home}" rel="home" title="{e(alt)}">\n'
                   f'            <img src="{e(logo)}" width="{w}" height="{h}" alt="{e(alt)}">\n'
                   f'          </a>')

    out["header-phone"] = f'<a class="header-phone" href="tel:{tel(phone)}">{ICON_PHONE} {e(phone)}</a>' if phone else ""

    rows = []
    if company:
        rows.append(f"<p><strong>{e(company)}</strong></p>")
    if address:
        rows.append(f"<p>{ICON_PIN} <span>{e(address)}</span></p>")
    if phone:
        rows.append(f'<p>{ICON_PHONE} <a href="tel:{tel(phone)}">{e(phone)}</a></p>')
    if phone2:
        rows.append(f"<p>{ICON_PHONE} <span>{e(phone2)}{f' – Contact ({e(note2)})' if note2 else ''}</span></p>")
    for m in (email, email2):
        if m:
            rows.append(f'<p>{ICON_MAIL} <a href="mailto:{e(m)}">{e(m)}</a></p>')
    widgets = [("contact", "\n".join("          " + r for r in rows))]
    if st.get("mapEmbed"):
        widgets.append(("map", f'''          <iframe class="footer-map" title="{t['map']}" loading="lazy"
            referrerpolicy="no-referrer-when-downgrade" allowfullscreen
            src="{e(st['mapEmbed'])}"></iframe>'''))
    about_rows = []
    if tr(st, "aboutTitle", lang):
        about_rows.append(f'          <p class="muted">{e(tr(st, "aboutTitle", lang))}</p>')
    if tr(st, "about", lang):
        about_rows.append(f'          <p><span>{e(tr(st, "about", lang))}</span></p>')
    if about_rows:
        widgets.append(("about", "\n".join(about_rows)))
    titles = {"contact": t["contact"], "map": "Google Map", "about": t["about"]}
    out["footer"] = '    <div class="row">\n\n' + "\n\n".join(
        f'''      <div class="widget">
        <h3 class="widget-title">{titles[k]}</h3>
        <div class="is-divider"></div>
        <div class="textwidget">
{body}
        </div>
      </div>''' for k, body in widgets) + "\n\n    </div>"

    slides = [s for s in st.get("slides") or [] if s.get("image")]
    n = len(slides)
    track = "".join(
        f'<div class="slide" role="group" aria-roledescription="slide" aria-label="{i + 1} / {n}" '
        f'aria-hidden="{"false" if i == 0 else "true"}"><div class="slide-bg" '
        f'style="background-image:url(&quot;{e(s["image"])}&quot;)" role="img" aria-label="{e(tr(s, "caption", lang))}"></div>'
        f'<div class="slide-overlay"></div>'
        + (f'<p class="slide-caption">{e(tr(s, "caption", lang))}</p>' if tr(s, "caption", lang) else "")
        + "</div>" for i, s in enumerate(slides))
    dots = "".join(
        f'<button type="button" role="tab" aria-selected="{"true" if i == 0 else "false"}" aria-label="{t["image"].format(i + 1)}"></button>'
        for i in range(n))
    out["slider"] = (f'      <div class="slider-track">{track}</div>\n'
                     + (f'      <button class="slider-arrow prev" type="button" aria-label="{t["prev"]}">{ICON_PREV}</button>\n'
                        f'      <button class="slider-arrow next" type="button" aria-label="{t["next"]}">{ICON_NEXT}</button>\n'
                        f'      <div class="slider-dots" role="tablist" aria-label="{t["choose"]}">{dots}</div>'
                        if n > 1 else "")).rstrip("\n")

    cards = []
    if address:
        cards.append(f"      <h3>{t['workshop']}</h3>\n      <p>{e(address)}</p>")
    ph = ([f'      <p><a href="tel:{tel(phone)}">{e(phone)}</a></p>'] if phone else []) + \
         ([f"      <p>{e(phone2)}{f' ({e(note2)})' if note2 else ''}</p>"] if phone2 else [])
    if ph:
        cards.append(f"      <h3>{t['phone']}</h3>\n" + "\n".join(ph))
    em = [f'      <p><a href="mailto:{e(m)}">{e(m)}</a></p>' for m in (email, email2) if m]
    if em:
        cards.append("      <h3>Email</h3>\n" + "\n".join(em))
    out["contact"] = '<div class="contact-grid">\n' + "\n".join(
        f'    <div class="contact-card">\n{c}\n    </div>' for c in cards) + "\n  </div>"
    out["contact-map"] = (f'''<iframe class="footer-map contact-map" title="{t['map']}" loading="lazy"
      referrerpolicy="no-referrer-when-downgrade" allowfullscreen
      src="{e(st['mapEmbed'])}"></iframe>''' if st.get("mapEmbed") else "")

    ac = []
    if company:
        ac.append(f"<p><strong>{e(company)}</strong></p>")
    if address:
        ac.append(f"<p>{t['address']}: {e(address)}</p>")
    if phone:
        ac.append(f'<p>{t["phone"]}: <a href="tel:{tel(phone)}">{e(phone)}</a></p>')
    if email:
        ac.append(f'<p>Email: <a href="mailto:{e(email)}">{e(email)}</a></p>')
    out["about-contact"] = "\n    ".join(ac)
    return out


SET_RE = re.compile(r"(<!-- set:([\w-]+) -->)(.*?)(<!-- /set:\2 -->)", re.S)
PHONE_LINK = re.compile(r'<a ((?:class="[^"]*" )?)href="tel:[^"]*" data-set="phone">(.*?)</a>', re.S)
EMAIL_LINK = re.compile(r'<a ((?:class="[^"]*" )?)href="mailto:[^"]*" data-set="email">(.*?)</a>', re.S)
ICON_LINK = re.compile(r'<link rel="icon" href="[^"]*"( sizes="[^"]*")?>')
TOUCH_LINK = re.compile(r'<link rel="apple-touch-icon" href="[^"]*">')


def apply_settings_to(s, st, regions):
    s = SET_RE.sub(lambda m: m.group(1) + regions.get(m.group(2), m.group(3)) + m.group(4), s)
    phone, email = st.get("phone", ""), st.get("email", "")

    def link(m, href, value, test):
        # keep button text ("Gọi ngay"); replace text that is the number / address itself
        inner = e(value) if test(m.group(2)) else m.group(2)
        return f'<a {m.group(1)}href="{href}" data-set="{"phone" if href.startswith("tel") else "email"}">{inner}</a>'
    if phone:
        s = PHONE_LINK.sub(lambda m: link(m, "tel:" + tel(phone), phone, lambda x: re.fullmatch(r"[\d\s+().-]+", x)), s)
    if email:
        s = EMAIL_LINK.sub(lambda m: link(m, "mailto:" + e(email), email, lambda x: "@" in x), s)
    fav = st.get("favicon")
    s = ICON_LINK.sub(f'<link rel="icon" href="{e(fav)}">' if fav else f'<link rel="icon" href="{FAVICON}" sizes="32x32">', s)
    s = TOUCH_LINK.sub(f'<link rel="apple-touch-icon" href="{e(fav or TOUCH_ICON)}">', s)
    return s


def apply_settings():
    st = load_settings()
    if not st:
        print("warning: data/settings.json missing - general settings not applied")
        return
    regions = {lang: settings_regions(st, lang) for lang in ("vi", "en")}
    for f in SITE.rglob("*.html"):
        rel = f.relative_to(SITE).parts
        if rel[0] in ("admin", "vendor", "assets"):
            continue
        s = read(f)
        lang = "en" if '<html lang="en"' in s else "vi"
        write(f, apply_settings_to(s, st, regions[lang]))


# ------------------------------------------------------------------ cleanup
def remove_orphans(parent, keep):
    base = SITE / parent
    if not base.is_dir():
        return
    for d in sorted(base.iterdir()):
        if d.is_dir() and (d / "index.html").exists() and d.name not in keep:
            shutil.rmtree(d)
            print(f"removed /{parent}/{d.name}/")


def main():
    vi, en = build_products()
    nvi, nen = build_news()
    remove_orphans("sp", vi)
    remove_orphans("product", en)
    remove_orphans("tin-tuc", nvi)
    remove_orphans("news", nen)
    apply_settings()
    sys.path.insert(0, str(ROOT / "scripts"))
    import seo
    seo.main()
    print(f"built {len(vi)} + {len(en)} product pages, {len(nvi)} + {len(nen)} articles")


if __name__ == "__main__":
    main()
