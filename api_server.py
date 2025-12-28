"""
Flask API服务器
端口：8887
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
import logging
from datetime import datetime
from services.data_collector import DataCollector
from services.health_calculator import HealthCalculator
from database.db_connection import db

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # 允许跨域

# 初始化服务
data_collector = DataCollector()
health_calculator = HealthCalculator()


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({'status': 'ok', 'message': 'API服务运行正常'})


# ==================== 用户相关API ====================

@app.route('/api/users', methods=['GET'])
def get_users():
    """获取用户列表"""
    try:
        sql = "SELECT id, username, email, phone, group_id, is_active, created_at FROM users"
        users = db.execute_query(sql)
        return jsonify({'code': 0, 'data': users})
    except Exception as e:
        logger.error(f"获取用户列表失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/user-groups', methods=['GET'])
def get_user_groups():
    """获取用户组列表"""
    try:
        sql = "SELECT id, group_name, description, permissions FROM user_groups"
        groups = db.execute_query(sql)
        return jsonify({'code': 0, 'data': groups})
    except Exception as e:
        logger.error(f"获取用户组列表失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


# ==================== 股票相关API ====================

@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    """获取股票列表"""
    try:
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 50))
        keyword = request.args.get('keyword', '')
        
        offset = (page - 1) * page_size
        
        if keyword:
            sql = """
            SELECT id, stock_code, market_code, stock_name, secid,
                   total_market_cap, circulating_market_cap, last_sync_time
            FROM stock_list
            WHERE (stock_name LIKE %s OR stock_code LIKE %s) AND is_active = 1
            ORDER BY stock_code
            LIMIT %s OFFSET %s
            """
            keyword_pattern = f'%{keyword}%'
            stocks = db.execute_query(sql, (keyword_pattern, keyword_pattern, page_size, offset))
        else:
            sql = """
            SELECT id, stock_code, market_code, stock_name, secid,
                   total_market_cap, circulating_market_cap, last_sync_time
            FROM stock_list
            WHERE is_active = 1
            ORDER BY stock_code
            LIMIT %s OFFSET %s
            """
            stocks = db.execute_query(sql, (page_size, offset))
        
        return jsonify({'code': 0, 'data': stocks})
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/stocks/<secid>/health', methods=['GET'])
def get_stock_health(secid):
    """获取股票健康度"""
    try:
        score_date_str = request.args.get('date')
        score_date = datetime.strptime(score_date_str, '%Y-%m-%d').date() if score_date_str else None
        
        health_data = health_calculator.calculate_health_score(secid, score_date)
        return jsonify({'code': 0, 'data': health_data})
    except Exception as e:
        logger.error(f"获取股票健康度失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/stocks/<secid>/history', methods=['GET'])
def get_stock_history(secid):
    """获取股票历史资金数据"""
    try:
        limit = int(request.args.get('limit', 30))
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if start_date and end_date:
            sql = """
            SELECT trade_date, main_net_inflow, super_large_net_inflow,
                   main_net_inflow_ratio, close_price, change_percent,
                   turnover_rate, turnover_amount
            FROM stock_capital_flow_history
            WHERE secid = %s AND trade_date BETWEEN %s AND %s
            ORDER BY trade_date DESC
            LIMIT %s
            """
            history = db.execute_query(sql, (secid, start_date, end_date, limit))
        else:
            sql = """
            SELECT trade_date, main_net_inflow, super_large_net_inflow,
                   main_net_inflow_ratio, close_price, change_percent,
                   turnover_rate, turnover_amount
            FROM stock_capital_flow_history
            WHERE secid = %s
            ORDER BY trade_date DESC
            LIMIT %s
            """
            history = db.execute_query(sql, (secid, limit))
        
        return jsonify({'code': 0, 'data': history})
    except Exception as e:
        logger.error(f"获取股票历史数据失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


# ==================== 实时数据API ====================

@app.route('/api/realtime/capital-flow', methods=['GET'])
def get_realtime_capital_flow():
    """获取实时资金流向（前20名）"""
    try:
        limit = int(request.args.get('limit', 20))
        sort_by = request.args.get('sort_by', 'main_net_inflow')  # 排序字段
        
        # 从API获取实时数据
        flow_data = data_collector.get_realtime_capital_flow(limit)
        
        # 按指定字段排序
        if sort_by == 'main_net_inflow':
            flow_data.sort(key=lambda x: x.get('main_net_inflow', 0), reverse=True)
        elif sort_by == 'change_percent':
            flow_data.sort(key=lambda x: x.get('change_percent', 0), reverse=True)
        
        return jsonify({'code': 0, 'data': flow_data[:limit]})
    except Exception as e:
        logger.error(f"获取实时资金流向失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/realtime/index', methods=['GET'])
def get_realtime_index():
    """获取实时指数数据"""
    try:
        index_data = data_collector.get_index_data()
        return jsonify({'code': 0, 'data': index_data})
    except Exception as e:
        logger.error(f"获取实时指数数据失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


# ==================== 用户股票看板API ====================

@app.route('/api/dashboard/my-stocks', methods=['GET'])
def get_my_stocks_dashboard():
    """获取我的股票看板数据"""
    try:
        user_id = int(request.args.get('user_id', 1))  # 默认用户ID为1
        
        # 获取用户持有的股票
        sql = """
        SELECT us.stock_code, us.market_code, us.secid, us.is_holding, us.is_favorite,
               sl.stock_name
        FROM user_stocks us
        LEFT JOIN stock_list sl ON us.stock_code = sl.stock_code AND us.market_code = sl.market_code
        WHERE us.user_id = %s AND (us.is_holding = 1 OR us.is_favorite = 1)
        """
        user_stocks = db.execute_query(sql, (user_id,))
        
        # 获取每只股票的健康度和最新数据
        dashboard_data = []
        for stock in user_stocks:
            secid = stock['secid']
            
            # 获取健康度
            health_data = health_calculator.calculate_health_score(secid)
            
            # 获取最新历史数据
            sql = """
            SELECT trade_date, main_net_inflow, close_price, change_percent
            FROM stock_capital_flow_history
            WHERE secid = %s
            ORDER BY trade_date DESC
            LIMIT 1
            """
            latest_data = db.execute_query(sql, (secid,))
            
            dashboard_data.append({
                'stock_code': stock['stock_code'],
                'stock_name': stock['stock_name'],
                'secid': secid,
                'is_holding': stock['is_holding'],
                'is_favorite': stock['is_favorite'],
                'health_score': health_data.get('health_score', 0),
                'trend_direction': health_data.get('trend_direction', 'unknown'),
                'risk_level': health_data.get('risk_level', 'high'),
                'latest_data': latest_data[0] if latest_data else None
            })
        
        return jsonify({'code': 0, 'data': dashboard_data})
    except Exception as e:
        logger.error(f"获取我的股票看板失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


# ==================== 数据同步API ====================

@app.route('/api/sync/stock-list', methods=['POST'])
def sync_stock_list():
    """同步个股列表"""
    try:
        data_collector.sync_stock_list()
        return jsonify({'code': 0, 'message': '同步成功'})
    except Exception as e:
        logger.error(f"同步个股列表失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/sync/stock-history/<secid>', methods=['POST'])
def sync_stock_history(secid):
    """同步个股历史数据"""
    try:
        limit = int(request.json.get('limit', 250) if request.json else 250)
        data_collector.sync_stock_capital_flow_history(secid, limit)
        return jsonify({'code': 0, 'message': '同步成功'})
    except Exception as e:
        logger.error(f"同步个股历史数据失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/sync/index', methods=['POST'])
def sync_index():
    """同步指数数据"""
    try:
        data_collector.sync_index_data()
        return jsonify({'code': 0, 'message': '同步成功'})
    except Exception as e:
        logger.error(f"同步指数数据失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


if __name__ == '__main__':
    logger.info("启动API服务器，端口: 8887")
    app.run(host='0.0.0.0', port=8887, debug=True)

