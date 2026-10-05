# web —— 前端

Vue 3 + Vite + JavaScript。设计说明见 [`../docs/FRONTEND_DESIGN.md`](../docs/FRONTEND_DESIGN.md)。

---

## 跑起来

```bat
cd /d D:\vegetable_fruit_yolo\web
npm install
npm run dev
```

打开 http://localhost:5173 。

**当前打开的是「设计令牌自检」页**，它会：

- 实时计算成熟度色在浅底/深底上的对比度，**标红不达标的**
- 显示字号梯度、间距刻度
- 演示焦点环、文字选中色、数字等宽

这是开发工具，上线前要删掉。

> 首次 `npm install` 要下载依赖，一两分钟正常。
> 如果报版本冲突，把报错贴出来 —— `package.json` 里的版本是为 Node 24 选的，
> 但不同机器上依赖树可能不一样。

---

## 目前有什么

```
web/
├── vite.config.js              ★ 含 /api 开发代理，转发到 8080
├── index.html
├── package.json
└── src/
    ├── main.js                 ★ 样式引入顺序在这里定
    ├── App.vue
    ├── router/index.js          路由表（H5 / 大屏的路由先注释着）
    ├── config/
    │   └── brand.js             ★ 产品名 + 可采收率门槛（待确认的业务规则）
    ├── utils/
    │   └── ripeness.js          ★ 四个成熟度的唯一真源
    ├── api/
    │   └── request.js           ★ axios 实例：统一拆 R<T>、统一报错
    ├── styles/
    │   ├── primitives.css         第一级令牌：只有值
    │   ├── semantic.css           第二级令牌：只有用途
    │   ├── base.css               重置 + 浏览器自带部分
    │   └── element-plus.css       覆盖 Element Plus 的默认长相
    └── views/
        └── DevTokens.vue          令牌自检页（临时）
```

**还没有页面。** 下一步是 `AnnotatedImage.vue`（逐果标注图）+ 上传页 + 结果页。

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

**所以开发时两个后端都要起：**

```bat
cd /d D:\vegetable_fruit_yolo
D:\Anaconda\envs\yolo\python.exe -m uvicorn ai.server.app:app --host 0.0.0.0 --port 8001
```

```bat
cd /d D:\vegetable_fruit_yolo\persimmon
mvnw spring-boot:run         :: Java 业务后端，8080
```

前端不直接连 8001 —— 它只跟 Java 说话，AI 服务对前端是透明的。
