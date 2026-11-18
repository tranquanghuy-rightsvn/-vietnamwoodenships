# -*- coding: utf-8 -*-
"""Verify every internal href/src in the generated site resolves to a real file."""
import os, re, sys, urllib.parse
sys.stdout.reconfigure(encoding='utf-8')

ROOT = 'html'
pages, bad_links, bad_assets, ext = [], [], [], set()

for dirpath, _dirs, files in os.walk(ROOT):
    for f in files:
        if f.endswith('.html'):
            pages.append(os.path.join(dirpath, f))

def resolve(page, ref):
    ref = ref.split('#')[0].split('?')[0]
    if not ref:
        return None
    if re.match(r'^(https?:)?//|^(mailto|tel|javascript|data):', ref):
        ext.add(ref.split('?')[0][:70])
        return None
    ref = urllib.parse.unquote(ref)
    if ref.startswith('/'):
        t = os.path.join(ROOT, ref.lstrip('/'))
    else:
        t = os.path.join(os.path.dirname(page), ref)
    if ref.endswith('/'):
        t = os.path.join(t, 'index.html')
    return os.path.normpath(t)

# page links must be /slug/ — never slug.html, never /slug
bad_form = []

for page in pages:
    s = open(page, encoding='utf-8').read()
    for m in re.finditer(r'\s(?:href|action)="([^"]+)"', s):
        v = m.group(1).split('#')[0].split('?')[0]
        if v and not re.match(r'^(https?:)?//|^(mailto|tel|javascript|data):', v) and "'" not in v:
            last = v.rsplit('/', 1)[-1]
            if v.endswith('.html') or not v.startswith('/') or (last and '.' not in last):
                bad_form.append((page, m.group(1)))
        t = resolve(page, m.group(1))
        if t and not os.path.exists(t):
            bad_links.append((page, m.group(1)))
    for m in re.finditer(r'\s(?:src|data-full|data-img)="([^"]+)"', s):
        t = resolve(page, m.group(1))
        if t and not os.path.exists(t):
            bad_assets.append((page, m.group(1)))
    # background-image url() in inline styles
    for m in re.finditer(r'background-image:url\(&quot;([^&]+)&quot;\)', s):
        t = resolve(page, m.group(1))
        if t and not os.path.exists(t):
            bad_assets.append((page, m.group(1)))

print('pages           :', len(pages))
print('broken links    :', len(bad_links))
for p, r in bad_links[:15]:
    print('   ', p, '->', r)
print('non-/slug/ links:', len(bad_form))
for p, r in bad_form[:15]:
    print('   ', p, '->', r)
print('broken assets   :', len(bad_assets))
for p, r in bad_assets[:15]:
    print('   ', p, '->', r)
print('external refs   :', len(ext))
for x in sorted(ext):
    print('   ', x)

imgs = sum(len(fs) for _d, _s, fs in os.walk(os.path.join(ROOT, 'assets', 'img')))
print('local images    :', imgs)
