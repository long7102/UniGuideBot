import re
import json
from pathlib import Path
import unicodedata

FIELD_LABELS = {'cntt':'Công nghệ thông tin','kinh_te':'Kinh tế – kinh doanh','ky_thuat':'Kỹ thuật – công nghệ','su_pham':'Sư phạm','y_duoc':'Y – dược','luat':'Luật','ngoai_ngu':'Ngoại ngữ','nghe_thuat':'Nghệ thuật – thiết kế','nong_lam':'Nông – lâm nghiệp','xa_hoi':'Xã hội – nhân văn','the_duc':'Thể dục – thể thao','khoa_hoc':'Khoa học tự nhiên'}
REGION_LABELS = {'bac':'Miền Bắc','trung':'Miền Trung','nam':'Miền Nam'}
CATALOGUE = json.loads((Path(__file__).parent/'sql/catalogue.json').read_text(encoding='utf-8-sig'))

def normalize(text):
    return ''.join(c for c in unicodedata.normalize('NFD', text.lower().replace('đ','d')) if unicodedata.category(c) != 'Mn')

def has(text, phrase):
    return re.search(r'(?<!\w)'+re.escape(phrase)+r'(?!\w)',text) is not None

def analyze(message):
    text = normalize(message)
    intent = {'field':None,'region':None,'topic':'outside','school':None,'schools':[],'needs_fees':False,'needs_scores':False}
    groups = {'cntt':['cntt','cong nghe thong tin','lap trinh','phan mem','may tinh','tri tue nhan tao','it'], 'kinh_te':['kinh te','kinh doanh','marketing','ke toan','tai chinh','logistics'], 'ky_thuat':['ky thuat','co khi','dien tu','tu dong hoa'], 'su_pham':['su pham','giao vien'], 'y_duoc':['y duoc','y khoa','bac si','nganh duoc','duoc hoc'], 'luat':['luat'], 'ngoai_ngu':['ngoai ngu','ngon ngu','tieng anh'],'nghe_thuat':['nghe thuat','thiet ke','my thuat','am nhac'],'nong_lam':['nong nghiep','nong lam','lam nghiep'],'xa_hoi':['xa hoi','nhan van','bao chi','truyen thong'],'the_duc':['the duc','the thao'],'khoa_hoc':['khoa hoc tu nhien','vat ly','hoa hoc','sinh hoc']}
    raw = unicodedata.normalize('NFC', message).lower()
    aliases_by_school = {'HUST':['bach khoa ha noi'], 'UIT':['dai hoc cong nghe thong tin'], 'NEU':['kinh te quoc dan'], 'HCMUE':['su pham tp hcm'], 'DUT':['bach khoa da nang'], 'CTU':['dai hoc can tho'], 'ULIS':['ngoai ngu ha noi'], 'HMU':['y ha noi'], 'HLU':['luat ha noi'], 'UEH':['kinh te tp hcm'], 'HCMUT':['bach khoa tp hcm'], 'HUE':['dai hoc hue']}
    for row in CATALOGUE:
        aliases_by_school.setdefault(row['short_name'], []).extend(row.get('aliases', []))
    criteria = text
    spans=[]
    candidates=[]
    internal_codes={row['short_name'] for row in CATALOGUE}
    for row in CATALOGUE:
        code=row['short_name']
        admission=row.get('admission_code','')
        if admission and admission not in internal_codes:
            aliases_by_school.setdefault(code,[]).append(admission.lower())
    for code, aliases in aliases_by_school.items():
        conditional = code=='NEU' and not has(text,'kinh te quoc dan') and not has(message,'NEU') and (re.search(r'\bneu\s+(em|toi|minh|ban|con|muon|hoc|duoc|chon|thi|khong)\b',text) or re.search(r'\bneu\b.+\bthi\b',text))
        if conditional: continue
        if has(raw,code.lower()):
            intent['schools'].append(code)
        for alias in aliases+[code.lower()]:
            for match in re.finditer(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',text):
                # Abbreviations must also exist in the original, accented text.
                if alias==code.lower() and not has(raw,alias): continue
                candidates.append((match.start(),match.end(),code))
    for left,right,code in sorted(candidates,key=lambda item:-(item[1]-item[0])):
        if any(left<end and right>start for start,end in spans): continue
        spans.append((left,right))
        if code not in intent['schools']: intent['schools'].append(code)
    for left,right in sorted(spans,reverse=True):
        criteria=criteria[:left]+' '*(right-left)+criteria[right:]
    intent['school']=intent['schools'][0] if len(intent['schools'])==1 else None
    for key, words in groups.items():
        if any(has(criteria,w) for w in words): intent['field']=key; break
    for key, words in {'bac':['mien bac','phia bac','ngoai bac','bac bo','ha noi','hanoi','thai nguyen','hai phong','nam dinh','bac ninh','hai duong','hung yen','bac giang','quang ninh','phu tho','vinh phuc','tuyen quang','lao cai','dien bien','son la','lai chau','lang son','cao bang','ha giang','bac kan','thai binh','ninh binh','hoa binh','yen bai'], 'trung':['mien trung','da nang','hue'], 'nam':['mien nam','phia nam','trong nam','tp hcm','tphcm','ho chi minh','sai gon','can tho']}.items():
        if any(has(criteria,w) for w in words): intent['region']=key; break
    education = any(has(text,w) for w in ['dai hoc','chon truong','tim truong','truong nao','truong phu hop','truong tot','nganh hoc','hoc nganh','chon nganh','tuyen sinh','xet tuyen','trung tuyen','diem chuan','hoc phi','hoc bong','ky tuc xa','to hop','khoi thi','nguyen vong','huong nghiep','cac truong','truong dai hoc','nghe nghiep','chon nghe','nghe tuong lai','hoc gi','hoc truong','tu van cho toi','truong cong lap','truong tu thuc','truong dan lap','truong ngoai cong lap'])
    short_field = intent['field'] and text.strip(' !?.') in [w for words in groups.values() for w in words]
    study_field = intent['field'] and any(has(text,w) for w in ['hoc','nganh','truong','tu van','thich'])
    relevant = bool(education or intent['schools'] or short_field or study_field)
    if relevant: intent['topic']='choose'
    intent['needs_fees'] = relevant and any(has(text,w) for w in ['hoc phi','ngan sach','trieu','chi phi'])
    intent['needs_scores'] = relevant and any(has(text,w) for w in ['diem chuan','diem','trung tuyen','do dai hoc'])
    if relevant and any(has(text,w) for w in ['so sanh','khac nhau']): intent['topic']='compare'
    if intent['needs_fees']: intent['topic']='fees'
    if intent['needs_scores']: intent['topic']='scores'
    if relevant and re.search(r'\b(?:hoc|chon|tu van|tim hieu)\s+(?:ve\s+)?(?:nganh|nghe)\b', text) and not intent['field'] and not intent['schools'] and not intent['needs_fees'] and not intent['needs_scores']:
        intent['topic']='clarify'
    career = any(has(text,w) for w in ['nghe nghiep','nganh nghe','thi truong lao dong','tuyen dung','viec lam','nhan luc','nghe nao','nghe hot','chon nghe','nghe tuong lai'])
    freshness = any(has(text,w) for w in ['xu huong','moi nhat','hien nay','nam nay','gan day','tuong lai','cap nhat','tim kiem','tra cuu','2026','2027'])
    if career or (relevant and freshness): intent['topic']='live'
    if text.strip(' !?.') in ['chao','xin chao','hello','hi']: intent['topic']='greeting'
    if any(has(text,w) for w in ['thoi tiet','nau an','thu cung','cho an','bong da','xo so','chung khoan','gia vang','bitcoin','xem phim','ke chuyen','lam tho','viet tho','dich sang','dich cau','viet code','viet ham','debug','sua code','giai phuong trinh','giai bai','chua benh','dau bung','cong thuc nau','cong thuc lam','huong dan nau']): intent['topic']='outside'
    # Route by the question's purpose, not the mere presence of a blacklisted word.
    school_details=any(has(text,w) for w in ['co so','phan hieu','khuon vien','dia chi','tru so','o dau','bao nhieu khoa','may khoa','hoc bao lau','chuan dau ra','chuong trinh dao tao','nganh dao tao','nganh gi','nganh nao','giang vien','thuc tap','co so vat chat','kiem dinh','doi tac','ky tuc xa','hoc bong'])
    school_context=bool(intent['schools']) or any(has(text,w) for w in ['truong','hoc vien','dai hoc','co so dao tao'])
    education_purpose=any(has(text,w) for w in ['nganh hoc','hoc nganh','nganh dao tao','chuong trinh dao tao','nganh nay','nganh do','nghe nay','nghe do','truong nay','truong do','co hoi nghe nghiep','dinh huong nghe','co hoi viec lam','ky nang nghe','can hoc gi','can ky nang gi','hoc nhung gi'])
    education_purpose=education_purpose or bool(intent['field'] and any(has(criteria,w) for w in ['nganh','hoc','nghe']))
    if school_details and school_context:
        intent['topic']='live' if freshness else 'school_info'
    elif education_purpose and not re.search(r'^(?:viet code|viet ham|debug|sua code|giai bai|giai phuong trinh)\b',text.strip()):
        intent['topic']='live' if career or freshness else ('choose' if intent['field'] else 'clarify')
    private=any(has(text,w) for w in ['tu thuc','dan lap','ngoai cong lap'])
    public=has(text,'cong lap') and not has(text,'ngoai cong lap')
    intent['ownership']='tu_thuc' if private and not public else 'cong_lap' if public and not private else None
    return intent

def local_answer(intent, schools):
    topic=intent['topic']
    if topic=='greeting': return 'Chào bạn! Mình là UniGuideBot. Bạn muốn học nhóm ngành nào, ở khu vực nào? Bạn có thể cho biết thêm điểm dự kiến và ngân sách để mình hướng dẫn cách đối chiếu.'
    if topic=='outside': return 'Mình chỉ hỗ trợ định hướng chọn trường và ngành học đại học. Mình chưa xác định được yêu cầu tư vấn tuyển sinh trong câu hỏi này. Bạn có thể hỏi: “Em muốn học CNTT ở miền Nam” hoặc “So sánh HUST và UIT”.'
    if topic=='clarify': return 'Mình chưa nhận diện được nhóm ngành bạn muốn học trong danh mục hiện có. Bạn hãy chọn nhóm ngành trong bộ lọc hoặc nói rõ hơn ngành và khu vực mong muốn.'
    opening=[]
    if intent.get('needs_scores') or topic=='scores': opening.append('Kho dữ liệu chưa có điểm chuẩn theo năm, ngành và phương thức xét tuyển. Mình không thể kết luận khả năng trúng tuyển chỉ từ điểm bạn cung cấp. Hãy đối chiếu đúng thang điểm, tổ hợp và thông báo chính thức của năm bạn đăng ký.')
    if intent.get('needs_fees') or topic=='fees': opening.append('Kho dữ liệu chưa có học phí theo chương trình và năm học, nên chưa thể lọc trường trong ngân sách cụ thể. Bạn nên cộng học phí, chi phí sinh hoạt, ký túc xá và dự phòng; kiểm tra mức thu tại website chính thức.')
    if topic in ('scores','fees') and not schools and not any(intent.get(k) for k in ('field','region','school','schools')):
        return '\n\n'.join(opening+['Bạn muốn tìm hiểu nhóm ngành nào, tại khu vực nào và đăng ký năm nào? Mình có thể gợi ý danh mục trường để bạn kiểm tra thông tin tuyển sinh chính thức.'])
    if not schools:
        return '\n\n'.join(opening+['Chưa tìm thấy trường khớp đồng thời các tiêu chí trong danh mục mẫu. Bạn có thể đổi khu vực hoặc nhóm ngành. Hệ thống giữ nguyên điều kiện thay vì tự gợi ý trường không phù hợp.'])
    if topic=='compare': opening.append('Bạn có thể so sánh các trường theo chương trình đào tạo, địa điểm, điều kiện xét tuyển, tổng chi phí và cơ hội thực tập. Danh mục dưới đây chưa phải bảng xếp hạng.')
    labels=[FIELD_LABELS.get(intent.get('field')), REGION_LABELS.get(intent.get('region'))]
    opening.append('Các trường để bạn tìm hiểu'+(' về '+', '.join(x for x in labels if x) if any(labels) else '')+':')
    opening.extend(f"{i}. {s['name']} ({s['short_name']}) – {s['city']}. {s['description']}" for i,s in enumerate(schools,1))
    opening.append('Đây là danh mục định hướng, không xác nhận ngành/chỉ tiêu của năm hiện tại và không bảo đảm trúng tuyển. Hãy mở nguồn chính thức trên thẻ trường để kiểm tra đề án tuyển sinh. Bạn ưu tiên ngành, khu vực và ngân sách nào?')
    return '\n\n'.join(opening)
