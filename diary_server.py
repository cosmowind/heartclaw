"""
日记查看服务器
提供日记页面和数据文件的访问
"""
import http.server
import socketserver
import os
from pathlib import Path

PORT = 18766
DIARY_ROOT = Path(__file__).parent

class DiaryHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIARY_ROOT), **kwargs)

    def end_headers(self):
        # 添加 CORS 头
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_GET(self):
        # 根路径重定向到日记页面
        if self.path == '/' or self.path == '':
            self.path = '/show/diary.html'
        return super().do_GET()

if __name__ == '__main__':
    with socketserver.TCPServer(("", PORT), DiaryHandler) as httpd:
        print(f"📔 日记查看服务器启动")
        print(f"   访问地址: http://localhost:{PORT}")
        print(f"   日记页面: http://localhost:{PORT}/show/diary.html")
        httpd.serve_forever()
