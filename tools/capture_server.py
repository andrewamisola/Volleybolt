#!/usr/bin/env python3
"""Serves the repo on :8090 and accepts POSTed canvas frames.

Usage: python3 tools/capture_server.py --out /path/to/frames
POST /save?name=fireball_0001.png with a data-URL body writes frames/fireball_0001.png
"""
import argparse, base64, os, re
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--port', type=int, default=8090)
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    class Handler(SimpleHTTPRequestHandler):
        def do_POST(self):
            u = urlparse(self.path)
            if u.path != '/save':
                self.send_error(404); return
            name = parse_qs(u.query).get('name', [''])[0]
            if not re.fullmatch(r'[A-Za-z0-9._-]+\.png', name):
                self.send_error(400, 'bad name'); return
            body = self.rfile.read(int(self.headers['Content-Length'])).decode('ascii')
            b64 = body.split(',', 1)[1] if ',' in body else body
            with open(os.path.join(args.out, name), 'wb') as f:
                f.write(base64.b64decode(b64))
            self.send_response(200); self.end_headers(); self.wfile.write(b'ok')
        def log_message(self, *a):  # keep terminal quiet during 60-frame bursts
            pass

    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()

if __name__ == '__main__':
    main()
