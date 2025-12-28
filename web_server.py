"""
Web服务器（HTML前端）
端口：8888
"""
from flask import Flask, send_from_directory
import os

app = Flask(__name__, static_folder='static')


@app.route('/')
def index():
    """首页"""
    return send_from_directory('static', 'index.html')


@app.route('/<path:path>')
def static_files(path):
    """静态文件"""
    return send_from_directory('static', path)


if __name__ == '__main__':
    print("启动Web服务器，端口: 8888")
    print("访问地址: http://localhost:8888")
    app.run(host='0.0.0.0', port=8888, debug=True)

