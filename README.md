# 柿果成熟度识别 · 蔬菜水果分类

用 Ultralytics **YOLO11n-cls** 做迁移学习，两个相互独立的分类任务：

| 模型 | 任务 | 类别 | 验证集 top-1 |
|---|---|---|---|
| `persimmon` | **柿果成熟度识别**（主项目） | 4 | **84.44%** |
| `species` | 蔬菜水果物种识别（对照/复用） | 12 | **97.95%** |

支持命令行单图/批量预测、摄像头实时识别。全部代码可离线运行，GPU/CPU 皆可。

---

## 快速开始

```bat
conda activate yolo
cd /d D:\vegetable_fruit_yolo
```

> **⚠️ 第一次使用先建数据集**（`dataset_persimmon/` 体积 191 MB，未随仓库上传）：
> ```bat
> python build_dataset_persimmon.py --source "你的分类图片目录"
> ```
> 源目录要求「一个类别一个子文件夹」。如果只是想跑物种模型，可跳过这一步。

```bat
python predict.py "D:\照片\柿子.jpg"          :: 单张预测
python predict.py "dataset_persimmon\val"     :: 整个验证集（自动算逐类准确率）
python camera.py                              :: 摄像头实时识别
python camera.py --test                       :: 摄像头自检（不弹窗口，排障用）
python train.py                               :: 重新训练（改 config 后）
```

切换模型只需改 `config.py` 一行：

```python
ACTIVE_MODEL = "persimmon"     # 或 "species"
```

---

## 结果

### 模型一：柿果成熟度（`fruits_cls_v2`）

| 类别 | 含义 | 验证准确率 |
|---|---|---|
| `1_unripe` | 未熟（青绿） | 26/27 = **96.30%** |
| `2_turning` | 转色期（黄橙） | 16/19 = 84.21% |
| `3_coloring` | 着色期（橙红） | 16/25 = **64.00%** |
| `4_full` | 完熟（深红） | 18/19 = **94.74%** |
| **总体** | | **76/90 = 84.44%** |

- 训练 50 轮耗时 147 秒，模型体积 3.05 MB
- **峰值 84.44% 出现在第 12 轮**，之后回落到 77.78% —— 典型过拟合，`best.pt` 保存的是第 12 轮
- 主要误差：`着色期 → 完熟`（25 张里错 7 张）

### 模型二：蔬菜水果物种（`fruits_cls_v1`）

| 指标 | 数值 |
|---|---|
| 验证集 top-1 | **97.95%**（383/391） |
| 验证集 top-5 | 100.00% |
| 训练耗时 | 13.4 分钟（CPU，50 轮） |
| 模型体积 | 3.07 MB |

作为对照，同一份数据用 **sklearn + 手工特征（HSV 直方图 + HOG）+ SVM** 只能到 **63.68%**，差距来自迁移学习。

---

## 架构

拆成四层，**上下层单向依赖，`predict` 与 `camera` 之间零依赖**：

```
    config.py          所有路径与参数（不依赖任何东西）
        ↑
    engine.py          推理核心：load_model / predict / predict_paths / is_ready
        ↑
  ┌─────┴─────┐
predict.py   camera.py   互不依赖
（图片/批量） （摄像头）
        ↑
   （以后）网页后端 / 小程序 / 检测模块 —— 直接 import engine 即可
```

```python
# 对外接口（engine.py 只有这四个）
import engine

engine.is_ready(key=None)                     -> bool
model, names, info = engine.load_model(key=None)
r = engine.predict(source, key=None, threshold=None, topk=None, imgsz=None)
results = engine.predict_paths([p1, p2, ...])
```

`predict()` 返回：

```python
{
    "ok":    bool,          # 是否被接受（未被拒识）
    "name":  str | None,    # 预测类别名；被拒识时为 None
    "conf":  float,         # 最高置信度 0~1
    "topk":  [(name, p)],   # 前 k 名
    "ms":    float,         # 推理耗时（毫秒）
    "error": str | None,
}
```

> 这样设计的理由：以前模型路径散落在 `predict.py` / `camera.py` 里，改一个忘一个；`camera.py` 还反向修改 `predict.CONFIG`，耦合很别扭。现在配置只有一份，模型注册表在 `config.py`，要加新模型加一项就行。

---

## 目录结构

```
vegetable_fruit_yolo/
├── config.py                       ★ 全部配置：模型注册表/推理参数/摄像头参数/中文类名
├── engine.py                       ★ 推理核心，对外接口
├── predict.py                        图片与文件夹测试（单图 / 批量 / 逐类准确率）
├── camera.py                         摄像头实时识别（--test 为自检模式）
├── train.py                          训练脚本
├── build_dataset_persimmon.py        数据集构建脚本（把分类图片整理成 train/val）
│
├── dataset/                          物种数据集（12 类）【随仓库上传】
│   ├── train/<12类>/                 841 张
│   └── val/<12类>/                   391 张
│
├── dataset_persimmon/                柿果成熟度数据集（4 类）【需用脚本重建】
│   ├── train/{1_unripe,2_turning,3_coloring,4_full}/   107/76/98/75 = 356 张
│   ├── val/...                                         27/19/25/19 = 90 张
│   ├── classes.txt                   类别列表
│   └── split_manifest.csv            446 行划分清单（每张图去了哪）
│
├── weights/yolo11n-cls.pt            预训练权重（ImageNet 1000 类，5.52 MB）
├── models/
│   ├── fruits_cls_v1/best.pt         物种模型（97.95%）
│   └── fruits_cls_v2/best.pt         柿果成熟度模型（84.44%）
├── runs/                             训练日志、曲线、混淆矩阵、args.yaml
├── .gitignore
└── README.md
```

> **为什么不把 `dataset_persimmon/` 传上来**：191 MB（平均 888 KB/张，是手机截图与实拍原图，
> 而 `dataset/` 是 21 KB/张的网图）。提交后 clone 会很慢。
> 用 `build_dataset_persimmon.py` 可以从你自己的图片重建出**结构完全一致**的数据集。

---

## 环境

独立 conda 环境，不污染 Anaconda base。

```
conda env: yolo
  Python        3.12.14
  PyTorch       2.14.0+cu126      ← CUDA 版，可用 GPU
  torchvision   0.29.0+cu126
  ultralytics   8.4.153
  opencv        5.0.0
  numpy         2.5.3
  GPU           NVIDIA RTX 4050 Laptop, 6 GB, sm_89
```

从零搭建：

```bat
conda create -n yolo python=3.12 -y
conda activate yolo
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/
pip install ultralytics
:: 需要 GPU 才装下面这行（约 2.6 GB）
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu126 --upgrade
```

> **PyCharm 用户注意**：项目解释器必须指向 `D:\Anaconda\envs\yolo\python.exe`。
> 选成系统里其他 Python（例如 `pythoncore-3.14-64`）会报 `ModuleNotFoundError: No module named 'ultralytics'`。

---

## 技术要点

### 迁移学习（为什么小数据集也能训）

`weights/yolo11n-cls.pt` 是在 ImageNet 1000 类上预训练好的权重。微调时：

1. 继承全部卷积层参数（通用视觉特征：边缘、纹理、形状、颜色）
2. 只把最后的分类头换成自己的类别数
3. 用几百张图继续训练几十轮

物种模型训练日志第一行即 `Transferred 234/236 items from pretrained weights`，第 1 轮精度就到 70.8%（随机初始化理论值 1/12 ≈ 8.3%）。

网络结构不是本项目设计的 —— 是 Ultralytics 设计好的 YOLO11n-cls（86 层，154 万参数，3.3 GFLOPs）。本项目的规范化工作集中在 **数据、流程、产物、接口** 四层。

### 拒识（open-set）：两个模型结论相反

分类模型是"N 选 1 的单选题"，softmax 必然归一化，**数学上没有"以上都不是"这个选项**。拿猫、手、白墙去问，它也会硬报一个水果名。

`engine.py` 提供一道闸门：最高置信度低于阈值即输出"未知"。阈值**按模型分别配置**，因为两个模型的实测结论完全相反：

**物种模型 —— 拒识非常有效：**

| 阈值 | 覆盖 | 认对 | 认错 | 覆盖内准确率 |
|---|---|---|---|---|
| 0.00 | 391 | 383 | 8 | 97.95% |
| 0.60 | 385 | 379 | 6 | 98.44% |
| **0.95** | 350 | 350 | **0** | **100.00%** |

**柿果成熟度模型 —— 拒识基本无效：**

| | 张数 | 置信度均值 |
|---|---|---|
| 判对 | 76 | 88.8% |
| **判错** | 14 | **82.0%** |

判错的图置信度也很高（平均值 82%，最高到 100%），**加阈值只会让系统多说"不知道"，并不能提高准确率**：

| 阈值 | 总体准确率 |
|---|---|
| **0.00 ~ 0.40** | **84.44%** |
| 0.60 | 76.69% |
| 0.80 | 63.33% |

所以 `config.py` 里两个模型的阈值分别是 `0.0` 和 `0.60`：

```python
"persimmon": {..., "threshold": 0.0},    # 成熟度各类太像，置信度不可靠
"species":   {..., "threshold": 0.60},
```

> ⚠️ 置信度阈值只能拦住"模型自己也没底"的情况。softmax 有过度自信的毛病，真要根治需要加一类"其他"重新训练。

### ⚠️ 数据增强的坑（本项目踩到的最大的坑）

Ultralytics 的 `hsv_*` 默认值是给**目标检测**用的，直接套到"**靠颜色判成熟度**"的任务上会把关键信号破坏掉：

| 参数 | 默认值 | 后果 |
|---|---|---|
| `hsv_h` | 0.015 | 色相随机偏移 ±5.4° —— 而 `着色期` 与 `完熟` 的色相**只差 6°** |
| `hsv_s` | **0.7** | 饱和度随机抖 ±70%，等于告诉模型"饱和度不用管" |
| `auto_augment` | `randaugment` | 含 Color / Posterize / Solarize，进一步破坏颜色 |

**实测各类的平均色相：** `未熟` 62.7° → `转色期` 53.2° → `着色期` 35.6° → `完熟` 29.5°

相邻两类只差 6~18°，而默认增强的抖动幅度几乎覆盖了这个差距 —— 这就是 `着色期` 被大量误判为 `完熟` 的主要原因。

**建议的修正参数：**

```python
"epochs": 25,              # 峰值在第 12 轮，50 轮只会过拟合
"hsv_h": 0.0,              # 色相不许乱改
"hsv_s": 0.2,              # 饱和度只轻微抖
"hsv_v": 0.3,              # 亮度保留（真实光照差异要保留）
"auto_augment": "none",    # 关掉会改颜色的自动增强
"erasing": 0.15,           # 默认 0.4 太容易遮掉果实
"patience": 10,            # 早停
```

---

## 已知问题

### 1. `着色期 ↔ 完熟` 混淆（当前最大问题）

`着色期` 召回率只有 64%，25 张里 7 张被判成 `完熟`。原因：

- 两类颜色相邻（色相 35.6° vs 29.5°，a\* +9.8 vs +28.6）
- 训练增强破坏了颜色信号（见上一节）
- 部分图片标注可能不一致

**处理顺序（按性价比）：**

1. **核对"高置信度判错"的图** —— 模型非常确定地给了不同答案，很可能是标注错误。零成本。
   涉及的文件见 `runs/fruits_cls_v2/` 目录下的记录，或用 `predict.py` 跑一遍验证集看"判错的 N 张"
2. **修正增强参数后重训** —— 不用补图，1 分钟出结果
3. 补 `着色期` 的边界样本（橙偏红、红偏橙）

### 2. 域偏移

物种模型的训练数据是**网上下载的白底商品图**，真实摄像头背景完全不同。实测一张手机实拍照片：

| | 边框背景色 | 平均亮度 | 到最近类中心距离 |
|---|---|---|---|
| 训练集 | R211 G206 B193（浅米白） | ~0.70 | 平均 0.373 |
| 手机实拍 | **R103 G95 B90（深灰）** | 0.442 | **0.883（2.4 倍）** |

**模型学到的不只是物体，还有"浅色背景 + 中间有个东西"这个组合。**

缓解办法：演示时把物体放在白纸/白盘子上（零成本）；或补拍几十张实拍图混入训练集重训（根治）。

### 3. 没有检测框

分类模型回答的是"整张图是什么"，**不是"东西在哪"**。所以摄像头画面里没有框，只有左上角几行字。

要画框需要另加检测模型，且需要**人工标注边界框**（每颗果一个框）—— 分类模型只需要文件夹分类，检测模型需要位置标注。

---

## 脚本说明

| 脚本 | 作用 | 会不会训练 |
|---|---|---|
| `config.py` | 配置中心，无副作用 | ❌ |
| `engine.py` | 模型加载 + 推理，对外接口 | ❌ |
| `predict.py` | 单图 / 批量 / 逐类准确率 | ❌ 只加载 |
| `camera.py` | 摄像头实时识别 + `--test` 自检 | ❌ 只加载 |
| `build_dataset_persimmon.py` | 把分类图片整理成 train/val 数据集 | ❌ |
| `train.py` | 环境检查 → 数据体检 → 训练 → 归档产物 | ✅ 训练 |

**训练一次，永久使用** —— `models/*/best.pt` 就是模型的全部状态，除非换数据或调参，否则不需要重新训练。

---

## 开发任务清单

- [x] 数据布局规范化（train/val 分类目录）
- [x] 迁移学习训练，产出 `best.pt`
- [x] 验证集评估 + 中文混淆矩阵
- [x] 单图 / 批量预测
- [x] 摄像头实时识别
- [x] CUDA 版 PyTorch（GPU 可用）
- [x] **架构解耦**：拆出 `config.py` / `engine.py`，`predict` 与 `camera` 零依赖
- [x] **多模型支持**：模型注册表 + 一行切换
- [x] **柿果成熟度模型**（4 类，84.44%）
- [ ] 修正数据增强参数后重训（预期 88~92%）
- [ ] 核对高置信度判错的图，修正标注
- [ ] 补 `着色期`、`留树软果`、`过熟果` 样本
- [ ] 画框（需检测模型 + 边界框标注）
- [ ] 摄像头多线程优化
- [ ] 推理服务化（FastAPI）

---

## 踩过的坑（供参考）

| 问题 | 原因 | 解决 |
|---|---|---|
| `ModuleNotFoundError: No module named 'ultralytics'` | PyCharm 项目解释器指向了系统 Python | 改指 `D:\Anaconda\envs\yolo\python.exe` |
| 装了 torch 却用不上 GPU | 默认装的是 `+cpu` 版 | `pip install torch --index-url https://download.pytorch.org/whl/cu126` |
| `pip install` 说"已满足"，不升级到 CUDA 版 | CPU/CUDA 版基础版本号相同，需显式指定或 `--force-reinstall` | 用 `torch==2.14.0+cu126` 显式指定 |
| 图表里中文变方块 | matplotlib 默认字体无中文字形 | `font.sans-serif = Microsoft YaHei` |
| `cv2.putText` 写中文变 `????` | OpenCV 只支持 ASCII | 转成 PIL 图像写中文再转回 |
| 中文在控制台对齐错乱 | 中文是全角字符，`str.ljust` 按字符数算 | 按显示宽度补空格（见 `predict.py` 的 `pad()`） |
| 自定义模块找不到（`import config` 失败） | PyCharm 的运行配置工作目录不对 | 脚本里用 `Path(__file__).resolve().parent` 定位，不依赖 cwd |
| 项目根目录凭空多出 `Ultralytics/` | ultralytics 往 `YOLO_CONFIG_DIR` 下再套一层，那层不存在就退回根目录 | 提前建好 `.ultralytics/Ultralytics/`（见 `config.py`） |
| `Failed to resolve 'github.com'` | 该域名解析被污染，返回 127.0.0.1 | 开代理，或把权重文件放进仓库 |

---

## 数据说明

| 数据集 | 类别 | 训练 | 验证 | 合计 | 体积 | 在仓库里？ |
|---|---|---|---|---|---|---|
| `dataset/` | 12（物种） | 841 | 391 | 1232 | 28 MB | ✅ 是 |
| `dataset_persimmon/` | 4（成熟度） | 356 | 90 | 446 | 191 MB | ❌ 用脚本重建 |

### dataset/（物种）

原始图为 299×299 JPEG。类别顺序由 `sorted()` 固定，编号即列表下标。

| # | 类别 | train | val | # | 类别 | train | val |
|---|---|---|---|---|---|---|---|
| 0 | 土豆 | 74 | 25 | 6 | 芒果 | 53 | 28 |
| 1 | 圣女果 | 61 | 27 | 7 | 苹果 | 79 | 48 |
| 2 | 大白菜 | 101 | 46 | 8 | 西红柿 | 60 | 31 |
| 3 | 大葱 | 65 | 31 | 9 | 韭菜 | 73 | 33 |
| 4 | 梨 | 68 | 31 | 10 | 香蕉 | 50 | 24 |
| 5 | 胡萝卜 | 74 | 34 | 11 | 黄瓜 | 83 | 33 |

`val` 集与 `train` **零交叉重复**（MD5 校验），因此验证精度可信。

### dataset_persimmon/（柿果成熟度）

| 类别 | 中文 | 训练 | 验证 |
|---|---|---|---|
| `1_unripe` | 未熟（青绿） | 107 | 27 |
| `2_turning` | 转色期（黄橙） | 76 | 19 |
| `3_coloring` | 着色期（橙红） | 98 | 25 |
| `4_full` | 完熟（深红） | 75 | 19 |
| **合计** | | **356** | **90** |

**重建方式：**

```bat
:: 把你的图片按类别放好：源目录/<类别名>/*.jpg
python build_dataset_persimmon.py --source "C:\Users\dell\Desktop\images"

:: 只想先看划分结果（不写文件）
python build_dataset_persimmon.py --source "..." --dry-run

:: 改比例或种子
python build_dataset_persimmon.py --source "..." --val-ratio 0.15 --seed 123
```

**划分规则**：逐类 8:2 分层，固定随机种子 `seed=42`，因此**同一份源数据每次得到完全相同的划分**，可复现。清单见 `dataset_persimmon/split_manifest.csv`。

> ⚠️ 图片平均 888 KB（手机截图 + 实拍原图），比 `dataset/` 的 21 KB 大得多。训练时会被统一缩放到 224×224，源图分辨率不影响精度。
