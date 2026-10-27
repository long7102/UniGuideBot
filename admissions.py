"""Sourced admissions records, by school, program, method and year."""
import json
from pathlib import Path
from database import search_universities
from ai_advisor import grounded_answer
DATA=Path(__file__).parent/'sql/admissions.json'
YEARS=(2024,2025,2026)
def records():
    return json.loads(DATA.read_text(encoding='utf-8-sig')) if DATA.exists() else {'schools':{}}
def school_admissions(code):
    schools=[row for row in search_universities(limit=1000) if row['short_name']==code]
    if not schools:return {'error':'Không tìm thấy trường.'},404
    data=records();school=schools[0];entry=data.get('schools',{}).get(code,{})
    tuition=entry.get('tuition',[]);scores=entry.get('scores',[])
    return {'school':school,'years':list(YEARS),'tuition':tuition,'scores':scores,'updated_at':data.get('updated_at'),
        'coverage':{str(year):{'tuition':sum(row['year']==year for row in tuition),'scores':sum(row['year']==year for row in scores)} for year in YEARS},
        'notice':'Điểm chuẩn khác nhau theo ngành, phương thức và thang điểm. Học phí phụ thuộc chương trình và năm học; mức dự kiến không phải hóa đơn thực tế. Năm thiếu nguồn được để trống.'}
def evidence(codes):
    all_data=records().get('schools',{})
    return {code:all_data[code] for code in codes if code in all_data}
def lookup(payload):
    if not isinstance(payload,dict) or not isinstance(payload.get('code'),str):return {'error':'Mã trường không hợp lệ.'},400
    entry=school_admissions(payload['code'])
    if isinstance(entry,tuple):return entry
    school=entry['school']
    result=grounded_answer(f"Tìm nguồn chính thức tại {school['website']} về {school['name']}, cơ sở {school['city']}: học phí và điểm trúng tuyển 2024, 2025, 2026. Phân biệt theo ngành, chương trình, phương thức và thang điểm; học phí theo tín chỉ/năm/toàn khóa. Không tìm thấy thì ghi thiếu. Tóm tắt tối đa 450 từ.",schools=[school])
    if not result['grounded']:return {'error':result['message'],'error_code':result.get('error_code'),'retryable':True},503
    return result

def attach_summaries(schools):
    data=records().get('schools',{})
    for school in schools:
        entry=data.get(school['short_name'],{})
        tuition=entry.get('tuition',[]);scores=entry.get('scores',[])
        by_year=[]
        for year in YEARS:
            groups={}
            for row in scores:
                if row['year']!=year:continue
                key=(row['method'],row['scale'])
                groups.setdefault(key,[]).append(row['score'])
            by_year.append({'year':year,'groups':[{'method':key[0],'scale':key[1],'min':min(values),'max':max(values),'programs':len(values)} for key,values in groups.items()]})
        latest=max((row['year'] for row in tuition),default=None)
        fee_groups={}
        for row in tuition:
            if row['year']!=latest:continue
            fee_groups.setdefault(row['unit'],[]).append(row)
        fees=[{'year':latest,'unit':unit,'min':min(r['minimum'] for r in rows),'max':max(r['maximum'] for r in rows),'programs':[r['program'] for r in rows],'estimated':any(r.get('estimated') for r in rows)} for unit,rows in fee_groups.items()]
        school['admissions_summary']={'tuition':fees,'scores':by_year}
    return schools
