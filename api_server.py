"""
Flask API服务器
端口：8887
"""
from flask import Flask, jsonify, request
from flask_cors import CORS
from functools import wraps
import logging
import requests
from datetime import datetime
from services.data_collector import DataCollector
from services.health_calculator import HealthCalculator
from services.auth_service import AuthService
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


# ==================== 认证相关API ====================

def require_auth(f):
    """需要认证的装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # 从请求头获取 token
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # 格式: "Bearer <token>"
                token = auth_header.split(' ')[1] if ' ' in auth_header else auth_header
            except IndexError:
                return jsonify({'code': -1, 'message': 'Token 格式错误'}), 401
        
        # 从查询参数获取 token（备用方式）
        if not token:
            token = request.args.get('token')
        
        if not token:
            return jsonify({'code': -1, 'message': '缺少认证 token'}), 401
        
        # 验证 token
        payload = AuthService.verify_token(token)
        if not payload:
            return jsonify({'code': -1, 'message': 'Token 无效或已过期'}), 401
        
        # 将用户信息添加到请求上下文
        request.current_user_id = payload['user_id']
        request.current_username = payload['username']
        
        return f(*args, **kwargs)
    
    return decorated_function


@app.route('/api/auth/register', methods=['POST'])
def register():
    """用户注册"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        email = data.get('email', '').strip()
        phone = data.get('phone', '').strip()
        
        if not username or not password:
            return jsonify({'code': -1, 'message': '用户名和密码不能为空'}), 400
        
        if len(password) < 6:
            return jsonify({'code': -1, 'message': '密码长度至少6位'}), 400
        
        result = AuthService.register(username, password, email, phone)
        
        if result['success']:
            return jsonify({'code': 0, 'message': result['message'], 'data': result.get('user')})
        else:
            return jsonify({'code': -1, 'message': result['message']}), 400
    except Exception as e:
        logger.error(f"用户注册失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """用户登录"""
    try:
        data = request.get_json()
        username = data.get('username', '').strip()
        password = data.get('password', '').strip()
        
        if not username or not password:
            return jsonify({'code': -1, 'message': '用户名和密码不能为空'}), 400
        
        result = AuthService.login(username, password)
        
        if result['success']:
            return jsonify({
                'code': 0,
                'message': result['message'],
                'data': {
                    'token': result['token'],
                    'user': result['user']
                }
            })
        else:
            return jsonify({'code': -1, 'message': result['message']}), 401
    except Exception as e:
        logger.error(f"用户登录失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/auth/verify', methods=['GET'])
@require_auth
def verify_token():
    """验证 token（测试用）"""
    user = AuthService.get_user_by_id(request.current_user_id)
    return jsonify({
        'code': 0,
        'message': 'Token 有效',
        'data': {
            'user_id': request.current_user_id,
            'username': request.current_username,
            'user': user
        }
    })


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
@require_auth
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
@require_auth
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


# 指数数据缓存（避免频繁请求，降低风险）
_index_cache = {
    'data': None,
    'timestamp': None,
    'ttl': 300  # 缓存5分钟（300秒）
}

@app.route('/api/realtime/index', methods=['GET'])
@require_auth
def get_realtime_index():
    """
    获取实时指数数据
    注意：使用缓存机制，避免频繁网络请求（爬虫技术有风险，需慎用）
    """
    try:
        import time
        current_time = time.time()
        
        # 检查缓存是否有效
        if (_index_cache['data'] is not None and 
            _index_cache['timestamp'] is not None and
            current_time - _index_cache['timestamp'] < _index_cache['ttl']):
            logger.info("返回缓存的指数数据")
            return jsonify({'code': 0, 'data': _index_cache['data'], 'cached': True})
        
        # 缓存过期或不存在，从API获取
        logger.warning("从API获取指数数据（注意：这是网络请求，请谨慎使用）")
        index_data = data_collector.get_index_data()
        
        # 更新缓存
        _index_cache['data'] = index_data
        _index_cache['timestamp'] = current_time
        
        return jsonify({'code': 0, 'data': index_data, 'cached': False})
    except Exception as e:
        logger.error(f"获取实时指数数据失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


# ==================== 用户股票看板API ====================

@app.route('/api/dashboard/holdings', methods=['GET'])
@require_auth
def get_holdings():
    """获取用户持股股票的健康度"""
    try:
        user_id = request.current_user_id
        
        sql = """
        SELECT us.stock_code, us.stock_market as market_code, us.is_holding, us.is_favorite,
               us.holding_quantity, us.holding_cost, sl.stock_name, sl.secid
        FROM user_stocks us
        LEFT JOIN stock_list sl ON us.stock_code = sl.stock_code AND us.stock_market = sl.market_code
        WHERE us.user_id = %s AND us.is_holding = 1
        """
        holdings = db.execute_query(sql, (user_id,))
        
        result = []
        for stock in holdings:
            secid = stock.get('secid')
            if not secid:
                # 如果没有secid，尝试构造
                market_code = stock.get('market_code', 0)
                stock_code = stock.get('stock_code', '')
                secid = f"{market_code}.{stock_code}"
            
            try:
                health_data = health_calculator.calculate_health_score(secid)
            except Exception as e:
                logger.warning(f"计算健康度失败 {secid}: {e}")
                health_data = {'health_score': 0, 'trend_direction': 'unknown', 'risk_level': 'high'}
            
            sql_latest = """
            SELECT trade_date, main_net_inflow, close_price, change_percent
            FROM stock_capital_flow_history
            WHERE secid = %s
            ORDER BY trade_date DESC
            LIMIT 1
            """
            latest_data = db.execute_query(sql_latest, (secid,))
            
            sql_7d = """
            SELECT SUM(main_net_inflow) as main_net_inflow_7d
            FROM stock_capital_flow_history
            WHERE secid = %s
            AND trade_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            """
            inflow_7d = db.execute_query(sql_7d, (secid,))
            main_net_inflow_7d = float(inflow_7d[0]['main_net_inflow_7d'] or 0) if inflow_7d and inflow_7d[0]['main_net_inflow_7d'] else 0
            
            result.append({
                'stock_code': stock['stock_code'],
                'stock_name': stock['stock_name'],
                'secid': secid,
                'holding_quantity': stock['holding_quantity'],
                'holding_cost': float(stock['holding_cost']) if stock['holding_cost'] else 0,
                'health_score': health_data.get('health_score', 0),
                'trend_direction': health_data.get('trend_direction', 'unknown'),
                'risk_level': health_data.get('risk_level', 'high'),
                'main_net_inflow_7d': main_net_inflow_7d,
                'latest_data': latest_data[0] if latest_data else None
            })
        
        return jsonify({'code': 0, 'data': result})
    except Exception as e:
        logger.error(f"获取持股数据失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/dashboard/favorites', methods=['GET'])
@require_auth
def get_favorites():
    """获取用户收藏股票的推荐度"""
    try:
        user_id = request.current_user_id
        
        sql = """
        SELECT us.stock_code, us.stock_market as market_code, us.is_favorite,
               sl.stock_name, sl.secid
        FROM user_stocks us
        LEFT JOIN stock_list sl ON us.stock_code = sl.stock_code AND us.stock_market = sl.market_code
        WHERE us.user_id = %s AND us.is_favorite = 1 AND us.is_holding = 0
        """
        favorites = db.execute_query(sql, (user_id,))
        
        result = []
        for stock in favorites:
            secid = stock.get('secid')
            if not secid:
                # 如果没有secid，尝试构造
                market_code = stock.get('market_code', 0)
                stock_code = stock.get('stock_code', '')
                secid = f"{market_code}.{stock_code}"
            
            try:
                health_data = health_calculator.calculate_health_score(secid)
            except Exception as e:
                logger.warning(f"计算健康度失败 {secid}: {e}")
                health_data = {'health_score': 0, 'trend_direction': 'unknown', 'risk_level': 'high'}
            
            sql_latest = """
            SELECT trade_date, main_net_inflow, close_price, change_percent
            FROM stock_capital_flow_history
            WHERE secid = %s
            ORDER BY trade_date DESC
            LIMIT 1
            """
            latest_data = db.execute_query(sql_latest, (secid,))
            
            sql_7d = """
            SELECT SUM(main_net_inflow) as main_net_inflow_7d
            FROM stock_capital_flow_history
            WHERE secid = %s
            AND trade_date >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
            """
            inflow_7d = db.execute_query(sql_7d, (secid,))
            main_net_inflow_7d = float(inflow_7d[0]['main_net_inflow_7d'] or 0) if inflow_7d and inflow_7d[0]['main_net_inflow_7d'] else 0
            
            result.append({
                'stock_code': stock['stock_code'],
                'stock_name': stock['stock_name'],
                'secid': secid,
                'health_score': health_data.get('health_score', 0),
                'trend_direction': health_data.get('trend_direction', 'unknown'),
                'risk_level': health_data.get('risk_level', 'high'),
                'main_net_inflow_7d': main_net_inflow_7d,
                'latest_data': latest_data[0] if latest_data else None
            })
        
        return jsonify({'code': 0, 'data': result})
    except Exception as e:
        logger.error(f"获取收藏数据失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/dashboard/refresh-holdings', methods=['POST'])
@require_auth
def refresh_holdings():
    """刷新持股股票数据"""
    try:
        # 这里可以触发重新计算健康度等操作
        # 暂时只返回成功
        return jsonify({'code': 0, 'message': '刷新成功'})
    except Exception as e:
        logger.error(f"刷新持股数据失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/dashboard/refresh-favorites', methods=['POST'])
@require_auth
def refresh_favorites():
    """刷新收藏股票数据"""
    try:
        # 这里可以触发重新计算推荐度等操作
        # 暂时只返回成功
        return jsonify({'code': 0, 'message': '刷新成功'})
    except Exception as e:
        logger.error(f"刷新收藏数据失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


# ==================== 设置相关API ====================

@app.route('/api/settings/general', methods=['GET'])
@require_auth
def get_general_settings():
    """获取通用设置"""
    try:
        user_id = request.current_user_id
        sql = "SELECT theme, language FROM user_settings WHERE user_id = %s"
        settings = db.execute_query(sql, (user_id,))
        
        if settings:
            return jsonify({'code': 0, 'data': settings[0]})
        else:
            # 返回默认设置
            return jsonify({'code': 0, 'data': {'theme': 'system', 'language': 'zh-CN'}})
    except Exception as e:
        logger.error(f"获取通用设置失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/settings/general', methods=['POST'])
@require_auth
def save_general_settings():
    """保存通用设置"""
    try:
        user_id = request.current_user_id
        data = request.get_json()
        theme = data.get('theme', 'system')
        language = data.get('language', 'zh-CN')
        
        sql = """
        INSERT INTO user_settings (user_id, theme, language)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE theme = %s, language = %s, updated_at = CURRENT_TIMESTAMP
        """
        db.execute_update(sql, (user_id, theme, language, theme, language))
        
        return jsonify({'code': 0, 'message': '设置保存成功'})
    except Exception as e:
        logger.error(f"保存通用设置失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/settings/llm', methods=['GET'])
@require_auth
def get_llm_configs():
    """获取LLM配置"""
    try:
        user_id = request.current_user_id
        sql = "SELECT provider, api_url, model, is_enabled FROM user_llm_configs WHERE user_id = %s"
        configs = db.execute_query(sql, (user_id,))
        
        result = {}
        for config in configs:
            provider = config['provider']
            result[provider] = {
                'api_url': config['api_url'],
                'model': config['model'],
                'is_enabled': bool(config['is_enabled'])
            }
        
        return jsonify({'code': 0, 'data': result})
    except Exception as e:
        logger.error(f"获取LLM配置失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/settings/llm/<provider>', methods=['POST'])
@require_auth
def save_llm_config(provider):
    """保存LLM配置"""
    try:
        user_id = request.current_user_id
        data = request.get_json()
        
        api_url = data.get('api_url', '')
        model = data.get('model', '')
        api_key = data.get('api_key', '')
        is_enabled = data.get('is_enabled', False)
        
        # 如果提供了新的api_key，则更新；否则保持原值
        if api_key:
            sql = """
            INSERT INTO user_llm_configs (user_id, provider, api_url, model, api_key, is_enabled)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                api_url = %s, model = %s, api_key = %s, is_enabled = %s, updated_at = CURRENT_TIMESTAMP
            """
            db.execute_update(sql, (user_id, provider, api_url, model, api_key, is_enabled,
                                   api_url, model, api_key, is_enabled))
        else:
            sql = """
            INSERT INTO user_llm_configs (user_id, provider, api_url, model, is_enabled)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                api_url = %s, model = %s, is_enabled = %s, updated_at = CURRENT_TIMESTAMP
            """
            db.execute_update(sql, (user_id, provider, api_url, model, is_enabled,
                                   api_url, model, is_enabled))
        
        return jsonify({'code': 0, 'message': '配置保存成功'})
    except Exception as e:
        logger.error(f"保存LLM配置失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/settings/holdings', methods=['GET'])
@require_auth
def get_holdings_settings():
    """获取持股记录"""
    try:
        user_id = request.current_user_id
        sql = """
        SELECT us.id, us.stock_code, us.stock_market, us.holding_quantity, us.holding_cost,
               sl.stock_name
        FROM user_stocks us
        LEFT JOIN stock_list sl ON us.stock_code = sl.stock_code AND us.stock_market = sl.market_code
        WHERE us.user_id = %s AND us.is_holding = 1
        ORDER BY us.created_at DESC
        """
        holdings = db.execute_query(sql, (user_id,))
        return jsonify({'code': 0, 'data': holdings})
    except Exception as e:
        logger.error(f"获取持股记录失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/settings/holdings', methods=['POST'])
@require_auth
def add_holding():
    """添加持股记录"""
    try:
        user_id = request.current_user_id
        data = request.get_json()
        
        stock_code = data.get('stock_code', '').strip()
        stock_market = int(data.get('stock_market', 0))
        stock_name = data.get('stock_name', '').strip()
        holding_quantity = int(data.get('holding_quantity', 0))
        holding_cost = float(data.get('holding_cost', 0))
        
        if not stock_code:
            return jsonify({'code': -1, 'message': '股票代码不能为空'}), 400
        
        # 检查是否已存在
        sql_check = """
        SELECT id FROM user_stocks 
        WHERE user_id = %s AND stock_code = %s AND stock_market = %s
        """
        existing = db.execute_query(sql_check, (user_id, stock_code, stock_market))
        
        if existing:
            # 更新现有记录
            sql = """
            UPDATE user_stocks 
            SET is_holding = 1, holding_quantity = %s, holding_cost = %s, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND stock_code = %s AND stock_market = %s
            """
            db.execute_update(sql, (holding_quantity, holding_cost, user_id, stock_code, stock_market))
        else:
            # 插入新记录
            sql = """
            INSERT INTO user_stocks (user_id, stock_code, stock_market, is_holding, is_favorite, 
                                     holding_quantity, holding_cost, notes)
            VALUES (%s, %s, %s, 1, 1, %s, %s, %s)
            """
            db.execute_update(sql, (user_id, stock_code, stock_market, holding_quantity, holding_cost, 
                                   f'股票名称: {stock_name}' if stock_name else None))
        
        return jsonify({'code': 0, 'message': '添加成功'})
    except Exception as e:
        logger.error(f"添加持股记录失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/settings/holdings/<int:holding_id>', methods=['DELETE'])
@require_auth
def delete_holding(holding_id):
    """删除持股记录"""
    try:
        user_id = request.current_user_id
        
        # 检查记录是否存在且属于当前用户
        sql_check = "SELECT id FROM user_stocks WHERE id = %s AND user_id = %s"
        existing = db.execute_query(sql_check, (holding_id, user_id))
        
        if not existing:
            return jsonify({'code': -1, 'message': '记录不存在'}), 404
        
        # 删除记录（如果只是收藏，则只取消持股；如果只持股，则删除）
        sql = """
        UPDATE user_stocks 
        SET is_holding = 0, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND user_id = %s
        """
        db.execute_update(sql, (holding_id, user_id))
        
        # 如果既不是持股也不是收藏，则删除记录
        sql_clean = "DELETE FROM user_stocks WHERE id = %s AND is_holding = 0 AND is_favorite = 0"
        db.execute_update(sql_clean, (holding_id,))
        
        return jsonify({'code': 0, 'message': '删除成功'})
    except Exception as e:
        logger.error(f"删除持股记录失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/settings/favorites', methods=['GET'])
@require_auth
def get_favorites_settings():
    """获取收藏记录"""
    try:
        user_id = request.current_user_id
        sql = """
        SELECT us.id, us.stock_code, us.stock_market, sl.stock_name
        FROM user_stocks us
        LEFT JOIN stock_list sl ON us.stock_code = sl.stock_code AND us.stock_market = sl.market_code
        WHERE us.user_id = %s AND us.is_favorite = 1
        ORDER BY us.created_at DESC
        """
        favorites = db.execute_query(sql, (user_id,))
        return jsonify({'code': 0, 'data': favorites})
    except Exception as e:
        logger.error(f"获取收藏记录失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/settings/favorites', methods=['POST'])
@require_auth
def add_favorite():
    """添加收藏记录"""
    try:
        user_id = request.current_user_id
        data = request.get_json()
        
        stock_code = data.get('stock_code', '').strip()
        stock_market = int(data.get('stock_market', 0))
        stock_name = data.get('stock_name', '').strip()
        
        if not stock_code:
            return jsonify({'code': -1, 'message': '股票代码不能为空'}), 400
        
        # 检查是否已存在
        sql_check = """
        SELECT id FROM user_stocks 
        WHERE user_id = %s AND stock_code = %s AND stock_market = %s
        """
        existing = db.execute_query(sql_check, (user_id, stock_code, stock_market))
        
        if existing:
            # 更新现有记录
            sql = """
            UPDATE user_stocks 
            SET is_favorite = 1, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s AND stock_code = %s AND stock_market = %s
            """
            db.execute_update(sql, (user_id, stock_code, stock_market))
        else:
            # 插入新记录
            sql = """
            INSERT INTO user_stocks (user_id, stock_code, stock_market, is_holding, is_favorite, notes)
            VALUES (%s, %s, %s, 0, 1, %s)
            """
            db.execute_update(sql, (user_id, stock_code, stock_market, 
                                   f'股票名称: {stock_name}' if stock_name else None))
        
        return jsonify({'code': 0, 'message': '添加成功'})
    except Exception as e:
        logger.error(f"添加收藏记录失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/settings/favorites/<int:favorite_id>', methods=['DELETE'])
@require_auth
def delete_favorite(favorite_id):
    """删除收藏记录"""
    try:
        user_id = request.current_user_id
        
        # 检查记录是否存在且属于当前用户
        sql_check = "SELECT id FROM user_stocks WHERE id = %s AND user_id = %s"
        existing = db.execute_query(sql_check, (favorite_id, user_id))
        
        if not existing:
            return jsonify({'code': -1, 'message': '记录不存在'}), 404
        
        # 删除记录（如果只是收藏，则只取消收藏；如果还持股，则只取消收藏）
        sql = """
        UPDATE user_stocks 
        SET is_favorite = 0, updated_at = CURRENT_TIMESTAMP
        WHERE id = %s AND user_id = %s
        """
        db.execute_update(sql, (favorite_id, user_id))
        
        # 如果既不是持股也不是收藏，则删除记录
        sql_clean = "DELETE FROM user_stocks WHERE id = %s AND is_holding = 0 AND is_favorite = 0"
        db.execute_update(sql_clean, (favorite_id,))
        
        return jsonify({'code': 0, 'message': '删除成功'})
    except Exception as e:
        logger.error(f"删除收藏记录失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


# ==================== 数据同步API ====================

@app.route('/api/sync/stock-list', methods=['POST'])
@require_auth
def sync_stock_list():
    """同步个股列表"""
    try:
        data_collector.sync_stock_list()
        return jsonify({'code': 0, 'message': '同步成功'})
    except Exception as e:
        logger.error(f"同步个股列表失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


@app.route('/api/sync/stock-history/<secid>', methods=['POST'])
@require_auth
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
@require_auth
def sync_index():
    """同步指数数据"""
    try:
        data_collector.sync_index_data()
        return jsonify({'code': 0, 'message': '同步成功'})
    except Exception as e:
        logger.error(f"同步指数数据失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


# ==================== 推荐股票API ====================

@app.route('/api/recommendations/stocks', methods=['GET'])
@require_auth
def get_recommended_stocks():
    """
    获取推荐股票（从数据库读取，已预计算）
    """
    try:
        import json
        from datetime import date
        
        # 获取推荐日期，默认为今天
        recommend_date_str = request.args.get('date')
        if recommend_date_str:
            recommend_date = datetime.strptime(recommend_date_str, '%Y-%m-%d').date()
        else:
            recommend_date = date.today()
        
        # 从数据库读取推荐股票
        sql = """
        SELECT recommend_date, stock_code, stock_name, secid, current_price, change_percent,
               total_main_inflow_10d, total_small_inflow_10d, volatility, max_change, min_change,
               recommend_reasons, sort_order
        FROM recommended_stocks
        WHERE recommend_date = %s
        ORDER BY sort_order ASC
        """
        
        recommendations = db.execute_query(sql, (recommend_date,))
        
        from decimal import Decimal
        
        result = []
        for rec in recommendations:
            # 解析推荐原因
            reasons = []
            if rec.get('recommend_reasons'):
                try:
                    reasons = json.loads(rec['recommend_reasons']) if isinstance(rec['recommend_reasons'], str) else rec['recommend_reasons']
                except (json.JSONDecodeError, TypeError):
                    reasons = []
            
            # 处理日期格式
            recommend_date_value = rec.get('recommend_date')
            if isinstance(recommend_date_value, date):
                recommend_date_str = recommend_date_value.strftime('%Y-%m-%d')
            elif isinstance(recommend_date_value, datetime):
                recommend_date_str = recommend_date_value.strftime('%Y-%m-%d')
            else:
                recommend_date_str = str(recommend_date_value)
            
            # 处理 Decimal 类型转换
            def to_float(value):
                if value is None:
                    return 0.0
                if isinstance(value, Decimal):
                    return float(value)
                return float(value)
            
            result.append({
                'recommend_date': recommend_date_str,
                'stock_code': rec['stock_code'],
                'stock_name': rec['stock_name'],
                'secid': rec['secid'],
                'latest_price': to_float(rec.get('current_price', 0)),
                'latest_change': to_float(rec.get('change_percent', 0)),
                'total_main_inflow_10d': to_float(rec.get('total_main_inflow_10d', 0)),
                'total_small_inflow_10d': to_float(rec.get('total_small_inflow_10d', 0)),
                'volatility': to_float(rec.get('volatility', 0)),
                'max_change': to_float(rec.get('max_change', 0)),
                'min_change': to_float(rec.get('min_change', 0)),
                'reasons': reasons
            })
        
        return jsonify({'code': 0, 'data': result})
    except Exception as e:
        logger.error(f"获取推荐股票失败: {e}")
        return jsonify({'code': -1, 'message': str(e)}), 500


# ==================== 智能聊天API ====================

@app.route('/api/chat', methods=['POST'])
@require_auth
def chat():
    """智能聊天接口，调用用户配置的 LLM"""
    try:
        import json
        
        user_id = request.current_user_id
        data = request.get_json()
        user_message = data.get('message', '').strip()
        conversation_id = data.get('conversation_id', 'default')
        
        if not user_message:
            return jsonify({'code': -1, 'message': '消息不能为空'}), 400
        
        # 获取用户启用的 LLM 配置
        sql = """
        SELECT provider, api_url, model, api_key 
        FROM user_llm_configs 
        WHERE user_id = %s AND is_enabled = 1
        ORDER BY provider = 'deepseek' DESC, provider = 'chatgpt' DESC
        LIMIT 1
        """
        llm_configs = db.execute_query(sql, (user_id,))
        
        if not llm_configs:
            return jsonify({'code': -1, 'message': '请先在设置中配置并启用 LLM（DeepSeek 或 ChatGPT）'}), 400
        
        config = llm_configs[0]
        provider = config['provider']
        api_url = config['api_url']
        model = config['model']
        api_key = config.get('api_key', '')
        
        if not api_url or not model or not api_key:
            return jsonify({'code': -1, 'message': 'LLM 配置不完整，请检查 API URL、Model 和 API Key'}), 400
        
        # 构建系统提示词（注入股票数据上下文）
        system_prompt = """你是一个专业的股票资金流动分析助手。你可以帮助用户分析股票资金流向、推荐股票、解读市场趋势等。

你可以访问以下数据：
- 实时资金流向数据
- 股票历史资金数据
- 推荐股票列表
- 用户关注的股票健康度

请用专业、简洁的语言回答用户的问题。如果涉及具体股票，请基于数据给出客观分析。"""
        
        # 构建消息列表
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_message}
        ]
        
        # 根据不同的 provider 调用不同的 API
        if provider == 'deepseek':
            # DeepSeek API 格式
            chat_url = f"{api_url.rstrip('/')}/chat/completions"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            payload = {
                'model': model,
                'messages': messages,
                'temperature': 0.7,
                'max_tokens': 2000
            }
        elif provider == 'chatgpt':
            # ChatGPT/OpenAI API 格式
            chat_url = f"{api_url.rstrip('/')}/chat/completions"
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            payload = {
                'model': model,
                'messages': messages,
                'temperature': 0.7,
                'max_tokens': 2000
            }
        else:
            return jsonify({'code': -1, 'message': f'不支持的 LLM 提供商: {provider}'}), 400
        
        # 调用 LLM API
        try:
            response = requests.post(chat_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result_data = response.json()
            
            # 提取回复内容
            if 'choices' in result_data and len(result_data['choices']) > 0:
                assistant_message = result_data['choices'][0]['message']['content']
                return jsonify({
                    'code': 0,
                    'data': {
                        'response': assistant_message,
                        'provider': provider,
                        'model': model
                    }
                })
            else:
                return jsonify({'code': -1, 'message': 'LLM API 返回格式异常'}), 500
                
        except requests.exceptions.RequestException as e:
            logger.error(f"调用 LLM API 失败: {e}")
            return jsonify({'code': -1, 'message': f'调用 LLM API 失败: {str(e)}'}), 500
        
    except Exception as e:
        logger.error(f"聊天接口失败: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'code': -1, 'message': str(e)}), 500


if __name__ == '__main__':
    logger.info("启动API服务器，端口: 8887")
    app.run(host='0.0.0.0', port=8887, debug=True)

