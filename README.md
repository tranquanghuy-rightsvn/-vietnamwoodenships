# hoatayviet.net — static clone

A hand-written HTML / CSS / JS clone of the **hoatayviet.net** home page, plus
generated category, product and search pages built from the site's full product
catalogue. No framework, no build step, no runtime dependencies.

## Run it

```bash
cd html
python -m http.server 8900
# http://127.0.0.1:8900/   (pages are /slug/ -> slug/index.html)
```

Any static host works — the output is plain files.

## Layout

```
html/                       the deliverable
  index.html                home page (the clone target)
  san-pham/                 all products, grouped by category
  tim-kiem/                 client-side search over products.json
  danh-muc/<slug>/          7 category listings
  sp/<slug>/                32 product pages
  gioi-thieu/ · lien-he/ · huong-dan-*/ · gio-hang/ · thanh-toan/ · tin-tuc/
  home/ · cart/ · about/ · …   English twin of every page above
  category/<slug>/ · product/<slug>/       English twins of danh-muc/ and sp/
  assets/
    css/style.css           ~980 lines, tokens first, then components
    js/main.js              sticky header, slider, menus, search, gallery, language menu
    img/                    217 images, mirrored from the original CDN
    data/products.json      catalogue used by the search page

scripts/                    reproducible pipeline
  mirror.py                 mirrors the original page for reference
  parse_home.py             home page -> sections + product cards
  crawl_products.py         32 product pages from the Wayback Machine
  parse_products.py         product pages -> products.json
  download_product_images.py
  build_site.py             renders every Vietnamese page, then calls build_en.py
  build_en.py               derives the English twin of each page (en_dict.json)
  lang_map.py               Vietnamese <-> English URL map (gio-hang.html -> cart.html)
  en_dict.json              Vietnamese -> English strings; add missing ones here
  check_site.py             link / asset integrity check
  cssgrep.py                pulls rules out of the original 441KB stylesheet

docs/research/
  DESIGN_TOKENS.md          colours, type, layout, breakpoints, motion
  BEHAVIORS.md              every interaction with its exact trigger + states
  KNOWN_ISSUES.md           bugs in the original that are reproduced, and how to fix each

_raw/                       captured source + intermediate JSON (not served)
_mirror/                    local copy of the original, for side-by-side diffing
```

## Rebuild

```bash
python3 scripts/build.py         # products + news from data/, then seo.py
python3 scripts/check_site.py    # verify every href/src resolves
```

## URLs

Every page lives at `<slug>/index.html` and every internal link is a
root-absolute directory URL with a trailing slash: `/`, `/gioi-thieu/`,
`/sp/victory/`, `/assets/css/style.css`. No `slug.html`, no `/slug`.
Vercel serves `html/` as-is (`vercel.json`: `trailingSlash: true` redirects
`/slug` -> `/slug/`). `scripts/restructure_urls.py` performs the conversion and
is safe to re-run after adding pages; `scripts/check_site.py` flags any link
not in `/slug/` form. Serve over HTTP (root-absolute links do not work from
`file://`).

## Content pipeline (CMS)

Products and news are managed in the admin (Google Apps Script CMS, see `GAS.md`).
The CMS writes JSON into `data/` through the GitHub API; GitHub Actions renders `html/`.

```
data/products.json            index: slug, slugEn, sku, cat, nameVi, nameEn, size, price,
                              image, image2, status, updatedAt  (order = display order)
data/products/<slug>.json     + priceNoteVi/En, metaVi/En, images[], introVi/En
data/news.json                index: slug, slugEn, tag, titleVi/En, descVi/En, cover, date, status
data/news/<slug>.json         + contentVi, contentEn
data/settings.json            general settings (CMS "Cài đặt chung"): logo, favicon, home slider,
                              company, address, phones, emails, map, footer text
data/news-images.json         Wikimedia Commons credits for /assets/img/news/* photos
templates/product-{vi,en}.html  product page design ({{PLACEHOLDERS}})
templates/news-{vi,en}.html     article page shell ({{MAIN}})
templates/news-en-empty.html    cards shown on /news/ while no article has an English version
```

`python3 scripts/build.py` (stdlib only, idempotent) renders:

- `/sp/<slug>/` and `/product/<slugEn>/` (English page only when `nameEn` is set);
- `/tin-tuc/<slug>/` and `/news/<slugEn>/` (only when `titleEn` is set) — table of
  contents (h2 ids added automatically), reading time, image sizes, photo credits,
  related articles;
- the product grids and article cards inside hand-made pages, between
  `<!-- build:NAME -->` / `<!-- /build:NAME -->` markers: `home1`…`home6` on `/` and
  `/home/` (curated order in `HOME_SECTIONS`, new products first), `all` on `/san-pham/`
  and `/products/`, `category` on every `/danh-muc/*/` and `/category/*/`, `news` on
  `/tin-tuc/` and `/news/`, `latest-news` on `/404.html`. Keep the markers when
  editing those pages;
- `html/assets/data/products(-en).json` (search) and `html/assets/js/catalog.js`;
- the general settings (`data/settings.json`) into every page, between
  `<!-- set:NAME -->` / `<!-- /set:NAME -->` markers (header top bar, logo, header phone, footer,
  home slider, contact cards + map, about-page contact) and into `data-set="phone"` /
  `data-set="email"` links and the favicon `<link>`s. Keep those markers when editing pages;
  `scripts/add_settings_markers.py` (idempotent) adds them to new pages;
- deletes pages of removed / hidden products and articles, then runs `scripts/seo.py`.

Hidden (`status: "hidden"`) items keep their data but get no page. Categories are a
fixed list (`CATEGORIES` in `build.py`, same as the CMS).

CI: `.github/workflows/build.yml` runs the build when `data/products.json`,
`data/news.json` or `data/settings.json` changes (the CMS always writes those last) and commits `html/`.

`scripts/migrate_to_data.py` did the one-time move from the hand-built pages to
`data/` + `templates/` (it refuses to run again once `data/products.json` exists).

## 404

`html/404.html` (site header/footer, search, category + article links,
noindex). Vercel serves it automatically for unknown URLs; `seo.py` skips it.

## SEO

`scripts/seo.py` rewrites one `<!-- seo:start --> … <!-- seo:end -->` block in
the `<head>` of every page in `html/` (idempotent — run it after any edit):

- meta description / robots, canonical, hreflang `vi` / `en` / `x-default`,
  Open Graph and Twitter card — all absolute `/slug/` URLs (`https://vietnamwoodenships.com/sp/victory/`)
- JSON-LD `@graph`: Organization, WebSite (+ SearchAction), the page
  (WebPage / AboutPage / ContactPage / CollectionPage / ItemPage), BreadcrumbList,
  Product (product pages, Offer only when a real price exists), ItemList (listings)
- `html/robots.txt` and `html/sitemap.xml` (hreflang alternates + product images)

Cart, checkout and search are `noindex, follow`
and left out of the sitemap. Domain: `SITE_URL=https://… python scripts/seo.py`.

## Fidelity

Measured against the original at a 1440px viewport, same machine, same fonts:

| | Original | Clone |
|---|---|---|
| Logo | `off 0, 200×100` | `off 0, 200×100` |
| Search block | `off 230, 582×40` | `off 230, 582×40` |
| Account / divider / cart | `948 · 983 · 998`, `112×44` | `948 · 983 · 998`, `112×44` |
| Mega menu | `off -2, 273×44`, list `273×274` | identical |
| Main nav | `off 276, 557×44`, first link `291` | identical |
| Header phone | `off 997, 113×45` | identical |
| Top bar height | `36` | `36` |
| Hero row | `1123×310`, cols `281` / `842` | identical |
| Section header | `1113×52`, chip `197×35` | identical |
| Product grid column | `281×326` | identical |
| Product card | `271×316`, media `271×271`, body `271×45` | identical |
| Sticky thresholds | stick `280`, release `37` | stick `280`, release `37` |

Responsive was checked at 1440 / 768 / 390 and matches at all three, including
the original's empty hero column between 550 and 849px.

## Notes

- The origin server was returning **HTTP 500 for every URL except the cached
  home page** during capture. Product data came from the Wayback Machine;
  images came from the live CDN. See `docs/research/KNOWN_ISSUES.md` §6.
- Five rendering bugs in the original are reproduced deliberately, each with a
  one-line fix documented in `KNOWN_ISSUES.md`. The most consequential: the
  mobile hamburger is white on white, so it is invisible.
- The one intentional deviation is loading Roboto / Roboto Condensed as
  webfonts, which the original declares but never links.
