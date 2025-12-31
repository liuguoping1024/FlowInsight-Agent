"""
技术指标计算示例脚本
演示如何使用TechnicalIndicators模块计算MACD、KDJ和RSI指标

【中国市场（A股）常用参数设置】

MACD指标：
- 常用参数1: (10, 20, 7)
  - 快速EMA周期: 10天（约2周交易日）
  - 慢速EMA周期: 20天（约1个月交易日）
  - 信号线周期: 7天（约1.5周交易日）
  - 适合中国A股市场，每周5个交易日的节奏

- 常用参数2: (10, 22, 9)
  - 快速EMA周期: 10天（约2周交易日）
  - 慢速EMA周期: 22天（约1个月交易日）
  - 信号线周期: 9天（约2周交易日）
  - 另一种常见的A股市场参数设置

- 超短线参数: (6, 13, 5)
  - 快速EMA周期: 6天
  - 慢速EMA周期: 13天
  - 信号线周期: 5天
  - 适合超短线交易，信号更敏感

KDJ指标：
- 标准参数: (9, 3, 3)
  - RSV计算周期: 9天
  - K值平滑周期: 3天
  - D值平滑周期: 3天
  - 通用标准设置，适用于大多数市场

RSI指标：
- 标准参数: 14
  - 14天周期（最常用）
  - 适用于大多数市场环境
- 短线参数: 6
  - 6天周期（更敏感）
  - 适合短线交易
- 中线参数: 21
  - 21天周期（更平滑）
  - 适合中长期趋势分析

【美国市场常用参数设置】

MACD指标：
- 传统标准参数: (12, 26, 9)
  - 快速EMA周期: 12天
  - 慢速EMA周期: 26天
  - 信号线周期: 9天
  - 1970年代美国市场最常用的设置

- 优化参数（2025年最新）: (8, 17, 5)
  - 快速EMA周期: 8天
  - 慢速EMA周期: 17天
  - 信号线周期: 5天
  - 趋势信号提前约1.5个交易日

KDJ指标：
- 传统标准参数: (9, 3, 3)
- 高波动市场优化: (13, 5, 5) - 适合纳斯达克等高波动市场

RSI指标：
- 标准参数: 14（通用标准）
"""
import logging
from services.technical_indicators import TechnicalIndicators
from database.db_connection import db

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def calculate_indicators_for_stock(
    secid: str,
    macd_params: tuple = (10, 20, 7),
    kdj_params: tuple = (9, 3, 3),
    rsi_period: int = 14,
    days: int = 60
):
    """
    为指定股票计算技术指标
    
    Args:
        secid: 股票代码（如 "1.000001"）
        macd_params: MACD参数 (fast_period, slow_period, signal_period)，默认(10, 20, 7)
        kdj_params: KDJ参数 (rsv_period, k_smooth, d_smooth)，默认(9, 3, 3)
        rsi_period: RSI周期，默认14
        days: 获取最近多少天的数据，默认60天
    """
    logger.info(f"开始为股票 {secid} 计算技术指标...")
    logger.info(f"MACD参数: {macd_params}")
    logger.info(f"KDJ参数: {kdj_params}")
    logger.info(f"RSI周期: {rsi_period}")
    
    # 获取历史数据
    sql = """
    SELECT trade_date, close_price, high_price, low_price, volume
    FROM stock_capital_flow_history
    WHERE secid = %s
    AND trade_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
    ORDER BY trade_date ASC
    """
    
    history_data = db.execute_query(sql, (secid, days))
    
    if not history_data:
        logger.warning(f"未找到股票 {secid} 的历史数据")
        return None
    
    logger.info(f"获取到 {len(history_data)} 条历史数据")
    
    # 检查是否有必要的数据字段
    sample = history_data[0]
    if 'close_price' not in sample or sample['close_price'] is None:
        logger.error("数据中缺少close_price字段")
        return None
    
    # 创建技术指标计算器
    calculator = TechnicalIndicators()
    
    # 计算所有指标
    result = calculator.calculate_all_indicators(
        history_data,
        macd_params=macd_params,
        kdj_params=kdj_params,
        rsi_period=rsi_period
    )
    
    # 显示最后几条结果
    logger.info("\n=== 计算结果（最后5条）===")
    for item in result[-5:]:
        logger.info(f"日期: {item['trade_date']}")
        logger.info(f"  收盘价: {item.get('close_price', 'N/A')}")
        if item.get('macd') is not None:
            logger.info(f"  MACD: {item['macd']:.4f}")
            logger.info(f"  Signal: {item.get('macd_signal', 'N/A'):.4f if item.get('macd_signal') else 'N/A'}")
            logger.info(f"  Histogram: {item.get('macd_histogram', 'N/A'):.4f if item.get('macd_histogram') else 'N/A'}")
        if item.get('kdj_k') is not None:
            logger.info(f"  KDJ-K: {item['kdj_k']:.2f}")
            logger.info(f"  KDJ-D: {item['kdj_d']:.2f}")
            logger.info(f"  KDJ-J: {item['kdj_j']:.2f}")
        if item.get('rsi') is not None:
            logger.info(f"  RSI: {item['rsi']:.2f}")
        logger.info("")
    
    return result


if __name__ == '__main__':
    # 示例：计算平安银行(000001)的技术指标
    
    secid = "1.000001"  # 平安银行
    
    # 示例1: 使用中国市场常用参数 (10, 20, 7)
    logger.info("=" * 60)
    logger.info("示例1: 使用中国市场常用参数 (10, 20, 7)")
    logger.info("MACD: (10, 20, 7) - A股市场常用设置（约2周/1个月/1.5周）")
    logger.info("KDJ: (9, 3, 3) - 标准设置")
    logger.info("RSI: 14 - 标准周期")
    logger.info("=" * 60)
    result1 = calculate_indicators_for_stock(
        secid=secid,
        macd_params=(10, 20, 7),  # 中国市场常用参数
        kdj_params=(9, 3, 3),
        rsi_period=14,
        days=60
    )
    
    # 示例2: 使用中国市场常用参数 (10, 22, 9)
    logger.info("\n" + "=" * 60)
    logger.info("示例2: 使用中国市场常用参数 (10, 22, 9)")
    logger.info("MACD: (10, 22, 9) - A股市场另一种常用设置")
    logger.info("KDJ: (9, 3, 3) - 标准设置")
    logger.info("RSI: 14 - 标准周期")
    logger.info("=" * 60)
    result2 = calculate_indicators_for_stock(
        secid=secid,
        macd_params=(10, 22, 9),  # 中国市场另一种常用参数
        kdj_params=(9, 3, 3),
        rsi_period=14,
        days=60
    )
    
    # 示例3: 使用美国市场传统标准参数
    logger.info("\n" + "=" * 60)
    logger.info("示例3: 使用美国市场传统标准参数")
    logger.info("MACD: (12, 26, 9) - 国际通用标准设置")
    logger.info("KDJ: (9, 3, 3) - 标准设置")
    logger.info("RSI: 14 - 标准周期")
    logger.info("=" * 60)
    result3 = calculate_indicators_for_stock(
        secid=secid,
        macd_params=(12, 26, 9),  # 美国市场传统标准
        kdj_params=(9, 3, 3),
        rsi_period=14,
        days=60
    )
    
    # 示例4: 使用短线参数（更敏感）
    logger.info("\n" + "=" * 60)
    logger.info("示例4: 使用短线参数（更敏感）")
    logger.info("MACD: (6, 13, 5) - 超短线参数")
    logger.info("KDJ: (9, 3, 3) - 标准设置")
    logger.info("RSI: 6 - 短线周期（更敏感）")
    logger.info("=" * 60)
    result4 = calculate_indicators_for_stock(
        secid=secid,
        macd_params=(6, 13, 5),  # 超短线参数
        kdj_params=(9, 3, 3),
        rsi_period=6,  # 短线RSI
        days=60
    )
    
    if result1:
        logger.info(f"\n使用参数(10, 20, 7, RSI=14)成功计算了 {len(result1)} 条数据的技术指标")
    if result2:
        logger.info(f"使用参数(10, 22, 9, RSI=14)成功计算了 {len(result2)} 条数据的技术指标")
    if result3:
        logger.info(f"使用参数(12, 26, 9, RSI=14)成功计算了 {len(result3)} 条数据的技术指标")
    if result4:
        logger.info(f"使用参数(6, 13, 5, RSI=6)成功计算了 {len(result4)} 条数据的技术指标")

