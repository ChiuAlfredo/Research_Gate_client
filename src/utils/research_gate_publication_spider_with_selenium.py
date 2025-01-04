import csv
import datetime
import ssl
import urllib.parse
from concurrent.futures import ThreadPoolExecutor

import requests
import scrapy
from bs4 import BeautifulSoup
from dateutil import parser
from requests.adapters import HTTPAdapter
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
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
    research_gate_publication = Table(
        'research_gate_publication', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('title', NVARCHAR(255), nullable=False),
        Column('link', Text, nullable=True),
        Column('year', Integer, nullable=True),
        Column('publication_type', NVARCHAR(255), nullable=True),
        Column('publication_date', Date, nullable=True),
        Column('doi', NVARCHAR(255), nullable=True),
        Column('abstract', Text, nullable=True),
        Column('created_at', DateTime, default=func.now(), nullable=False),  
        Column('updated_at', DateTime, default=func.now(), onupdate=func.now(), nullable=False),  
        Column('deleted_at', DateTime, nullable=True),  
        Column('is_deleted', Boolean, default=False, nullable=False),
        Column('authors', NVARCHAR(255), nullable=True),
        Column('patent', NVARCHAR(255), nullable=True),
        Column('trackid', NVARCHAR(255), nullable=True),
    )
    return research_gate_publication

class ResearchGatePublicationItem(scrapy.Item):
    title = scrapy.Field()
    link = scrapy.Field()
    year = scrapy.Field()
    publication_type = scrapy.Field()
    publication_date = scrapy.Field()
    doi = scrapy.Field()
    abstract = scrapy.Field()
    authors = scrapy.Field()
    patent = scrapy.Field()

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
    adapter = TLSAdapter(tls_version=ssl.TLSVersion.TLSv1_3)
    session = requests.Session()
    session.mount("https://", adapter)
    url = f"https://www.researchgate.net:443/search/publication?q={keyword}&page={page}"
    response = session.get(url, headers=headers, cookies=cookies, timeout=10)
    if response.status_code != 200:
        print(f'驗證錯誤response.status_code:{response.status_code}')
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
        doi = detail_soup[1].text if len(detail_soup) > 2 else ''
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

def get_headers_cookies():
    # 建立 ChromeDriver 的服務
    service = Service()

    # 設定 Chrome 的選項
    chrome_options = Options()
    chrome_options.add_argument("--start-maximized")  # 瀏覽器啟動時最大化
    chrome_options.add_argument("--disable-infobars")  # 禁用 "Chrome 正在受自動測試軟件控制" 的提示
    chrome_options.add_argument("--disable-extensions")  

    # 啟動 WebDriver
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.get(url = f"https://www.researchgate.net:443/search/publication?q={keyword}&page=1")
    # 獲取 User-Agent
    user_agent = driver.execute_script("return navigator.userAgent;")

    # 獲取所有的 cookies
    cookies = driver.get_cookies()
    cf_clearance = next((cookie['value'] for cookie in cookies if cookie['name'] == 'cf_clearance'), None)
    driver.close()
    return user_agent, cf_clearance
    
def main(): 
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = executor.map(parse_detail, range(1, 21))
    
    fieldnames = [
        'title', 'link', 'year', 'publication_type', 'publication_date',
        'doi', 'abstract', 'authors', 'patent', 'created_at', 'updated_at'
    ]
    research_gate_publication = defi_talbe()
    session = create_session()
    with open('research_gate_publication_spider_output.csv', mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()
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
                writer.writerow(publication_data)
                # 將數據插入資料庫
                session.execute(insert(research_gate_publication).values(publication_data))
                session.commit()
        session.close()



if __name__ == '__main__':
    keyword = 'antenna'
    user_agent, cf_clearance = get_headers_cookies()
    cookies = {"cf_clearance":cf_clearance}
    headers = {"User-Agent":user_agent}
    
    main()