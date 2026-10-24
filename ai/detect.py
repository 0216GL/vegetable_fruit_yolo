"""
两层推理：先找柿子，再判成熟度。

    第 1 层  检测   models/persimmon_det_v1/best.pt   找出每个柿子的位置（1 类，不管成熟度）
    第 2 层  分类   models/persimmon_cls_v1/best.pt   把框里的图裁出来判成熟度

    python detect.py "某张图.jpg"        测单张
    python detect.py "某个文件夹"        测整个文件夹（结果存到 runs/detect_predict/）
    python detect.py -m species ...    换第二层的分类模型
"""

import sys
from pathlib import Path

import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

from ai import config, inference

ROOT = config.ROOT
OUT_DIR = ROOT / "runs" / "detect_predict"


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
# 推理逻辑已经搬到 inference.py —— 命令行 / Web 服务 / 摄像头共用那一份。
# 这个文件只保留「命令行界面」相关的东西：加载提示、画框、三种运行模式。
# ==============================================================================


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
        cls_name = d.get("smooth_class", d["ripeness"])
        conf = d.get("smooth_conf", d["ripeness_conf"])
        label = config.label_of(cls_name) if cls_name != "未知" else "未知"
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
        print(f"    {i}. {d['ripeness_label']:<14} 成熟度置信度 {d['ripeness_conf'] * 100:5.1f}%   "
              f"检测框 ({x1},{y1})-({x2},{y2})  检测置信度 {d['det_conf'] * 100:.1f}%")


# ==============================================================================
# 三种模式
# ==============================================================================
def run_image(path, font, key=None):
    frame = inference.read_image(path)
    if frame is None:
        print(f"[错误] 读不出这张图：{path}")
        return

    out = inference.predict(frame, key=key)
    results = out["detections"]
    det_ms, cls_ms = out["timing"]["detect_ms"], out["timing"]["classify_ms"]
    frame = draw_results(frame, results, font)

    print()
    print("=" * 70)
    print(f"  图片   {path}")
    print("=" * 70)
    summarize(results)
    print(f"\n  耗时  检测 {det_ms:.0f} ms + 分类 {cls_ms:.0f} ms")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out_path = OUT_DIR / f"{Path(path).stem}_det.jpg"
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 92])
    if ok:
        buf.tofile(str(out_path))
    print(f"  结果图 {out_path}")


def run_folder(folder, font, key=None):
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
        frame = inference.read_image(f)
        if frame is None:
            print(f"  [跳过] 读不出 {f.name}")
            continue
        out = inference.predict(frame, key=key)
        results = out["detections"]
        total_boxes += len(results)
        vis = draw_results(frame, results, font)
        ok, buf = cv2.imencode(".jpg", vis, [cv2.IMWRITE_JPEG_QUALITY, 92])
        if ok:
            buf.tofile(str(OUT_DIR / f"{f.stem}_det.jpg"))

        labels = ", ".join(f"{d['ripeness_label']}({d['ripeness_conf'] * 100:.0f}%)" for d in results) or "无"
        print(f"  {f.name:<34} {len(results)} 个   {labels}")

    print()
    print(f"  共 {total_boxes} 个框，结果图存到 {OUT_DIR}")


# ==============================================================================
# 主流程
# ==============================================================================
def main():
    key, args = config.take_model_arg(sys.argv[1:])

    # 必须显式给一个图片路径或文件夹（摄像头实时识别已暂停，专注服务器部署）
    if not args:
        print("用法：")
        print("  python -m ai.detect \"某张图.jpg\"      测单张")
        print("  python -m ai.detect \"某个文件夹\"       测整个文件夹")
        print("  python -m ai.detect -m species <路径>  换第二层的分类模型")
        return 1
    target = args[0]

    info = config.get_model_info(key)
    print("=" * 70)
    print(f"  第 1 层  检测     {config.DETECT['weights']}")
    print(f"  第 2 层  分类     {info['weights']}   ({info['label']})")
    print("=" * 70)

    try:
        inference.load(verbose=True)
    except Exception as e:
        print(f"\n[错误] {e}")
        return 1

    font = find_font(22)

    p = Path(target)
    if not p.exists():
        print(f"\n[错误] 路径不存在：{p}")
        return 1
    if p.is_dir():
        run_folder(p, font, key)
    else:
        run_image(p, font, key)
    return 0


if __name__ == "__main__":
    sys.exit(main())
