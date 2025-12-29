"""
推荐股票计算服务
用于计算每日推荐的股票（大资金建仓、震荡、散户退出）
"""
import logging
from datetime import date
from typing import List, Dict
from database.db_connection import db

logger = logging.getLogger(__name__)


class RecommendationCalculator:
    """推荐股票计算器"""
    
    def calculate_recommendations(self, recommend_date: date = None, days: int = 10, limit: int = 10) -> List[Dict]:
        """
        计算推荐股票
        
        Args:
            recommend_date: 推荐日期，默认为今天
            days: 分析的天数，默认10天
            limit: 最多推荐数量，默认10个
            
        Returns:
            推荐股票列表
        """
        if recommend_date is None:
            recommend_date = date.today()
        
        logger.info(f"Starting to calculate recommended stocks for {recommend_date}...")
        
        # 获取所有有历史数据的股票（至少要有最近N天的数据，但考虑到周末和节假日，实际交易日可能少于N天）
        # 使用最近N个交易日，而不是最近N个自然日
        sql_stocks = """
        SELECT DISTINCT sl.secid, sl.stock_code, sl.stock_name, sl.market_code
        FROM stock_list sl
        INNER JOIN stock_capital_flow_history h ON sl.secid = h.secid
        WHERE sl.is_active = 1
        AND h.trade_date >= DATE_SUB(%s, INTERVAL %s DAY)
        AND h.trade_date <= %s
        GROUP BY sl.secid, sl.stock_code, sl.stock_name, sl.market_code
        HAVING COUNT(DISTINCT h.trade_date) >= %s
        """
        
        # 考虑到周末和节假日，实际交易日可能少于自然日，所以降低要求
        # 如果要求10天，实际交易日可能是7-8天，所以至少要求6个交易日
        min_trade_days = max(6, int(days * 0.6))  # 至少60%的交易日
        
        stocks = db.execute_query(sql_stocks, (recommend_date, days, recommend_date, min_trade_days))
        logger.info(f"Found {len(stocks)} stocks with historical data (at least {min_trade_days} trading days)")
        
        result = []
        for stock in stocks:
            secid = stock['secid']
            
            # 获取最近N天的历史数据
            sql_history = """
            SELECT trade_date, main_net_inflow, small_net_inflow, 
                   close_price, change_percent, turnover_rate
            FROM stock_capital_flow_history
            WHERE secid = %s
            AND trade_date >= DATE_SUB(%s, INTERVAL %s DAY)
            AND trade_date <= %s
            ORDER BY trade_date DESC
            """
            history = db.execute_query(sql_history, (secid, recommend_date, days, recommend_date))
            
            # 至少要有6个交易日的数据
            if len(history) < min_trade_days:
                continue
            
            # 计算指标（处理 Decimal 类型）
            from decimal import Decimal
            
            def to_float(value):
                if value is None:
                    return 0.0
                if isinstance(value, Decimal):
                    return float(value)
                return float(value)
            
            total_main_inflow = sum(to_float(d.get('main_net_inflow', 0)) for d in history)
            total_small_inflow = sum(to_float(d.get('small_net_inflow', 0)) for d in history)
            changes = [to_float(d.get('change_percent', 0)) for d in history]
            max_change = max(changes) if changes else 0
            min_change = min(changes) if changes else 0
            avg_change = sum(changes) / len(changes) if changes else 0
            
            # 计算波动率（标准差）
            if len(changes) > 1:
                variance = sum((x - avg_change) ** 2 for x in changes) / len(changes)
                volatility = variance ** 0.5
            else:
                volatility = 0
            
            # 获取最新数据
            latest = history[0] if history else {}
            current_price = to_float(latest.get('close_price', 0))
            
            # 筛选条件：
            # 1. 主力净流入累计 > 5000万（大资金建仓，但不要太明显，< 5亿）
            # 2. 涨跌幅在-8%到8%之间（震荡）
            # 3. 小单净流入累计 < 0（散户退出）
            # 4. 波动率 > 1%（有一定震荡）
            # 5. 当前价格 < 100元（价格适中，普通投资者可承受）
            if (50000000 <= total_main_inflow < 500000000 and  # 主力建仓，但不太明显
                -8 <= max_change <= 8 and -8 <= min_change <= 8 and  # 震荡区间
                total_small_inflow < 0 and  # 散户退出
                volatility > 1.0 and  # 有一定波动
                current_price > 0 and current_price < 100):  # 价格在100元以下
                
                # 计算推荐理由
                reasons = []
                if total_main_inflow > 100000000:
                    reasons.append('大资金持续建仓')
                if volatility > 2.0:
                    reasons.append('震荡洗盘')
                if total_small_inflow < -10000000:
                    reasons.append('散户逐步退出')
                if total_main_inflow > 200000000:
                    reasons.append('主力资金明显流入')
                
                result.append({
                    'stock_code': stock['stock_code'],
                    'stock_name': stock['stock_name'],
                    'secid': secid,
                    'market_code': stock['market_code'],
                    'current_price': current_price,
                    'change_percent': to_float(latest.get('change_percent', 0)),
                    'total_main_inflow_10d': total_main_inflow,
                    'total_small_inflow_10d': total_small_inflow,
                    'volatility': volatility,
                    'max_change': max_change,
                    'min_change': min_change,
                    'recommend_reasons': reasons
                })
        
        # 按主力净流入排序
        result.sort(key=lambda x: x['total_main_inflow_10d'], reverse=True)
        
        logger.info(f"Calculated {len(result)} qualified recommended stocks")
        return result[:limit]
    
    def save_recommendations(self, recommend_date: date = None, days: int = 10, limit: int = 10):
        """
        计算并保存推荐股票到数据库
        
        Args:
            recommend_date: 推荐日期，默认为今天
            days: 分析的天数，默认10天
            limit: 最多推荐数量，默认10个
        """
        if recommend_date is None:
            recommend_date = date.today()
        
        # 先删除当天的旧推荐
        sql_delete = "DELETE FROM recommended_stocks WHERE recommend_date = %s"
        db.execute_update(sql_delete, (recommend_date,))
        logger.info(f"Deleted old recommendations for {recommend_date}")
        
        # 计算推荐股票
        recommendations = self.calculate_recommendations(recommend_date, days, limit)
        
        if not recommendations:
            logger.warning(f"No qualified recommended stocks found for {recommend_date}")
            return
        
        # 保存到数据库
        import json
        sql_insert = """
        INSERT INTO recommended_stocks (
            recommend_date, stock_code, market_code, stock_name, secid,
            current_price, change_percent, total_main_inflow_10d, total_small_inflow_10d,
            volatility, max_change, min_change, recommend_reasons, sort_order
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        for idx, rec in enumerate(recommendations):
            db.execute_update(sql_insert, (
                recommend_date,
                rec['stock_code'],
                rec['market_code'],
                rec['stock_name'],
                rec['secid'],
                rec['current_price'],
                rec['change_percent'],
                rec['total_main_inflow_10d'],
                rec['total_small_inflow_10d'],
                rec['volatility'],
                rec['max_change'],
                rec['min_change'],
                json.dumps(rec['recommend_reasons'], ensure_ascii=False),
                idx + 1  # 排序顺序
            ))
        
        logger.info(f"Successfully saved {len(recommendations)} recommended stocks to database")

