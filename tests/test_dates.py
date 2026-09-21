import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from update_events import extract_article, merge_events, date_span, fetch

def article(body,title='【開催案内】テスト交流会',posted='2026年09月04日(金)'):
    return f'<div id="contArea"><div class="titleArea"><h2>{title}</h2><span class="day">{posted}</span></div><div class="clearfix">{body}</div></div>'
def extract(body,id='1000',**kw):
    return extract_article(article(body,**kw),f'https://www.nfuca-tokyo.jp/news/news_detail_{id}.html','東京ブロック')

class DateTests(unittest.TestCase):
    def test_publication_is_never_event_date(self):
        events,unknown=extract('日程は添付資料をご確認ください。')
        self.assertEqual(events,[])
        self.assertIsNotNone(unknown)
    def test_distinct_deadline_and_inline_tags(self):
        events,_=extract('日時：９/２６（土）10:00～12:00<br>参加申込<strong>〆切：9月20日（日）23:59</strong>まで')
        self.assertEqual(events[0]['startDate'],'2026-09-26')
        self.assertEqual(events[0]['deadline'],'2026-09-20')
        self.assertEqual(events[0]['deadlineTime'],'23:59')
    def test_multi_day_and_year_boundary(self):
        self.assertEqual(date_span('2026年10月10日(土)～11日(日)',date(2026,7,15)),(date(2026,10,10),date(2026,10,11)))
        self.assertEqual(date_span('1月9日(土)',date(2026,12,10))[0],date(2027,1,9))
    def test_mismatched_weekday_rejected(self):
        with self.assertRaises(ValueError):date_span('2025年6月20日(土)',date(2026,3,21))
    def test_latest_extension_wins_and_sources_remain(self):
        old,_=extract('日時：9/26(土)13:00～17:30<br>参加申込〆切：9月20日(日)23:59','1000')
        new,_=extract('日時：9/26(土)13:00～17:30<br>参加申込〆切：9月24日(木)23:59','1001',posted='2026年09月11日(金)')
        merged=merge_events(old+new)
        self.assertEqual(len(merged),1)
        self.assertEqual(merged[0]['deadline'],'2026-09-24')
        self.assertEqual(len(merged[0]['sources']),2)
    def test_missing_new_deadline_keeps_cited_original(self):
        old,_=extract('日時：10月8日(木)18:30～20:30<br>申込締切：10⽉5⽇(⽉)終⽇','1000')
        new,_=extract('日時：10月8日(木)18:30～20:30','1001',posted='2026年09月18日(金)')
        merged=merge_events(old+new)[0]
        self.assertEqual(merged['deadline'],'2026-10-05')
        self.assertIn('1000',merged['deadlineSourceUrl'])
        self.assertIn('1001',merged['sourceUrl'])
    def test_narrative_opening(self):
        events,_=extract('9/28(月)18:00~19:00に<br>オンライン(Zoom)にて<br>相談会を開催いたします。')
        self.assertEqual(events[0]['startDate'],'2026-09-28')
    def test_multiple_deadlines_are_not_guessed(self):
        events,_=extract('日時：9/26(土)10:00～12:00<br>一次締切：9月20日(日)<br>二次締切：9月24日(木)')
        self.assertIsNone(events[0]['deadline'])
        self.assertTrue(events[0]['notes'])
    def test_multiple_events_need_explicit_sections(self):
        events,unknown=extract('日時：9/26(土)10:00～12:00<br>日時：10/8(木)18:30～20:30')
        self.assertEqual(events,[])
        self.assertIsNotNone(unknown)
    def test_reports_include_historical_events(self):
        events,unknown=extract('日時：9/26(土)10:00～12:00',title='【開催報告】交流会')
        self.assertEqual(events[0]["startDate"],"2026-09-26");self.assertIsNone(unknown)
    def test_report_also_has_named_next_event(self):
        events,_=extract('本日は8月8日(土)に開催されました。<br>次回の武蔵野エリア連帯「第3回 集まれ！むさっしーず」は11月14日(土)に開催予定です！',id='2536',title='【開催報告】第2回 集まれ！むさっしーず')
        self.assertEqual([e['startDate'] for e in events],['2026-08-08','2026-11-14'])
        self.assertIn('第3回',events[1]['title'])
    def test_report_does_not_replace_detailed_notice(self):
        old,_=extract('日時：9/26(土)10:00～12:00<br>申込締切：9月20日(日)','1000')
        report,_=extract('9/26(土)に開催されたテスト交流会です。','1001',title='【開催報告】テスト交流会',posted='2026年09月28日(月)')
        merged=merge_events(old+report)
        self.assertEqual(len(merged),1)
        self.assertEqual(merged[0]['deadline'],'2026-09-20')
        self.assertEqual(merged[0]['time'],'10:00~12:00')
    def test_continuation_line_and_middle_dot_day_range(self):
        events,_=extract('日時：5月30日(土)13:00～17:00<br>～31日(日)10:00～16:00')
        self.assertEqual(events[0]['endDate'],'2026-05-31')
        self.assertEqual(date_span('2026年7月11日(土)13:00-18:00・12日(日)10:00～12:30',date(2026,6,1))[1],date(2026,7,12))
    def test_fiscal_year_date_and_prose_deadline(self):
        events,_=extract('日時：2026年度6月11日(木)18:00-19:30<br>以下のリンクから6月9日(火)までにお申し込みください。')
        self.assertEqual(events[0]['startDate'],'2026-06-11')
        self.assertEqual(events[0]['deadline'],'2026-06-09')
    def test_five_peace_now_sections_are_distinct(self):
        body='<br>'.join(['☆日時：8/31(月)13時集合～9/2(水)15時解散']*3+['日時：8月5日(水)19時～21時','日時：9月17日(木)19時～21時'])
        events,_=extract(body,id='2484')
        self.assertEqual(len(events),5)
        self.assertEqual(len({e['title'] for e in events}),5)
    def test_shared_program_selects_matching_time(self):
        events,_=extract('日時：7月11日(土)<br>10:00～12:30 第3回ブロック運営委員会<br>12:30～13:30 お昼休憩<br>13:30～17:30 新学期スタート会議',title='【開催案内】新学期スタート会議2026')
        self.assertEqual(events[0]['time'],'13:30~17:30')
    def test_transport_failure_aborts(self):
        with patch('update_events.urlopen',side_effect=TimeoutError),patch('update_events.time.sleep'):
            with self.assertRaises(RuntimeError):fetch('https://www.nfuca-tokyo.jp/seminar.html')

if __name__=='__main__':unittest.main()
