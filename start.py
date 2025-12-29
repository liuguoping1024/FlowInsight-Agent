"""
启动脚本
同时启动API服务器和Web服务器
"""
import subprocess
import sys
import os
import time
import signal
import platform

def start_server(script_name, port):
    """启动服务器"""
    print(f"启动 {script_name}，端口: {port}")
    # Windows上不使用PIPE，让输出直接显示，这样Ctrl+C才能正常工作
    if platform.system() == 'Windows':
        process = subprocess.Popen(
            [sys.executable, script_name],
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if hasattr(subprocess, 'CREATE_NEW_PROCESS_GROUP') else 0
        )
    else:
        process = subprocess.Popen(
            [sys.executable, script_name]
        )
    return process

def signal_handler(sig, frame):
    """处理退出信号"""
    print("\n正在关闭服务器...")
    if 'api_process' in globals():
        try:
            if platform.system() == 'Windows':
                api_process.terminate()
            else:
                api_process.send_signal(signal.SIGTERM)
        except:
            pass
    if 'web_process' in globals():
        try:
            if platform.system() == 'Windows':
                web_process.terminate()
            else:
                web_process.send_signal(signal.SIGTERM)
        except:
            pass
    
    # 等待进程结束
    time.sleep(1)
    
    # 如果还没结束，强制杀死
    if 'api_process' in globals():
        try:
            api_process.kill()
        except:
            pass
    if 'web_process' in globals():
        try:
            web_process.kill()
        except:
            pass
    
    print("服务器已关闭")
    sys.exit(0)

if __name__ == '__main__':
    # 注册信号处理器
    if platform.system() != 'Windows':
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
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
        # Windows上使用轮询方式等待
        if platform.system() == 'Windows':
            while True:
                # 检查进程是否还在运行
                if api_process.poll() is not None:
                    print(f"API服务器进程已退出，退出码: {api_process.returncode}")
                    break
                if web_process.poll() is not None:
                    print(f"Web服务器进程已退出，退出码: {web_process.returncode}")
                    break
                time.sleep(0.5)
        else:
            # 非Windows系统，等待进程
            api_process.wait()
            web_process.wait()
    except KeyboardInterrupt:
        signal_handler(None, None)

