"""
两层推理核心 —— 命令行(detect.py)、Web 服务(server/app.py) 共用这一份。

    第 1 层  检测   models/persimmon_det_v1/best.pt   找出柿子在哪儿（1 个类别）
    第 2 层  分类   models/persimmon_cls_v1/best.pt   把框裁出来判成熟度（4 个类别）

【对外三个函数】

    load(verbose=True)          启动时调一次，预加载两个模型
    predict(frame, key=None)    喂一张 numpy 图(BGR)，返回标准结果 dict
    read_image(path)            读图片（能处理中文路径）

【predict() 返回什么 —— 这就是前后端的接口契约】

    {
      "ok": true,
      "image": {"width": 1280, "height": 1714},
      "detections": [
        {
          "box": [392, 754, 833, 1129],       # 像素坐标 x1,y1,x2,y2
          "det_conf": 0.976,                   # 第 1 层的置信度
          "ripeness": "3_coloring",            # 第 2 层类别（英文，给程序用）
          "ripeness_label": "着色期（橙红）",   # 中文，给界面用
          "ripeness_conf": 0.897               # 第 2 层的置信度
        }
      ],
      "counts": {"1_unripe": 0, "2_turning": 0, "3_coloring": 6, "4_full": 0},
      "timing": {"detect_ms": 42.1, "classify_ms": 86.3},
      "error": null
    }

【为什么这里要有一把锁】

    只有一块 GPU，而 PyTorch 不是线程安全的。多个 Web 请求同时进来时，
    并发调用 model.predict() 会结果错乱甚至直接崩。
    所以用一把全局锁把推理串行化 —— 并发的本质变成"排队"。
    单卡场景这是正确的取舍（要真并发得上多卡或专用模型服务框架）。
"""

import threading
import time

import numpy as np

from ai import config
from ai import engine

DET_IMGSZ = 640                      # 检测输入尺寸，必须和训练时一致

RIPENESS_CLASSES = ["1_unripe", "2_turning", "3_coloring", "4_full"]

_LOCK = threading.Lock()             # 单卡 GPU 串行化
_DET = {}                            # 检测模型缓存：{品种: model}，每个品种只加载一次


# ==============================================================================
# 读图（cv2.imread 读不了中文路径，必须用 imdecode）
# ==============================================================================
def read_image(path):
    """读一张图，返回 BGR numpy 数组；读不出来返回 None。"""
    import cv2
    try:
        buf = np.fromfile(str(path), dtype=np.uint8)
        return cv2.imdecode(buf, cv2.IMREAD_COLOR)
    except Exception:
        return None


# ==============================================================================
# 模型加载
# ==============================================================================
def load_detector(key=None, verbose=True):
    """加载指定品种的第 1 层检测模型（同一品种只加载一次，按品种缓存）。"""
    key = key or config.ACTIVE_MODEL
    info = config.get_model_info(key)
    weights = info.get("det")

    if weights is None:
        raise RuntimeError(
            f"品种 {key!r}（{info['label']}）没有检测模型，只能整图分类，不能做上传识别。\n"
            f"       可用于上传识别的品种：{config.list_species()}"
        )
    if not weights.exists():
        raise FileNotFoundError(
            f"找不到品种 {key!r} 的检测模型：{weights}\n"
            f"       请先训练：python -m ai.train_detect"
        )

    if key not in _DET:
        from ultralytics import YOLO
        t0 = time.time()
        _DET[key] = YOLO(str(weights))
        if verbose:
            print(f"检测模型已加载  [{info['label']}]  {weights.name}  ({(time.time() - t0) * 1000:.0f} 毫秒)")
    return _DET[key]


def load(key=None, verbose=True):
    """预加载一个品种的两层模型。服务启动时调一次，之后所有请求复用。"""
    key = key or config.ACTIVE_MODEL
    det = load_detector(key, verbose=verbose)
    engine.load_model(key, verbose=verbose)
    return det


def is_ready(key=None):
    """指定品种的两层模型文件都在不在（给 /health 用的）。"""
    key = key or config.ACTIVE_MODEL
    try:
        info = config.get_model_info(key)
        det = info.get("det")
        return det is not None and det.exists() and engine.is_ready(key)
    except Exception:
        return False


# ==============================================================================
# 第 2 层：按框裁剪
# ==============================================================================
def crop_box(frame, xyxy, margin):
    """按框裁出一块图，四周多留一点边（给分类模型更多上下文）。"""
    h, w = frame.shape[:2]
    x1, y1, x2, y2 = (float(v) for v in xyxy)
    bw, bh = x2 - x1, y2 - y1
    x1 = int(max(0, x1 - bw * margin))
    y1 = int(max(0, y1 - bh * margin))
    x2 = int(min(w, x2 + bw * margin))
    y2 = int(min(h, y2 + bh * margin))
    if x2 - x1 < 4 or y2 - y1 < 4:
        return None
    return frame[y1:y2, x1:x2]


# ==============================================================================
# 内部：真正的两层推理（调用方自己保证加锁）
# ==============================================================================
def _run(frame, key=None):
    key = key or config.ACTIVE_MODEL
    info = config.get_model_info(key)

    det_model = load_detector(key, verbose=False)

    t0 = time.time()
    r = det_model.predict(source=frame, imgsz=DET_IMGSZ,
                          conf=info["conf"],     # 该品种自己的置信度门槛
                          iou=info["iou"],       # NMS 阈值，压重复框
                          verbose=False)[0]
    det_ms = (time.time() - t0) * 1000

    detections = []
    cls_ms = 0.0

    if r.boxes is not None:
        for box in r.boxes:
            xyxy = box.xyxy[0].cpu().numpy()
            crop = crop_box(frame, xyxy, info["margin"])
            if crop is None:
                continue

            # ---- 第 2 层：把裁出来的图喂给成熟度分类模型 ----
            cr = engine.predict(crop, key=key, verbose=False)
            cls_ms += cr["ms"]
            if cr["error"]:
                continue

            detections.append({
                "box": [int(v) for v in xyxy],
                "det_conf": round(float(box.conf[0]), 4),
                "ripeness": cr["name"],
                "ripeness_label": config.label_of(cr["name"]) if cr["ok"] else "未知",
                "ripeness_conf": round(float(cr["conf"]), 4),
            })

    return detections, det_ms, cls_ms


# ==============================================================================
# 对外主接口
# ==============================================================================
def predict(frame, key=None):
    """
    喂一张 numpy 图（BGR），返回契约 dict（结构见文件开头）。

    frame 为 None 或不是有效图片时，返回 ok=False + error 说明。
    """
    if frame is None or not isinstance(frame, np.ndarray) or frame.size == 0:
        return _result(error="图片读不出来（格式不支持或文件损坏）")

    h, w = frame.shape[:2]

    try:
        # 先把该品种的两个模型都解析出来，缺哪个当场报错，而不是跑到一半才崩
        _, names, _ = engine.load_model(key, verbose=False)
        load_detector(key, verbose=False)
    except Exception as e:
        return _result(w, h, error=str(e))

    try:
        # ★ 关键：单卡 GPU 串行化，避免并发请求互相踩
        with _LOCK:
            detections, det_ms, cls_ms = _run(frame, key)
    except Exception as e:
        return _result(w, h, error=f"推理失败：{e}")

    # 统计键跟着该品种的类别走：柿子 4 类、苹果 3 类
    counts = {n: 0 for n in names}
    for d in detections:
        if d["ripeness"] in counts:
            counts[d["ripeness"]] += 1

    out = _result(w, h, detections, counts, det_ms, cls_ms)
    out["species"] = key or config.ACTIVE_MODEL
    return out


def predict_file(path, key=None):
    """给一个图片路径，直接返回结果 dict。"""
    return predict(read_image(path), key=key)


def _result(w=0, h=0, detections=None, counts=None, det_ms=0.0, cls_ms=0.0, error=None):
    return {
        "ok": error is None,
        "image": {"width": w, "height": h},
        "detections": detections or [],
        "counts": counts or {c: 0 for c in RIPENESS_CLASSES},
        "timing": {"detect_ms": round(det_ms, 1), "classify_ms": round(cls_ms, 1)},
        "error": error,
    }


# ==============================================================================
# 直接运行这个文件：命令行快速自测
# ==============================================================================
if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) < 2:
        print(__doc__)
        print("用法： python inference.py 某张图.jpg")
        sys.exit(1)

    load(verbose=True)
    out = predict_file(sys.argv[1])
    print()
    print(json.dumps(out, ensure_ascii=False, indent=2))
