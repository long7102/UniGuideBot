"""Feature tests use temporary SQLite and mocked providers; no API fees."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import database
import ai_advisor
import trends
from chatbot import analyze, CATALOGUE
from service import chat, recommend

class FeatureTests(unittest.TestCase):
    def setUp(self):
        self.provider=patch("service.answer_with_ai", return_value={"message":"AI tư vấn và lộ trình","ai_powered":True,"grounded":False,"sources":[]}).start()
        patch("urllib.request.urlopen",side_effect=AssertionError("Unexpected network call")).start()
        self.addCleanup(patch.stopall)
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        cls.old_db=database.DB_PATH
        database.DB_PATH=Path(cls.temp.name)/'features.db'
        database.init_db()
        trends.init_cache()
    @classmethod
    def tearDownClass(cls):
        database.DB_PATH=cls.old_db
        cls.temp.cleanup()

    def test_north_coverage_and_private(self):
        stats=database.catalogue_stats()
        self.assertEqual(stats['north'],127)
        self.assertEqual(stats['north_private'],26)
        rows=database.search_universities('bac',limit=1000)
        self.assertEqual(len(rows),127)
        self.assertEqual(len({r['short_name'] for r in rows}),127)
        self.assertTrue(all(r['source_url'].startswith('https://') for r in rows))

    def test_every_catalogue_name_is_unambiguous(self):
        for row in CATALOGUE:
            with self.subTest(code=row['short_name']):
                self.assertEqual(analyze(row['name'])['schools'],[row['short_name']])

    @patch('service.grounded_answer',return_value={'message':'Limit429','grounded':False,'ai_powered':False,'error_code':'quota_exceeded'})
    def test_search_failure_still_uses_real_ai(self,ground):
        result=chat({'message':'Xu hướng nghề nghiệp năm 2026 là gì?'})
        self.assertTrue(result['ai_powered']);self.assertFalse(result['grounded'])
        self.assertEqual(result['research_mode'],'rss_context');self.provider.assert_called_once()
    @patch('service.grounded_answer',return_value={'message':'Web evidence','grounded':True,'ai_powered':True,'sources':[]})
    def test_successful_grounding(self,ground):
        self.assertTrue(chat({'message':'Xu hướng nghề nghiệp năm 2026 là gì?'})['grounded'])
        self.provider.assert_not_called()
    def test_profile_recommendation_ai(self):
        self.provider.return_value={'message':'AI tư vấn và lộ trình','ai_powered':True,'grounded':False,'sources':[],'match_reasons':[{'code':'HUST','reason':'Liên hệ lập trình với khoa học máy tính','input_matches':['Lập trình'],'cautions':['Chưa có điểm dự kiến'] }]}
        result=recommend({'profile':{'interests':'Lập trình','field':'cntt','region':'bac'},'use_web':False})
        self.assertTrue(result['ai_powered']);self.assertTrue(result['universities'])
        self.assertIn('90 NGÀY',self.provider.call_args.args[0])
    def test_invalid_profile(self):
        for payload in [None,{}, {'profile':[]},{'profile':{'interests':2}},{'profile':{'region':'wrong'}}]:
            self.assertEqual(recommend(payload)[1],400)
    def test_private_content_not_persisted(self):
        with database.connect() as con:names={r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(names,{'universities','university_fields','trend_cache'})
    def test_admissions_years_and_units(self):
        from admissions import school_admissions
        result=school_admissions('HUST')
        self.assertEqual(result['years'],[2024,2025,2026])
        self.assertEqual(len(result['scores']),82)
        self.assertTrue(all(row['source_url'].startswith('https://') for row in result['scores']+result['tuition']))
        self.assertTrue(any(row['year']==2026 and row['unit']=='VND/TCHP' for row in result['tuition']))
    def test_no_fabricated_missing_years(self):
        from admissions import school_admissions
        result=school_admissions('CMC')
        self.assertEqual(result['scores'],[]);self.assertEqual(result['tuition'],[])
        self.assertEqual(school_admissions('DOES_NOT_EXIST')[1],404)
    def test_thumbnail_rejects_unsafe_urls(self):
        import xml.etree.ElementTree as ET
        item=ET.fromstring('<item><description>&lt;img src="https://evil.example/image.jpg"&gt;</description></item>')
        self.assertIsNone(trends.article_thumbnail(item))
    def test_visible_summary_preserves_scale_and_fee_unit(self):
        result=database.search_universities(name='HUST')[0]['admissions_summary']
        self.assertEqual(result['tuition'][0]['unit'],'VND/TCHP')
        self.assertEqual(result['tuition'][0]['min'],620000)
        ulis=database.search_universities(name='ULIS')[0]['admissions_summary']
        self.assertEqual(ulis['scores'][0]['groups'][0]['scale'],40)
        self.assertEqual(ulis['scores'][1]['groups'][0]['scale'],30)
    @patch('ai_advisor._request')
    def test_structured_school_reasons_validate_catalogue(self,request):
        data={'message':'Tư vấn và lộ trình','matches':[{'code':'HUST','reason':'Phù hợp với lập trình Python','input_matches':['lập trình Python'],'cautions':['Thiếu điểm dự kiến']},{'code':'FAKE','reason':'Invented','input_matches':[],'cautions':[]}]}
        request.return_value=({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':json.dumps(data,ensure_ascii=False)}]}}]},None)
        result=ai_advisor.answer_with_ai('Tư vấn',{'structured_recommendation':True,'profile':{'interests':'lập trình Python'}},[{'short_name':'HUST'}])
        self.assertEqual([r['code'] for r in result['match_reasons']],['HUST'])
        self.assertIn('responseSchema',request.call_args.args[0]['generationConfig'])
    @patch('ai_advisor._request')
    def test_broken_structured_output_never_becomes_fake_reasons(self,request):
        request.return_value=({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'invalid JSON'}]}}]},None)
        result=ai_advisor.answer_with_ai('Tư vấn',{'structured_recommendation':True},[])
        self.assertEqual(result[1],503)
    def test_recommendation_does_not_show_unexplained_schools(self):
        self.provider.return_value={'message':'Bạn cần làm rõ sở thích','ai_powered':True,'match_reasons':[]}
        result=recommend({'profile':{'field':'cntt'},'use_web':False})
        self.assertEqual(result['universities'],[])
    def candidate(self,metadata=None):
        return {'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'Nhu cầu kỹ năng dữ liệu thay đổi.'}]},'groundingMetadata':metadata or {}}]}

    @patch('ai_advisor._request')
    def test_grounding_requires_actual_evidence(self,request):
        request.return_value=(self.candidate(),None)
        self.assertFalse(ai_advisor.grounded_answer('Xu hướng nghề?')['grounded'])
        self.assertIn('googleSearch',request.call_args.args[0]['tools'][0])

    @patch('ai_advisor._request')
    def test_grounding_cites_vietnamese_segments(self,request):
        request.return_value=(self.candidate({'groundingChunks':[{'web':{'uri':'https://www.ilo.org/report','title':'ILO'}}], 'groundingSupports':[{'segment':{'text':'Nhu cầu kỹ năng dữ liệu thay đổi.'},'groundingChunkIndices':[0]}],'webSearchQueries':['xu hướng nghề Việt Nam 2026'],'searchEntryPoint':{'renderedContent':'<div>Google Search</div>'}}),None)
        result=ai_advisor.grounded_answer('Xu hướng nghề?')
        self.assertTrue(result['grounded']);self.assertIn('[1]',result['message'])
        self.assertEqual(result['sources'][0]['url'],'https://www.ilo.org/report')
        self.assertTrue(result['checked_at'])

    @patch('ai_advisor._request')
    def test_grounding_rejects_script_sources(self,request):
        request.return_value=(self.candidate({'groundingChunks':[{'web':{'uri':'javascript:alert(1)','title':'fake'}}],'groundingSupports':[{'segment':{'text':'Nhu cầu kỹ năng dữ liệu thay đổi.'},'groundingChunkIndices':[0]}]}),None)
        result=ai_advisor.grounded_answer('Xu hướng nghề?')
        self.assertFalse(result['grounded']);self.assertEqual(result['sources'],[])

    @patch('ai_advisor._request',return_value=(None,'quota_exceeded'))
    def test_quota_error_is_not_reported_as_live(self,request):
        result=ai_advisor.grounded_answer('Xu hướng nghề?')
        self.assertFalse(result['grounded']);self.assertFalse(result['ai_powered'])
        self.assertIsNone(result['checked_at']);self.assertIn('429',result['message'])

    def test_feed_dates(self):
        self.assertEqual(trends.parse_publication_date('10/27/2026 4:49:00\u202fPM'),'2026-10-27T09:49:00+00:00')
        self.assertIsNone(trends.parse_publication_date('not a date'))

    def test_two_hour_interval(self): self.assertEqual(trends.INTERVAL,7200)

    @patch('trends.collect_news',return_value=([{'title':'Xu hướng nghề mới','url':'https://vnexpress.net/test','publisher':'VnExpress','published_at':None,'collected_at':'2026-10-27T00:00:00+00:00'}],[]))
    @patch('trends.grounded_answer',return_value={'message':'Hết hạn mức','grounded':False,'checked_at':None})
    def test_rss_still_updates_when_gemini_is_unavailable(self,ground,news):
        trends._refresh_lock.acquire();trends._refresh()
        snapshot=trends.get_snapshot()
        self.assertEqual(len(snapshot['articles']),1)
        self.assertEqual(snapshot['search_error'],'Hết hạn mức')
        self.assertIsNone(snapshot['analysis'])
        self.assertFalse(snapshot['refreshing'])

    @patch('trends.collect_news',return_value=([],['VnExpress','Tuổi Trẻ']))
    @patch('trends.grounded_answer',return_value={'message':'Hết hạn mức','grounded':False,'checked_at':None})
    def test_failed_refresh_keeps_previous_snapshot(self,ground,news):
        before=trends.get_snapshot()
        trends._refresh_lock.acquire();trends._refresh()
        after=trends.get_snapshot()
        self.assertEqual(before['updated_at'],after['updated_at'])
        self.assertEqual(before['articles'],after['articles'])
        self.assertTrue(after['refresh_error'])

    def test_api_status_never_contains_secret(self):
        with patch('ai_advisor.GEMINI_API_KEY','test-secret-not-for-output'):
            result=ai_advisor.api_status()
            self.assertTrue(result['configured'])
            self.assertNotIn('test-secret-not-for-output',json.dumps(result))

if __name__=='__main__': unittest.main(verbosity=2)
