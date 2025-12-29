"""
股票健康度计算服务
"""
import logging
from datetime import date
from typing import Dict, Optional
from database.db_connection import db

logger = logging.getLogger(__name__)


class HealthCalculator:
    """股票健康度计算器"""
    
    def calculate_health_score(self, secid: str, score_date: Optional[date] = None) -> Dict:
        """
        计算股票健康度评分
        
        评分规则：
        1. 主力资金流入情况（40分）
        2. 资金流入趋势（30分）
        3. 价格表现（20分）
        4. 成交量活跃度（10分）
        """
        if score_date is None:
            score_date = date.today()
        
        # 获取最近30天的数据
        sql = """
        SELECT trade_date, main_net_inflow, super_large_net_inflow,
               close_price, change_percent, turnover_rate, turnover_amount
        FROM stock_capital_flow_history
        WHERE secid = %s AND trade_date <= %s
        ORDER BY trade_date DESC
        LIMIT 30
        """
        
        try:
            history_data = db.execute_query(sql, (secid, score_date))
            if not history_data:
                return {
                    'health_score': 0,
                    'trend_direction': 'unknown',
                    'risk_level': 'high',
                    'message': '暂无历史数据'
                }
            
            # 计算各项指标
            recent_7d = history_data[:7] if len(history_data) >= 7 else history_data
            recent_30d = history_data
            
            # 1. 主力资金流入情况（40分）
            main_net_inflow_7d = sum(float(d['main_net_inflow'] or 0) for d in recent_7d)
            main_net_inflow_30d = sum(float(d['main_net_inflow'] or 0) for d in recent_30d)
            
            # 评分：7日累计流入 > 1亿：满分，> 5000万：30分，> 0：20分，否则0分
            if main_net_inflow_7d > 100000000:
                inflow_score = 40
            elif main_net_inflow_7d > 50000000:
                inflow_score = 30
            elif main_net_inflow_7d > 0:
                inflow_score = 20
            else:
                inflow_score = 0
            
            # 2. 资金流入趋势（30分）
            if len(recent_7d) >= 3:
                # 检查是否连续流入
                consecutive_inflow_days = 0
                for d in recent_7d[:3]:
                    if float(d['main_net_inflow'] or 0) > 0:
                        consecutive_inflow_days += 1
                
                # 检查是否加速流入
                if len(recent_7d) >= 3:
                    inflows = [float(d['main_net_inflow'] or 0) for d in recent_7d[:3]]
                    is_accelerating = inflows[0] > inflows[1] > inflows[2] and all(i > 0 for i in inflows)
                else:
                    is_accelerating = False
                
                if is_accelerating:
                    trend_score = 30
                elif consecutive_inflow_days >= 3:
                    trend_score = 25
                elif consecutive_inflow_days >= 2:
                    trend_score = 15
                else:
                    trend_score = 5
            else:
                trend_score = 10
            
            # 3. 价格表现（20分）
            if recent_7d:
                avg_change = sum(float(d['change_percent'] or 0) for d in recent_7d) / len(recent_7d)
                if avg_change > 3:
                    price_score = 20
                elif avg_change > 1:
                    price_score = 15
                elif avg_change > 0:
                    price_score = 10
                else:
                    price_score = 5
            else:
                price_score = 10
            
            # 4. 成交量活跃度（10分）
            if recent_7d:
                avg_turnover_rate = sum(float(d['turnover_rate'] or 0) for d in recent_7d) / len(recent_7d)
                if avg_turnover_rate > 5:
                    turnover_score = 10
                elif avg_turnover_rate > 3:
                    turnover_score = 7
                elif avg_turnover_rate > 1:
                    turnover_score = 5
                else:
                    turnover_score = 2
            else:
                turnover_score = 5
            
            # 计算总分
            total_score = inflow_score + trend_score + price_score + turnover_score
            
            # 判断趋势方向
            if main_net_inflow_7d > 50000000:
                trend_direction = 'inflow'
            elif main_net_inflow_7d < -50000000:
                trend_direction = 'outflow'
            else:
                trend_direction = 'stable'
            
            # 判断风险等级
            if total_score >= 80:
                risk_level = 'low'
            elif total_score >= 60:
                risk_level = 'medium'
            else:
                risk_level = 'high'
            
            score_details = {
                'inflow_score': inflow_score,
                'trend_score': trend_score,
                'price_score': price_score,
                'turnover_score': turnover_score,
                'main_net_inflow_7d': main_net_inflow_7d,
                'main_net_inflow_30d': main_net_inflow_30d,
            }
            
            return {
                'health_score': round(total_score, 2),
                'trend_direction': trend_direction,
                'risk_level': risk_level,
                'main_net_inflow_7d': main_net_inflow_7d,
                'main_net_inflow_30d': main_net_inflow_30d,
                'score_details': score_details
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate health score: {e}, secid: {secid}")
            return {
                'health_score': 0,
                'trend_direction': 'unknown',
                'risk_level': 'high',
                'message': f'计算失败: {str(e)}'
            }
    
    def update_health_score(self, secid: str, score_date: Optional[date] = None):
        """更新股票健康度评分到数据库"""
        if score_date is None:
            score_date = date.today()
        
        health_data = self.calculate_health_score(secid, score_date)
        
        # 解析secid获取stock_code和market_code
        try:
            market_code, stock_code = secid.split('.')
        except ValueError:
            logger.error(f"Invalid secid format: {secid}")
            return
        
        sql = """
        INSERT INTO stock_health_scores (
            stock_code, market_code, secid, score_date,
            health_score, score_details, main_net_inflow_7d,
            main_net_inflow_30d, trend_direction, risk_level
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            health_score = VALUES(health_score),
            score_details = VALUES(score_details),
            main_net_inflow_7d = VALUES(main_net_inflow_7d),
            main_net_inflow_30d = VALUES(main_net_inflow_30d),
            trend_direction = VALUES(trend_direction),
            risk_level = VALUES(risk_level),
            updated_at = NOW()
        """
        
        import json
        score_details_json = json.dumps(health_data.get('score_details', {}), ensure_ascii=False)
        
        params = (
            stock_code, int(market_code), secid, score_date,
            health_data['health_score'], score_details_json,
            health_data.get('main_net_inflow_7d', 0),
            health_data.get('main_net_inflow_30d', 0),
            health_data.get('trend_direction', 'unknown'),
            health_data.get('risk_level', 'high')
        )
        
        try:
            db.execute_update(sql, params)
            logger.info(f"Health score updated successfully: {secid}, score: {health_data['health_score']}")
        except Exception as e:
            logger.error(f"Failed to update health score to database: {e}, secid: {secid}")

