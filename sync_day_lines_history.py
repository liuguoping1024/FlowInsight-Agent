"""
同步股票日K线历史数据脚本
从数据库获取股票列表，逐个同步每只股票的日K线历史数据
"""
import logging
import sys
import io
import time
from datetime import datetime, timedelta
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


def sync_day_lines_history(
    stock_limit: int = None, 
    days: int = None, 
    beg: str = None, 
    end: str = None,
    test_mode: bool = False, 
    skip_synced: bool = False,
    fqt: int = 1
):
    """
    同步股票日K线历史数据
    
    Args:
        stock_limit: 限制同步的股票数量，None表示同步全部股票
        days: 同步多少天的数据，None时使用默认值（180天，约120个交易日）
        beg: 开始日期，格式：YYYYMMDD（如 '20240101'），如果指定则覆盖days参数
        end: 结束日期，格式：YYYYMMDD（如 '20241231'），默认为今天
        test_mode: 测试模式，True时只同步前10只股票
        skip_synced: 是否跳过已同步的股票（检查是否有日K线数据）
        fqt: 复权类型（0=不复权，1=前复权，2=后复权），默认1
    """
    print("=" * 60)
    print("FlowInsight-Agent 股票日K线历史数据同步")
    print("=" * 60)
    
    if test_mode:
        print("\n[测试模式] 只同步前10只股票")
        stock_limit = 10
    elif stock_limit:
        print(f"\n[限制模式] 只同步前 {stock_limit} 只股票")
    else:
        print("\n[完整模式] 同步所有股票")
    
    # 处理日期范围
    if beg and end:
        print(f"[日期范围] {beg} 到 {end}")
        beg_date = beg
        end_date = end
    elif beg:
        # 只指定了开始日期，结束日期为今天
        end_date = datetime.now().strftime('%Y%m%d')
        beg_date = beg
        print(f"[日期范围] {beg_date} 到 {end_date}")
    elif end:
        # 只指定了结束日期，往前推180天
        end_date = end
        end_datetime = datetime.strptime(end, '%Y%m%d')
        beg_datetime = end_datetime - timedelta(days=180)
        beg_date = beg_datetime.strftime('%Y%m%d')
        print(f"[日期范围] {beg_date} 到 {end_date} (结束日期往前推180天)")
    else:
        # 没有指定日期，使用默认值：180天（约120个交易日）
        if days is None:
            days = 180
        end_date = datetime.now().strftime('%Y%m%d')
        beg_datetime = datetime.now() - timedelta(days=days)
        beg_date = beg_datetime.strftime('%Y%m%d')
        print(f"[日期范围] {beg_date} 到 {end_date} ({days}天，约{int(days*5/7)}个交易日)")
    
    print(f"[复权类型] {'前复权' if fqt == 1 else '后复权' if fqt == 2 else '不复权'}")
    print("注意：每次请求后会等待1秒，避免被限流")
    print("=" * 60)
    
    # 从数据库获取股票列表
    try:
        if skip_synced:
            # 跳过已同步的股票（已有日K线数据的）
            if stock_limit:
                sql = """
                SELECT sl.stock_code, sl.market_code, sl.secid, sl.stock_name
                FROM stock_list sl
                LEFT JOIN (
                    SELECT DISTINCT secid 
                    FROM stock_day_lines_history
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
                    FROM stock_day_lines_history
                ) h ON sl.secid = h.secid
                WHERE sl.is_active = 1 AND h.secid IS NULL
                ORDER BY sl.stock_code
                """
                stocks = db.execute_query(sql)
            print("\n[跳过模式] 将跳过已有日K线数据的股票")
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
        
        # 如果使用跳过模式，需要检查指数是否已有日K线数据
        if skip_synced:
            for index_secid in index_secids:
                if index_secid not in existing_secids:
                    # 检查指数是否有日K线数据
                    sql_check_history = """
                    SELECT COUNT(*) as count
                    FROM stock_day_lines_history
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
            # 更新模式：确保指数在列表中（即使已有日K线数据也会更新）
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
            # 同步日K线历史数据
            result = collector.sync_stock_day_kline_history(
                secid=secid,
                beg=beg_date,
                end=end_date,
                fqt=fqt
            )
            
            if result.get('success'):
                success_count += 1
                stats = result.get('sync_stats', {})
                new_days = stats.get('new_days', 0)
                updated_days = stats.get('updated_days', 0)
                print(f"  [成功] {stock_code} 同步完成 (新增: {new_days}, 更新: {updated_days})")
            else:
                fail_count += 1
                message = result.get('message', '未知错误')
                print(f"  [失败] {stock_code} 同步失败: {message}")
            
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
    print("[完成] 股票日K线历史数据同步完成！")
    print("=" * 60)
    print(f"总股票数: {total_stocks}")
    print(f"成功: {success_count} 只")
    print(f"失败: {fail_count} 只")
    print(f"耗时: {elapsed_time:.2f} 秒 ({elapsed_time/60:.2f} 分钟)")
    print("=" * 60)
    
    # 验证数据
    if success_count > 0:
        print("\n[信息] 验证数据库中的日K线数据...")
        try:
            sql = """
            SELECT COUNT(DISTINCT secid) as stock_count,
                   COUNT(*) as total_records
            FROM stock_day_lines_history
            """
            result = db.execute_query(sql)
            if result:
                stats = result[0]
                print(f"  有日K线数据的股票数: {stats['stock_count']} 只")
                print(f"  日K线数据总记录数: {stats['total_records']} 条")
        except Exception as e:
            logger.error(f"验证数据失败: {e}")


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(
        description='同步股票日K线历史数据',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 同步所有股票的日K线数据（默认180天，约120个交易日）
  python sync_day_lines_history.py
  
  # 只同步前10只股票的日K线数据
  python sync_day_lines_history.py --stock-limit 10
  
  # 同步指定天数的数据（例如90天）
  python sync_day_lines_history.py --days 90
  
  # 同步指定日期范围的数据
  python sync_day_lines_history.py --beg 20241201 --end 20241231
  
  # 测试模式：只同步前10只股票
  python sync_day_lines_history.py --test
  
  # 跳过已同步的股票
  python sync_day_lines_history.py --skip-synced
  
  # 使用不复权数据
  python sync_day_lines_history.py --fqt 0
  
  # 使用后复权数据
  python sync_day_lines_history.py --fqt 2

日期参数说明:
  --days: 同步多少天的数据（默认180天，约120个交易日）
  --beg: 开始日期，格式：YYYYMMDD（如 20241201）
  --end: 结束日期，格式：YYYYMMDD（如 20241231），默认为今天
  
  如果指定了 --beg 和 --end，则使用指定的日期范围
  如果只指定了 --beg，则从开始日期到今天
  如果只指定了 --end，则从结束日期往前推180天
  如果都不指定，则使用默认值：从今天往前推180天

复权类型说明:
  --fqt: 复权类型（0=不复权，1=前复权，2=后复权），默认1（前复权）
        """
    )
    parser.add_argument('--test', action='store_true', 
                       help='测试模式：只同步前10只股票')
    parser.add_argument('--stock-limit', type=int, metavar='N',
                       help='限制同步的股票数量（默认：同步所有股票）')
    parser.add_argument('--days', type=int, metavar='N',
                       help='同步多少天的数据（默认180天，约120个交易日）')
    parser.add_argument('--beg', type=str, metavar='YYYYMMDD',
                       help='开始日期，格式：YYYYMMDD（如 20241201）')
    parser.add_argument('--end', type=str, metavar='YYYYMMDD',
                       help='结束日期，格式：YYYYMMDD（如 20241231），默认为今天')
    parser.add_argument('--skip-synced', action='store_true', 
                       help='跳过已同步的股票（已有日K线数据的）')
    parser.add_argument('--fqt', type=int, default=1, choices=[0, 1, 2],
                       help='复权类型（0=不复权，1=前复权，2=后复权），默认1')
    parser.add_argument('--yes', '-y', action='store_true', 
                       help='自动确认，跳过交互提示')
    
    args = parser.parse_args()
    
    try:
        # 默认同步所有股票的日K线数据（180天）
        if args.test:
            sync_day_lines_history(
                stock_limit=10, 
                days=args.days,
                beg=args.beg,
                end=args.end,
                test_mode=True, 
                skip_synced=args.skip_synced,
                fqt=args.fqt
            )
        elif args.stock_limit is not None:
            if args.stock_limit == 0:
                # stock_limit=0 表示同步所有股票
                sync_day_lines_history(
                    stock_limit=None, 
                    days=args.days,
                    beg=args.beg,
                    end=args.end,
                    skip_synced=args.skip_synced,
                    fqt=args.fqt
                )
            else:
                sync_day_lines_history(
                    stock_limit=args.stock_limit, 
                    days=args.days,
                    beg=args.beg,
                    end=args.end,
                    skip_synced=args.skip_synced,
                    fqt=args.fqt
                )
        else:
            # 默认同步所有股票的日K线数据（180天）
            sync_day_lines_history(
                stock_limit=None, 
                days=args.days,
                beg=args.beg,
                end=args.end,
                skip_synced=args.skip_synced,
                fqt=args.fqt
            )
    except KeyboardInterrupt:
        print("\n\n[警告] 用户中断操作")
        sys.exit(1)
    except Exception as e:
        logger.error(f"同步失败: {e}")
        print(f"\n[错误] 同步失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
