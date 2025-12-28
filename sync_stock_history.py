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


def sync_stock_history(limit: int = None, test_mode: bool = False, skip_synced: bool = False):
    """
    同步股票历史资金数据
    
    Args:
        limit: 限制同步的股票数量，None表示同步全部
        test_mode: 测试模式，True时只同步前10只股票
        skip_synced: 是否跳过已同步的股票（检查是否有历史数据）
    """
    print("=" * 60)
    print("FlowInsight-Agent 股票历史资金数据同步")
    print("=" * 60)
    
    if test_mode:
        print("\n[测试模式] 只同步前10只股票")
        limit = 10
    elif limit:
        print(f"\n[限制模式] 只同步前 {limit} 只股票")
    else:
        print("\n[完整模式] 同步所有股票")
    
    print("注意：每次请求后会等待1秒，避免被限流")
    print("=" * 60)
    
    # 从数据库获取股票列表
    try:
        if skip_synced:
            # 跳过已同步的股票（已有历史数据的）
            if limit:
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
                stocks = db.execute_query(sql, (limit,))
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
            print(f"\n[跳过模式] 将跳过已有历史数据的股票")
        else:
            if limit:
                sql = """
                SELECT stock_code, market_code, secid, stock_name
                FROM stock_list
                WHERE is_active = 1
                ORDER BY stock_code
                LIMIT %s
                """
                stocks = db.execute_query(sql, (limit,))
            else:
                sql = """
                SELECT stock_code, market_code, secid, stock_name
                FROM stock_list
                WHERE is_active = 1
                ORDER BY stock_code
                """
                stocks = db.execute_query(sql)
            print(f"\n[更新模式] 已同步的股票将更新数据（使用ON DUPLICATE KEY UPDATE）")
        
        total_stocks = len(stocks)
        print(f"\n[信息] 找到 {total_stocks} 只股票需要同步")
        
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
            # 同步历史数据（最多250天）
            collector.sync_stock_capital_flow_history(secid, limit=250)
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
    
    parser = argparse.ArgumentParser(description='同步股票历史资金数据')
    parser.add_argument('--test', action='store_true', help='测试模式：只同步前10只股票')
    parser.add_argument('--limit', type=int, help='限制同步的股票数量（0表示全部）')
    parser.add_argument('--skip-synced', action='store_true', help='跳过已同步的股票（已有历史数据的）')
    parser.add_argument('--all', action='store_true', help='同步全部股票（5499只）')
    parser.add_argument('--yes', '-y', action='store_true', help='自动确认，跳过交互提示')
    
    args = parser.parse_args()
    
    try:
        if args.test:
            sync_stock_history(test_mode=True, skip_synced=args.skip_synced)
        elif args.all:
            # 同步全部股票
            print("\n[确认] 即将同步全部5499只股票的历史数据")
            print("预计耗时: 约1.5-2小时（5499秒 ≈ 91分钟 + 网络请求时间）")
            print("已同步的股票将更新数据（使用ON DUPLICATE KEY UPDATE）")
            if not args.yes:
                try:
                    response = input("\n确认开始同步？(y/n): ")
                    if response.lower() != 'y':
                        print("已取消")
                        sys.exit(0)
                except (EOFError, KeyboardInterrupt):
                    print("\n[错误] 无法读取输入，请使用 --yes 参数自动确认")
                    sys.exit(1)
            sync_stock_history(limit=None, skip_synced=args.skip_synced)
        elif args.limit is not None:
            if args.limit == 0:
                sync_stock_history(limit=None, skip_synced=args.skip_synced)
            else:
                sync_stock_history(limit=args.limit, skip_synced=args.skip_synced)
        else:
            # 默认测试模式，避免误操作
            print("[警告] 未指定模式，默认使用测试模式（只同步10只股票）")
            print("如需同步全部股票，请使用: python sync_stock_history.py --all")
            print("或使用: python sync_stock_history.py --limit 0")
            response = input("\n是否继续测试模式？(y/n): ")
            if response.lower() == 'y':
                sync_stock_history(test_mode=True)
            else:
                print("已取消")
    except KeyboardInterrupt:
        print("\n\n[警告] 用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"同步失败: {e}")
        print(f"\n[错误] 同步失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

