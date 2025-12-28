"""
Web服务器（HTML前端）
端口：8888
"""
from flask import Flask, send_from_directory
import os

app = Flask(__name__, static_folder='static')


@app.route('/')
def index():
    """首页 - 重定向到登录页"""
    from flask import redirect
    return redirect('/login.html')

@app.route('/dashboard.html')
def dashboard():
    """我的看板页面"""
    return send_from_directory('static', 'dashboard.html')

@app.route('/settings.html')
def settings():
    """设置页面"""
    return send_from_directory('static', 'settings.html')


@app.route('/<path:path>')
def static_files(path):
    """静态文件"""
    return send_from_directory('static', path)


if __name__ == '__main__':
    print("启动Web服务器，端口: 8888")
    print("访问地址: http://localhost:8888")
    app.run(host='0.0.0.0', port=8888, debug=True)

