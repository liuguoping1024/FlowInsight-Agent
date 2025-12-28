"""
数据采集服务
从东方财富API采集股票数据
"""
import requests
import logging
from datetime import datetime
from typing import List, Dict
from database.db_connection import db
from config import EASTMONEY_API_BASE, EASTMONEY_HISTORY_API_BASE, INDICES_MAP

logger = logging.getLogger(__name__)


class DataCollector:
    """数据采集器"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://www.eastmoney.com/'
        })
    
    def get_stock_list(self, page_size: int = 8000, delay: float = 1.0) -> List[Dict]:
        """
        获取A股个股列表（分页获取所有数据）
        API: https://push2.eastmoney.com/api/qt/clist/get?pz=8000&pn=1&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f12,f13,f14,f26,f38,f39
        
        Args:
            page_size: 每页数量，默认8000
            delay: 每次请求后的延迟时间（秒），默认1秒
        """
        import time
        all_stocks = []
        page = 1
        
        try:
            while True:
                url = f"{EASTMONEY_API_BASE}/qt/clist/get"
                params = {
                    'pz': page_size,
                    'pn': page,
                    'fs': 'm:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23',
                    'fields': 'f12,f13,f14,f26,f38,f39'
                }
                
                logger.info(f"正在获取第 {page} 页股票数据...")
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                # 调试：打印响应结构
                if page == 1:
                    logger.info(f"API响应结构: rc={data.get('rc')}, data类型={type(data.get('data'))}")
                
                if data.get('rc') == 0 and 'data' in data:
                    data_obj = data['data']
                    # 处理data可能是字符串的情况
                    if isinstance(data_obj, str):
                        import json
                        try:
                            data_obj = json.loads(data_obj)
                        except Exception as parse_err:
                            logger.warning(f"第 {page} 页数据解析失败: {parse_err}, 跳过")
                            break
                    
                    if not isinstance(data_obj, dict):
                        logger.error(f"第 {page} 页data不是字典类型: {type(data_obj)}")
                        break
                    
                    page_stocks = []
                    diff_data = data_obj.get('diff', [])
                    
                    # diff可能是列表或字典，需要处理两种情况
                    if isinstance(diff_data, dict):
                        # 如果是字典，可能是按索引组织的，需要获取所有值
                        diff_list = list(diff_data.values()) if diff_data else []
                    elif isinstance(diff_data, list):
                        diff_list = diff_data
                    else:
                        logger.error(f"第 {page} 页diff格式不正确: {type(diff_data)}")
                        break
                    
                    for item in diff_list:
                        if not isinstance(item, dict):
                            continue
                        stock_code = item.get('f12', '')
                        market_code = item.get('f13', 1)  # 0=深市，1=沪市
                        stock_name = item.get('f14', '')
                        total_market_cap = item.get('f26', 0)  # 总市值
                        circulating_market_cap = item.get('f38', 0)  # 流通市值
                        
                        secid = f"{market_code}.{stock_code}"
                        page_stocks.append({
                            'stock_code': stock_code,
                            'market_code': market_code,
                            'stock_name': stock_name,
                            'secid': secid,
                            'total_market_cap': total_market_cap,
                            'circulating_market_cap': circulating_market_cap
                        })
                    
                    if not page_stocks:
                        # 没有更多数据了
                        break
                    
                    all_stocks.extend(page_stocks)
                    logger.info(f"第 {page} 页获取成功，本页 {len(page_stocks)} 条，累计 {len(all_stocks)} 条")
                    
                    # 检查是否还有更多数据
                    total = data_obj.get('total', 0) if isinstance(data_obj, dict) else 0
                    if total > 0:
                        logger.info(f"API返回总数: {total}, 已获取: {len(all_stocks)}")
                        if len(all_stocks) >= total:
                            # 已获取全部数据
                            logger.info(f"已获取全部 {total} 条数据")
                            break
                    
                    # 如果本页没有数据，说明已经是最后一页
                    if len(page_stocks) == 0:
                        logger.info("本页无数据，已获取全部数据")
                        break
                    
                    # 等待指定时间后再请求下一页
                    if delay > 0:
                        logger.info(f"等待 {delay} 秒后获取下一页...")
                        time.sleep(delay)
                    
                    page += 1
                else:
                    logger.warning(f"第 {page} 页获取失败，响应: {data}")
                    break
            
            logger.info(f"股票列表获取完成，共 {len(all_stocks)} 条")
            return all_stocks
            
        except Exception as e:
            logger.error(f"获取个股列表失败: {e}")
            return all_stocks  # 返回已获取的数据
    
    def sync_stock_list(self, delay: float = 1.0):
        """同步个股列表到数据库
        
        Args:
            delay: 每次请求后的延迟时间（秒），默认1秒
        """
        stocks = self.get_stock_list(delay=delay)
        if not stocks:
            logger.warning("未获取到个股数据")
            return
        
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
            logger.info(f"同步个股列表成功，共 {affected} 条记录")
        except Exception as e:
            logger.error(f"同步个股列表到数据库失败: {e}")
    
    def get_realtime_capital_flow(self, limit: int = 20) -> List[Dict]:
        """
        获取实时资金流向（前N名）
        API: https://push2.eastmoney.com/api/qt/clist/get?fid=f62&po=1&pz=50&pn=1&np=1&fltt=2&invt=2&ut=8dec03ba335b81bf4ebdf7b29ec27d15&fs=m:0+t:6+f:!2,m:0+t:13+f:!2,m:0+t:80+f:!2,m:1+t:2+f:!2,m:1+t:23+f:!2,m:0+t:7+f:!2,m:1+t:3+f:!2&fields=f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13
        """
        try:
            url = f"{EASTMONEY_API_BASE}/qt/clist/get"
            params = {
                'fid': 'f62',  # 按主力净流入排序
                'po': 1,
                'pz': limit,
                'pn': 1,
                'np': 1,
                'fltt': 2,
                'invt': 2,
                'ut': '8dec03ba335b81bf4ebdf7b29ec27d15',
                'fs': 'm:0+t:6+f:!2,m:0+t:13+f:!2,m:0+t:80+f:!2,m:1+t:2+f:!2,m:1+t:23+f:!2,m:0+t:7+f:!2,m:1+t:3+f:!2',
                'fields': 'f12,f14,f2,f3,f62,f184,f66,f69,f72,f75,f78,f81,f84,f87,f204,f205,f124,f1,f13'
            }
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('rc') == 0 and 'data' in data:
                results = []
                for item in data['data'].get('diff', []):
                    stock_code = item.get('f12', '')
                    market_code = item.get('f13', 1)
                    stock_name = item.get('f14', '')
                    current_price = item.get('f2', 0)
                    change_percent = item.get('f3', 0)
                    main_net_inflow = item.get('f62', 0)  # 主力净流入
                    super_large_net_inflow = item.get('f66', 0)  # 超大单净流入
                    large_net_inflow = item.get('f69', 0)  # 大单净流入
                    medium_net_inflow = item.get('f72', 0)  # 中单净流入
                    small_net_inflow = item.get('f75', 0)  # 小单净流入
                    
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
            return []
        except Exception as e:
            logger.error(f"获取实时资金流向失败: {e}")
            return []
    
    def get_stock_capital_flow_history(self, secid: str, limit: int = 250) -> List[Dict]:
        """
        获取个股历史资金数据
        API: https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get?lmt=0&klt=101&fields1=f1,f2,f3,f7&fields2=f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65&secid=0.300274
        """
        try:
            url = f"{EASTMONEY_HISTORY_API_BASE}/qt/stock/fflow/daykline/get"
            params = {
                'lmt': limit,
                'klt': 101,  # 日K线
                'fields1': 'f1,f2,f3,f7',
                'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63,f64,f65',
                'secid': secid
            }
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('rc') == 0 and 'data' in data:
                klines = data['data'].get('klines', [])
                results = []
                
                # 解析secid
                market_code, stock_code = secid.split('.')
                
                for kline_str in klines:
                    parts = kline_str.split(',')
                    if len(parts) < 15:
                        continue
                    
                    try:
                        # 根据字段映射表解析数据（共15个字段，索引0-14）
                        # 索引0: 日期
                        trade_date = datetime.strptime(parts[0], '%Y-%m-%d').date()
                        
                        # 索引1 (f51): 主力净流入（大单+超大单）
                        main_net_inflow = float(parts[1]) if len(parts) > 1 and parts[1] else 0  # f51
                        
                        # 索引2 (f52): 小单净流入
                        small_net_inflow = float(parts[2]) if len(parts) > 2 and parts[2] else 0  # f52
                        
                        # 索引3 (f53): 中单净流入
                        medium_net_inflow = float(parts[3]) if len(parts) > 3 and parts[3] else 0  # f53
                        
                        # 索引4 (f54): 大单净流入
                        large_net_inflow = float(parts[4]) if len(parts) > 4 and parts[4] else 0  # f54
                        
                        # 索引5 (f55): 超大单净流入
                        super_large_net_inflow = float(parts[5]) if len(parts) > 5 and parts[5] else 0  # f55
                        
                        # 索引6 (f56): 主力净流入占比
                        main_net_inflow_ratio = float(parts[6]) if len(parts) > 6 and parts[6] else 0  # f56
                        
                        # 索引11 (f61): 收盘价
                        close_price = float(parts[11]) if len(parts) > 11 and parts[11] else 0  # f61
                        
                        # 索引12 (f62): 涨跌幅
                        change_percent = float(parts[12]) if len(parts) > 12 and parts[12] else 0  # f62
                        
                        # 注意：索引13和14是保留字段（f63, f64），值为0.00
                        # 成交额和换手率可能不在这个API返回的数据中，设为NULL
                        turnover_amount = None  # 成交额（API未提供）
                        turnover_rate = None   # 换手率（API未提供）
                        
                        # 将CSV字符串转换为JSON字符串格式存储
                        import json
                        raw_data_json = json.dumps(kline_str, ensure_ascii=False)
                        
                        results.append({
                            'stock_code': stock_code,
                            'market_code': int(market_code),
                            'secid': secid,
                            'trade_date': trade_date,
                            'main_net_inflow': main_net_inflow,  # f51: 主力净流入
                            'super_large_net_inflow': super_large_net_inflow,  # f55: 超大单净流入
                            'large_net_inflow': large_net_inflow,  # f54: 大单净流入
                            'medium_net_inflow': medium_net_inflow,  # f53: 中单净流入
                            'small_net_inflow': small_net_inflow,  # f52: 小单净流入
                            'main_net_inflow_ratio': main_net_inflow_ratio,  # f56: 主力净流入占比
                            'close_price': close_price,  # f61: 收盘价
                            'change_percent': change_percent,  # f62: 涨跌幅
                            'turnover_rate': turnover_rate,  # 换手率（待确认字段）
                            'turnover_amount': turnover_amount,  # 成交额（待确认字段）
                            'raw_data': raw_data_json
                        })
                    except (ValueError, IndexError) as e:
                        logger.warning(f"解析历史数据失败: {e}, 数据: {kline_str}")
                        continue
                
                return results
            return []
        except Exception as e:
            logger.error(f"获取个股历史资金数据失败: {e}, secid: {secid}")
            return []
    
    def sync_stock_capital_flow_history(self, secid: str, limit: int = 250):
        """同步个股历史资金数据到数据库"""
        history_data = self.get_stock_capital_flow_history(secid, limit)
        if not history_data:
            logger.warning(f"未获取到历史数据: {secid}")
            return
        
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
            logger.info(f"同步历史资金数据成功，secid: {secid}, 共 {affected} 条记录")
        except Exception as e:
            logger.error(f"同步历史资金数据到数据库失败: {e}, secid: {secid}")
    
    def get_index_data(self) -> List[Dict]:
        """
        获取指数数据
        API: https://push2.eastmoney.com/api/qt/ulist.np/get?fltt=2&secids=1.000001,0.399001&fields=f1,f2,f3,f4,f6,f12,f13,f104,f105,f106
        """
        try:
            secids = ','.join(INDICES_MAP.keys())
            url = f"{EASTMONEY_API_BASE}/qt/ulist.np/get"
            params = {
                'fltt': 2,
                'secids': secids,
                'fields': 'f1,f2,f3,f4,f6,f12,f13,f104,f105,f106'
            }
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data.get('rc') == 0 and 'data' in data:
                results = []
                for item in data['data'].get('diff', []):
                    index_code = item.get('f12', '')
                    market_code = item.get('f13', 1)
                    current_value = item.get('f2', 0)
                    change_value = item.get('f4', 0)
                    change_percent = item.get('f3', 0)
                    total_amount = item.get('f6', 0)
                    up_count = item.get('f104', 0)
                    down_count = item.get('f105', 0)
                    flat_count = item.get('f106', 0)
                    
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
            return []
        except Exception as e:
            logger.error(f"获取指数数据失败: {e}")
            return []
    
    def sync_index_data(self):
        """同步指数数据到数据库"""
        index_data = self.get_index_data()
        if not index_data:
            logger.warning("未获取到指数数据")
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
            logger.info(f"同步指数数据成功，共 {affected} 条记录")
        except Exception as e:
            logger.error(f"同步指数数据到数据库失败: {e}")

