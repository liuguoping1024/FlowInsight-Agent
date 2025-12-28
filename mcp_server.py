"""
MCP (Model Context Protocol) 服务器
提供AI模型访问股票数据的接口
"""
# 显式导入 cryptography 以确保 pymysql 可以正确使用它（必须在导入数据库模块之前）
try:
    import cryptography  # noqa: F401
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("cryptography 未安装，数据库连接可能失败")

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
            'get_stock_secid': self._get_stock_secid,  # 新增：便捷查询股票代码和交易所
            'get_stock_health': self._get_stock_health,
            'get_stock_history': self._get_stock_history,
            'get_realtime_capital_flow': self._get_realtime_capital_flow,
            'get_index_data': self._get_index_data,
            'analyze_stock_trend': self._analyze_stock_trend,
            'compare_stocks': self._compare_stocks,
            'sync_stock_list': self._sync_stock_list,
            'sync_stock_history': self._sync_stock_history,
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
        """
        获取股票列表
        注意：此方法仅从数据库查询，不会执行任何同步操作（sync_stock_list）
        如需同步股票列表，请使用 sync_stock_list 工具
        """
        keyword = params.get('keyword', '')
        limit = params.get('limit', 50)
        
        # 仅从数据库查询，不执行同步操作
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
    
    async def _get_stock_secid(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        便捷查询股票代码和交易所信息
        输入股票名称，返回股票代码、交易所代码（SZ/SH）和 secid
        例如：输入"中国平安"，返回 {"stock_code": "000001", "exchange": "SZ", "secid": "0.000001"}
        """
        stock_name = params.get('stock_name', '').strip()
        if not stock_name:
            raise ValueError('stock_name参数必填，请输入股票名称（如"中国平安"）')
        
        # 确保 stock_name 是正确的 UTF-8 字符串
        # 如果传入的是字节串，尝试解码
        if isinstance(stock_name, bytes):
            try:
                stock_name = stock_name.decode('utf-8')
            except UnicodeDecodeError:
                try:
                    stock_name = stock_name.decode('gbk')
                except UnicodeDecodeError:
                    stock_name = stock_name.decode('utf-8', errors='replace')
        
        # 查询股票信息
        sql = """
        SELECT stock_code, market_code, stock_name, secid
        FROM stock_list
        WHERE stock_name LIKE %s AND is_active = 1
        ORDER BY 
            CASE WHEN stock_name = %s THEN 1 ELSE 2 END,
            stock_code
        LIMIT 10
        """
        keyword_pattern = f'%{stock_name}%'
        stocks = db.execute_query(sql, (keyword_pattern, stock_name))
        
        if not stocks:
            # 使用安全的错误消息格式化，避免编码问题
            # 如果 stock_name 包含无法显示的字符，使用 repr 或转义
            try:
                # 尝试直接格式化
                safe_name = stock_name
                message = f'未找到股票名称包含"{safe_name}"的股票'
            except (UnicodeEncodeError, UnicodeDecodeError):
                # 如果格式化失败，使用安全的表示方式
                safe_name = repr(stock_name) if isinstance(stock_name, str) else str(stock_name)
                message = f'未找到匹配的股票（搜索关键词: {safe_name}）'
            
            return {
                'found': False,
                'message': message,
                'search_keyword': stock_name,  # 同时返回原始搜索关键词
                'suggestions': []
            }
        
        # 格式化结果
        results = []
        for stock in stocks:
            market_code = stock['market_code']
            # market_code: 0=深市(SZ), 1=沪市(SH)
            exchange = 'SZ' if market_code == 0 else 'SH'
            
            results.append({
                'stock_code': stock['stock_code'],
                'exchange': exchange,
                'secid': stock['secid'],
                'stock_name': stock['stock_name'],
                'market_code': market_code
            })
        
        # 如果只找到一个完全匹配的，直接返回第一个
        if len(results) == 1 or (len(results) > 0 and results[0]['stock_name'] == stock_name):
            return {
                'found': True,
                'stock_code': results[0]['stock_code'],
                'exchange': results[0]['exchange'],
                'secid': results[0]['secid'],
                'stock_name': results[0]['stock_name']
            }
        
        # 多个匹配结果，返回列表
        return {
            'found': True,
            'count': len(results),
            'message': f'找到 {len(results)} 个匹配结果，请选择：',
            'results': results
        }
    
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
            SELECT trade_date, main_net_inflow, super_large_net_inflow, large_net_inflow,
                   medium_net_inflow, small_net_inflow, main_net_inflow_ratio,
                   close_price, change_percent, turnover_rate, turnover_amount
            FROM stock_capital_flow_history
            WHERE secid = %s AND trade_date >= %s
            ORDER BY trade_date DESC
            """
            history = db.execute_query(sql, (secid, start_date))
        else:
            sql = """
            SELECT trade_date, main_net_inflow, super_large_net_inflow, large_net_inflow,
                   medium_net_inflow, small_net_inflow, main_net_inflow_ratio,
                   close_price, change_percent, turnover_rate, turnover_amount
            FROM stock_capital_flow_history
            WHERE secid = %s
            ORDER BY trade_date DESC
            LIMIT %s
            """
            history = db.execute_query(sql, (secid, limit))
        
        # 将 date 和 Decimal 对象转换为字符串/数字，确保 JSON 序列化正常
        from decimal import Decimal
        formatted_history = []
        for record in history:
            formatted_record = {}
            for key, value in record.items():
                if isinstance(value, date):
                    formatted_record[key] = value.strftime('%Y-%m-%d')
                elif isinstance(value, datetime):
                    formatted_record[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                elif isinstance(value, Decimal):
                    # Decimal 转换为 float
                    formatted_record[key] = float(value)
                elif value is None:
                    formatted_record[key] = None
                else:
                    formatted_record[key] = value
            formatted_history.append(formatted_record)
        
        return {'history': formatted_history}
    
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
    
    async def _sync_stock_list(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        同步股票列表（手工触发）
        注意：此操作可能需要较长时间，请耐心等待
        """
        delay = params.get('delay', 1.0)  # 默认1秒延迟
        
        # 提醒用户
        logger.info(f"开始同步股票列表，延迟设置: {delay}秒")
        
        # 执行同步（同步方法会返回详细统计）
        result = data_collector.sync_stock_list(delay=delay)
        
        return {
            'message': '股票列表同步完成，请查看详细统计',
            'result': result
        }
    
    async def _sync_stock_history(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        同步股票历史资金数据（手工触发）
        注意：此操作可能需要较长时间，请耐心等待
        
        参数:
            secid: 可选，股票完整代码（如 "0.000001"）。如果不提供，将同步所有股票
            limit: 可选，每只股票获取的历史数据条数，默认250
            delay: 可选，每只股票请求后的延迟时间（秒），默认1.0
        """
        secid = params.get('secid', None)
        limit = params.get('limit', 250)
        delay = params.get('delay', 1.0)
        
        import time
        
        if secid:
            # 同步单只股票
            logger.info(f"开始同步单只股票历史数据: {secid}")
            result = data_collector.sync_stock_capital_flow_history(secid, limit)
            
            return {
                'message': '单只股票历史数据同步完成',
                'result': result
            }
        else:
            # 同步所有股票
            logger.info("开始同步所有股票历史数据，这可能需要较长时间，请耐心等待...")
            
            # 获取所有股票列表
            sql = """
            SELECT stock_code, market_code, secid, stock_name
            FROM stock_list
            WHERE is_active = 1
            ORDER BY stock_code
            """
            stocks = db.execute_query(sql)
            total_stocks = len(stocks)
            
            if total_stocks == 0:
                return {
                    'message': '数据库中没有股票数据，请先同步股票列表',
                    'result': {'success': False, 'error': 'no_stocks'}
                }
            
            # 统计信息
            results = {
                'total_stocks': total_stocks,
                'success_count': 0,
                'fail_count': 0,
                'details': []
            }
            
            # 逐个同步
            for idx, stock in enumerate(stocks, 1):
                secid = stock['secid']
                stock_code = stock['stock_code']
                
                try:
                    result = data_collector.sync_stock_capital_flow_history(secid, limit)
                    if result.get('success'):
                        results['success_count'] += 1
                    else:
                        results['fail_count'] += 1
                    
                    results['details'].append({
                        'secid': secid,
                        'stock_code': stock_code,
                        'success': result.get('success', False),
                        'message': result.get('message', '')
                    })
                    
                    logger.info(f"[{idx}/{total_stocks}] {stock_code} 同步完成")
                    
                except Exception as e:
                    results['fail_count'] += 1
                    logger.error(f"同步 {secid} 失败: {e}")
                    results['details'].append({
                        'secid': secid,
                        'stock_code': stock_code,
                        'success': False,
                        'message': str(e)
                    })
                
                # 延迟（最后一只股票不需要延迟）
                if idx < total_stocks and delay > 0:
                    time.sleep(delay)
            
            return {
                'message': f'所有股票历史数据同步完成，成功 {results["success_count"]} 只，失败 {results["fail_count"]} 只',
                'result': results
            }


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
    def mcp_endpoint():
        import asyncio
        data = request.json
        # 在同步函数中运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(mcp_server.handle_request(data.get('method'), data))
            return jsonify(response)
        finally:
            loop.close()
    
    logger.info("启动MCP服务器")
    app.run(host='0.0.0.0', port=8889, debug=True)

