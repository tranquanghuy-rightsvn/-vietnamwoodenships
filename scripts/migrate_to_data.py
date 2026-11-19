#!/usr/bin/env python3
"""ONE-TIME migration: current hand-built site -> data/ (CMS source of truth) + templates/.

    python3 scripts/migrate_to_data.py           # writes data/*, templates/*, inserts build markers
    python3 scripts/migrate_to_data.py --force   # overwrite existing data/ / templates/

After this, scripts/build.py renders html/ from data/ + templates/ (see GAS.md).
Already run on 2026-11-19; its inputs under content/ were deleted afterwards (data/ is the
source of truth now). Kept for reference only — do not run again: it would overwrite what
editors saved in the CMS.

Reads:
  html/san-pham/index.html            display order + card front/back images
  html/sp/<slug>/index.html           VI product: name, specs, gallery, "Mô tả" notes, category
  html/product/<slugEn>/index.html    EN product: "Description" notes
  html/assets/js/catalog.js           VI slug -> EN name / slug
  content/products/<slug>.vi|en.html  long introduction + meta description
  content/tin-tuc/<slug>.html         news articles (front matter + body)
  content/tin-tuc/images.json         Wikimedia credits -> data/news-images.json
Writes:
  data/products.json, data/products/<slug>.json, data/news.json, data/news/<slug>.json,
  data/news-images.json, templates/product-{vi,en}.html, templates/news-{vi,en}.html,
  build markers inside listing pages (home, san-pham, danh-muc, tin-tuc, news, 404).
"""
import html as H
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "html"
DATA = ROOT / "data"
TPL = ROOT / "templates"
CONTENT = ROOT / "content"
FORCE = "--force" in sys.argv
NOW = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

NEWS_ORDER = [
    "chon-mo-hinh-tau-du-lich-du-thuyen",
    "mo-hinh-thuyen-buom-tau-huyen-thoai",
    "mo-hinh-tau-cho-hang",
    "noi-that-go-thu-cong",
    "kinh-nghiem-mua-mo-hinh-thuyen-go",
    "bao-quan-mo-hinh-thuyen-go",
]
TAG = re.compile(r"<[^>]+>")


def text(s):
    return re.sub(r"\s+", " ", H.unescape(TAG.sub(" ", s or ""))).strip()


def read(p):
    return Path(p).read_text(encoding="utf-8")


def write(p, s):
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(s, encoding="utf-8")


def dump(p, obj):
    write(p, json.dumps(obj, ensure_ascii=False, indent=1) + "\n")


def front_matter(path):
    raw = read(path)
    m = re.match(r"\s*<!--meta\s*(\{.*?\})\s*-->", raw, re.S)
    return (json.loads(m.group(1)), raw[m.end():].strip()) if m else ({}, raw.strip())


def catalog():
    js = read(SITE / "assets/js/catalog.js")
    return json.loads(js[js.index("{"): js.rindex("}") + 1])


def desc_block(page):
    """Lines + images of the legacy 'Mô tả' / 'Description' block."""
    m = re.search(r'<div class="product-desc">.*?<div style="margin-top:16px">(.*?)</div></div>', page, re.S)
    if not m:
        return [], []
    inner = m.group(1)
    imgs = re.findall(r'<img[^>]*src="([^"]+)"', inner)
    lines = [text(p) for p in re.findall(r"<p>(.*?)</p>", inner, re.S)]
    # drop empty placeholders left over from the original shop ("Kích thước:", "Gía bán:……")
    lines = [l for l in lines if l and not re.fullmatch(r"[^:]{0,20}:\s*[.…]*", l)]
    return lines, imgs


def migrate_products():
    cat_map = catalog()
    listing = read(SITE / "san-pham/index.html")
    cards = re.findall(r'<div class="col">\s*<article class="product-card">.*?</article>\s*</div>', listing, re.S)
    index = []
    for card in cards:
        slug = re.search(r'data-slug="([^"]+)"', card).group(1)
        front = re.search(r'<img src="([^"]+)"', card).group(1)
        back = re.search(r'class="img-back" src="([^"]+)"', card)
        page = read(SITE / "sp" / slug / "index.html")
        name = text(re.search(r"<h1>(.*?)</h1>", page, re.S).group(1))
        specs = {text(dt): text(dd) for dt, dd in re.findall(r"<dt>(.*?)</dt><dd>(.*?)</dd>", page)}
        cat = re.search(r'<p class="product-meta">[^<]*<a href="/danh-muc/([^/]+)/"', page).group(1)
        price = re.search(r'data-product[^>]*data-price="(\d*)"', page, re.S).group(1)
        gallery = re.findall(r'data-full="([^"]+)"', page)
        if not gallery:
            gallery = re.findall(r'<div class="gallery-main"><img src="([^"]+)"', page)
        lines_vi, desc_imgs = desc_block(page)
        images = list(gallery) + [i for i in desc_imgs if i not in gallery]

        en = cat_map.get(slug, {})
        name_en, slug_en, lines_en = en.get("name", ""), en.get("slug", ""), []
        if slug_en and (SITE / "product" / slug_en / "index.html").exists():
            lines_en, _ = desc_block(read(SITE / "product" / slug_en / "index.html"))
        meta_vi, intro_vi = front_matter(CONTENT / "products" / f"{slug}.vi.html")
        meta_en, intro_en = front_matter(CONTENT / "products" / f"{slug}.en.html") \
            if (CONTENT / "products" / f"{slug}.en.html").exists() else ({}, "")

        rec = {
            "slug": slug, "slugEn": slug_en, "sku": specs.get("Mã sản phẩm", ""), "cat": cat,
            "nameVi": name, "nameEn": name_en, "size": specs.get("Kích thước", ""),
            "price": int(price) if price else None,
            "image": front, "image2": back.group(1) if back else "",
            "status": "published", "updatedAt": NOW,
        }
        index.append(dict(rec))
        rec.update({
            "priceNoteVi": "\n".join(lines_vi), "priceNoteEn": "\n".join(lines_en),
            "metaVi": meta_vi.get("description", ""), "metaEn": meta_en.get("description", ""),
            "images": images, "introVi": intro_vi, "introEn": intro_en,
        })
        dump(DATA / "products" / f"{slug}.json", rec)
    dump(DATA / "products.json", index)
    return index


def migrate_news():
    index = []
    for slug in NEWS_ORDER:
        meta, body = front_matter(CONTENT / "tin-tuc" / f"{slug}.html")
        rec = {
            "slug": slug, "slugEn": "", "tag": meta["tag"],
            "titleVi": meta.get("h1") or meta["title"], "titleEn": "",
            "descVi": meta["description"], "descEn": "", "cover": meta["cover"],
            "date": meta["date"], "status": "published", "updatedAt": NOW,
        }
        index.append(dict(rec))
        rec.update({"contentVi": body, "contentEn": ""})
        dump(DATA / "news" / f"{slug}.json", rec)
    dump(DATA / "news.json", index)
    credits = CONTENT / "tin-tuc" / "images.json"
    if credits.exists():
        write(DATA / "news-images.json", read(credits))
    return index


# ---------------------------------------------------------------- templates
def strip_seo(s):
    return re.sub(r"\n?<!-- seo:start -->.*?<!-- seo:end -->", "", s, flags=re.S)


def shell(page, url_vi, url_en):
    """Page minus seo block, with {{TITLE}}, {{HEAD}}, {{URL_VI}}, {{URL_EN}} placeholders."""
    s = strip_seo(page)
    s = re.sub(r"\n?<meta (?:name=\"(?:description|keywords)\"|property=\"article:[^\"]*\")[^>]*>", "", s)
    s = re.sub(r"<title>.*?</title>", "<title>{{TITLE}}</title>", s, count=1, flags=re.S)
    s = s.replace("</head>", "{{HEAD}}\n</head>", 1)
    s = s.replace(f'href="{url_vi}" hreflang="vi"', 'href="{{URL_VI}}" hreflang="vi"')
    s = s.replace(f'href="{url_en}" hreflang="en"', 'href="{{URL_EN}}" hreflang="en"')
    return s


def product_template(page, url_vi, url_en, lang):
    s = shell(page, url_vi, url_en)
    i, j = s.index('<main id="main">'), s.index("</main>")
    main = s[i:j]
    main = re.sub(r'(<nav class="breadcrumb" aria-label="Breadcrumb">\s*<a href=")[^"]*(">)[^<]*(</a><span>/</span>\s*<a href=")[^"]*(">)[^<]*(</a><span>/</span>)[^\n<]*',
                  r"\1{{HOME_URL}}\2{{HOME_LABEL}}\3{{CAT_URL}}\4{{CAT_NAME}}\5{{NAME}}", main, count=1)
    main = re.sub(r'<div class="gallery-main">.*?</div>\s*<div class="gallery-thumbs".*?</div>', "{{GALLERY}}", main, count=1, flags=re.S)
    main = re.sub(r"<h1>.*?</h1>", "<h1>{{NAME}}</h1>", main, count=1)
    main = re.sub(r'<dl class="spec-list">.*?</dl>', "{{SPECS}}", main, count=1)
    main = re.sub(r'data-slug="[^"]*" data-name="[^"]*"\s*data-img="[^"]*" data-price-text="[^"]*" data-price="[^"]*"',
                  'data-slug="{{CART_SLUG}}" data-name="{{NAME_ATTR}}"\n             data-img="{{IMAGE}}" data-price-text="{{PRICE_TEXT_ATTR}}" data-price="{{PRICE}}"', main, count=1)
    main = re.sub(r'(<p class="product-meta">[^<]*<a href=")[^"]*(">)[^<]*(</a>)', r"\1{{CAT_URL}}\2{{CAT_NAME}}\3", main, count=1)
    main = re.sub(r'\n?\s*<div class="product-desc">.*?</div></div>', "\n        {{DESC}}", main, count=1, flags=re.S)
    main = re.sub(r"<!-- about:start -->.*?<!-- about:end -->\s*", "{{ABOUT}}\n", main, count=1, flags=re.S)
    main = re.sub(r'\s*<section class="row row-small" style="margin-top:30px">.*?</section>\n', "\n  {{RELATED}}\n", main, count=1, flags=re.S)
    for ph in ("{{GALLERY}}", "{{SPECS}}", "{{DESC}}", "{{ABOUT}}", "{{RELATED}}", "{{CART_SLUG}}", "{{CAT_URL}}"):
        assert ph in main, (lang, ph)
    return s[:i] + main + s[j:]


def news_template(listing, url_vi, url_en):
    s = shell(listing, url_vi, url_en)
    i, j = s.index('<main id="main">'), s.index("</main>") + len("</main>")
    return s[:i] + "{{MAIN}}" + s[j:]


def scaffold_templates():
    write(TPL / "product-vi.html", product_template(read(SITE / "sp/victory/index.html"), "/sp/victory/", "/product/victory/", "vi"))
    write(TPL / "product-en.html", product_template(read(SITE / "product/victory/index.html"), "/sp/victory/", "/product/victory/", "en"))
    write(TPL / "news-vi.html", news_template(read(SITE / "tin-tuc/index.html"), "/tin-tuc/", "/news/"))
    write(TPL / "news-en.html", news_template(read(SITE / "news/index.html"), "/tin-tuc/", "/news/"))
    # cards shown on /news/ while no article has an English version
    grid = re.search(r'(<div class="news-grid">.*?</article></div>)', read(SITE / "news/index.html"), re.S)
    write(TPL / "news-en-empty.html", grid.group(1))


# ---------------------------------------------------------------- build markers
def mark(path, pattern, name, flags=re.S):
    """Wrap the first match of `pattern` (group 1 = region) in <!-- build:name --> markers."""
    p = SITE / path
    s = read(p)
    if f"<!-- build:{name} -->" in s:
        return
    m = re.search(pattern, s, flags)
    assert m, (path, name)
    s = s[:m.start(1)] + f"<!-- build:{name} -->" + m.group(1) + f"<!-- /build:{name} -->" + s[m.end(1):]
    write(p, s)


def insert_markers():
    for home in ("index.html", "home/index.html"):
        s = read(SITE / home)
        n = 0
        def repl(m):
            nonlocal n
            n += 1
            return f'{m.group(1)}<!-- build:home{n} -->{m.group(2)}<!-- /build:home{n} -->{m.group(3)}'
        if "<!-- build:home1 -->" not in s:
            s = re.sub(r'(<div class="row row-small grid-products">)(.*?</article>\s*</div>)(</div>\s*</div>\s*</section>)', repl, s, flags=re.S)
            write(SITE / home, s)
    for page in ("san-pham/index.html", "products/index.html"):
        mark(page, r'<div class="container"><nav class="breadcrumb">.*?</nav></div>(<section class="row row-small">.*</section>)</div>', "all")
    for parent in ("danh-muc", "category"):
        for d in sorted((SITE / parent).iterdir()):
            if (d / "index.html").exists():
                mark(f"{parent}/{d.name}/index.html", r'</div>\n  (<section class="row row-small">.*?</section>)\n</div>', "category")
    mark("tin-tuc/index.html", r'(<div class="news-grid">.*?</div>)\s*<p class="news-cta">', "news")
    mark("news/index.html", r'(<div class="news-grid">.*?</article></div>)', "news")
    mark("404.html", r"<div><h2>Bài viết mới</h2>(<ul>.*?</ul>)</div>", "latest-news")


def main():
    if (DATA / "products.json").exists() and not FORCE:
        raise SystemExit("data/products.json already exists - the CMS owns data/ now. Use --force to re-migrate.")
    products = migrate_products()
    news = migrate_news()
    if not (TPL / "product-vi.html").exists() or FORCE:
        scaffold_templates()
    insert_markers()
    print(f"{len(products)} products, {len(news)} articles -> data/; templates/ + build markers ready")


if __name__ == "__main__":
    main()
