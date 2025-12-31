# -*- coding: utf-8 -*-
"""
@Date: 2025/1/XX
@Author: Auto Generated
@Description: 东方财富(eastmoney.com) API 封装
@Reference: https://push2.eastmoney.com/
"""

import requests
import pandas as pd
from typing import Union, List, Dict, Optional
from datetime import datetime
import json
import time
import urllib3

# 禁用SSL警告（因为某些环境下东方财富API的SSL证书可能有问题）
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ==================== 常量定义 ====================

# 标准请求头
EASTMONEY_REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
    'Referer': 'http://www.eastmoney.com/',
    'Accept': 'application/json, text/plain, */*',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate',
    'Connection': 'keep-alive',
}

# 固定参数
EASTMONEY_UT = 'bd1d9ddb04089700cf9c27f6f7426281'  # 固定ut参数

# K线类型映射
KLINE_TYPE = {
    1: '1分钟',
    5: '5分钟',
    15: '15分钟',
    30: '30分钟',
    60: '60分钟',
    101: '日线',
    102: '周线',
    103: '月线',
}

# 复权类型
FQT_TYPE = {
    0: '不复权',
    1: '前复权',
    2: '后复权',
}

# 市场编号映射
MARKET_NUMBER = {
    0: '深交所',
    1: '上交所',
    90: '北交所',
    116: '港股',
    124: '美股',
    155: '英股',
}

# 字段映射（英文字段名，避免乱码）
KLINE_FIELDS = {
    'f51': 'time',
    'f52': 'open',
    'f53': 'close',
    'f54': 'high',
    'f55': 'low',
    'f56': 'volume',
    'f57': 'amount',
    'f58': 'amplitude',
    'f59': 'pct_chg',
    'f60': 'change',
    'f61': 'turnover_rate',
}

QUOTE_FIELDS = {
    'f12': 'code',
    'f13': 'market',
    'f14': 'name',
    'f2': 'price',
    'f3': 'pct_chg',
    'f4': 'change',
    'f5': 'volume',
    'f6': 'amount',
    'f7': 'amplitude',
    'f8': 'high',
    'f9': 'low',
    'f10': 'open',
    'f11': 'pre_close',
    'f15': 'high',
    'f16': 'low',
    'f17': 'open',
    'f18': 'pre_close',
    'f20': 'total_mv',
    'f21': 'circ_mv',
    'f23': 'pb',
    'f24': 'turnover_rate',
    'f25': 'pe',
    'f26': 'volume_ratio',
    'f37': 'pct_chg',
    'f38': 'turnover_rate',
    'f39': 'pe',
    'f40': 'total_mv',
    'f45': 'high',
    'f46': 'low',
    'f47': 'open',
    'f48': 'pre_close',
    'f49': 'volume_ratio',
    'f50': 'turnover_rate',
    'f60': 'pre_close',
    'f92': 'main_net_inflow',
    'f94': 'super_large_net_inflow',
    'f95': 'large_net_inflow',
    'f96': 'medium_net_inflow',
    'f97': 'small_net_inflow',
}

BASE_INFO_FIELDS = {
    'f12': 'code',
    'f14': 'name',
    'f2': 'price',
    'f3': 'pct_chg',
    'f4': 'change',
    'f5': 'volume',
    'f6': 'amount',
    'f7': 'amplitude',
    'f8': 'high',
    'f9': 'low',
    'f10': 'open',
    'f11': 'pre_close',
    'f15': 'high',
    'f16': 'low',
    'f17': 'open',
    'f18': 'pre_close',
    'f20': 'total_mv',
    'f21': 'circ_mv',
    'f23': 'pb',
    'f24': 'turnover_rate',
    'f25': 'pe',
    'f26': 'volume_ratio',
    'f37': 'pct_chg',
    'f38': 'turnover_rate',
    'f39': 'pe',
    'f40': 'total_mv',
    'f45': 'high',
    'f46': 'low',
    'f47': 'open',
    'f48': 'pre_close',
    'f49': 'volume_ratio',
    'f50': 'turnover_rate',
    'f60': 'pre_close',
}

CAPITAL_FLOW_FIELDS = {
    'f51': 'date',
    'f52': 'main_net_inflow',
    'f53': 'super_large_net_inflow',
    'f54': 'large_net_inflow',
    'f55': 'medium_net_inflow',
    'f56': 'small_net_inflow',
    'f57': 'main_net_inflow_pct',
    'f58': 'super_large_net_inflow_pct',
    'f59': 'large_net_inflow_pct',
    'f60': 'medium_net_inflow_pct',
    'f61': 'small_net_inflow_pct',
    'f62': 'main_net_inflow_trend',
    'f63': 'main_net_inflow_trend_pct',
}


# ==================== 工具函数 ====================

def _get_quote_id(code: str, market: Optional[int] = None) -> str:
    """
    获取行情ID（市场编号.代码）
    
    Parameters
    ----------
    code : str
        股票代码：
        - A股：6位数字（如 '000001'）
        - 港股：5位数字（如 '00700'）
        - 美股：字母代码（如 'AAPL'）
    market : int, optional
        市场编号，如果不提供则自动判断：
        - 0: 深交所
        - 1: 上交所
        - 90: 北交所
        - 116: 港股
        - 124: 美股
        - 155: 英股
        
    Returns
    -------
    str
        行情ID，格式：市场编号.代码（如 '0.000001', '116.00700'）
    """
    if market is not None:
        return f"{market}.{code}"
    
    # 自动判断市场
    code_clean = code.strip()
    
    # 港股：5位数字
    if len(code_clean) == 5 and code_clean.isdigit():
        return f"116.{code_clean}"
    
    # A股：6位数字
    if len(code_clean) == 6 and code_clean.isdigit():
        if code_clean.startswith('6'):
            return f"1.{code_clean}"  # 上交所
        elif code_clean.startswith(('0', '3')):
            return f"0.{code_clean}"  # 深交所
        elif code_clean.startswith(('8', '4')):
            return f"90.{code_clean}"  # 北交所
    
    # 美股：通常是字母代码（如 AAPL, TSLA）
    if code_clean.isalpha() or (code_clean.isalnum() and len(code_clean) <= 5):
        # 这里需要更多上下文判断，暂时返回美股格式
        # 实际使用时建议明确指定 market=124
        return f"124.{code_clean}"
    
    # 默认深交所
    return f"0.{code_clean}"


def _make_request(url: str, params: Dict, timeout: int = 10, verify: bool = False) -> Dict:
    """
    发送HTTP请求
    
    Parameters
    ----------
    url : str
        请求URL
    params : dict
        请求参数
    timeout : int
        超时时间（秒）
    verify : bool
        是否验证SSL证书
        
    Returns
    -------
    dict
        JSON响应数据
        
    Raises
    ------
    requests.RequestException
        请求异常
    """
    try:
        response = requests.get(
            url,
            params=params,
            headers=EASTMONEY_REQUEST_HEADERS,
            timeout=timeout,
            verify=verify,
            proxies={'http': None, 'https': None}  # 禁用代理
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        raise Exception(f"请求失败: {url}, 错误: {str(e)}")


# ==================== K线数据相关 ====================

def get_kline_data(
    code: str,
    klt: int = 101,
    fqt: int = 1,
    beg: Optional[str] = None,
    end: Optional[str] = None,
    market: Optional[int] = None,
    fields2: str = "f51,f52,f53,f54,f55,f56,f57",
    timeout: int = 10
) -> pd.DataFrame:
    """
    获取股票/ETF/债券的K线数据
    
    Parameters
    ----------
    code : str
        股票代码：
        - A股：6位数字（如 '000001'）
        - 港股：5位数字（如 '00700'）
    klt : int, default 101
        K线类型：
        - 1: 1分钟
        - 5: 5分钟
        - 15: 15分钟
        - 30: 30分钟
        - 60: 60分钟
        - 101: 日线
        - 102: 周线
        - 103: 月线
    fqt : int, default 1
        复权类型：
        - 0: 不复权
        - 1: 前复权
        - 2: 后复权
    beg : str, optional
        开始日期，格式：YYYYMMDD（如 '20240101'），默认为最早日期
    end : str, optional
        结束日期，格式：YYYYMMDD（如 '20241231'），默认为最新日期
    market : int, optional
        市场编号，如果不提供则自动判断：
        - 0: 深交所
        - 1: 上交所
        - 90: 北交所
        - 116: 港股
    fields2 : str, default "f51,f52,f53,f54,f55,f56,f57"
        返回字段：
        - f51: 时间
        - f52: 开盘
        - f53: 收盘
        - f54: 最高
        - f55: 最低
        - f56: 成交量
        - f57: 成交额
        - f58: 振幅
        - f59: 涨跌幅
        - f60: 涨跌额
        - f61: 换手率
    timeout : int, default 10
        请求超时时间（秒）
        
    Returns
    -------
    pd.DataFrame
        K线数据，包含以下列：
        - code: 代码
        - name: 名称（如果有）
        - time/date: 时间/日期
        - open: 开盘
        - close: 收盘
        - high: 最高
        - low: 最低
        - volume: 成交量
        - amount: 成交额
        - 其他指定字段
        
    Examples
    --------
    >>> # 获取A股：平安银行日线数据
    >>> df = get_kline_data('000001', klt=101, beg='20240101', end='20241231')
    >>> 
    >>> # 获取A股：5分钟K线
    >>> df = get_kline_data('000001', klt=5, beg='20241201', end='20241231')
    >>> 
    >>> # 获取港股：腾讯控股(00700)日线数据（自动识别）
    >>> df = get_kline_data('00700', klt=101, beg='20240101', end='20241231')
    >>> 
    >>> # 获取港股：手动指定市场编号
    >>> df = get_kline_data('00700', market=116, klt=101, beg='20240101', end='20241231')
    """
    quote_id = _get_quote_id(code, market)
    
    if beg is None:
        beg = '19000101'
    if end is None:
        end = datetime.now().strftime('%Y%m%d')
    
    url = 'https://push2his.eastmoney.com/api/qt/stock/kline/get'
    
    params = {
        'secid': quote_id,
        'klt': str(klt),
        'fqt': str(fqt),
        'beg': beg,
        'end': end,
        'fields1': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13',
        'fields2': fields2,
        'rtntype': '6',
    }
    
    json_response = _make_request(url, params, timeout=timeout)
    
    data = json_response.get('data', {})
    if not data:
        return pd.DataFrame()
    
    klines = data.get('klines', [])
    if not klines:
        return pd.DataFrame()
    
    # 解析K线数据（直接使用原始f字段名）
    field_list = fields2.split(',')
    columns = field_list  # 直接使用f字段名，保持原汁原味
    
    rows = []
    for kline in klines:
        values = kline.split(',')
        if len(values) >= len(field_list):
            rows.append(values[:len(field_list)])
    
    df = pd.DataFrame(rows, columns=columns)
    
    # 数据类型转换（使用f字段名）
    if 'f51' in df.columns:  # f51是时间字段
        df['f51'] = pd.to_datetime(df['f51'])
    
    # 数值字段转换（f52-f61）
    numeric_fields = ['f52', 'f53', 'f54', 'f55', 'f56', 'f57', 'f58', 'f59', 'f60', 'f61']
    for col in numeric_fields:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 添加代码和名称
    df.insert(0, 'code', code)
    if 'name' in data:
        df.insert(0, 'name', data['name'])
    
    return df


def get_recent_ndays_kline(
    code: str,
    ndays: int = 1,
    market: Optional[int] = None,
    timeout: int = 10
) -> pd.DataFrame:
    """
    获取股票最近N天的1分钟K线数据
    
    Parameters
    ----------
    code : str
        股票代码：
        - A股：6位数字（如 '000001'）
        - 港股：5位数字（如 '00700'）
    ndays : int, default 1
        天数，最大为5
    market : int, optional
        市场编号，如果不提供则自动判断：
        - 0: 深交所
        - 1: 上交所
        - 90: 北交所
        - 116: 港股
    timeout : int, default 10
        请求超时时间（秒）
        
    Returns
    -------
    pd.DataFrame
        1分钟K线数据
        
    Examples
    --------
    >>> # 获取A股：最近3天的1分钟K线
    >>> df = get_recent_ndays_kline('000001', ndays=3)
    >>> 
    >>> # 获取港股：腾讯控股最近3天的1分钟K线
    >>> df = get_recent_ndays_kline('00700', ndays=3)
    """
    if ndays > 5:
        ndays = 5
    
    quote_id = _get_quote_id(code, market)
    
    url = 'http://push2his.eastmoney.com/api/qt/stock/trends2/get'
    
    fields2 = ','.join(['f51', 'f52', 'f53', 'f54', 'f55', 'f56', 'f57'])
    
    params = {
        'fields1': 'f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13',
        'fields2': fields2,
        'ndays': str(ndays),
        'iscr': '0',
        'iscca': '0',
        'secid': quote_id,
    }
    
    json_response = _make_request(url, params, timeout=timeout)
    
    data = json_response.get('data', {})
    if not data:
        return pd.DataFrame()
    
    trends = data.get('trends', [])
    if not trends:
        return pd.DataFrame()
    
    # 直接使用f字段名（f51-f57对应时间、开盘、收盘、最高、最低、成交量、成交额）
    columns = ['f51', 'f52', 'f53', 'f54', 'f55', 'f56', 'f57']
    rows = [trend.split(',')[:7] for trend in trends]
    
    df = pd.DataFrame(rows, columns=columns)
    df['f51'] = pd.to_datetime(df['f51'])  # f51是时间字段
    
    numeric_cols = ['f52', 'f53', 'f54', 'f55', 'f56', 'f57']
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df.insert(0, 'code', code)
    if 'name' in data:
        df.insert(0, 'name', data['name'])
    
    return df


# ==================== 实时行情相关 ====================

def get_realtime_quotes(
    fs: str = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23",
    pn: int = 1,
    pz: int = 80,
    po: int = 1,
    np: int = 1,
    fields: str = "f12,f13,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f12,f13,f14,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f37,f38,f39,f40,f45,f46,f47,f48,f49,f50,f60",
    timeout: int = 10
) -> pd.DataFrame:
    """
    获取实时行情列表
    
    Parameters
    ----------
    fs : str, default "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
        筛选条件：
        - A股：
          - m:0+t:6: 深交所A股
          - m:0+t:80: 深交所其他
          - m:1+t:2: 上交所A股
          - m:1+t:23: 上交所其他
        - 港股：
          - m:116+t:3: 港股主板
          - m:116+t:4: 港股创业板
        - ETF：
          - b:MK0021: ETF板块
    pn : int, default 1
        页码
    pz : int, default 80
        每页数量
    po : int, default 1
        排序方式
    np : int, default 1
        是否新数据
    fields : str
        返回字段列表，用逗号分隔
    timeout : int, default 10
        请求超时时间（秒）
        
    Returns
    -------
    pd.DataFrame
        实时行情数据
        
    Examples
    --------
    >>> # 获取所有A股股票
    >>> df = get_realtime_quotes(fs="m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23")
    >>> 
    >>> # 获取港股列表
    >>> df = get_realtime_quotes(fs="m:116+t:3,m:116+t:4")
    >>> 
    >>> # 获取ETF列表
    >>> df = get_realtime_quotes(fs="b:MK0021,b:MK0022,b:MK0023,b:MK0024")
    """
    url = 'http://push2.eastmoney.com/api/qt/clist/get'
    
    # 生成时间戳（毫秒）
    timestamp = int(time.time() * 1000)
    
    params = {
        'pn': str(pn),
        'pz': str(pz),
        'po': str(po),
        'np': str(np),
        'ut': EASTMONEY_UT,
        'fltt': '2',
        'invt': '2',
        'fid': 'f3',
        'fs': fs,
        'fields': fields,
        '_': str(timestamp),  # 时间戳参数
    }
    
    json_response = _make_request(url, params, timeout=timeout)
    
    data = json_response.get('data', {})
    if not data:
        return pd.DataFrame()
    
    diff = data.get('diff', [])
    if not diff:
        return pd.DataFrame()
    
    df = pd.DataFrame(diff)
    # 直接使用原始f字段名，不进行转换，保持原汁原味
    
    # 数据类型转换（使用f字段名）
    # 常见的数值字段：f2(最新价), f3(涨跌幅), f4(涨跌额), f5(成交量), f6(成交额)等
    numeric_fields = ['f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 
                     'f15', 'f16', 'f17', 'f18', 'f20', 'f21', 'f23', 'f24', 'f25', 'f26',
                     'f37', 'f38', 'f39', 'f40', 'f45', 'f46', 'f47', 'f48', 'f49', 'f50',
                     'f60', 'f92', 'f94', 'f95', 'f96', 'f97']
    for col in numeric_fields:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 添加行情ID（使用f字段名）
    if 'f13' in df.columns and 'f12' in df.columns:
        df['quote_id'] = df['f13'].astype(str) + '.' + df['f12'].astype(str)
    
    return df


def get_all_a_stocks(
    fields: str = "f12,f13,f14,f26,f38,f39",
    timeout: int = 30
) -> pd.DataFrame:
    """
    获取所有A股股票列表（自动处理分页）
    
    Parameters
    ----------
    fields : str, default "f12,f13,f14,f26,f38,f39"
        返回字段：
        - f12: code
        - f13: market
        - f14: name
        - f26: volume_ratio
        - f38: turnover_rate
        - f39: pe
    timeout : int, default 30
        请求超时时间（秒），已适当延长
        
    Returns
    -------
    pd.DataFrame
        A股股票列表，包含以下列：
        - code: 代码
        - market: 市场编号
        - name: 名称
        - volume_ratio: 量比
        - turnover_rate: 换手率
        - pe: 市盈率
        
    Examples
    --------
    >>> # 获取所有A股股票（自动分页）
    >>> df = get_all_a_stocks()
    >>> print(f"共获取 {len(df)} 只A股")
    """
    fs = "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23"
    all_stocks = []
    pn = 1
    pz = 80
    
    while True:
        df = get_realtime_quotes(fs=fs, pn=pn, pz=pz, fields=fields, timeout=timeout)
        if df.empty:
            break
        all_stocks.append(df)
        # 如果返回的数据少于pz，说明已经是最后一页
        if len(df) < pz:
            break
        pn += 1
        time.sleep(0.1)  # 避免请求过快
    
    if not all_stocks:
        return pd.DataFrame()
    
    result = pd.concat(all_stocks, ignore_index=True)
    # 去重（可能存在重复），使用f字段名
    if 'f12' in result.columns and 'f13' in result.columns:
        result = result.drop_duplicates(subset=['f12', 'f13'], keep='first')
    return result.reset_index(drop=True)


def get_all_hk_stocks(
    fields: str = "f12,f13,f14,f2,f3,f4,f5,f6",
    timeout: int = 30
) -> pd.DataFrame:
    """
    获取所有港股股票列表（自动处理分页）
    
    Parameters
    ----------
    fields : str, default "f12,f13,f14,f2,f3,f4,f5,f6"
        返回字段：
        - f12: code
        - f13: market
        - f14: name
        - f2: price
        - f3: pct_chg
        - f4: change
        - f5: volume
        - f6: amount
    timeout : int, default 30
        请求超时时间（秒），已适当延长
        
    Returns
    -------
    pd.DataFrame
        港股股票列表，包含以下列：
        - code: 代码（5位数字，如 '00700'）
        - market: 市场编号（116）
        - name: 名称
        - price: 最新价
        - pct_chg: 涨跌幅
        - change: 涨跌额
        - volume: 成交量
        - amount: 成交额
        
    Examples
    --------
    >>> # 获取所有港股股票（自动分页）
    >>> df = get_all_hk_stocks()
    >>> print(f"共获取 {len(df)} 只港股")
    >>> 
    >>> # 获取腾讯控股(00700)的行情
    >>> df = get_all_hk_stocks()
    >>> tencent = df[df['code'] == '00700']
    """
    # 港股筛选条件：m:116+t:3（主板）+ m:116+t:4（创业板）
    fs = "m:116+t:3,m:116+t:4"
    all_stocks = []
    pn = 1
    pz = 80
    
    while True:
        df = get_realtime_quotes(fs=fs, pn=pn, pz=pz, fields=fields, timeout=timeout)
        if df.empty:
            break
        all_stocks.append(df)
        # 如果返回的数据少于pz，说明已经是最后一页
        if len(df) < pz:
            break
        pn += 1
        time.sleep(0.1)  # 避免请求过快
    
    if not all_stocks:
        return pd.DataFrame()
    
    result = pd.concat(all_stocks, ignore_index=True)
    # 去重（可能存在重复），使用f字段名
    if 'f12' in result.columns and 'f13' in result.columns:
        result = result.drop_duplicates(subset=['f12', 'f13'], keep='first')
    return result.reset_index(drop=True)


def get_latest_quotes(
    quote_ids: Union[str, List[str]],
    fields: Optional[str] = None,
    timeout: int = 10
) -> pd.DataFrame:
    """
    获取股票、期货、债券的最新行情（批量）
    
    Parameters
    ----------
    quote_ids : str or list of str
        行情ID或行情ID列表，格式：市场编号.代码（如 '0.000001' 或 ['0.000001', '1.600000']）
    fields : str, optional
        返回字段列表，如果不提供则使用默认字段
    timeout : int, default 10
        请求超时时间（秒）
        
    Returns
    -------
    pd.DataFrame
        最新行情数据
        
    Examples
    --------
    >>> # 获取A股：单只股票最新行情
    >>> df = get_latest_quotes('0.000001')
    >>> 
    >>> # 获取A股：批量获取多只股票最新行情
    >>> df = get_latest_quotes(['0.000001', '1.600000', '0.300750'])
    >>> 
    >>> # 获取港股：腾讯控股最新行情
    >>> df = get_latest_quotes('116.00700')
    >>> 
    >>> # 混合获取：A股+港股
    >>> df = get_latest_quotes(['0.000001', '116.00700', '1.600000'])
    """
    if isinstance(quote_ids, str):
        quote_ids = [quote_ids]
    
    if fields is None:
        fields = "f12,f13,f14,f2,f3,f4,f5,f6,f7,f8,f9,f10,f11,f15,f16,f17,f18,f20,f21,f23,f24,f25,f26,f37,f38,f39,f40,f45,f46,f47,f48,f49,f50,f60"
    
    url = 'https://push2.eastmoney.com/api/qt/ulist.np/get'
    
    params = {
        'OSVersion': '14.3',
        'appVersion': '6.3.8',
        'fields': fields,
        'fltt': '2',
        'plat': 'Iphone',
        'product': 'EFund',
        'secids': ','.join(quote_ids),
        'serverVersion': '6.3.6',
        'version': '6.3.8',
    }
    
    json_response = _make_request(url, params, timeout=timeout)
    
    data = json_response.get('data', {})
    if not data:
        return pd.DataFrame()
    
    diff = data.get('diff', [])
    if not diff:
        return pd.DataFrame()
    
    df = pd.DataFrame(diff)
    # 直接使用原始f字段名，不进行转换，保持原汁原味
    
    # 数据类型转换（使用f字段名）
    # 常见的数值字段：f2(最新价), f3(涨跌幅), f4(涨跌额), f5(成交量), f6(成交额)等
    numeric_fields = ['f2', 'f3', 'f4', 'f5', 'f6', 'f7', 'f8', 'f9', 'f10', 'f11', 
                     'f15', 'f16', 'f17', 'f18', 'f20', 'f21', 'f23', 'f24', 'f25', 'f26',
                     'f37', 'f38', 'f39', 'f40', 'f45', 'f46', 'f47', 'f48', 'f49', 'f50',
                     'f60', 'f92', 'f94', 'f95', 'f96', 'f97']
    for col in numeric_fields:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 添加行情ID（使用f字段名）
    if 'f13' in df.columns and 'f12' in df.columns:
        df['quote_id'] = df['f13'].astype(str) + '.' + df['f12'].astype(str)
    
    return df


def get_etf_list(
    pn: int = 1,
    pz: int = 500,
    timeout: int = 10
) -> pd.DataFrame:
    """
    获取所有场内ETF列表
    
    Parameters
    ----------
    pn : int, default 1
        页码
    pz : int, default 500
        每页数量
    timeout : int, default 10
        请求超时时间（秒）
        
    Returns
    -------
    pd.DataFrame
        ETF列表，包含以下列：
        - code: 代码
        - name: 名称
        - price: 最新价
        - market: 市场编号
        
    Examples
    --------
    >>> # 获取ETF列表
    >>> df = get_etf_list()
    """
    url = 'http://68.push2.eastmoney.com/api/qt/clist/get'
    
    # 生成时间戳（毫秒）
    timestamp = int(time.time() * 1000)
    
    params = {
        'cb': 'jQuery1124047482019788167995_1690884441114',
        'pn': str(pn),
        'pz': str(pz),
        'po': '1',
        'np': '1',
        'ut': EASTMONEY_UT,
        'fltt': '2',
        'invt': '2',
        'wbp2u': '|0|0|0|web',
        'fid': 'f3',
        'fs': 'b:MK0021,b:MK0022,b:MK0023,b:MK0024',
        'fields': 'f12,f14,f2,f13',
        '_': str(timestamp),  # 时间戳参数
    }
    
    try:
        response = requests.get(
            url, 
            params=params, 
            headers=EASTMONEY_REQUEST_HEADERS, 
            timeout=timeout,
            proxies={'http': None, 'https': None}  # 禁用代理
        )
        text = response.text
        
        # 处理JSONP响应
        if text.startswith('jQuery'):
            start_idx = text.index('{')
            end_idx = text.rindex('}') + 1
            text = text[start_idx:end_idx]
        
        json_response = json.loads(text)
    except Exception as e:
        raise Exception(f"请求失败: {url}, 错误: {str(e)}")
    
    data = json_response.get('data', {})
    if not data:
        return pd.DataFrame()
    
    diff = data.get('diff', [])
    if not diff:
        return pd.DataFrame()
    
    df = pd.DataFrame(diff)
    # 直接使用原始f字段名，不进行转换，保持原汁原味
    
    # 数据类型转换（使用f字段名）
    if 'f2' in df.columns:
        df['f2'] = pd.to_numeric(df['f2'], errors='coerce')
    
    return df


# ==================== 资金流向相关 ====================

def get_history_capital_flow(
    code: str,
    lmt: int = 100000,
    market: Optional[int] = None,
    timeout: int = 10
) -> pd.DataFrame:
    """
    获取单支股票、债券的历史资金流向数据（日线）
    
    Parameters
    ----------
    code : str
        股票代码：
        - A股：6位数字（如 '000001'）
        - 港股：5位数字（如 '00700'）
    lmt : int, default 100000
        限制条数
    market : int, optional
        市场编号，如果不提供则自动判断：
        - 0: 深交所
        - 1: 上交所
        - 90: 北交所
        - 116: 港股
    timeout : int, default 10
        请求超时时间（秒）
        
    Returns
    -------
    pd.DataFrame
        历史资金流向数据，包含以下列：
        - code: 代码
        - name: 名称（如果有）
        - date: 日期
        - main_net_inflow: 主力净流入
        - super_large_net_inflow: 超大单净流入
        - large_net_inflow: 大单净流入
        - medium_net_inflow: 中单净流入
        - small_net_inflow: 小单净流入
        - main_net_inflow_pct: 主力净流入占比
        - 其他占比字段
        
    Examples
    --------
    >>> # 获取A股：平安银行历史资金流向
    >>> df = get_history_capital_flow('000001')
    >>> 
    >>> # 获取港股：腾讯控股历史资金流向
    >>> df = get_history_capital_flow('00700', market=116)
    """
    quote_id = _get_quote_id(code, market)
    
    url = 'http://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get'
    
    fields2 = ','.join(['f51', 'f52', 'f53', 'f54', 'f55', 'f56', 'f57', 'f58', 'f59', 'f60', 'f61', 'f62', 'f63'])
    
    params = {
        'lmt': str(lmt),
        'klt': '101',
        'secid': quote_id,
        'fields1': 'f1,f2,f3,f7',
        'fields2': fields2,
    }
    
    json_response = _make_request(url, params, timeout=timeout)
    
    klines = json_response.get('data', {}).get('klines', [])
    if not klines:
        return pd.DataFrame()
    
    # 直接使用f字段名（f51-f63对应日期、主力净流入等）
    columns = ['f51', 'f52', 'f53', 'f54', 'f55', 'f56', 'f57', 'f58', 'f59', 'f60', 
               'f61', 'f62', 'f63']
    
    rows = [kline.split(',')[:13] for kline in klines]
    df = pd.DataFrame(rows, columns=columns)
    
    # 数据类型转换（使用f字段名）
    df['f51'] = pd.to_datetime(df['f51'])  # f51是日期字段
    numeric_cols = ['f52', 'f53', 'f54', 'f55', 'f56', 'f57', 'f58', 'f59', 'f60', 'f61', 'f62', 'f63']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # 添加代码和名称
    data = json_response.get('data', {})
    df.insert(0, 'code', code)
    if 'name' in data:
        df.insert(0, 'name', data['name'])
    
    return df


def get_today_capital_flow(
    code: str,
    market: Optional[int] = None,
    timeout: int = 10
) -> pd.DataFrame:
    """
    获取单只股票最新交易日的日内分钟级资金流向数据
    
    Parameters
    ----------
    code : str
        股票代码（6位数字）
    market : int, optional
        市场编号，如果不提供则自动判断
    timeout : int, default 10
        请求超时时间（秒）
        
    Returns
    -------
    pd.DataFrame
        今日资金流向数据（分钟级），包含以下列：
        - code: 代码
        - name: 名称（如果有）
        - time: 时间
        - main_net_inflow: 主力净流入
        - small_net_inflow: 小单净流入
        - medium_net_inflow: 中单净流入
        - large_net_inflow: 大单净流入
        - super_large_net_inflow: 超大单净流入
        
    Examples
    --------
    >>> # 获取A股：平安银行今日资金流向
    >>> df = get_today_capital_flow('000001')
    >>> 
    >>> # 获取港股：腾讯控股今日资金流向
    >>> df = get_today_capital_flow('00700', market=116)
    """
    quote_id = _get_quote_id(code, market)
    
    url = 'http://push2.eastmoney.com/api/qt/stock/fflow/kline/get'
    
    params = {
        'lmt': '0',
        'klt': '1',
        'secid': quote_id,
        'fields1': 'f1,f2,f3,f7',
        'fields2': 'f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61,f62,f63',
    }
    
    json_response = _make_request(url, params, timeout=timeout)
    
    data = json_response.get('data', {})
    if not data:
        return pd.DataFrame()
    
    klines = data.get('klines', [])
    if not klines:
        return pd.DataFrame()
    
    # 直接使用f字段名（f51-f56对应时间、主力净流入等）
    columns = ['f51', 'f52', 'f53', 'f54', 'f55', 'f56']
    rows = [kline.split(',')[:6] for kline in klines]
    
    df = pd.DataFrame(rows, columns=columns)
    df['f51'] = pd.to_datetime(df['f51'])  # f51是时间字段
    
    numeric_cols = ['f52', 'f53', 'f54', 'f55', 'f56']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df.insert(0, 'code', code)
    if 'name' in data:
        df.insert(0, 'name', data['name'])
    
    return df


# ==================== 股票基本信息 ====================

def get_stock_base_info(
    code: str,
    market: Optional[int] = None,
    timeout: int = 10
) -> pd.Series:
    """
    获取股票、期货、债券的基本信息
    
    Parameters
    ----------
    code : str
        股票代码：
        - A股：6位数字（如 '000001'）
        - 港股：5位数字（如 '00700'）
    market : int, optional
        市场编号，如果不提供则自动判断：
        - 0: 深交所
        - 1: 上交所
        - 90: 北交所
        - 116: 港股
    timeout : int, default 10
        请求超时时间（秒）
        
    Returns
    -------
    pd.Series
        股票基本信息，包含以下字段：
        - code: 代码
        - name: 名称
        - price: 最新价
        - pct_chg: 涨跌幅
        - change: 涨跌额
        - volume: 成交量
        - amount: 成交额
        - amplitude: 振幅
        - high: 最高
        - low: 最低
        - open: 今开
        - pre_close: 昨收
        - total_mv: 总市值
        - circ_mv: 流通市值
        - pb: 市净率
        - turnover_rate: 换手率
        - pe: 市盈率
        - volume_ratio: 量比
        
    Examples
    --------
    >>> # 获取A股：平安银行基本信息
    >>> info = get_stock_base_info('000001')
    >>> print(info['name'], info['price'])
    >>> 
    >>> # 获取港股：腾讯控股基本信息（自动识别）
    >>> info = get_stock_base_info('00700')
    >>> print(info['name'], info['price'])
    """
    quote_id = _get_quote_id(code, market)
    
    url = 'http://push2.eastmoney.com/api/qt/stock/get'
    
    fields = ','.join(BASE_INFO_FIELDS.keys())
    
    params = {
        'ut': 'fa5fd1943c7b386f172d6893dbfba10b',
        'invt': '2',
        'fltt': '2',
        'fields': fields,
        'secid': quote_id,
    }
    
    json_response = _make_request(url, params, timeout=timeout)
    
    data = json_response.get('data', {})
    if not data:
        return pd.Series(dtype='object')
    
    # 直接使用原始f字段名，不进行转换，保持原汁原味
    s = pd.Series(data, dtype='object')
    return s


def get_deal_details(
    code: str,
    max_count: int = 1000000,
    market: Optional[int] = None,
    timeout: int = 10
) -> pd.DataFrame:
    """
    获取股票、期货、债券的最新交易日成交明细
    
    Parameters
    ----------
    code : str
        股票代码：
        - A股：6位数字（如 '000001'）
        - 港股：5位数字（如 '00700'）
    max_count : int, default 1000000
        最大数据条数
    market : int, optional
        市场编号，如果不提供则自动判断：
        - 0: 深交所
        - 1: 上交所
        - 90: 北交所
        - 116: 港股
    timeout : int, default 10
        请求超时时间（秒）
        
    Returns
    -------
    pd.DataFrame
        成交明细，包含以下列：
        - name: 名称
        - code: 代码
        - time: 时间
        - pre_close: 昨收
        - price: 成交价
        - volume: 成交量
        - count: 单数
        
    Examples
    --------
    >>> # 获取A股：平安银行成交明细
    >>> df = get_deal_details('000001', max_count=1000)
    >>> 
    >>> # 获取港股：腾讯控股成交明细
    >>> df = get_deal_details('00700', market=116, max_count=1000)
    """
    quote_id = _get_quote_id(code, market)
    
    # 先获取基本信息
    base_info = get_stock_base_info(code, market, timeout=timeout)
    if base_info.empty or pd.isna(base_info.get('f12', None)):
        return pd.DataFrame(columns=['name', 'code', 'f51', 'prePrice', 'f52', 'f53', 'f54'])
    
    code_value = base_info.get('f12', code)  # f12是代码
    name_value = base_info.get('f14', '')  # f14是名称
    
    url = 'https://push2.eastmoney.com/api/qt/stock/details/get'
    
    params = {
        'secid': quote_id,
        'fields1': 'f1,f2,f3,f4,f5',
        'fields2': 'f51,f52,f53,f54,f55',
        'pos': f'-{int(max_count)}',
    }
    
    json_response = _make_request(url, params, timeout=timeout)
    
    data = json_response.get('data', {})
    if not data:
        return pd.DataFrame(columns=['name', 'code', 'f51', 'prePrice', 'f52', 'f53', 'f54'])
    
    details = data.get('details', [])
    if not details:
        return pd.DataFrame(columns=['name', 'code', 'f51', 'prePrice', 'f52', 'f53', 'f54'])
    
    pre_price = data.get('prePrice', 0)
    
    # 直接使用f字段名（f51-f54对应时间、成交价、成交量、单数）
    columns = ['f51', 'f52', 'f53', 'f54']
    rows = [detail.split(',')[:4] for detail in details]
    
    df = pd.DataFrame(rows, columns=columns)
    df['prePrice'] = pre_price  # 昨收价格
    df['f51'] = pd.to_datetime(df['f51'])  # f51是时间字段
    
    numeric_cols = ['f52', 'f53', 'f54', 'prePrice']
    for col in numeric_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    df.insert(0, 'code', code_value)
    df.insert(0, 'name', name_value)
    
    return df


# ==================== 核心题材数据 ====================

def get_core_concept(
    code: str,
    market: Optional[int] = None,
    timeout: int = 10
) -> Dict:
    """
    获取个股核心题材数据
    
    Parameters
    ----------
    code : str
        股票代码：
        - A股：6位数字（如 '000001'）
        - 港股：5位数字（如 '00700'）
    market : int, optional
        市场编号，如果不提供则自动判断：
        - 0: 深交所
        - 1: 上交所
        - 90: 北交所
        - 116: 港股
    timeout : int, default 10
        请求超时时间（秒）
        
    Returns
    -------
    dict
        核心题材数据
        
    Examples
    --------
    >>> # 获取A股：平安银行核心题材
    >>> concept = get_core_concept('000001')
    >>> 
    >>> # 获取港股：腾讯控股核心题材
    >>> concept = get_core_concept('00700', market=116)
    """
    quote_id = _get_quote_id(code, market)
    
    # 转换为东方财富格式
    if quote_id.startswith('0.'):
        em_code = f"SZ.{code}"  # 深交所
    elif quote_id.startswith('1.'):
        em_code = f"SH.{code}"  # 上交所
    elif quote_id.startswith('116.'):
        em_code = f"HK.{code}"  # 港股
    else:
        em_code = code
    
    url = 'http://emweb.securities.eastmoney.com/PC_HSF10/CoreConception/PageAjax'
    
    params = {
        'code': em_code,
    }
    
    json_response = _make_request(url, params, timeout=timeout)
    
    return json_response




