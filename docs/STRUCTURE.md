# 目标项目结构设计

> 2026-10-05。这份是**设计**（应该长什么样），不是现状统计。
> 现状见 [`PROJECT_MAP.md`](PROJECT_MAP.md)。

---

## 一、设计原则

1. **代码 / 数据 / 文档 / 产物 分开** —— 四类东西不混
2. **能重新生成的，不进仓库**（缓存、编译产物、依赖）
3. **运行时产物和历史记录放一边**，不占主视线
4. **不为了好看去改代码引用的路径** —— 改路径的成本远大于收益

---

## 二、目标结构

```
vegetable_fruit_yolo/
│
├── README.md                    项目总说明（从哪看起）
├── PRODUCT.md                   产品事实
├── .gitignore
│
├── ── 代码（三个独立工程）──────────────────
├── ai/                          AI 推理与训练（Python）
│   ├── config.py  engine.py  inference.py
│   ├── detect.py  train.py  train_detect.py  add_to_dataset.py
│   └── server/                  FastAPI 服务
│
├── persimmon/                   Java 业务后端
│   ├── src/
│   ├── pom.xml
│   └── README.md
│
├── web/                         前端（Vue 3）
│   ├── src/
│   ├── preview/
│   └── README.md
│
├── ── 支撑 ──────────────────────────────
├── docs/                        文档（设计与过程）
│
├── scripts/                     ★ 新增：启动脚本
│   ├── run_server.bat              起 AI 服务（8001）
│   └── camera.bat                  摄像头实时识别
│
├── ── 数据与模型 ────────────────────────
├── dataset/                     数据集（3 个，各给一个模型）
│   ├── dataset_persimmon/         4 类成熟度（443 张）★ 未上传，源图已丢失
│   ├── dataset_persimmon_det/     单类检测（98 张）
│   └── dataset_fruit&&vegetable/  12 类物种（1232 张）
│
├── weights/                     预训练权重（重训的起点）
│   ├── yolo11n-cls.pt             分类
│   └── yolo11n.pt                 检测
│
├── models/                      训好的模型（产品在用）
│   ├── persimmon_cls_v1/best.pt   成熟度分类　88.89%
│   ├── persimmon_det_v1/best.pt   检测　　　　mAP 88.23%
│   └── fruits_cls_v1/best.pt      物种　　　　97.95%
│
└── ── 历史产物（不参与运行，留档）──────────
    runs/                        训练日志、曲线、混淆矩阵
    └── (只保留日志类文件，见第三节)

    artifacts/                   ★ 新增：把散落的历史产物收进来
    └── field-test-2026-09-26/      原「测试结果/」（检测漏检的实测证据）
```

**和现在比，只动了两处**（见第五节的风险说明，为什么只动这两处）：
- 两个 `.bat` → `scripts/`
- `测试结果/` → `artifacts/field-test-2026-09-26/`

---

## 三、该删的（无价值，删了不影响任何东西）

### 3.1 缓存类 —— 会自动重建

| 路径 | 说明 |
|---|---|
| `__pycache__/`（各处） | Python 字节码 |
| `.mplcache/` | matplotlib 字体缓存 |
| `.ultralytics/` | Ultralytics 运行时配置 |
| `dataset/dataset_persimmon/*.cache` | 训练缓存（`train.cache` / `val.cache`） |
| `web/node_modules/` | npm 依赖 —— ⚠️ 删了要重跑 `npm install` |
| `persimmon/target/` | Maven 编译产物 |

### 3.2 `runs/` 里的无用文件

| 路径 | 为什么能删 |
|---|---|
| `runs/**/train_batch*.jpg` | Ultralytics 自动生成的批次预览图，材料用不上 |
| `runs/**/val_batch*.jpg` | 同上 |
| `runs/persimmon_cls_v1/weights/` | **已在 `models/persimmon_cls_v1/` 有副本** |
| `runs/detect/persimmon_det_v1/weights/` | 已在 `models/persimmon_det_v1/` 有副本 |
| `runs/classify/val/` | 被 `val-2/` 取代（旧的评估） |
| `runs/detect/val/` | 被 `val-2/` 取代 |

### 3.3 零散文件

| 路径 | 说明 |
|---|---|
| `persimmon/HELP.md` | IDEA 生成的样板文件，没有任何内容价值 |

### ❌ 这些**不能删**（容易误判）

| 路径 | 为什么留 |
|---|---|
| `runs/*/results.csv` / `results.png` | **训练曲线，材料要用** |
| `runs/*/args.yaml` | 训练参数记录，证明"改过哪些增强参数" |
| `runs/*/confusion_matrix*.png` | **混淆矩阵，答辩要放的图** |
| `runs/detect_predict/` | 检测效果图 |
| `测试结果/` | **检测漏检 2% 的实测证据**，是最重要的一份材料 |
| `dataset/dataset_fruit&&vegetable/` | 12 类物种数据集 —— 是"可迁移到其他农产品"的证据 |
| `weights/*.pt` | 删了没法重训 |
| `models/*/best.pt` | 删了产品跑不起来 |
| `.idea/` | PyCharm 工程配置，删了要重新配解释器 |

---

## 四、回答你的四个具体问题

### 4.1 `run_server.bat` 和 `camera.bat` 能删吗？

**能删，但不建议。** 它们里面记着两件容易忘的事：

```
D:\Anaconda\envs\yolo\python.exe     ← conda 环境的绝对路径
                                     （PATH 里那个 python 是微软商店的占位符，会静默失败）
PORT=8001                            ← 8000 被系统占用了，只能用 8001
```

删了就得每次手打完整命令。**建议移到 `scripts/`，别删。**

### 4.2 训练权重只留最好的一个？

**`models/` 里已经是"每个模型只留一个 best.pt"了，不用动。**

有重复的是 `runs/*/weights/`（best + last），那些**可以删**——因为训练完已经复制到 `models/` 了。

**但 `weights/` 那两个预训练权重不能删**，它们是重训的起点。名字看着像"重复"，其实是不同用途。

### 4.3 为什么有两个柿子数据集？

**其实是三个数据集，各给一个模型用**（见第一节）。删任何一个都会让对应的模型没法重训。

### 4.4 看不懂的文件夹

| 文件夹 | 是什么 | 能不能删 |
|---|---|---|
| `.idea/` | PyCharm 工程配置 | ⚠️ 删了要重配解释器 |
| `.ultralytics/` | Ultralytics 运行时配置 | ✅ 自动重建 |
| `.mplcache/` | matplotlib 字体缓存 | ✅ 自动重建 |
| `runs/` | 训练日志与结果图 | ⚠️ **部分要留** |
| `web/node_modules/` | npm 依赖（几万个文件） | ✅ 可重装 |
| `persimmon/target/` | Java 编译产物 | ✅ 自动重建 |
| `测试结果/` | 09-26 的实测报告 | ❌ **留着** |

---

## 五、⚠️ 我不建议做的三件事（以及为什么）

### 5.1 不改 `dataset/`、`models/`、`weights/`、`runs/` 的名字

**理由：`ai/config.py` 里写死了这些路径。**

```python
"dataset": ROOT / "dataset" / "dataset_persimmon",
"weights": ROOT / "models" / info["run"] / "best.pt",
```

改成 `data/`、`checkpoints/` 之类，就得同步改 `config.py`、`train.py`、`detect.py`、`README`、`.gitignore`……

**而这些名字本来就是业界常见叫法**（`dataset/`、`models/`、`weights/`），改成别的不会更"企业级"。

### 5.2 不改 `persimmon/` 为 `backend/`

**理由：** 只为了和 `ai/`、`web/` 看起来对称，但要动 IDEA 工程配置 + pom + 多处文档引用。**收益是美观，成本是可能出问题。** 现在这样不影响任何人理解。

（真要改，等你有整块时间的时候单独做。）

### 5.3 暂不改 `dataset_fruit&&vegetable/` 那个 `&&`

**这个是真该改的** —— `&&` 在命令行里是"并且"的意思，会让脚本出错。

**但要同时改 `config.py` 一行**，所以别顺手改。要改的话单独说，我一起处理。

---

## 六、执行清单（按风险从低到高）

**第 1 组：纯删除，零风险**（不影响任何代码）

```
[ ] 删 __pycache__/（各处）
[ ] 删 .mplcache/
[ ] 删 .ultralytics/
[ ] 删 dataset/dataset_persimmon/train.cache 和 val.cache
[ ] 删 persimmon/HELP.md
[ ] 删 persimmon/target/（如果存在）
[ ] 删 runs/**/train_batch*.jpg 和 val_batch*.jpg
[ ] 删 runs/classify/val/（保留 val-2）
[ ] 删 runs/detect/val/（保留 val-2）
[ ] 删 runs/persimmon_cls_v1/weights/
[ ] 删 runs/detect/persimmon_det_v1/weights/
```

**第 2 组：移动，低风险**（脚本用的是绝对路径）

```
[ ] 新建 scripts/
[ ] run_server.bat  →  scripts/
[ ] camera.bat      →  scripts/
[ ] 新建 artifacts/
[ ] 测试结果/  →  artifacts/field-test-2026-09-26/
```

**移完这一组，根目录就只剩：**

```
README.md  PRODUCT.md  .gitignore  .idea/
ai/  persimmon/  web/  docs/  scripts/
dataset/  models/  weights/  runs/  artifacts/
```

**干净了。**

**第 3 组：要改代码，中风险 —— 建议以后再说**

```
[ ] dataset_fruit&&vegetable/ 改名（同时改 config.py）
[ ] persimmon/ 改名 backend/（同时改 IDEA 配置和文档）
```

---

## 七、关于"企业级标准"

说句实话：**上面这个结构已经够企业级了。**

企业级不是"文件夹名字好看"，是：

| 特征 | 你有没有 |
|---|---|
| 代码分层清楚、依赖单向 | ✅ `config` → `engine` → `inference` → 入口 |
| 接口契约独立成文 | ✅ `docs/API.md` + `schemas.py` + `AiPredictResponse.java` |
| 配置集中、不散落 | ✅ `ai/config.py`、`application.yaml` |
| 有文档、有设计记录 | ✅ `docs/` 一整套 |
| 可运行产物与源码分离 | ✅ `models/` vs `ai/` |
| 有测试记录 | ✅ `测试结果/分析报告.md` |
| 有 .gitignore、不提交产物 | ✅ |

**你缺的不是结构，是"把垃圾清掉"和"把文档里的过时内容改对"。** 这两件做完，观感就完全不一样了。
