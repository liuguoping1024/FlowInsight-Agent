"""
检查同步进度
"""
import sys
import io
from database.db_connection import db

# 设置标准输出编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("=" * 60)
print("股票历史数据同步进度")
print("=" * 60)

try:
    # 总股票数
    sql_total = "SELECT COUNT(*) as total FROM stock_list WHERE is_active = 1"
    total_result = db.execute_query(sql_total)
    total_stocks = total_result[0]['total'] if total_result else 0
    
    # 已同步的股票数（有历史数据的）
    sql_synced = """
    SELECT COUNT(DISTINCT secid) as synced_count
    FROM stock_capital_flow_history
    """
    synced_result = db.execute_query(sql_synced)
    synced_stocks = synced_result[0]['synced_count'] if synced_result else 0
    
    # 历史数据总记录数
    sql_records = "SELECT COUNT(*) as total FROM stock_capital_flow_history"
    records_result = db.execute_query(sql_records)
    total_records = records_result[0]['total'] if records_result else 0
    
    # 计算进度
    progress = (synced_stocks / total_stocks * 100) if total_stocks > 0 else 0
    
    print(f"\n总股票数: {total_stocks} 只")
    print(f"已同步: {synced_stocks} 只")
    print(f"剩余: {total_stocks - synced_stocks} 只")
    print(f"进度: {progress:.2f}%")
    print(f"历史数据总记录数: {total_records:,} 条")
    
    # 显示最近同步的10只股票
    sql_recent = """
    SELECT secid, MAX(trade_date) as last_date, COUNT(*) as record_count
    FROM stock_capital_flow_history
    GROUP BY secid
    ORDER BY last_date DESC
    LIMIT 10
    """
    recent_stocks = db.execute_query(sql_recent)
    
    if recent_stocks:
        print("\n" + "-" * 60)
        print("最近同步的10只股票：")
        print("-" * 60)
        for stock in recent_stocks:
            print(f"  {stock['secid']}: 最新日期 {stock['last_date']}, 共 {stock['record_count']} 条记录")
    
    print("\n" + "=" * 60)
    
except Exception as e:
    print(f"[错误] 查询失败: {e}")
    import traceback
    traceback.print_exc()

