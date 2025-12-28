"""
数据库连接检查脚本
用于验证数据库配置是否正确
"""
import pymysql
import sys
import io

# 设置标准输出编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from config import DB_CONFIG

def check_database():
    """检查数据库连接和表结构"""
    print("=" * 60)
    print("数据库连接检查")
    print("=" * 60)
    print(f"\n配置信息:")
    print(f"  主机: {DB_CONFIG['host']}")
    print(f"  端口: {DB_CONFIG['port']}")
    print(f"  用户: {DB_CONFIG['user']}")
    print(f"  数据库: {DB_CONFIG['database']}")
    print("=" * 60)
    
    try:
        # 测试连接
        print("\n1. 测试MySQL服务器连接...")
        connection = pymysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            charset=DB_CONFIG['charset']
        )
        print("   [成功] MySQL服务器连接成功")
        connection.close()
        
        # 测试数据库连接
        print("\n2. 测试数据库连接...")
        connection = pymysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            charset=DB_CONFIG['charset']
        )
        print(f"   [成功] 数据库 '{DB_CONFIG['database']}' 连接成功")
        
        # 检查表
        print("\n3. 检查数据表...")
        with connection.cursor() as cursor:
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            table_names = [table[0] for table in tables]
            
            expected_tables = [
                'user_groups',
                'users',
                'user_stocks',
                'stock_list',
                'stock_capital_flow_history',
                'stock_health_scores',
                'index_data'
            ]
            
            print(f"   找到 {len(table_names)} 个表:")
            for table in table_names:
                print(f"     - {table}")
            
            print(f"\n   期望的表 ({len(expected_tables)} 个):")
            missing_tables = []
            for expected in expected_tables:
                if expected in table_names:
                    print(f"     [成功] {expected}")
                else:
                    print(f"     [错误] {expected} (缺失)")
                    missing_tables.append(expected)
            
            if missing_tables:
                print(f"\n   [警告] 缺少 {len(missing_tables)} 个表，请运行 init_database.py 初始化数据库")
            else:
                print(f"\n   [成功] 所有表都存在")
        
        # 检查数据
        print("\n4. 检查初始数据...")
        with connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) FROM user_groups")
            group_count = cursor.fetchone()[0]
            print(f"   用户组: {group_count} 条")
            
            cursor.execute("SELECT COUNT(*) FROM users")
            user_count = cursor.fetchone()[0]
            print(f"   用户: {user_count} 条")
            
            cursor.execute("SELECT COUNT(*) FROM index_data")
            index_count = cursor.fetchone()[0]
            print(f"   指数: {index_count} 条")
        
        connection.close()
        
        print("\n" + "=" * 60)
        print("[成功] 数据库检查完成！")
        print("=" * 60)
        return True
        
    except pymysql.Error as e:
        print(f"\n[错误] 数据库连接失败: {e}")
        print("\n可能的原因:")
        print("  1. MySQL服务未启动")
        print("  2. 用户名或密码错误")
        print("  3. 数据库不存在（需要先运行 init_database.py）")
        print("  4. 网络连接问题")
        return False
    except Exception as e:
        print(f"\n[错误] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    check_database()

