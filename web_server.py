"""
Web服务器（HTML前端）
端口：8888
"""
from flask import Flask, send_from_directory, request
import os
import logging
import logging.handlers

# 创建logs目录
if not os.path.exists('logs'):
    os.makedirs('logs')

# 配置日志 - 同时输出到控制台和文件
log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
date_format = '%Y-%m-%d %H:%M:%S'

# 文件日志处理器 - 按日期轮转，保留30天
file_handler = logging.handlers.TimedRotatingFileHandler(
    filename='logs/web_server.log',
    when='midnight',
    interval=1,
    backupCount=30,
    encoding='utf-8'
)
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(log_format, date_format))

# 控制台日志处理器
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(logging.Formatter(log_format, date_format))

# 配置根日志记录器
root_logger = logging.getLogger()
root_logger.setLevel(logging.INFO)
root_logger.addHandler(file_handler)
root_logger.addHandler(console_handler)

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')


@app.before_request
def log_request():
    """记录每个请求"""
    logger.info(f"请求: {request.method} {request.path}")

@app.route('/')
def index():
    """首页 - 重定向到登录页"""
    from flask import redirect
    logger.info("访问首页，重定向到登录页")
    return redirect('/login.html')

@app.route('/dashboard.html')
def dashboard():
    """我的看板页面"""
    logger.info("访问dashboard页面")
    return send_from_directory('static', 'dashboard.html')

@app.route('/settings.html')
def settings():
    """设置页面"""
    logger.info("访问settings页面")
    return send_from_directory('static', 'settings.html')


@app.route('/<path:path>')
def static_files(path):
    """静态文件"""
    logger.debug(f"请求静态文件: {path}")
    return send_from_directory('static', path)


if __name__ == '__main__':
    logger.info("启动Web服务器，端口: 8888")
    logger.info("访问地址: http://localhost:8888")
    app.run(host='0.0.0.0', port=8888, debug=True)

