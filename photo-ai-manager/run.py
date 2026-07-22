#!/usr/bin/env python3
"""启动 AI 照片分类管理服务。

    python run.py               # 仅本机访问 http://localhost:8000
    python run.py --lan         # 局域网访问：手机/平板浏览器打开 http://<本机IP>:8000
    python run.py --port 9000   # 自定义端口
"""
import argparse
import socket

import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--lan", action="store_true", help="允许局域网设备（手机/平板）访问")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    host = "0.0.0.0" if args.lan else "127.0.0.1"
    if args.lan:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            print(f"手机/平板请在浏览器打开: http://{ip}:{args.port}")
        except OSError:
            pass
    uvicorn.run("app.main:app", host=host, port=args.port)
