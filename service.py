from chatbot import analyze, FIELD_LABELS, REGION_LABELS
from database import search_universities
from admissions import evidence
from trends import get_snapshot
from ai_advisor import grounded_answer, answer_with_ai
from personalization import validate_profile, match_profile

def validate_history(value):
    if not isinstance(value,list) or len(value)>20:raise ValueError('Lịch sử hội thoại không hợp lệ.')
    result=[];total=0
    for row in value:
        if not isinstance(row,dict) or row.get('role') not in ('user','assistant') or not isinstance(row.get('content'),str) or len(row['content'])>6000:raise ValueError('Tin nhắn lịch sử không hợp lệ.')
        total+=len(row['content'])
        if total>20000:raise ValueError('Lịch sử gửi đến AI quá dài.')
        result.append({'role':row['role'],'content':row['content']})
    return result

def live_advice(message,profile,schools,history=None):
    web=grounded_answer(message,profile,schools,history=history)
    if web['ai_powered']:return web
    try:articles=get_snapshot().get('articles',[])[:6]
    except Exception:articles=[]
    sources=[{'id':i+1,'title':a['title'],'url':a['url']} for i,a in enumerate(articles)]
    context={'profile':profile,'search_unavailable':web.get('error_code'),'news_headlines':[{'id':i+1,'title':a['title'],'url':a['url'],'published_at':a.get('published_at')} for i,a in enumerate(articles)],'admission_evidence':evidence([s['short_name'] for s in schools])}
    instruction=message+'\nYêu cầu trả lời: Google Search đang không khả dụng trong lượt này. Nêu ngắn hạn chế đó và tiếp tục tư vấn định hướng bằng thông tin đã cung cấp. Chỉ coi tiêu đề RSS là tin đã thu thập, không suy ra số liệu thị trường hay chi tiết bài báo chưa đọc. Nếu dùng tiêu đề, trích [id] tương ứng. Không nói đã tìm Google thành công. Không tự tạo dữ liệu 2026.'
    result=answer_with_ai(instruction,context,schools,history=history)
    if isinstance(result,tuple):return result
    return {**result,'sources':sources,'research_mode':'rss_context','search_warning':'Google Search chưa khả dụng; phần tư vấn do AI thực hiện với thông tin hiện có.'}

def chat(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('message'),str):
        return {'error':'Cần gửi đối tượng JSON với message là chuỗi.'},400
    try:history=validate_history(payload.get('history',[]))
    except ValueError as error:return {'error':str(error)},400
    message=payload['message'].strip()
    if not message or len(message)>2000: return {'error':'Câu hỏi cần từ 1 đến 2.000 ký tự.'},400
    intent=analyze(message)
    supplied=payload.get('filters',{})
    if not isinstance(supplied,dict): return {'error':'Bộ lọc không hợp lệ.'},400
    for key,allowed in [('field',FIELD_LABELS),('region',REGION_LABELS)]:
        if supplied.get(key):
            if not isinstance(supplied[key],str) or supplied[key] not in allowed: return {'error':'Giá trị bộ lọc không hợp lệ.'},400
            intent[key]=supplied[key]
    try:
        profile=validate_profile(payload.get('profile',{}))
    except ValueError as error:
        return {'error':str(error)},400
    if intent['topic']=='live':
        # Never persist personalized questions or profiles in the public trends cache.
        candidates=search_universities(intent['region'],intent['field'])
        result=live_advice(message,profile,candidates,history)
        if isinstance(result,tuple):return result
        return {**result,'universities':[],'intent':intent,'notice':'Mở nguồn để đối chiếu năm dữ liệu và bối cảnh.'}
    if any(profile.values()) and intent['topic'] not in ('greeting','outside'):
        intent['profile']=profile
        if not intent['field'] and profile['field']: intent['field']=profile['field']
        if not intent['region'] and profile['region']: intent['region']=profile['region']
    if intent['topic']=='clarify' and intent['field']:
        intent['topic']='choose'
    schools=[]
    if intent['topic'] not in ('greeting','outside','clarify'):
        if intent['schools']:
            for code in intent['schools']:
                schools.extend(search_universities(intent['region'],intent['field'],code,ownership=intent['ownership']))
        else:
            schools=search_universities(intent['region'],intent['field'],limit=1000,ownership=intent['ownership'])
    if intent['topic'] in ('scores','fees') and not any(intent.get(k) for k in ('field','region','school','schools')):
        schools=[]
    total_matches=len(schools)
    schools=schools[:12]
    intent['admission_evidence']=evidence([s['short_name'] for s in schools])
    from pathlib import Path
    import json
    facts_file=Path(__file__).parent/'sql/school-facts.json'
    facts=json.loads(facts_file.read_text(encoding='utf-8')) if facts_file.exists() else {}
    intent['school_facts']={code:facts[code] for code in intent['schools'] if code in facts}
    fact_sources=[{'id':i+1,'url':row['source_url'],'title':row['title']} for i,row in enumerate(intent['school_facts'].values())]
    intent['fact_sources']=fact_sources
    ai_result=answer_with_ai(message,intent,schools,history=history)
    if isinstance(ai_result,tuple): return ai_result
    return {**ai_result,'sources':ai_result.get('sources') or fact_sources,'universities':schools,'intent':intent,'total_matches':total_matches,'notice':(f'Có {total_matches} cơ sở khớp tiêu chí; mở danh mục để xem đầy đủ.' if total_matches>len(schools) else '')}

def recommend(payload):
    if not isinstance(payload,dict): return {'error':'Hồ sơ không hợp lệ.'},400
    try:
        profile=validate_profile(payload.get('profile'))
    except ValueError as error:
        return {'error':str(error)},400
    if not any(profile.values()): return {'error':'Hãy nhập sở thích, thế mạnh hoặc chọn nhóm ngành để bắt đầu.'},400
    use_web=payload.get('use_web',True)
    if not isinstance(use_web,bool): return {'error':'Lựa chọn tra cứu không hợp lệ.'},400
    schools,careers,reasons=match_profile(profile)
    question='Tư vấn cá nhân dựa trên hồ sơ. Nêu 2-3 hướng nghề phù hợp, lý do, điểm cần bổ sung, và trường trong catalogue để tìm hiểu. Viết một LỘ TRÌNH 90 NGÀY gồm 3 giai đoạn: ngày 1-30, 31-60, 61-90; mỗi giai đoạn có mục tiêu, hành động cụ thể, sản phẩm kiểm chứng. Nếu sở thích còn mơ hồ, hỏi làm rõ thay vì đoán trường. Không coi sở thích/hành vi có hại là thế mạnh nghề nghiệp.'
    context={'profile':profile,'structured_recommendation':True,'admission_evidence':evidence([s['short_name'] for s in schools])}
    sources=[];warning=None;grounded=False;checked_at=None
    if use_web:
        web=grounded_answer(question+' Đối chiếu xu hướng thị trường lao động mới nhất.',profile,schools)
        if web.get('grounded'):
            context['web_evidence']=web['message'];sources=web.get('sources',[]);grounded=True;checked_at=web.get('checked_at')
        else:
            warning='Google Search chưa khả dụng trong lượt này. AI tiếp tục phân tích hồ sơ và dữ liệu trường đã có.'
            context['search_unavailable']=True
    result=answer_with_ai(question,context,schools)
    if isinstance(result,tuple):return result
    reasons=result.get('match_reasons',[])
    by_code={s['short_name']:s for s in schools}
    selected=[by_code[r['code']] for r in reasons if r.get('code') in by_code]
    return {**result,'universities':selected,'careers':[], 'match_reasons':reasons,'sources':sources,'grounded':grounded,'checked_at':checked_at,'search_warning':warning,'profile_snapshot':profile,
        'notice':'AI giải thích dựa trên hồ sơ và dữ liệu được cung cấp; chưa có căn cứ không được xem là đủ điều kiện trúng tuyển hoặc vừa ngân sách.'}
