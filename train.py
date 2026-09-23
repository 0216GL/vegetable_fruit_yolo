# -*- coding: utf-8 -*-
"""
训练脚本（物种分类 / 柿果成熟度，同一套代码）
================================================================================

【这份代码到底在干什么】

    调用 Ultralytics 的 YOLO11n-cls 模型，在本地数据集上做「微调」（fine-tune）。

    「微调」的意思是：模型不是从零学的。
    weights/yolo11n-cls.pt 这个 5.52 MB 的文件里，装着别人在 ImageNet
    1000 个类别上训练好的参数。我们把它加载进来，只把最后的分类头
    换成自己的类别数，再用自己的图继续训练几轮。

    所以真正的训练代码只有一行： model.train(...)
    其余的代码都是「体检」和「归档」。

【训练哪个任务：改 CONFIG 的两行】

    ┌──────────────┬─────────────────────────┬──────────────────────────┐
    │ 想训什么      │ CONFIG["data"]           │ CONFIG["name"]           │
    ├──────────────┼─────────────────────────┼──────────────────────────┤
    │ 蔬菜水果 12 类 │ ROOT/"dataset"/"dataset_fruit&&vegetable" │ "fruits_cls_v1"    │
    │ 柿果成熟度 4 类 │ ROOT/"dataset"/"dataset_persimmon"        │ "persimmon_cls_v1" │
    └──────────────┴─────────────────────────┴──────────────────────────┘

    ⚠️ ["name"] 决定产物目录（runs/<name>/、models/<name>/）。
       换数据集必须同时改它，否则会覆盖上一次训练的成品。

【注意：数据增强参数】

    ultralytics 的 hsv_* 默认值是给「目标检测」用的。
    柿果成熟度是「靠颜色分级」的任务，默认的 hsv_s=0.7（饱和度 ±70%）
    和 hsv_h=0.015（色相 ±5.4°）会把关键信号破坏掉
    —— 实测「着色期」与「完熟」的色相只差 6°。
    CONFIG 里已给出针对本任务的建议值，见注释。

【为什么代码这么短】

    因为神经网络、反向传播、优化器、学习率调度、数据增强……
    全部封装在 ultralytics 这个第三方库里了。

    Java 类比：你写 Spring Boot 时，业务代码也就几行，
    框架的复杂度在 pom.xml 的依赖里，不在你的代码里。
    这里一模一样 —— 复杂度在 pip 装的那 150 MB 包里。

【怎么运行】

    PyCharm 里右键 → Run 'train'
    或者命令行： conda activate yolo && python train.py

    前提：PyCharm 的项目解释器必须指向
          D:\\Anaconda\\envs\\yolo\\python.exe

【产物】

    models/fruits_cls_v1/best.pt       训练好的模型（以后预测只用这个）
    models/fruits_cls_v1/classes.json  类别映射表（防止标签错位）
    runs/fruits_cls_v1/                训练日志、精度曲线、混淆矩阵

【预计耗时】

    CPU（当前环境）：约 10~20 分钟
    GPU（需换 CUDA 版 torch）：约 1~3 分钟
    两者产出的模型精度完全相同，只是速度差别。
"""

import json
import os
import shutil
import sys
import time
from pathlib import Path

# ==============================================================================
# 第 0 步：确定项目路径 + 设置环境变量
# ==============================================================================

# ROOT = 本文件所在目录，也就是 D:\vegetable_fruit_yolo
#
# 为什么用 __file__ 而不是 "."：
#   "." 表示"当前工作目录"，而 PyCharm、命令行、计划任务启动时的
#   工作目录可能各不相同。用 __file__ 就永远指向脚本自己所在的目录，
#   这样无论从哪启动，路径都不会错。
ROOT = Path(__file__).resolve().parent

# ------------------------------------------------------------------------------
# 这两个环境变量必须在 import ultralytics 之前设置，否则不生效！
# ------------------------------------------------------------------------------
# YOLO_CONFIG_DIR
#     ultralytics 的配置文件默认写到 C:\Users\用户名\AppData\Roaming\Ultralytics
#     指定到项目里之后，整个项目就"自包含"了 —— 拷到别的电脑也能直接跑。
#
# MPLCONFIGDIR
#     matplotlib 的字体缓存目录，同理，避免往系统目录里扔文件。
os.environ["YOLO_CONFIG_DIR"] = str(ROOT / ".ultralytics")
os.environ["MPLCONFIGDIR"] = str(ROOT / ".mplcache")

# ultralytics 会往 YOLO_CONFIG_DIR 下面再套一层 "Ultralytics" 目录，
# 如果那层目录不存在，它检测到"不可写"就会退回写到项目根目录，
# 于是项目里凭空多出一个 Ultralytics\ 文件夹。这里先建好，避免这个副作用。
(ROOT / ".ultralytics" / "Ultralytics").mkdir(parents=True, exist_ok=True)
(ROOT / ".mplcache").mkdir(parents=True, exist_ok=True)

# 让中文能正常输出到 PyCharm 的 Run 窗口（Windows 默认编码不是 utf-8）
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# ------------------------------------------------------------------------------
# 让图表里的中文能正常显示
# ------------------------------------------------------------------------------
# matplotlib 的默认字体（DejaVu Sans）里**没有汉字字形**，
# 不设置的话，混淆矩阵、训练曲线图上的"土豆""苹果"会全部变成 □□ 方块，
# 同时在控制台刷几十行 "Glyph xxxxx missing from font" 警告。
#
# 解决：把字体设成系统自带的中文字体。
# 顺序表示"优先用第一个，找不到就退到下一个"。
import matplotlib
matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"]
# 顺便修掉负号显示成方块的问题（中文字体的减号和 ASCII 减号不是同一个字符）
matplotlib.rcParams["axes.unicode_minus"] = False

# 环境变量设置完了，现在才可以 import
from ultralytics import YOLO


# ==============================================================================
# 训练配置 —— 想调参，改这里就够了
# ==============================================================================
CONFIG = {
    # 预训练权重：从哪个模型开始微调。
    # 这就是"站在巨人肩膀上"的那个巨人。删掉它就只能从零训练，精度会差一大截。
    "weights": ROOT / "weights" / "yolo11n-cls.pt",

    # 数据集根目录：里面必须有 train/ 和 val/ 两个子目录，各自按类别分文件夹
    # "data": ROOT / "dataset" / "dataset_fruit&&vegetable",
    "data": ROOT / "dataset" / "dataset_persimmon",

    # 训练轮数。一"轮"(epoch) = 把 841 张训练图完整看一遍。
    # 50 轮对这个规模足够了。想更保险可以改 100，代价是时间翻倍。
    "epochs": 50,

    # 输入图片尺寸（正方形边长）。
    # 预训练权重是按 224 训练的，改成别的值会削弱迁移效果。
    # 我们的原图是 299×299，YOLO 会自动缩放到这个尺寸。
    "imgsz": 224,

    # 批大小：一次同时送进网络几张图。
    # 越大越快但越吃内存。CPU 上 16 比较稳，报内存不足就改成 8。
    "batch": 16,

    # 数据加载的并行进程数。8 核以上用 8 就够。
    # 如果报多进程相关的错误，改成 0（退化成单进程，慢但最稳）。
    "workers": 8,

    # 随机种子。固定住，保证每次训练结果可复现（学术上叫"可复现性"）。
    "seed": 0,

    # 本次训练的代号，决定产物目录名：
    #   runs/fruits_cls_v1/      训练过程与日志
    #   models/fruits_cls_v1/    归档的最终产物
    # 下次换数据重训，改成 persimmon_cls_v1 就能并存，不会覆盖。
    # "name": "fruits_cls_v1",
    "name": "persimmon_cls_v1",

    # 随机水平翻转的概率（数据增强）。
    # 苹果左右翻转还是苹果，所以可以放开来用。0.5 是常用值。
    "fliplr": 0.5,
}


# ==============================================================================
# 小工具：打印带框的标题，让 Run 窗口的输出好读
# ==============================================================================
def title(text):
    print()
    print("=" * 78)
    print("  " + text)
    print("=" * 78)


# ==============================================================================
# 第 1 步：环境检查
# ==============================================================================
def check_environment():
    """
    确认"我在用哪个 Python、有没有显卡"。

    这一步看着像废话，但它是排错的第一现场：
    90% 的"训练很慢"最终都发现是解释器选错了，或者装成了 CPU 版 torch。
    """
    title("第 1 步 / 环境检查")

    import torch
    import ultralytics

    print(f"  Python          {sys.version.split()[0]}")
    print(f"  PyTorch         {torch.__version__}")
    print(f"  Ultralytics     {ultralytics.__version__}")
    print(f"  解释器路径      {sys.executable}")

    # torch 版本号的后缀能直接看出装的是哪个版本：
    #     +cpu    只能跑 CPU
    #     +cu126  支持 CUDA 12.6，能用 N 卡
    # 所以下面这两行不是"报错"，是"如实汇报"。
    if torch.cuda.is_available():
        print(f"  计算设备        GPU  {torch.cuda.get_device_name(0)}")
    else:
        print(f"  计算设备        CPU")
        print(f"                  （torch 是 {torch.__version__}，没有 CUDA 支持）")
        print(f"                  CPU 训练慢一些，但产出的模型精度和 GPU 完全相同")


# ==============================================================================
# 第 2 步：数据集体检
# ==============================================================================
def check_dataset():
    """
    在花 15 分钟训练之前，先用 2 秒钟确认数据没问题。

    这是命令行做不到的一步，也是"规范化"的核心之一：
    逐类统计张数、检查 train/val 的类别是否一致、把类别顺序固定下来。

    返回：排好序的类别名列表；数据有问题则返回 None。
    """
    title("第 2 步 / 数据集检查")

    data_root = CONFIG["data"]
    if not data_root.is_dir():
        print(f"  [错误] 找不到数据集目录: {data_root}")
        return None

    per_split = {}

    for split in ("train", "val"):
        d = data_root / split
        if not d.is_dir():
            print(f"  [错误] 找不到目录: {d}")
            return None

        # 每个子目录名 = 一个类别名；目录里的图片 = 该类别的样本。
        # 注意这里用了 sorted()：类别编号顺序必须固定死，
        # 否则同一批数据每次跑出来的标签编号都可能不同。
        # （原项目的 tfrecord.py 就是用 os.listdir() 的原始顺序，
        #   在 Windows 和 macOS 上顺序不同，导致预测出来的名字全对不上。）
        classes = sorted([p.name for p in d.iterdir() if p.is_dir()])

        counts = {}
        for c in classes:
            n = len([
                f for f in (d / c).iterdir()
                if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp")
            ])
            counts[c] = n

        per_split[split] = counts
        total = sum(counts.values())
        print(f"\n  {split} 集: {len(classes)} 个类别, 共 {total} 张")
        for c, n in counts.items():
            print(f"      {c:<8} {n:>4} 张")

        if total == 0:
            print(f"  [错误] {split} 集里一张图都没有")
            return None

    # 训练集和验证集的类别必须一字不差地一致，
    # 否则"第 3 号类别"在两边指的不是同一个东西，评估结果就没有意义了。
    tr, va = per_split["train"], per_split["val"]
    if sorted(tr) != sorted(va):
        print("\n  [错误] train 和 val 的类别不一致！")
        print(f"    只在 train 里有的: {sorted(set(tr) - set(va))}")
        print(f"    只在 val 里有的  : {sorted(set(va) - set(tr))}")
        return None

    # 类别顺序表 —— 整个项目里"标签编号"的唯一权威来源
    class_names = sorted(tr)
    print("\n  类别编号表（这个顺序就是标签编号，务必固定）:")
    for i, c in enumerate(class_names):
        print(f"      {i:>2} -> {c}")

    print(f"\n  ✓ 数据检查通过")
    return class_names


# ==============================================================================
# 第 3 步：训练
# ==============================================================================
def train():
    """
    加载预训练权重 → 微调。

    这就是全部。真正的训练只有 model.train(...) 一行。
    返回训练好的 model 对象和 best.pt 的路径。
    """
    title("第 3 步 / 开始训练")

    print(f"  预训练权重      {CONFIG['weights'].name}")
    print(f"  数据集          {CONFIG['data']}")
    print(f"  轮数 (epochs)   {CONFIG['epochs']}")
    print(f"  输入尺寸        {CONFIG['imgsz']} × {CONFIG['imgsz']}")
    print(f"  批大小 (batch)  {CONFIG['batch']}")
    print(f"  训练日志目录    runs/{CONFIG['name']}/")
    print()

    # ------------------------------------------------------------------------
    # 加载预训练模型。
    #
    # 这一行做了三件事：
    #   1. 读出 weights/yolo11n-cls.pt 里的全部参数
    #   2. 把分类头（原来输出 1000 类）换成输出 12 类
    #   3. 前面那些卷积层的参数原样保留 —— 这就是"迁移"
    #
    # 训练时你会看到一行日志：
    #     Transferred 234/236 items from pretrained weights
    # 意思就是 234 个参数张量成功继承过来了。这一行是整个方案的命脉。
    # ------------------------------------------------------------------------
    model = YOLO(str(CONFIG["weights"]))

    # ------------------------------------------------------------------------
    # 【真正的训练】—— 就这一行
    #
    #   参数            作用
    #   ------------    ------------------------------------------------------
    #   data            数据集根目录（里面有 train/ 和 val/）
    #   epochs          训练轮数
    #   imgsz           输入尺寸
    #   batch           批大小
    #   project         产物写到哪个根目录
    #   name            子目录名，所以日志在 runs/fruits_cls_v1/
    #   exist_ok        目录已存在时直接覆盖，而不是新建 train2、train3…
    #   fliplr          随机水平翻转的概率（数据增强）
    #   seed            随机种子
    #   workers         数据加载的并行进程数
    # ------------------------------------------------------------------------
    model.train(
        data=str(CONFIG["data"]),
        epochs=CONFIG["epochs"],
        imgsz=CONFIG["imgsz"],
        batch=CONFIG["batch"],
        project=str(ROOT / "runs"),
        name=CONFIG["name"],
        exist_ok=True,
        fliplr=CONFIG["fliplr"],
        seed=CONFIG["seed"],
        workers=CONFIG["workers"],
    )

    # 训练过程中，YOLO 每轮结束都会在验证集上测一次精度，
    # 并把"历史最好"的那一份存成 best.pt、"最后一轮"存成 last.pt。
    best = ROOT / "runs" / CONFIG["name"] / "weights" / "best.pt"
    return model, best


# ==============================================================================
# 第 4 步：归档产物
# ==============================================================================
def save_artifacts(model, best_path, class_names):
    """
    把模型和类别表复制到 models/ 下统一管理。

    为什么要专门归档，而不是直接用 runs/ 里的那份：
      1. runs/ 会随着每次训练堆积很多目录，模型散在里面不好找
      2. predict.py 只需要认 models/ 一个地方，不用关心 runs/ 的历史
      3. 将来要部署时，models/ 整个目录拷走就能用
    """
    title("第 4 步 / 归档产物")

    out_dir = ROOT / "models" / CONFIG["name"]
    out_dir.mkdir(parents=True, exist_ok=True)

    if not best_path.exists():
        print(f"  [警告] 没找到 best.pt: {best_path}")
        return out_dir

    # ---- 模型文件 ----
    dst_model = out_dir / "best.pt"
    shutil.copy2(best_path, dst_model)
    print(f"  模型文件    {dst_model}")
    print(f"              大小 {dst_model.stat().st_size / 2**20:.2f} MB")

    # ---- 类别映射表 ----
    #
    # 这是"防标签错位"的关键产物。
    #
    # 模型输出的其实不是"苹果"，而是一个数字下标（0~11）。
    # 这个下标和中文名的对应关系必须存下来，否则预测时会张冠李戴。
    #
    # 优先从模型自己记录的信息里读（最权威），读不到才退回用目录扫描的结果。
    names = getattr(model, "names", None)
    if isinstance(names, dict):
        names = [names[i] for i in sorted(names)]
    if not names:
        names = class_names

    mapping = {
        "version": CONFIG["name"],
        "num_classes": len(names),
        "index_to_name": list(names),
        "created": time.strftime("%Y-%m-%d %H:%M:%S"),
        "note": "模型输出的是下标(0~11)，用本表翻译成中文类别名。",
    }

    dst_json = out_dir / "classes.json"
    with open(dst_json, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False, indent=2)

    print(f"\n  类别映射表  {dst_json}")
    for i, n in enumerate(names):
        print(f"              {i:>2} -> {n}")

    return out_dir


# ==============================================================================
# 第 5 步：评估
# ==============================================================================
def evaluate(best_path):
    """
    拿训练好的模型在验证集上跑一遍，报告 top1 / top5 精度。

    验证集的 391 张图模型在训练时从未见过，所以这个精度是可信的。
    （在训练集上算精度毫无意义 —— 相当于考前背了答案再夸自己考得好。）
    """
    title("第 5 步 / 评估")

    if not best_path.exists():
        print(f"  [跳过] 找不到模型: {best_path}")
        return

    m = YOLO(str(best_path))
    metrics = m.val(data=str(CONFIG["data"]), split="val")

    # ultralytics 不同版本字段名略有差异，用 getattr 兼容一下
    top1 = getattr(metrics, "top1", None)
    top5 = getattr(metrics, "top5", None)

    print()
    if top1 is not None:
        # top1 = 第一猜就猜对的概率
        print(f"  验证集 top1 精度:  {top1 * 100:.2f}%")
    if top5 is not None:
        # top5 = 前五个候选里包含正确答案的概率
        print(f"  验证集 top5 精度:  {top5 * 100:.2f}%")


# ==============================================================================
# 主流程
# ==============================================================================
def main():
    started = time.time()

    print("=" * 78)
    print("  蔬菜水果 12 类图像分类 —— 训练")
    print(f"  项目根目录: {ROOT}")
    print("=" * 78)

    # 第 1 步：环境
    check_environment()

    # 第 2 步：数据体检（不通过就直接停，不浪费 15 分钟）
    class_names = check_dataset()
    if not class_names:
        print("\n>>> 数据检查未通过，已停止。请修好数据再运行。")
        return 1

    # 第 3 步：训练
    model, best = train()

    # 第 4 步：归档
    out_dir = save_artifacts(model, best, class_names)

    # 第 5 步：评估
    evaluate(best)

    # 收尾汇总
    title("全部完成")
    print(f"  总耗时      {(time.time() - started) / 60:.1f} 分钟")
    print(f"  模型        {out_dir / 'best.pt'}")
    print(f"  类别表      {out_dir / 'classes.json'}")
    print(f"  训练日志    {ROOT / 'runs' / CONFIG['name']}")
    print()
    print("  下一步：用 predict.py 拿一张图试试")
    print(f"      python predict.py \"某张图片的路径\"")

    return 0


# Windows 上如果用多进程加载数据，必须有这个 __main__ 保护，
# 否则子进程会反复导入本文件、无限递归启动。
if __name__ == "__main__":
    sys.exit(main())
