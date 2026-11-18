#!/usr/bin/env python3
"""Build the news articles: content/tin-tuc/<slug>.html -> html/tin-tuc/<slug>/index.html

Each source file starts with a JSON front-matter comment

    <!--meta
    {"title": ..., "h1": ..., "description": ..., "date": "YYYY-MM-DD",
     "tag": ..., "cover": "/assets/...", "coverAlt": ..., "keywords": [...]}
    -->

followed by the article body (h2 with ids, p, figure, table, div.faq ...).

The page shell (header, footer, menus) is taken from html/tin-tuc/index.html so
articles always match the rest of the site. The script also:
  - adds width/height + lazy loading to every image,
  - appends the author / licence credit to web images (content/tin-tuc/images.json),
  - builds the table of contents, reading time and related-articles block,
  - rewrites the card grid on /tin-tuc/ to link to the articles.
Run scripts/seo.py afterwards for meta / canonical / JSON-LD / sitemap.
"""
import html as H
import json
import re
import subprocess
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "html"
SRC = ROOT / "content" / "tin-tuc"
LISTING = SITE / "tin-tuc" / "index.html"
BRAND = "Vietnam Wooden Ships"

# order on the listing page
ORDER = [
    "chon-mo-hinh-tau-du-lich-du-thuyen",
    "mo-hinh-thuyen-buom-tau-huyen-thoai",
    "mo-hinh-tau-cho-hang",
    "noi-that-go-thu-cong",
    "kinh-nghiem-mua-mo-hinh-thuyen-go",
    "bao-quan-mo-hinh-thuyen-go",
]

TAG = re.compile(r"<[^>]+>")
_size_cache = {}


def e(s):
    return H.escape(s or "", quote=True)


def text(s):
    return re.sub(r"\s+", " ", H.unescape(TAG.sub(" ", s or ""))).strip()


def img_size(src):
    if src not in _size_cache:
        out = subprocess.run(["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(SITE / src.lstrip("/"))],
                             capture_output=True, text=True).stdout
        wh = [int(x) for x in re.findall(r"pixel(?:Width|Height): (\d+)", out)]
        _size_cache[src] = tuple(wh) if len(wh) == 2 else None
    return _size_cache[src]


def load(path):
    raw = path.read_text(encoding="utf-8")
    m = re.match(r"\s*<!--meta\s*(\{.*?\})\s*-->", raw, re.S)
    if not m:
        raise SystemExit(f"{path}: missing <!--meta {{...}} --> header")
    meta = json.loads(m.group(1))
    meta["slug"] = path.stem
    meta["body"] = raw[m.end():].strip()
    meta["url"] = f"/tin-tuc/{path.stem}/"
    return meta


def fix_images(body, credits):
    def img(m):
        tag = m.group(0)
        src = re.search(r'src="([^"]+)"', tag).group(1)
        attrs = ""
        if "width=" not in tag:
            wh = img_size(src)
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
        span = (f' <span class="credit">Ảnh: <a href="{e(c["page"])}" rel="nofollow noopener" target="_blank">'
                f'{e(c["author"])}</a> / Wikimedia Commons, {e(c["license"])}</span>')
        if "</figcaption>" in fig:
            return fig.replace("</figcaption>", span + "</figcaption>", 1)
        return fig.replace("</figure>", f"<figcaption>{span.strip()}</figcaption></figure>", 1)

    body = re.sub(r"<figure\b.*?</figure>", credit, body, flags=re.S)
    # external links open in a new tab
    body = re.sub(r'<a href="(https?://[^"]+)"(?![^>]*rel=)', r'<a href="\1" rel="noopener" target="_blank"', body)
    return body


def toc(body):
    items = re.findall(r'<h2 id="([^"]+)">(.*?)</h2>', body, re.S)
    if len(items) < 3:
        return ""
    lis = "".join(f'<li><a href="#{i}">{e(text(t))}</a></li>' for i, t in items)
    return f'<nav class="toc" aria-label="Mục lục"><p class="toc-title">Mục lục bài viết</p><ol>{lis}</ol></nav>'


def card(a, heading="h3"):
    return (f'<article class="news-card">\n'
            f'      <a class="news-media" href="{a["url"]}"><img src="{e(a["cover"])}" alt="{e(a["coverAlt"])}" loading="lazy" decoding="async"></a>\n'
            f'      <div class="news-body">\n'
            f'        <span class="news-tag">{e(a["tag"])}</span>\n'
            f'        <{heading}><a href="{a["url"]}">{e(a["h1"])}</a></{heading}>\n'
            f'        <p>{e(a["description"])}</p>\n'
            f'        <a class="news-more" href="{a["url"]}" aria-label="Đọc bài: {e(a["h1"])}">Đọc tiếp</a>\n'
            f'      </div>\n'
            f'    </article>')


def vn_date(d):
    y, m, dd = d.split("-")
    return f"{dd}/{m}/{y}"


def page(a, shell_head, shell_top, shell_bottom, related, credits):
    body = fix_images(a["body"], credits)
    # if the cover photo also appears as a figure in the body, show it once:
    # as the cover, carrying that figure's caption (and credit)
    cover_caption = ""
    for fig in re.findall(r"<figure\b.*?</figure>", body, flags=re.S):
        if f'src="{a["cover"]}"' in fig:
            cap = re.search(r"<figcaption>.*?</figcaption>", fig, re.S)
            cover_caption = cap.group(0) if cap else ""
            body = body.replace(fig, "", 1)
            break
    if not cover_caption:
        c = credits.get(Path(a["cover"]).stem) if "/assets/img/news/" in a["cover"] else None
        if c:
            cover_caption = fix_images(f'<figure><img src="{a["cover"]}" alt=""></figure>', credits)
            cover_caption = re.search(r"<figcaption>.*?</figcaption>", cover_caption, re.S).group(0)
    words = len(text(body).split())
    minutes = max(1, round(words / 220))
    cover_wh = img_size(a["cover"])
    cover_dim = f' width="{cover_wh[0]}" height="{cover_wh[1]}"' if cover_wh else ""

    head = shell_head
    head = re.sub(r"\n?<!-- seo:start -->.*?<!-- seo:end -->", "", head, flags=re.S)
    head = re.sub(r'\n?<meta (?:property="article:|name="keywords")[^>]*>', "", head)
    head = re.sub(r"<title>.*?</title>", f"<title>{e(a['title'])}</title>", head, flags=re.S)
    head = head.replace(
        f"<title>{e(a['title'])}</title>",
        f"<title>{e(a['title'])}</title>\n"
        f'<meta name="description" content="{e(a["description"])}">\n'
        f'<meta name="keywords" content="{e(", ".join(a.get("keywords", [])))}">\n'
        f'<meta property="article:published_time" content="{a["date"]}">\n'
        f'<meta property="article:modified_time" content="{a.get("modified", a["date"])}">\n'
        f'<meta property="article:section" content="{e(a["tag"])}">', 1)

    rel = "\n    ".join(card(r) for r in related)
    main = f'''<main id="main">
<div class="page-wrap"><div class="container article-wrap">
  <nav class="breadcrumb" aria-label="Breadcrumb"><a href="/">Trang chủ</a><span>/</span><a href="/tin-tuc/">Tin tức</a><span>/</span>{e(a["h1"])}</nav>
  <article class="article">
    <header class="article-head">
      <span class="news-tag">{e(a["tag"])}</span>
      <h1>{e(a["h1"])}</h1>
      <p class="article-meta"><span>{BRAND}</span><span aria-hidden="true">·</span><time datetime="{a["date"]}">{vn_date(a["date"])}</time><span aria-hidden="true">·</span><span>{minutes} phút đọc</span></p>
    </header>
    <figure class="article-cover"><img src="{e(a["cover"])}" alt="{e(a["coverAlt"])}"{cover_dim} fetchpriority="high" decoding="async">{cover_caption}</figure>
    {toc(body)}
    <div class="article-body">
{body}
    </div>
  </article>
  <aside class="related" aria-labelledby="related-title">
    <h2 class="related-title" id="related-title">Bài viết liên quan</h2>
    <div class="news-grid">
    {rel}
    </div>
  </aside>
</div></div>
</main>'''
    return head + shell_top + main + shell_bottom, words


def main():
    credits = json.loads((SRC / "images.json").read_text(encoding="utf-8")) if (SRC / "images.json").exists() else {}
    arts = {p.stem: load(p) for p in SRC.glob("*.html")}
    order = [s for s in ORDER if s in arts] + sorted(s for s in arts if s not in ORDER)
    listing = LISTING.read_text(encoding="utf-8")

    i_head = listing.index("</head>")
    shell_head = listing[:i_head]
    i_main, j_main = listing.index('<main id="main">'), listing.index("</main>") + len("</main>")
    shell_top = listing[i_head:i_main]
    shell_bottom = listing[j_main:]

    for n, slug in enumerate(order):
        a = arts[slug]
        same_tag = [arts[s] for s in order if s != slug and arts[s]["tag"] == a["tag"]]
        others = [arts[order[(n + k) % len(order)]] for k in range(1, len(order))]
        related = (same_tag + [o for o in others if o not in same_tag])[:3]
        out, words = page(a, shell_head, shell_top, shell_bottom, related, credits)
        dst = SITE / "tin-tuc" / slug / "index.html"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(out, encoding="utf-8")
        links = len(set(re.findall(r'href="(/[^"#]*)"', a["body"])))
        print(f"{a['url']:48} {words:5} words  {links:3} internal links")

    # listing page: cards now link to the articles
    grid = '<div class="news-grid">' + "".join(card(arts[s]) for s in order) + "</div>"
    listing = re.sub(r'<div class="news-grid">.*?</div>\s*(?=<p class="news-cta">)', grid + "\n  ", listing, flags=re.S)
    LISTING.write_text(listing, encoding="utf-8")


if __name__ == "__main__":
    main()
