"""
检查上证指数和深证成指的历史数据同步情况
"""
import sys
import io
from datetime import date
from database.db_connection import db

# 设置标准输出编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def check_index_history():
    """检查指数历史数据"""
    print("=" * 60)
    print("检查上证指数和深证成指的历史数据")
    print("=" * 60)
    
    index_secids = [
        {'secid': '1.000001', 'name': '上证指数'},
        {'secid': '0.399001', 'name': '深证成指'}
    ]
    
    today = date.today()
    
    try:
        for index_info in index_secids:
            secid = index_info['secid']
            name = index_info['name']
            
            print(f"\n{name} ({secid}):")
            print("-" * 60)
            
            # 检查历史数据统计
            sql_history = """
            SELECT COUNT(*) as count, 
                   MIN(trade_date) as earliest_date,
                   MAX(trade_date) as latest_date
            FROM stock_capital_flow_history
            WHERE secid = %s
            """
            history_result = db.execute_query(sql_history, (secid,))
            
            if history_result and history_result[0]['count'] > 0:
                history = history_result[0]
                latest_date = history['latest_date']
                
                print(f"  历史记录数: {history['count']} 条")
                print(f"  最早日期: {history['earliest_date']}")
                print(f"  最新日期: {latest_date}")
                
                # 检查最新数据是否是今天
                if isinstance(latest_date, date):
                    days_diff = (today - latest_date).days
                    if days_diff == 0:
                        print(f"  ✓ 数据已同步到今天 ({today})")
                    elif days_diff == 1:
                        print(f"  ⚠ 最新数据是昨天 ({latest_date})，今天数据未同步")
                    else:
                        print(f"  ⚠ 最新数据是 {days_diff} 天前 ({latest_date})，需要同步")
                else:
                    print(f"  ⚠ 最新日期格式异常: {latest_date}")
                
                # 显示最近5天的数据
                sql_recent = """
                SELECT trade_date, main_net_inflow, close_price, change_percent
                FROM stock_capital_flow_history
                WHERE secid = %s
                ORDER BY trade_date DESC
                LIMIT 5
                """
                recent_data = db.execute_query(sql_recent, (secid,))
                
                if recent_data:
                    print("\n  最近5个交易日数据:")
                    for record in recent_data:
                        trade_date = record['trade_date']
                        main_inflow = record['main_net_inflow'] or 0
                        close_price = record['close_price'] or 0
                        change_pct = record['change_percent'] or 0
                        print(f"    {trade_date}: 收盘价={close_price:.2f}, 涨跌幅={change_pct:.2f}%, 主力净流入={main_inflow/10000:.2f}万")
            else:
                print("  ✗ 暂无历史数据")
                print("  需要运行: python sync_stock_history.py --test")
        
        print("\n" + "=" * 60)
        print("检查完成")
        print("=" * 60)
        print("\n提示:")
        print("  如果数据未同步到今天，可以运行:")
        print("    python sync_stock_history.py --test  # 测试模式（同步前10只股票+指数）")
        print("    或")
        print("    python sync_stock_history.py --limit 2  # 只同步指数（如果指数在前2只）")
        
        return True
        
    except Exception as e:
        print(f"\n[错误] 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    try:
        check_index_history()
    except KeyboardInterrupt:
        print("\n\n[警告] 用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n[错误] 发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

