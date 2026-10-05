# persimmon —— Java 后端

柿子成熟度检测系统的业务后端。Spring Boot 4.0.8 + Java 17 + MyBatis + MySQL。

---

## 一、哪些是搭好的，哪些要你写

### ✅ 已经搭好（我写的，你要看一眼）

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
└── ai/                              ★ 与 Python 的边界
    ├── AiPredictResponse.java       AI 返回结构（= schemas.py 的镜像）
    └── AiClient.java                调用 AI 服务 ← 这个要读
```

`src/main/resources/`
```
├── application.yaml               ★ 数据库连接 + MyBatis 配置
└── db/schema.sql                  建表 SQL（已执行）
```

### ⬜ 你来写

```
src/main/java/org/ymg/persimmon/
├── entity/                         对应数据库表
│   ├── Region.java                 id, name, remark, createTime
│   ├── Capture.java                id, regionId, capturedAt, imagePath,
│   │                               countUnripe/Turning/Coloring/Full,
│   │                               detectMs, classifyMs, createTime
│   └── Notification.java           id, regionId, triggeredAt,
│                                   四个 countXxx, message, isRead, createTime
│
├── mapper/                         接口，不写实现（MyBatis 动态生成）
│   ├── RegionMapper.java
│   ├── CaptureMapper.java
│   └── NotificationMapper.java
│
├── service/
│   └── CaptureService.java         ★ 核心：调 AI → 转成 Capture → 落库
│
└── controller/
    └── CaptureController.java      上传图片的接口
```

**建议顺序：`Region` → `RegionMapper` → 一个最简单的查询 Controller → 跑通 → 再写 `Capture`。**

别三个实体一起写完再试。出了错你不知道是哪个的问题。

---

## 二、三个必踩的坑（先看，省你两小时）

### ① 下划线转驼峰 —— 不配置就是"全是 null，且不报错"

已经帮你在 `application.yaml` 里配好了：

```yaml
mybatis:
  configuration:
    map-underscore-to-camel-case: true
```

**这个坑的特征：接口通、SQL 没错、字段全是 null。** 最难受的一类 bug。
如果以后你查出来对象字段是空的，第一件事回来检查这行还在不在。

### ② Mapper 必须是接口 + 已经在启动类上扫了包

`@MapperScan("org.ymg.persimmon.mapper")` 已经加在启动类上了。
**所以你新建 Mapper 只要放在 `org.ymg.persimmon.mapper` 包下就行**，不用每个都写 `@Mapper`。

放错包 = 启动报"找不到 bean"，而且错误信息不会提包名。

### ③ 时间用 `LocalDateTime`，不要用 `Date`

数据库是 `DATETIME`，Java 对应 `java.time.LocalDateTime`（Java 8+ 标准做法）。
用 `java.util.Date` 面试会被问"为什么不用新 API"。

---

## 三、你要写的第一段核心逻辑

`CaptureService` 里那段"AI 结果 → 数据库记录"的转换，是整个后端的核心：

```
AI 返回：  counts = { "1_unripe": 34, "2_turning": 22, ... }   ← 英文 key 的 Map
                                  ↓  转换
表字段：   countUnripe=34, countTurning=22, ...                ← 四个独立列
```

**两个现成的工具已经给你了：**

- `AiPredictResponse.countOf("1_unripe")` —— 直接从 Map 取数，自动兜底 null 和 0
- `AiPredictResponse.timing().detectMs()` —— 取耗时

**四个 key 是固定的，别写错：**
```
1_unripe   2_turning   3_coloring   4_full
```
（和 Python 端 `inference.py` 的 `RIPENESS_CLASSES` 必须一字不差）

---

## 四、跑起来

**启动前先确认两件事：**

1. `application.yaml` 里 **数据库密码改成你自己的**
2. **Python AI 服务已经起来了** —— 否则调 AI 时会报"AI 服务连不上"

```bat
cd /d D:\vegetable_fruit_yolo
D:\Anaconda\envs\yolo\python.exe -m uvicorn ai.server.app:app --host 0.0.0.0 --port 8001
```

```bat
cd /d D:\vegetable_fruit_yolo\persimmon
mvnw spring-boot:run              :: 再起这个（8080）
```

看到 `Tomcat started on port 8080` 就是成了。

**访问 http://localhost:8080/api/health** 应该能看到 Java 和 AI 两边的状态。

---

## 五、⚠️ 两个我没法验证的风险

**一、Spring Boot 4.0 我只写了很久之前就存在的 API。**

Boot 4 是很新的版本（你的 pom 里 starter 都改名了：
`spring-boot-starter-web` → `spring-boot-starter-webmvc`）。
`RestTemplateConfig` 那一处我**最没把握** —— 如果编译不过，把报错整段贴出来。

**二、这份代码我一行都没跑过。**

我这边没有能执行命令的环境。所以**有报错是正常的**，不是藏了问题。
贴给我，我改。

---

## 六、前后端的契约（别改坏）

前端 `web/src/api/request.js` 已经写死了这个约定：

```js
if (body.code !== 0) { 弹错误; 抛异常 }
return body.data        // 剥掉外壳
```

**所以：所有接口必须返回 `R<T>`**，`code=0` 表示成功。
你如果自己加接口，也照这个来 —— 否则前端每个页面都要改。
