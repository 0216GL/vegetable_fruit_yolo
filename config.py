"""
全局配置 —— 所有可调参数集中在这里。
改这个文件，predict.py / camera.py / engine.py 全部跟着变。
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# 必须在 import ultralytics 之前设置，否则不生效
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".ultralytics"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplcache"))
(ROOT / ".ultralytics" / "Ultralytics").mkdir(parents=True, exist_ok=True)
(ROOT / ".mplcache").mkdir(parents=True, exist_ok=True)

# 中文输出到 PyCharm 的 Run 窗口
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 图表里的中文（ultralytics 画混淆矩阵会用到）
try:
    import matplotlib
    matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False
except Exception:
    pass


# ==============================================================================
# 1. 模型注册表 —— 要加新模型，在这里加一项
# ==============================================================================

ACTIVE_MODEL = "persimmon"      # ★ 切换模型：改这一行（persimmon / species）

MODELS = {
    "persimmon": {
        "label":     "柿果成熟度（4级）",
        "run":       "persimmon_cls_v1",        # 训练代号 = models/ 下的目录名
        "dataset":   ROOT / "dataset" / "dataset_persimmon",
        "threshold": 0.0,       # 各类太像，模型过度自信，加阈值无益 → 不拒识
    },
    "species": {
        "label":     "蔬菜水果（12类）",
        "run":       "fruits_cls_v1",
        "dataset":   ROOT / "dataset" / "dataset_fruit&&vegetable",
        "threshold": 0.60,      # 物种之间差异大，拒识有效
    },
}


def get_model_info(key=None):

    key = key or ACTIVE_MODEL
    if key not in MODELS:
        raise KeyError(f"未知模型 {key!r}，可选：{list(MODELS)}")
    info = dict(MODELS[key])
    info["key"] = key
    info["weights"] = ROOT / "models" / info["run"] / "best.pt"
    return info


def take_model_arg(argv):
    args = list(argv)
    key = None
    if "-m" in args:
        i = args.index("-m")
        if i + 1 >= len(args):
            raise SystemExit("[错误] -m 后面要跟模型名，可选：" + " / ".join(MODELS))
        key = args[i + 1]
        del args[i:i + 2]
    return key, args


# ==============================================================================
# 2. 推理参数
# ==============================================================================

IMGSZ = 224             # 输入尺寸，必须和训练时一致，否则掉精度
TOPK = 3                # 打印前几名
# 拒识阈值不在这里 —— 每个模型差异很大，写在各自 MODELS 条目的 "threshold" 里


# ==============================================================================
# 3. 默认输入（predict.py 不带参数时测什么）
# ==============================================================================

def get_default_input(key=None):
    """默认测当前模型的 val 目录。"""
    return get_model_info(key)["dataset"] / "val"


# ==============================================================================
# 4. 摄像头参数
# ==============================================================================

CAMERA = {
    "index": 0,         # 0 = 笔记本自带，1 = 外接
    "width": 640,
    "height": 480,
    "mirror": True,     # 画面镜像（像照镜子，看着自然）
    "smooth_n": 5,      # 结果平滑：取最近 N 帧里出现最多的结果
}


# ==============================================================================
# 5. 类别中文显示名
# 键 = 模型输出的类名（必须和训练时的文件夹名完全一致）
# 没登记的类名原样显示
# ==============================================================================

CLASS_LABELS = {
    "1_unripe":   "未熟（青绿）",
    "2_turning":  "转色期（黄橙）",
    "3_coloring": "着色期（橙红）",
    "4_full":     "完熟（深红）",
}


def label_of(name):
    """把模型输出的类名翻译成中文显示名。"""
    return CLASS_LABELS.get(name, name)


# ==============================================================================
# 6. 支持的图片扩展名
# ==============================================================================

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp")


# ==============================================================================
# 7. 检测模型（第一层：只找柿子，不判成熟度）
#
# 两层推理的流程：
#     第 1 层  DETECT["weights"]  检测出每个柿子的框（1 个类别：persimmon）
#     第 2 层  MODELS[ACTIVE_MODEL]["weights"]  把框里的图裁出来判成熟度
#
# 训练见 train_detect.py，推理见 detect.py
# ==============================================================================

DETECT = {
    "run":     "persimmon_det_v1",                          # 训练代号
    "weights": ROOT / "models" / "persimmon_det_v1" / "best.pt",
    "dataset": ROOT / "dataset" / "dataset_persimmon_det",  # 里面是 images/ + labels/

    # ---- 两个阈值：管的是完全不同的两件事 ----
    # conf  置信度门槛。YOLO 会输出一堆候选框各带一个分数，低于这个分数的直接丢掉。
    #       调高 → 假正例（把脸、树干框成柿子）变少，但弱一点的真题也会被丢掉。
    #       预测模式官方默认就是 0.25。
    "conf":    0.40,

    # iou   NMS（非极大值抑制）的 IoU 阈值，专门用来合并【重复框】。
    #       两颗框重叠度超过这个值，分数低的那颗被压掉。
    #       调低 → 压制更狠 → 重复框更少。官方默认 0.7。
    "iou":     0.55,

    "margin":  0.06,     # 裁给分类模型时，框外多留一点边（按框尺寸的比例）
}

