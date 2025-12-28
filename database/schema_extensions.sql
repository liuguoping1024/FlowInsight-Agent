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

