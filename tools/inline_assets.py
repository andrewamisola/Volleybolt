#!/usr/bin/env python3
"""Emit a self-contained copy of an art-bible-style page with all local assets inlined.

Inlines both HTML src="..." attributes and CSS url(...) references (the hero
background is a CSS url). External (http/data:) refs and missing files are
left untouched. Note: external webfont <link>s are NOT handled here — the
artifact host blocks external requests, so fonts must be inlined as
@font-face data URIs by the publish step (or the fallback accepted).

Usage: python3 tools/inline_assets.py [OUT] [SRC]
  OUT defaults to art-bible-inline.html, SRC to brand/art-bible.html
"""
import base64, mimetypes, pathlib, re, sys

out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path('art-bible-inline.html')
src = pathlib.Path(sys.argv[2]) if len(sys.argv) > 2 else pathlib.Path('brand/art-bible.html')
html = src.read_text()

def to_data_uri(rel):
    if rel.startswith(('http', 'data:', '//')):
        return None
    p = src.parent / rel
    if not p.exists():
        return None
    mime = mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
    return f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode()

def inline_src(m):
    uri = to_data_uri(m.group(2))
    return m.group(1) + uri + m.group(3) if uri else m.group(0)

def inline_url(m):
    uri = to_data_uri(m.group(2))
    return f"url('{uri}')" if uri else m.group(0)

html = re.sub(r'''(src=["'])([^"']+)(["'])''', inline_src, html)
html = re.sub(r'''url\((['"]?)([^'")]+)\1\)''', inline_url, html)
out.write_text(html)
print(out, len(html) // 1024, 'KB')
