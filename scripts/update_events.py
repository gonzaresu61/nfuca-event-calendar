#!/usr/bin/env python3
"""Collect public seminar dates conservatively. Never use publication dates as events."""
from __future__ import annotations
import argparse
import json
import re
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
SOURCE = 'https://www.nfuca-tokyo.jp/seminar.html'
CATEGORIES = ['東京ブロック','連合会・共済連','南エリア','総武エリア','武蔵野エリア','北甲エリア']
DATE_RE = re.compile(r'(?:(?P<year>20\d{2})\s*[年/.-]\s*)?(?P<month>\d{1,2})\s*[月/]\s*(?P<day>\d{1,2})\s*日?(?:\s*\((?P<weekday>[月火水木金土日])\))?')
DATE_LABEL = re.compile(r'^[\s◯○〇・◆【\[■]*(?:開催日時|開催日程|開催日|日時|日程)\s*[】\]:：]')
DEADLINE_LABEL = re.compile(r'(?:申[し]?込[み]?[^。\n]{0,10})?(?:締[め]?切[り]?|〆切)')
TIME_RE = re.compile(r'\d{1,2}\s*[:時]\s*\d{0,2}\s*分?(?:\s*[~〜～-]\s*\d{1,2}\s*[:時]\s*\d{0,2}\s*分?)?')


def norm(value):
    return unicodedata.normalize('NFKC',value).replace('\u200b','').replace('\ufeff','')


def clean_title(value):
    return re.sub(r'【[^】]*】','',norm(value)).strip()


def title_key(value):
    return re.sub(r'[\s\u3000!！「」()（）:：]','',clean_title(value))


def read_html(raw):
    return BeautifulSoup(raw, 'html.parser')


def body_lines(soup):
    body=soup.select_one('#contArea > div.clearfix')
    if body is None:
        raise ValueError('記事本文の構造が変わりました')
    for br in body.find_all('br'):
        br.replace_with('\n')
    # Inline emphasis must not split the date, unlike get_text("\\n").
    return [re.sub(r'\s+',' ',norm(s)).strip() for s in body.get_text().splitlines() if s.strip()]


def parsed_date(match, reference):
    y=int(match['year']) if match['year'] else reference.year
    m,d=int(match['month']),int(match['day'])
    if not match['year'] and reference.month >= 11 and m<=2:
        y+=1
    result=date(y,m,d)
    if match['weekday'] and '月火水木金土日'[result.weekday()]!=match['weekday']:
        raise ValueError('日付と曜日が一致しないため原文確認が必要です')
    return result


def date_span(line, reference):
    matches=list(DATE_RE.finditer(line))
    if not matches:
        return None
    first=parsed_date(matches[0],reference)
    end=first
    tail=line[matches[0].end():]
    # A date after a time is allowed, e.g. 6月20日13:00〜21日16:00.
    range_marker=re.search(r'[~〜～−-]',tail)
    if len(matches)>1:
        if not range_marker:
            raise ValueError('複数の開催日は個別確認が必要です')
        end=parsed_date(matches[1],first)
    elif range_marker:
        short=re.search(r'[~〜～−-]\s*(\d{1,2})\s*日(?:\s*\(([月火水木金土日])\))?',tail)
        if short:
            end=date(first.year,first.month,int(short[1]))
            if short[2] and '月火水木金土日'[end.weekday()]!=short[2]:
                raise ValueError('終了日と曜日が一致しません')
    if end<first or (end-first).days>14:
        raise ValueError('開催期間を確認してください')
    return first,end


def extract_article(raw, url, category):
    soup=read_html(raw)
    heading=soup.select_one('.titleArea h2')
    posted=soup.select_one('.titleArea .day')
    if not heading or not posted:
        raise ValueError('記事見出しまたは掲載日が取得できません')
    full_title=norm(heading.get_text(strip=True))
    title=clean_title(full_title)
    if '開催報告' in full_title:
        return [], None
    publication_match=DATE_RE.search(norm(posted.get_text(strip=True)))
    if not publication_match:
        raise ValueError('掲載年を確認できません')
    # Publication date supplies a year only. It is never emitted as an event date.
    published=parsed_date(publication_match,date(2000,1,1))
    lines=body_lines(soup)
    article_id=re.search(r'news_detail_(\d+)',url)[1]
    candidates=[(i,line) for i,line in enumerate(lines) if DATE_LABEL.search(line) and DATE_RE.search(line)]
    if not candidates:
        # Explicit narrative opening, with date + time + a nearby statement of holding.
        candidates=[(i,line) for i,line in enumerate(lines[:5]) if DATE_RE.search(line) and TIME_RE.search(line) and '開催' in ''.join(lines[i:i+4]) and not DEADLINE_LABEL.search(line)]
    relevant=bool(candidates or re.search(r'開催|参加|セミナー|学習会|ミーティング|交流会|委員会|相談会',full_title))
    if not candidates:
        if relevant:
            return [],dict(title=title,category=category,sourceUrl=url,publishedAt=published.isoformat(),reason='本文から開催日を確定できません。添付資料を含め原文をご確認ください。')
        return [],None
    if article_id=='2520':
        # An aggregate announcement superseded by two independently updated detailed notices.
        return [],dict(title=title,category=category,sourceUrl=url,publishedAt=published.isoformat(),reason='複数企画の開催要項を確認してください。',supersededBy=['2532','2533'])
    if len(candidates)>1 and article_id!='2488':
        return [],dict(title=title,category=category,sourceUrl=url,publishedAt=published.isoformat(),reason='複数の日程を含むため企画ごとの確認が必要です。')
    if article_id=='2488' and len(candidates)!=3:
        raise ValueError('複数企画の記事構成が変わりました')
    deadlines=[]
    deadline_notes=[]
    for i,line in enumerate(lines):
        if not DEADLINE_LABEL.search(line):
            continue
        scope=line if DATE_RE.search(line) else ' '.join(lines[i:i+2])
        match=DATE_RE.search(scope)
        if match:
            try:
                d=parsed_date(match,published)
                t=TIME_RE.search(scope[match.end():])
                deadlines.append((d.isoformat(),t[0].replace(' ','') if t else ('終日' if '終日' in scope else '')))
            except ValueError as error:
                deadline_notes.append(str(error))
    unique_dates={d for d,_ in deadlines}
    deadline=None;deadline_time=''
    if len(unique_dates)==1:
        deadline,deadline_time=deadlines[-1]
    elif len(unique_dates)>1:
        deadline_notes.append('異なる締切日が複数記載されているため締切を確認してください')
    events=[]
    for n,(i,line) in enumerate(candidates):
        start,end=date_span(line,published)
        scope=lines[i:(candidates[n+1][0] if n+1<len(candidates) else min(len(lines),i+8))]
        venue=''
        for text in scope[1:]:
            v=re.match(r'^[◯○〇・◆【\[■]*(?:場所|会場|形式)\s*[】\]:：]\s*(.+)',text)
            if v:
                venue=v[1];break
            if re.match(r'オンライン\s*\(',text):
                venue=text;break
        times=TIME_RE.findall(line[DATE_RE.search(line).end():])
        if not times and i+1<len(lines) and re.match(r'^\d{1,2}:',lines[i+1]):
            times=TIME_RE.findall(lines[i+1])
        display_time=' / '.join(t.strip() for t in times)
        suffix=['事前学習会','ツアー当日','事後交流会'][n] if article_id=='2488' else ''
        title_here=f'{title}｜{suffix}' if suffix else title
        event_deadline=deadline
        if deadline and deadline>start.isoformat():
            event_deadline=None
            deadline_notes.append('開催日より後の締切が記載されているため確認が必要です')
        events.append(dict(id=f'{article_id}-{n}',title=title_here,category=category,startDate=start.isoformat(),endDate=end.isoformat(),time=display_time,venue=venue,deadline=event_deadline,deadlineTime=deadline_time if event_deadline else '',sourceUrl=url,deadlineSourceUrl=url if event_deadline else None,publishedAt=published.isoformat(),sources=[url],evidence={'date':line,'deadline':[s for s in lines if DEADLINE_LABEL.search(s) and DATE_RE.search(s)]},notes=list(set(deadline_notes))))
    return events,None


def merge_events(events):
    grouped={}
    for e in sorted(events,key=lambda x:(x['publishedAt'],int(x['id'].split('-')[0]))):
        key=(title_key(e['title']),e['startDate'],e['endDate'],e['category'])
        previous=grouped.get(key)
        if previous:
            e['sources']=list(dict.fromkeys(previous['sources']+e['sources']))
            # New notices often omit a deadline. Keep its explicitly linked older source.
            if not e['deadline'] and not e['notes'] and previous['deadline']:
                e['deadline']=previous['deadline'];e['deadlineTime']=previous['deadlineTime'];e['deadlineSourceUrl']=previous['deadlineSourceUrl']
            if not e['venue']:e['venue']=previous['venue']
        grouped[key]=e
    return sorted(grouped.values(),key=lambda x:(x['startDate'],x['time'],x['title']))


def fetch(url):
    if urlparse(url).hostname!='www.nfuca-tokyo.jp':
        raise ValueError('想定外の取得先です')
    last=None
    for attempt in range(3):
        try:
            req=Request(url,headers={'User-Agent':'NUFCA-Event-Calendar/1.0 (+public event dates; weekly refresh)'})
            with urlopen(req,timeout=30) as r:
                return r.read().decode('utf-8')
        except Exception as error:
            last=error
            if attempt<2:time.sleep(1+attempt)
    raise RuntimeError(f'取得に失敗: {url}: {last}')


def collect(cache=None):
    urls={}
    for index in range(7):
        url=SOURCE if index==0 else f'https://www.nfuca-tokyo.jp/news/cate_list.php?a=cate_list&news_cate_id={index}'
        raw=(cache/('seminar.html' if index==0 else f'category-{index}.html')).read_text() if cache else fetch(url)
        soup=read_html(raw)
        anchors=soup.select('article a[href]')
        if not anchors:
            raise RuntimeError(f'一覧の記事が見つかりません: {url}')
        for a in anchors:
            href=urljoin(url,a['href'])
            if not re.search(r'/news/news_detail_\d+\.html$',href):continue
            if index:
                category=CATEGORIES[index-1]
            else:
                area=a.find_parent(class_='newsArea')
                if area is None:raise RuntimeError('エリアを確認できません')
                category=CATEGORIES[int(area['id'][-2:])-1]
            urls[href]=category
    path=ROOT/'dist/data/events.json'
    previous=json.loads(path.read_text()) if path.exists() else {}
    for item in previous.get('events',[])+previous.get('unconfirmed',[]):
        for url in item.get('sources',[item['sourceUrl']]):
            urls.setdefault(url,item['category'])
    def load(item):
        url,category=item
        ident=re.search(r'news_detail_(\d+)',url)[1]
        raw=(cache/f'article-{ident}.html').read_text() if cache else fetch(url)
        return url,category,raw
    # If any fetch fails, abort and retain the last successfully published calendar.
    with ThreadPoolExecutor(max_workers=3) as pool:
        articles=list(pool.map(load,urls.items()))
    now=datetime.now(ZoneInfo('Asia/Tokyo'))
    today=now.date().isoformat()
    events=[];unconfirmed=[];warnings=[];parsed_ids=set()
    for url,category,raw in articles:
        try:
            found,unknown=extract_article(raw,url,category)
            parsed_ids.add(re.search(r'news_detail_(\d+)',url)[1]) if found else None
            events.extend(found)
            if unknown:unconfirmed.append(unknown)
        except (ValueError,TypeError,AttributeError) as error:
            s=read_html(raw);heading=s.select_one('.titleArea h2')
            posted=s.select_one('.titleArea .day')
            pm=DATE_RE.search(norm(posted.get_text(strip=True))) if posted else None
            try:
                published_at=date(int(pm['year']),int(pm['month']),int(pm['day'])).isoformat() if pm and pm['year'] else today
            except ValueError:
                published_at=today
            unknown=dict(title=clean_title(heading.get_text(strip=True)) if heading else '記事を確認してください',category=category,sourceUrl=url,publishedAt=published_at,reason=str(error))
            unconfirmed.append(unknown);warnings.append(url)
    unconfirmed=[u for u in unconfirmed if not (u.get('supersededBy') and all(i in parsed_ids for i in u['supersededBy'])) and u['publishedAt']>=(now.date()-timedelta(days=180)).isoformat()]
    merged=[e for e in merge_events(events) if e['endDate']>=today]
    known_keys={title_key(e['title']) for e in merged}
    unconfirmed=[u for u in unconfirmed if title_key(u['title']) not in known_keys]
    for e in merged:
        if e['notes']:
            unconfirmed.append(dict(title=e['title']+'（締切確認）',category=e['category'],sourceUrl=e['sourceUrl'],publishedAt=e['publishedAt'],reason=' / '.join(e['notes'])))
    warnings=[url for url in warnings if any(u['sourceUrl']==url for u in unconfirmed)]
    result=dict(generatedAt=now.isoformat(timespec='seconds'),sourceUrl=SOURCE,schedule='毎週日曜日 09:17（日本時間）',events=merged,unconfirmed=unconfirmed,warnings=warnings,articleCount=len(articles))
    for e in result['events']:
        assert date.fromisoformat(e['startDate'])<=date.fromisoformat(e['endDate'])
        if e['deadline']:assert date.fromisoformat(e['deadline'])<=date.fromisoformat(e['startDate'])
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    tmp.replace(path)
    print(f'Checked {len(articles)} articles; {len(merged)} upcoming events; {len(unconfirmed)} require review')
    for e in merged:print(e['startDate'],e['endDate'],e['title'],'deadline:',e['deadline'])
    for u in unconfirmed:print('REVIEW',u['title'],u['reason'])
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cache-dir',type=Path)
    args=parser.parse_args()
    collect(args.cache_dir)
