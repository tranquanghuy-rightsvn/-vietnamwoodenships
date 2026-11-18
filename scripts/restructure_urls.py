#!/usr/bin/env python3
"""Move every page to <slug>/index.html and make every internal URL a
root-absolute directory URL with a trailing slash.

    about.html             -> about/index.html        linked as /about/
    sp/foo/index.html      (stays)                    linked as /sp/foo/
    index.html             (stays)                    linked as /
    ../../assets/x.css     -> /assets/x.css

Safe to re-run: pages already in <slug>/index.html form are left in place and
links already in /slug/ form are unchanged.
"""
import re
from pathlib import Path
from posixpath import dirname, join, normpath

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "html"
ATTR = re.compile(r'(\b(?:href|src|action|data-img|data-full)=")([^"]*)(")')
STYLE_URL = re.compile(r'(url\(&quot;)([^&]*)(&quot;\))')
SKIP = ("http:", "https:", "//", "#", "mailto:", "tel:", "data:", "javascript:")
JS_CHARS = "'+{<"  # value is a JS string fragment, not a URL


def to_url(site_path):
    """'/about.html' -> '/about/', '/sp/x/index.html' -> '/sp/x/', '/assets/a.gif' unchanged."""
    if site_path.endswith("/index.html"):
        return site_path[: -len("index.html")]
    if site_path.endswith(".html"):
        return site_path[: -len(".html")] + "/"
    if not site_path.endswith("/") and "." not in site_path.rsplit("/", 1)[-1]:
        return site_path + "/"          # /about -> /about/
    return site_path


def clean(val, page_rel, root_relative=False):
    if not val or val.startswith(SKIP) or any(c in val for c in JS_CHARS):
        return val
    m = re.match(r"([^?#]*)(.*)$", val)
    path, tail = m.group(1), m.group(2)
    if not path:
        return val
    if not path.startswith("/"):
        base = "/" if root_relative else "/" + dirname(page_rel)
        path = normpath(join(base, path))
    return to_url(path) + tail


JS_FIXES = [
    ("fetch('assets/", "fetch('/assets/"),
    ("'sp/' + p.slug + '/index.html'", "'/sp/' + p.slug + '/'"),
    ("'product/' + p.slug + '/index.html'", "'/product/' + p.slug + '/'"),
    ('<img src="\' + p.thumb', '<img src="/\' + p.thumb'),
    ('data-img="\' + esc(p.thumb)', 'data-img="/\' + esc(p.thumb)'),
]


def rewrite_page(f, page_rel):
    src = f.read_text(encoding="utf-8")

    def attr(m):
        root_rel = m.group(1).startswith("data-img")   # cart image paths are site-root relative
        return m.group(1) + clean(m.group(2), page_rel, root_rel) + m.group(3)

    out = ATTR.sub(attr, src)
    out = STYLE_URL.sub(lambda m: m.group(1) + clean(m.group(2), page_rel) + m.group(3), out)
    for a, b in JS_FIXES:
        out = out.replace(a, b)
    if out != src:
        f.write_text(out, encoding="utf-8")


def main():
    # 1. rewrite links, resolved against each page's *current* location
    for f in SITE.rglob("*.html"):
        rewrite_page(f, f.relative_to(SITE).as_posix())
    # 2. move foo.html -> foo/index.html
    moved = 0
    for f in sorted(SITE.rglob("*.html")):
        if f.name == "index.html":
            continue
        dest = f.with_suffix("") / "index.html"
        dest.parent.mkdir(parents=True, exist_ok=True)
        f.rename(dest)
        moved += 1
    # 3. JS that builds URLs at runtime
    js = SITE / "assets" / "js"
    cart = js / "cart.js"
    s = cart.read_text(encoding="utf-8")
    s = (s.replace("product: 'product/'", "product: '/product/'")
          .replace("product: 'sp/'", "product: '/sp/'")
          .replace(" + '/index.html';", " + '/';"))
    if "function imgUrl" not in s:
        s = s.replace(
            "  function each(list, fn)",
            "  // carts saved before the move hold 'assets/...' paths\n"
            "  function imgUrl(src) { return src && !/^(\\/|https?:|data:)/.test(src) ? '/' + src : src; }\n\n"
            "  function each(list, fn)", 1)
        s = s.replace("img.src = i.img;", "img.src = imgUrl(i.img);")
    cart.write_text(s, encoding="utf-8")
    main_js = js / "main.js"
    s = main_js.read_text(encoding="utf-8")
    main_js.write_text(s.replace("|| 'tim-kiem.html')", "|| '/tim-kiem/')"), encoding="utf-8")
    print("moved", moved, "pages")


if __name__ == "__main__":
    main()
