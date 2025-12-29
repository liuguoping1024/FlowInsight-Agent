"""
定时任务调度器
用于定时同步数据
"""
import schedule
import time
import logging
from services.data_collector import DataCollector
from services.recommendation_calculator import RecommendationCalculator
from config import SYNC_INTERVAL_MINUTES

logger = logging.getLogger(__name__)
data_collector = DataCollector()
recommendation_calculator = RecommendationCalculator()


def sync_all_data():
    """同步所有数据"""
    logger.info("Starting scheduled data sync...")
    try:
        # 同步指数数据
        data_collector.sync_index_data()
        
        # 同步个股列表（每天只同步一次）
        # data_collector.sync_stock_list()
        
        logger.info("Data sync completed")
    except Exception as e:
        logger.error(f"Data sync failed: {e}")


def sync_stock_list_daily():
    """每天同步一次个股列表"""
    logger.info("Starting stock list sync...")
    try:
        data_collector.sync_stock_list()
        logger.info("Stock list sync completed")
    except Exception as e:
        logger.error(f"Stock list sync failed: {e}")


def calculate_recommendations_daily():
    """每天计算推荐股票（收盘后执行）"""
    logger.info("Starting recommended stocks calculation...")
    try:
        recommendation_calculator.save_recommendations()
        logger.info("Recommended stocks calculation completed")
    except Exception as e:
        logger.error(f"Recommended stocks calculation failed: {e}")


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 每30分钟同步一次指数数据
    schedule.every(SYNC_INTERVAL_MINUTES).minutes.do(sync_all_data)
    
    # 每天凌晨2点同步个股列表
    schedule.every().day.at("02:00").do(sync_stock_list_daily)
    
    # 每天下午4点计算推荐股票（收盘后）
    schedule.every().day.at("16:00").do(calculate_recommendations_daily)
    
    logger.info("Scheduler started")
    logger.info(f"Index data sync interval: {SYNC_INTERVAL_MINUTES} minutes")
    logger.info("Stock list sync time: Daily at 02:00")
    logger.info("Recommended stocks calculation time: Daily at 16:00 (after market close)")
    
    # 立即执行一次
    sync_all_data()
    
    # 运行调度器
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

