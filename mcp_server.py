"""
MCP (Model Context Protocol) 服务器
提供AI模型访问股票数据的接口
"""
import json
import logging
from typing import Any, Dict
from datetime import datetime, date, timedelta
from services.data_collector import DataCollector
from services.health_calculator import HealthCalculator
from database.db_connection import db

logger = logging.getLogger(__name__)

data_collector = DataCollector()
health_calculator = HealthCalculator()


class MCPServer:
    """MCP服务器类"""
    
    def __init__(self):
        self.tools = {
            'get_stock_list': self._get_stock_list,
            'get_stock_health': self._get_stock_health,
            'get_stock_history': self._get_stock_history,
            'get_realtime_capital_flow': self._get_realtime_capital_flow,
            'get_index_data': self._get_index_data,
            'analyze_stock_trend': self._analyze_stock_trend,
            'compare_stocks': self._compare_stocks,
        }
    
    async def handle_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """处理MCP请求"""
        try:
            if method in self.tools:
                result = await self.tools[method](params)
                return {
                    'jsonrpc': '2.0',
                    'result': result,
                    'id': params.get('id')
                }
            else:
                return {
                    'jsonrpc': '2.0',
                    'error': {'code': -32601, 'message': f'Method not found: {method}'},
                    'id': params.get('id')
                }
        except Exception as e:
            logger.error(f"MCP请求处理失败: {e}")
            return {
                'jsonrpc': '2.0',
                'error': {'code': -32603, 'message': str(e)},
                'id': params.get('id')
            }
    
    async def _get_stock_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取股票列表"""
        keyword = params.get('keyword', '')
        limit = params.get('limit', 50)
        
        if keyword:
            sql = """
            SELECT stock_code, market_code, stock_name, secid
            FROM stock_list
            WHERE (stock_name LIKE %s OR stock_code LIKE %s) AND is_active = 1
            LIMIT %s
            """
            keyword_pattern = f'%{keyword}%'
            stocks = db.execute_query(sql, (keyword_pattern, keyword_pattern, limit))
        else:
            sql = """
            SELECT stock_code, market_code, stock_name, secid
            FROM stock_list
            WHERE is_active = 1
            LIMIT %s
            """
            stocks = db.execute_query(sql, (limit,))
        
        return {'stocks': stocks}
    
    async def _get_stock_health(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取股票健康度"""
        secid = params.get('secid')
        if not secid:
            raise ValueError('secid参数必填')
        
        score_date_str = params.get('date')
        score_date = datetime.strptime(score_date_str, '%Y-%m-%d').date() if score_date_str else None
        
        health_data = health_calculator.calculate_health_score(secid, score_date)
        return health_data
    
    async def _get_stock_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取股票历史数据"""
        secid = params.get('secid')
        if not secid:
            raise ValueError('secid参数必填')
        
        limit = params.get('limit', 30)
        days = params.get('days', None)
        
        if days:
            start_date = date.today() - timedelta(days=days)
            sql = """
            SELECT trade_date, main_net_inflow, close_price, change_percent,
                   turnover_rate, turnover_amount
            FROM stock_capital_flow_history
            WHERE secid = %s AND trade_date >= %s
            ORDER BY trade_date DESC
            """
            history = db.execute_query(sql, (secid, start_date))
        else:
            sql = """
            SELECT trade_date, main_net_inflow, close_price, change_percent,
                   turnover_rate, turnover_amount
            FROM stock_capital_flow_history
            WHERE secid = %s
            ORDER BY trade_date DESC
            LIMIT %s
            """
            history = db.execute_query(sql, (secid, limit))
        
        return {'history': history}
    
    async def _get_realtime_capital_flow(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取实时资金流向"""
        limit = params.get('limit', 20)
        flow_data = data_collector.get_realtime_capital_flow(limit)
        return {'data': flow_data}
    
    async def _get_index_data(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取指数数据"""
        index_data = data_collector.get_index_data()
        return {'data': index_data}
    
    async def _analyze_stock_trend(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """分析股票趋势"""
        secid = params.get('secid')
        if not secid:
            raise ValueError('secid参数必填')
        
        days = params.get('days', 30)
        start_date = date.today() - timedelta(days=days)
        
        # 获取历史数据
        sql = """
        SELECT trade_date, main_net_inflow, close_price, change_percent
        FROM stock_capital_flow_history
        WHERE secid = %s AND trade_date >= %s
        ORDER BY trade_date ASC
        """
        history = db.execute_query(sql, (secid, start_date))
        
        if not history:
            return {'message': '数据不足，无法分析'}
        
        # 分析趋势
        total_inflow = sum(float(d['main_net_inflow'] or 0) for d in history)
        avg_change = sum(float(d['change_percent'] or 0) for d in history) / len(history)
        
        # 计算最近7天和之前的数据对比
        recent_7d = history[-7:] if len(history) >= 7 else history
        previous_data = history[:-7] if len(history) >= 7 else []
        
        recent_inflow = sum(float(d['main_net_inflow'] or 0) for d in recent_7d)
        previous_inflow = sum(float(d['main_net_inflow'] or 0) for d in previous_data) if previous_data else 0
        
        # 判断趋势
        if recent_inflow > previous_inflow * 1.5:
            trend = '加速流入'
        elif recent_inflow > 0:
            trend = '持续流入'
        elif recent_inflow < previous_inflow * 0.5:
            trend = '加速流出'
        else:
            trend = '持续流出'
        
        return {
            'secid': secid,
            'period_days': days,
            'total_inflow': total_inflow,
            'recent_7d_inflow': recent_inflow,
            'avg_change_percent': round(avg_change, 2),
            'trend': trend,
            'data_points': len(history)
        }
    
    async def _compare_stocks(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """比较多只股票"""
        secids = params.get('secids', [])
        if not secids:
            raise ValueError('secids参数必填，应为数组')
        
        comparison = []
        for secid in secids:
            health_data = health_calculator.calculate_health_score(secid)
            
            # 获取股票名称
            sql = "SELECT stock_name FROM stock_list WHERE secid = %s LIMIT 1"
            stock_info = db.execute_query(sql, (secid,))
            stock_name = stock_info[0]['stock_name'] if stock_info else secid
            
            comparison.append({
                'secid': secid,
                'stock_name': stock_name,
                'health_score': health_data.get('health_score', 0),
                'trend_direction': health_data.get('trend_direction', 'unknown'),
                'risk_level': health_data.get('risk_level', 'high'),
                'main_net_inflow_7d': health_data.get('main_net_inflow_7d', 0)
            })
        
        # 按健康度排序
        comparison.sort(key=lambda x: x['health_score'], reverse=True)
        
        return {'comparison': comparison}


# MCP服务器实例
mcp_server = MCPServer()


async def handle_mcp_message(message: str) -> str:
    """处理MCP消息"""
    try:
        request = json.loads(message)
        method = request.get('method')
        params = request.get('params', {})
        
        response = await mcp_server.handle_request(method, params)
        return json.dumps(response, ensure_ascii=False)
    except json.JSONDecodeError:
        return json.dumps({
            'jsonrpc': '2.0',
            'error': {'code': -32700, 'message': 'Parse error'},
            'id': None
        })
    except Exception as e:
        logger.error(f"MCP消息处理失败: {e}")
        return json.dumps({
            'jsonrpc': '2.0',
            'error': {'code': -32603, 'message': str(e)},
            'id': None
        })


if __name__ == '__main__':
    # MCP服务器可以通过stdin/stdout或HTTP接口提供服务
    # 这里提供一个简单的HTTP接口示例
    from flask import Flask, request, jsonify
    from flask_cors import CORS
    
    app = Flask(__name__)
    CORS(app)
    
    @app.route('/mcp', methods=['POST'])
    async def mcp_endpoint():
        data = request.json
        response = await mcp_server.handle_request(data.get('method'), data)
        return jsonify(response)
    
    logger.info("启动MCP服务器")
    app.run(host='0.0.0.0', port=8889, debug=True)

