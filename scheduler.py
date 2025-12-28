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
    logger.info("开始定时同步数据...")
    try:
        # 同步指数数据
        data_collector.sync_index_data()
        
        # 同步个股列表（每天只同步一次）
        # data_collector.sync_stock_list()
        
        logger.info("数据同步完成")
    except Exception as e:
        logger.error(f"数据同步失败: {e}")


def sync_stock_list_daily():
    """每天同步一次个股列表"""
    logger.info("开始同步个股列表...")
    try:
        data_collector.sync_stock_list()
        logger.info("个股列表同步完成")
    except Exception as e:
        logger.error(f"个股列表同步失败: {e}")


def calculate_recommendations_daily():
    """每天计算推荐股票（收盘后执行）"""
    logger.info("开始计算推荐股票...")
    try:
        recommendation_calculator.save_recommendations()
        logger.info("推荐股票计算完成")
    except Exception as e:
        logger.error(f"推荐股票计算失败: {e}")


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
    
    logger.info("定时任务调度器启动")
    logger.info(f"指数数据同步间隔: {SYNC_INTERVAL_MINUTES}分钟")
    logger.info("个股列表同步时间: 每天02:00")
    logger.info("推荐股票计算时间: 每天16:00（收盘后）")
    
    # 立即执行一次
    sync_all_data()
    
    # 运行调度器
    while True:
        schedule.run_pending()
        time.sleep(60)  # 每分钟检查一次

