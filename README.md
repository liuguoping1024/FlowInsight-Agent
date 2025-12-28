# FlowInsight-Agent

基于跟踪股票资金流动的智能分析系统，用于及时发现股票的投资价值。

## 项目简介

FlowInsight-Agent 是一个股票资金流动跟踪和分析系统，基于以下核心理念：

- **主力资金跟踪**：股票主力由于体量大，加入和退出都需要一定时间，通过计算资本累计和消失程度观察主力动向
- **历史数据分析**：通过历史数据初步预测股票走势
- **实时数据监控**：对股票资金加入和退出的及时速度保持警觉
- **健康度评分**：综合多个维度计算股票健康度，辅助投资决策

## 技术栈

- **后端**: Python + Flask
- **数据库**: MySQL
- **前端**: HTML + JavaScript
- **协议**: MCP (Model Context Protocol)
- **AI集成**: vLLM (未来将集成 DeepSeek)

## 系统架构

```
FlowInsight-Agent/
├── database/              # 数据库相关
│   ├── schema.sql         # 数据库结构定义
│   └── db_connection.py   # 数据库连接管理
├── services/              # 业务服务
│   ├── data_collector.py  # 数据采集服务
│   └── health_calculator.py # 健康度计算服务
├── static/                # 前端静态文件
│   └── index.html        # 主页面
├── api_server.py         # API服务器（端口8887）
├── web_server.py         # Web服务器（端口8888）
├── mcp_server.py         # MCP服务器
├── scheduler.py          # 定时任务调度器
├── config.py             # 配置文件
├── requirements.txt      # Python依赖
└── start.py             # 启动脚本
```

## 数据库设计

### 主要数据表

1. **user_groups** - 用户组表
2. **users** - 用户表
3. **user_stocks** - 用户持股和收藏表
4. **stock_list** - 个股列表（A股）
5. **stock_capital_flow_history** - 个股历史资金数据
6. **stock_health_scores** - 股票健康度评分表
7. **index_data** - 指数数据表

## 安装和配置

### 1. 环境要求

- Python 3.8+
- MySQL 5.7+
- 网络连接（用于访问东方财富API）

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 数据库配置

编辑 `config.py` 或创建 `.env` 文件：

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=Shushi6688
DB_NAME=flowinsight
```

### 4. 初始化数据库

```bash
mysql -u root -p < database/schema.sql
```

### 5. 启动服务

#### 方式一：使用启动脚本（推荐）

```bash
python start.py
```

#### 方式二：分别启动

```bash
# 终端1：启动API服务器
python api_server.py

# 终端2：启动Web服务器
python web_server.py

# 终端3：启动定时任务（可选）
python scheduler.py
```

## 功能模块

### 1. 我的股票看板

- 实时显示用户持有的股票
- 显示每只股票的健康度评分（0-100分）
- 显示趋势方向（资金流入/流出/稳定）
- 显示风险等级（低/中/高）
- 显示7日主力净流入累计

### 2. 实时资金流向

- 显示前20名资金流向最大的股票
- 支持按主力净流入排序
- 支持按涨跌幅排序
- 显示主要指数实时数据
- 自动刷新（每30秒）

### 3. 历史资金流量

- 查询个股历史资金数据
- 显示主力净流入、超大单、大单等数据
- 支持数据同步功能
- 本地数据库缓存，减少API请求

## API接口

### 用户相关

- `GET /api/users` - 获取用户列表
- `GET /api/user-groups` - 获取用户组列表

### 股票相关

- `GET /api/stocks` - 获取股票列表
- `GET /api/stocks/<secid>/health` - 获取股票健康度
- `GET /api/stocks/<secid>/history` - 获取股票历史数据

### 实时数据

- `GET /api/realtime/capital-flow` - 获取实时资金流向
- `GET /api/realtime/index` - 获取实时指数数据

### 数据同步

- `POST /api/sync/stock-list` - 同步个股列表
- `POST /api/sync/stock-history/<secid>` - 同步个股历史数据
- `POST /api/sync/index` - 同步指数数据

## MCP接口

MCP服务器提供以下工具：

- `get_stock_list` - 获取股票列表
- `get_stock_health` - 获取股票健康度
- `get_stock_history` - 获取股票历史数据
- `get_realtime_capital_flow` - 获取实时资金流向
- `get_index_data` - 获取指数数据
- `analyze_stock_trend` - 分析股票趋势
- `compare_stocks` - 比较多只股票

## 健康度评分规则

健康度评分（0-100分）由以下维度组成：

1. **主力资金流入情况（40分）**
   - 7日累计流入 > 1亿：40分
   - 7日累计流入 > 5000万：30分
   - 7日累计流入 > 0：20分
   - 否则：0分

2. **资金流入趋势（30分）**
   - 加速流入：30分
   - 连续3天流入：25分
   - 连续2天流入：15分
   - 其他：5分

3. **价格表现（20分）**
   - 平均涨跌幅 > 3%：20分
   - 平均涨跌幅 > 1%：15分
   - 平均涨跌幅 > 0%：10分
   - 其他：5分

4. **成交量活跃度（10分）**
   - 平均换手率 > 5%：10分
   - 平均换手率 > 3%：7分
   - 平均换手率 > 1%：5分
   - 其他：2分

## 数据来源

数据来源于东方财富API：

- 个股列表：`https://push2.eastmoney.com/api/qt/clist/get`
- 实时资金流向：`https://push2.eastmoney.com/api/qt/clist/get`
- 历史资金数据：`https://push2his.eastmoney.com/api/qt/stock/fflow/daykline/get`
- 指数数据：`https://push2.eastmoney.com/api/qt/ulist.np/get`

## 注意事项

1. **API限流**：为避免被网站风控，系统会优先使用数据库缓存的数据
2. **数据同步**：建议在非交易时间进行大量数据同步
3. **定时任务**：默认每30分钟同步一次指数数据，每天凌晨2点同步个股列表

## 未来计划

- [ ] 集成MACD、KDJ等技术指标监控
- [ ] 集成DeepSeek AI进行数据分析和预测
- [ ] 增加更多技术分析指标
- [ ] 支持策略回测功能
- [ ] 增加移动端适配

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交Issue。
