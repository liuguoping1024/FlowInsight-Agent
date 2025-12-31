"""
技术指标计算模块
支持MACD、KDJ等常用技术指标的计算，参数可自定义

不同市场常用参数参考：

【中国市场（A股）常用参数】
MACD指标：
- 常用参数1: (10, 20, 7) - 快速EMA=10(约2周), 慢速EMA=20(约1个月), 信号线=7(约1.5周)
- 常用参数2: (10, 22, 9) - 快速EMA=10(约2周), 慢速EMA=22(约1个月), 信号线=9(约2周)
- 传统参数: (12, 26, 9) - 国际通用标准参数
- 超短线参数: (6, 13, 5) - 适合超短线交易，信号更敏感

KDJ指标：
- 标准参数: (9, 3, 3) - RSV周期=9, K平滑=3, D平滑=3（通用标准）

RSI指标：
- 标准参数: 14 - 14天周期（最常用）
- 短线参数: 6 - 6天周期（更敏感）
- 中线参数: 21 - 21天周期（更平滑）

【美国市场常用参数】
MACD指标：
- 传统标准参数: (12, 26, 9) - 快速EMA=12, 慢速EMA=26, 信号线=9
- 优化参数: (8, 17, 5) - 快速EMA=8, 慢速EMA=17, 信号线=5（2025年优化）

KDJ指标：
- 传统标准参数: (9, 3, 3) - RSV周期=9, K平滑=3, D平滑=3
- 高波动市场优化: (13, 5, 5) - RSV周期=13, K平滑=5, D平滑=5（适合纳斯达克等高波动市场）

注意：中国市场每周5个交易日，参数设置通常对应交易周数，如(10, 20, 7)对应约2周、1个月、1.5周的交易周期。
"""
import logging
from typing import List, Dict, Optional, Tuple
from decimal import Decimal

logger = logging.getLogger(__name__)


class TechnicalIndicators:
    """技术指标计算器"""
    
    def __init__(self):
        """初始化技术指标计算器"""
        pass
    
    def _to_float(self, value) -> float:
        """将值转换为float类型"""
        if value is None:
            return 0.0
        if isinstance(value, Decimal):
            return float(value)
        return float(value)
    
    def _ensure_ascending_order(self, data: List[Dict], date_key: str = 'trade_date') -> List[Dict]:
        """确保数据按日期升序排列"""
        return sorted(data, key=lambda x: x[date_key])
    
    def calculate_ema(self, prices: List[float], period: int) -> List[float]:
        """
        计算指数移动平均线(EMA)
        
        Args:
            prices: 价格列表
            period: 周期
            
        Returns:
            EMA值列表
        """
        if len(prices) == 0 or period <= 0:
            return []
        
        ema_values = []
        multiplier = 2.0 / (period + 1)
        
        # 第一个EMA值使用SMA
        if len(prices) >= period:
            sma = sum(prices[:period]) / period
            ema_values.append(sma)
            
            # 计算后续EMA值
            for i in range(period, len(prices)):
                ema = (prices[i] - ema_values[-1]) * multiplier + ema_values[-1]
                ema_values.append(ema)
        else:
            # 数据不足，返回空列表
            return []
        
        # 前面不足period的数据用None填充
        return [None] * (period - 1) + ema_values
    
    def calculate_macd(
        self, 
        data: List[Dict], 
        fast_period: int = 12, 
        slow_period: int = 26, 
        signal_period: int = 9,
        price_key: str = 'close_price'
    ) -> List[Dict]:
        """
        计算MACD指标
        
        MACD = 快速EMA - 慢速EMA
        Signal = MACD的EMA
        Histogram = MACD - Signal
        
        Args:
            data: 股票历史数据列表，必须包含price_key字段
            fast_period: 快速EMA周期，默认12
            slow_period: 慢速EMA周期，默认26
            signal_period: 信号线EMA周期，默认9
            price_key: 价格字段名，默认'close_price'
            
        Returns:
            包含MACD指标的数据列表，每个元素包含：
            - macd: MACD值
            - signal: 信号线值
            - histogram: MACD柱状图值
        """
        if not data:
            return []
        
        # 确保数据按日期升序排列
        sorted_data = self._ensure_ascending_order(data)
        
        # 提取价格序列
        prices = [self._to_float(d.get(price_key, 0)) for d in sorted_data]
        
        if len(prices) < slow_period + signal_period:
            logger.warning(f"数据不足，无法计算MACD。需要至少{slow_period + signal_period}个数据点，当前只有{len(prices)}个")
            return []
        
        # 计算快速EMA和慢速EMA
        fast_ema = self.calculate_ema(prices, fast_period)
        slow_ema = self.calculate_ema(prices, slow_period)
        
        # 计算MACD线
        macd_line = []
        min_len = min(len(fast_ema), len(slow_ema))
        for i in range(min_len):
            if fast_ema[i] is not None and slow_ema[i] is not None:
                macd_line.append(fast_ema[i] - slow_ema[i])
            else:
                macd_line.append(None)
        
        # 计算信号线（MACD的EMA）
        # 只对有效的MACD值计算EMA
        valid_macd_values = [m for m in macd_line if m is not None]
        if len(valid_macd_values) < signal_period:
            logger.warning(f"MACD有效值不足，无法计算信号线。需要至少{signal_period}个有效MACD值")
            # 返回只有MACD值的结果
            return [{
                **d,
                'macd': macd_line[i] if i < len(macd_line) else None,
                'macd_signal': None,
                'macd_histogram': None
            } for i, d in enumerate(sorted_data)]
        
        signal_line_raw = self.calculate_ema(valid_macd_values, signal_period)
        
        # 将信号线值映射回原始位置
        signal_line = []
        valid_idx = 0
        for macd_val in macd_line:
            if macd_val is not None:
                # 找到对应的信号线值
                signal_idx = valid_idx - (signal_period - 1)
                if signal_idx >= 0 and signal_idx < len(signal_line_raw):
                    signal_line.append(signal_line_raw[signal_idx])
                else:
                    signal_line.append(None)
                valid_idx += 1
            else:
                signal_line.append(None)
        
        # 计算柱状图并构建结果
        result = []
        for i, d in enumerate(sorted_data):
            macd_val = macd_line[i] if i < len(macd_line) else None
            signal_val = signal_line[i] if i < len(signal_line) else None
            
            histogram = None
            if macd_val is not None and signal_val is not None:
                histogram = macd_val - signal_val
            
            result.append({
                **d,
                'macd': macd_val,
                'macd_signal': signal_val,
                'macd_histogram': histogram
            })
        
        return result
    
    def calculate_kdj(
        self,
        data: List[Dict],
        rsv_period: int = 9,
        k_smooth: int = 3,
        d_smooth: int = 3,
        high_key: str = 'high_price',
        low_key: str = 'low_price',
        close_key: str = 'close_price'
    ) -> List[Dict]:
        """
        计算KDJ指标
        
        RSV = (收盘价 - 最低价) / (最高价 - 最低价) * 100
        K值 = (2/3) * 前一日K值 + (1/3) * 当日RSV
        D值 = (2/3) * 前一日D值 + (1/3) * 当日K值
        J值 = 3 * K值 - 2 * D值
        
        Args:
            data: 股票历史数据列表，必须包含high_key, low_key, close_key字段
            rsv_period: RSV计算周期，默认9
            k_smooth: K值平滑周期，默认3
            d_smooth: D值平滑周期，默认3
            high_key: 最高价字段名，默认'high_price'
            low_key: 最低价字段名，默认'low_price'
            close_key: 收盘价字段名，默认'close_price'
            
        Returns:
            包含KDJ指标的数据列表，每个元素包含：
            - k: K值
            - d: D值
            - j: J值
        """
        if not data:
            return []
        
        # 确保数据按日期升序排列
        sorted_data = self._ensure_ascending_order(data)
        
        if len(sorted_data) < rsv_period:
            logger.warning(f"数据不足，无法计算KDJ。需要至少{rsv_period}个数据点，当前只有{len(sorted_data)}个")
            return []
        
        # 提取价格序列
        highs = [self._to_float(d.get(high_key, 0)) for d in sorted_data]
        lows = [self._to_float(d.get(low_key, 0)) for d in sorted_data]
        closes = [self._to_float(d.get(close_key, 0)) for d in sorted_data]
        
        # 计算RSV
        rsv_values = []
        for i in range(len(sorted_data)):
            if i < rsv_period - 1:
                rsv_values.append(None)
            else:
                period_highs = highs[i - rsv_period + 1:i + 1]
                period_lows = lows[i - rsv_period + 1:i + 1]
                period_high = max(period_highs)
                period_low = min(period_lows)
                
                if period_high == period_low:
                    rsv = 50.0  # 避免除零
                else:
                    rsv = ((closes[i] - period_low) / (period_high - period_low)) * 100
                rsv_values.append(rsv)
        
        # 计算K值和D值
        k_values = []
        d_values = []
        
        for i, rsv in enumerate(rsv_values):
            if rsv is None:
                k_values.append(None)
                d_values.append(None)
            else:
                if i == rsv_period - 1:
                    # 第一个K值等于RSV
                    k = rsv
                else:
                    # K值平滑
                    prev_k = k_values[-1] if k_values else 50.0
                    k = (2.0 / (k_smooth + 1)) * prev_k + (1.0 / (k_smooth + 1)) * rsv
                
                k_values.append(k)
                
                if i == rsv_period - 1:
                    # 第一个D值等于K值
                    d = k
                else:
                    # D值平滑
                    prev_d = d_values[-1] if d_values else 50.0
                    d = (2.0 / (d_smooth + 1)) * prev_d + (1.0 / (d_smooth + 1)) * k
                
                d_values.append(d)
        
        # 计算J值并构建结果
        result = []
        for i, d in enumerate(sorted_data):
            k_val = k_values[i] if i < len(k_values) else None
            d_val = d_values[i] if i < len(d_values) else None
            
            j_val = None
            if k_val is not None and d_val is not None:
                j_val = 3 * k_val - 2 * d_val
            
            result.append({
                **d,
                'kdj_k': k_val,
                'kdj_d': d_val,
                'kdj_j': j_val
            })
        
        return result
    
    def calculate_rsi(
        self,
        data: List[Dict],
        period: int = 14,
        close_key: str = 'close_price'
    ) -> List[Dict]:
        """
        计算RSI（相对强弱指标）
        
        RSI = 100 - (100 / (1 + RS))
        RS = 平均上涨幅度 / 平均下跌幅度
        
        使用EMA方法计算平均上涨和下跌幅度
        
        Args:
            data: 股票历史数据列表，必须包含close_key字段
            period: RSI计算周期，默认14
            close_key: 收盘价字段名，默认'close_price'
            
        Returns:
            包含RSI指标的数据列表，每个元素包含：
            - rsi: RSI值（0-100之间）
        """
        if not data:
            return []
        
        # 确保数据按日期升序排列
        sorted_data = self._ensure_ascending_order(data)
        
        if len(sorted_data) < period + 1:
            logger.warning(f"数据不足，无法计算RSI。需要至少{period + 1}个数据点，当前只有{len(sorted_data)}个")
            return []
        
        # 提取收盘价序列
        closes = [self._to_float(d.get(close_key, 0)) for d in sorted_data]
        
        # 计算价格变化
        changes = []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i - 1]
            changes.append(change)
        
        # 分离上涨和下跌
        gains = [change if change > 0 else 0.0 for change in changes]
        losses = [-change if change < 0 else 0.0 for change in changes]
        
        # 计算平均上涨和平均下跌（使用EMA平滑）
        avg_gains = self.calculate_ema(gains, period)
        avg_losses = self.calculate_ema(losses, period)
        
        # 计算RSI
        rsi_values = []
        for i in range(len(avg_gains)):
            if avg_gains[i] is None or avg_losses[i] is None:
                rsi_values.append(None)
            else:
                if avg_losses[i] == 0:
                    # 如果平均下跌为0，RSI为100
                    rsi = 100.0
                else:
                    rs = avg_gains[i] / avg_losses[i]
                    rsi = 100.0 - (100.0 / (1.0 + rs))
                rsi_values.append(rsi)
        
        # 构建结果（第一个数据点没有变化，RSI为None）
        result = []
        for i, d in enumerate(sorted_data):
            if i == 0:
                # 第一个数据点没有RSI值
                rsi_val = None
            else:
                rsi_val = rsi_values[i - 1] if (i - 1) < len(rsi_values) else None
            
            result.append({
                **d,
                'rsi': rsi_val
            })
        
        return result
    
    def calculate_all_indicators(
        self,
        data: List[Dict],
        macd_params: Optional[Tuple[int, int, int]] = None,
        kdj_params: Optional[Tuple[int, int, int]] = None,
        rsi_period: Optional[int] = None
    ) -> List[Dict]:
        """
        计算所有技术指标
        
        Args:
            data: 股票历史数据列表
            macd_params: MACD参数元组 (fast_period, slow_period, signal_period)，默认(12, 26, 9)
            kdj_params: KDJ参数元组 (rsv_period, k_smooth, d_smooth)，默认(9, 3, 3)
            rsi_period: RSI周期，默认14
            
        Returns:
            包含所有技术指标的数据列表
        """
        if macd_params is None:
            macd_params = (12, 26, 9)
        if kdj_params is None:
            kdj_params = (9, 3, 3)
        if rsi_period is None:
            rsi_period = 14
        
        result = data.copy()
        
        # 计算MACD
        try:
            result = self.calculate_macd(
                result,
                fast_period=macd_params[0],
                slow_period=macd_params[1],
                signal_period=macd_params[2]
            )
        except Exception as e:
            logger.error(f"计算MACD失败: {e}", exc_info=True)
        
        # 计算KDJ
        try:
            result = self.calculate_kdj(
                result,
                rsv_period=kdj_params[0],
                k_smooth=kdj_params[1],
                d_smooth=kdj_params[2]
            )
        except Exception as e:
            logger.error(f"计算KDJ失败: {e}", exc_info=True)
        
        # 计算RSI
        try:
            result = self.calculate_rsi(
                result,
                period=rsi_period
            )
        except Exception as e:
            logger.error(f"计算RSI失败: {e}", exc_info=True)
        
        return result

