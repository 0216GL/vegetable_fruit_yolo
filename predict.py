# -*- coding: utf-8 -*-
"""
蔬菜水果 12 类图像分类 —— 预测脚本
================================================================================

【这个脚本干什么】

    加载已经训练好的模型，给它一张图片，告诉你这是什么。

    ★ 它不训练。模型是 train.py 训好、存在 models/ 里的。
    ★ 它不用摄像头。摄像头在另一个脚本里（那是后面的事）。
    ★ 它只做一件事：读图 → 推理 → 打印结果。

【怎么用】

    :: 单张图片
    python predict.py "D:\\照片\\苹果.jpg"

    :: 整个文件夹（批量，会额外统计准确率）
    python predict.py "dataset\\val\\苹果"

    :: 不带参数 → 显示用法和几个可以试的例子
    python predict.py

【产物与依赖】

    模型      models/fruits_cls_v1/best.pt
    类别表    models/fruits_cls_v1/classes.json

    这两个文件缺一个都不行。模型负责"算"，类别表负责"把算出来的数字翻译成中文"。

【耗时】

    加载模型    约 0.1 秒（只加载一次）
    每张图推理  约 10 毫秒
"""

import os
import sys
import json
import math
import time
from pathlib import Path

# ==============================================================================
# 第 0 步：项目路径 + 环境变量（和 train.py 保持一致）
# ==============================================================================
ROOT = Path(__file__).resolve().parent

os.environ["YOLO_CONFIG_DIR"] = str(ROOT / ".ultralytics")
os.environ["MPLCONFIGDIR"] = str(ROOT / ".mplcache")

# ultralytics 会往 YOLO_CONFIG_DIR 下面再套一层 "Ultralytics" 目录，
# 如果那层目录不存在，它检测到"不可写"就会退回写到项目根目录，
# 于是项目里凭空多出一个 Ultralytics\ 文件夹。这里先建好，避免这个副作用。
(ROOT / ".ultralytics" / "Ultralytics").mkdir(parents=True, exist_ok=True)
(ROOT / ".mplcache").mkdir(parents=True, exist_ok=True)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 图表中文（ultralytics 画预测图时会用到，和 train.py 同一套路）
import matplotlib
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"]
matplotlib.rcParams["axes.unicode_minus"] = False

from ultralytics import YOLO


# ==============================================================================
# 预测配置 —— 想改行为就改这里
# ==============================================================================
CONFIG = {
    # 用哪个模型。换模型版本时改这个目录名。
    "model": ROOT / "models" / "fruits_cls_v1" / "best.pt",
    "classes": ROOT / "models" / "fruits_cls_v1" / "classes.json",

    # 输入尺寸，必须和训练时一致（不一致会明显掉精度）
    "imgsz": 224,

    # 打印前几名
    "topk": 3,

    # ------------------------------------------------------------------------
    # 【T7 拒识】置信度阈值
    # ------------------------------------------------------------------------
    # 模型是"12 选 1 的单选题"，它一定会选一个，数学上没有"以上都不是"的选项。
    # 所以拿它不认识的东西（猫、手、白墙）去问，它也会硬报一个蔬菜名。
    #
    # 这里设一道闸门：最高置信度低于这个值，就输出"未知"，而不是硬猜。
    #
    #     0.60  保守，宁可说"不知道"
    #     0.40  宽松，尽量给答案
    #     0.00  等于关闭拒识（永远硬猜）
    #
    # ⚠️ 诚实提醒：这个办法只在"模型自己也没底"时有效。
    #    softmax 有过度自信的毛病 —— 对着猫它可能给"苹果 0.95"，那就拦不住。
    #    真要根治，得加第 13 类"其他"重新训练（需要额外收集几百张干扰图）。
    "conf_threshold": 0.60,
}

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


# ==============================================================================
# 加载模型和类别表
# ==============================================================================
def load():
    """把模型和类别表读进内存。只做一次。"""
    if not CONFIG["model"].exists():
        print(f"[错误] 找不到模型文件: {CONFIG['model']}")
        print(f"       请先运行 train.py 训练模型。")
        sys.exit(1)

    # 类别表 —— 把模型的数字输出翻译成中文
    if CONFIG["classes"].exists():
        with open(CONFIG["classes"], encoding="utf-8") as f:
            names = json.load(f)["index_to_name"]
    else:
        # 没有类别表就退回用模型自带的（一般也够用）
        print(f"[提示] 没找到 {CONFIG['classes'].name}，改用模型内置类别名")
        names = None

    t0 = time.time()
    model = YOLO(str(CONFIG["model"]))
    load_ms = (time.time() - t0) * 1000

    # 模型自己的类别表是最权威的，优先用
    model_names = getattr(model, "names", None)
    if isinstance(model_names, dict):
        model_names = [model_names[i] for i in sorted(model_names)]
    if model_names:
        names = model_names

    print(f"模型已加载  {CONFIG['model'].name}  ({load_ms:.0f} 毫秒)")
    print(f"类别数      {len(names)}")
    return model, names


# ==============================================================================
# 核心：对一张图做预测
# ==============================================================================
def predict_one(model, names, img_path):
    """
    输入一张图，返回一个结果字典。

    返回值：
        path     图片路径
        ok       是否被接受（未被拒识）
        name     预测的类别名（被拒识时是 None）
        conf     最高置信度
        topk     [(类别名, 置信度), ...] 前 k 名
        entropy  分布熵，越低越确定
        ms       推理耗时（毫秒）
        error    出错信息（正常时为 None）
    """
    result = {
        "path": str(img_path),
        "ok": False,
        "name": None,
        "conf": 0.0,
        "topk": [],
        "entropy": 0.0,
        "ms": 0.0,
        "error": None,
    }

    try:
        t0 = time.time()
        # 推理。模型直接吃文件路径，内部会自动做缩放等预处理。
        preds = model.predict(source=str(img_path), imgsz=CONFIG["imgsz"], verbose=False)
        result["ms"] = (time.time() - t0) * 1000
    except Exception as e:
        result["error"] = str(e)
        return result

    probs = preds[0].probs           # 分类任务的概率对象
    p = probs.data.cpu().numpy()     # 12 个概率值，加起来等于 1

    # 把概率从大到小排序，取前 k 名
    order = p.argsort()[::-1]
    result["topk"] = [(names[i], float(p[i])) for i in order[:CONFIG["topk"]]]

    top1_idx = int(order[0])
    result["conf"] = float(p[top1_idx])
    result["name"] = names[top1_idx]

    # 分布熵：衡量"这个预测有多犹豫"
    #   全押一个类 → 接近 0
    #   12 类平均分 → 2.485（ln 12，最大可能值）
    result["entropy"] = float(-sum(pi * math.log(pi + 1e-12) for pi in p))

    # ---------------- T7 拒识闸门 ----------------
    if result["conf"] < CONFIG["conf_threshold"]:
        result["ok"] = False          # 拒识：不给答案
    else:
        result["ok"] = True
    return result


# ==============================================================================
# 把结果打印成人能读的格式
# ==============================================================================
def bar(p, width=28):
    """画一个横向进度条，让结果一眼能看出差距。"""
    n = int(round(p * width))
    return "█" * n + "·" * (width - n)


def show(result, true_label=None):
    """打印单张图的预测结果。"""
    print()
    print("─" * 74)
    print(f"  图片   {result['path']}")
    if true_label:
        print(f"  真实   {true_label}")
    print("─" * 74)

    if result["error"]:
        print(f"  [读图失败] {result['error']}")
        return

    if result["ok"]:
        mark = "✅"
        # 如果知道真实答案，顺带标一下对错
        if true_label:
            mark = "✅" if result["name"] == true_label else "❌"
        print(f"  {mark} 这是【{result['name']}】    置信度 {result['conf'] * 100:.1f}%")
    else:
        print(f"  ❓ 【未知】—— 判断为不属于这 12 类")
        print(f"     最高分只有 {result['conf'] * 100:.1f}%，"
              f"低于阈值 {CONFIG['conf_threshold'] * 100:.0f}%")

    print()
    print("  详细排名:")
    for i, (name, p) in enumerate(result["topk"], 1):
        print(f"     {i}. {name:<8} {bar(p)} {p * 100:5.1f}%")

    print(f"  分布熵 {result['entropy']:.3f}"
          f"（0 = 非常确定，2.485 = 完全瞎猜）    推理 {result['ms']:.0f} 毫秒")


# ==============================================================================
# 批量：对整个文件夹预测
# ==============================================================================
def predict_folder(model, names, folder: Path):
    """
    跑完整个文件夹。

    如果文件夹名恰好是一个已知类别（比如 dataset/val/苹果），
    就顺带统计准确率 —— 这是最直观的"模型行不行"的检验。
    """
    files = sorted([f for f in folder.iterdir()
                    if f.is_file() and f.suffix.lower() in IMAGE_EXT])
    if not files:
        print(f"[错误] 这个文件夹里没有图片: {folder}")
        return

    # 文件夹名是不是一个类别？是的话我们就有"标准答案"可以对
    true_label = folder.name if folder.name in names else None

    print()
    print("=" * 74)
    print(f"  批量预测: {folder}")
    print(f"  图片数量: {len(files)}")
    if true_label:
        print(f"  标准答案: {true_label}  （将统计准确率）")
    else:
        print(f"  标准答案: 无（文件夹名不是已知类别，只列结果不打分）")
    print("=" * 74)

    correct = 0
    rejected = 0
    total_ms = 0.0
    wrong_list = []

    for f in files:
        r = predict_one(model, names, f)
        total_ms += r["ms"]

        if r["error"]:
            print(f"  [读图失败] {f.name}: {r['error']}")
            continue

        if not r["ok"]:
            rejected += 1
            tag = "❓未知"
        elif true_label:
            if r["name"] == true_label:
                correct += 1
                tag = "✅"
            else:
                tag = "❌"
                wrong_list.append((f.name, r["name"], r["conf"]))
        else:
            tag = "  "

        line = f"  {tag} {f.name:<28} -> {r['name']:<8} {r['conf'] * 100:5.1f}%"
        print(line)

    print()
    print("─" * 74)
    print(f"  平均单张耗时   {total_ms / max(len(files), 1):.0f} 毫秒")
    if true_label:
        print(f"  准确率         {correct}/{len(files)} = {correct / len(files) * 100:.2f}%")
        if rejected:
            print(f"  被拒识         {rejected} 张（判为未知）")
        if wrong_list:
            print(f"  判错的 {len(wrong_list)} 张:")
            for fn, pred, c in wrong_list:
                print(f"      {fn:<28} 误判为 {pred}  ({c * 100:.1f}%)")


# ==============================================================================
# 没给参数时：显示用法 + 给几个现成的例子
# ==============================================================================
def show_usage():
    print(__doc__)
    print("=" * 74)
    print("  下面这些图片可以直接复制去试（都是模型没见过的验证集图片）:")
    print("=" * 74)
    shown = 0
    val_dir = ROOT / "dataset" / "val"
    if val_dir.is_dir():
        for cls_dir in sorted(val_dir.iterdir()):
            if not cls_dir.is_dir():
                continue
            imgs = sorted([f for f in cls_dir.iterdir()
                           if f.is_file() and f.suffix.lower() in IMAGE_EXT])
            if imgs:
                print(f'    python predict.py "{imgs[0]}"')
                shown += 1
                if shown >= 5:
                    break
    print()
    print('  或者跑一整个类别（会统计准确率）:')
    print(f'    python predict.py "{val_dir / "苹果"}"')


# ==============================================================================
# 主流程
# ==============================================================================
def main():
    model, names = load()

    # ---- 情况 1：没给参数 ----
    if len(sys.argv) < 2:
        show_usage()
        return 0

    target = Path(sys.argv[1])

    # ---- 情况 2：路径不存在 ----
    if not target.exists():
        print(f"\n[错误] 路径不存在: {target}")
        return 1

    # ---- 情况 3：文件夹（批量）----
    if target.is_dir():
        predict_folder(model, names, target)
        return 0

    # ---- 情况 4：单张图片 ----
    show(predict_one(model, names, target))
    return 0


if __name__ == "__main__":
    sys.exit(main())
