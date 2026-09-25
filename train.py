import shutil
import sys
import time
import config
from ultralytics import YOLO

ROOT = config.ROOT
INFO = config.get_model_info()      # 当前激活模型的配置（见 config.ACTIVE_MODEL）

# ==============================================================================
# 训练配置 —— 想调参，改这里就够了
# 数据集和训练代号从 config.py 取，避免两处对不上
# ==============================================================================
CONFIG = {
    # 预训练权重：从哪个模型开始微调（不是训练产物）
    "pretrained": ROOT / "weights" / "yolo11n-cls.pt",

    # 以下两项来自 config.py，要改数据集/代号请去 config.py 改
    "data": INFO["dataset"],        # 里面必须有 train/ 和 val/，各自按类别分文件夹
    "name": INFO["run"],            # 训练代号，决定 runs/<name>/ 和 models/<name>/

    # 训练轮数
    "epochs": 100,

    # 输入图片尺寸（正方形边长）
    "imgsz": 224,

    # 批大小：越大越快但越吃内存。CPU 上 16 比较稳，报内存不足就改成 8
    "batch": 16,

    # 数据加载的并行进程数。报多进程相关的错误就改成 0
    "workers": 8,

    # 随机种子。固定住保证结果可复现
    "seed": 0,

    # ---- 数据增强 ----
    # ultralytics 默认 hsv_s=0.7（±70%）、auto_augment=randaugment，会破坏颜色信号
    "hsv_h": 0.0,             # 色相不许乱动（默认 0.015 = ±5.4°）
    "hsv_s": 0.2,             # ★ 饱和度只轻微抖（默认 0.7 = ±70%，太狠）
    "hsv_v": 0.3,             # 亮度保留（默认 0.4）
    "auto_augment": None,     # ⚠️ 必须写 None。写字符串 "none" 会抛 ValueError
    "erasing": 0.15,          # 默认 0.4 太容易把果实整个遮掉
    "fliplr": 0.5,            # 随机水平翻转
    "patience": 10,           # 连续 10 轮验证集没提升就早停
}


# ==============================================================================
# 小工具：打印带框的标题
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
    """确认在用哪个 Python、有没有显卡。解释器选错是最常见的失败原因。"""
    title("第 1 步 / 环境检查")

    import torch
    import ultralytics

    print(f"  Python          {sys.version.split()[0]}")
    print(f"  PyTorch         {torch.__version__}")
    print(f"  Ultralytics     {ultralytics.__version__}")
    print(f"  解释器路径      {sys.executable}")
    if torch.cuda.is_available():
        print(f"  计算设备        GPU  {torch.cuda.get_device_name(0)}")
    else:
        print(f"  计算设备        CPU（torch 是 {torch.__version__}，没有 CUDA 支持）")


# ==============================================================================
# 第 2 步：数据集体检
# ==============================================================================
def check_dataset():
    """花 2 秒确认数据没问题，免得白跑十几分钟。返回类别名列表，有问题返回 None。"""
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

        # sorted() 固定类别编号顺序：否则同一批数据每次跑出来的标签编号可能不同
        counts = {}
        for c in sorted([p.name for p in d.iterdir() if p.is_dir()]):
            counts[c] = len([f for f in (d / c).iterdir()
                             if f.is_file() and f.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp")])

        per_split[split] = counts
        print(f"\n  {split} 集: {len(counts)} 个类别, 共 {sum(counts.values())} 张")
        for c, n in counts.items():
            print(f"      {c:<8} {n:>4} 张")

        if sum(counts.values()) == 0:
            print(f"  [错误] {split} 集里一张图都没有")
            return None

    # train 和 val 的类别必须一字不差地一致，否则"第 3 号类别"两边指的不是同一个东西
    tr, va = per_split["train"], per_split["val"]
    if sorted(tr) != sorted(va):
        print("\n  [错误] train 和 val 的类别不一致！")
        print(f"    只在 train 里有的: {sorted(set(tr) - set(va))}")
        print(f"    只在 val 里有的  : {sorted(set(va) - set(tr))}")
        return None

    class_names = sorted(tr)
    print("\n  类别编号表（这个顺序就是标签编号，务必固定）:")
    for i, c in enumerate(class_names):
        print(f"      {i:>2} -> {c}")
    print("\n  ✓ 数据检查通过")
    return class_names


# ==============================================================================
# 第 3 步：训练
# ==============================================================================
def train():
    """加载预训练权重 → 微调。"""
    title("第 3 步 / 开始训练")

    print(f"  模型代号        {CONFIG['name']}   (config.ACTIVE_MODEL = {config.ACTIVE_MODEL})")
    print(f"  预训练权重      {CONFIG['pretrained'].name}")
    print(f"  数据集          {CONFIG['data']}")
    print(f"  轮数 (epochs)   {CONFIG['epochs']}   早停 patience={CONFIG['patience']}")
    print(f"  输入尺寸        {CONFIG['imgsz']} × {CONFIG['imgsz']}")
    print(f"  批大小 (batch)  {CONFIG['batch']}")
    print(f"  训练日志目录    runs/{CONFIG['name']}/")
    print()

    model = YOLO(str(CONFIG["pretrained"]))

    # 【真正的训练】—— 就这一行
    model.train(
        data=str(CONFIG["data"]),
        epochs=CONFIG["epochs"],
        imgsz=CONFIG["imgsz"],
        batch=CONFIG["batch"],
        project=str(ROOT / "runs"),
        name=CONFIG["name"],
        exist_ok=True,
        seed=CONFIG["seed"],
        workers=CONFIG["workers"],
        patience=CONFIG["patience"],
        # ---- 数据增强（说明见上面 CONFIG）----
        hsv_h=CONFIG["hsv_h"],
        hsv_s=CONFIG["hsv_s"],
        hsv_v=CONFIG["hsv_v"],
        auto_augment=CONFIG["auto_augment"],
        erasing=CONFIG["erasing"],
        fliplr=CONFIG["fliplr"],
    )

    # 每轮结束 YOLO 都会在验证集上测一次，把"历史最好"存成 best.pt
    best = ROOT / "runs" / CONFIG["name"] / "weights" / "best.pt"
    return best


# ==============================================================================
# 第 4 步：归档产物
# ==============================================================================
def save_model(best_path):
    """把 best.pt 复制到 models/<代号>/。这个路径由 config.py 推导，不会对不上。"""
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
    print(f"              （predict.py 读的就是这个路径）")
    return out_dir


# ==============================================================================
# 第 5 步：评估
# ==============================================================================
def evaluate(best_path):
    """拿存下来的 best.pt 在验证集上跑一遍，报告 top1 / top5。"""
    title("第 5 步 / 评估")

    if not best_path.exists():
        print(f"  [跳过] 找不到模型: {best_path}")
        return

    metrics = YOLO(str(best_path)).val(data=str(CONFIG["data"]), split="val")

    # ultralytics 不同版本字段名略有差异，用 getattr 兼容
    print()
    if (top1 := getattr(metrics, "top1", None)) is not None:
        print(f"  验证集 top1 精度:  {top1 * 100:.2f}%")
    if (top5 := getattr(metrics, "top5", None)) is not None:
        print(f"  验证集 top5 精度:  {top5 * 100:.2f}%")


# ==============================================================================
# 主流程
# ==============================================================================
def main():
    started = time.time()

    print("=" * 78)
    print(f"  图像分类训练 —— {CONFIG['name']}")
    print(f"  项目根目录: {ROOT}")
    print("=" * 78)

    check_environment()

    if not check_dataset():
        print("\n>>> 数据检查未通过，已停止。请修好数据再运行。")
        return 1

    best = train()
    out_dir = save_model(best)
    evaluate(best)

    title("全部完成")
    print(f"  总耗时      {(time.time() - started) / 60:.1f} 分钟")
    print(f"  模型        {out_dir / 'best.pt'}")
    print(f"  训练日志    {ROOT / 'runs' / CONFIG['name']}")
    print()
    print("  下一步：python predict.py")
    return 0


# Windows 上用多进程加载数据必须有这个保护，否则子进程会反复导入本文件
if __name__ == "__main__":
    sys.exit(main())
