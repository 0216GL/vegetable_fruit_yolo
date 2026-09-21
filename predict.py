# -*- coding: utf-8 -*-
"""
图片 / 文件夹 测试脚本
================================================================================

【干什么】
    给模型一张图或一个文件夹，看它认成什么。不训练、不用摄像头。

【怎么用】
    python predict.py                          测默认目录（见 config.DEFAULT_INPUT）
    python predict.py "D:\\照片\\柿子.jpg"       测单张
    python predict.py "D:\\照片\\待测"           测整个文件夹
    python predict.py -m species "..."          临时换模型

【文件夹测试会自动算准确率】
    如果文件夹里是按类别分的子文件夹（如 dataset_persimmon/val/1_unripe），
    就逐类统计准确率，并列出判错的图 —— 这是最直观的"模型行不行"的检验。

【产物】
    模型    config.MODELS[ACTIVE_MODEL]["weights"]
================================================================================
"""

import sys
from pathlib import Path

import config
import engine


def pad(s, width):
    """
    按【显示宽度】补空格。
    中文字符占 2 列，str.ljust 按字符数算，会错位。
    """
    w = sum(2 if ord(c) > 0x2E80 else 1 for c in s)
    return s + " " * max(0, width - w)


# ==============================================================================
# 命令行解析
# ==============================================================================
def parse_args(argv):
    """
    返回 (目标路径, 模型key)
    支持：python predict.py [-m 模型key] [路径]
    """
    args = list(argv)
    key = None

    if "-m" in args:
        i = args.index("-m")
        if i + 1 >= len(args):
            print("[错误] -m 后面要跟模型名，可选：" + " / ".join(config.MODELS))
            sys.exit(1)
        key = args[i + 1]
        del args[i:i + 2]

    target = Path(args[0]) if args else config.get_default_input(key)
    return target, key


# ==============================================================================
# 打印单张结果
# ==============================================================================
def show_one(r, true_label=None):
    print()
    print("─" * 70)
    print(f"  图片   {r.get('path', '(单帧画面)')}")
    if true_label:
        print(f"  真实   {true_label}")
    print("─" * 70)

    if r["error"]:
        print(f"  [失败] {r['error']}")
        return

    if r["ok"]:
        mark = "✅"
        if true_label:
            mark = "✅" if r["name"] == true_label else "❌"
        print(f"  {mark} 【{config.label_of(r['name'])}】    置信度 {r['conf'] * 100:.1f}%")
    else:
        print(f"  ❓ 【未知】 最高分只有 {r['conf'] * 100:.1f}%，"
              f"低于阈值 {config.CONF_THRESHOLD * 100:.0f}%")

    print("\n  排名:")
    for i, (name, p) in enumerate(r["topk"], 1):
        n = int(round(p * 26))
        print(f"     {i}. {pad(config.label_of(name), 18)} {'█' * n}{'·' * (26 - n)} {p * 100:5.1f}%")
    print(f"\n  推理 {r['ms']:.0f} 毫秒")


# ==============================================================================
# 批量测试
# ==============================================================================
def test_paths(target: Path, key=None):
    """
    target 可以是：
      1. 一个文件夹，里面直接放图片          -> 只列结果
      2. 一个文件夹，里面按类别分子文件夹    -> 逐类算准确率
      3. 单个图片文件                        -> 单张结果
    """
    if target.is_file():
        r = engine.predict(target, key=key)
        r["path"] = str(target)
        show_one(r, true_label=None)
        return

    # 判断是"按类别分"还是"平铺"
    subdirs = [d for d in sorted(target.iterdir()) if d.is_dir()]
    if subdirs:
        test_by_class(target, subdirs, key)
    else:
        test_flat(target, key)


def test_flat(folder: Path, key=None):
    files = sorted(f for f in folder.iterdir()
                   if f.is_file() and f.suffix.lower() in config.IMAGE_EXT)
    if not files:
        print(f"[错误] 这个文件夹里没有图片：{folder}")
        return

    print()
    print("=" * 70)
    print(f"  文件夹   {folder}")
    print(f"  图片数   {len(files)}")
    print("=" * 70)

    results = engine.predict_paths(files, key=key, verbose=True)
    for f, r in zip(files, results):
        if r["error"]:
            print(f"  [失败] {f.name}: {r['error']}")
            continue
        tag = "  " if r["ok"] else "❓"
        name = config.label_of(r["name"]) if r["ok"] else "未知"
        print(f"  {tag} {f.name:<34} -> {name:<14} {r['conf'] * 100:5.1f}%")

    ms = sum(r["ms"] for r in results) / max(len(results), 1)
    print(f"\n  平均 {ms:.0f} 毫秒/张")


def test_by_class(folder: Path, subdirs, key=None):
    print()
    print("=" * 70)
    print(f"  类别测试   {folder}")
    print("=" * 70)

    total = correct = rejected = 0
    wrong = []

    for cls_dir in subdirs:
        files = sorted(f for f in cls_dir.iterdir()
                       if f.is_file() and f.suffix.lower() in config.IMAGE_EXT)
        if not files:
            continue
        results = engine.predict_paths(files, key=key, verbose=False)
        c = 0
        for f, r in zip(files, results):
            if r["error"]:
                continue
            if not r["ok"]:
                rejected += 1
            elif r["name"] == cls_dir.name:
                c += 1
            else:
                wrong.append((f.name, cls_dir.name, r["name"], r["conf"]))
        total += len(files)
        correct += c
        print(f"  {pad(config.label_of(cls_dir.name), 18)} {c:>4}/{len(files):<4} "
              f"{c / len(files) * 100:6.2f}%")

    if not total:
        print("  （没有可用图片）")
        return

    print("─" * 70)
    print(f"  {'总体准确率':<18} {correct:>4}/{total:<4} {correct / total * 100:6.2f}%")
    if rejected:
        print(f"  被拒识（判为未知）  {rejected} 张")

    if wrong:
        print(f"\n  判错的 {len(wrong)} 张：")
        for fn, true_n, pred_n, c in wrong[:20]:
            print(f"    {fn:<32} 真实 {pad(config.label_of(true_n), 16)} "
                  f"误判为 {pad(config.label_of(pred_n), 16)} {c * 100:5.1f}%")
        if len(wrong) > 20:
            print(f"    ... 还有 {len(wrong) - 20} 张")


# ==============================================================================
# 主流程
# ==============================================================================
def main():
    target, key = parse_args(sys.argv[1:])

    info = config.get_model_info(key)
    print("=" * 70)
    print(f"  模型      {info['label']}   ({info['key']})")
    print(f"  权重      {info['weights']}")
    print("=" * 70)

    if not engine.is_ready(key):
        print(f"\n[错误] 模型文件不存在，请先训练或把 best.pt 放到：")
        print(f"       {info['weights'].parent}")
        return 1

    # 加载一次（后面走缓存）
    engine.load_model(key, verbose=True)

    if not target.exists():
        print(f"\n[错误] 路径不存在：{target}")
        return 1

    test_paths(target, key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
