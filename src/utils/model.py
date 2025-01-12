
import urllib.parse

import scrapy
from sqlalchemy import (NVARCHAR, Boolean, Column, Date, DateTime, Integer,
                        Table, Text, create_engine, func)
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

def defi_research_gate_publication_talbe():
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

def defi_research_gate_questions_talbe():
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
    
class ResearchGateQuestionItem(scrapy.Item):
    title = scrapy.Field()
    link = scrapy.Field()
    question_date = scrapy.Field()
    question_abstract = scrapy.Field()
    answer_content = scrapy.Field()
    has_more_answers = scrapy.Field()
