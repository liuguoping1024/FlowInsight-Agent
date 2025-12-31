"""
数据采集服务
从东方财富API采集股票数据
使用 services/eastmoney_api.py 统一封装的API接口
"""
import logging
from datetime import datetime
from typing import List, Dict
import pandas as pd
from database.db_connection import db
from config import INDICES_MAP
from services.eastmoney_api import (
    get_all_a_stocks,
    get_realtime_quotes,
    get_history_capital_flow,
    get_latest_quotes
)

logger = logging.getLogger(__name__)


class DataCollector:
    """数据采集器"""
    
    def __init__(self):
        # 不再需要 requests.Session，所有网络请求都通过 eastmoney_api 模块
        pass
    
    def get_stock_list(self, page_size: int = 8000, delay: float = 1.0) -> List[Dict]:
        """
        获取A股个股列表（使用 eastmoney_api.get_all_a_stocks 自动分页）
        
        Args:
            page_size: 每页数量（已废弃，get_all_a_stocks 内部使用固定分页大小）
            delay: 每次请求后的延迟时间（已废弃，get_all_a_stocks 内部已处理延迟）
        """
        try:
            # 使用 eastmoney_api 模块的 get_all_a_stocks 函数
            # 请求字段：f12(代码), f13(市场), f14(名称), f20(总市值), f21(流通市值)
            fields = "f12,f13,f14,f20,f21"
            logger.info("Fetching all A-stock data using eastmoney_api.get_all_a_stocks...")
            
            df = get_all_a_stocks(fields=fields, timeout=30)
            
            if df.empty:
                logger.warning("No stock data retrieved")
                return []
            
            # 转换为原来的格式
            all_stocks = []
            for _, row in df.iterrows():
                stock_code = str(row.get('f12', ''))
                market_code = int(row.get('f13', 1))  # 0=深市，1=沪市
                stock_name = str(row.get('f14', ''))
                total_market_cap = float(row.get('f20', 0)) if pd.notna(row.get('f20')) else 0  # f20=总市值
                circulating_market_cap = float(row.get('f21', 0)) if pd.notna(row.get('f21')) else 0  # f21=流通市值
                
                secid = f"{market_code}.{stock_code}"
                all_stocks.append({
                    'stock_code': stock_code,
                    'market_code': market_code,
                    'stock_name': stock_name,
                    'secid': secid,
                    'total_market_cap': total_market_cap,
                    'circulating_market_cap': circulating_market_cap
                })
            
            logger.info(f"Stock list fetch completed, total {len(all_stocks)} items")
            return all_stocks
            
        except Exception as e:
            logger.error(f"Failed to get stock list: {e}")
            return []
    
    def sync_stock_list(self, delay: float = 1.0) -> Dict:
        """
        同步个股列表到数据库（增强版，包含同步前后检查）
        返回同步结果统计
        
        Args:
            delay: 每次请求后的延迟时间（秒），默认1秒
        """
        result = {
            'success': False,
            'message': '',
            'before_sync': {},
            'after_sync': {},
            'sync_stats': {
                'api_returned_count': 0,
                'new_stocks': 0,
                'updated_stocks': 0
            }
        }
        
        # 1. 同步前检查：查询数据库中已有的股票数量
        try:
            sql_before = """
            SELECT COUNT(*) as total_stocks
            FROM stock_list
            WHERE is_active = 1
            """
            before_data = db.execute_query(sql_before)
            result['before_sync'] = {
                'total_stocks': before_data[0]['total_stocks'] if before_data else 0
            }
        except Exception as e:
            logger.warning(f"Pre-sync check failed: {e}")
            result['before_sync'] = {'error': str(e)}
        
        # 2. 从API获取数据
        stocks = self.get_stock_list(delay=delay)
        if not stocks:
            result['message'] = '未获取到个股数据'
            logger.warning(result['message'])
            return result
        
        result['sync_stats']['api_returned_count'] = len(stocks)
        
        # 3. 检查哪些是新股票，哪些是更新股票
        if result['before_sync'].get('total_stocks', 0) > 0:
            # 查询数据库中已存在的股票代码
            sql_existing = """
            SELECT secid
            FROM stock_list
            WHERE is_active = 1
            """
            existing_secids = {row['secid'] for row in db.execute_query(sql_existing)}
            
            new_secids = [s['secid'] for s in stocks if s['secid'] not in existing_secids]
            update_secids = [s['secid'] for s in stocks if s['secid'] in existing_secids]
            
            result['sync_stats']['new_stocks'] = len(new_secids)
            result['sync_stats']['updated_stocks'] = len(update_secids)
        else:
            # 首次同步，全部是新股票
            result['sync_stats']['new_stocks'] = len(stocks)
            result['sync_stats']['updated_stocks'] = 0
        
        # 4. 执行数据库插入/更新
        sql = """
        INSERT INTO stock_list (stock_code, market_code, stock_name, secid, 
                               total_market_cap, circulating_market_cap, last_sync_time)
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
            stock_name = VALUES(stock_name),
            total_market_cap = VALUES(total_market_cap),
            circulating_market_cap = VALUES(circulating_market_cap),
            last_sync_time = NOW(),
            updated_at = NOW()
        """
        
        params_list = [
            (s['stock_code'], s['market_code'], s['stock_name'], s['secid'],
             s['total_market_cap'], s['circulating_market_cap'])
            for s in stocks
        ]
        
        try:
            affected = db.execute_many(sql, params_list)
            logger.info(f"Stock list sync successful, {affected} records")
            
            # 5. 同步后检查：查询更新后的股票数量
            sql_after = """
            SELECT COUNT(*) as total_stocks
            FROM stock_list
            WHERE is_active = 1
            """
            after_data = db.execute_query(sql_after)
            result['after_sync'] = {
                'total_stocks': after_data[0]['total_stocks'] if after_data else 0
            }
            
            result['success'] = True
            result['message'] = f'同步成功，新增 {result["sync_stats"]["new_stocks"]} 只，更新 {result["sync_stats"]["updated_stocks"]} 只'
            
        except Exception as e:
            logger.error(f"Stock list sync failed: {e}")
            result['message'] = f'同步失败: {str(e)}'
            result['success'] = False
        
        return result
    
    def get_realtime_capital_flow(self, limit: int = 20) -> List[Dict]:
        """
        获取实时资金流向（前N名）
        使用 eastmoney_api.get_realtime_quotes 接口
        """
        try:
            # 使用 eastmoney_api 模块的 get_realtime_quotes 函数
            # 筛选条件：A股市场
            fs = 'm:0+t:6+f:!2,m:0+t:13+f:!2,m:0+t:80+f:!2,m:1+t:2+f:!2,m:1+t:23+f:!2,m:0+t:7+f:!2,m:1+t:3+f:!2'
            fields = 'f12,f13,f14,f2,f3,f62,f66,f69,f72,f75'  # 资金流向相关字段
            # f62: 主力净流入, f66: 超大单净流入, f69: 大单净流入, f72: 中单净流入, f75: 小单净流入
            
            # 获取更多数据以便排序后取前N名（获取 limit * 2 条数据以确保有足够的数据）
            fetch_limit = max(limit * 2, 100)
            
            logger.info(f"Fetching realtime capital flow data (top {limit})...")
            df = get_realtime_quotes(
                fs=fs,
                pn=1,
                pz=fetch_limit,
                po=1,  # 排序方式（虽然不能按f62排序，但我们可以手动排序）
                np=1,
                fields=fields,
                timeout=30
            )
            
            if df.empty:
                logger.warning("No capital flow data retrieved")
                return []
            
            # 确保 f62 字段存在且为数值类型，然后按主力净流入降序排序
            if 'f62' in df.columns:
                # 确保 f62 是数值类型
                df['f62'] = pd.to_numeric(df['f62'], errors='coerce')
                # 按主力净流入降序排序，取前 limit 条
                df = df.sort_values('f62', ascending=False).head(limit)
            else:
                # 如果 f62 字段不存在，只取前 limit 条
                df = df.head(limit)
            
            # 转换为原来的格式
            results = []
            for _, row in df.iterrows():
                stock_code = str(row.get('f12', ''))
                market_code = int(row.get('f13', 1))
                stock_name = str(row.get('f14', ''))
                current_price = float(row.get('f2', 0)) if pd.notna(row.get('f2')) else 0
                change_percent = float(row.get('f3', 0)) if pd.notna(row.get('f3')) else 0
                main_net_inflow = float(row.get('f62', 0)) if pd.notna(row.get('f62')) else 0  # 主力净流入
                super_large_net_inflow = float(row.get('f66', 0)) if pd.notna(row.get('f66')) else 0  # 超大单净流入
                large_net_inflow = float(row.get('f69', 0)) if pd.notna(row.get('f69')) else 0  # 大单净流入
                medium_net_inflow = float(row.get('f72', 0)) if pd.notna(row.get('f72')) else 0  # 中单净流入
                small_net_inflow = float(row.get('f75', 0)) if pd.notna(row.get('f75')) else 0  # 小单净流入
                
                secid = f"{market_code}.{stock_code}"
                results.append({
                    'stock_code': stock_code,
                    'market_code': market_code,
                    'stock_name': stock_name,
                    'secid': secid,
                    'current_price': current_price,
                    'change_percent': change_percent,
                    'main_net_inflow': main_net_inflow,
                    'super_large_net_inflow': super_large_net_inflow,
                    'large_net_inflow': large_net_inflow,
                    'medium_net_inflow': medium_net_inflow,
                    'small_net_inflow': small_net_inflow,
                })
            
            return results
        except Exception as e:
            logger.error(f"Failed to get realtime capital flow: {e}")
            return []
    
    def get_stock_capital_flow_history(self, secid: str, limit: int = 250) -> List[Dict]:
        """
        获取个股历史资金数据
        使用 eastmoney_api.get_history_capital_flow 接口
        """
        try:
            # 解析secid
            market_code, stock_code = secid.split('.')
            market_code_int = int(market_code)
            
            # 使用 eastmoney_api 模块的 get_history_capital_flow 函数
            logger.info(f"Fetching history capital flow data for {secid}...")
            df = get_history_capital_flow(
                code=stock_code,
                lmt=limit,
                market=market_code_int,
                timeout=30
            )
            
            if df.empty:
                logger.warning(f"No history capital flow data for {secid}")
                return []
            
            # 根据 eastmoney_api 的字段映射转换数据
            # get_history_capital_flow 返回的 DataFrame 包含以下字段：
            # f51: 日期, f52: 主力净流入, f53: 超大单净流入, f54: 大单净流入, 
            # f55: 中单净流入, f56: 小单净流入, f57: 主力净流入占比, ...
            # 注意：根据 CAPITAL_FLOW_FIELDS 映射，实际字段顺序可能不同
            # 需要根据实际返回的字段进行映射
            
            results = []
            for _, row in df.iterrows():
                try:
                    # f51 是日期字段（已转换为 datetime）
                    trade_date = row.get('f51')
                    if pd.isna(trade_date):
                        continue
                    if isinstance(trade_date, pd.Timestamp):
                        trade_date = trade_date.date()
                    elif isinstance(trade_date, str):
                        trade_date = datetime.strptime(trade_date, '%Y-%m-%d').date()
                    
                    # 根据 CAPITAL_FLOW_FIELDS 映射：
                    # f52: main_net_inflow (主力净流入)
                    # f53: super_large_net_inflow (超大单净流入)
                    # f54: large_net_inflow (大单净流入)
                    # f55: medium_net_inflow (中单净流入)
                    # f56: small_net_inflow (小单净流入)
                    # f57: main_net_inflow_pct (主力净流入占比)
                    # f61: small_net_inflow_pct (小单净流入占比)
                    # f62: main_net_inflow_trend (主力净流入趋势)
                    # f63: main_net_inflow_trend_pct (主力净流入趋势占比)
                    
                    main_net_inflow = float(row.get('f52', 0)) if pd.notna(row.get('f52')) else 0
                    super_large_net_inflow = float(row.get('f53', 0)) if pd.notna(row.get('f53')) else 0
                    large_net_inflow = float(row.get('f54', 0)) if pd.notna(row.get('f54')) else 0
                    medium_net_inflow = float(row.get('f55', 0)) if pd.notna(row.get('f55')) else 0
                    small_net_inflow = float(row.get('f56', 0)) if pd.notna(row.get('f56')) else 0
                    main_net_inflow_ratio = float(row.get('f57', 0)) if pd.notna(row.get('f57')) else 0
                    
                    # 尝试获取收盘价和涨跌幅（如果存在）
                    # 注意：get_history_capital_flow 可能不包含这些字段，需要从其他API获取
                    close_price = float(row.get('f61', 0)) if pd.notna(row.get('f61')) and 'f61' in row.index else None
                    change_percent = float(row.get('f62', 0)) if pd.notna(row.get('f62')) and 'f62' in row.index else None
                    
                    # 如果 close_price 和 change_percent 不在资金流向数据中，设为 None
                    # 这些数据可能需要从 K线数据中获取
                    if close_price == 0:
                        close_price = None
                    if change_percent == 0:
                        change_percent = None
                    
                    turnover_amount = None  # 成交额（API未提供）
                    turnover_rate = None   # 换手率（API未提供）
                    
                    # 将原始数据转换为JSON字符串格式存储
                    import json
                    raw_data_dict = {col: str(row[col]) if pd.notna(row[col]) else None for col in df.columns}
                    raw_data_json = json.dumps(raw_data_dict, ensure_ascii=False)
                    
                    results.append({
                        'stock_code': stock_code,
                        'market_code': market_code_int,
                        'secid': secid,
                        'trade_date': trade_date,
                        'main_net_inflow': main_net_inflow,  # f52: 主力净流入
                        'super_large_net_inflow': super_large_net_inflow,  # f53: 超大单净流入
                        'large_net_inflow': large_net_inflow,  # f54: 大单净流入
                        'medium_net_inflow': medium_net_inflow,  # f55: 中单净流入
                        'small_net_inflow': small_net_inflow,  # f56: 小单净流入
                        'main_net_inflow_ratio': main_net_inflow_ratio,  # f57: 主力净流入占比
                        'close_price': close_price,  # f61: 收盘价（如果存在）
                        'change_percent': change_percent,  # f62: 涨跌幅（如果存在）
                        'turnover_rate': turnover_rate,  # 换手率（待确认字段）
                        'turnover_amount': turnover_amount,  # 成交额（待确认字段）
                        'raw_data': raw_data_json
                    })
                except Exception as e:
                    logger.warning(f"Failed to parse history data row: {e}")
                    continue
            
            return results
        except Exception as e:
            logger.error(f"Failed to get stock history capital flow data: {e}, secid: {secid}")
            return []
    
    def sync_stock_capital_flow_history(self, secid: str, limit: int = 250) -> Dict:
        """
        同步个股历史资金数据到数据库（增强版，包含同步前后检查）
        返回同步结果统计
        """
        result = {
            'secid': secid,
            'success': False,
            'message': '',
            'before_sync': {},
            'after_sync': {},
            'sync_stats': {
                'api_returned_days': 0,
                'new_days': 0,
                'updated_days': 0,
                'date_range': {}
            }
        }
        
        # 1. 同步前检查：查询数据库中已有的数据范围
        try:
            sql_before = """
            SELECT 
                MIN(trade_date) as earliest_date,
                MAX(trade_date) as latest_date,
                COUNT(*) as total_records
            FROM stock_capital_flow_history
            WHERE secid = %s
            """
            before_data = db.execute_query(sql_before, (secid,))
            if before_data and before_data[0]['earliest_date']:
                result['before_sync'] = {
                    'earliest_date': str(before_data[0]['earliest_date']),
                    'latest_date': str(before_data[0]['latest_date']),
                    'total_records': before_data[0]['total_records']
                }
            else:
                result['before_sync'] = {
                    'earliest_date': None,
                    'latest_date': None,
                    'total_records': 0
                }
        except Exception as e:
            logger.warning(f"Pre-sync check failed: {e}")
            result['before_sync'] = {'error': str(e)}
        
        # 2. 从API获取数据
        history_data = self.get_stock_capital_flow_history(secid, limit)
        if not history_data:
            result['message'] = f'未获取到历史数据: {secid}'
            logger.warning(result['message'])
            return result
        
        # 统计API返回的数据
        api_dates = [d['trade_date'] for d in history_data]
        result['sync_stats']['api_returned_days'] = len(history_data)
        result['sync_stats']['date_range'] = {
            'earliest': str(min(api_dates)) if api_dates else None,
            'latest': str(max(api_dates)) if api_dates else None
        }
        
        # 3. 检查哪些是新数据，哪些是更新数据
        if result['before_sync'].get('total_records', 0) > 0:
            # 查询数据库中已存在的日期
            sql_existing = """
            SELECT trade_date
            FROM stock_capital_flow_history
            WHERE secid = %s
            """
            existing_dates = {row['trade_date'] for row in db.execute_query(sql_existing, (secid,))}
            
            new_dates = [d for d in api_dates if d not in existing_dates]
            update_dates = [d for d in api_dates if d in existing_dates]
            
            result['sync_stats']['new_days'] = len(new_dates)
            result['sync_stats']['updated_days'] = len(update_dates)
        else:
            # 首次同步，全部是新数据
            result['sync_stats']['new_days'] = len(history_data)
            result['sync_stats']['updated_days'] = 0
        
        # 4. 执行数据库插入/更新
        sql = """
        INSERT INTO stock_capital_flow_history (
            stock_code, market_code, secid, trade_date,
            main_net_inflow, super_large_net_inflow, large_net_inflow,
            medium_net_inflow, small_net_inflow, main_net_inflow_ratio,
            close_price, change_percent, turnover_rate, turnover_amount, raw_data
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            main_net_inflow = VALUES(main_net_inflow),
            super_large_net_inflow = VALUES(super_large_net_inflow),
            large_net_inflow = VALUES(large_net_inflow),
            medium_net_inflow = VALUES(medium_net_inflow),
            small_net_inflow = VALUES(small_net_inflow),
            main_net_inflow_ratio = VALUES(main_net_inflow_ratio),
            close_price = VALUES(close_price),
            change_percent = VALUES(change_percent),
            turnover_rate = COALESCE(VALUES(turnover_rate), turnover_rate),
            turnover_amount = COALESCE(VALUES(turnover_amount), turnover_amount),
            raw_data = VALUES(raw_data),
            updated_at = NOW()
        """
        
        params_list = [
            (d['stock_code'], d['market_code'], d['secid'], d['trade_date'],
             d['main_net_inflow'], d['super_large_net_inflow'], d['large_net_inflow'],
             d['medium_net_inflow'], d['small_net_inflow'], d['main_net_inflow_ratio'],
             d['close_price'], d['change_percent'], d['turnover_rate'],
             d['turnover_amount'], d['raw_data'])
            for d in history_data
        ]
        
        try:
            affected = db.execute_many(sql, params_list)
            logger.info(f"History capital flow data sync successful, secid: {secid}, {affected} records")
            
            # 5. 同步后检查：查询更新后的数据范围
            sql_after = """
            SELECT 
                MIN(trade_date) as earliest_date,
                MAX(trade_date) as latest_date,
                COUNT(*) as total_records
            FROM stock_capital_flow_history
            WHERE secid = %s
            """
            after_data = db.execute_query(sql_after, (secid,))
            if after_data and after_data[0]['earliest_date']:
                result['after_sync'] = {
                    'earliest_date': str(after_data[0]['earliest_date']),
                    'latest_date': str(after_data[0]['latest_date']),
                    'total_records': after_data[0]['total_records']
                }
            
            result['success'] = True
            result['message'] = f'同步成功，新增 {result["sync_stats"]["new_days"]} 天，更新 {result["sync_stats"]["updated_days"]} 天'
            
        except Exception as e:
            logger.error(f"History capital flow data sync failed: {e}")
            result['message'] = f'同步失败: {str(e)}'
            result['success'] = False
        
        return result
    
    def get_index_data(self) -> List[Dict]:
        """
        获取指数数据
        使用 eastmoney_api.get_latest_quotes 接口
        """
        try:
            # 获取所有指数的 secid 列表
            secids = list(INDICES_MAP.keys())
            
            if not secids:
                logger.warning("No indices configured in INDICES_MAP")
                return []
            
            # 使用 eastmoney_api 模块的 get_latest_quotes 函数
            # 请求字段：f1, f2(最新价), f3(涨跌幅), f4(涨跌额), f6(成交额), f12(代码), f13(市场), f104(上涨家数), f105(下跌家数), f106(平盘家数)
            fields = 'f1,f2,f3,f4,f6,f12,f13,f104,f105,f106'
            
            logger.info(f"Fetching index data for {len(secids)} indices...")
            df = get_latest_quotes(quote_ids=secids, fields=fields, timeout=30)
            
            if df.empty:
                logger.warning("No index data retrieved")
                return []
            
            # 转换为原来的格式
            results = []
            for _, row in df.iterrows():
                index_code = str(row.get('f12', ''))
                market_code = int(row.get('f13', 1))
                current_value = float(row.get('f2', 0)) if pd.notna(row.get('f2')) else 0
                change_value = float(row.get('f4', 0)) if pd.notna(row.get('f4')) else 0
                change_percent = float(row.get('f3', 0)) if pd.notna(row.get('f3')) else 0
                total_amount = float(row.get('f6', 0)) if pd.notna(row.get('f6')) else 0
                up_count = int(row.get('f104', 0)) if pd.notna(row.get('f104')) else 0
                down_count = int(row.get('f105', 0)) if pd.notna(row.get('f105')) else 0
                flat_count = int(row.get('f106', 0)) if pd.notna(row.get('f106')) else 0
                
                secid = f"{market_code}.{index_code}"
                index_name = INDICES_MAP.get(secid, '')
                
                results.append({
                    'index_code': index_code,
                    'index_name': index_name,
                    'secid': secid,
                    'current_value': current_value,
                    'change_value': change_value,
                    'change_percent': change_percent,
                    'total_amount': total_amount,
                    'up_count': up_count,
                    'down_count': down_count,
                    'flat_count': flat_count,
                })
            
            return results
        except Exception as e:
            logger.error(f"Failed to get index data: {e}")
            return []
    
    def sync_index_data(self):
        """同步指数数据到数据库"""
        index_data = self.get_index_data()
        if not index_data:
            logger.warning("No index data retrieved")
            return
        
        sql = """
        INSERT INTO index_data (
            index_code, index_name, secid,
            current_value, change_value, change_percent, total_amount,
            up_count, down_count, flat_count, update_time
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
        ON DUPLICATE KEY UPDATE
            index_name = VALUES(index_name),
            current_value = VALUES(current_value),
            change_value = VALUES(change_value),
            change_percent = VALUES(change_percent),
            total_amount = VALUES(total_amount),
            up_count = VALUES(up_count),
            down_count = VALUES(down_count),
            flat_count = VALUES(flat_count),
            update_time = NOW()
        """
        
        params_list = [
            (d['index_code'], d['index_name'], d['secid'],
             d['current_value'], d['change_value'], d['change_percent'], d['total_amount'],
             d['up_count'], d['down_count'], d['flat_count'])
            for d in index_data
        ]
        
        try:
            affected = db.execute_many(sql, params_list)
            logger.info(f"Index data sync successful, {affected} records")
        except Exception as e:
            logger.error(f"Failed to sync index data to database: {e}")

