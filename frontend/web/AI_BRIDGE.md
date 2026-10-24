# 识别接口桥接说明（AI Bridge）

这份前端（`frontend/web/`，v27 快照）原本是纯静态展示页。「识别工作台」是一个
**本地观察台**：照片只在浏览器里预览，右侧按钮写死成灰色的
「真实检测 · 模型待接入」，点不动。

本目录多出来的两个文件，把它接到了本项目自己的两层识别模型上：

| 文件 | 作用 |
|---|---|
| `dist/assets/ai-bridge.js` | 桥接层本体。**只有这一份**，要改逻辑改它 |
| `inject_ai_bridge.py` | 把上面那个文件挂进 `dist/index.html` 的小工具 |

`dist/index.html` 里只多了一句（在 `</body>` 前）：

```html
<script src="assets/ai-bridge.js"></script>
```

原页面的 HTML 结构、内联 JS、全部 CSS（背景图、配色、动效、观察台布局）
**一个字节都没动**。注入脚本按字节插入，自带自检：把那 47 字节抠掉之后，
必须和 `dist/index.original.html`（原始备份）逐字节一致。

---

## 一、怎么跑起来

顺序不能乱，三个东西都要在：

```bat
:: ① 识别服务（两层模型）
cd /d D:\vegetable_fruit_yolo
D:\Anaconda\envs\yolo\python.exe -m uvicorn ai.server.app:app --host 0.0.0.0 --port 8001

:: ② 可选：Java 后端（要落库才需要；不启动也能识别，只是不写 MySQL）
cd /d D:\vegetable_fruit_yolo\persimmon
mvnw spring-boot:run

:: ③ 前端静态站 —— 必须用项目自带的 serve_frontend.py
D:\Anaconda\envs\yolo\python.exe D:\vegetable_fruit_yolo\serve_frontend.py 8089 "D:\vegetable_fruit_yolo\frontend\web\dist"
```

浏览器打开 <http://127.0.0.1:8089/index.html> → 顶部「识别工作台」。

> ⚠️ **不要用 `python -m http.server`**。
> Windows 上 Python 自带的 `mimetypes` 不认识 `.webp`，会以 `application/octet-stream`
> 发出去，浏览器拒绝渲染 → 所有背景图不显示，只剩 CSS 里的兜底底色，看起来像「整站变蓝」。
> `serve_frontend.py` 就是为这个坑写的（顺手禁了缓存）。

---

## 二、它到底做了什么

1. **按钮可用** —— 把「真实检测 · 模型待接入」改成「开始成熟度检测」，
   去掉 `disabled`，用行内样式盖成主题橙（页面自己的 `--ow-orange` 那一挂）。
   选了几张会显示成「开始成熟度检测（3 张）」。
2. **支持多张** —— 给隐藏的 `#ow-file` 加 `multiple`，选择和拖拽都收；
   逐张**串行**上传，不并行打爆单卡服务；某张失败只红那一张，不影响后面的。
3. **结果在图下面** —— 在图片下方的缩放工具条 `.ow-toolbar` 后面插入新面板
   `#ai-results`，每张图一张卡片：画好检测框的照片 + 各成熟度等级数量 + 耗时。
   面板最高 520px，图多时自己滚动，不会把页面撑爆。
4. **检测框前端自己画** —— 后端只回坐标（`detections[].box`），不回图片，
   省一次图片传输；前端按原图坐标画在 canvas 上再等比缩小显示。
5. **双链路自动切换** —— 先探 Java `8080/api/health`：活着走 Java（结果写进
   MySQL `capture` 表），探不到就直连 Python `8001`（只推理、不落库）。
   页面右上角的小圆点和说明会显示当前走哪条。
6. **文案纠错** —— 页面原话「照片仅在当前浏览器中预览」「苹果为拓展品类，尚未接入
   对应模型」「模型尚未接入，当前没有成熟度结果」在接上模型后都不成立了，
   桥接层会在对应时机改成实话。
7. **动画性能** —— 卡顿来自首页两个全屏 canvas 粒子动画，优化分两处：
   - `frontend/web/patch_perf.py` 改 `index.html` 里的粒子参数（降 DPR、减粒子、限 30fps、
     CSS 变量去重），可 `--restore` 一键回滚；
   - 本文件里的**离屏动画守卫**：滚出视口的无限循环 CSS 动画自动暂停，回到视口再继续
     （网址加 `?noanim=1` 可关掉）。
   合计待机 CPU 降约 42%（实测方法见 `patch_perf.py` 顶部说明）。
8. **多了一张「巡检记录」页** —— 顶部导航新增入口，展示数据库里的历史记录
   （时间 / 地块 / 品种 / 各级数量 / 总数 / 可采收率 / 图片缩略图，带翻页）。
   数据走 Java 的 `GET /api/inspection/list`。

支持品种：**柿子（4 级）**、**苹果（3 级）**。
梨、桃仍是「待开放」，点它们按钮会提示「该品类尚未接入模型」。

### 它是怎么挂上去的

页面切路由是整块重写 `#app.innerHTML`，所以不能只在加载时挂一次：

- 包裹 `window.render()` —— 每次重渲染后重新挂载；
- 另加一个 `MutationObserver` 兜底（写 DOM 全部幂等，不会自激成死循环）。

当前文件、当前品类不靠猜 DOM，直接读页面自己的全局状态 `orchardState.file` /
`orchardState.fruit`（页面用 `const` 声明的，同页面的普通脚本可以直接读）。

---

## 三、想还原 / 想重装

```bat
:: 撤销注入（只删那一行）
D:\Anaconda\envs\yolo\python.exe frontend\web\inject_ai_bridge.py --remove

:: 整份还原成队友交付的原样
D:\Anaconda\envs\yolo\python.exe frontend\web\inject_ai_bridge.py --restore
```

队友发来**新版本前端**时：先整份覆盖 `dist/`，再跑一次（不带参数），
它会重新注入并自动备份。重复跑是安全的，已经注入过会提示跳过。

---

## 四、两个已知点

1. **接口地址写死在脚本里**：Java 认 `127.0.0.1:8080`，Python 认 `127.0.0.1:8001`。
   换机器/换端口要改 `dist/assets/ai-bridge.js` 顶部的 `ENDPOINTS` 和 `HEALTH`。
   两个服务都已开 CORS（Python 是 `allow_origins=["*"]`），静态站（8089）能直接跨源调。
2. **`SHA256SUMS.txt` 会有一行对不上**：它是队友导出快照时算的，我们改过
   `index.html` 又新增了 `ai-bridge.js`。校验时以 `dist/index.original.html` 为准，
   或者先 `--remove` 再校验。

---

## 五、自测记录（2026-10-22）

用 Chrome 无头 + CDP 真跑过一遍，不是只跑语法检查：

| 用例 | 结果 |
|---|---|
| 进入 `#recognize/persimmon` | 面板挂载、`#ow-file` 已 `multiple`、按钮文案正确、连接状态显示「结果写入数据库」 |
| 选 2 张 → 点检测 | 2 张卡片、2 张标注图，`完成 2/2 张 · 684 ms`，等级统计正确 |
| 切苹果 → 检测 | 走通 3 级链路，统计为「未熟/转色期/成熟」，无报错 |
| 切梨 | 按钮正确禁用，提示「该品类尚未接入模型」 |
| 控制台 | 只有一条 `favicon.ico 404`（页面本来就没放图标，无害） |
