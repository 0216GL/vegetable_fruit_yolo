# 接口契约

> **这份就是"前端定的接口"，后端照着它实现就行。**
> 前端代码在 `web/src/api/inspection.js`，它写的就是下面这些。
> 2026-10-05

---

## 一、一条铁律

**所有接口都返回这个结构：**

```json
{ "code": 0, "message": "ok", "data": { ... } }
```

- `code = 0` → 成功，前端读 `data`
- `code ≠ 0` → 失败，前端弹 `message` 里的提示

前端的 `web/src/api/request.js` 里已经写死了这个判断，**所以后端必须按这个来**。
Java 侧对应的类：`org.ymg.persimmon.common.R`。

**你写 Controller 时只要 `return R.ok(数据)` 或 `return R.fail(码, "提示")` 就行。**
异常不用 try-catch，`GlobalExceptionHandler` 会统一接住。

---

## 二、接口清单

### ① 上传图片识别

```
POST  /api/inspection/predict
Content-Type: multipart/form-data
```

| 参数 | 位置 | 说明 |
|---|---|---|
| `file` | 表单字段 | 图片文件。**名字必须是 file**，叫别的会 400 |

**返回：**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "ok": true,
    "image": { "width": 4096, "height": 3072 },
    "detections": [
      { "box": [392,754,833,1129], "det_conf": 0.976,
        "ripeness": "3_coloring", "ripeness_label": "着色期（橙红）",
        "ripeness_conf": 0.897 }
    ],
    "counts": { "1_unripe": 34, "2_turning": 22, "3_coloring": 41, "4_full": 18 },
    "timing": { "detect_ms": 42.1, "classify_ms": 86.3 },
    "error": null
  }
}
```

`data` 的结构就是 `ai/AiPredictResponse.java` 的形状 —— **直接把 AI 返回的整个对象透传给前端**，
再顺手往 capture 表存一条。

> **注意：图里没有柿子不是错误。** 这时 `code` 仍然是 `0`，
> `detections` 是空数组， `counts` 四项都是 0。
> "识别结果为空"和"识别失败"必须分开，前端要分别处理。

---

### ② 历史列表

```
GET  /api/inspection/list?page=1&size=20
```

| 参数 | 说明 |
|---|---|
| `page` | 第几页，从 1 开始 |
| `size` | 每页多少条 |

**返回：**

```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "list": [
      { "id": 1, "regionName": "东坡地",
        "capturedAt": "2026-10-03 15:22:01",
        "total": 115, "readyRate": 51 }
    ],
    "total": 1
  }
}
```

字段来源（注意**不是**直接对应表字段，要转）：

| 前端要的 | 从哪来 |
|---|---|
| `id` | `capture.id` |
| `regionName` | 要 **JOIN region 表** 取 `region.name`，capture 表里只有 `region_id` |
| `capturedAt` | `capture.captured_at` |
| `total` | 四个 count 相加，**表里没这列** |
| `readyRate` | (着色 + 完熟) ÷ 总数 × 100，**表里没这列** |

> ⚠️ **这是你写 SQL 时第一个要 JOIN 的地方。**
> 表设计时刻意没在 capture 里冗余区域名（改个区域名要更新所有历史记录，不划算）。
> `total` 和 `readyRate` 也不存 —— 能算出来的不存。

---

### ③ 健康检查

```
GET  /api/health
```

```json
{
  "code": 0,
  "message": "ok",
  "data": { "java": "ok", "aiService": "ok" }
}
```

用来看 Java 和 Python 两边是否都活着。`aiService` 为 `down` 说明 Python 服务没起。

---

## 三、⚠️ 前端有一处字段名对不上，需要改

前端 `web/src/views/h5/History.vue` 是**早先按旧设计写的**，字段名和现在的表对不上：

| History.vue 现在读的 | 应该改成 |
|---|---|
| `it.plot` | `it.regionName` |
| `it.createdAt` | `it.capturedAt` |
| `it.fruitCount` | `it.total` |

**三个字段名，我改一下就行**（说一声我就改）。不改的话，历史页会显示空白 ——
而且**不会报错**，因为是拿到 `undefined` 直接渲染，这种 bug 最难查。

> 这件事本身也说明一个道理：**接口契约一变，两端都要改。**
> 所以定契约的时候要想清楚 —— 这也是为什么我们前面花那么多时间做设计。

---

## 四、还没做、暂时不做的接口

| 接口 | 状态 |
|---|---|
| `GET /api/inspection/{id}` | 详情页要用的，前端函数写好了但没人调，先不做 |
| `GET /api/stats/overview` | 大屏用的，前端函数写好了但**大屏现在读的是内存里的数据**，没调它，先不做 |
| `POST /api/auth/*` | 登录，**明确不做** |

所以你现在**只要实现上面那三个接口**（①②③），前端所有页面就都能跑通真实数据。
