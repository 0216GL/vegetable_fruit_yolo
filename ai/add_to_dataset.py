"""
把新图片 / 新标注加进检测数据集。

    python add_to_dataset.py images "C:\\某文件夹"     加图片（自动缩小超大图、自动处理重名）
    python add_to_dataset.py labels "C:\\某文件夹"     加标注（只加能配到图片的，悬空的会列出来）
    python add_to_dataset.py check                    检查当前配对情况

为什么要有这个脚本：
    ① 你标注用的原图常常是 27 MP 的相机原图（一张 14 MB），十几张就 200 MB。
       训练最多用到 1280 像素，所以这里会自动把长边缩到 1920，体积降到 1/10 左右。
       YOLO 标注是【归一化坐标】（都除以了宽高），所以缩放不会让标注错位。
    ② 图片和标注必须【文件名一一对应】。这个脚本会检查，避免出现"漏标被当成背景图"。

注意：图片放哪、Split 是 train 还是 val，这里统一进 train。
      要放 val，自己把文件从 images\\train 挪到 images\\val 就行。
"""

import shutil
import sys
from pathlib import Path

import numpy as np
import cv2

from ai import config

DET = config.DETECT["dataset"]
MAX_SIDE = 1920          # 长边超过这个就缩小（够 imgsz=1280 训练用）
JPG_QUALITY = 92


def imread_u(path):
    """cv2.imread 读不了中文路径，用 imdecode 代替。"""
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)


def imwrite_u(path, img):
    """cv2.imwrite 写不了中文路径，用 imencode 代替。"""
    ok, buf = cv2.imencode(Path(path).suffix or ".jpg", img,
                           [cv2.IMWRITE_JPEG_QUALITY, JPG_QUALITY])
    if ok:
        buf.tofile(str(path))
    return ok


def existing_stems():
    """数据集里已有的所有图片名（不含扩展名），用来防止重名覆盖。"""
    out = {}
    for split in ("train", "val"):
        d = DET / "images" / split
        if d.is_dir():
            for p in d.iterdir():
                if p.is_file():
                    out.setdefault(p.stem, []).append(split)
    return out


# ==============================================================================
# 加图片
# ==============================================================================
def add_images(src_dir):
    src = Path(src_dir)
    if not src.is_dir():
        print(f"[错误] 找不到文件夹：{src}")
        return 1

    dst = DET / "images" / "train"
    dst.mkdir(parents=True, exist_ok=True)

    files = sorted(p for p in src.rglob("*")
                   if p.is_file() and p.suffix.lower() in config.IMAGE_EXT)
    if not files:
        print(f"[错误] 这个文件夹里没有图片：{src}")
        return 1

    known = existing_stems()
    added = skipped = shrunk = 0
    renamed = []

    print(f"源目录：{src}")
    print(f"找到 {len(files)} 张图\n")

    for f in files:
        stem = f.stem
        if stem in known:
            print(f"  [跳过] 数据集里已有同名图：{f.name}")
            skipped += 1
            continue

        img = imread_u(f)
        if img is None:
            print(f"  [跳过] 读不出来（格式不支持或文件损坏）：{f.name}")
            skipped += 1
            continue

        h, w = img.shape[:2]
        out_name = f.name
        if max(h, w) > MAX_SIDE:
            s = MAX_SIDE / max(h, w)
            img = cv2.resize(img, (int(w * s), int(h * s)), interpolation=cv2.INTER_AREA)
            h2, w2 = img.shape[:2]
            print(f"  [缩小] {f.name:<34} {w}x{h} -> {w2}x{h2}")
            shrunk += 1

        # 统一存成 jpg（png 也转，省体积；标注是归一化的，不受影响）
        out_name = Path(out_name).stem + ".jpg"
        if not imwrite_u(dst / out_name, img):
            print(f"  [失败] 写不进去：{out_name}")
            skipped += 1
            continue

        known[stem] = ["train"]
        added += 1
        if Path(f.name).stem != Path(out_name).stem:
            renamed.append((f.name, out_name))

    print()
    print(f"  新增 {added} 张，跳过 {skipped} 张，缩小 {shrunk} 张")
    print(f"  目录 {dst}")
    print()
    print("  下一步：把这些图上传统网工具标注，标完用")
    print('      python add_to_dataset.py labels "导出的文件夹"')
    return 0


# ==============================================================================
# 加标注
# ==============================================================================
def add_labels(src_dir):
    src = Path(src_dir)
    if not src.is_dir():
        print(f"[错误] 找不到文件夹：{src}")
        return 1

    known = existing_stems()
    txts = sorted(src.rglob("*.txt"))
    if not txts:
        print(f"[错误] 这个文件夹里没有 .txt：{src}")
        return 1

    added = orphan = 0
    orphans = []

    print(f"源目录：{src}")
    print(f"找到 {len(txts)} 个标注文件\n")

    for t in txts:
        splits = known.get(t.stem)
        if not splits:
            orphans.append(t.name)
            orphan += 1
            continue

        # 标注里的框，做一次合法性检查
        bad = 0
        nbox = 0
        for line in t.read_text(encoding="utf-8", errors="replace").splitlines():
            parts = line.split()
            if not parts:
                continue
            if len(parts) != 5:
                bad += 1
                continue
            nbox += 1
            try:
                if parts[0] not in ("0", "0.0"):
                    bad += 1
                if not all(0.0 <= float(x) <= 1.0 for x in parts[1:]):
                    bad += 1
            except ValueError:
                bad += 1

        if bad:
            print(f"  [警告] {t.name} 有 {bad} 行不合法（本数据集只有 1 个类别，编号必须是 0）")

        # 图片在哪个 split，标注就放到哪个 split
        for split in splits:
            shutil.copy2(t, DET / "labels" / split / t.name)
        added += 1

    print()
    print(f"  新增标注 {added} 个")
    if orphans:
        print(f"  ⚠️ {orphan} 个标注找不到对应图片（用不了，先列出来）：")
        for o in orphans[:20]:
            print(f"      {o}")
        if orphan > 20:
            print(f"      ... 还有 {orphan - 20} 个")
        print()
        print("  这些通常是：图片没在 images\\train 里。先用 images 模式把图加进来，再重跑这个命令。")
    return 0


# ==============================================================================
# 检查
# ==============================================================================
def check():
    print("=" * 70)
    print("  检测数据集检查")
    print("=" * 70)
    ok = True
    for split in ("train", "val"):
        img_dir, lab_dir = DET / "images" / split, DET / "labels" / split
        imgs = {p.stem for p in img_dir.iterdir() if p.is_file()} if img_dir.is_dir() else set()
        labs = {p.stem for p in lab_dir.glob("*.txt")} if lab_dir.is_dir() else set()

        print(f"\n  {split}:  图片 {len(imgs)}   标注 {len(labs)}")
        if imgs - labs:
            print(f"    [错误] {len(imgs - labs)} 张图没有标注 —— 会被当成背景图，训练前必须处理")
            for x in list(imgs - labs)[:5]:
                print(f"        {x}")
            ok = False
        if labs - imgs:
            print(f"    [错误] {len(labs - imgs)} 个标注没有对应图片")
            for x in list(labs - imgs)[:5]:
                print(f"        {x}")
            ok = False

        nbox = big = small = 0
        for f in lab_dir.glob("*.txt"):
            for line in f.read_text(encoding="utf-8", errors="replace").splitlines():
                p = line.split()
                if len(p) != 5:
                    continue
                nbox += 1
                w = float(p[3])
                if w > 0.30:
                    big += 1
                if w < 0.05:
                    small += 1
        if nbox:
            print(f"    框 {nbox} 个   大目标(宽>30%) {big} 个   小目标(宽<5%) {small} 个")

    print()
    print("  ✓ 配对没问题" if ok else "  ✗ 有问题，见上面")
    return ok


# ==============================================================================
def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    mode = sys.argv[1].lower()
    if mode == "check":
        return 0 if check() else 1
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    if mode == "images":
        return add_images(sys.argv[2])
    if mode == "labels":
        return add_labels(sys.argv[2])
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
