"""Two-hour, server-side public-news collection; profiles never enter this cache."""
import json
import os
from pathlib import Path
import re
from html import unescape
import threading
import time
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from email.utils import parsedate_to_datetime
from urllib.parse import urlsplit
from ai_advisor import grounded_answer, safe_url, now_iso
from chatbot import normalize, has
from database import connect

INTERVAL = 2 * 60 * 60
FEEDS = [('VnExpress','https://vnexpress.net/rss/giao-duc.rss','vnexpress.net'),
         ('Tuổi Trẻ','https://tuoitre.vn/rss/giao-duc.rss','tuoitre.vn')]
_refresh_lock = threading.Lock()
_start_lock = threading.Lock()
_started = False
_last_started = 0.0
_last_error = ''

def parse_publication_date(value):
    if not value: return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc).isoformat()
    except (TypeError,ValueError,OverflowError):
        try:
            # Tuổi Trẻ's RSS uses a local Vietnam timestamp rather than RFC 822.
            clean=' '.join(value.split())
            local=datetime.strptime(clean,'%m/%d/%Y %I:%M:%S %p').replace(tzinfo=timezone(timedelta(hours=7)))
            return local.astimezone(timezone.utc).isoformat()
        except (ValueError,TypeError): return None

def init_cache():
    with connect() as con:
        con.execute('CREATE TABLE IF NOT EXISTS trend_cache (id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)')
        seed=Path(__file__).parent/'sql/public-news.json'
        if os.environ.get('VERCEL') and seed.exists():
            con.execute('INSERT OR IGNORE INTO trend_cache(id,payload) VALUES(1,?)',(seed.read_text(encoding='utf-8'),))

def article_thumbnail(item):
    candidates=[]
    for child in item:
        if child.tag.rsplit('}',1)[-1] in ('thumbnail','content','enclosure'):
            candidates.append(child.attrib.get('url',''))
    description=unescape(item.findtext('description') or '')
    candidates.extend(re.findall(r'<img[^>]+src=[\"\']([^\"\']+)',description,re.I))
    for candidate in candidates:
        url=safe_url(unescape(candidate))
        host=(urlsplit(url).hostname or '').lower() if url else ''
        if any(host==domain or host.endswith('.'+domain) for domain in ('vnecdn.net','tuoitre.vn')):
            return url
    return None

def collect_news():
    articles, errors, seen = [], [], set()
    for publisher, url, host in FEEDS:
        try:
            request=urllib.request.Request(url, headers={'User-Agent':'UniGuideBot/1.1 (public RSS reader)'})
            with urllib.request.urlopen(request,timeout=10) as response:
                data=response.read(1_000_001)
            if len(data)>1_000_000 or b'<!DOCTYPE' in data.upper() or b'<!ENTITY' in data.upper(): raise ValueError('Invalid feed')
            root=ET.fromstring(data)
            for item in root.findall('.//item'):
                title=(item.findtext('title') or '').strip()
                link=safe_url((item.findtext('link') or '').strip())
                if not title or not link or link in seen: continue
                hostname=urlsplit(link).hostname or ''
                if hostname!=host and not hostname.endswith('.'+host): continue
                normalized=normalize(title)
                if any(has(normalized,word) for word in ['lop 1','lop 6','mam non','tieu hoc']): continue
                if not any(has(normalized,word) for word in ['nghe','nganh','nhan luc','viec lam','tuyen dung','ky nang','tuyen sinh','ai','tri tue nhan tao','thi truong lao dong','giao vien','nhu cau','dao tao']): continue
                published=parse_publication_date(item.findtext('pubDate'))
                seen.add(link)
                articles.append({'title':title[:500],'url':link,'publisher':publisher,'published_at':published,'collected_at':now_iso(),'thumbnail':article_thumbnail(item)})
        except (OSError, ValueError, ET.ParseError):
            errors.append(publisher)
    articles.sort(key=lambda article:article['published_at'] or '',reverse=True)
    return articles[:24], errors

def get_snapshot():
    init_cache()
    with connect() as con:
        row=con.execute('SELECT payload FROM trend_cache WHERE id=1').fetchone()
    result=json.loads(row[0]) if row else {'analysis':None,'articles':[],'updated_at':None,'news_updated_at':None,'analysis_updated_at':None,'feed_errors':[]}
    timestamp=result.get('updated_at')
    try:
        updated=datetime.fromisoformat(timestamp) if timestamp else None
        stale=not updated or (datetime.now(timezone.utc)-updated).total_seconds()>=INTERVAL
    except ValueError:
        updated=None; stale=True
    result.update({'refreshing':_refresh_lock.locked(),'stale':stale,'interval_seconds':INTERVAL,
        'next_update_at':(updated+timedelta(seconds=INTERVAL)).isoformat() if updated else None,'worker_active':_started,'refresh_error':_last_error})
    return result

def _refresh(rss_only=False):
    global _last_error
    try:
        previous=get_snapshot()
        articles, feed_errors=collect_news()
        year=datetime.now(timezone.utc).year
        analysis=({'grounded':False,'message':'Phân tích AI sẽ được thực hiện khi bạn đặt câu hỏi về xu hướng.'} if rss_only else grounded_answer(f'Tìm kiếm web: xu hướng nghề nghiệp, nhu cầu tuyển dụng và kỹ năng tại Việt Nam năm {year}. Ưu tiên báo cáo công bố gần nhất, nêu mốc thời gian dữ liệu. Tổng hợp 4-6 xu hướng giúp học sinh chọn ngành; đối chiếu dự báo với bằng chứng, không khẳng định chắc chắn về tương lai.'))
        success=bool(articles) or analysis['grounded']
        if success:
            payload={'articles':articles or previous.get('articles',[]),'analysis':analysis if analysis['grounded'] else previous.get('analysis'),
                'updated_at':now_iso(),'news_updated_at':now_iso() if articles else previous.get('news_updated_at'),
                'analysis_updated_at':analysis.get('checked_at') if analysis['grounded'] else previous.get('analysis_updated_at'),
                'feed_errors':feed_errors,'search_error':None if analysis['grounded'] else analysis['message']}
            with connect() as con:
                con.execute('INSERT INTO trend_cache(id,payload) VALUES(1,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload',(json.dumps(payload,ensure_ascii=False),))
            _last_error=''
        else:
            _last_error=analysis['message']+' Chưa lấy được nguồn tin RSS; dữ liệu cũ được giữ nguyên.'
    except Exception:
        _last_error='Chưa hoàn tất lượt cập nhật. Dữ liệu đã lưu được giữ nguyên.'
    finally:
        _refresh_lock.release()

def request_refresh(force=False, synchronous=False, rss_only=False):
    global _last_started
    # Server-wide cooldown covers concurrent browsers and manual refresh clicks.
    if not _refresh_lock.acquire(blocking=False): return False
    snapshot=get_snapshot()
    if time.monotonic()-_last_started<60 or (not force and not snapshot['stale']):
        _refresh_lock.release(); return False
    _last_started=time.monotonic()
    if synchronous:_refresh(rss_only=rss_only)
    else:threading.Thread(target=_refresh,kwargs={'rss_only':rss_only},daemon=True,name='uniguide-trend-refresh').start()
    return True

def start_worker():
    global _started
    if os.environ.get("VERCEL"):return
    with _start_lock:
        if _started: return
        init_cache(); _started=True
    def run():
        while True:
            request_refresh()
            if _refresh_lock.locked():
                time.sleep(5)
                continue
            snapshot=get_snapshot()
            # Wake at the saved timestamp's two-hour deadline; retry failures every ten minutes.
            if snapshot['next_update_at'] and not snapshot['stale']:
                remaining=(datetime.fromisoformat(snapshot['next_update_at'])-datetime.now(timezone.utc)).total_seconds()
                time.sleep(min(600,max(1,remaining)))
            else:
                time.sleep(600)
    threading.Thread(target=run,daemon=True,name='uniguide-trend-scheduler').start()
