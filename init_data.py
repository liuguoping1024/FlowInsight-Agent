"""
初始化数据脚本
同步所有A股股票列表到数据库
"""
import logging
import sys
import io
import time
from services.data_collector import DataCollector
from database.db_connection import db

# 设置标准输出编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sync_all_stocks():
    """同步所有A股股票列表到数据库"""
    print("=" * 60)
    print("FlowInsight-Agent 股票列表同步")
    print("=" * 60)
    print("\n开始同步所有A股股票列表...")
    print("注意：每次网络请求后会等待1秒，避免被限流")
    print("预计需要几分钟时间，请耐心等待...\n")
    
    collector = DataCollector()
    
    # 同步所有股票列表，每次请求后等待1秒
    start_time = time.time()
    collector.sync_stock_list(delay=1.0)
    elapsed_time = time.time() - start_time
    
    # 统计数据库中的股票数量
    try:
        sql = "SELECT COUNT(*) as count FROM stock_list WHERE is_active = 1"
        result = db.execute_query(sql)
        total_count = result[0]['count'] if result else 0
        
        print("\n" + "=" * 60)
        print(f"[成功] 股票列表同步完成！")
        print("=" * 60)
        print(f"数据库中共有股票: {total_count} 只")
        print(f"耗时: {elapsed_time:.2f} 秒")
        print("=" * 60)
        
    except Exception as e:
        logger.error(f"统计股票数量失败: {e}")
        print(f"\n[警告] 同步完成，但统计数量时出错: {e}")


if __name__ == '__main__':
    try:
        sync_all_stocks()
    except KeyboardInterrupt:
        print("\n\n[警告] 用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"数据同步失败: {e}")
        print(f"\n[错误] 数据同步失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

