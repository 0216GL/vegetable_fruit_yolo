#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
把 AI 桥接脚本挂进 dist/index.html —— 按【字节】操作，除插入的那一行外，
原始文件一个字节都不改（保留原文件的 CRLF / LF、BOM 与否、编码）。

用法（项目根目录执行）：
    D:\\Anaconda\\envs\\yolo\\python.exe frontend\\web\\inject_ai_bridge.py
    D:\\Anaconda\\envs\\yolo\\python.exe frontend\\web\\inject_ai_bridge.py --remove   # 撤销
    D:\\Anaconda\\envs\\yolo\\python.exe frontend\\web\\inject_ai_bridge.py --restore  # 从备份还原

行为：
  * 在 </body> 前插入 <script src="assets/ai-bridge.js"></script>
  * 幂等：重复跑不会插第二次
  * 首次注入把原始 index.html 备份为 dist/index.original.html
  * 原页面 HTML / CSS / 视觉一律不动 —— 想恢复原样就 --remove 或 --restore
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

# Windows 控制台默认 GBK，打中文/符号会 UnicodeEncodeError —— 先兜住
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

WEB_DIR = Path(__file__).resolve().parent
DIST = WEB_DIR / "dist"
INDEX = DIST / "index.html"
BACKUP = DIST / "index.original.html"
SCRIPT = DIST / "assets" / "ai-bridge.js"
MARK = b'src="assets/ai-bridge.js"'


def write_bytes_with_retry(path: Path, data: bytes, retries: int = 8) -> None:
    """浏览器/编辑器有时占着文件，Windows 报 EIO(Win32 32)，重试几次即可。"""
    for i in range(retries):
        try:
            path.write_bytes(data)
            return
        except OSError as e:
            if i == retries - 1:
                raise
            print(f"  写入被占用，重试 {i + 1}/{retries}：{e}")
            time.sleep(0.4)


def newline_of(data: bytes) -> bytes:
    return b"\r\n" if b"\r\n" in data else b"\n"


def build_tag(nl: bytes) -> bytes:
    return nl + b'  <script src="assets/ai-bridge.js"></script>'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--remove", action="store_true", help="只删掉桥接那一行")
    ap.add_argument("--restore", action="store_true", help="从 index.original.html 整份还原")
    args = ap.parse_args()

    if not INDEX.exists():
        print(f"[错误] 找不到 {INDEX}")
        return 1

    data = INDEX.read_bytes()

    if args.restore:
        if not BACKUP.exists():
            print("[错误] 没有备份文件，无法还原。")
            return 1
        write_bytes_with_retry(INDEX, BACKUP.read_bytes())
        print(f"[完成] 已从 {BACKUP.name} 还原（{INDEX.stat().st_size} 字节）")
        return 0

    if args.remove:
        if MARK not in data:
            print("[跳过] 没找到桥接标签，本来就是原样。")
            return 0
        out = b"".join(
            ln for ln in data.splitlines(keepends=True) if MARK not in ln
        )
        write_bytes_with_retry(INDEX, out)
        print(f"[完成] 已移除桥接标签（{len(data)} → {len(out)} 字节）")
        return 0

    if not SCRIPT.exists():
        print(f"[错误] 找不到 {SCRIPT.name}，先放好桥接脚本。")
        return 1

    if MARK in data:
        print("[跳过] 已经注入过了。")
        return 0

    close = data.rfind(b"</body>")
    if close < 0:
        print("[错误] index.html 里找不到 </body>，不敢乱插。")
        return 1

    if not BACKUP.exists():
        shutil.copy2(INDEX, BACKUP)
        print(f"[备份] {BACKUP.name}（{BACKUP.stat().st_size} 字节）")

    tag = build_tag(newline_of(data))
    out = data[:close] + tag + data[close:]
    write_bytes_with_retry(INDEX, out)

    # ---- 自检：把插入的部分抠掉，必须和备份逐字节一致 ----
    ok = "（无备份可比）"
    if BACKUP.exists():
        orig = BACKUP.read_bytes()
        restored = out[:close] + out[close + len(tag):]
        ok = "[OK] 逐字节一致" if restored == orig else "[FAIL] 有额外改动，请检查！"

    print(f"[完成] 已注入 {len(out) - len(data)} 字节，文件 {len(data)} → {len(out)} 字节")
    print(f"[自检] 去掉桥接行后与原始文件比对：{ok}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
