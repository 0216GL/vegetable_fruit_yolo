# -*- coding: utf-8 -*-
"""
带正确 MIME 的静态文件服务器 —— 专门给前端 dist/ 用。

为什么需要它：
    Python 自带的 `python -m http.server` 在 Windows 上不认识 .webp，
    mimetypes.guess_type('.webp') 返回 None，于是所有 .webp 图片都以
    Content-Type: application/octet-stream 发出去。
    浏览器拿到 octet-stream 很可能拒绝渲染 -> 背景图全都不显示,
    只露出 CSS 里写的兜底底色（深青绿 #223b36 / 深蓝黑 #09151a），
    看起来就像"背景变成蓝的了"。

用法：
    python serve_frontend.py [端口] [目录]
    python serve_frontend.py 8089 dist
"""
import functools
import http.server
import mimetypes
import os
import pathlib
import socketserver
import sys

# ---- 关键：把前端用到的所有后缀都注册一遍 ----
EXTRA = {
    ".webp": "image/webp",
    ".avif": "image/avif",
    ".woff": "font/woff",
    ".woff2": "font/woff2",
    ".json": "application/json",
    ".mjs": "text/javascript",
    ".js": "text/javascript",
    ".css": "text/css",
    ".svg": "image/svg+xml",
    ".webmanifest": "application/manifest+json",
}
for ext, mime in EXTRA.items():
    mimetypes.add_type(mime, ext)
    mimetypes.add_type(mime, ext.upper())


class Handler(http.server.SimpleHTTPRequestHandler):
    # 关掉每次请求都打日志，控制台干净些；要看就改成 log_message 默认实现
    def log_message(self, fmt, *args):
        pass

    def end_headers(self):
        # 开发阶段禁用缓存，改完刷新就能看到
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8089
    root = sys.argv[2] if len(sys.argv) > 2 else "dist"

    base = pathlib.Path(root)
    if not base.is_dir():
        print("目录不存在: %s" % base.resolve())
        return 1

    handler = functools.partial(Handler, directory=str(base))

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("0.0.0.0", port), handler) as httpd:
        print("静态服务已启动")
        print("  目录: %s" % base.resolve())
        print("  地址: http://localhost:%d/" % port)
        print("  webp -> %s" % mimetypes.guess_type("a.webp")[0])
        print("  按 Ctrl+C 停止")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n已停止")
    return 0


if __name__ == "__main__":
    sys.exit(main())
