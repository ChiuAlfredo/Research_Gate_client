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
            print('驗證錯誤：超過最大嘗試')
            return 
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
    abstract = abstract_elements[0].text if abstract_elements else ''

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
        patent = detail_soup[2].text if len(detail_soup) >= 2 else ''
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

def research_publication(keywords,cf_clearance, user_agent):
    global cookies, headers

    

    cookies = {"cf_clearance":cf_clearance}
    headers = {"User-Agent":user_agent}
    fieldnames = [
                'title', 'link', 'year', 'publication_type', 'publication_date',
                'doi', 'abstract', 'authors', 'patent', 'created_at', 'updated_at'
            ]
    with open('research_gate_publication_spider_output.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
        
        for keyword in keywords:
            trackid = uuid.uuid1().hex
            log_search_history(
                trackid=trackid,
                function_name="research-gate-publication",
                keyword=keywords,
                keyword_type="AND",
                status="Success",
                other=None,
            )
            with ThreadPoolExecutor(max_workers=8) as executor:
                parse_detail_with_keyword = partial(parse_detail, keyword=keyword)
                results = executor.map(parse_detail_with_keyword, range(1, 11))
            
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
import requests

burp0_url = "https://www.researchgate.net/publication/335116843_A_7-GHz_Fast-Lock_Two-Step_Time-to-Digital_Converter-Based_All-Digital_DLL"
burp0_cookies = {"__cf_bm": "QcwT2fxhgZWlJzv0v8oIRVBQfDi1hp8r1qKmSvn7ztw-1737300294-1.0.1.1-WxHIYfeZWNWE6Td6OWWGw8lomc4Al8QzsBKn6c_hnBqnRpuI52h_7EVoppfqFKTMQesXwbLgc.sEn.LY69f0IA", "cirgu": "_1_TZZ%2FcXCFiEmNs4pigbebX0e1DtbSQHNvjbuawT0LITA0co%2FWmSX8u8cx3lBk0wMWhh4s", "did": "eaOOE0wZD0GBuWNLzjQlbgwzXK18jucWAP3I1fAFJvNRSXKz0Y0eLZHOrXVYxpQO", "ptc": "RG1.7598713900902995424.1737222545", "_cfuvid": "FM.dfWWStkUDhsgMY6Ru0JkIvcRhz8rd54gIvcDk8f4-1737300294562-0.0.1.1-604800000", "_gid": "GA1.2.92274840.1737300291", "_gat": "1", "cf_clearance": "gbze_CvCiolQgc2XMzwdktWY2GIPWY9CWDaadhNV_mE-1737300295-1.2.1.1-sPb9d9yoZ8vi_rhYzc03IZyIvd.BxewoQx_qHVXz0pTjFpWyfg.ArzmlsI9H3Dy9qOen8iTcxhLhpQfyxEWe2QHxLy5ZxsohmljbZWDlDAPSDbFL3zPnNap0tehtSrm9V7TFr1JL.ROXkekmnHqhMu0kSYUc.bjbO7idmB4gqnUClNEavMeGuDRTaZh7IuXPjQvtzkobNUWa1ZBcKztJTFI59dwuYqdq5qMfyZ4H0XZDQNS4x6SljZRYdc2gRxXZa1keSflyY8aD_aJ0FOFi.mjQp.pAwYd9bW9xV4IQrGMoTF.bDDFVcI8I_Dt5J8Y3v2to_aga7CdDyeCtZMQR9A", "_gat_UA-58591210-1": "1", "__gads": "ID=ee8b011769620250:T=1737300300:RT=1737300300:S=ALNI_Mawmuupr1k3KRysQgNc0SsU7Y2s3g", "__gpi": "UID=00000ff24b9cc12b:T=1737300300:RT=1737300300:S=ALNI_Mbz0deueC3bcJ6wEFIaR-EP0W7TUA", "__eoi": "ID=d40d07aa6a4ff530:T=1737300300:RT=1737300300:S=AA-Afjba1iqXa-VysfdnHae3t_qT", "_dc_gtm_UA-58591210-1": "1", "sid": "SILArJY42j0XSsKAdMv4PQTCkxb0iNOJ805gofpYi8hfz6DLp6X2OKKPy7XEWDALHf7l5OKzuzLkJNPsUGowoEK5ywuLhmeQNv14zANVGca50vRKGARZYxIipJK9kgtw", "isInstIp": "false", "hasPdpNext": "false", "_ga_4P31SJ70EJ": "GS1.1.1737299531.17.1.1737300302.0.0.0", "_ga": "GA1.2.680663890.1737300291", "_pbjs_userid_consent_data": "3524755945110770", "_lr_retry_request": "true", "_lr_env_src_ats": "false", "pbjs-unifiedid": "%7B%22TDID%22%3A%2241fd784c-0db2-44f4-8401-9b6512f837da%22%2C%22TDID_LOOKUP%22%3A%22TRUE%22%2C%22TDID_CREATED_AT%22%3A%222024-12-19T15%3A25%3A15%22%7D", "pbjs-unifiedid_last": "Sun%2C%2019%20Jan%202025%2015%3A25%3A11%20GMT", "panoramaId_expiry": "1737905116547", "_cc_id": "5653871c5b5a5512ff8d8bb16cd50f89", "panoramaId": "eb07f370cce381acfe7d45607de1185ca02ceef33b264cf566eb21c5ca636125", "ph_phc_ma1XTQyee96N1GML6qUTgLQRiDifnRcE9STiHTZ0CfZ_posthog": "%7B%22distinct_id%22%3A%2201947f2a-c660-7caf-b826-1c4dd56ae2f8%22%2C%22%24sesid%22%3A%5B1737300327203%2C%2201947f2a-c663-791d-b1f1-f241a61d1a15%22%2C1737300297315%5D%2C%22%24initial_person_info%22%3A%7B%22r%22%3A%22https%3A%2F%2Fwww.researchgate.net%2Fpublication%2F367263856_Solder_Joint_Reliability_Assessment_on_FO-CSP_for_Next_Generation_DDR6%3F__cf_chl_tk%3DD5SncsSqlDhqeBpg3LCatOFUvug3Ea.6XrcxG4IqHCQ-1737300273-1.0.1.1-Pzvfr2mBtGdeAR8Tsw_o8WkU9U._WX69PHQGOn9jdsg%22%2C%22u%22%3A%22https%3A%2F%2Fwww.researchgate.net%2Fpublication%2F367263856_Solder_Joint_Reliability_Assessment_on_FO-CSP_for_Next_Generation_DDR6%22%7D%7D"}
burp0_headers = {"Cache-Control": "max-age=0", "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.6778.140 Safari/537.36", "Accept-Language": "en-US,en;q=0.9", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7", "Upgrade-Insecure-Requests": "1", "X-Entry-Page": "", "X-Rg-Referrer": "", "Sec-Fetch-Site": "same-origin", "Sec-Fetch-Mode": "same-origin", "Sec-Fetch-Dest": "empty", "Referer": "https://www.researchgate.net/publication/lite.worker.js", "Accept-Encoding": "gzip, deflate, br", "Priority": "u=0, i"}
response = session.get(burp0_url, headers=burp0_headers, cookies=burp0_cookies, timeout=10)
        