import os
from flask import Flask,request,jsonify,send_from_directory
from database import init_db,get_stats,search_universities,catalogue_stats
from service import chat, recommend
from admissions import school_admissions, lookup
from ai_advisor import api_status
from trends import get_snapshot, request_refresh, start_worker
app=Flask(__name__)
# A small process-local throttle protects public AI routes; no chat/profile is stored.
import threading,time
from collections import deque
_hits={};_rate_lock=threading.Lock()
@app.before_request
def limit_public_ai_requests():
    if not os.environ.get('VERCEL') or request.method!='POST' or request.path not in ('/chat','/api/recommend','/api/admissions/lookup'):return
    identity=request.headers.get('x-forwarded-for',request.remote_addr or 'unknown').split(',')[0].strip()
    now=time.monotonic()
    with _rate_lock:
        for key in list(_hits):
            if not _hits[key] or now-_hits[key][-1]>60:del _hits[key]
        events=_hits.setdefault(identity,deque())
        while events and now-events[0]>60:events.popleft()
        if len(events)>=8:return jsonify({'error':'Bạn đã gửi nhiều yêu cầu liên tiếp. Vui lòng đợi một phút rồi thử lại.'}),429,{'Retry-After':'60'}
        events.append(now)

app.config['MAX_CONTENT_LENGTH']=98304
init_db()
start_worker()
@app.get('/')
def index(): return send_from_directory('templates','index.html')
@app.post('/chat')
def answer():
    result=chat(request.get_json(silent=True))
    return (jsonify(result[0]),result[1]) if isinstance(result,tuple) else jsonify(result)
@app.get('/api/stats')
def stats(): return jsonify(catalogue_stats())
@app.get('/api/suggest')
def suggest(): return jsonify({'universities':search_universities(limit=3)})
@app.get('/api/universities')
def universities(): return jsonify({'universities':search_universities(request.args.get('region'),request.args.get('field'),limit=1000,ownership=request.args.get('ownership'))})
@app.get('/api/trends')
def trends():
    if os.environ.get('VERCEL'):request_refresh(synchronous=True,rss_only=True)
    return jsonify(get_snapshot())
@app.post('/api/trends/refresh')
def refresh():
    request_refresh(force=True,synchronous=bool(os.environ.get('VERCEL')),rss_only=bool(os.environ.get('VERCEL')))
    return jsonify(get_snapshot()),202
@app.post('/api/recommend')
def recommendation():
    result=recommend(request.get_json(silent=True))
    return (jsonify(result[0]),result[1]) if isinstance(result,tuple) else jsonify(result)
@app.get('/api/ai/status')
def ai_health(): return jsonify(api_status())
@app.before_request
def reject_cross_origin_write():
    if request.method=='POST' and request.headers.get('Origin'):
        from urllib.parse import urlsplit
        if urlsplit(request.headers['Origin']).netloc!=request.host:
            return jsonify({'error':'Nguồn yêu cầu không hợp lệ.'}),403
@app.get('/api/admissions')
def admission_details():
    result=school_admissions(request.args.get('code',''))
    return (jsonify(result[0]),result[1]) if isinstance(result,tuple) else jsonify(result)
@app.post('/api/admissions/lookup')
def admission_lookup():
    result=lookup(request.get_json(silent=True))
    return (jsonify(result[0]),result[1]) if isinstance(result,tuple) else jsonify(result)
if __name__=='__main__': app.run(host='127.0.0.1',port=5001,debug=False)
