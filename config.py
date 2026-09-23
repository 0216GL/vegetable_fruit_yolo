# -*- coding: utf-8 -*-
"""
全局配置 —— 所有可调参数集中在这一个文件里
================================================================================

【怎么用】
    只改这个文件，predict.py / camera.py / engine.py 全部跟着变。

【最常改的两个地方】
    1. ACTIVE_MODEL     —— 切换用哪个模型（柿子成熟度 / 蔬菜水果物种）
    2. DEFAULT_INPUT    —— predict.py 不带参数时默认测哪个目录

【为什么单独一个文件】
    以前模型路径散落在 predict.py / camera.py 里，改一个忘一个。
    现在只有一份，改完全局生效 —— 这就是"低耦合"。
================================================================================
"""

import os
import sys
from pathlib import Path

# ==============================================================================
# 项目根目录 + 环境变量
# ==============================================================================

ROOT = Path(__file__).resolve().parent

# 这两个环境变量必须在 import ultralytics 之前设置，否则不生效。
# 放在这里而不是各脚本里，保证任何入口（PyCharm、命令行、被别的代码 import）
# 都是一致的。
os.environ.setdefault("YOLO_CONFIG_DIR", str(ROOT / ".ultralytics"))
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".mplcache"))
(ROOT / ".ultralytics" / "Ultralytics").mkdir(parents=True, exist_ok=True)
(ROOT / ".mplcache").mkdir(parents=True, exist_ok=True)

# 让中文能正常输出到 PyCharm 的 Run 窗口
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

# 图表里的中文（ultralytics 画预测图会用到）
try:
    import matplotlib
    matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun", "DejaVu Sans"]
    matplotlib.rcParams["axes.unicode_minus"] = False
except Exception:
    pass


# ==============================================================================
# 1. 模型注册表 —— 要加新模型，在这里加一项就行
# ==============================================================================

# ★★★ 切换模型：改这一行 ★★★
ACTIVE_MODEL = "persimmon"

MODELS = {
    "persimmon": {
        "label": "柿果成熟度（4级）",
        "weights": ROOT / "models" / "persimmon_cls_v1" / "best.pt",
        "dataset": ROOT / "dataset" / "dataset_persimmon",
        # 成熟度各类长得很像，模型"过度自信"：判错时的置信度平均也有 82%。
        # 实测加阈值只会让系统多说"不知道"，并不能提高准确率，
        # 所以这一档【不做拒识】。
        "threshold": 0.0,
    },
    "species": {
        "label": "蔬菜水果（12类）",
        "weights": ROOT / "models" / "fruits_cls_v1" / "best.pt",
        "dataset": ROOT / "dataset" / "dataset_fruit&&vegetable",
        # 物种之间差异大，拒识有效（首次训练时 0.60 是调过的值）。
        "threshold": 0.60,
    },
}


def get_model_info(key=None):
    """取某个模型的配置。key=None 表示当前激活的那个。"""
    key = key or ACTIVE_MODEL
    if key not in MODELS:
        raise KeyError(f"未知模型 {key!r}，可选：{list(MODELS)}")
    info = dict(MODELS[key])
    info["key"] = key
    info.setdefault("threshold", CONF_THRESHOLD)
    return info


# ==============================================================================
# 2. 推理参数
# ==============================================================================

IMGSZ = 224          # 输入尺寸，必须和训练时一致，否则掉精度
TOPK = 3             # 打印前几名
CONF_THRESHOLD = 0.60  # 低于这个置信度就报"未知"，而不是硬猜


# ==============================================================================
# 3. 默认输入（predict.py 不带命令行参数时用）
# ==============================================================================

# None = 自动用当前模型的 val 目录
# 也可以写死一个路径，例如：ROOT / "照片" / "待测"
DEFAULT_INPUT = None


def get_default_input(key=None):
    """算出不带参数时该测什么。"""
    if DEFAULT_INPUT is not None:
        return Path(DEFAULT_INPUT)
    return get_model_info(key)["dataset"] / "val"


# ==============================================================================
# 4. 摄像头参数
# ==============================================================================

CAMERA = {
    "index": 0,          # 0 = 笔记本自带，1 = 外接
    "width": 640,
    "height": 480,
    "mirror": True,      # 画面镜像（像照镜子，看着自然）
    "smooth_n": 5,       # 结果平滑：取最近 N 帧里出现最多的结果
}


# ==============================================================================
# 5. 类别的中文显示名
# ==============================================================================

# 键 = 模型输出的英文类名（必须和训练时文件夹名完全一致）
# 值 = 屏幕上/报告里显示的中文名
# 没在这里登记的类名，原样显示英文。
#
# ⚠️ 括号里的颜色是【暂时】的说明，方便看屏幕时一眼知道是哪一级。
#    等分类定稿后再改成正式名称。
#    颜色依据：实测各类验证图的平均色相
#      1_unripe   H≈63°  黄绿
#      2_turning  H≈53°  黄橙
#      3_coloring H≈36°  橙红
#      4_full     H≈30°  深红
CLASS_LABELS = {
    # ---- 柿子成熟度（persimmon_cls_v1）----
    "1_unripe":   "未熟（青绿）",
    "2_turning":  "转色期（黄橙）",
    "3_coloring": "着色期（橙红）",
    "4_full":     "完熟（深红）",

    # ---- 蔬菜水果物种（fruits_cls_v1）----
    "土豆": "土豆", "圣女果": "圣女果", "大白菜": "大白菜", "大葱": "大葱",
    "梨": "梨", "胡萝卜": "胡萝卜", "芒果": "芒果", "苹果": "苹果",
    "西红柿": "西红柿", "韭菜": "韭菜", "香蕉": "香蕉", "黄瓜": "黄瓜",
}


def label_of(name):
    """把模型的英文类名翻译成中文显示名（含颜色说明）。"""
    return CLASS_LABELS.get(name, name)


def short_label_of(name):
    """只要括号前的部分，版面紧张时用（如摄像头大字）。"""
    full = CLASS_LABELS.get(name, name)
    i = full.find("（")
    return full[:i] if i > 0 else full


# ==============================================================================
# 6. 支持的图片扩展名
# ==============================================================================

IMAGE_EXT = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
