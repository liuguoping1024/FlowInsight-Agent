-- FlowInsight-Agent 数据库扩展
-- 添加用户设置、LLM配置等表

USE flowinsight;

-- 用户设置表（主题、偏好等）
CREATE TABLE IF NOT EXISTS user_settings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用户ID',
    theme VARCHAR(20) DEFAULT 'system' COMMENT '主题：light/dark/system',
    language VARCHAR(10) DEFAULT 'zh-CN' COMMENT '语言',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_id (user_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户设置表';

-- LLM配置表
CREATE TABLE IF NOT EXISTS user_llm_configs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用户ID',
    provider VARCHAR(50) NOT NULL COMMENT '提供商：deepseek/chatgpt',
    api_url VARCHAR(255) COMMENT 'API URL',
    model VARCHAR(100) COMMENT '模型名称',
    api_key VARCHAR(500) COMMENT 'API Key（加密存储）',
    is_enabled BOOLEAN DEFAULT FALSE COMMENT '是否启用',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_provider (user_id, provider),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_provider (provider)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户LLM配置表';

-- 推荐股票表（每日推荐）
CREATE TABLE IF NOT EXISTS recommended_stocks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    recommend_date DATE NOT NULL COMMENT '推荐日期',
    stock_code VARCHAR(20) NOT NULL COMMENT '股票代码',
    market_code INT NOT NULL COMMENT '市场代码（0=深市，1=沪市）',
    stock_name VARCHAR(100) NOT NULL COMMENT '股票名称',
    secid VARCHAR(20) NOT NULL COMMENT '完整代码',
    current_price DECIMAL(10, 2) COMMENT '当前价格',
    change_percent DECIMAL(10, 4) COMMENT '涨跌幅',
    total_main_inflow_10d DECIMAL(20, 2) COMMENT '10日主力净流入累计',
    total_small_inflow_10d DECIMAL(20, 2) COMMENT '10日小单净流入累计',
    volatility DECIMAL(10, 4) COMMENT '波动率',
    max_change DECIMAL(10, 4) COMMENT '最大涨跌幅',
    min_change DECIMAL(10, 4) COMMENT '最小涨跌幅',
    recommend_reasons JSON COMMENT '推荐原因（数组）',
    sort_order INT DEFAULT 0 COMMENT '排序顺序（数字越小越靠前）',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_date_stock (recommend_date, secid),
    INDEX idx_recommend_date (recommend_date),
    INDEX idx_stock_code (stock_code),
    INDEX idx_sort_order (sort_order)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='推荐股票表';

