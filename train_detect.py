import shutil
import sys
import time

# ⚠️ import config 必须在 import ultralytics 之前（环境变量、中文显示都在里面设）
import config
from ultralytics import YOLO

ROOT = config.ROOT


# ==============================================================================
# 检测训练配置 —— 第一层：只找柿子，不判成熟度
#
# ⚠️ 数据增强【不能照搬分类那套】：
#     分类靠颜色判成熟度 → 所以 hsv_s 压到 0.2、auto_augment 关掉；
#     检测靠形状/纹理定位目标 → 颜色抖动反而帮助泛化，用默认值就好。
# ==============================================================================
CONFIG = {
    # 检测预训练权重（不是 -cls 结尾那个）
    "pretrained": ROOT / "weights" / "yolo11n.pt",

    # 检测数据集必须用 yaml（不是分类那种目录）
    "data": config.DETECT["dataset"] / "dataset.yaml",
    "name": config.DETECT["run"],

    "epochs": 100,
    "imgsz": 640,        # 检测用 640；分类才是 224
    "batch": 8,          # 6 GB 显存 + 640 分辨率，8 比较稳，报内存不足就改 4
    "workers": 8,
    "seed": 0,
    "patience": 20,      # 连续 20 轮验证集没提升就早停

    # ---- 检测的数据增强（保持默认值）----
    "mosaic": 1.0,       # 拼 4 张图，检测的招牌增强，对小目标帮助大
    "close_mosaic": 10,  # 最后 10 轮关掉 mosaic，收尾更稳
    "fliplr": 0.5,
}


# ==============================================================================
# 小工具
# ==============================================================================
def title(text):
    print()
    print("=" * 78)
    print("  " + text)
    print("=" * 78)


def check_dataset():
    """确认图片和标注一一对应、类别编号和坐标都合法。有问题返回 False。"""
    title("第 2 步 / 数据集检查")

    root = config.DETECT["dataset"]
    ok = True

    for split in ("train", "val"):
        img_dir, lab_dir = root / "images" / split, root / "labels" / split
        if not img_dir.is_dir():
            print(f"  [错误] 找不到 {img_dir}")
            return False

        imgs = {p.stem for p in img_dir.iterdir() if p.is_file()}
        labs = {p.stem for p in lab_dir.glob("*.txt")}

        print(f"\n  {split}: 图片 {len(imgs)} 张, 标注 {len(labs)} 个")

        # 没有标注的图会被 ultralytics 当成"背景图"，对训练有害，必须拦下来
        if imgs - labs:
            print(f"  [错误] {len(imgs - labs)} 张图没有对应标注 —— 会被当成背景图，训练前必须处理")
            ok = False
        if labs - imgs:
            print(f"  [错误] {len(labs - imgs)} 个标注没有对应图片")
            ok = False

        # 查框本身
        n_box, bad_cls, bad_xy = 0, 0, 0
        for f in lab_dir.glob("*.txt"):
            for line in f.read_text(encoding="utf-8").splitlines():
                parts = line.split()
                if not parts:
                    continue
                if len(parts) != 5:
                    bad_xy += 1
                    continue
                n_box += 1
                if parts[0] not in ("0", "0.0"):
                    bad_cls += 1
                vals = [float(x) for x in parts[1:]]
                if not all(0.0 <= v <= 1.0 for v in vals):
                    bad_xy += 1

        print(f"        框 {n_box} 个")
        if bad_cls:
            print(f"  [错误] {bad_cls} 个框的类别不是 0 —— 本数据集只有 1 个类别 persimmon")
            ok = False
        if bad_xy:
            print(f"  [错误] {bad_xy} 行坐标不合法（必须 5 个数、归一化到 0~1）")
            ok = False

    print()
    print("  ✓ 数据检查通过" if ok else "  ✗ 数据有问题，见上面")
    return ok


# ==============================================================================
# 第 3 步：训练
# ==============================================================================
def train():
    """加载检测预训练权重 -> 微调成单类别柿子检测器。"""
    title("第 3 步 / 开始训练")

    print(f"  预训练权重      {CONFIG['pretrained'].name}")
    print(f"  数据集          {CONFIG['data']}")
    print(f"  轮数 (epochs)   {CONFIG['epochs']}   早停 patience={CONFIG['patience']}")
    print(f"  输入尺寸        {CONFIG['imgsz']}")
    print(f"  批大小 (batch)  {CONFIG['batch']}")
    print(f"  训练日志目录    runs/detect/{CONFIG['name']}/")
    print()

    model = YOLO(str(CONFIG["pretrained"]))

    # 【真正的训练】—— 就这一行
    model.train(
        data=str(CONFIG["data"]),
        epochs=CONFIG["epochs"],
        imgsz=CONFIG["imgsz"],
        batch=CONFIG["batch"],
        project=str(ROOT / "runs" / "detect"),
        name=CONFIG["name"],
        exist_ok=True,
        seed=CONFIG["seed"],
        workers=CONFIG["workers"],
        patience=CONFIG["patience"],
        mosaic=CONFIG["mosaic"],
        close_mosaic=CONFIG["close_mosaic"],
        fliplr=CONFIG["fliplr"],
    )

    best = ROOT / "runs" / "detect" / CONFIG["name"] / "weights" / "best.pt"
    return best


# ==============================================================================
# 第 4 步：归档产物
# ==============================================================================
def save_model(best_path):
    """把 best.pt 复制到 models/<代号>/。detect.py 读的就是这个路径。"""
    title("第 4 步 / 归档产物")

    out_dir = ROOT / "models" / CONFIG["name"]
    out_dir.mkdir(parents=True, exist_ok=True)

    if not best_path.exists():
        print(f"  [警告] 没找到 best.pt: {best_path}")
        return out_dir

    dst = out_dir / "best.pt"
    shutil.copy2(best_path, dst)
    print(f"  模型文件    {dst}")
    print(f"              大小 {dst.stat().st_size / 2**20:.2f} MB")
    print(f"              （detect.py 读的就是这个路径）")
    return out_dir


# ==============================================================================
# 第 5 步：评估
# ==============================================================================
def evaluate(best_path):
    """在验证集上算 mAP50 / mAP50-95。检测的精度指标和分类不一样。"""
    title("第 5 步 / 评估")

    if not best_path.exists():
        print(f"  [跳过] 找不到模型: {best_path}")
        return

    metrics = YOLO(str(best_path)).val(data=str(CONFIG["data"]), split="val")

    print()
    box = getattr(metrics, "box", None)
    if box is not None:
        print(f"  mAP50        {box.map50 * 100:.2f}%")
        print(f"  mAP50-95     {box.map * 100:.2f}%")
        print(f"  精确率       {box.mp * 100:.2f}%")
        print(f"  召回率       {box.mr * 100:.2f}%")


# ==============================================================================
# 主流程
# ==============================================================================
def main():
    started = time.time()

    print("=" * 78)
    print(f"  柿子检测训练（第一层）—— {CONFIG['name']}")
    print(f"  项目根目录: {ROOT}")
    print("=" * 78)

    import torch
    import ultralytics

    title("第 1 步 / 环境检查")
    print(f"  Python          {sys.version.split()[0]}")
    print(f"  PyTorch         {torch.__version__}")
    print(f"  Ultralytics     {ultralytics.__version__}")
    print(f"  解释器路径      {sys.executable}")
    if torch.cuda.is_available():
        print(f"  计算设备        GPU  {torch.cuda.get_device_name(0)}")
    else:
        print(f"  计算设备        CPU（会很慢）")

    if not check_dataset():
        print("\n>>> 数据检查未通过，已停止。")
        return 1

    best = train()
    out_dir = save_model(best)
    evaluate(best)

    title("全部完成")
    print(f"  总耗时      {(time.time() - started) / 60:.1f} 分钟")
    print(f"  模型        {out_dir / 'best.pt'}")
    print(f"  训练日志    {ROOT / 'runs' / 'detect' / CONFIG['name']}")
    print()
    print("  下一步：python detect.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
