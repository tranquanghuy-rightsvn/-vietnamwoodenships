#!/usr/bin/env python3
"""One-time (idempotent): put <!-- set:NAME --> markers around the parts of every page that
come from data/settings.json (Cài đặt chung in the CMS), so scripts/build.py can rewrite them.

    python3 scripts/add_settings_markers.py

Regions (see apply_settings() in build.py):
  set:topbar        phone + email in the desktop top bar
  set:topbar-m      phone in the mobile top bar
  set:logo          header logo link
  set:header-phone  phone link in the bottom nav bar
  set:footer        the 3 footer widgets (contact, map, about)
  set:slider        home page hero slider (/ and /home/)
  set:contact       address/phone/email cards on /lien-he/ and /contact/
  set:contact-map   map on /lien-he/ and /contact/
  set:about-contact company / address / phone / email on /gioi-thieu/ and /about/
Other links to the main phone / email (call-to-action buttons, "Gọi 0908 062 685" lines) get
data-set="phone" / data-set="email" instead.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PHONE_TEL = "tel:0908062685"
EMAIL_TO = "mailto:hoatayviet.modelship@gmail.com"


def wrap(s, name, pattern, f):
    """Wrap group 'body' of the first match of pattern with set:name markers."""
    if f"<!-- set:{name} -->" in s:
        return s, 0
    m = re.search(pattern, s, re.S)
    if not m:
        return s, 0
    a, b = m.span("body")
    return s[:a] + f"<!-- set:{name} -->" + s[a:b] + f"<!-- /set:{name} -->" + s[b:], 1


PATTERNS = [
    ("topbar", r'<ul class="topbar-nav hide-for-medium">\n(?P<body>\s*<li><span class="topbar-text">.*?)\n\s*</ul>'),
    ("topbar-m", r'<ul class="topbar-nav show-for-medium">\n(?P<body>.*?)\n\s*</ul>'),
    ("logo", r'<div class="header-col logo">\n(?P<body>.*?)\n\s*</div>'),
    ("header-phone", r'(?P<body><a class="header-phone".*?</a>)'),
    ("footer", r'<div class="footer-widgets">\n(?P<body>.*?)\n  </div>\n\n  <a class="back-to-top"'),
    ("slider", r'<div class="slider" data-slider[^>]*>\n(?P<body>.*?</div>)\n    </div>\n  </div>\n</div>'),
    ("contact", r'(?P<body><div class="contact-grid">.*?</div>\n  </div>)'),
    ("contact-map", r'(?P<body><iframe class="footer-map contact-map".*?</iframe>)'),
    ("about-contact", r'\n    (?P<body><p><strong>[^<]*</strong></p>\n    <p>(?:Địa chỉ|Address):.*?<p>Email:.*?</p>)'),
]


def tag_links(s):
    """data-set on remaining main phone/email links outside set: regions."""
    parts = re.split(r"(<!-- set:[\w-]+ -->.*?<!-- /set:[\w-]+ -->)", s, flags=re.S)
    n = 0
    for i in range(0, len(parts), 2):
        for href, key in ((PHONE_TEL, "phone"), (EMAIL_TO, "email")):
            new, k = re.subn(rf'<a ((?:class="[^"]*" )?)href="{re.escape(href)}">',
                             rf'<a \1href="{href}" data-set="{key}">', parts[i])
            parts[i] = new
            n += k
    return "".join(parts), n


def process(p):
    s = p.read_text(encoding="utf-8")
    done = []
    for name, pat in PATTERNS:
        s, k = wrap(s, name, pat, p)
        if k:
            done.append(name)
    s, n = tag_links(s)
    if n:
        done.append(f"{n} link(s)")
    if done:
        p.write_text(s, encoding="utf-8")
    return done


def main():
    files = sorted((ROOT / "templates").glob("*.html")) + sorted(
        f for f in (ROOT / "html").rglob("*.html")
        if not any(x in f.parts for x in ("admin", "vendor", "assets")))
    for f in files:
        done = process(f)
        if done:
            print(f"{f.relative_to(ROOT)}: {', '.join(done)}")


if __name__ == "__main__":
    sys.exit(main())
