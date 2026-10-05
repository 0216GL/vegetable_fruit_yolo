# 项目全景清单

> 2026-10-05 全盘扫描。**标 ⚠️ 的地方需要你决定。**
> 这份文档本身也是给你做"删/留/分类"决策用的。

---

## 一、项目主干：三个能跑的系统

```
                    手机 / 摄像头
                         │
                         ▼
        ┌────────────────────────────────┐
        │  前端 web/          :5173       │  Vue 3 + Vite
        └───────────────┬────────────────┘
                        │ HTTP
                        ▼
        ┌────────────────────────────────┐
        │  Java 后端 persimmon/   :8080   │  Spring Boot 4 + MyBatis + MySQL
        └───────────────┬────────────────┘
                        │ HTTP
                        ▼
        ┌────────────────────────────────┐
        │  AI 服务（根目录 .py）  :8001    │  Ultralytics YOLO
        └────────────────────────────────┘
```

### 1.1 AI 推理与训练（`ai/`，Python）

> 2026-10-05 这些文件从项目根目录移进了 `ai/` 包。

| 文件 | 用途 | 状态 |
|---|---|---|
| `ai/__init__.py` | 包标记（`from ai import ...` 靠它） | ✅ 必须有 |
| `ai/config.py` | **配置中心**：模型注册表、阈值、摄像头参数、中文类名 | ✅ 在用 |
| `ai/engine.py` | 分类模型加载 + 推理 | ✅ 在用 |
| `ai/inference.py` | **两层推理核心**（检测 + 分类），被 `detect.py` 和 `server/` 调用 | ✅ 在用 |
| `ai/detect.py` | 命令行：单图 / 文件夹 / 摄像头 | ✅ 在用 |
| `ai/train.py` | 训练成熟度分类模型 | ✅ 在用 |
| `ai/train_detect.py` | 训练检测模型 | ✅ 在用 |
| `ai/add_to_dataset.py` | **往检测数据集加图/标注**（含 `check` 模式，会统计小目标数量） | ✅ 在用 |
| **`run_server.bat`**（根目录） | 起 FastAPI 服务 | ✅ 在用 |
| **`camera.bat`**（根目录） | 开摄像头 | ✅ 在用 |

```
ai/server/                    FastAPI 服务（8001）
├── app.py                      ✅ 接口定义
├── schemas.py                  ✅ 接口契约（★ 对应 Java 的 AiPredictResponse）
└── __init__.py                 ✅

⚠️ static/index.html 在移动时丢了（原来是个临时测试页）。
   app.py 有兜底，不会报错，`/` 会提示"测试页缺失"。
   要恢复的话说一声。
```

> ⚠️ **两个 `.bat` 故意留在项目根目录** —— 双击就在根目录，不用点进代码文件夹。
> **但它们必须在根目录执行**，因为脚本内部是 `from ai import ...`。

### 1.2 Java 业务后端（`persimmon/`）

**已搭好的（基础设施）：**

```
src/main/java/org/ymg/persimmon/
├── PersimmonApplication.java     ✅ 启动类 + @MapperScan
├── common/                       ✅ 通用层
│   ├── R.java                      统一响应体
│   ├── ErrorCode.java              错误码表
│   ├── BizException.java           业务异常
│   └── GlobalExceptionHandler.java 全局异常收口
├── config/
│   ├── WebConfig.java              跨域
│   └── RestTemplateConfig.java     HTTP 客户端 + 超时
├── ai/
│   ├── AiPredictResponse.java      AI 返回结构（= schemas.py 的镜像）
│   └── AiClient.java               调 AI 服务
└── entity/ mapper/ service/ controller/   ⬜ 四个空包（等你写）

src/main/resources/
├── application.yaml              ✅ 数据库 + MyBatis 配置
└── db/schema.sql                 ✅ 建表 SQL（已执行）
```

**还缺的：** Entity / Mapper / Service / Controller 四层（用户正在写）

**其他文件：** `pom.xml`、`mvnw`/`mvnw.cmd`（Maven 包装器）、`.gitignore`、`.mvn/`、`src/test/`、`README.md`、`HELP.md`（IDEA 生成，可删）

### 1.3 前端（`web/`）

```
web/
├── package.json / vite.config.js / index.html / .gitignore   ✅
├── README.md                                                 ✅
├── preview/design-preview.html   ⚠️ 静态预览页（见第五节）
├── node_modules/                 依赖（几万个文件，已 gitignore）
└── src/
    ├── main.js / App.vue / router/index.js    ✅
    ├── config/brand.js            产品名 + 可采收率门槛
    ├── utils/ripeness.js          ★ 四个成熟度的唯一真源
    ├── api/request.js             ★ axios 实例，统一拆 R<T>
    ├── api/inspection.js          各接口
    ├── stores/inspection.js       最近一次结果
    ├── styles/                    两级令牌
    │   ├── primitives.css            第一级：只有值
    │   ├── semantic.css              第二级：只有用途
    │   ├── base.css                  重置 + 浏览器自带部分
    │   └── element-plus.css          覆盖 Element Plus 外观
    ├── components/
    │   ├── AnnotatedImage.vue     ★ 逐果标注图
    │   ├── RipenessBar.vue        ★ 成熟度色带
    │   └── RipenessBadge.vue
    ├── layouts/  H5Layout.vue · ScreenLayout.vue
    └── views/
        ├── DevTokens.vue          令牌自检页（开发用，上线删）
        ├── h5/  Upload.vue · Result.vue · History.vue
        └── screen/Dashboard.vue
```

**五个页面全部能跑，对比度已实测。**

---

## 二、数据与模型资产

| 路径 | 内容 | 体积 | 在 git 里？ |
|---|---|---|---|
| `dataset/dataset_fruit&&vegetable/` | 物种数据集，12 类 1232 张 | 28 MB | ✅ 是 |
| `dataset/dataset_persimmon/` | **成熟度数据集，4 类 443 张** | 191 MB | ❌ **否，且源图已丢失** |
| `dataset/dataset_persimmon_det/` | 检测数据集，单类 98 张 | — | ✅ 是 |
| `weights/yolo11n-cls.pt` | 预训练权重（分类） | 5.5 MB | ✅ 是 |
| `weights/yolo11n.pt` | 预训练权重（检测） | — | ✅ 是 |
| `models/persimmon_cls_v1/best.pt` | **成熟度分类模型（88.89%）** | 3.05 MB | ✅ 是 |
| `models/persimmon_det_v1/best.pt` | 检测模型（mAP 88.23%） | — | ✅ 是 |
| `models/fruits_cls_v1/best.pt` | 物种模型（97.95%） | 3.07 MB | ✅ 是 |
| `dataset_persimmon/*.cache` | 训练缓存，会自动重建 | — | ❌ 已忽略 |

> **⚠️ 太行山采集的 100 多张实拍照片现在在桌面 `C:\Users\dell\Desktop\test3\`，不在项目里。**
> 建议移到 `dataset/field_trip/`（已加 gitignore 规则）。

---

## 三、文档（★ 这里最乱）

`docs/` 下 **8 份文档**，其中**两份和现在的实现对不上**：

| 文档 | 讲什么 | 状态 |
|---|---|---|
| `docs/ARCHITECTURE.md` | 系统架构、设计取舍、路线图 | ✅ 有效（10-05 已更新） |
| `docs/API.md` | **接口契约**，前后端对接靠它 | ✅ 有效 |
| `docs/TECH_DATA.md` | **技术数据汇总**，商业计划书素材 | ✅ 有效（10-05 新建） |
| `docs/FRONTEND_DESIGN.md` | 前端设计、五页面清单、令牌 | ✅ 有效 |
| `docs/DESIGN_WORKSHEET.md` | 数据库设计的方法与练习 | ✅ 有效 |
| `docs/FIELD_TRIP.md` | 太行山采集清单与访谈问题 | ✅ 有效 |
| **`docs/前端技术方案.md`** | 前端技术方案（概要设计） | ⚠️ **见下** |
| **`docs/UI设计规范.md`** | UI 设计规范（设计交付稿） | ⚠️ **见下** |

### ⚠️ 两份冲突的文档 —— 必须二选一

`前端技术方案.md` + `UI设计规范.md` 是**另一套设计**，和 `web/` 里已实现的不一致：

| | 那两份文档 | **现在实现（`web/`）** |
|---|---|---|
| 成熟度色值 | `#7EC850` `#E8B33A` `#E87A2A` `#D33B3B` | `#7a8c33` `#9c7a14` `#c4631f` `#9e2c21` |
| 主色 | **蓝色 `#2B7DE9`** | **无第六个强调色**（只有成熟度四色） |
| 登录 | **列为本期必做** | **明确不做** |
| 布局 | 检测页一屏两栏（左图右结果） | H5 单列 + 大屏两栏 |
| 对比度 | 未验证 | **已实测全部达标** |
| 是否已实现 | ❌ 没有代码对应 | ✅ 22 个文件已实现 |

**两份都留着 → 谁打开都会迷惑**（包括你自己三个月后，和面试官）。

**三条路：**
- **A. 删掉那两份**，以 `FRONTEND_DESIGN.md` 为准（我倾向这个，因为实现已经在那了）
- **B. 保留那两份当"早期方案"存档**，移到一个 `docs/archive/` 里
- **C. 保留，但在开头加一行"已被 `FRONTEND_DESIGN.md` 取代"**

（那两份里也有一些 `FRONTEND_DESIGN.md` 没写细的东西，比如组件级规范。C 能保住这部分。）

---

## 四、构建产物与缓存（不进 git，但占磁盘）

| 路径 | 是什么 | 能不能删 |
|---|---|---|
| `web/node_modules/` | npm 依赖，几万文件 | ✅ 能删（`npm install` 可重建） |
| `persimmon/target/` | Maven 编译产物 | ✅ 能删（重新编译就有） |
| `.idea/` | PyCharm 工程配置 | ⚠️ 删了要重新配解释器，**建议留** |
| `.ultralytics/` | Ultralytics 运行时配置 | ✅ 能删（自动重建） |
| `.mplcache/` | matplotlib 字体缓存 | ✅ 能删（自动重建） |
| `__pycache__/` | Python 字节码 | ✅ 能删 |
| `runs/` | 训练日志与结果图 | ⚠️ 见下 |
| `dataset_persimmon/*.cache` | 训练缓存 | ✅ 能删 |

### ⚠️ `runs/` 里有一堆重复的评估结果

```
runs/
├── persimmon_cls_v1/        ← 成熟度分类的训练记录（★ 重要，留）
├── classify/val/            ← 评估结果，第 1 次
├── classify/val-2/          ← 评估结果，第 2 次（★ 最新，混淆矩阵在这）
├── detect/val/              ← 检测评估，第 1 次
├── detect/val-2/            ← 检测评估，第 2 次
├── detect/persimmon_det_v1/ ← 检测训练记录
└── detect_predict/          ← 检测结果图 + 分辨率/切图对照实验图
```

**每次调一次 `val()` 就多一个 `val-N` 目录**，会一直堆。

**建议：**
- **留**：`persimmon_cls_v1/`（训练记录）、`detect/persimmon_det_v1/`（训练记录）、`classify/val-2/`（最新混淆矩阵）、`detect_predict/`（检测效果图，材料要用）
- **删**：`classify/val/`、`detect/val/`、`detect/val-2/`（旧的、被新版取代的）

> `runs/` 整个被 gitignore 了，所以删掉不影响仓库，只是清理磁盘。

---

## 五、两个"使命已完成"的东西 —— 你决定

### 5.1 `web/preview/design-preview.html`

**是什么：** 我做的静态预览页，用来在**不装 Node 的情况下**看设计长什么样（当时前端还没跑起来）。

**现在：** `npm run dev` 已经能跑了，真实页面比它准。

**三个选择：**
- **留** —— 面试时可以在**任何电脑上双击打开**展示界面，不用配环境（这个价值不小）
- **删** —— 它用的是**手写的 SVG 假图**，和真实效果有差距，可能误导
- **移到 `docs/`** —— 当设计稿存档

> 我倾向**留**。理由是它「零依赖可展示」——面试官面前你不想先跑 `npm install`。
> 但要在页面顶部写清"静态设计预览，非真实应用"。

### 5.2 `server/static/index.html`

**是什么：** FastAPI 自带的临时测试页，直接在浏览器拖图给 AI 服务试。

**现在：** 有正式前端了。

**但**：它访问的是 **8001 的 AI 服务**，**不经过 Java**。
调试 AI 时（比如换模型、调阈值）直接用它比走完整链路快得多。

> 我倾向**留**。它是"绕开业务层直连 AI"的调试入口，很有用。
> 删了的话，以后调 AI 就只能通过前端 → Java → Python 三层排查。

---

## 六、需要你拍板的五件事

| # | 决定什么 | 我的建议 | 影响 |
|---|---|---|---|
| **1** | 那份冲突的前端设计文档怎么处理 | 加"已作废"标记（选项 C），保住其中的组件细节 | 高 —— 不处理会持续误导 |
| **2** | `docs/` 8 份是否精简 | 现在不多，**建议先不动**。等材料定稿后再合并 | 低 |
| **3** | `runs/` 里的旧 `val-N` 目录 | 删旧的，留最新的 | 低（只占磁盘） |
| **4** | `web/preview/` | 留（零依赖展示有独特价值） | 中 |
| **5** | `server/static/` | 留（调试直连 AI 的入口） | 低 |

**另外两件小事：**
- `persimmon/HELP.md` —— IDEA 生成的样板文件，**可以删**
- 太行山照片还在桌面，**建议移到 `dataset/field_trip/`**

---

## 七、一句话总结现状

**代码结构其实是清楚的**：三个系统 + 数据 + 文档，各就各位。

**真正乱的是"文档层"** —— 同一件事有两套说法（前端设计），而且旧的那套没标作废。
**代码层几乎没有重复**（`java-backend` 你已经删了）。

所以**最该做的一件事就是第 6 节第 1 条**：给那两份冲突文档一个说法。
