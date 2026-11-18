#!/usr/bin/env python3
"""Add full SEO markup to every page in html/ and write robots.txt + sitemap.xml.

For each page it (re)writes one block in <head>, between
<!-- seo:start --> and <!-- seo:end -->:

  meta description / robots, canonical, hreflang (vi, en, x-default),
  Open Graph, Twitter card and a JSON-LD @graph
  (Organization, WebSite, WebPage/ItemPage/..., BreadcrumbList, Product, ItemList).

All URLs are absolute directory URLs with a trailing slash (/sp/victory/,
/about/), each served from <slug>/index.html (see vercel.json). Idempotent: safe to run after every edit.

    python3 scripts/seo.py                    # uses https://vietnamwoodenships.com
    SITE_URL=https://example.com python3 scripts/seo.py
"""
import html as H
import json
import os
import re
from datetime import date, datetime
from pathlib import Path
from posixpath import join, normpath

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "html"
BASE = os.environ.get("SITE_URL", "https://vietnamwoodenships.com").rstrip("/")
LOGO = "/assets/img/2023/06/logo.jpg"

# Pages with no search value (per-user state, or no real content yet):
# noindex,follow and left out of the sitemap.
NOINDEX = {
    "gio-hang", "cart", "thanh-toan", "checkout",
    "tai-khoan", "account", "tim-kiem", "search",
    "huong-dan", "guide",
}

# Descriptions for pages that had none (or only a stub).
DESC = {
    "gioi-thieu": "Hoa Tay Việt – xưởng sản xuất thuyền mỹ nghệ tại Long Thành, Đồng Nai, chuyên chế tác thủ công và xuất khẩu mô hình tàu, du thuyền, thuyền buồm và nội thất gỗ.",
    "about": "Hoa Tay Viet – an art boat workshop in Long Thanh, Dong Nai, Vietnam, handcrafting and exporting ship models, yachts, sailing boats and wooden furniture.",
    "lien-he": "Liên hệ Hoa Tay Việt để được tư vấn mẫu mã, kích thước và báo giá mô hình thuyền: 199 ấp 1B, Phước Thái, Long Thành, Đồng Nai – 0908 062 685.",
    "contact": "Contact Hoa Tay Viet for advice on models, sizes and a quote for handmade ship models: 199 Hamlet 1B, Phuoc Thai, Long Thanh, Dong Nai – +84 908 062 685.",
    "tin-tuc": "Tin tức, kiến thức và hướng dẫn chọn mua, bảo quản mô hình tàu thuyền thủ công từ xưởng Hoa Tay Việt.",
    "news": "News, tips and guides on choosing and caring for handmade ship models from the Hoa Tay Viet workshop.",
    "huong-dan-mua-hang": "Hướng dẫn mua hàng tại Hoa Tay Việt: chọn sản phẩm, thêm vào giỏ hàng, kiểm tra giỏ và thanh toán khi nhận hàng hoặc quét mã QR.",
    "buying-guide": "How to buy at Hoa Tay Viet: choose a product, add it to the cart, review your cart and pay on delivery or by QR code.",
    "huong-dan-su-dung": "Hướng dẫn sử dụng và bảo quản mô hình thuyền gỗ thủ công Hoa Tay Việt: đặt nơi khô ráo, tránh nắng gắt, vệ sinh và cầm đúng cách.",
    "user-guide": "How to care for your handmade Hoa Tay Viet wooden boat model: keep it dry, out of strong sun, dust it gently and handle it correctly.",
    "huong-dan": "Hướng dẫn mua hàng và sử dụng sản phẩm thuyền mỹ nghệ Hoa Tay Việt.",
    "guide": "Guides for buying and using Hoa Tay Viet art boat products.",
    "gio-hang": "Giỏ hàng của bạn tại Hoa Tay Việt.",
    "cart": "Your shopping cart at Hoa Tay Viet.",
    "thanh-toan": "Thanh toán đơn hàng tại Hoa Tay Việt – thanh toán khi nhận hàng hoặc quét mã QR.",
    "checkout": "Checkout at Hoa Tay Viet – pay on delivery or by QR code.",
    "tai-khoan": "Đăng nhập tài khoản Hoa Tay Việt.",
    "account": "Sign in to your Hoa Tay Viet account.",
    "tim-kiem": "Tìm kiếm sản phẩm thuyền mỹ nghệ Hoa Tay Việt theo tên, mã sản phẩm hoặc danh mục.",
    "search": "Search Hoa Tay Viet art boat products by name, product code or category.",
    "san-pham": "Toàn bộ 32 sản phẩm thủ công của Hoa Tay Việt: mô hình tàu du lịch, du thuyền, tàu chở hàng, thuyền buồm, thuyền đi dạo và nội thất gỗ.",
    "products": "All 32 handmade products of Hoa Tay Viet: cruise ship and yacht models, cargo ships, sailing boats, leisure boats and wooden furniture.",
}

PAGE_TYPE = {
    "gioi-thieu": "AboutPage", "about": "AboutPage",
    "lien-he": "ContactPage", "contact": "ContactPage",
    "tim-kiem": "SearchResultsPage", "search": "SearchResultsPage",
    "tin-tuc": "CollectionPage", "news": "CollectionPage",
    "san-pham": "CollectionPage", "products": "CollectionPage",
}

START, END = "<!-- seo:start -->", "<!-- seo:end -->"
TAG = re.compile(r"<[^>]+>")


def text(s):
    return re.sub(r"\s+", " ", H.unescape(TAG.sub(" ", s or ""))).strip()


def rel(f):
    return f.relative_to(SITE).as_posix()


def clean_path(path):
    """'sp/x/index.html' -> '/sp/x/', 'about/index.html' -> '/about/', 'index.html' -> '/'."""
    path = "/" + path.lstrip("/")
    if path.endswith("index.html"):
        path = path[: -len("index.html")]
    elif path.endswith(".html"):
        path = path[: -len(".html")]
    return path.rstrip("/") + "/"


def resolve(href, page_rel):
    """Relative href on page -> site-root path ('assets/x.gif' -> '/assets/x.gif')."""
    href = href.split("#")[0].split("?")[0]
    if href.startswith("/"):
        return href
    return normpath(join("/", os.path.dirname(page_rel), href))


def url_of(href, page_rel):
    return BASE + clean_path(resolve(href, page_rel))


def asset_url(src, page_rel):
    return BASE + resolve(src, page_rel)


def ld(obj):
    s = json.dumps(obj, ensure_ascii=False, indent=1)
    return s.replace("</", "<\\/")


def org(lang):
    vi = lang == "vi"
    return {
        "@type": "Organization",
        "@id": BASE + "/#organization",
        "name": "Hoa Tay Việt",
        "alternateName": "Hoa Tay Viet",
        "legalName": "Công ty TNHH Hoa Tay Việt",
        "description": "Xưởng sản xuất thuyền mỹ nghệ" if vi else "Art boat workshop",
        "url": BASE + "/",
        "logo": {"@type": "ImageObject", "url": BASE + LOGO},
        "image": BASE + LOGO,
        "email": "hoatayviet.modelship@gmail.com",
        "telephone": "+84908062685",
        "address": {
            "@type": "PostalAddress",
            "streetAddress": "199 ấp 1B, Phước Thái",
            "addressLocality": "Long Thành",
            "addressRegion": "Đồng Nai",
            "addressCountry": "VN",
        },
        "contactPoint": [
            {"@type": "ContactPoint", "contactType": "customer service",
             "telephone": "+84908062685", "email": "hoatayviet.modelship@gmail.com",
             "availableLanguage": ["vi", "en"]},
            {"@type": "ContactPoint", "contactType": "sales",
             "telephone": "+84352344343", "email": "lywoodenmodelboat@gmail.com",
             "availableLanguage": ["vi", "en"]},
        ],
    }


def website(lang, search_page):
    return {
        "@type": "WebSite",
        "@id": BASE + "/#website",
        "url": BASE + "/",
        "name": "Hoa Tay Việt",
        "inLanguage": ["vi", "en"],
        "publisher": {"@id": BASE + "/#organization"},
        "potentialAction": {
            "@type": "SearchAction",
            "target": {"@type": "EntryPoint", "urlTemplate": BASE + search_page + "?s={search_term_string}"},
            "query-input": "required name=search_term_string",
        },
    }


def breadcrumb(src, page_rel, canonical):
    m = re.search(r'<nav class="breadcrumb"[^>]*>(.*?)</nav>', src, re.S)
    if not m:
        return None
    inner = m.group(1)
    items = [(url_of(h, page_rel), text(t))
             for h, t in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', inner, re.S)]
    last = text(re.split(r"</a>|</span>", inner)[-1])
    if last:
        items.append((canonical, last))
    return {
        "@type": "BreadcrumbList",
        "@id": canonical + "#breadcrumb",
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": u}
            for i, (u, n) in enumerate(items)
        ],
    }


def item_list(src, page_rel, canonical):
    seen, out = set(), []
    for h, n in re.findall(r'<p class="product-name"><a href="([^"]+)">(.*?)</a>', src, re.S):
        u = url_of(h, page_rel)
        if u not in seen:
            seen.add(u)
            out.append((u, text(n)))
    if not out:
        return None
    return {
        "@type": "ItemList",
        "@id": canonical + "#products",
        "numberOfItems": len(out),
        "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "url": u, "name": n}
            for i, (u, n) in enumerate(out)
        ],
    }


def product(src, page_rel, canonical, desc, lang):
    name = text(re.search(r"<h1>(.*?)</h1>", src, re.S).group(1))
    dds = [text(d) for d in re.findall(r"<dd>(.*?)</dd>", src, re.S)]
    images = []
    for s in re.findall(r'data-full="([^"]+)"', src) or \
            re.findall(r'<div class="gallery-main"><img src="([^"]+)"', src):
        u = asset_url(s, page_rel)
        if u not in images:
            images.append(u)
    cat = re.search(r'<p class="product-meta">[^<]*<a href="[^"]+">(.*?)</a>', src, re.S)
    price = re.search(r'data-product[^>]*data-price="(\d*)"', src, re.S)
    p = {
        "@type": "Product",
        "@id": canonical + "#product",
        "name": name,
        "url": canonical,
        "image": images,
        "description": desc,
        "brand": {"@type": "Brand", "name": "Hoa Tay Việt"},
        "manufacturer": {"@id": BASE + "/#organization"},
        "material": "Gỗ" if lang == "vi" else "Wood",
    }
    if dds:
        p["sku"] = p["mpn"] = dds[0]
    if len(dds) > 1:
        p["size"] = dds[1]
    if cat:
        p["category"] = text(cat.group(1))
    if price and price.group(1):
        p["offers"] = {
            "@type": "Offer",
            "url": canonical,
            "price": price.group(1),
            "priceCurrency": "VND",
            "availability": "https://schema.org/InStock",
            "itemCondition": "https://schema.org/NewCondition",
            "seller": {"@id": BASE + "/#organization"},
        }
    return p, images


def process(f, today):
    r = rel(f)
    src = f.read_text(encoding="utf-8")
    # Read description + hreflang first (from the original tags, or from the
    # block a previous run wrote), then drop them so they are written once.
    lang = re.search(r'<html lang="([a-z]+)"', src).group(1)
    title = text(re.search(r"<title>(.*?)</title>", src, re.S).group(1))
    old_desc = re.search(r'<meta name="description" content="([^"]*)">', src)
    desc = DESC.get(clean_path(r).strip("/")) or (H.unescape(old_desc.group(1)) if old_desc else "")

    # hreflang pairs come from the page itself (built by build_en.py)
    alts = {hl: (BASE + clean_path(re.sub(r"^https?://[^/]+", "", h)) if h.startswith("http") else url_of(h, r)) for hl, h in
            re.findall(r'<link rel="alternate" hreflang="(vi|en)" href="([^"]+)">', src)}
    src = re.sub(r"\n?" + re.escape(START) + r".*?" + re.escape(END), "", src, flags=re.S)
    canonical = BASE + clean_path(r)
    alts.setdefault(lang, canonical)
    src = re.sub(r'\n?<link rel="alternate" hreflang="[^"]*" href="[^"]*">', "", src)
    src = re.sub(r'\n?<meta name="description" content="[^"]*">', "", src)

    is_product = r.startswith(("sp/", "product/"))
    is_category = r.startswith(("danh-muc/", "category/"))
    is_home = r in ("index.html", "home/index.html")
    name = clean_path(r).strip("/")          # 'gioi-thieu', 'sp/victory', '' (home)
    noindex = name in NOINDEX
    vi = lang == "vi"

    if is_product:
        suffix = (" Mô hình thủ công bằng gỗ của xưởng thuyền mỹ nghệ Hoa Tay Việt."
                  if vi else " Handmade wooden model by the Hoa Tay Viet art boat workshop.")
        desc = desc.replace(suffix, "")          # idempotent re-runs
        desc = (desc.rstrip(".") + "." + suffix) if desc else suffix.strip()
    if is_category:
        cat_name = title.rsplit(" - ", 1)[0]
        desc = (f"Danh mục {cat_name} tại Hoa Tay Việt – mô hình thủ công bằng gỗ, chế tác tỉ mỉ từng chi tiết, nhận đặt hàng và xuất khẩu."
                if vi else
                f"{cat_name} at Hoa Tay Viet – handmade wooden models crafted in fine detail, made to order and exported worldwide.")

    image = BASE + LOGO
    graph = [org(lang), website(lang, "/tim-kiem/" if vi else "/search/")]
    page_type = "ItemPage" if is_product else "CollectionPage" if is_category else PAGE_TYPE.get(name, "WebPage")
    page = {
        "@type": page_type,
        "@id": canonical + "#webpage",
        "url": canonical,
        "name": title,
        "description": desc,
        "inLanguage": lang,
        "isPartOf": {"@id": BASE + "/#website"},
        "about": {"@id": BASE + "/#organization"},
        "dateModified": today,
    }
    graph.append(page)
    bc = breadcrumb(src, r, canonical)
    if bc and not is_home:
        graph.append(bc)
        page["breadcrumb"] = {"@id": bc["@id"]}
    images = []
    if is_product:
        prod, images = product(src, r, canonical, desc, lang)
        graph.append(prod)
        page["mainEntity"] = {"@id": prod["@id"]}
        if images:
            image = images[0]
            page["primaryImageOfPage"] = {"@type": "ImageObject", "url": image}
    elif page_type in ("CollectionPage",) or is_home:
        il = item_list(src, r, canonical)
        if il:
            graph.append(il)
            page["mainEntity"] = {"@id": il["@id"]}

    locale = {"vi": "vi_VN", "en": "en_US"}
    e = lambda s: H.escape(s, quote=True)
    lines = [
        START,
        f'<meta name="description" content="{e(desc)}">',
        f'<meta name="robots" content="{"noindex, follow" if noindex else "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"}">',
        f'<link rel="canonical" href="{canonical}">',
    ]
    for hl in ("vi", "en"):
        if hl in alts:
            lines.append(f'<link rel="alternate" hreflang="{hl}" href="{alts[hl]}">')
    lines.append(f'<link rel="alternate" hreflang="x-default" href="{alts.get("vi", canonical)}">')
    lines += [
        '<meta name="author" content="Hoa Tay Việt">',
        '<meta name="theme-color" content="#446084">',
        '<meta name="format-detection" content="telephone=no">',
        f'<meta property="og:type" content="{"product" if is_product else "website"}">',
        f'<meta property="og:site_name" content="{"Hoa Tay Việt" if vi else "Hoa Tay Viet"}">',
        f'<meta property="og:title" content="{e(title)}">',
        f'<meta property="og:description" content="{e(desc)}">',
        f'<meta property="og:url" content="{canonical}">',
        f'<meta property="og:image" content="{image}">',
        f'<meta property="og:image:alt" content="{e(title)}">',
        f'<meta property="og:locale" content="{locale[lang]}">',
        f'<meta property="og:locale:alternate" content="{locale["en" if vi else "vi"]}">',
        '<meta name="twitter:card" content="summary_large_image">',
        f'<meta name="twitter:title" content="{e(title)}">',
        f'<meta name="twitter:description" content="{e(desc)}">',
        f'<meta name="twitter:image" content="{image}">',
        '<script type="application/ld+json">',
        ld({"@context": "https://schema.org", "@graph": graph}),
        "</script>",
        END,
    ]
    src = src.replace("</title>", "</title>\n" + "\n".join(lines), 1)
    f.write_text(src, encoding="utf-8")
    return {"loc": canonical, "alts": alts, "noindex": noindex, "images": images,
            "lastmod": datetime.fromtimestamp(f.stat().st_mtime).date().isoformat(),
            "priority": "1.0" if is_home else "0.8" if (is_category or is_product) else "0.6"}


def sitemap(pages):
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"'
           ' xmlns:xhtml="http://www.w3.org/1999/xhtml"'
           ' xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">']
    for p in sorted(pages, key=lambda p: (p["loc"] != BASE + "/", p["loc"])):
        if p["noindex"]:
            continue
        out.append("  <url>")
        out.append(f"    <loc>{H.escape(p['loc'])}</loc>")
        out.append(f"    <lastmod>{p['lastmod']}</lastmod>")
        out.append(f"    <priority>{p['priority']}</priority>")
        for hl in ("vi", "en"):
            if hl in p["alts"]:
                out.append(f'    <xhtml:link rel="alternate" hreflang="{hl}" href="{H.escape(p["alts"][hl])}"/>')
        out.append(f'    <xhtml:link rel="alternate" hreflang="x-default" href="{H.escape(p["alts"].get("vi", p["loc"]))}"/>')
        for img in p["images"]:
            out.append(f"    <image:image><image:loc>{H.escape(img)}</image:loc></image:image>")
        out.append("  </url>")
    out.append("</urlset>")
    return "\n".join(out) + "\n"


def main():
    today = date.today().isoformat()
    pages = [process(f, today) for f in sorted(SITE.rglob("*.html"))]
    (SITE / "sitemap.xml").write_text(sitemap(pages), encoding="utf-8")
    robots = ["User-agent: *", "Allow: /"]
    # Cart/checkout/account/search are noindex; block crawling of search query URLs only,
    # so crawlers can still read the noindex tag on the plain pages.
    robots += ["Disallow: /tim-kiem/?", "Disallow: /search/?", "Disallow: /*?s=", ""]
    robots += [f"Sitemap: {BASE}/sitemap.xml", ""]
    (SITE / "robots.txt").write_text("\n".join(robots), encoding="utf-8")
    n = sum(not p["noindex"] for p in pages)
    print(f"{len(pages)} pages processed, {n} in sitemap, {len(pages) - n} noindex")


if __name__ == "__main__":
    main()
