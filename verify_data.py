"""
验证数据库中的历史数据是否正确
"""
import sys
import io
from database.db_connection import db

# 设置标准输出编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("验证数据库中的历史数据")
print("=" * 60)

# 查询平安银行（000001）的最新几条数据
sql = """
SELECT trade_date, main_net_inflow, super_large_net_inflow, large_net_inflow,
       medium_net_inflow, small_net_inflow, main_net_inflow_ratio,
       close_price, change_percent, turnover_rate, turnover_amount
FROM stock_capital_flow_history
WHERE secid = '0.000001'
ORDER BY trade_date DESC
LIMIT 5
"""

try:
    results = db.execute_query(sql)
    print(f"\n平安银行（000001）最新5条数据：")
    print("-" * 60)
    for i, row in enumerate(results, 1):
        print(f"\n第{i}条:")
        print(f"  日期: {row['trade_date']}")
        print(f"  主力净流入(f51): {row['main_net_inflow']:,.2f}")
        print(f"  超大单净流入(f55): {row['super_large_net_inflow']:,.2f}")
        print(f"  大单净流入(f54): {row['large_net_inflow']:,.2f}")
        print(f"  中单净流入(f53): {row['medium_net_inflow']:,.2f}")
        print(f"  小单净流入(f52): {row['small_net_inflow']:,.2f}")
        print(f"  主力净流入占比(f56): {row['main_net_inflow_ratio']}%")
        print(f"  收盘价(f61): {row['close_price']}")
        print(f"  涨跌幅(f62): {row['change_percent']}%")
        print(f"  换手率: {row['turnover_rate'] if row['turnover_rate'] else 'NULL'}")
        print(f"  成交额: {row['turnover_amount'] if row['turnover_amount'] else 'NULL'}")
    
    # 统计null字段
    sql_null = """
    SELECT 
        COUNT(*) as total,
        SUM(CASE WHEN main_net_inflow IS NULL THEN 1 ELSE 0 END) as null_main,
        SUM(CASE WHEN super_large_net_inflow IS NULL THEN 1 ELSE 0 END) as null_super,
        SUM(CASE WHEN large_net_inflow IS NULL THEN 1 ELSE 0 END) as null_large,
        SUM(CASE WHEN medium_net_inflow IS NULL THEN 1 ELSE 0 END) as null_medium,
        SUM(CASE WHEN small_net_inflow IS NULL THEN 1 ELSE 0 END) as null_small,
        SUM(CASE WHEN main_net_inflow_ratio IS NULL THEN 1 ELSE 0 END) as null_ratio,
        SUM(CASE WHEN close_price IS NULL THEN 1 ELSE 0 END) as null_price,
        SUM(CASE WHEN change_percent IS NULL THEN 1 ELSE 0 END) as null_change,
        SUM(CASE WHEN turnover_rate IS NULL THEN 1 ELSE 0 END) as null_turnover_rate,
        SUM(CASE WHEN turnover_amount IS NULL THEN 1 ELSE 0 END) as null_turnover_amount
    FROM stock_capital_flow_history
    WHERE secid = '0.000001'
    """
    
    null_stats = db.execute_query(sql_null)
    if null_stats:
        stats = null_stats[0]
        print("\n" + "=" * 60)
        print("NULL字段统计（平安银行）：")
        print("=" * 60)
        print(f"总记录数: {stats['total']}")
        print(f"主力净流入为NULL: {stats['null_main']}")
        print(f"超大单净流入为NULL: {stats['null_super']}")
        print(f"大单净流入为NULL: {stats['null_large']}")
        print(f"中单净流入为NULL: {stats['null_medium']}")
        print(f"小单净流入为NULL: {stats['null_small']}")
        print(f"主力净流入占比为NULL: {stats['null_ratio']}")
        print(f"收盘价为NULL: {stats['null_price']}")
        print(f"涨跌幅为NULL: {stats['null_change']}")
        print(f"换手率为NULL: {stats['null_turnover_rate']}")
        print(f"成交额为NULL: {stats['null_turnover_amount']}")
    
    print("\n" + "=" * 60)
    print("验证完成")
    print("=" * 60)
    
except Exception as e:
    print(f"[错误] 验证失败: {e}")
    import traceback
    traceback.print_exc()

