# 智慧农业综合巡检平台 · 柿子成熟度检测

> 拍一张果园照片，判断**每一颗果实**的成熟度，汇总成"这片林子现在能不能采"。
> 用于互联网+ / 挑战杯参赛，同时作为求职作品。

---

## 这是什么

一个完整的系统，三块：

```
  手机 / 摄像头
        │  拍照上传
        ▼
┌──────────────────┐     ┌────────────────────┐
│  前端  web/       │ ──▶ │ Java 后端 persimmon/ │
│  Vue 3 + Vite     │     │ Spring Boot + MySQL │
└──────────────────┘     └─────────┬──────────┘
                                   │ HTTP
                                   ▼
                         ┌────────────────────┐
                         │ AI 服务（根目录 .py）│
                         │ YOLO 检测 + 成熟度分类│
                         └────────────────────┘
```

**AI 服务先识别，Java 落库存业务数据，前端展示。** 三层分开是有意为之——
换模型不用动业务代码，换前端不用动模型。

---

## 目录速查

| 目录 | 是什么 | 用什么打开 | 详细说明 |
|---|---|---|---|
| **`persimmon/`** | Java 业务后端（Spring Boot 4 + MyBatis + MySQL） | **IntelliJ IDEA** | [persimmon/README.md](persimmon/README.md) |
| **`web/`** | 前端（Vue 3 + Vite） | **VS Code** | [web/README.md](web/README.md) |
| **`ai/`** | AI 推理与训练（Ultralytics YOLO） | **PyCharm** | 本文末尾 |
| `docs/` | 设计与过程文档 | 任意 | 见下方索引 |
| `dataset/` `weights/` `models/` `runs/` | 数据集、预训练权重、训练产物 | — | — |

> ⚠️ **三个部分要用不同的 IDE 打开。** 拿 PyCharm 开 `persimmon/` 它是看不懂 Maven 工程的。

---

## 怎么跑起来

**需要三个进程，缺一不可。**

```bat
:: ① AI 服务（8001）—— 先起这个，另外两个都依赖它
cd /d D:\vegetable_fruit_yolo
run_server.bat
```

```bat
:: ② Java 后端（8080）
cd /d D:\vegetable_fruit_yolo\persimmon
mvnw spring-boot:run
```

```bat
:: ③ 前端（5173）
cd /d D:\vegetable_fruit_yolo\web
npm install     :: 第一次才要
npm run dev
```

| 地址 | 是什么 |
|---|---|
| http://localhost:5173/h5 | 手机端：上传 → 结果 → 历史 |
| http://localhost:5173/screen | 大屏：路演演示用 |
| http://localhost:5173/dev/tokens | 设计令牌自检（开发用，上线删） |
| http://localhost:8080/api/health | Java + AI 两边是否都活着 |
| http://localhost:8001/docs | AI 服务的接口文档 |

---

## 文档索引

| 文档 | 讲什么 | 什么时候看 |
|---|---|---|
| [`PRODUCT.md`](PRODUCT.md) | **产品事实**：用户是谁、解决什么、有什么证据、**不许虚构什么** | 写任何材料前 |
| [`docs/API.md`](docs/API.md) | **接口契约**：前后端对接就靠这份 | 写后端接口时 |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | 系统架构、关键设计取舍、分阶段路线图 | 答辩前 |
| [`docs/FRONTEND_DESIGN.md`](docs/FRONTEND_DESIGN.md) | 前端设计、五页面清单、设计令牌 | 改前端时 |
| [`docs/DESIGN_WORKSHEET.md`](docs/DESIGN_WORKSHEET.md) | 数据库设计的方法（七步）与练习 | 回顾设计思路 |
| [`docs/FIELD_TRIP.md`](docs/FIELD_TRIP.md) | 太行山实地采集清单与访谈问题 | 再采集时 |
| [`persimmon/README.md`](persimmon/README.md) | Java 后端：哪些已搭好、哪些要写、三个必踩的坑 | 写 Java 时 |
| [`web/README.md`](web/README.md) | 前端：怎么跑、三条不能破的规矩 | 改前端时 |

---

# 附录：AI 部分详细说明

> 以下是原 README，讲的是根目录 Python 脚本那部分（模型、训练、实验数据、踩过的坑）。
> 内容仍然有效，保留在这里。

## 柿果成熟度识别 · 蔬菜水果分类

用 Ultralytics **YOLO11** 做迁移学习。**两层结构**：先检测出每颗柿子在哪儿，再判它的成熟度。

| 模型 | 任务 | 类别 | 指标 |
|---|---|---|---|
| `persimmon_det_v1` | 检测：找出柿子在哪儿 | 1 | mAP@0.5 = **88.23%** |
| `persimmon_cls_v1` | 分类：判断成熟度（主任务） | 4 | top-1 = **88.89%** / top-5 = 100% |
| `fruits_cls_v1` | 物种识别（对照实验） | 12 | top-1 = 97.95% |

> ⚠️ **上面是 2026-10-05 重测的数字，以此为准。**
> 旧版 README 里写的 84.44% 是**修正数据增强参数之前**那次的结果。
> **完整的技术数据（含逐类指标、检测漏检问题、缺口清单）见 [`docs/TECH_DATA.md`](docs/TECH_DATA.md)。**

---

## 快速开始

```bat
conda activate yolo
cd /d D:\vegetable_fruit_yolo
```

> ⚠️ **数据集说明**：`dataset/dataset_persimmon/`（191 MB）**没有随仓库上传**，
> 而且**原始源图片已丢失，无法重建**。想重新训练需要一个同结构的数据集。

> 💡 **下面所有命令都用 `-m ai.xxx` 的形式，而且必须在项目根目录下执行。**
> 因为代码已经收进 `ai/` 包了，脚本内部写的是 `from ai import config`，
> 这种写法要求**项目根目录**在 Python 的搜索路径里。
> （直接 `python ai\detect.py` 会报 `ModuleNotFoundError: No module named 'ai'`）

### 训练

```bat
python -m ai.train                :: 训练成熟度分类模型
python -m ai.train_detect         :: 训练检测模型
```

训练参数在 `ai/train.py` 顶部的 `CONFIG` 字典里。

### 推理

```bat
python -m ai.detect "D:\照片\柿子.jpg"    :: 单张图，两层推理
python -m ai.detect "某个文件夹"           :: 整个文件夹
python -m ai.detect                       :: 不带参数 = 开摄像头
```

结果图存到 `runs/detect_predict/`。

### 往检测数据集加数据

```bat
python -m ai.add_to_dataset check                    :: 先检查配对情况
python -m ai.add_to_dataset images "C:\新图文件夹"     :: 加图片（自动缩小超大图）
python -m ai.add_to_dataset labels "C:\标注文件夹"     :: 加标注
```

### 起服务

```bat
run_server.bat                 :: FastAPI 服务（8001）
```

等价于 `uvicorn ai.server.app:app --host 0.0.0.0 --port 8001`，也必须从项目根目录跑。

切换模型改 `ai/config.py` 一行：

```python
ACTIVE_MODEL = "persimmon"     # 或 "species"
```

> **⚠️ 旧版 README 里提到的 `predict.py`、`camera.py`、`build_dataset_persimmon.py` 已经不在项目里了**
> （重构成 `detect.py` 时合并掉了）。看到那三个名字请忽略。

---

## 结果

**详细的逐类指标、混淆矩阵解读、以及检测层的实测数据，全部在
[`docs/TECH_DATA.md`](docs/TECH_DATA.md)。** 这里只放结论：

| 项目 | 结果 |
|---|---|
| 成熟度分类 top-1 | **88.89%**（80/90） |
| 成熟度分类 top-5 | **100%** |
| 最弱的类别 | **转色期**（召回 74%）—— 它处在成熟连续体正中间，被两边挤 |
| 曾经的弱项 | 着色期（旧模型 64% → 新模型 **88%**），**已通过修正增强参数解决** |
| 物种识别（对照） | 97.95%；同一份数据用 sklearn+SVM 只有 63.68% —— 差距来自迁移学习 |

> **★ 检测层有个严重问题必须先看：** 整树照片上只找到 **2%** 的果实。
> 详见 `docs/TECH_DATA.md` 的「检测层」一节。**这是产品能否成立的关键。**

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
from ai import engine

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

## 完整目录结构

```
vegetable_fruit_yolo/
│
├── ai/                          ★ 代码①：AI 推理与训练（Python）
│   ├── __init__.py                包标记（必须有，`from ai import ...` 靠它）
│   ├── config.py                  ★ 全部配置：模型注册表 / 阈值 / 中文类名
│   ├── engine.py                  分类模型加载 + 推理
│   ├── inference.py               ★ 两层推理核心（检测 → 裁剪 → 分类）
│   ├── detect.py                  命令行：单图 / 文件夹 / 摄像头
│   ├── train.py                   训练成熟度分类模型
│   ├── train_detect.py            训练检测模型
│   ├── add_to_dataset.py          往检测数据集加图/标注
│   └── server/                    FastAPI 服务（8001）
│       ├── app.py                   接口定义
│       └── schemas.py               ★ 接口契约（对应 Java 的 AiPredictResponse）
│
├── persimmon/                   ★ 代码②：Java 业务后端
│   ├── pom.xml
│   ├── src/main/java/org/ymg/persimmon/
│   │   ├── PersimmonApplication.java
│   │   ├── common/                 统一响应体、错误码、全局异常
│   │   ├── config/                 跨域、HTTP 客户端
│   │   ├── ai/                     调 Python 服务
│   │   └── entity/ mapper/ service/ controller/   ⬜ 待写
│   ├── src/main/resources/
│   │   ├── application.yaml        数据库 + MyBatis 配置
│   │   └── db/schema.sql           ★ 建表 SQL（已执行）
│   └── README.md
│
├── web/                         ★ 代码③：前端（Vue 3 + Vite）
│   ├── package.json / vite.config.js / index.html
│   ├── preview/design-preview.html  静态预览页（不装 Node 也能看）
│   ├── src/
│   │   ├── config/brand.js         产品名 + 可采收率门槛
│   │   ├── utils/ripeness.js       ★ 四个成熟度的唯一真源
│   │   ├── api/                    axios 实例 + 接口
│   │   ├── stores/                 最近一次结果
│   │   ├── styles/                 ★ 两级设计令牌
│   │   ├── components/             标注图 / 色带 / 标签
│   │   ├── layouts/                H5 / 大屏
│   │   └── views/                  五个页面
│   └── README.md
│
├── docs/                        ★ 文档
│   ├── ARCHITECTURE.md             系统架构与路线图
│   ├── API.md                      ★ 接口契约（前后端对接看这份）
│   ├── TECH_DATA.md                ★ 技术数据（写材料用）
│   ├── FRONTEND_DESIGN.md          前端设计
│   ├── DESIGN_WORKSHEET.md         数据库设计方法与练习
│   ├── FIELD_TRIP.md               实地采集清单
│   ├── PROJECT_MAP.md              项目全景清单
│   ├── 前端技术方案.md              ⚠️ 早期方案，与实现冲突
│   └── UI设计规范.md                ⚠️ 早期方案，与实现冲突
│
├── dataset/                     数据
│   ├── dataset_fruit&&vegetable/   物种数据集（12 类 1232 张）✅ 已上传
│   ├── dataset_persimmon/          柿果成熟度（4 类 443 张）❌ 未上传，源图已丢失
│   └── dataset_persimmon_det/      检测数据集（单类 98 张）✅ 已上传
│
├── weights/                     预训练权重（yolo11n.pt / yolo11n-cls.pt）
├── models/                      训练产物
│   ├── persimmon_cls_v1/best.pt    ★ 成熟度分类（88.89%）
│   ├── persimmon_det_v1/best.pt    ★ 检测（mAP@0.5 = 88.23%）
│   └── fruits_cls_v1/best.pt       物种（97.95%）
├── runs/                        训练日志、曲线、混淆矩阵、检测结果图
├── 测试结果/                     09-26 的实测报告与对照图（★ 建议看）
│
├── run_server.bat               启动脚本：AI 服务（8001）
├── camera.bat                   启动脚本：摄像头实时识别
├── README.md                    本文件
├── PRODUCT.md                   产品事实（用户是谁、证据、不许虚构什么）
└── .gitignore
```

**三个代码目录 + 数据 + 文档，各自独立、互不干扰。**

> **⚠️ 关于 `dataset_persimmon/`（191 MB）**
> 它**没有随仓库上传**，而且 `.gitignore` 里写明：**原始源图片已丢失，无法重建**。
> 现有这 443 张是**唯一副本，勿删**。
> 2026-10-04 太行山新采的 100 多张实拍照片是唯一的补充来源，放在
> `dataset/field_trip/`（该目录被 gitignore，不进仓库）。

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

### 1. ★ 检测层严重漏检（当前最大问题）

2026-09-26 实测：**整棵树照片上只找到 2% 的果实**（3 / 约 200）。

| 场景 | 检出 / 目测可见 | 召回率 |
|---|---|---|
| 手拿大柿子（近景） | 3 / 约 10 | 约 30% |
| 近景一丛 | 6 / 约 14 | 约 43% |
| **整棵树（远景）** | **3 / 约 200** | **约 2%** |

**根因**：检测训练集只有 82 张，而且 **100% 是未熟青果的近景大图**，负样本 0 张。
模型只学过"近景、大颗、青绿色"这一种形态。

**这一条直接决定产品能不能成立** —— 声称"判断一整片林子"，检测层目前撑不住。

- 完整分析、已实测排除的方案、改进方向：[`docs/TECH_DATA.md`](docs/TECH_DATA.md)
- 原始测试报告：[`测试结果/分析报告.md`](测试结果/分析报告.md)

### 2. ~~`着色期 ↔ 完熟` 混淆~~（已解决 ✅）

旧模型（84.44%）时着色期召回只有 64%，25 张里错 7 张。

**修正数据增强参数后已修复**：着色期召回 **64% → 88%**，整体 **84.44% → 88.89%**。

原因回顾：两类平均色相只差 6°（35.6° vs 29.5°），
而 Ultralytics 默认的 `hsv_s = 0.7`（饱和度随机抖 ±70%）把这个信号破坏了。
改成 0.2 并关掉 `auto_augment` 之后解决。

**代价**：最弱的类别转移到了 `转色期`（召回 74%）——
它处在成熟连续体正中间，往青一点是未熟、往红一点是着色，两边都被挤。

### 3. 域偏移

物种模型的训练数据是**网上下载的白底商品图**，真实果园背景完全不同。实测一张手机实拍照片：

| | 边框背景色 | 平均亮度 | 到最近类中心距离 |
|---|---|---|---|
| 训练集 | R211 G206 B193（浅米白） | ~0.70 | 平均 0.373 |
| 手机实拍 | **R103 G95 B90（深灰）** | 0.442 | **0.883（2.4 倍）** |

**模型学到的不只是物体，还有"浅色背景 + 中间有个东西"这个组合。**

缓解办法：演示时把物体放在白纸/白盘子上（零成本）；或补拍实拍图混入训练集重训（根治）。
**2026-10-04 太行山采的 100 多张实拍照片正好可以用于此。**

### 4. 成熟度分级是否该改成三级 —— 未决

「着色期」和「完熟」在颜色上相邻，一直是难点。
曾考虑合并成三类，但老师提出"**不同农副产品需要不同成熟度**"
（柿饼要硬的着色果、醋可以用完熟软果）——
**这条边界恰恰是商业上最值钱的**，所以不能合并。

⚠️ 但这个用途-成熟度的对应关系**目前没有一手依据，需要向企业核实**。

---

## 脚本说明（当前实际存在的）

| 脚本 | 作用 | 会不会训练 |
|---|---|---|
| `config.py` | 配置中心：模型注册表、阈值、摄像头参数 | ❌ |
| `engine.py` | 分类模型加载 + 推理 | ❌ |
| `inference.py` | **两层推理核心**（检测 + 分类），`detect.py` 和 `server/` 都调它 | ❌ |
| `detect.py` | 命令行：单图 / 文件夹 / 摄像头 | ❌ 只加载 |
| `train.py` | 训练成熟度分类模型 | ✅ |
| `train_detect.py` | 训练检测模型 | ✅ |
| `add_to_dataset.py` | 把新图片加进数据集 | ❌ |
| `server/app.py` | FastAPI 服务（8001） | ❌ |

**训练一次，永久使用** —— `models/*/best.pt` 就是模型的全部状态。

**两个 .bat：** `run_server.bat`（起服务）、`camera.bat`（开摄像头）。

---

## 开发任务清单（2026-10-05 更新）

**AI 侧：**

- [x] 数据布局规范化（train/val 分类目录）
- [x] 迁移学习训练，产出 `best.pt`
- [x] 验证集评估 + 中文混淆矩阵
- [x] **架构解耦**：拆出 `config.py` / `engine.py` / `inference.py`
- [x] **多模型支持**：模型注册表 + 一行切换
- [x] **柿果成熟度分类模型**（4 类，**88.89%**）
- [x] **检测模型**（单类别，mAP@0.5 = 88.23%）
- [x] **修正数据增强参数并重训** —— 着色期召回 64% → 88%（原本预期 88~92%，达成）
- [x] 推理服务化（FastAPI，8001）
- [ ] ★ **补检测训练数据：远景小目标图 + 负样本**（当前最大的问题，见「已知问题 1」）
- [ ] 太行山采集的实拍照片整理进数据集
- [ ] 补 `转色期` 样本（现在是分类最弱的一类）
- [ ] 与他人对比实验（YOLO n/s/m/l 不同规模）

**应用侧：**

- [x] Java 后端骨架（`persimmon/`）
- [x] 数据库设计与建表（`region` / `capture` / `notification`）
- [x] 前端五页面（`web/`）
- [ ] Java 业务层：Entity / Mapper / Service / Controller
- [ ] 历史页与大屏接真实数据
- [ ] 比赛材料（商业计划书、PPT、技术报告）

**明确不做：** 登录与鉴权、病虫害识别、多地块管理、边缘设备部署（构想，未验证）

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

> ⚠️ **详细的、已核实的数据集信息见 [`docs/TECH_DATA.md`](docs/TECH_DATA.md) 第 4、5 节。**
> 下面只是速查表。

| 数据集 | 类别 | 训练 | 验证 | 合计 | 体积 | 在仓库里？ |
|---|---|---|---|---|---|---|
| `dataset_fruit&&vegetable` | 12（物种） | 841 | 391 | 1232 | 28 MB | ✅ 是 |
| `dataset_persimmon` | 4（成熟度） | **353** | 90 | **443** | 191 MB | ❌ **未上传，源图已丢失** |
| `dataset_persimmon_det` | 1（检测） | 82 | 16 | 98 | — | ✅ 是 |

> **训练集从 356 变成了 353**（2026-10-05 实测 `val()` 时发现的）。
> 逐类数字需要重新数一遍，暂以总数 353 为准。

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

> ⚠️ **准确数字以 [`docs/TECH_DATA.md`](docs/TECH_DATA.md) 第 5 节为准。**
> 2026-10-05 实测时发现训练集是 **353 张**（不是 356），
> **逐类数字需要重新数一遍**，下表是旧值，仅供参考：

| 类别 | 中文 | 训练（旧值） | 验证 |
|---|---|---|---|
| `1_unripe` | 未熟（青绿） | 107 | 27 |
| `2_turning` | 转色期（黄橙） | 76 | 19 |
| `3_coloring` | 着色期（橙红） | 98 | 25 |
| `4_full` | 完熟（深红） | 75 | 19 |
| **合计** | | ~~356~~ **353** | **90** |

**⚠️ `dataset_persimmon/` 的原始源图片已丢失，无法重建。**
现有这份是**唯一副本，勿删**。

**划分规则**：逐类 8:2 分层，固定随机种子 `seed=42`，因此**同一份源数据每次得到完全相同的划分**，可复现。

> ⚠️ 图片平均 888 KB（手机截图 + 实拍原图），比 `dataset/` 的 21 KB 大得多。
> 训练时会被统一缩放到 224×224，**源图分辨率不影响精度**。

### 想加新数据怎么办

**用 `add_to_dataset.py`**，或者最直接的办法：**把图片按类别丢进对应的文件夹**

```
dataset/dataset_persimmon/train/<类别名>/新图片.jpeg
dataset/dataset_persimmon/val/<类别名>/新图片.jpeg
```

**分类数据集不需要标注工具**——文件夹名就是标签。这是分类和检测最大的区别。

> **❌ 旧版 README 里的 `build_dataset_persimmon.py` 已经不在项目里了**（重构成现在的结构时删掉了）。
> 而且它也没用了——**源图片已丢失，重建不出来**。
