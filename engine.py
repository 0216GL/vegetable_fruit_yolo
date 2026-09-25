"""
推理核心 —— predict.py 和 camera.py 共同依赖的底座。

对外四个接口：
    is_ready(key=None)              -> bool        模型文件在不在
    load_model(key=None)            -> (model, names, info)
    predict(source, key=None)       -> dict        单张 / 单帧
    predict_paths(paths, key=None)  -> list[dict]  批量

predict() 返回：
    {
        "ok":        bool,          # 是否被接受（未被拒识）
        "name":      str | None,    # 类别名；被拒识时为 None
        "conf":      float,         # 最高置信度 0~1
        "topk":      [(name, p)],   # 前 k 名
        "threshold": float,         # 本次用的拒识阈值
        "ms":        float,         # 推理耗时（毫秒）
        "error":     str | None,
    }
"""

import time
from pathlib import Path

import numpy as np

# 必须先 import config —— 它负责设置 YOLO_CONFIG_DIR 等环境变量，
# 且必须发生在 import ultralytics 之前
import config


_CACHE = {}     # 模型缓存：同一个模型只加载一次


# ==============================================================================
# 加载模型
# ==============================================================================
def is_ready(key=None):
    """模型权重文件在不在。"""
    return config.get_model_info(key)["weights"].exists()


def load_model(key=None, verbose=True):
    """返回 (model, names, info)。同一个 key 只真正加载一次，之后走缓存。"""
    key = key or config.ACTIVE_MODEL

    if key in _CACHE:
        return _CACHE[key]

    info = config.get_model_info(key)
    weights = info["weights"]

    if not weights.exists():
        raise FileNotFoundError(
            f"找不到模型文件：{weights}\n"
            f"       请先训练，或把训练好的 best.pt 放到 {weights.parent}"
        )

    # 延迟 import：避免只 import engine 就拖起整个 torch
    from ultralytics import YOLO

    t0 = time.time()
    model = YOLO(str(weights))
    ms = (time.time() - t0) * 1000

    raw = getattr(model, "names", None)
    if isinstance(raw, dict):
        names = [raw[i] for i in sorted(raw)]
    elif raw:
        names = list(raw)
    else:
        raise RuntimeError("模型没有携带类别名，无法解读输出")

    if verbose:
        print(f"模型已加载  [{info['label']}]  {weights.name}  ({ms:.0f} 毫秒)")
        print(f"类别数      {len(names)}  ->  {', '.join(names)}")

    _CACHE[key] = (model, names, info)
    return _CACHE[key]


# ==============================================================================
# 推理
# ==============================================================================
def predict(source, key=None, threshold=None, topk=None, imgsz=None, verbose=True):
    """
    source     图片路径（str / Path），或 numpy 数组（摄像头的一帧）
    threshold  拒识阈值，None = 用该模型自己的（见 config.MODELS[*]["threshold"]）
    topk       返回前几名，None = 用 config.TOPK
    imgsz      输入尺寸，None = 用 config.IMGSZ
    """
    topk = config.TOPK if topk is None else topk
    imgsz = config.IMGSZ if imgsz is None else imgsz

    if threshold is None:
        threshold = config.get_model_info(key)["threshold"]

    result = {"ok": False, "name": None, "conf": 0.0, "topk": [],
              "threshold": threshold, "ms": 0.0, "error": None}

    try:
        model, names, _ = load_model(key, verbose=verbose)
    except Exception as e:
        result["error"] = str(e)
        return result

    try:
        t0 = time.time()
        # ultralytics 可以直接吃 路径 或 numpy 数组
        src = str(source) if isinstance(source, (str, Path)) else source
        preds = model.predict(source=src, imgsz=imgsz, verbose=False)
        result["ms"] = (time.time() - t0) * 1000
    except Exception as e:
        result["error"] = str(e)
        return result

    p = preds[0].probs.data.cpu().numpy()
    order = np.argsort(p)[::-1]

    result["topk"] = [(names[int(i)], float(p[int(i)])) for i in order[:topk]]
    top1 = int(order[0])
    result["conf"] = float(p[top1])
    result["name"] = names[top1]
    result["ok"] = result["conf"] >= threshold
    return result


def predict_paths(paths, key=None, **kw):
    """批量推理一组路径。每张图的结果里会多一个 "path" 字段。"""
    out = []
    for p in paths:
        r = predict(p, key=key, **kw)
        r["path"] = str(p)
        out.append(r)
    return out
