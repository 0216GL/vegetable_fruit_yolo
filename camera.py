# -*- coding: utf-8 -*-
"""
蔬菜水果 12 类图像分类 —— 摄像头实时识别
================================================================================

【这个脚本干什么】

    打开你电脑的摄像头，把画面里的东西实时识别出来，结果显示在画面上。

    ★ 它不训练。模型是 train.py 训好存在 models/ 里的。
    ★ 它复用 predict.py 的模型加载和拒识阈值设置，参数只有一份。

【怎么运行】

    PyCharm 里直接点绿三角
    或者命令行： python camera.py
    指定别的摄像头： python camera.py 1

【操作】

    q      退出
    s      把当前画面存成图片（存到 runs/camera_snapshots/）
    + / -  调高 / 调低置信度阈值（实时生效，屏幕右上角会显示当前值）

【画面长什么样】

    ┌────────────────────────────────────┐
    │  苹果  97.3%                        │  ← 左上角，识别结果
    │  1. 苹果 97.3%                      │  ← 详细排名
    │  2. 梨    1.8%                      │
    │  3. 香蕉  0.5%                      │
    │                                    │
    │        （摄像头画面）                │
    │                                    │
    │  阈值 0.60          FPS 23.5  推理 31ms │  ← 状态栏
    └────────────────────────────────────┘

【重要说明】

    ⚠️ 分类模型回答的是"整张图是什么"，不是"东西在哪"。
       所以画面里【没有框】，只有左上角一行字。
       想要框，需要另外的检测模型（那是下一步的事）。

    ⚠️ 训练数据是"白底商品图"，摄像头看到的是"真实环境"。
       背景差异会让精度明显下降。演示时把东西放在白纸/白盘子上，效果好很多。
"""

import os
import sys
import time
from collections import Counter, deque
from pathlib import Path

import numpy as np

# ==============================================================================
# 第 0 步：路径与环境（和 train.py / predict.py 保持一致）
# ==============================================================================
ROOT = Path(__file__).resolve().parent

os.environ["YOLO_CONFIG_DIR"] = str(ROOT / ".ultralytics")
os.environ["MPLCONFIGDIR"] = str(ROOT / ".mplcache")
(ROOT / ".ultralytics" / "Ultralytics").mkdir(parents=True, exist_ok=True)
(ROOT / ".mplcache").mkdir(parents=True, exist_ok=True)

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import cv2
from PIL import Image, ImageDraw, ImageFont

# 复用 predict.py 的模型加载和阈值配置 —— 参数只维护一份
import predict as P


# ==============================================================================
# 摄像头配置
# ==============================================================================
CAM = {
    # 用哪个摄像头。0 一般是笔记本自带，1 是外接的。命令行可以覆盖。
    "index": 0,

    # 期望的采集分辨率。设小一点能提高帧率。
    "width": 640,
    "height": 480,

    # 画面是否镜像。自己看着自然（像照镜子），对识别没有影响，
    # 因为训练时用了随机左右翻转（fliplr=0.5），模型对镜像不敏感。
    "mirror": True,

    # 显示出来的画面是否放大。1.0 = 原始大小。
    "zoom": 1.0,
}

# 结果平滑：保存最近 N 帧的识别结果，显示出现次数最多的那个。
# 不加这个的话，画面上的标签会每帧乱跳，看着很烦。
SMOOTH_N = 5

# 中文字体候选（Windows 自带）。按顺序找，找到第一个能用的。
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",      # 微软雅黑
    r"C:\Windows\Fonts\msyhbd.ttc",    # 微软雅黑 粗体
    r"C:\Windows\Fonts\simhei.ttf",    # 黑体
    r"C:\Windows\Fonts\simsun.ttc",    # 宋体
]

# 颜色（BGR 顺序，不是 RGB）
COLOR_OK = (80, 220, 80)        # 识别成功 —— 绿
COLOR_UNKNOWN = (60, 190, 250)  # 判为未知 —— 橙
COLOR_TEXT = (255, 255, 255)    # 普通文字 —— 白
COLOR_DIM = (170, 170, 170)     # 次要文字 —— 灰
COLOR_BG = (0, 0, 0)            # 文字背景条 —— 黑


# ==============================================================================
# 中文字体加载
# ==============================================================================
def find_font(size):
    """
    找一个能显示中文的字体。

    为什么要这一步：OpenCV 自带的 cv2.putText 只认 ASCII，
    写"苹果"会变成一串问号。所以要借 PIL 来写中文，而 PIL 需要字体文件。
    """
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size), path
            except Exception:
                continue
    # 全找不到就退回 PIL 默认字体（中文会变方块，但至少不崩）
    return ImageFont.load_default(), None


# ==============================================================================
# 在画面上写中文
# ==============================================================================
def put_chinese(frame, items, font):
    """
    在 OpenCV 的 BGR 画面上写中文。

    做法：BGR → RGB → PIL 图像 → 用 PIL 写字 → 转回 BGR。
    比 cv2.putText 慢一点点（几毫秒），但这是让中文正常显示的标准办法。

    items: [(文字, 左上角坐标, 颜色, 是否加黑底), ...]
    """
    # OpenCV 是 BGR，PIL 要 RGB，转换一下
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)

    for text, pos, color, with_bg in items:
        # PIL 的颜色要 RGB，把 BGR 反过来
        rgb = (color[2], color[1], color[0])

        if with_bg:
            # 加一条半透明黑底，避免文字和背景撞色看不清
            box = draw.textbbox(pos, text, font=font)
            pad = 6
            draw.rectangle(
                [box[0] - pad, box[1] - pad // 2, box[2] + pad, box[3] + pad // 2],
                fill=COLOR_BG,
            )

        draw.text(pos, text, font=font, fill=rgb)

    # 转回 OpenCV 的 BGR
    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


# ==============================================================================
# 对一帧画面做识别
# ==============================================================================
def infer_frame(model, names, frame, imgsz):
    """
    输入一帧画面（numpy 数组），输出识别结果。

    注意：模型可以直接吃 numpy 数组，不需要先存成文件再读 ——
    这是实时识别能跑起来的前提。
    """
    t0 = time.time()
    preds = model.predict(source=frame, imgsz=imgsz, verbose=False)
    ms = (time.time() - t0) * 1000

    p = preds[0].probs.data.cpu().numpy()
    order = np.argsort(p)[::-1]

    return {
        "name": names[int(order[0])],
        "conf": float(p[int(order[0])]),
        "topk": [(names[int(i)], float(p[int(i)])) for i in order[:3]],
        "ms": ms,
    }


# ==============================================================================
# 主循环
# ==============================================================================
def main():
    # 命令行可以覆盖摄像头编号
    if len(sys.argv) > 1:
        CAM["index"] = int(sys.argv[1])

    # ---- 加载模型 ----
    model, names = P.load()
    threshold = P.CONFIG["conf_threshold"]
    imgsz = P.CONFIG["imgsz"]

    # ---- 打开摄像头 ----
    cap = cv2.VideoCapture(CAM["index"])
    if not cap.isOpened():
        print(f"\n[错误] 打不开摄像头 {CAM['index']} 号。")
        print("       可能原因：")
        print("         1. 摄像头被别的程序占用（微信/腾讯会议/相机应用等）")
        print("         2. 笔记本有物理摄像头开关或快捷键没打开")
        print("         3. 换个编号试试：python camera.py 1")
        return 1

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAM["width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAM["height"])
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    print(f"摄像头已打开  {w} x {h}")
    print(f"屏幕操作:  q 退出   s 存图   + / - 调阈值")
    print(f"开始识别...\n")

    font_big, font_path = find_font(34)
    font_small, _ = find_font(20)
    if font_path:
        print(f"中文字体      {font_path}")
    else:
        print("中文字体      未找到（中文会显示成方块，但程序正常运行）")

    # ---- 运行状态 ----
    history = deque(maxlen=SMOOTH_N)   # 最近几帧的结果，用于平滑
    frames = 0
    total_ms = 0.0
    t_start = time.time()
    snap_dir = ROOT / "runs" / "camera_snapshots"

    while True:
        ok, frame = cap.read()
        if not ok:
            print("[警告] 读不到画面，摄像头可能被拔掉了")
            break

        if CAM["mirror"]:
            frame = cv2.flip(frame, 1)

        # ---- 识别 ----
        r = infer_frame(model, names, frame, imgsz)
        frames += 1
        total_ms += r["ms"]

        # ---- 拒识：低于阈值就记成"未知" ----
        label = r["name"] if r["conf"] >= threshold else "未知"
        history.append((label, r["conf"]))

        # ---- 平滑：最近几帧里出现次数最多的那个 ----
        counter = Counter(name for name, _ in history)
        shown_label, votes = counter.most_common(1)[0]
        confs = [c for name, c in history if name == shown_label]
        shown_conf = sum(confs) / len(confs)

        # ---- 画界面 ----
        color = COLOR_UNKNOWN if shown_label == "未知" else COLOR_OK

        # 左上角：主结果（大字）
        main_text = (f"{shown_label}  {shown_conf * 100:.1f}%"
                     if shown_label != "未知"
                     else f"未知  (最高仅 {r['conf'] * 100:.1f}%)")
        frame = put_chinese(frame, [(main_text, (16, 14), color, True)], font_big)

        # 第二行开始：前三名
        lines = []
        for i, (n, c) in enumerate(r["topk"], 1):
            lines.append((f"{i}. {n}  {c * 100:.1f}%", (18, 62 + (i - 1) * 26), COLOR_TEXT, False))
        frame = put_chinese(frame, lines, font_small)

        # 底部状态栏
        elapsed = time.time() - t_start
        fps = frames / elapsed if elapsed > 0 else 0
        status = f"阈值 {threshold:.2f}      FPS {fps:.1f}      推理 {total_ms / frames:.0f}ms"
        frame = put_chinese(frame, [(status, (18, h - 34), COLOR_DIM, True)], font_small)

        # 显示
        if CAM["zoom"] != 1.0:
            frame = cv2.resize(frame, None, fx=CAM["zoom"], fy=CAM["zoom"],
                               interpolation=cv2.INTER_LINEAR)
        cv2.imshow("Vegetable / Fruit Recognition  (q=quit)", frame)

        # ---- 键盘 ----
        key = cv2.waitKey(1) & 0xFF
        if key == ord("q"):
            break
        elif key == ord("s"):
            snap_dir.mkdir(parents=True, exist_ok=True)
            path = snap_dir / time.strftime("snap_%Y%m%d_%H%M%S.jpg")
            cv2.imwrite(str(path), frame)
            print(f"已存图  {path}")
        elif key in (ord("+"), ord("=")):
            threshold = min(0.99, threshold + 0.05)
            P.CONFIG["conf_threshold"] = threshold
        elif key in (ord("-"), ord("_")):
            threshold = max(0.0, threshold - 0.05)
            P.CONFIG["conf_threshold"] = threshold

    # ---- 收尾 ----
    cap.release()
    cv2.destroyAllWindows()

    elapsed = time.time() - t_start
    print()
    print("=" * 60)
    print("  会话统计")
    print("=" * 60)
    print(f"  运行时长      {elapsed:.1f} 秒")
    print(f"  处理帧数      {frames} 帧")
    if frames:
        print(f"  平均帧率      {frames / elapsed:.1f} FPS")
        print(f"  平均推理      {total_ms / frames:.0f} 毫秒/帧")
        print(f"  纯推理上限    {1000 / (total_ms / frames):.1f} FPS")
        print()
        if frames / elapsed >= 20:
            print("  ✅ 帧率充足，CPU 完全够用，不需要 GPU")
        elif frames / elapsed >= 12:
            print("  ⚠️ 帧率可用但不算流畅。想更顺滑可以考虑 CUDA 版 torch")
        else:
            print("  ❌ 帧率偏低。建议装 CUDA 版 torch（约 2 GB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
