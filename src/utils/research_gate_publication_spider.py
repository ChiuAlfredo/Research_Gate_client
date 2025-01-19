import csv
import datetime
import ssl
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Optional

import requests
from bs4 import BeautifulSoup
from dateutil import parser
from requests.adapters import HTTPAdapter
from sqlalchemy import func, insert

from utils.model import (ResearchGatePublicationItem, create_session,
                         defi_research_gate_publication_table,
                         defi_search_history_table)

cookies = {}
headers = {}

class TLSAdapter(HTTPAdapter):
    def __init__(self, tls_version=None, **kwargs):
        self.tls_version = tls_version
        self.ssl_context = ssl.create_default_context()
        if tls_version:
            self.ssl_context.minimum_version = tls_version
        super().__init__(**kwargs)

    def init_poolmanager(self, *args, **kwargs):
        kwargs["ssl_context"] = self.ssl_context
        return super().init_poolmanager(*args, **kwargs)

            
def parse_detail(page,keyword):
    max_try_num = 0
    while True:
        adapter = TLSAdapter(tls_version=ssl.TLSVersion.TLSv1_3)
        session = requests.Session()
        session.mount("https://", adapter)
        url = f"https://www.researchgate.net:443/search/publication?q={keyword}&page={page}"
        response = session.get(url, headers=headers, cookies=cookies, timeout=10)
        if max_try_num == 10:
            raise Exception('驗證錯誤：超過最大嘗試')
        if response.status_code != 200:
            max_try_num += 1
            continue
        break
    soup = BeautifulSoup(response.text, 'lxml')
    items = []
    for sing_publications in soup.select('[class="nova-legacy-c-card__body nova-legacy-c-card__body--spacing-inherit"]'):
        title = sing_publications.select('[itemprop="headline"] a')[0].text
        link = "https://www.researchgate.net/" + sing_publications.select('[itemprop="headline"] a')[0]['href'].split('?')[0]#.split('_')[0]
        publication_type = sing_publications.select(
            '[class="nova-legacy-e-badge nova-legacy-e-badge--color-green nova-legacy-e-badge--display-block nova-legacy-e-badge--luminosity-high nova-legacy-e-badge--size-l nova-legacy-e-badge--theme-solid nova-legacy-e-badge--radius-m nova-legacy-v-publication-item__badge"]')[0].text
        item = get_publication_detail(session, title, link, publication_type)
        items.append(item)
    return items

            
def get_publication_detail(session, title, link, publication_type):
    response = session.get(link, headers=headers, cookies=cookies, timeout=10)
    soup = BeautifulSoup(response.text, 'lxml')
    detail_soup = soup.select('[class="research-detail-header-section__metadata-after-square-logo"] div')
    
    item = ResearchGatePublicationItem()
    authors = ', '.join([i.text for i in soup.select(
        '[class="nova-legacy-v-person-list-item__align"] [class="nova-legacy-e-text nova-legacy-e-text--size-m nova-legacy-e-text--family-display nova-legacy-e-text--spacing-none nova-legacy-e-text--color-inherit nova-legacy-v-person-list-item__title"]')])
    abstract_elements = soup.select(
        '[class="nova-legacy-e-text nova-legacy-e-text--size-m nova-legacy-e-text--family-sans-serif nova-legacy-e-text--spacing-none nova-legacy-e-text--color-grey-800 research-detail-middle-section__abstract"]')
    
    abstract = ','.join(element.get_text(strip=True) for element in abstract_elements) if abstract_elements else ''
        
    # 確保 detail_soup 存在並提取 publication_date 和 year
    if detail_soup and len(detail_soup) > 0:
        publication_date = detail_soup[0].select('[class="nova-legacy-e-list__item"]')[0].text
        year = publication_date.split(' ')[1]
    else:
        publication_date = ''
        year = ''
        
    item['title'] = title
    item['link'] = link
    item['publication_type'] = publication_type
    item['publication_date'] = publication_date
    item['year'] = year
    item['abstract'] = abstract
    item['authors'] = authors
    if publication_type == 'Article':
        doi = detail_soup[1].text if len(detail_soup) >= 2 else ''
        item['doi'] = doi
        item['patent'] = ''
    elif publication_type == 'Patent':
        patent = detail_soup[2].text if len(detail_soup) > 2 else ''
        item['doi'] = ''
        item['patent'] = patent
    else:  # 預設處理 Preprint 和未知類型
        item['doi'] = ''
        item['patent'] = ''
    return item

def parse_date(date_str):
    """將日期字符串轉換為 datetime.date 對象"""
    if not date_str:
        return None  # 如果日期字符串為空，返回 None

    try:
        # 使用 dateutil.parser 來解析常見的日期格式
        default_date = datetime.datetime(2024, 12, 1)
        parsed_date = parser.parse(date_str, default=default_date)
        return parsed_date  # 轉換為 date 對象
    except Exception as e:
        # 捕捉解析錯誤，並記錄錯誤信息
        print(f"Error parsing date '{date_str}': {str(e)}")
        return None
    
def log_search_history(
    trackid: str,
    function_name: str,
    keyword: str,
    keyword_type: str,
    status: str,
    other: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
) -> None:
    """
    在 search_history 資料表中新增一筆查詢紀錄。

    :param trackid: 查詢追蹤 ID
    :param user_name: 用戶名稱
    :param user_id: 用戶 ID
    :param function_name: 功能名稱
    :param keyword: 查詢關鍵字
    :param keyword_type: 關鍵字類型
    :param status: 查詢結果狀態
    :param other: 其他補充資訊（可選）
    :param start_date: 用戶查詢的開始時間（可選）
    :param end_date: 用戶查詢的結束時間（可選）
    """
    try:
        # 獲取資料表和會話
        search_history_table = defi_search_history_table()
        session = create_session()

        # 建立插入語句
        stmt = insert(search_history_table).values(
            trackid=trackid,
            function_name=function_name,
            keyword=keyword,
            keyword_type=keyword_type,
            status=status,
            other=other,
            start_date=start_date,
            end_date=end_date,
            created_at=func.now(),  # 記錄創建時間
            updated_at=func.now()   # 記錄最後更新時間
        )

        # 執行插入操作
        session.execute(stmt)
        session.commit()

    except Exception as e:
        # 捕捉錯誤並記錄日誌
        raise

    finally:
        # 確保關閉會話
        session.close()
def write_history_pub(keywords,trackid):

    log_search_history(
        trackid=trackid,
        function_name="research-gate-publication",
        keyword=keywords,
        keyword_type="AND",
        status="Success",
        other=None,
    )


def research_publication(keywords,cf_clearance, user_agent,trackid):
    global cookies, headers

    

    cookies = {"cf_clearance":cf_clearance}
    headers = {"User-Agent":user_agent}
    fieldnames = [
                'title', 'link', 'year', 'publication_type', 'publication_date',
                'doi', 'abstract', 'authors', 'patent', 'created_at', 'updated_at','trackid'
            ]
    with open('research_gate_publication_spider_output.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        

        with ThreadPoolExecutor(max_workers=8) as executor:
            parse_detail_with_keyword = partial(parse_detail, keyword=keywords)
            results = executor.map(parse_detail_with_keyword, range(1, 101))
        
        research_gate_publication = defi_research_gate_publication_table()
        session = create_session()
        for items in results:
            for item in items:
                publication_data = {
                    'title': item.get('title'),
                    'link': item.get('link'),
                    'year': item.get('year'),
                    'publication_type': item.get('publication_type'),
                    'publication_date': parse_date(item.get('publication_date')),
                    'doi': item.get('doi', ''),  # 預設 DOI 為空字符串
                    'abstract': item.get('abstract'),
                    'authors': item.get('authors'),
                    'patent': item.get('patent', ''),  # 預設 patent 為空字符串
                    'created_at': datetime.datetime.now(),
                    'updated_at': datetime.datetime.now(),
                    'trackid': trackid,
                }
                print(publication_data)
                writer.writerow(publication_data)
                # 將數據插入資料庫
                session.execute(insert(research_gate_publication).values(publication_data))
                session.commit()
        session.close()
            

# if __name__ == '__main__':
#     # cf_clearance 一定要是經過cloudflare驗證的，如果沒有辦法觸發cloudflare 那就先跑一次
#     keyword = 'antenna'
#     cf_clearance = '_FDaXi2lH692S_bFfYWJLRALzHjqTZxILlYHhV5L7kU-1735883763-1.2.1.1-aILIglYP5Ab9xJKs.fWKKyB0kAAbQsH3OJIyq3lr4sbg.PhlPAR18cYDzBdtj5UQf2r27B2Qw3maR3mz.RfhGRpvcMKap08pXazoAM2Y8IkL0ZOOEipzzWYSho1gek6y9xPKpBStoim_wslOK4knbsdeabaQVfuDuHo9S.NKeb9GX9nROuHWSogex6HbTpM5CXP0y7VcsQIFOoNpYsB671GHi9cGQvTpam6XNb6kV6BF9Z9a7kt8S0R3yIkNZGD.SOn36X5rGcUDjprieHhH0ZzAhWmjzs40WdaGvqYQehVyket3a5_aWhoW_eNIk58_AuscAmglHlI2tHlNPnykTqn52nGIXkOTHwjHeCkE7iEXC2NAAGKd4uc75qLaFqI0VXNL8Aj03gRSqrYP8.vGcU45erv7AYqo596yIYamXFOrs2OgGjvUJQ08R1tcM3lv'
#     user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'

    
#     main()