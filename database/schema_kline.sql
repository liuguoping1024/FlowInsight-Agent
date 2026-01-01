-- 日K线数据表结构设计
-- 专门用于存储日K线数据，与 stock_capital_flow_history 表通过 (secid, trade_date) 联合查询

-- 8. 股票日K线历史数据表
CREATE TABLE IF NOT EXISTS stock_day_lines_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    market_code INT NOT NULL COMMENT '市场代码（0=深市，1=沪市）',
    secid VARCHAR(20) NOT NULL COMMENT '完整代码（market_code.stock_code）',
    trade_date DATE NOT NULL COMMENT '交易日期',
    -- K线数据字段（来自API的f52-f61）
    open_price DECIMAL(10, 2) COMMENT '开盘价(f52)',
    close_price DECIMAL(10, 2) COMMENT '收盘价(f53)',
    high_price DECIMAL(10, 2) COMMENT '最高价(f54)',
    low_price DECIMAL(10, 2) COMMENT '最低价(f55)',
    volume BIGINT COMMENT '成交量(f56，单位：手)',
    amount DECIMAL(20, 2) COMMENT '成交额(f57，单位：元)',
    amplitude DECIMAL(10, 4) COMMENT '振幅(f58，单位：%)',
    change_percent DECIMAL(10, 4) COMMENT '涨跌幅(f59，单位：%)',
    change_amount DECIMAL(10, 2) COMMENT '涨跌额(f60)',
    turnover_rate DECIMAL(10, 4) COMMENT '换手率(f61，单位：%)',
    raw_data JSON COMMENT '原始API数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    -- 唯一索引：同一股票、同一日期只能有一条日K线记录
    -- 与 stock_capital_flow_history 表的唯一键结构一致，便于联合查询
    UNIQUE KEY uk_stock_date (secid, trade_date),
    -- 索引设计（优化联合查询性能）
    INDEX idx_stock_code (stock_code),
    INDEX idx_secid (secid),
    INDEX idx_trade_date (trade_date),
    INDEX idx_secid_date (secid, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票日K线历史数据表';
