"""Deterministic regression tests. Gemini is mocked, never billed here."""
import unittest
import tempfile
from pathlib import Path
import database
from unittest.mock import patch
from database import init_db,search_universities,get_stats
from chatbot import analyze
from service import chat

class SystemTests(unittest.TestCase):
    def setUp(self):
        self.provider=patch("service.answer_with_ai", return_value={"message":"AI kiểm thử","ai_powered":True,"grounded":False,"sources":[]}).start()
        self.network=patch("urllib.request.urlopen",side_effect=AssertionError("Unexpected network call")).start()
        self.addCleanup(patch.stopall)
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parent)
        cls.original_db = database.DB_PATH
        database.DB_PATH = Path(cls.temp.name) / 'test.db'
        init_db()
    @classmethod
    def tearDownClass(cls):
        database.DB_PATH = cls.original_db
        import gc
        gc.collect()
        cls.temp.cleanup()
    def test_catalogue(self): self.assertEqual(get_stats(),{'universities':134,'fields':12,'regions':3})
    def test_vietnamese(self): self.assertEqual(analyze('Em thích công nghệ thông tin ở Hà Nội')['field'],'cntt')
    def test_no_accents(self): self.assertEqual(analyze('kinh te mien nam')['region'],'nam')
    def test_word_boundaries(self):
        self.assertEqual(analyze('Em thích thiết kế')['field'],'nghe_thuat')
        self.assertIsNone(analyze('Em được 25 điểm thì có chắc đỗ đại học không?')['field'])
    def test_region_and_field(self):
        rows=search_universities('nam','cntt');self.assertTrue(rows);self.assertTrue(all(r['region']=='nam' and 'cntt' in r['fields'] for r in rows))
    def test_no_relaxation(self): self.assertEqual(search_universities('trung','luat'),[])
    def test_sql_parameters(self): self.assertEqual(search_universities(name="' OR 1=1 --"),[])
    def test_invalid_inputs(self):
        for payload in (None,[],{}, {'message':3},{'message':''},{'message':'a'*2001},{'message':'hi','filters':[]},{'message':'hi','filters':{'region':'invalid'}}): self.assertEqual(chat(payload)[1],400)
    def test_all_chat_types_use_ai(self):
        for question in ['Xin chào','Hôm nay ăn gì?','Tìm trường CNTT ở Hà Nội','25 điểm có đỗ UIT không?','Học phí dưới 20 triệu','Tìm trường luật miền Trung']:
            result=chat({'message':question})
            self.assertTrue(result['ai_powered'])
        self.assertEqual(self.provider.call_count,6)
    def test_outside_has_no_school_cards(self):
        for question in ['Hôm nay ăn gì?','Giá vàng hôm nay','Viết code Python cho sinh viên CNTT','Thời tiết mới nhất năm 2026','So sánh iPhone và Samsung']:
            self.assertEqual(chat({'message':question,'filters':{'field':'cntt','region':'bac'}})['universities'],[])
    def test_no_template_when_provider_fails(self):
        self.provider.return_value=({'error':'Provider unavailable','error_code':'service_unavailable'},503)
        result=chat({'message':'Xin chào'})
        self.assertEqual(result[1],503)
        self.assertNotIn('message',result[0])
    def test_comparison_keeps_all_named_schools(self):
        result=chat({'message':'So sánh HUST và UIT'})
        self.assertEqual({s['short_name'] for s in result['universities']},{'HUST','UIT'})
    def test_filters_override(self):
        result=chat({'message':'CNTT ở miền Bắc','filters':{'region':'nam'}})
        self.assertTrue(all(s['region']=='nam' for s in result['universities']))
    def test_history_sent_to_ai(self):
        history=[{'role':'user','content':'Tôi thích toán'},{'role':'assistant','content':'Bạn thích lập trình chứ?'}]
        chat({'message':'Có','history':history})
        self.assertEqual(self.provider.call_args.kwargs['history'],history)
    def test_invalid_history(self):
        for history in [None,{},[{'role':'system','content':'bad'}],[{'role':'user','content':'a'*6001}],[{'role':'user','content':'a'*6000}]*4]:
            self.assertEqual(chat({'message':'Xin chào','history':history})[1],400)
    def test_north_catalogue(self):
        self.assertEqual(len(search_universities('bac',limit=1000)),127)
    def test_names_unambiguous(self):
        from chatbot import CATALOGUE
        for row in CATALOGUE:self.assertEqual(analyze(row['name'])['schools'],[row['short_name']])
    def test_conditional_not_neu(self):
        self.assertIsNone(analyze('Nếu em muốn học CNTT ở miền Nam thì chọn trường nào?')['school'])

class EducationRoutingTests(unittest.TestCase):
    def test_school_information_is_education(self):
        for question in ['trường học viện phụ nữ việt nam có mấy cơ sở','HPN có những ngành nào?','Học viện Phụ nữ Việt Nam có phân hiệu ở đâu?','Ngành khoa học máy tính có học viết code không?','Nghề này cần học những gì?']:
            with self.subTest(question=question):self.assertNotEqual(analyze(question)['topic'],'outside')
    def test_actual_task_requests_remain_outside(self):
        for question in ['Viết code Python cho sinh viên CNTT','HUST hôm nay có thời tiết thế nào?','Công thức nấu phở']:
            self.assertEqual(analyze(question)['topic'],'outside')
    def test_campus_fact_source_lists_three_locations(self):
        import json
        facts=json.loads((Path(__file__).parent/'sql/school-facts.json').read_text(encoding='utf-8'))['HPN']
        self.assertEqual(len(facts['locations']),3)
        self.assertTrue(any(row['type']=='Cơ sở Gia Lâm' for row in facts['locations']))

if __name__=='__main__':unittest.main(verbosity=2)
