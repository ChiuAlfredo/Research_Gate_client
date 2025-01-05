import csv
import datetime
import ssl
import urllib.parse
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import requests
import scrapy
from bs4 import BeautifulSoup
from dateutil import parser
from requests.adapters import HTTPAdapter
from sqlalchemy import (DECIMAL, NVARCHAR, Boolean, Column, Date, DateTime,
                        Float, Integer, MetaData, String, Table, Text,
                        create_engine, func, insert)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 設定資料庫連接資訊
username = "SA"
password = "@Bb11033003"  # 包含 @ 符號的密碼
server_address = "140.118.60.18"
database_name = "model"
driver = "ODBC Driver 17 for SQL Server"


cookies = {}
headers = {}


def create_session():
    username_encoded = urllib.parse.quote_plus(username)
    password_encoded = urllib.parse.quote_plus(password)
    driver_encoded = urllib.parse.quote_plus(driver)

    sqlalchemy_connection_string = (
        f"mssql+pyodbc://{username_encoded}:{password_encoded}@{server_address}/{database_name}"
        f"?driver={driver_encoded}&encoding=utf8"
    )
    engine = create_engine(sqlalchemy_connection_string)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    return session

def defi_talbe():
    Base = declarative_base()
    metadata = Base.metadata
    research_gate_questions = Table(
        'research_gate_questions', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('title', NVARCHAR(255), nullable=False),
        Column('link', Text, nullable=True),
        Column('question_date', Date, nullable=True),
        Column('question_abstract', Text, nullable=True),
        Column('answer_content', Text, nullable=True),
        Column('has_more_answers', Boolean, nullable=True),
        Column('created_at', DateTime, default=func.now(), nullable=False),  
        Column('updated_at', DateTime, default=func.now(), onupdate=func.now(), nullable=False),  
        Column('deleted_at', DateTime, nullable=True),  
        Column('is_deleted', Boolean, default=False, nullable=False),
        Column('trackid', NVARCHAR(255), nullable=False),
    )
    return research_gate_questions

class ResearchGateQuestionItem(scrapy.Item):
    title = scrapy.Field()
    link = scrapy.Field()
    question_date = scrapy.Field()
    question_abstract = scrapy.Field()
    answer_content = scrapy.Field()
    has_more_answers = scrapy.Field()

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

            
def parse_detail(page):
    url = f"https://www.researchgate.net:443/search/question?q={keyword.replace(' ','%20')}&page={page}"
    adapter = TLSAdapter(tls_version=ssl.TLSVersion.TLSv1_3)
    session = requests.Session()
    session.mount("https://", adapter)
    response = session.get(url=url, headers=headers, cookies=cookies)
    if response.status_code != 200:
        print('驗證錯誤')
    soup = BeautifulSoup(response.text, 'lxml')
    
    items = []
    for sing_question in soup.select('[class="nova-legacy-o-stack__item"]')[:-6]:
        item = ResearchGateQuestionItem()
        if len(sing_question.select('a')) == 0:
            break
        title = sing_question.select('a')[0].text
        link = "https://www.researchgate.net/" + sing_question.select('a')[0]['href']
        question_date = sing_question.select(
            '[class="nova-legacy-e-list__item nova-legacy-v-entity-item__meta-data-item"]')[0].text
        
        abstract = sing_question.select('[class="Linkify"] div')[0].text if sing_question.select('[class="Linkify"] div') else ''
        comments = get_comments(session, link)
        item['title'] = title
        item['link'] = link
        item['question_date'] = question_date
        item['question_abstract'] = abstract
        item['answer_content'] = comments[:10]
        item['has_more_answers'] = True if len(comments[10:])>0 else False
        items.append(item)
    return items
        
def get_comments(session, link):
    response = session.get(url=link, headers=headers, cookies=cookies)
    soup = BeautifulSoup(response.text, 'lxml')
    answer_num = soup.select('[class="nova-legacy-e-text nova-legacy-e-text--size-l nova-legacy-e-text--family-display nova-legacy-e-text--spacing-none nova-legacy-e-text--color-inherit"]')
    if len(answer_num) == 0:
        return []
    
    comments = [i.text for i in soup.select('[class="nova-legacy-o-stack__item"] [class="nova-legacy-v-activity-item"] [class="Linkify"]')[1:]]
    return comments

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
    
def research_question(keywords,cf_clearance, user_agent):   
    global cookies, headers
    
    cookies = {"cf_clearance":cf_clearance}
    headers = {"User-Agent":user_agent}
    
    with open('research_gate_questions_spider_output.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader() #
        for keyword in keywords:
            with ThreadPoolExecutor(max_workers=8) as executor:
                parse_detail_with_keyword = partial(parse_detail, keyword=keyword)
                results = executor.map(parse_detail_with_keyword, range(1, 21))
            fieldnames = [
                'title', 'link', 'question_date', 'question_abstract',
                'answer_content', 'has_more_answers', 'created_at', 'updated_at'
            ]
            research_gate_questions = defi_talbe()
            session = create_session()
            for items in results:
                for item in items:
                    ResearchGateQuestionPipelinetion_data = {
                        'title': item.get('title'),
                        'link': item.get('link'),
                        'question_date': parse_date(item.get('question_date')),
                        'question_abstract': item.get('question_abstract'),
                        'answer_content': ' | '.join(item.get('answer_content', [])),
                        'has_more_answers': item.get('has_more_answers', False),  # 預設 patent 為空字符串
                        'created_at': datetime.datetime.now(),
                        'updated_at': datetime.datetime.now(),
                    }
                    writer.writerow(ResearchGateQuestionPipelinetion_data)
                    # 將數據插入資料庫
                    session.execute(insert(research_gate_questions).values(ResearchGateQuestionPipelinetion_data))
                    session.commit()
            session.close()


# if __name__ == '__main__':
#     # cf_clearance 一定要是經過cloudflare驗證的，如果沒有辦法觸發cloudflare 那就先跑一次
#     keyword = 'antenna'
#     cf_clearance = '.ldO8y8NoIHlKvsXSoW3IJZ3G9SZVqqNJPtCANaQdpM-1735857070-1.2.1.1-gn2GXv4mfrF5HB0EYAwpkU4yUWphS2FZ73KjgyNtOHqdfN51XYq3swEEwW4aSh4L56QcSzYnNkxc3_KJEFvaZATvequscbtsIqJ4g82Wku.HwyNGyKC9v.5jUzX2VHBcg1tsbhHZCOCxDR5fvA3DnW.B2cRXtEgFYh3C5ClNCjy2DtgeC1GQh3uicdgNaCvTE63XW_zwkXgiv_IJmmMqj_ZQw5dTHG_rOxE123dNN0gHYCEJwou9Z9RgXW3lUI4NfbCnvKF9Ox7uRsJCZLhO3PS36niiBzQ2Lvx6s2AsN7FKmuvoM6cYp.VA9tE3nf4r2dXxglxKtNkrhGmXipkYD_Xm9vU5t35vmGPt5O9MmBpaIySPbOYI8nxRmgD4Wac_C9d2.DwXORLl8zMX9ECi_pCTliMqjbylx0L2rgLof16xkNvOUC8KRgOw.qDxn1l5'
#     user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
#     cookies = {"cf_clearance":cf_clearance}
#     headers = {"User-Agent":user_agent}
    
#     main()