
import urllib.parse

import scrapy
from sqlalchemy import (NVARCHAR, Boolean, Column, Date, DateTime, Integer,
                        Table, Text, create_engine, func, String, Enum)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from utils.config import get_config

# 獲取配置
config = get_config()


def create_session():

    sqlalchemy_connection_string = config.SQLALCHEMY_DATABASE_URL
    engine = create_engine(sqlalchemy_connection_string)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    return session

def defi_research_gate_publication_table():
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

def defi_research_gate_questions_table():
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

def defi_search_history_table():
    Base = declarative_base()
    metadata = Base.metadata
    search_history = Table(
        'search_history', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('user_id', String(255)),
        Column('username', String(255)),
        Column('trackid', String(255)),
        Column('function_name', NVARCHAR(255), nullable=False),
        Column('keyword', NVARCHAR(None)),
        Column('keyword_type', NVARCHAR(255)),
        Column('status', Enum('In Progress', 'Success', 'Failure', name='status_enum'), nullable=False),
        Column('start_date', DateTime),
        Column('end_date', DateTime),
        Column('other', NVARCHAR(255)),
        Column('created_at', DateTime, default=func.now(), nullable=False),
        Column('updated_at', DateTime, default=func.now(), onupdate=func.now(), nullable=False),
        Column('is_deleted', Boolean, default=False, nullable=False)
        )
    return search_history

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
