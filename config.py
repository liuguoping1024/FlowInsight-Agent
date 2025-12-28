"""
配置文件
"""
import os
from dotenv import load_dotenv

load_dotenv()

# 数据库配置
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'port': int(os.getenv('DB_PORT', 3306)),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', 'Shushi6688'),
    'database': os.getenv('DB_NAME', 'flowinsight'),
    'charset': 'utf8mb4'
}

# API配置
API_PORT = int(os.getenv('API_PORT', 8887))
WEB_PORT = int(os.getenv('WEB_PORT', 8888))

# 东方财富API配置
EASTMONEY_API_BASE = 'https://push2.eastmoney.com/api'
EASTMONEY_HISTORY_API_BASE = 'https://push2his.eastmoney.com/api'

# 指数代码映射
INDICES_MAP = {
    '1.000001': '上证指数',
    '0.399001': '深证成指',
    '0.399006': '创业板指',
    '1.000688': '科创50',
    '1.000016': '上证50',
    '1.000300': '沪深300',
    '1.000905': '中证500',
    '1.000852': '中证1000',
    '0.399005': '中小板指',
    '0.399102': '创业板综',
}

# 数据同步配置
SYNC_INTERVAL_MINUTES = 30  # 数据同步间隔（分钟）
MAX_RETRY_TIMES = 3  # 最大重试次数

