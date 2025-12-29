"""
手动添加上证指数和深证成指到 stock_list 表
如果数据已存在，则更新
"""
import sys
import io
from database.db_connection import db

# 设置标准输出编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def add_indices():
    """添加上证指数和深证成指到 stock_list 表"""
    print("=" * 60)
    print("添加上证指数和深证成指到 stock_list 表")
    print("=" * 60)
    
    indices = [
        {
            'stock_code': '000001',
            'market_code': 1,
            'stock_name': '上证指数',
            'secid': '1.000001'
        },
        {
            'stock_code': '399001',
            'market_code': 0,
            'stock_name': '深证成指',
            'secid': '0.399001'
        }
    ]
    
    try:
        sql = """
        INSERT INTO stock_list (stock_code, market_code, stock_name, secid, is_active)
        VALUES (%s, %s, %s, %s, 1)
        ON DUPLICATE KEY UPDATE
            stock_name = VALUES(stock_name),
            is_active = VALUES(is_active),
            updated_at = NOW()
        """
        
        for index_info in indices:
            try:
                affected = db.execute_update(sql, (
                    index_info['stock_code'],
                    index_info['market_code'],
                    index_info['stock_name'],
                    index_info['secid']
                ))
                
                if affected > 0:
                    print(f"\n✓ {index_info['stock_name']} ({index_info['secid']})")
                    print(f"  股票代码: {index_info['stock_code']}")
                    print(f"  市场代码: {index_info['market_code']}")
                    print(f"  操作: {'已添加' if affected == 1 else '已更新'}")
                else:
                    print(f"\n⚠ {index_info['stock_name']} ({index_info['secid']}) - 无变化")
                    
            except Exception as e:
                print(f"\n✗ {index_info['stock_name']} ({index_info['secid']}) 添加失败: {e}")
        
        # 验证数据
        print("\n" + "=" * 60)
        print("验证数据")
        print("=" * 60)
        
        for index_info in indices:
            sql_check = """
            SELECT stock_code, market_code, stock_name, secid, is_active
            FROM stock_list
            WHERE secid = %s
            """
            result = db.execute_query(sql_check, (index_info['secid'],))
            
            if result:
                stock = result[0]
                print(f"\n✓ {stock['stock_name']} ({stock['secid']})")
                print(f"  股票代码: {stock['stock_code']}")
                print(f"  市场代码: {stock['market_code']}")
                print(f"  是否活跃: {'是' if stock['is_active'] else '否'}")
            else:
                print(f"\n✗ {index_info['stock_name']} ({index_info['secid']}) 未找到")
        
        print("\n" + "=" * 60)
        print("操作完成")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n[错误] 操作失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    try:
        add_indices()
    except KeyboardInterrupt:
        print("\n\n[警告] 用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n[错误] 发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

