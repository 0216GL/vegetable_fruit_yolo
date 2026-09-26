"""
两层推理：先找柿子，再判成熟度。

    第 1 层  检测   models/persimmon_det_v1/best.pt   找出每个柿子的位置（1 类，不管成熟度）
    第 2 层  分类   models/persimmon_cls_v1/best.pt   把框里的图裁出来判成熟度

    python detect.py                   开摄像头（默认，等价于 detect.py 0）
    python detect.py 1                 换摄像头编号（1 = 外接）
    python detect.py "某张图.jpg"        测单张
    python detect.py "某个文件夹"        测整个文件夹（结果存到 runs/detect_predict/）
    python detect.py -m species ...    换第二层的分类模型

摄像头模式键盘：q 退出   s 存图
"""

import sys
import time
from collections import Counter, deque
from pathlib import Path

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

import config
import engine

ROOT = config.ROOT
OUT_DIR = ROOT / "runs" / "detect_predict"
DET_IMGSZ = 640      # 检测的输入尺寸，必须和训练时一致


# ==============================================================================
# 在 OpenCV 画面上写中文（putText 不认中文，得借 PIL + 字体文件）
# ==============================================================================
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
]


def find_font(size):
    for path in FONT_CANDIDATES:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    return ImageFont.load_default()


def put_chinese(frame, items, font):
    """items: [(文字, (x, y), (B, G, R), 是否加黑底), ...]"""
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)

    for text, pos, color, with_bg in items:
        rgb = (color[2], color[1], color[0])
        if with_bg:
            box = draw.textbbox(pos, text, font=font)
            pad = 5
            draw.rectangle([box[0] - pad, box[1] - pad // 2,
                            box[2] + pad, box[3] + pad // 2], fill=(0, 0, 0))
        draw.text(pos, text, font=font, fill=rgb)

    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


# ==============================================================================
# 第 1 层：检测模型
# ==============================================================================
_DET = {}


def load_detector(verbose=True):
    """加载柿子检测模型（同一个进程只加载一次）。"""
    weights = config.DETECT["weights"]
    if not weights.exists():
        raise FileNotFoundError(
            f"找不到检测模型：{weights}\n"
            f"       请先训练：python train_detect.py"
        )
    if "m" not in _DET:
        from ultralytics import YOLO
        t0 = time.time()
        _DET["m"] = YOLO(str(weights))
        if verbose:
            print(f"检测模型已加载  {weights.name}  ({(time.time() - t0) * 1000:.0f} 毫秒)")
    return _DET["m"]


# ==============================================================================
# 第 2 层：裁剪 + 分类
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


def detect_and_classify(frame, det_model, key=None):
    """
    两层推理。返回 (结果列表, 检测耗时ms, 分类耗时ms)
    每项: {"box": (x1,y1,x2,y2), "det_conf": float, "name": str, "label": str, "conf": float}
    """
    t0 = time.time()
    r = det_model.predict(source=frame, imgsz=DET_IMGSZ,
                          conf=config.DETECT["conf"],
                          iou=config.DETECT["iou"],        # NMS 阈值，压重复框
                          verbose=False)[0]
    det_ms = (time.time() - t0) * 1000

    results = []
    cls_ms = 0.0

    if r.boxes is None or len(r.boxes) == 0:
        return results, det_ms, cls_ms

    for box in r.boxes:
        xyxy = box.xyxy[0].cpu().numpy()
        crop = crop_box(frame, xyxy, config.DETECT["margin"])
        if crop is None:
            continue
        # ---- 第 2 层：裁出来的图喂给成熟度分类模型 ----
        cr = engine.predict(crop, key=key, verbose=False)
        cls_ms += cr["ms"]
        if cr["error"]:
            continue
        results.append({
            "box": tuple(int(v) for v in xyxy),
            "det_conf": float(box.conf[0]),
            "name": cr["name"],
            "label": config.label_of(cr["name"]) if cr["ok"] else "未知",
            "conf": cr["conf"],
        })
    return results, det_ms, cls_ms


# ==============================================================================
# 画框 + 写成熟度
# ==============================================================================
C_OK = (80, 220, 80)        # 判出来了
C_UNKNOWN = (60, 190, 250)  # 未知


def draw_results(frame, results, font):
    items = []
    for d in results:
        x1, y1, x2, y2 = d["box"]
        # 摄像头模式下用平滑后的结果（没有平滑时退回原始结果）
        name = d.get("smooth_label", d["name"])
        conf = d.get("smooth_conf", d["conf"])
        label = config.label_of(name) if d["label"] != "未知" else "未知"
        color = C_UNKNOWN if label == "未知" else C_OK
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        text = f"{label} {conf * 100:.0f}%"
        items.append((text, (x1 + 5, max(6, y1 - 24)), color, True))
    if items:
        frame = put_chinese(frame, items, font)
    return frame


def summarize(results):
    if not results:
        print("  没有检测到柿子")
        return
    print(f"  检测到 {len(results)} 个柿子:")
    for i, d in enumerate(results, 1):
        x1, y1, x2, y2 = d["box"]
        print(f"    {i}. {d['label']:<14} 成熟度置信度 {d['conf'] * 100:5.1f}%   "
              f"检测框 ({x1},{y1})-({x2},{y2})  检测置信度 {d['det_conf'] * 100:.1f}%")


# ==============================================================================
# 三种模式
# ==============================================================================
def run_image(path, det_model, font, key=None):
    frame = cv2.imread(str(path))
    if frame is None:
        print(f"[错误] 读不出这张图：{path}")
        return

    results, det_ms, cls_ms = detect_and_classify(frame, det_model, key)
    frame = draw_results(frame, results, font)

    print()
    print("=" * 70)
    print(f"  图片   {path}")
    print("=" * 70)
    summarize(results)
    print(f"\n  耗时  检测 {det_ms:.0f} ms + 分类 {cls_ms:.0f} ms")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"{Path(path).stem}_det.jpg"
    cv2.imwrite(str(out), frame)
    print(f"  结果图 {out}")


def run_folder(folder, det_model, font, key=None):
    files = sorted(f for f in folder.iterdir()
                   if f.is_file() and f.suffix.lower() in config.IMAGE_EXT)
    if not files:
        print(f"[错误] 这个文件夹里没有图片：{folder}")
        return

    print()
    print("=" * 70)
    print(f"  文件夹   {folder}   共 {len(files)} 张")
    print("=" * 70)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    total_boxes = 0
    for f in files:
        frame = cv2.imread(str(f))
        if frame is None:
            print(f"  [跳过] 读不出 {f.name}")
            continue
        results, det_ms, cls_ms = detect_and_classify(frame, det_model, key)
        total_boxes += len(results)
        frame = draw_results(frame, results, font)
        cv2.imwrite(str(OUT_DIR / f"{f.stem}_det.jpg"), frame)

        labels = ", ".join(f"{d['label']}({d['conf'] * 100:.0f}%)" for d in results) or "无"
        print(f"  {f.name:<34} {len(results)} 个   {labels}")

    print()
    print(f"  共 {total_boxes} 个框，结果图存到 {OUT_DIR}")


# ==============================================================================
# 时序平滑 —— 消掉摄像头里标签乱跳的问题
#
# 原理：同一颗果子在相邻帧里位置差不多，用 IoU 把前后两帧的框关联起来，
#       每个目标保存最近 N 帧的分类结果，显示"N 帧里出现最多的那个"。
#       没有这一步的话，每一帧独立分类，标签会一直闪
#       （一帧"转色期"、下一帧"完熟"）。
# ==============================================================================
def _iou(a, b):
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter <= 0:
        return 0.0
    union = (ax2 - ax1) * (ay2 - ay1) + (bx2 - bx1) * (by2 - by1) - inter
    return inter / union if union > 0 else 0.0


class LabelSmoother:
    """给每个目标维护一小段历史，输出多数投票的结果。"""

    def __init__(self, n=None, thr=0.4):
        self.n = n or config.CAMERA["smooth_n"]
        self.thr = thr
        self.tracks = []        # [{"box":..., "labels": deque, "confs": deque}]

    def smooth(self, results):
        """就地给每个结果补上 smooth_label / smooth_conf 两个字段。"""
        matched = [False] * len(results)
        alive = []

        for t in self.tracks:
            best, bi = 0.0, -1
            for i, d in enumerate(results):
                if matched[i]:
                    continue
                v = _iou(t["box"], d["box"])
                if v > best:
                    best, bi = v, i
            if bi >= 0 and best >= self.thr:
                d = results[bi]
                matched[bi] = True
                t["box"] = d["box"]
                t["labels"].append(d["name"])
                t["confs"].append(d["conf"])
                d["smooth_label"] = Counter(t["labels"]).most_common(1)[0][0]
                d["smooth_conf"] = sum(t["confs"]) / len(t["confs"])
                alive.append(t)

        # 这一帧新出现的目标，开一条新轨迹
        for i, d in enumerate(results):
            if matched[i]:
                continue
            alive.append({"box": d["box"],
                          "labels": deque([d["name"]], maxlen=self.n),
                          "confs": deque([d["conf"]], maxlen=self.n)})
            d["smooth_label"] = d["name"]
            d["smooth_conf"] = d["conf"]

        self.tracks = alive
        return results


# ==============================================================================
# 摄像头
# ==============================================================================
def run_camera(index, det_model, font, key=None):
    cap = cv2.VideoCapture(index)
    if not cap.isOpened():
        print(f"[错误] 打不开摄像头 {index} 号（可能被别的程序占用，或换个编号试试）")
        return

    print("摄像头已打开。q 退出，s 存图。")
    frames = 0
    t_start = time.time()
    smoother = LabelSmoother()

    while True:
        ok, frame = cap.read()
        if not ok:
            print("[警告] 读不到画面")
            break
        if config.CAMERA["mirror"]:
            frame = cv2.flip(frame, 1)

        results, det_ms, cls_ms = detect_and_classify(frame, det_model, key)
        results = smoother.smooth(results)      # 时序平滑，防标签乱跳
        frame = draw_results(frame, results, font)

        frames += 1
        fps = frames / max(1e-6, time.time() - t_start)
        status = f"柿子 {len(results)} 个    检测 {det_ms:.0f}ms + 分类 {cls_ms:.0f}ms    FPS {fps:.1f}"
        frame = put_chinese(frame, [(status, (14, frame.shape[0] - 32), (170, 170, 170), True)], font)

        cv2.imshow("Persimmon Detect + Ripeness  (q=quit, s=snap)", frame)

        k = cv2.waitKey(1) & 0xFF
        if k == ord("q"):
            break
        if k == ord("s"):
            OUT_DIR.mkdir(parents=True, exist_ok=True)
            p = OUT_DIR / time.strftime("snap_%Y%m%d_%H%M%S.jpg")
            cv2.imwrite(str(p), frame)
            print(f"已存图  {p}")

    cap.release()
    cv2.destroyAllWindows()


# ==============================================================================
# 主流程
# ==============================================================================
def main():
    key, args = config.take_model_arg(sys.argv[1:])

    # 不带参数 = 直接开摄像头（和以前的 camera.py 一样，PyCharm 里点绿三角就能开）；
    # 想测图片就显式给一个路径
    target = args[0] if args else str(config.CAMERA["index"])

    info = config.get_model_info(key)
    print("=" * 70)
    print(f"  第 1 层  检测     {config.DETECT['weights']}")
    print(f"  第 2 层  分类     {info['weights']}   ({info['label']})")
    print("=" * 70)

    try:
        det_model = load_detector(verbose=True)
    except Exception as e:
        print(f"\n[错误] {e}")
        return 1

    try:
        engine.load_model(key, verbose=True)
    except Exception as e:
        print(f"\n[错误] 第二层分类模型加载失败：{e}")
        return 1

    font = find_font(22)

    # 纯数字 = 摄像头编号
    if target.isdigit():
        run_camera(int(target), det_model, font, key)
    else:
        p = Path(target)
        if not p.exists():
            print(f"\n[错误] 路径不存在：{p}")
            return 1
        if p.is_dir():
            run_folder(p, det_model, font, key)
        else:
            run_image(p, det_model, font, key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
