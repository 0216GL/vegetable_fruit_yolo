#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
首页动画性能补丁 —— 只调参数，不改画法，视觉几乎无差。

补的是 index.html 里两段 canvas 粒子动画：
  startAtmosphere()  雾气   #environment-mist
  startSceneSnow()   雪花   #scene-snow

改什么（每一条都是"少算一点"，不改颜色/形状/轨迹）：
  1. canvas 背衬分辨率 devicePixelRatio 上限 1.5/1.4 → 1.0
     （像素数少 2.25 倍；1x 屏无差别，2x 屏雪花边缘略柔）
  2. 雪花数量 68/52/11 → 48/36/9（约 -29%）
  3. 两段循环都加 32ms 闸门 → 30fps（雪是慢速飘落，30fps 看不出区别）
  4. 雾气每帧写 2 个 CSS 变量（--sun-breath/--sky-breath）→ 量化到千分之一，
     只有真的变了才写。这是"样式重算"开销的大头，改完从每秒上百次降到约 1 次。

用法：
    python patch_perf.py            # 应用（幂等，重复跑不会叠加）
    python patch_perf.py --restore  # 撤回，回到队友交付的原样
    python patch_perf.py --check    # 只看当前是否已打补丁

首次应用会把当时的状态备份成 dist/index.pre-perf.html。
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # noqa: BLE001
    pass

WEB_DIR = Path(__file__).resolve().parent
INDEX = WEB_DIR / "dist" / "index.html"
BACKUP = WEB_DIR / "dist" / "index.pre-perf.html"

# (说明, 原文, 补丁后)
PATCHES: list[tuple[str, str, str]] = [
    (
        "雾气：dpr 上限 1.4 → 1.0",
        "const dpr=Math.min(devicePixelRatio,1.4),w=canvas.clientWidth",
        "const dpr=Math.min(devicePixelRatio,1),w=canvas.clientWidth",
    ),
    (
        "雾气：加 30fps 闸门 + CSS 变量去重变量",
        "let raf=0,last=performance.now(),time=0,active=true;",
        "let raf=0,last=performance.now(),time=0,active=true,"
        "lastDraw=0,lastSun=-1,lastSky=-1;",
    ),
    (
        "雾气：每帧限一次（32ms）",
        "function frame(now){if(!active)return;raf=requestAnimationFrame(frame);"
        "let dt=Math.min((now-last)/1000,.05);last=now;",
        "function frame(now){if(!active)return;raf=requestAnimationFrame(frame);"
        "if(now-lastDraw<32)return;lastDraw=now;"
        "let dt=Math.min((now-last)/1000,.05);last=now;",
    ),
    (
        "雾气：CSS 变量量化后再写（大幅减少样式重算）",
        "hero.style.setProperty('--sun-breath',String(.035+breath*.045));"
        "hero.style.setProperty('--sky-breath',String(.025+breath*.025))",
        "const sb=Math.round((.035+breath*.045)*1000)/1000,"
        "kb=Math.round((.025+breath*.025)*1000)/1000;"
        "if(sb!==lastSun){lastSun=sb;hero.style.setProperty('--sun-breath',String(sb))}"
        "if(kb!==lastSky){lastSky=kb;hero.style.setProperty('--sky-breath',String(kb))}",
    ),
    (
        "雪花：dpr 上限 1.5 → 1.0",
        "const dpr=Math.min(devicePixelRatio||1,1.5);canvas.width=Math.round(w*dpr);"
        "canvas.height=Math.round(h*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);flakes=[];",
        "const dpr=Math.min(devicePixelRatio||1,1);canvas.width=Math.round(w*dpr);"
        "canvas.height=Math.round(h*dpr);ctx.setTransform(dpr,0,0,dpr,0,0);flakes=[];",
    ),
    (
        "雪花：三层数量 68/52/11 → 48/36/9",
        "[[68,.5,1,15,25,.25,.43],[52,1.05,1.95,28,46,.43,.68],[11,2.6,4.5,48,74,.29,.47]]",
        "[[48,.5,1,15,25,.25,.43],[36,1.05,1.95,28,46,.43,.68],[9,2.6,4.5,48,74,.29,.47]]",
    ),
    (
        "雪花：加 30fps 闸门变量",
        "let w=0,h=0,flakes=[],last=performance.now(),time=0,visibleTime=0,seed=137;",
        "let w=0,h=0,flakes=[],last=performance.now(),time=0,visibleTime=0,seed=137,"
        "lastDraw=0;",
    ),
    (
        "雪花：每帧限一次（32ms）",
        "function tick(now){requestAnimationFrame(tick);"
        "const dt=Math.min((now-last)/1000,.05);last=now;",
        "function tick(now){requestAnimationFrame(tick);"
        "if(now-lastDraw<32)return;lastDraw=now;"
        "const dt=Math.min((now-last)/1000,.05);last=now;",
    ),
]


def write_with_retry(path: Path, text: str, retries: int = 8) -> None:
    for i in range(retries):
        try:
            path.write_text(text, encoding="utf-8", newline="")
            return
        except OSError as e:
            if i == retries - 1:
                raise
            print(f"  写入被占用，重试 {i + 1}/{retries}：{e}")
            time.sleep(0.4)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--restore", action="store_true", help="回到打补丁之前")
    ap.add_argument("--check", action="store_true", help="只检查状态")
    args = ap.parse_args()

    if not INDEX.exists():
        print(f"[错误] 找不到 {INDEX}")
        return 1

    html = INDEX.read_text(encoding="utf-8")
    done = sum(1 for _, _, new in PATCHES if new in html)

    if args.check:
        print(f"已应用 {done}/{len(PATCHES)} 条补丁")
        for label, old, new in PATCHES:
            state = "已打" if new in html else ("可打" if old in html else "?? 找不到原文")
            print(f"  [{state}] {label}")
        return 0

    if args.restore:
        if not BACKUP.exists():
            print("[错误] 没有备份文件，无法还原。")
            return 1
        shutil.copy2(BACKUP, INDEX)
        print(f"[完成] 已还原到打补丁之前（{INDEX.stat().st_size} 字节）")
        return 0

    if done == len(PATCHES):
        print("[跳过] 补丁已经全部应用过了。")
        return 0

    if not BACKUP.exists():
        shutil.copy2(INDEX, BACKUP)
        print(f"[备份] {BACKUP.name}（{BACKUP.stat().st_size} 字节）")

    for label, old, new in PATCHES:
        if new in html:
            print(f"  [跳过] {label}（已应用）")
            continue
        cnt = html.count(old)
        if cnt != 1:
            print(f"  [失败] {label}：原文命中 {cnt} 次（应为 1 次），为安全起见中止")
            return 2
        html = html.replace(old, new, 1)
        print(f"  [应用] {label}")

    write_with_retry(INDEX, html)
    print(f"\n[完成] 补丁已写入 {INDEX}")
    print("       自测：刷新页面看首页雪花/雾气是否还在、卡不卡。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
