-- FlowInsight-Agent 数据库结构设计
-- MySQL数据库，用户名：root，密码：root

CREATE DATABASE IF NOT EXISTS flowinsight CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE flowinsight;

-- 1. 用户组表格
CREATE TABLE IF NOT EXISTS user_groups (
    id INT AUTO_INCREMENT PRIMARY KEY,
    group_name VARCHAR(100) NOT NULL COMMENT '用户组名称',
    description TEXT COMMENT '用户组描述',
    permissions JSON COMMENT '权限配置',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_group_name (group_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户组表';

-- 2. 用户表格
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE COMMENT '用户名',
    password_hash VARCHAR(255) NOT NULL COMMENT '密码哈希',
    email VARCHAR(100) COMMENT '邮箱',
    phone VARCHAR(20) COMMENT '手机号',
    group_id INT COMMENT '用户组ID',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否激活',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES user_groups(id) ON DELETE SET NULL,
    INDEX idx_username (username),
    INDEX idx_group_id (group_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 3. 用户持股以及收藏表格（持股的股票默认收藏）
CREATE TABLE IF NOT EXISTS user_stocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用户ID',
    stock_code VARCHAR(20) NOT NULL COMMENT '股票代码（如300274）',
    stock_market INT NOT NULL COMMENT '市场代码（0=深市，1=沪市）',
    is_holding BOOLEAN DEFAULT FALSE COMMENT '是否持股',
    is_favorite BOOLEAN DEFAULT FALSE COMMENT '是否收藏',
    holding_quantity INT DEFAULT 0 COMMENT '持股数量',
    holding_cost DECIMAL(10, 2) DEFAULT 0 COMMENT '持仓成本',
    notes TEXT COMMENT '备注',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY uk_user_stock (user_id, stock_code, stock_market),
    INDEX idx_user_id (user_id),
    INDEX idx_stock_code (stock_code),
    INDEX idx_is_holding (is_holding),
    INDEX idx_is_favorite (is_favorite)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户持股和收藏表';

-- 4. 个股列表（A股）
CREATE TABLE IF NOT EXISTS stock_list (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    market_code INT NOT NULL COMMENT '市场代码（0=深市，1=沪市）',
    stock_name VARCHAR(100) NOT NULL COMMENT '股票名称',
    secid VARCHAR(20) NOT NULL COMMENT '完整代码（market_code.stock_code）',
    total_market_cap DECIMAL(20, 2) COMMENT '总市值',
    circulating_market_cap DECIMAL(20, 2) COMMENT '流通市值',
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否活跃',
    last_sync_time TIMESTAMP COMMENT '最后同步时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_secid (secid),
    INDEX idx_stock_code (stock_code),
    INDEX idx_market_code (market_code),
    INDEX idx_stock_name (stock_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='个股列表表';

-- 5. 个股历史资金数据
CREATE TABLE IF NOT EXISTS stock_capital_flow_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    market_code INT NOT NULL COMMENT '市场代码',
    secid VARCHAR(20) NOT NULL COMMENT '完整代码',
    trade_date DATE NOT NULL COMMENT '交易日期',
    -- 资金流向字段（来自API的f51-f65）
    main_net_inflow DECIMAL(20, 2) COMMENT '主力净流入额(f52)',
    super_large_net_inflow DECIMAL(20, 2) COMMENT '超大单净流入额(f56)',
    large_net_inflow DECIMAL(20, 2) COMMENT '大单净流入额',
    medium_net_inflow DECIMAL(20, 2) COMMENT '中单净流入额',
    small_net_inflow DECIMAL(20, 2) COMMENT '小单净流入额',
    main_net_inflow_ratio DECIMAL(10, 4) COMMENT '主力净流入占比(f57)',
    close_price DECIMAL(10, 2) COMMENT '收盘价(f62)',
    change_percent DECIMAL(10, 4) COMMENT '涨跌幅(f63)',
    turnover_rate DECIMAL(10, 4) COMMENT '换手率(f65)',
    turnover_amount DECIMAL(20, 2) COMMENT '成交额(f64)',
    -- 其他字段
    open_price DECIMAL(10, 2) COMMENT '开盘价',
    high_price DECIMAL(10, 2) COMMENT '最高价',
    low_price DECIMAL(10, 2) COMMENT '最低价',
    volume BIGINT COMMENT '成交量',
    raw_data JSON COMMENT '原始API数据',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_date (secid, trade_date),
    INDEX idx_stock_code (stock_code),
    INDEX idx_trade_date (trade_date),
    INDEX idx_main_net_inflow (main_net_inflow),
    INDEX idx_secid_date (secid, trade_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='个股历史资金数据表';

-- 6. 股票健康度评分表（用于看板）
CREATE TABLE IF NOT EXISTS stock_health_scores (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    stock_code VARCHAR(20) NOT NULL,
    market_code INT NOT NULL,
    secid VARCHAR(20) NOT NULL,
    score_date DATE NOT NULL COMMENT '评分日期',
    health_score DECIMAL(5, 2) COMMENT '健康度评分（0-100）',
    score_details JSON COMMENT '评分详情',
    main_net_inflow_7d DECIMAL(20, 2) COMMENT '7日主力净流入累计',
    main_net_inflow_30d DECIMAL(20, 2) COMMENT '30日主力净流入累计',
    trend_direction VARCHAR(20) COMMENT '趋势方向（inflow/outflow/stable）',
    risk_level VARCHAR(20) COMMENT '风险等级（low/medium/high）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_stock_score_date (secid, score_date),
    INDEX idx_score_date (score_date),
    INDEX idx_health_score (health_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票健康度评分表';

-- 7. 指数数据表
CREATE TABLE IF NOT EXISTS index_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    index_code VARCHAR(20) NOT NULL COMMENT '指数代码',
    index_name VARCHAR(100) NOT NULL COMMENT '指数名称',
    secid VARCHAR(20) NOT NULL COMMENT '完整代码',
    current_value DECIMAL(15, 2) COMMENT '当前值',
    change_value DECIMAL(15, 2) COMMENT '涨跌值',
    change_percent DECIMAL(10, 4) COMMENT '涨跌幅',
    total_amount DECIMAL(20, 2) COMMENT '总成交额',
    up_count INT COMMENT '上涨家数',
    down_count INT COMMENT '下跌家数',
    flat_count INT COMMENT '平盘家数',
    update_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_index_code (index_code),
    INDEX idx_update_time (update_time)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='指数数据表';

-- 初始化数据表（用于快速初始化部分数据）

-- 插入默认用户组
INSERT INTO user_groups (group_name, description, permissions) VALUES
('admin', '管理员组', '{"all": true}'),
('user', '普通用户组', '{"view": true, "trade": true}'),
('guest', '访客组', '{"view": true}');

-- 插入默认用户（密码：admin123，实际使用时需要哈希）
INSERT INTO users (username, password_hash, email, group_id) VALUES
('admin', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyY5Y5Y5Y5Y5', 'admin@flowinsight.com', 1),
('testuser', '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyY5Y5Y5Y5', 'test@flowinsight.com', 2);

-- 插入主要指数
INSERT INTO index_data (index_code, index_name, secid) VALUES
('000001', '上证指数', '1.000001'),
('399001', '深证成指', '0.399001'),
('399006', '创业板指', '0.399006'),
('000688', '科创50', '1.000688'),
('000016', '上证50', '1.000016'),
('000300', '沪深300', '1.000300'),
('000905', '中证500', '1.000905'),
('000852', '中证1000', '1.000852'),
('399005', '中小板指', '0.399005'),
('399102', '创业板综', '0.399102');

-- 插入上证指数和深证成指到 stock_list 表（用于资金流向分析）
INSERT INTO stock_list (stock_code, market_code, stock_name, secid, is_active) VALUES
('000001', 1, '上证指数', '1.000001', 1),
('399001', 0, '深证成指', '0.399001', 1)
ON DUPLICATE KEY UPDATE
    stock_name = VALUES(stock_name),
    is_active = VALUES(is_active),
    updated_at = NOW();

