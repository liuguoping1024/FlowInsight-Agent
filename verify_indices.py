"""
验证上证指数和深证成指是否已正确添加到数据库
"""
import sys
import io
from database.db_connection import db

# 设置标准输出编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def verify_indices():
    """验证上证指数和深证成指是否在 stock_list 表中"""
    print("=" * 60)
    print("验证上证指数和深证成指")
    print("=" * 60)
    
    index_secids = [
        {'secid': '1.000001', 'name': '上证指数'},
        {'secid': '0.399001', 'name': '深证成指'}
    ]
    
    try:
        for index_info in index_secids:
            secid = index_info['secid']
            name = index_info['name']
            
            sql = """
            SELECT stock_code, market_code, stock_name, secid, is_active
            FROM stock_list
            WHERE secid = %s
            """
            result = db.execute_query(sql, (secid,))
            
            if result:
                stock = result[0]
                print(f"\n✓ {name} ({secid})")
                print(f"  股票代码: {stock['stock_code']}")
                print(f"  市场代码: {stock['market_code']}")
                print(f"  股票名称: {stock['stock_name']}")
                print(f"  是否活跃: {'是' if stock['is_active'] else '否'}")
                
                # 检查是否有历史数据
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
                    print(f"  历史数据: {history['count']} 条记录")
                    print(f"  日期范围: {history['earliest_date']} 至 {history['latest_date']}")
                else:
                    print(f"  历史数据: 暂无（需要运行 sync_stock_history.py 同步）")
            else:
                print(f"\n✗ {name} ({secid}) 未找到")
                print(f"  请运行 python init_database.py 初始化数据库")
        
        print("\n" + "=" * 60)
        print("验证完成")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[错误] 验证失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == '__main__':
    try:
        verify_indices()
    except KeyboardInterrupt:
        print("\n\n[警告] 用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n[错误] 发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

