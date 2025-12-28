"""
数据库扩展初始化脚本
只执行 schema_extensions.sql，用于添加推荐股票表等扩展功能
"""
import pymysql
import os
import sys
import io

# 设置标准输出编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from config import DB_CONFIG

def read_sql_file(file_path):
    """读取SQL文件内容"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    except Exception as e:
        print(f"[错误] 读取SQL文件失败: {e}")
        return None

def execute_sql_script(sql_content):
    """执行SQL脚本"""
    try:
        # 连接到MySQL服务器
        connection = pymysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            charset=DB_CONFIG['charset'],
            autocommit=True
        )
        
        print("[成功] 成功连接到MySQL数据库")
        
        with connection.cursor() as cursor:
            # 分割SQL语句（按分号和换行）
            statements = []
            current_statement = ""
            
            for line in sql_content.split('\n'):
                # 跳过注释和空行
                line = line.strip()
                if not line or line.startswith('--'):
                    continue
                
                current_statement += line + '\n'
                
                # 如果遇到分号，说明一个语句结束
                if line.endswith(';'):
                    statements.append(current_statement.strip())
                    current_statement = ""
            
            # 执行每个SQL语句
            success_count = 0
            error_count = 0
            
            for i, statement in enumerate(statements, 1):
                if not statement:
                    continue
                
                try:
                    cursor.execute(statement)
                    success_count += 1
                    print(f"  [成功] 执行语句 {i}/{len(statements)}")
                except Exception as e:
                    error_count += 1
                    # 如果是表已存在的错误，可以忽略
                    error_msg = str(e).lower()
                    if "already exists" in error_msg or "duplicate table" in error_msg:
                        print(f"  [跳过] 语句 {i}: 表已存在，跳过")
                        success_count += 1  # 也算成功
                    else:
                        print(f"  [警告] 语句 {i} 执行失败: {str(e)[:100]}")
            
            print(f"\n[成功] SQL执行完成: 成功 {success_count} 条, 失败 {error_count} 条")
            
        connection.close()
        return True
        
    except pymysql.Error as e:
        print(f"[错误] 数据库操作失败: {e}")
        print("\n请检查:")
        print(f"  1. MySQL服务是否已启动")
        print(f"  2. 数据库配置是否正确:")
        print(f"     - 主机: {DB_CONFIG['host']}")
        print(f"     - 端口: {DB_CONFIG['port']}")
        print(f"     - 用户: {DB_CONFIG['user']}")
        print(f"     - 数据库: {DB_CONFIG['database']}")
        print(f"     - 密码: {'*' * len(DB_CONFIG['password'])}")
        return False
    except Exception as e:
        print(f"[错误] 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_connection():
    """测试数据库连接"""
    try:
        connection = pymysql.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            charset=DB_CONFIG['charset']
        )
        connection.close()
        print("[成功] 数据库连接测试成功")
        return True
    except Exception as e:
        print(f"[错误] 数据库连接测试失败: {e}")
        return False

def main():
    """主函数"""
    print("=" * 60)
    print("FlowInsight-Agent 数据库扩展初始化工具")
    print("=" * 60)
    print(f"\n数据库配置:")
    print(f"  主机: {DB_CONFIG['host']}")
    print(f"  端口: {DB_CONFIG['port']}")
    print(f"  用户: {DB_CONFIG['user']}")
    print(f"  数据库: {DB_CONFIG['database']}")
    print("=" * 60)
    
    # 检查SQL文件是否存在
    sql_file = os.path.join('database', 'schema_extensions.sql')
    if not os.path.exists(sql_file):
        print(f"[错误] SQL文件不存在: {sql_file}")
        print("请确保 database/schema_extensions.sql 文件存在")
        sys.exit(1)
    
    # 读取SQL文件
    print(f"\n[信息] 读取SQL文件: {sql_file}")
    sql_content = read_sql_file(sql_file)
    if not sql_content:
        sys.exit(1)
    
    print(f"[成功] SQL文件读取成功 ({len(sql_content)} 字符)")
    
    # 执行SQL脚本
    print("\n[信息] 开始执行SQL脚本...")
    print("注意: 如果表已存在，将自动跳过（使用 CREATE TABLE IF NOT EXISTS）")
    if execute_sql_script(sql_content):
        print("\n" + "=" * 60)
        print("[成功] 数据库扩展初始化完成！")
        print("=" * 60)
        
        # 测试连接
        print("\n[信息] 测试数据库连接...")
        if test_connection():
            print("\n[成功] 所有操作完成！扩展表已创建。")
            print("\n已创建的表:")
            print("  - user_settings (用户设置表)")
            print("  - user_llm_configs (用户LLM配置表)")
            print("  - recommended_stocks (推荐股票表)")
            print("\n下一步:")
            print("  1. 运行 python calculate_recommendations.py 计算推荐股票（可选）")
            print("  2. 运行 python start.py 启动服务")
        else:
            print("\n[警告] 扩展初始化完成，但连接测试失败，请检查配置")
    else:
        print("\n" + "=" * 60)
        print("[错误] 数据库扩展初始化失败")
        print("=" * 60)
        sys.exit(1)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[警告] 用户中断操作")
        sys.exit(1)
    except Exception as e:
        print(f"\n[错误] 发生未预期的错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

