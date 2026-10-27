"""Dependency-free local HTTP server; shared service with Flask."""
import json
import os
import hashlib
import mimetypes
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit, parse_qs
from database import init_db,get_stats,search_universities,catalogue_stats
from service import chat, recommend
from admissions import school_admissions, lookup
from ai_advisor import api_status
from trends import get_snapshot, request_refresh, start_worker
ROOT=Path(__file__).resolve().parent

class Handler(BaseHTTPRequestHandler):
    def send(self,body,status=200,content_type='application/json; charset=utf-8'):
        data=json.dumps(body,ensure_ascii=False).encode('utf-8') if isinstance(body,(dict,list)) else body
        self.send_response(status)
        self.send_header('Content-Type',content_type); self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store'); self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        path=urlsplit(self.path).path
        if path=='/': return self.send((ROOT/'templates/index.html').read_bytes(),content_type='text/html; charset=utf-8')
        if path=='/api/dev/revision' and os.environ.get('UNIGUIDE_DEV')=='1':
            watched=[*ROOT.glob('*.py'),*(ROOT/'static').glob('*.*'),*(ROOT/'templates').glob('*.html'),*(ROOT/'sql').glob('*.json')]
            revision=hashlib.sha256('|'.join(str(p.stat().st_mtime_ns) for p in sorted(watched) if p.is_file()).encode()).hexdigest()
            return self.send({'revision':revision})
        if path=='/api/ai/status': return self.send(api_status())
        if path=='/api/admissions':
            result=school_admissions(parse_qs(urlsplit(self.path).query).get('code',[''])[0])
            return self.send(result[0],result[1]) if isinstance(result,tuple) else self.send(result)
        if path=='/api/trends': return self.send(get_snapshot())
        if path=='/api/universities':
            query=parse_qs(urlsplit(self.path).query)
            return self.send({'universities':search_universities(query.get('region',[None])[0],query.get('field',[None])[0],limit=1000)})
        if path=='/api/stats': return self.send(catalogue_stats())
        if path=='/api/suggest': return self.send({'universities':search_universities(limit=3)})
        if path.startswith('/static/'):
            candidate=(ROOT/path.lstrip('/')).resolve()
            static_root=(ROOT/'static').resolve()
            if static_root not in candidate.parents or not candidate.is_file(): return self.send({'error':'Không tìm thấy tệp.'},404)
            mime=mimetypes.guess_type(candidate.name)[0] or 'application/octet-stream'
            return self.send(candidate.read_bytes(),content_type=mime)
        if path in ('/static/style.css','/static/script.js','/static/theme.js'):
            return self.send((ROOT/path.lstrip('/')).read_bytes(),content_type='text/css; charset=utf-8' if path.endswith('.css') else 'text/javascript; charset=utf-8')
        return self.send({'error':'Không tìm thấy trang.'},404)
    def do_POST(self):
        path=urlsplit(self.path).path
        origin=self.headers.get('Origin')
        if origin and urlsplit(origin).netloc!=self.headers.get('Host'):
            return self.send({'error':'Nguồn yêu cầu không hợp lệ.'},403)
        if path=='/api/trends/refresh':
            request_refresh(force=True)
            return self.send(get_snapshot(),202)
        if path not in ('/chat','/api/recommend','/api/admissions/lookup'): return self.send({'error':'Không tìm thấy API.'},404)
        try:
            size=int(self.headers.get('Content-Length','0'))
            if not 0<size<=98304: return self.send({'error':'Dữ liệu quá lớn hoặc không hợp lệ.'},400)
            result={'/chat':chat,'/api/recommend':recommend,'/api/admissions/lookup':lookup}[path](json.loads(self.rfile.read(size)))
            if isinstance(result,tuple): return self.send(result[0],result[1])
            self.send(result)
        except (ValueError,UnicodeError): self.send({'error':'JSON không hợp lệ.'},400)
        except Exception: self.send({'error':'Không thể xử lý yêu cầu.'},500)

if __name__=='__main__':
    init_db(); start_worker(); port=int(os.environ.get('PORT','5001'))
    print(f'UniGuideBot: http://127.0.0.1:{port} - Ctrl+C de dung',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
