#!/usr/bin/env python3
"""Emit a self-contained copy of brand/art-bible.html with all local images inlined."""
import base64, mimetypes, pathlib, re, sys

src = pathlib.Path('brand/art-bible.html')
out = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path('art-bible-inline.html')
html = src.read_text()

def inline(m):
    rel = m.group(2)
    p = src.parent / rel
    if not p.exists() or rel.startswith(('http', 'data:')):
        return m.group(0)
    mime = mimetypes.guess_type(p.name)[0] or 'application/octet-stream'
    return m.group(1) + f'data:{mime};base64,' + base64.b64encode(p.read_bytes()).decode() + m.group(3)

html = re.sub(r'''(src=["'])([^"']+)(["'])''', inline, html)
out.write_text(html)
print(out, len(html) // 1024, 'KB')
