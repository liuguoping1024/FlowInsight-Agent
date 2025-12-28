"""
数据库连接管理
"""
import pymysql
from pymysql.cursors import DictCursor
from config import DB_CONFIG
import logging

logger = logging.getLogger(__name__)


class Database:
    """数据库连接类"""
    
    def __init__(self):
        self.config = DB_CONFIG
    
    def get_connection(self):
        """获取数据库连接"""
        try:
            connection = pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset=self.config['charset'],
                cursorclass=DictCursor,
                autocommit=False
            )
            return connection
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            raise
    
    def execute_query(self, sql, params=None):
        """执行查询"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(sql, params)
                result = cursor.fetchall()
                conn.commit()
                return result
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"查询执行失败: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_update(self, sql, params=None):
        """执行更新/插入/删除"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                affected_rows = cursor.execute(sql, params)
                conn.commit()
                return affected_rows
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"更新执行失败: {e}")
            raise
        finally:
            if conn:
                conn.close()
    
    def execute_many(self, sql, params_list):
        """批量执行"""
        conn = None
        try:
            conn = self.get_connection()
            with conn.cursor() as cursor:
                affected_rows = cursor.executemany(sql, params_list)
                conn.commit()
                return affected_rows
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"批量执行失败: {e}")
            raise
        finally:
            if conn:
                conn.close()


# 全局数据库实例
db = Database()

