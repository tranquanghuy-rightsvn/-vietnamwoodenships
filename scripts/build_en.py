# -*- coding: utf-8 -*-
"""Generate the English twin of every Vietnamese page.

Runs after build_site.py has written the Vietnamese pages (build_site.py calls
main() at the end, or run `python scripts/build_en.py` on its own).

    gio-hang.html  ->  cart.html
    sp/ban-go/     ->  product/wooden-table/

The Vietnamese HTML is the source: text nodes and a few attributes are
translated through scripts/en_dict.json, internal links are re-pointed at the
English pages, and the language switcher is wired to the page's twin.
Nothing is translated in the browser.

Run with --report to list Vietnamese text that still has no translation.
"""
import os, re, sys, json, html, posixpath
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import lang_map

ROOT = 'site'
HERE = os.path.dirname(os.path.abspath(__file__))

DICT = json.load(open(os.path.join(HERE, 'en_dict.json'), encoding='utf-8'))
DICT.update(lang_map.PRODUCT_NAMES_EN)
DICT.update(lang_map.CATEGORY_NAMES_EN)

# (regex, replacement) - groups are looked up in DICT first
PATTERNS = [
    (r'^(\d+) sản phẩm$', r'\1 products'),
    (r'^Xem tất cả \((\d+)\)$', r'View all (\1)'),
    (r'^Xem (.+)$', r'View \1'),
    (r'^Xóa (.+) khỏi giỏ hàng$', r'Remove \1 from cart'),
    (r'^Thêm (.+) vào giỏ hàng$', r'Add \1 to cart'),
    (r'^Kết quả cho “(.*)”$', r'Results for “\1”'),
    (r'^Ảnh (\d+)$', r'Image \1'),
    (r'^Danh mục (.+) tại Vietnam Wooden Ships\.$', r'Category \1 at Vietnam Wooden Ships.'),
    (r'^Toàn bộ (\d+) sản phẩm của Vietnam Wooden Ships\.$', r'All \1 products of Vietnam Wooden Ships.'),
    (r'^Gọi ngay (.+)$', r'Call \1 now'),
    # meta description of a product: "NAME — Category. 80L x 10W (cm)"
    (r'^(.+?) — ([^.]+)\.(.*)$', r'\1 — \2.\3'),
    (r'^GIÁ SỈ: (.+) VND \( ĐƠN HÀNG ÍT NHẤT (\d+) CÁI \)$',
     r'WHOLESALE PRICE: \1 VND (MINIMUM ORDER \2 PCS)'),
]
PATTERNS = [(re.compile(a), b) for a, b in PATTERNS]

VI_CHARS = re.compile(r'[àáạảãâầấậẩẫăằắặẳẵèéẹẻẽêềếệểễìíịỉĩòóọỏõôồốộổỗơờớợởỡùúụủũưừứựửữỳýỵỷỹđ'
                      r'ÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸĐ]')

TEXT_ATTRS = {'placeholder', 'aria-label', 'title', 'alt', 'data-name', 'data-price-text',
              'data-alt'}
LINK_ATTRS = {'href', 'action'}


def norm(s):
    return re.sub(r'\s+', ' ', s).strip()


def tr(raw):
    """Translate one string; None when nothing applies."""
    s = norm(raw)
    if not s:
        return None
    if s in DICT:
        return DICT[s]
    for rx, out in PATTERNS:
        m = rx.match(s)
        if m:
            return rx.sub(lambda mm: re.sub(r'\\(\d)', lambda g: DICT.get(mm.group(int(g.group(1))),
                          mm.group(int(g.group(1)))), out), s)
    m = re.match(r'^(.*) - Vietnam Wooden Ships$', s)
    if m:
        return (tr(m.group(1)) or m.group(1)) + ' - Vietnam Wooden Ships'
    m = re.match(r'^(.*) - Xưởng Sản Xuất Thuyền Mỹ Nghệ Vietnam Wooden Ships$', s)
    if m:
        return (tr(m.group(1)) or m.group(1)) + ' - Vietnam Wooden Ships Art Boat Workshop'
    return None


MISSING = {}   # untranslated Vietnamese string -> pages


def tx(raw, page):
    """Translate text/attribute content (already unescaped); keep its edge whitespace."""
    t = tr(raw)
    if t is None:
        if VI_CHARS.search(raw) and norm(raw) != 'Tiếng Việt':
            MISSING.setdefault(norm(raw), set()).add(page)
        return raw
    lead = re.match(r'^\s*', raw).group(0)
    trail = re.search(r'\s*$', raw).group(0)
    return lead + t + trail


# --------------------------------------------------------------------------
TOKEN = re.compile(r'(<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>|<!--.*?-->|<[^>]+>)', re.S)
ATTR = re.compile(r'''([\w:-]+)\s*=\s*"([^"]*)"''')
EXTERNAL = re.compile(r'^(?:[a-z][a-z0-9+.-]*:|//|#)', re.I)


def map_link(value, vi_path, en_path):
    """Re-point a relative link to a Vietnamese page at its English twin."""
    if not value or EXTERNAL.match(value):
        return value
    m = re.match(r'^([^?#]*)(.*)$', value)
    path, tail = m.group(1), m.group(2)
    if not path.endswith('.html'):
        return value
    target = posixpath.normpath(posixpath.join(posixpath.dirname(vi_path), path))
    en = lang_map.PATH_MAP.get(target)
    if not en:
        return value
    return lang_map.rel(en, en_path) + tail


def do_tag(tag, vi_path, en_path):
    name = re.match(r'<\s*([\w:-]+)', tag)
    if not name:
        return tag
    tname = name.group(1).lower()

    # language switcher: one link per language, the English one is "current"
    if tname == 'a' and 'data-lang=' in tag:
        lang = re.search(r'data-lang="(\w+)"', tag).group(1)
        target = vi_path if lang == 'vi' else en_path
        tag = re.sub(r'href="[^"]*"', 'href="%s"' % lang_map.rel(target, en_path), tag)
        tag = re.sub(r'\s*aria-current="[^"]*"', '', tag)
        if lang == 'en':
            tag = tag[:-1] + ' aria-current="true">'
        return tag
    if tname == 'link' and 'rel="alternate"' in tag:
        lang = re.search(r'hreflang="(\w+)"', tag).group(1)
        target = vi_path if lang == 'vi' else en_path
        return re.sub(r'href="[^"]*"', 'href="%s"' % lang_map.rel(target, en_path), tag)

    if tname == 'html':
        return re.sub(r'lang="vi"', 'lang="en"', tag)

    is_desc = tname == 'meta' and 'name="description"' in tag

    def attr(m):
        k, v = m.group(1), m.group(2)
        kl = k.lower()
        if kl in LINK_ATTRS:
            return '%s="%s"' % (k, map_link(html.unescape(v), vi_path, en_path))
        if tname == 'option' and kl == 'value' and v in lang_map.CATEGORY_SLUGS:
            return '%s="%s"' % (k, lang_map.CATEGORY_SLUGS[v])
        if kl in TEXT_ATTRS or (is_desc and kl == 'content'):
            return '%s="%s"' % (k, html.escape(tx(html.unescape(v), en_path), quote=True))
        return m.group(0)

    return ATTR.sub(attr, tag)


SEARCH_JS = [
    ("fetch('assets/data/products.json')", "fetch('assets/data/products-en.json')"),
    ("'sp/' + p.slug + '/index.html'", "'product/' + p.slug + '/index.html'"),
    ("data-slug=\"' + esc(p.slug)", "data-slug=\"' + esc(p.cartSlug)"),
    ("'Kết quả cho “' + term + '”'", "'Results for “' + term + '”'"),
    ("'Tất cả sản phẩm'", "'All products'"),
    ("aria-label=\"Thêm ' + esc(p.name) + ' vào giỏ hàng\"", "aria-label=\"Add ' + esc(p.name) + ' to cart\""),
]


def do_script(tok, vi_path):
    if 'src=' in tok[:200]:
        # every page loads cart.js; give it the English catalogue first
        if 'assets/js/cart.js' in tok:
            src = re.search(r'src="([^"]*)cart\.js"', tok).group(1)
            return '<script src="%scatalog.js"></script>\n%s' % (src, tok)
        return tok
    if 'search-results' in tok:
        for a, b in SEARCH_JS:
            if a not in tok:
                raise SystemExit('search script changed, cannot translate: ' + a)
            tok = tok.replace(a, b)
    return tok


def translate_page(vi_path):
    en_path = lang_map.PATH_MAP[vi_path]
    src = open(os.path.join(ROOT, vi_path), encoding='utf-8').read()
    out = []
    for tok in TOKEN.split(src):
        if not tok:
            continue
        if tok.startswith('<!--') or tok.startswith('<style'):
            out.append(tok)
        elif tok.startswith('<script'):
            out.append(do_script(tok, vi_path))
        elif tok.startswith('<'):
            out.append(do_tag(tok, vi_path, en_path))
        else:
            out.append(html.escape(tx(html.unescape(tok), en_path), quote=False))
    full = os.path.join(ROOT, en_path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    open(full, 'w', encoding='utf-8').write(''.join(out))


def write_data():
    prods = json.load(open(os.path.join(ROOT, 'assets/data/products.json'), encoding='utf-8'))
    en = []
    for p in prods:
        q = dict(p)
        q['slug'] = lang_map.PRODUCT_SLUGS[p['slug']]
        q['cartSlug'] = p['slug']            # the cart is keyed by the Vietnamese slug
        q['name'] = tr(p['name']) or p['name']
        q['price'] = tr(p['price']) or p['price']
        q['category'] = tr(p['category']) or p['category']
        q['categorySlug'] = lang_map.CATEGORY_SLUGS.get(p['categorySlug'], p['categorySlug'])
        en.append(q)
    json.dump(en, open(os.path.join(ROOT, 'assets/data/products-en.json'), 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)

    # catalogue for cart.js: Vietnamese slug -> English name + product URL
    cat = {p['slug']: {'name': (tr(p['name']) or p['name']),
                       'slug': lang_map.PRODUCT_SLUGS[p['slug']]} for p in prods}
    open(os.path.join(ROOT, 'assets/js/catalog.js'), 'w', encoding='utf-8').write(
        '/* generated by scripts/build_en.py - English names / URLs of the products,\n'
        '   keyed by the Vietnamese slug the cart stores. */\n'
        'window.HTY_CATALOG = %s;\n' % json.dumps(cat, ensure_ascii=False, indent=1))


def main(report=False):
    MISSING.clear()
    for vi_path in lang_map.PATH_MAP:
        translate_page(vi_path)
    write_data()
    print('english pages written:', len(lang_map.PATH_MAP))
    if MISSING:
        print('untranslated Vietnamese strings:', len(MISSING))
        if report or '--report' in sys.argv:
            for s, pages in sorted(MISSING.items()):
                print('  %r  (%d page(s), e.g. %s)' % (s, len(pages), sorted(pages)[0]))
    return len(MISSING)


if __name__ == '__main__':
    main(report=True)
