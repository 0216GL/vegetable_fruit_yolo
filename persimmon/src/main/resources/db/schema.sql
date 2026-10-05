-- ============================================================================
--  柿子成熟度检测系统 —— 建库建表
-- ============================================================================
--  设计过程见 docs/DESIGN_WORKSHEET.md，这里是最后落地的 SQL。
--
--  三张表：
--    region        区域       一行 = 一个区域
--    capture       采集记录    一行 = 一次采集（一张图 + 一个区域 + 一个时间）
--    notification  通知        一行 = 系统主动发出的一条提醒
--
--  没有第 4 张"汇总表"—— "某区域某天总共多少"是**查出来**的，不是存出来的。
--  理由见文件末尾的注释。
-- ============================================================================

CREATE DATABASE IF NOT EXISTS persimmon
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE persimmon;

-- ----------------------------------------------------------------------------
-- 开发期方便重来，正式环境请删掉这三行
-- ⚠️ 删表顺序和建表顺序相反（先删依赖别人的）
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS notification;
DROP TABLE IF EXISTS capture;
DROP TABLE IF EXISTS region;


-- ============================================================================
--  1. region —— 区域
-- ============================================================================
--  关于"区域要不要能套娃"（大区域下面分小区域）：
--  这一版**不做**。你说了"先把我们负责的这一小块做好"。
--  真到要分层那天，加一个 parent_id 字段就行，不返工。
-- ============================================================================

CREATE TABLE region (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',

  name        VARCHAR(64)     NOT NULL                COMMENT '区域名称，如：东坡地',
  remark      VARCHAR(255)    DEFAULT NULL            COMMENT '备注',

  create_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

  PRIMARY KEY (id),

  UNIQUE KEY uk_region_name (name)
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT = '巡检区域';


-- ============================================================================
--  2. capture —— 采集记录
-- ============================================================================
--  ★ 这是三张表里会长得最快的一张，所有索引设计都是为它服务的。
--
--  ★ 为什么是四个数量，而不是一个"成熟度"字段？
--    因为一次采集会同时看到四类果实（比如 34 颗未熟 + 22 颗转色 + 41 颗着色 + 18 颗完熟）。
--    存"一个成熟度"根本表达不了。这是你这轮设计里最重要的一个修正。
--
--  ★ 为什么不存"总数"和"百分比"？
--    它们都能从这四个数算出来。
--    存了就要负责让它们永远和四个数一致 —— 那是自找麻烦。
--    能算出来的，不存。
-- ============================================================================

CREATE TABLE capture (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',

  region_id   BIGINT UNSIGNED NOT NULL                COMMENT '所属区域',

  captured_at DATETIME        NOT NULL                COMMENT '采集时刻（设备拍这张图的时间）',

  image_path  VARCHAR(255)    DEFAULT NULL            COMMENT '原图相对路径',

  -- ---- 四类果实的数量 ----
  count_unripe    INT UNSIGNED NOT NULL DEFAULT 0     COMMENT '未熟数量',
  count_turning   INT UNSIGNED NOT NULL DEFAULT 0     COMMENT '转色期数量',
  count_coloring  INT UNSIGNED NOT NULL DEFAULT 0     COMMENT '着色期数量',
  count_full      INT UNSIGNED NOT NULL DEFAULT 0     COMMENT '完熟数量',

  detect_ms   DECIMAL(8, 1)   DEFAULT NULL            COMMENT '第 1 层检测耗时(ms)',
  classify_ms DECIMAL(8, 1)   DEFAULT NULL            COMMENT '第 2 层分类耗时(ms)',

  create_time DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',

  PRIMARY KEY (id),

  KEY idx_region_time (region_id, captured_at),

  CONSTRAINT fk_capture_region
    FOREIGN KEY (region_id) REFERENCES region (id)
    ON DELETE RESTRICT
    ON UPDATE RESTRICT
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT = '一次采集的记录';


-- ============================================================================
--  3. notification —— 通知
-- ============================================================================
--  ★ 这张表存的是【事件】，不是【当前状态】。
--    一旦生成就是历史事实，不再修改。所以下面可以安全地存"当时"的四类数量。
--    ⚠️ 千万不要拿这张表当"当前成熟度"来查 ——
--       没超过阈值就不会有通知，所以它根本没有"当前值"。
-- ============================================================================

CREATE TABLE notification (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',

  region_id    BIGINT UNSIGNED NOT NULL                COMMENT '所属区域',

  triggered_at DATETIME        NOT NULL                COMMENT '触发时刻',

  -- 触发【当时】的四类数量快照。
  -- 存快照而不是百分比：百分比能从数量算出来，数量不能从百分比还原。
  -- 存了数量，通知自己就是完整的，用户点开不用再查库。
  count_unripe    INT UNSIGNED NOT NULL DEFAULT 0      COMMENT '触发时未熟数量',
  count_turning   INT UNSIGNED NOT NULL DEFAULT 0      COMMENT '触发时转色期数量',
  count_coloring  INT UNSIGNED NOT NULL DEFAULT 0      COMMENT '触发时着色期数量',
  count_full      INT UNSIGNED NOT NULL DEFAULT 0      COMMENT '触发时完熟数量',

  message      VARCHAR(255)    DEFAULT NULL            COMMENT '给用户看的一句话',

  -- 已读状态。不加索引 —— 它只有 0/1 两个值，区分度太低，
  -- 数据库对低区分度的列建了索引也基本不走，白白占空间。
  is_read      TINYINT         NOT NULL DEFAULT 0      COMMENT '0=未读 1=已读',

  create_time  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '入库时间',

  PRIMARY KEY (id),

  -- 查"某区域的通知，按时间倒序"—— 和 capture 表同一个模式
  KEY idx_region_time (region_id, triggered_at),

  CONSTRAINT fk_notification_region
    FOREIGN KEY (region_id) REFERENCES region (id)
    ON DELETE RESTRICT
    ON UPDATE RESTRICT
) ENGINE = InnoDB
  DEFAULT CHARSET = utf8mb4
  COLLATE = utf8mb4_unicode_ci
  COMMENT = '系统通知';


-- ============================================================================
--  为什么没有"汇总表"？
-- ============================================================================
--  "某区域某天总共多少"是这么查出来的：
--
--    SELECT region_id,
--           DATE(captured_at) AS day,
--           SUM(count_unripe)   AS unripe,
--           SUM(count_turning)  AS turning,
--           SUM(count_coloring) AS coloring,
--           SUM(count_full)     AS full
--    FROM capture
--    WHERE region_id = ?
--      AND captured_at >= ? AND captured_at < ?
--    GROUP BY region_id, DATE(captured_at);
--
--  不建汇总表的三个理由：
--    1. 数据量小 —— 一天几十条，GROUP BY 快得没感觉
--    2. 汇总表要维护，漏写一次就永久是错的；查询算出来的永远对
--    3. 等它真慢了再加 —— 那时你有真实数据，才知道该按什么维度汇总
--
--  ⚠️ 注意：多组数据汇总时【先加数量，再算比例】，千万不要 AVG(百分比)。
--     采集A：10 颗里 9 颗可采 → 90%
--     采集B：100 颗里 40 颗可采 → 40%
--     错的： (90% + 40%) / 2      = 65%
--     对的： (9 + 40) / (10 + 100) = 44.5%
--     样本大小不一样，凭什么各占一半权重。
-- ============================================================================


-- ============================================================================
--  手工验证用（建完表跑一下确认）
-- ============================================================================
-- INSERT INTO region (name, remark) VALUES ('东坡地', '演示用');
-- INSERT INTO capture (region_id, captured_at, image_path,
--                      count_unripe, count_turning, count_coloring, count_full)
--   VALUES (1, NOW(), 'capture/demo.jpg', 34, 22, 41, 18);
--
-- SELECT r.name, DATE(c.captured_at) AS day, SUM(c.count_coloring + c.count_full) AS ready
--   FROM capture c JOIN region r ON r.id = c.region_id
--   GROUP BY r.name, DATE(c.captured_at);
