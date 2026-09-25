"""
摄像头实时识别。

    python camera.py                用 config.CAMERA["index"]
    python camera.py 1              临时指定摄像头编号
    python camera.py -m species     临时换模型
    python camera.py --test         自检（不弹窗口，排障用）

键盘：q 退出   s 存图（runs/camera_snapshots/）   + / - 调置信度阈值

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


# ==============================================================================
# 中文字体（OpenCV 的 putText 不认中文，得借 PIL + 字体文件）
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
    """
    在 OpenCV 的 BGR 画面上写中文。
    items: [(文字, (x, y), (B, G, R), 是否加黑底), ...]
    """
    img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)

    for text, pos, color, with_bg in items:
        rgb = (color[2], color[1], color[0])
        if with_bg:
            box = draw.textbbox(pos, text, font=font)
            pad = 6
            draw.rectangle([box[0] - pad, box[1] - pad // 2,
                            box[2] + pad, box[3] + pad // 2], fill=(0, 0, 0))
        draw.text(pos, text, font=font, fill=rgb)

    return cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)


# ==============================================================================
# 颜色（BGR 顺序）
# ==============================================================================
C_OK = (80, 220, 80)        # 识别成功
C_UNKNOWN = (60, 190, 250)  # 未知
C_TEXT = (255, 255, 255)
C_DIM = (170, 170, 170)


# ==============================================================================
# 自检模式（不弹窗口）
# ==============================================================================
def self_check(index=None, key=None):
    """摄像头弹不出窗口时，先用这个确认是摄像头的问题还是 GUI 的问题。"""
    cam = dict(config.CAMERA)
    if index is not None:
        cam["index"] = int(index)

    print("=" * 66)
    print("摄像头自检（不弹窗口）")
    print("=" * 66)

    # 1) 模型
    info = config.get_model_info(key)
    print(f"\n【1】模型")
    print(f"  当前模型    {config.ACTIVE_MODEL}  ({info['label']})")
    print(f"  权重文件    {info['weights']}")
    print(f"  文件存在    {info['weights'].exists()}")
    if not info["weights"].exists():
        print("  ❌ 模型不存在，请先训练，或改 config.py 的 ACTIVE_MODEL")
        return 1
    try:
        _, names, _ = engine.load_model(key, verbose=False)
        print(f"  加载成功    类别 {names}")
    except Exception as e:
        print(f"  ❌ 加载失败  {e}")
        return 1

    # 2) 摄像头
    print(f"\n【2】摄像头 index={cam['index']}")
    cap = cv2.VideoCapture(cam["index"], cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(cam["index"])
    if not cap.isOpened():
        print("  ❌ 打不开。可能：被别的程序占用 / 摄像头开关没开 / 换个编号试试")
        cap.release()
        return 1
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"  ✅ 已打开    {w} x {h}")

    ret, frame = cap.read()
    cap.release()
    if not ret:
        print("  ❌ 能打开但读不到画面")
        return 1
    print(f"  ✅ 读帧成功  画面尺寸 {frame.shape}")

    # 3) 推理
    print(f"\n【3】推理")
    r = engine.predict(frame, key=key, verbose=False)
    if r["error"]:
        print(f"  ❌ 失败 {r['error']}")
        return 1
    print(f"  预测        {config.label_of(r['name'])}  ({r['name']})  {r['conf'] * 100:.1f}%")
    for i, (n, c) in enumerate(r["topk"], 1):
        print(f"    {i}. {config.label_of(n):<10} {c * 100:5.1f}%")
    print(f"  耗时        {r['ms']:.0f} 毫秒（含首次预热）")

    # 4) 连跑几帧看速度
    cap = cv2.VideoCapture(cam["index"], cv2.CAP_DSHOW)
    if cap.isOpened():
        t0 = time.time()
        n = 0
        for _ in range(20):
            ok, f2 = cap.read()
            if ok:
                engine.predict(f2, key=key, verbose=False)
                n += 1
        dt = time.time() - t0
        cap.release()
        if n:
            print(f"  连续 {n} 帧   {dt / n * 1000:.0f} ms/帧  → 约 {n / dt:.0f} FPS")

    print("\n【结论】")
    print("  摄像头和模型都正常 → 没弹窗口的话，是 GUI 层面的问题")
    print("  正常启动请运行：python camera.py")
    return 0


# ==============================================================================
# 实时识别主循环
# ==============================================================================
def run(index=None, key=None):
    cam = dict(config.CAMERA)
    if index is not None:
        cam["index"] = int(index)

    info = config.get_model_info(key)
    threshold = info["threshold"]        # 用该模型自己的阈值，别用全局的

    print("=" * 70)
    print(f"  模型      {info['label']}   ({info['key']})")
    print("=" * 70)
    try:
        engine.load_model(key, verbose=True)
    except Exception as e:
        print(f"\n[错误] {e}")
        return 1

    cap = cv2.VideoCapture(cam["index"])
    if not cap.isOpened():
        print(f"\n[错误] 打不开摄像头 {cam['index']} 号。可能原因：")
        print("       1. 被别的程序占用（微信 / 腾讯会议 / 相机应用）")
        print("       2. 笔记本的摄像头开关或快捷键没开")
        print("       3. 换编号试试：python camera.py 1")
        return 1

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam["width"])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam["height"])
    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    font_big = find_font(32)
    font_small = find_font(19)

    print(f"摄像头      {w} x {h}")
    print("操作        q 退出   s 存图   + / - 调阈值")
    print("开始识别...\n")

    history = deque(maxlen=cam["smooth_n"])
    frames = 0
    total_ms = 0.0
    t_start = time.time()
    snap_dir = config.ROOT / "runs" / "camera_snapshots"

    while True:
        ok, frame = cap.read()
        if not ok:
            print("[警告] 读不到画面，摄像头可能断开了")
            break

        if cam["mirror"]:
            frame = cv2.flip(frame, 1)

        r = engine.predict(frame, key=key, threshold=threshold, verbose=False)
        frames += 1
        total_ms += r["ms"]

        if r["error"]:
            print(f"[警告] 推理失败：{r['error']}")
            break

        # ---- 拒识 + 平滑 ----
        label = r["name"] if r["ok"] else "未知"
        history.append((label, r["conf"]))
        counter = Counter(n for n, _ in history)
        shown_label, _ = counter.most_common(1)[0]
        confs = [c for n, c in history if n == shown_label]
        shown_conf = sum(confs) / len(confs)

        # ---- 画界面 ----
        color = C_UNKNOWN if shown_label == "未知" else C_OK
        disp = config.label_of(shown_label)          # 英文类名 -> 中文
        main_text = (f"{disp}  {shown_conf * 100:.1f}%"
                     if shown_label != "未知"
                     else f"未知  (最高 {r['conf'] * 100:.1f}%)")
        frame = put_chinese(frame, [(main_text, (16, 14), color, True)], font_big)

        lines = [(f"{i}. {config.label_of(n)}  {c * 100:.1f}%",
                  (18, 58 + (i - 1) * 25), C_TEXT, False)
                 for i, (n, c) in enumerate(r["topk"], 1)]
        frame = put_chinese(frame, lines, font_small)

        elapsed = time.time() - t_start
        fps = frames / elapsed if elapsed > 0 else 0
        status = f"阈值 {threshold:.2f}      FPS {fps:.1f}      推理 {total_ms / frames:.0f}ms"
        frame = put_chinese(frame, [(status, (18, h - 34), C_DIM, True)], font_small)

        cv2.imshow("Persimmon Maturity  (q=quit, s=snap, +/- threshold)", frame)

        # ---- 键盘 ----
        key_code = cv2.waitKey(1) & 0xFF
        if key_code == ord("q"):
            break
        elif key_code == ord("s"):
            snap_dir.mkdir(parents=True, exist_ok=True)
            path = snap_dir / time.strftime("snap_%Y%m%d_%H%M%S.jpg")
            cv2.imwrite(str(path), frame)
            print(f"已存图  {path}")
        elif key_code in (ord("+"), ord("=")):
            threshold = min(0.99, round(threshold + 0.05, 2))
            print(f"阈值 -> {threshold:.2f}")
        elif key_code in (ord("-"), ord("_")):
            threshold = max(0.0, round(threshold - 0.05, 2))
            print(f"阈值 -> {threshold:.2f}")

    cap.release()
    cv2.destroyAllWindows()

    elapsed = time.time() - t_start
    if frames:
        print(f"\n本次会话：{elapsed:.0f} 秒，{frames} 帧，"
              f"平均 {frames / elapsed:.1f} FPS，推理 {total_ms / frames:.0f} ms/帧")
    return 0


# ==============================================================================
# 入口
# ==============================================================================
def main():
    args = sys.argv[1:]
    test = "--test" in args
    if test:
        args.remove("--test")

    key, args = config.take_model_arg(args)

    index = None
    if args:
        try:
            index = int(args[0])
        except ValueError:
            print(f"[错误] 摄像头编号要是数字，收到 {args[0]!r}")
            return 1

    if test:
        return self_check(index=index, key=key)
    return run(index=index, key=key)


if __name__ == "__main__":
    sys.exit(main())
