import os
import urllib.parse

class Config:
    """
    基本配置類
    """
    # 資料庫配置
    DB_USERNAME = os.getenv("DB_USERNAME", "SA")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "@Bb11033003")  # 包含 @ 符號的密碼
    DB_SERVER = os.getenv("DB_SERVER", "140.118.60.18")
    DB_NAME = os.getenv("DB_NAME", "model")
    DB_DRIVER = os.getenv("DB_DRIVER", "ODBC Driver 17 for SQL Server")

    # URL 編碼
    DB_USERNAME_ENCODED = urllib.parse.quote_plus(DB_USERNAME)
    DB_PASSWORD_ENCODED = urllib.parse.quote_plus(DB_PASSWORD)
    DB_DRIVER_ENCODED = urllib.parse.quote_plus(DB_DRIVER)

    # SQLAlchemy 連接字串
    SQLALCHEMY_DATABASE_URL = (
        f"mssql+pyodbc://{DB_USERNAME_ENCODED}:{DB_PASSWORD_ENCODED}@{DB_SERVER}/{DB_NAME}"
        f"?driver={DB_DRIVER_ENCODED}&encoding=utf8"
    )

# 根據需要擴展不同環境
class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

# 自動選擇配置
def get_config():
    env = os.getenv("ENV", "development").lower()
    if env == "production":
        return ProductionConfig()
    return DevelopmentConfig()
