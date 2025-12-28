"""
检查推荐股票计算所需的数据情况
"""
import sys
import io
from datetime import date, timedelta
from database.db_connection import db

# 设置标准输出编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("检查推荐股票计算所需的数据")
print("=" * 60)

try:
    # 1. 检查总数据量
    print("\n1. 检查历史数据总量:")
    sql_total = "SELECT COUNT(*) as total FROM stock_capital_flow_history"
    total_result = db.execute_query(sql_total)
    total_records = total_result[0]['total'] if total_result else 0
    print(f"   历史数据总记录数: {total_records:,} 条")
    
    # 2. 检查有多少只股票有历史数据
    sql_stocks = "SELECT COUNT(DISTINCT secid) as stock_count FROM stock_capital_flow_history"
    stocks_result = db.execute_query(sql_stocks)
    stock_count = stocks_result[0]['stock_count'] if stocks_result else 0
    print(f"   有历史数据的股票数: {stock_count} 只")
    
    # 3. 检查日期范围
    print("\n2. 检查数据日期范围:")
    sql_date_range = """
    SELECT 
        MIN(trade_date) as min_date,
        MAX(trade_date) as max_date
    FROM stock_capital_flow_history
    """
    date_result = db.execute_query(sql_date_range)
    if date_result and date_result[0]['min_date']:
        min_date = date_result[0]['min_date']
        max_date = date_result[0]['max_date']
        print(f"   最早日期: {min_date}")
        print(f"   最新日期: {max_date}")
        print(f"   今天日期: {date.today()}")
        
        # 计算距离今天的天数
        if isinstance(max_date, date):
            days_diff = (date.today() - max_date).days
            print(f"   最新数据距离今天: {days_diff} 天")
    
    # 4. 检查最近10天的数据
    print("\n3. 检查最近10天的数据:")
    today = date.today()
    ten_days_ago = today - timedelta(days=10)
    
    sql_recent = """
    SELECT COUNT(DISTINCT secid) as stock_count,
           COUNT(*) as record_count
    FROM stock_capital_flow_history
    WHERE trade_date >= %s AND trade_date <= %s
    """
    recent_result = db.execute_query(sql_recent, (ten_days_ago, today))
    if recent_result:
        recent_stocks = recent_result[0]['stock_count']
        recent_records = recent_result[0]['record_count']
        print(f"   最近10天有数据的股票数: {recent_stocks} 只")
        print(f"   最近10天的记录数: {recent_records:,} 条")
    
    # 5. 检查推荐计算查询的实际结果
    print("\n4. 检查推荐计算查询:")
    sql_recommend = """
    SELECT DISTINCT sl.secid, sl.stock_code, sl.stock_name, sl.market_code
    FROM stock_list sl
    INNER JOIN stock_capital_flow_history h ON sl.secid = h.secid
    WHERE sl.is_active = 1
    AND h.trade_date >= DATE_SUB(%s, INTERVAL %s DAY)
    GROUP BY sl.secid, sl.stock_code, sl.stock_name, sl.market_code
    HAVING COUNT(DISTINCT h.trade_date) >= %s
    """
    recommend_result = db.execute_query(sql_recommend, (today, 10, 10))
    print(f"   符合推荐计算条件的股票数: {len(recommend_result)} 只")
    
    if len(recommend_result) > 0:
        print(f"\n   前5只股票示例:")
        for i, stock in enumerate(recommend_result[:5], 1):
            print(f"     {i}. {stock['stock_name']} ({stock['stock_code']})")
    
    # 6. 如果数据是旧的，检查使用旧日期的情况
    if date_result and date_result[0]['max_date']:
        max_date = date_result[0]['max_date']
        if isinstance(max_date, date) and max_date < today:
            print(f"\n5. 数据日期较旧，尝试使用最新数据日期计算:")
            # 使用最新数据日期作为推荐日期
            sql_recommend_old = """
            SELECT DISTINCT sl.secid, sl.stock_code, sl.stock_name, sl.market_code
            FROM stock_list sl
            INNER JOIN stock_capital_flow_history h ON sl.secid = h.secid
            WHERE sl.is_active = 1
            AND h.trade_date >= DATE_SUB(%s, INTERVAL %s DAY)
            GROUP BY sl.secid, sl.stock_code, sl.stock_name, sl.market_code
            HAVING COUNT(DISTINCT h.trade_date) >= %s
            """
            recommend_old_result = db.execute_query(sql_recommend_old, (max_date, 10, 10))
            print(f"   使用最新数据日期 ({max_date}) 符合条件的股票数: {len(recommend_old_result)} 只")
    
    # 7. 检查一些样本数据
    print("\n6. 检查样本数据（前5只股票最近10天的数据）:")
    sql_sample = """
    SELECT secid, stock_code, stock_name
    FROM stock_list
    WHERE is_active = 1
    LIMIT 5
    """
    sample_stocks = db.execute_query(sql_sample)
    
    for stock in sample_stocks:
        secid = stock['secid']
        sql_history = """
        SELECT COUNT(*) as count,
               MIN(trade_date) as min_date,
               MAX(trade_date) as max_date,
               SUM(main_net_inflow) as total_main_inflow
        FROM stock_capital_flow_history
        WHERE secid = %s
        AND trade_date >= DATE_SUB(%s, INTERVAL 10 DAY)
        """
        history_info = db.execute_query(sql_history, (secid, today))
        if history_info and history_info[0]['count']:
            info = history_info[0]
            print(f"   {stock['stock_name']} ({stock['stock_code']}):")
            print(f"     记录数: {info['count']}, 日期范围: {info['min_date']} ~ {info['max_date']}")
            print(f"     10日主力流入: {float(info['total_main_inflow'] or 0):,.0f} 元")
    
    print("\n" + "=" * 60)
    print("检查完成")
    print("=" * 60)
    
except Exception as e:
    print(f"\n[错误] 检查失败: {e}")
    import traceback
    traceback.print_exc()

