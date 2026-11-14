#!/usr/bin/env python3
"""每次發布前執行：產生每章 PDF（pdf/<id>.pdf）與全書 PDF（pdf/book.pdf）。
需要：playwright（Python）、Google Chrome、pypdf。用法：python3 tools/build_pdfs.py"""
import json, os, sys, hashlib, threading, functools, http.server, socketserver
from playwright.sync_api import sync_playwright

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'pdf')
os.makedirs(OUT, exist_ok=True)
chapters = json.load(open(os.path.join(ROOT, 'content/chapters.json'), encoding='utf-8'))['chapters']
# 只重新產生內容有變的章節（加 --force 全部重做）
HF = os.path.join(OUT, 'hashes.json')
old = json.load(open(HF)) if os.path.exists(HF) and '--force' not in sys.argv else {}
shared = open(os.path.join(ROOT, 'content/diagrams.json'), 'rb').read() + open(os.path.join(ROOT, 'content/chapters.json'), 'rb').read()
def h(c): return hashlib.sha256(open(os.path.join(ROOT, c['file']), 'rb').read() + shared).hexdigest()
new = {c['id']: h(c) for c in chapters}
todo = [c for c in chapters if old.get(c['id']) != new[c['id']] or not os.path.exists(os.path.join(OUT, c['id'] + '.pdf'))]
if not todo:
    print('沒有章節變動，不需要重新產生 PDF'); sys.exit(0)

Handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=ROOT)
Handler.log_message = lambda *a: None
srv = socketserver.TCPServer(('127.0.0.1', 0), Handler)
port = srv.server_address[1]
threading.Thread(target=srv.serve_forever, daemon=True).start()

FOOT = '<div style="font-size:8px;width:100%;text-align:center;color:#777">老陳的原始佛學指南：理性修佛篇 · {label} · <span class="pageNumber"></span>/<span class="totalPages"></span></div>'
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome')
    ctx = b.new_context(viewport={'width': 800, 'height': 1100}, service_workers='block')
    pg = ctx.new_page()
    pg.goto('http://127.0.0.1:%d/#%s' % (port, chapters[0]['id'])); pg.wait_for_timeout(3000)
    pg.emulate_media(media='print')
    files = []
    for c in todo:
        pg.evaluate("location.hash = '%s'" % c['id']); pg.wait_for_timeout(500)
        f = os.path.join(OUT, c['id'] + '.pdf')
        pg.pdf(path=f, format='A4', print_background=False, display_header_footer=True,
               header_template='<span></span>', footer_template=FOOT.format(label=c['label']),
               margin={'top': '16mm', 'bottom': '16mm', 'left': '14mm', 'right': '14mm'})
        files.append(f); print('ok', c['id'])
    b.close()
# 全書：一次排版（字型只嵌入一次，檔案比較小）
with sync_playwright() as p:
    b = p.chromium.launch(executable_path='/usr/bin/google-chrome')
    ctx = b.new_context(viewport={'width': 800, 'height': 1100}, service_workers='block')
    pg = ctx.new_page()
    pg.goto('http://127.0.0.1:%d/?printall=1#%s' % (port, chapters[0]['id'])); pg.wait_for_timeout(4000)
    pg.emulate_media(media='print')
    raw = os.path.join(OUT, 'book-raw.pdf')
    pg.pdf(path=raw, format='A4', display_header_footer=True, header_template='<span></span>',
           footer_template=FOOT.format(label='全書'), margin={'top': '16mm', 'bottom': '16mm', 'left': '14mm', 'right': '14mm'})
    b.close()
# 壓縮
import subprocess
for f in files + [raw]:
    tmp = f + '.tmp'
    subprocess.run(['qpdf', '--object-streams=generate', '--recompress-flate', '--compression-level=9', f, tmp], check=True)
    os.replace(tmp, f)
os.replace(raw, os.path.join(OUT, 'book.pdf'))
json.dump(new, open(HF, 'w'), indent=1)
srv.shutdown()
print('book.pdf done')
