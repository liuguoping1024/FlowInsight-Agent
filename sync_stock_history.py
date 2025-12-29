"""
同步股票历史资金数据脚本
从数据库获取股票列表，逐个同步每只股票的历史资金数据
"""
import logging
import sys
import io
import time
from services.data_collector import DataCollector
from database.db_connection import db

# 设置标准输出编码为UTF-8（Windows兼容）
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def sync_stock_history(stock_limit: int = None, limit: int = 0, test_mode: bool = False, skip_synced: bool = False):
    """
    同步股票历史资金数据
    
    Args:
        stock_limit: 限制同步的股票数量，None表示同步全部股票
        limit: API请求的lmt参数，0表示获取所有历史记录，1表示获取最新1条，默认0
        test_mode: 测试模式，True时只同步前10只股票
        skip_synced: 是否跳过已同步的股票（检查是否有历史数据）
    """
    print("=" * 60)
    print("FlowInsight-Agent 股票历史资金数据同步")
    print("=" * 60)
    
    if test_mode:
        print("\n[测试模式] 只同步前10只股票")
        stock_limit = 10
    elif stock_limit:
        print(f"\n[限制模式] 只同步前 {stock_limit} 只股票")
    else:
        print("\n[完整模式] 同步所有股票")
    
    # API limit参数说明
    if limit == 0:
        print("[API参数] lmt=0，获取所有历史记录")
    else:
        print(f"[API参数] lmt={limit}，获取最新 {limit} 条交易数据")
    
    print("注意：每次请求后会等待1秒，避免被限流")
    print("=" * 60)
    
    # 从数据库获取股票列表
    try:
        if skip_synced:
            # 跳过已同步的股票（已有历史数据的）
            if stock_limit:
                sql = """
                SELECT sl.stock_code, sl.market_code, sl.secid, sl.stock_name
                FROM stock_list sl
                LEFT JOIN (
                    SELECT DISTINCT secid 
                    FROM stock_capital_flow_history
                ) h ON sl.secid = h.secid
                WHERE sl.is_active = 1 AND h.secid IS NULL
                ORDER BY sl.stock_code
                LIMIT %s
                """
                stocks = db.execute_query(sql, (stock_limit,))
            else:
                sql = """
                SELECT sl.stock_code, sl.market_code, sl.secid, sl.stock_name
                FROM stock_list sl
                LEFT JOIN (
                    SELECT DISTINCT secid 
                    FROM stock_capital_flow_history
                ) h ON sl.secid = h.secid
                WHERE sl.is_active = 1 AND h.secid IS NULL
                ORDER BY sl.stock_code
                """
                stocks = db.execute_query(sql)
            print("\n[跳过模式] 将跳过已有历史数据的股票")
        else:
            if stock_limit:
                sql = """
                SELECT stock_code, market_code, secid, stock_name
                FROM stock_list
                WHERE is_active = 1
                ORDER BY stock_code
                LIMIT %s
                """
                stocks = db.execute_query(sql, (stock_limit,))
            else:
                sql = """
                SELECT stock_code, market_code, secid, stock_name
                FROM stock_list
                WHERE is_active = 1
                ORDER BY stock_code
                """
                stocks = db.execute_query(sql)
            print("\n[更新模式] 已同步的股票将更新数据（使用ON DUPLICATE KEY UPDATE）")
        
        # 确保上证指数和深证成指在列表中（默认包含，优先同步）
        index_secids = ['1.000001', '0.399001']  # 上证指数、深证成指
        existing_secids = {stock['secid'] for stock in stocks}
        
        # 如果使用跳过模式，需要检查指数是否已有历史数据
        if skip_synced:
            for index_secid in index_secids:
                if index_secid not in existing_secids:
                    # 检查指数是否有历史数据
                    sql_check_history = """
                    SELECT COUNT(*) as count
                    FROM stock_capital_flow_history
                    WHERE secid = %s
                    """
                    history_check = db.execute_query(sql_check_history, (index_secid,))
                    has_history = history_check and history_check[0]['count'] > 0
                    
                    if not has_history:
                        # 从数据库查询指数信息
                        sql_index = """
                        SELECT stock_code, market_code, secid, stock_name
                        FROM stock_list
                        WHERE secid = %s AND is_active = 1
                        """
                        index_stocks = db.execute_query(sql_index, (index_secid,))
                        if index_stocks:
                            stocks.insert(0, index_stocks[0])  # 插入到列表开头
                            print(f"[信息] 添加指数到同步列表: {index_stocks[0]['stock_name']} ({index_secid})")
        else:
            # 更新模式：确保指数在列表中（即使已有历史数据也会更新）
            for index_secid in index_secids:
                if index_secid not in existing_secids:
                    # 从数据库查询指数信息
                    sql_index = """
                    SELECT stock_code, market_code, secid, stock_name
                    FROM stock_list
                    WHERE secid = %s AND is_active = 1
                    """
                    index_stocks = db.execute_query(sql_index, (index_secid,))
                    if index_stocks:
                        stocks.insert(0, index_stocks[0])  # 插入到列表开头
                        print(f"[信息] 添加指数到同步列表: {index_stocks[0]['stock_name']} ({index_secid})")
        
        total_stocks = len(stocks)
        print(f"\n[信息] 找到 {total_stocks} 只股票需要同步（包含上证指数和深证成指）")
        
        if total_stocks == 0:
            print("[错误] 数据库中没有股票数据，请先运行 init_data.py 同步股票列表")
            return
        
    except Exception as e:
        logger.error(f"获取股票列表失败: {e}")
        print(f"[错误] 获取股票列表失败: {e}")
        return
    
    # 初始化数据采集器
    collector = DataCollector()
    
    # 统计信息
    success_count = 0
    fail_count = 0
    start_time = time.time()
    
    print(f"\n开始同步，共 {total_stocks} 只股票...")
    print("-" * 60)
    
    # 逐个同步每只股票
    for idx, stock in enumerate(stocks, 1):
        secid = stock['secid']
        stock_code = stock['stock_code']
        stock_name = stock['stock_name']
        
        print(f"\n[{idx}/{total_stocks}] 正在同步: {stock_code} - {stock_name} ({secid})")
        
        try:
            # 同步历史数据，使用limit参数（0表示获取所有记录）
            collector.sync_stock_capital_flow_history(secid, limit=limit)
            success_count += 1
            print(f"  [成功] {stock_code} 同步完成")
            
        except Exception as e:
            fail_count += 1
            logger.error(f"同步 {secid} 失败: {e}")
            print(f"  [失败] {stock_code} 同步失败: {str(e)[:100]}")
        
        # 等待1秒后再请求下一只股票（最后一只不需要等待）
        if idx < total_stocks:
            time.sleep(1.0)
    
    # 统计结果
    elapsed_time = time.time() - start_time
    print("\n" + "=" * 60)
    print("[完成] 股票历史数据同步完成！")
    print("=" * 60)
    print(f"总股票数: {total_stocks}")
    print(f"成功: {success_count} 只")
    print(f"失败: {fail_count} 只")
    print(f"耗时: {elapsed_time:.2f} 秒 ({elapsed_time/60:.2f} 分钟)")
    print("=" * 60)
    
    # 验证数据
    if success_count > 0:
        print("\n[信息] 验证数据库中的历史数据...")
        try:
            sql = """
            SELECT COUNT(DISTINCT secid) as stock_count,
                   COUNT(*) as total_records
            FROM stock_capital_flow_history
            """
            result = db.execute_query(sql)
            if result:
                stats = result[0]
                print(f"  有历史数据的股票数: {stats['stock_count']} 只")
                print(f"  历史数据总记录数: {stats['total_records']} 条")
        except Exception as e:
            logger.error(f"验证数据失败: {e}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='同步股票历史资金数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 同步所有股票的所有历史数据（默认）
  python sync_stock_history.py
  
  # 只同步前10只股票的所有历史数据
  python sync_stock_history.py --stock-limit 10
  
  # 同步所有股票，但API只获取最新1条数据
  python sync_stock_history.py --limit 1
  
  # 测试模式：只同步前10只股票
  python sync_stock_history.py --test
  
  # 跳过已同步的股票
  python sync_stock_history.py --skip-synced

API参数说明:
  --limit 参数对应API的 lmt 参数:
    - 0 (默认): 获取所有历史记录
    - 1: 获取最新1条交易数据
    - N: 获取最新N条交易数据
        """
    )
    parser.add_argument('--test', action='store_true', 
                       help='测试模式：只同步前10只股票')
    parser.add_argument('--stock-limit', type=int, metavar='N',
                       help='限制同步的股票数量（默认：同步所有股票）')
    parser.add_argument('--limit', type=int, default=0, metavar='N',
                       help='API的lmt参数：0=获取所有历史记录（默认），1=获取最新1条，N=获取最新N条')
    parser.add_argument('--skip-synced', action='store_true', 
                       help='跳过已同步的股票（已有历史数据的）')
    parser.add_argument('--yes', '-y', action='store_true', 
                       help='自动确认，跳过交互提示')
    
    args = parser.parse_args()
    
    try:
        # 默认同步所有股票的所有历史数据
        if args.test:
            sync_stock_history(stock_limit=10, limit=args.limit, 
                             test_mode=True, skip_synced=args.skip_synced)
        elif args.stock_limit is not None:
            if args.stock_limit == 0:
                # stock_limit=0 表示同步所有股票
                sync_stock_history(stock_limit=None, limit=args.limit, 
                                 skip_synced=args.skip_synced)
            else:
                sync_stock_history(stock_limit=args.stock_limit, limit=args.limit, 
                                 skip_synced=args.skip_synced)
        else:
            # 默认同步所有股票的所有历史数据
            sync_stock_history(stock_limit=None, limit=args.limit, 
                             skip_synced=args.skip_synced)
    except KeyboardInterrupt:
        print("\n\n[警告] 用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"同步失败: {e}")
        print(f"\n[错误] 同步失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

