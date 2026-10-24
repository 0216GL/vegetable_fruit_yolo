# web —— 前端

Vue 3 + Vite + Pinia + Vue Router（JavaScript，非 TS）。设计说明见 [`../docs/FRONTEND_DESIGN.md`](../docs/FRONTEND_DESIGN.md)。

> ✅ **五个页面已全部完成**（2026-10-05），接口已接后端、全链路跑通。

---

## 跑起来

```bat
cd /d D:\vegetable_fruit_yolo\web
npm install     :: 第一次才要
npm run dev
```

打开 <http://localhost:5173>（会自动跳到 `/h5`）。

| 地址 | 是什么 |
|---|---|
| `/h5` | 手机端：上传 → 结果 → 历史（**主要操作入口**） |
| `/screen` | 大屏：路演投影演示用（纯展示，**没有操作按钮**） |
| `/dev/tokens` | 设计令牌自检（开发用，上线删） |

> 手机端在电脑浏览器里也能开（不锁设备），只是被限成 480px 宽、模拟手机。

---

## 目录结构

```
web/
├── vite.config.js              ★ 含 /api 开发代理，转发到 8080
├── index.html
├── package.json
└── src/
    ├── main.js                 ★ 样式引入顺序在这里定
    ├── App.vue
    ├── router/index.js          路由表
    ├── config/
    │   └── brand.js             产品名 + 可采收率门槛（待确认的业务规则）
    ├── utils/
    │   └── ripeness.js          ★ 四个成熟度的唯一真源
    ├── api/
    │   ├── request.js           ★ axios 实例：统一拆 R<T>、统一报错
    │   └── inspection.js         四个接口的封装
    ├── stores/
    │   └── inspection.js        最近一次结果（内存，不落盘）
    ├── styles/
    │   ├── primitives.css         第一级令牌：只有值
    │   ├── semantic.css           第二级令牌：只有用途
    │   ├── base.css               重置 + 浏览器自带部分
    │   └── element-plus.css       覆盖 Element Plus 的默认长相
    ├── components/
    │   ├── AnnotatedImage.vue   ★ 逐果标注图（英雄区）
    │   ├── RipenessBar.vue        成熟度色带
    │   └── RipenessBadge.vue      成熟度标签
    ├── layouts/
    │   ├── H5Layout.vue           手机端外壳（限 480px 居中）
    │   └── ScreenLayout.vue       大屏外壳（切深色面）
    └── views/
        ├── DevTokens.vue          令牌自检页（临时）
        ├── h5/
        │   ├── Upload.vue       ★ 上传页（选图 + 区域下拉框）
        │   ├── Result.vue         结果页（标注图 + 可采收率 + 逐果清单）
        │   └── History.vue        历史列表
        └── screen/
            └── Dashboard.vue      大屏看板
```

---

## 两个表面

- **`/h5` 手机端 = 操作面**：拍照、上传、看结果、查历史
- **`/screen` 大屏 = 展示面**：路演投影给评委看，**故意没有按钮**。
  它读的是"最近一次上传的结果"（存在 store 里，刷新即失）。
  想在它上面看到真实数据，先去 `/h5` 传一张。

两者**共用**设计令牌和 API 层，但**不共用**布局 —— 用途差别太大。
**大屏不是"手机端的电脑版"，它是另一张脸。**

---

## 三条不能破的规矩

**1. 组件里不许出现十六进制色值。**
只能用 `semantic.css` 里的语义令牌。要新颜色，先在 `primitives.css` 加值，
再到 `semantic.css` 加语义名。

**2. 产品名从 `config/brand.js` 读，不要写死在模板里。**
用户明确说了名字后期要改。

**3. 成熟度的中文名和颜色从 `utils/ripeness.js` 读。**
它是和 Java 的 `AiPredictResponse`、Python 的 `schemas.py` 对应的契约层。
改这里等于改接口，两边要同时改。

---

## 前后端怎么连

前端写 `axios.get('/api/health')`，Vite 把 `/api` 转发到 `http://localhost:8080`（见 `vite.config.js`）。

**所以开发时三个服务都要起：** AI 服务（8001）→ Java 后端（8080）→ 前端（5173）。
前端**不直接连 8001** —— 它只跟 Java 说话，AI 服务对前端是透明的。

```bat
cd /d D:\vegetable_fruit_yolo
D:\Anaconda\envs\yolo\python.exe -m uvicorn ai.server.app:app --host 0.0.0.0 --port 8001
```

```bat
cd /d D:\vegetable_fruit_yolo\persimmon
mvnw spring-boot:run         :: Java 业务后端，8080
```

> ⚠️ **上传前确认 region 表里有数据**，否则区域下拉框为空、提交按钮点不动
> （看着像"识别不了"，其实是按钮压根没让你点）。
