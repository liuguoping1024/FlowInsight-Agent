"""
手动计算推荐股票脚本
可以单独运行此脚本来计算推荐股票
"""
import logging
from datetime import date
from services.recommendation_calculator import RecommendationCalculator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

if __name__ == '__main__':
    calculator = RecommendationCalculator()
    
    # 计算今天的推荐股票
    recommend_date = date.today()
    logger.info(f"Starting to calculate recommended stocks for {recommend_date}...")
    
    try:
        calculator.save_recommendations(recommend_date=recommend_date, days=10, limit=10)
        logger.info("Recommended stocks calculation completed!")
    except Exception as e:
        logger.error(f"Calculation failed: {e}", exc_info=True)

