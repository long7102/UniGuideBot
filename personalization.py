"""Validate transient profiles and explain catalogue matching without admission claims."""
from chatbot import FIELD_LABELS, REGION_LABELS, normalize, has
from database import search_universities

TEXT_FIELDS = {'interests':1200,'strengths':1200,'subjects':500,'score':150,'budget':150,'goals':1200}
CAREERS = {
 'cntt':('Phát triển phần mềm, dữ liệu và an toàn thông tin','Tư duy logic, lập trình, xác suất và tiếng Anh'),
 'ky_thuat':('Kỹ thuật, điện tử và tự động hóa','Toán, vật lý, thiết kế hệ thống và làm dự án'),
 'kinh_te':('Kinh doanh, phân tích kinh doanh và logistics','Phân tích dữ liệu, giao tiếp, vận hành và tài chính cơ bản'),
 'su_pham':('Giáo dục và phát triển học liệu','Chuyên môn môn học, giao tiếp và phương pháp giảng dạy'),
 'y_duoc':('Sức khỏe và dược','Sinh học, hóa học, kỷ luật nghề nghiệp và kỹ năng chăm sóc'),
 'luat':('Pháp lý và tuân thủ','Đọc hiểu, lập luận, viết và nghiên cứu văn bản'),
 'ngoai_ngu':('Ngôn ngữ, biên phiên dịch và giao tiếp quốc tế','Ngoại ngữ, kiến thức chuyên ngành và giao tiếp liên văn hóa'),
 'nghe_thuat':('Thiết kế và sáng tạo nội dung','Tư duy thị giác, thực hành sáng tạo và hồ sơ sản phẩm'),
 'nong_lam':('Nông nghiệp, lâm nghiệp và quản lý tài nguyên','Sinh học, kỹ thuật sản xuất và thực hành thực địa'),
 'xa_hoi':('Truyền thông và nghiên cứu xã hội','Đọc hiểu, viết, phân tích xã hội và nghiên cứu'),
 'the_duc':('Thể thao và huấn luyện','Thể lực, chuyên môn vận động và phương pháp huấn luyện'),
 'khoa_hoc':('Nghiên cứu và ứng dụng khoa học tự nhiên','Toán, phương pháp thực nghiệm và phân tích dữ liệu')}
SIGNALS = {
 'cntt':['cntt','lap trinh','phan mem','du lieu','may tinh','logic','toan','tri tue nhan tao'],
 'ky_thuat':['ky thuat','co khi','dien tu','tu dong hoa','vat ly','robot','toan'],
 'kinh_te':['kinh te','kinh doanh','marketing','tai chinh','logistics','ke toan','quan ly'],
 'su_pham':['giao vien','giang day','day hoc','su pham','truyen dat'],
 'y_duoc':['y duoc','bac si','y khoa','duoc','sinh hoc','hoa hoc','cham soc'],
 'luat':['luat','phap ly','tranh bien','lap luan'],
 'ngoai_ngu':['ngoai ngu','tieng anh','tieng trung','ngon ngu','bien dich','phien dich'],
 'nghe_thuat':['thiet ke','my thuat','ve','am nhac','sang tao'],
 'nong_lam':['nong nghiep','nong lam','lam nghiep','trong trot'],
 'xa_hoi':['xa hoi','nhan van','bao chi','truyen thong','viet lach'],
 'the_duc':['the thao','huan luyen','the duc'],
 'khoa_hoc':['khoa hoc','nghien cuu','thi nghiem','vat ly','hoa hoc']}

DISPLAY_SIGNALS={'lap trinh':'lập trình','du lieu':'dữ liệu','phan mem':'phần mềm','may tinh':'máy tính','toan':'Toán','vat ly':'Vật lý','kinh doanh':'kinh doanh','tai chinh':'tài chính','ke toan':'kế toán','tieng anh':'tiếng Anh','ngon ngu':'ngôn ngữ','giao vien':'giáo viên','giang day':'giảng dạy','thiet ke':'thiết kế','my thuat':'mỹ thuật','nghien cuu':'nghiên cứu','ky thuat':'kỹ thuật','tu dong hoa':'tự động hóa','co khi':'cơ khí'}

def validate_profile(value):
    if not isinstance(value, dict): raise ValueError('Hồ sơ cần là một đối tượng hợp lệ.')
    profile = {}
    for key, maximum in TEXT_FIELDS.items():
        text = value.get(key, '')
        if not isinstance(text,str) or len(text)>maximum: raise ValueError('Thông tin hồ sơ quá dài hoặc không hợp lệ.')
        profile[key] = text.strip()
    for key, allowed in [('field',FIELD_LABELS),('region',REGION_LABELS)]:
        item=value.get(key,'')
        if not isinstance(item,str) or (item and item not in allowed): raise ValueError('Nhóm ngành hoặc khu vực trong hồ sơ không hợp lệ.')
        profile[key]=item
    return profile

def match_profile(profile, filters=None):
    filters = filters or {}
    field = filters.get('field') or profile.get('field')
    region = filters.get('region') or profile.get('region')
    text = normalize(' '.join(profile.get(key,'') for key in ('interests','strengths','subjects','goals')))
    matches = {key:[word for word in words if has(text,word)] for key,words in SIGNALS.items()}
    fields = [field] if field else [key for key in sorted(matches,key=lambda k:len(matches[k]),reverse=True) if matches[key]][:3]
    if not fields: return [], [], []
    schools = search_universities(region,field,limit=1000)
    schools = [school for school in schools if set(school['fields']) & set(fields)]
    schools.sort(key=lambda school: -len(set(school['fields']) & set(fields)))
    schools = schools[:8]
    careers = [{'field':key,'label':FIELD_LABELS[key],'title':CAREERS[key][0],'skills':CAREERS[key][1],
        'reason':'Bạn đã chọn nhóm ngành này.' if field else 'Liên hệ với các tín hiệu trong hồ sơ: '+', '.join(DISPLAY_SIGNALS.get(word,word) for word in matches[key])} for key in fields]
    reasons = [{'code':school['short_name'],'reason':'Có nhóm lĩnh vực '+', '.join(FIELD_LABELS[key] for key in fields if key in school['fields'])+(' tại '+REGION_LABELS[region] if region else '')+'. Cần kiểm tra chương trình cụ thể.'} for school in schools]
    return schools, careers, reasons
