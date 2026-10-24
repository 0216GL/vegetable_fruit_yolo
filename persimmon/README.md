# persimmon —— Java 后端

柿子成熟度检测系统的业务后端。Spring Boot 4.0.8 + Java 17 + MyBatis + MySQL。

> ✅ **业务层已写完，全链路已跑通**（2026-10-05）。
> 上传 → 识别 → 落库 → 历史查询，四个接口全部可用。

---

## 一、目录结构

```
src/main/java/org/ymg/persimmon/
├── PersimmonApplication.java      ★ 启动类 + @MapperScan
│
├── common/                          通用层（和业务无关）
│   ├── R.java                       统一响应体 {code, message, data}
│   ├── ErrorCode.java               错误码表
│   ├── BizException.java            业务异常
│   └── GlobalExceptionHandler.java  全局异常收口
│
├── config/
│   ├── WebConfig.java               跨域
│   └── RestTemplateConfig.java      HTTP 客户端 + 超时
│
├── ai/                              ★ 与 Python 的边界
│   ├── AiPredictResponse.java       AI 返回结构（= schemas.py 的镜像）
│   └── AiClient.java                调用 AI 服务 ← 这个值得一读
│
├── entity/                          ★ 对应数据库表
│   ├── Region.java                  id, name, remark, createTime
│   └── Capture.java                 一行 = 一次采集（品种 + 各级数量 ripeness）
│
├── dto/
│   └── CaptureListItem.java         历史列表返回给前端的形状（VO）
│
├── mapper/                          接口，不写实现（MyBatis 动态生成）
│   ├── RegionMapper.java
│   └── CaptureMapper.java           ★ 含唯一的 JOIN
│
├── service/
│   ├── RegionService.java           区域校验
│   └── CaptureService.java          ★ 核心：调 AI → 转成 Capture → 落库
│
└── controller/
    ├── RegionController.java        GET /api/region/list
    ├── CaptureController.java       POST predict + GET list
    └── HealthController.java        GET /api/health
```

`src/main/resources/`
```
├── application.yaml               ★ 数据库连接 + MyBatis 配置
└── db/schema.sql                  建表 SQL（已执行）
```

---

## 二、四个接口

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/inspection/predict` | 上传图片 → 调 AI → 落库 → 返回结果。multipart，字段 `file` + `regionId` |
| GET | `/api/inspection/list` | 历史列表分页。JOIN region 取区域名，现算 total / readyRate |
| GET | `/api/region/list` | 区域下拉框数据源 |
| GET | `/api/health` | Java + AI 是否都活着 |

> **契约的权威版本是 [`../docs/API.md`](../docs/API.md)。** 所有接口返回 `R<T>`。

---

## 三、分层职责（改代码前先看这个）

| 层 | 干什么 | 不干什么 |
|---|---|---|
| entity | 表在 Java 里的样子 | 不掺接口专用字段 |
| dto | 接口返回的形状（VO） | 不直接当表用 |
| mapper | 只管 SQL 读写 | 不写业务判断 |
| service | 业务规则、转换、校验 | 不碰 HTTP |
| controller | 接参数、调 service、包 `R` | 不写业务逻辑 |

---

## 四、跑起来

**启动前确认三件事：**

1. `application.yaml` 里**数据库密码**已填（默认是占位符 `改这里`）
2. MySQL 有 `persimmon` 库、三张表，且 **region 至少有一条数据**
   —— 否则上传报 `4004`、前端区域下拉框为空、提交按钮点不动
3. **AI 服务（8001）先起来**

```bat
:: ① 先起 AI 服务（8001）—— 必须在项目根目录
cd /d D:\vegetable_fruit_yolo
D:\Anaconda\envs\yolo\python.exe -m uvicorn ai.server.app:app --host 0.0.0.0 --port 8001

:: ② 再起 Java 后端（8080）
cd /d D:\vegetable_fruit_yolo\persimmon
mvnw spring-boot:run
```

看到 `Started PersimmonApplication` 就是成了。
访问 <http://localhost:8080/api/health> 能看到 Java 和 AI 两边的状态。

---

## 五、几个关键设计（答辩 / 面试会问）

**① 统一响应体 `R<T>`** —— 所有接口返回 `{code, message, data}`，`code=0` 成功。
前端拦截器靠它判断成败，不能改。

**② 全局异常收口** —— `@RestControllerAdvice` 把异常统一转成 `R`。
所以 Controller 里**一个 try-catch 都不用写**。

**③ `map-underscore-to-camel-case: true`** —— 数据库列 `region_name` ↔ Java 字段 `regionName`。
**不配置的话，字段全是 null 而且不报错**，是最难查的一类 bug。

**④ 时间用 `LocalDateTime`**，不用老的 `java.util.Date`。

**⑤ `total` / `readyRate` 不存库，查询时现算** —— 能算出来的不存。
算法在 `RipenessCodec`：`total` 是 `ripeness` 各位相加，`readyRate` 是"可采收颗数/总数"。

**⑥ 品种决定成熟度怎么读** —— `capture` 只有一列 `ripeness`（如 `0,2,4,17`），
里面几位、每位是什么等级，由同一行的 `species` 决定（柿子 4 位、苹果 3 位）。
这套对应关系**只在 `org.ymg.persimmon.common.RipenessCodec` 写一份**，别的代码不许自己 split。

**⑥ 历史列表要 JOIN** —— capture 表只有 `region_id`，区域名在 region 表。

---

## ⚠️ Spring Boot 4 的两个坑

**一、Jackson 3。** Boot 4 的默认 JSON 库换成了 Jackson 3，`databind`/`core` 的包名从
`com.fasterxml.jackson` 改成了 `tools.jackson`。**但注解（`@JsonProperty` / `@JsonFormat`
/ `@JsonIgnoreProperties`）没改名**，仍然是 `com.fasterxml.jackson.annotation`。
写错会报「程序包 com.fasterxml.jackson.databind 不存在」。

**二、starter 改名。** `spring-boot-starter-web` → `spring-boot-starter-webmvc`。
`RestTemplateBuilder` 的超时 API 也有变动，`RestTemplateConfig` 里改用了低层的
`SimpleClientHttpRequestFactory` 绕开。

---

## 六、前后端的契约（别改坏）

前端 `web/src/api/request.js` 已经写死了这个约定：

```js
if (body.code !== 0) { 弹错误; 抛异常 }
return body.data        // 剥掉外壳
```

**所以：所有接口必须返回 `R<T>`**，`code=0` 表示成功。
自己加接口也照这个来 —— 否则前端每个页面都要改。
