"""
启动脚本
同时启动API服务器和Web服务器
"""
import subprocess
import sys
import os
import time

def start_server(script_name, port):
    """启动服务器"""
    print(f"启动 {script_name}，端口: {port}")
    process = subprocess.Popen(
        [sys.executable, script_name],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    return process

if __name__ == '__main__':
    print("=" * 50)
    print("FlowInsight-Agent 启动中...")
    print("=" * 50)
    
    # 启动API服务器
    api_process = start_server('api_server.py', 8887)
    time.sleep(2)
    
    # 启动Web服务器
    web_process = start_server('web_server.py', 8888)
    time.sleep(2)
    
    print("\n" + "=" * 50)
    print("服务器启动完成！")
    print("=" * 50)
    print("API服务器: http://localhost:8887")
    print("Web前端: http://localhost:8888")
    print("\n按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    try:
        # 等待进程
        api_process.wait()
        web_process.wait()
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
        api_process.terminate()
        web_process.terminate()
        print("服务器已关闭")

