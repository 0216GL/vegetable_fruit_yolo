-- ============================================================================
--  柿子成熟度检测系统 —— 建库建表
-- ============================================================================
--  这里是最后落地的建表 SQL（设计与取舍都写在下面的注释里）。
--
--  三张表：
--    region        区域       一行 = 一个区域
--    capture       采集记录    一行 = 一次采集（一张图 + 一个品种 + 一个区域 + 一个时间）
--    notification  通知        一行 = 系统主动发出的一条提醒（当前代码还没用到）
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
--  ★ 一行 = 一张图。一张图里通常不止一颗果，而且各颗的成熟度不一样
--    （库里真实数据：平均 7.3 颗/张，最多 43 颗；53/99 张图同时出现 2 个以上等级）。
--    所以成熟度这一列存的不是一个等级，而是【各级各有几颗】：
--
--      species      ripeness        解读
--      ----------   -------------   ------------------------------------
--      persimmon    "0,2,4,17"      未熟0 / 转色期2 / 着色期4 / 完熟17
--      apple        "1,3,8"         未熟1 / 转色期3 / 成熟8
--
--    顺序由 species 决定，解码规则唯一权威在
--    Java 的 org.ymg.persimmon.common.RipenessCodec（前端可用接口返回的 gradeText）。
--
--  ★ 为什么不给每一级建一列（count_unripe / count_turning / …）：
--    那样等级就被写死在表结构里了。柿子 4 级、苹果 3 级、以后加第 5 级或第三个品种，
--    每次都要改表 + 改实体 + 改 SQL。现在加品种只改 RipenessCodec 一处。
--
--  ★ 为什么不存 总数 / 可采收率 / 耗时：
--    都能算出来，或者根本不属于业务数据。
--    total  = ripeness 各位相加
--    ready  = 可采收颗数 / total（柿子取着色期+完熟，苹果取成熟）
--    耗时  = 性能指标，日志里有，不该让业务表背这个包袱
--    「能算出来的，不存。」
-- ============================================================================

CREATE TABLE capture (
  id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',

  region_id   BIGINT UNSIGNED NOT NULL                COMMENT '所属区域',

  species     VARCHAR(16)     NOT NULL                COMMENT '品种：persimmon=柿子(4级) / apple=苹果(3级)，决定 ripeness 怎么解读',

  captured_at DATETIME        NOT NULL                COMMENT '采集时刻（设备拍这张图的时间）',

  image_path  VARCHAR(255)    DEFAULT NULL            COMMENT '原图相对路径（图片落盘还没做，暂时为 NULL）',

  ripeness    VARCHAR(32)     NOT NULL                COMMENT '各级果实数量，逗号分隔，顺序由 species 决定，如柿子 0,2,4,17',

  PRIMARY KEY (id),

  -- 查"某区域最近的采集记录"
  KEY idx_region_time  (region_id, captured_at),

  -- 查"某品种最近的采集记录"
  KEY idx_species_time (species, captured_at),

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
--  ⚠️ 这张表结构已经和新方案对齐，但**当前没有任何 Java 代码在用**。
--     要做"哪块地该采了"的提醒功能时再补 Mapper / Service / Controller。
--
--  ★ 这张表存的是【事件】，不是【当前状态】。
--    一旦生成就是历史事实，不再修改。所以下面可以安全地存"当时"的数量快照。
--    ⚠️ 千万不要拿这张表当"当前成熟度"来查 ——
--       没超过阈值就不会有通知，所以它根本没有"当前值"。
-- ============================================================================

CREATE TABLE notification (
  id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',

  region_id    BIGINT UNSIGNED NOT NULL                COMMENT '所属区域',

  species      VARCHAR(16)     NOT NULL                COMMENT '品种：persimmon / apple',

  triggered_at DATETIME        NOT NULL                COMMENT '触发时刻',

  -- 触发【当时】的数量快照，格式与 capture.ripeness 完全一致。
  -- 存快照而不是百分比：百分比能从数量算出来，数量不能从百分比还原。
  -- 存了数量，通知自己就是完整的，用户点开不用再查库。
  ripeness     VARCHAR(32)     NOT NULL                COMMENT '触发时各级数量，如柿子 0,2,4,17',

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
--  "某区域某天总共多少"是这么查出来的（MySQL 8 才有 REGEXP_SUBSTR）：
--
--    SELECT region_id,
--           DATE(captured_at) AS day,
--           SUM(CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(ripeness, ',', 1), ',', -1) AS UNSIGNED)) AS g1,
--           SUM(CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(ripeness, ',', 2), ',', -1) AS UNSIGNED)) AS g2,
--           SUM(CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(ripeness, ',', 3), ',', -1) AS UNSIGNED)) AS g3,
--           SUM(CAST(SUBSTRING_INDEX(ripeness, ',', -1) AS UNSIGNED))                          AS g4
--    FROM capture
--    WHERE region_id = ? AND species = ?
--      AND captured_at >= ? AND captured_at < ?
--    GROUP BY region_id, DATE(captured_at);
--
--  ⚠️ 上面的 SQL 只适合"临时看一眼"。真正的统计接口请走 Java：
--     用 RipenessCodec 解码后累加，比在 SQL 里拆字符串可靠。
--     一页 20 条在内存里算毫无压力；真到几十万行再考虑加汇总表。
--
--  不建汇总表的三个理由：
--    1. 数据量小 —— 一天几十条，算一下快得没感觉
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
--
-- INSERT INTO capture (region_id, species, captured_at, image_path, ripeness)
--   VALUES (1, 'persimmon', NOW(), NULL, '34,22,41,18'),
--          (1, 'apple',     NOW(), NULL, '5,3,12');
--
-- SELECT r.name, c.species, c.ripeness,
--        (CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(c.ripeness, ',', 1), ',', -1) AS UNSIGNED)
--       + CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(c.ripeness, ',', 2), ',', -1) AS UNSIGNED)
--       + CAST(SUBSTRING_INDEX(SUBSTRING_INDEX(c.ripeness, ',', 3), ',', -1) AS UNSIGNED)
--       + CAST(SUBSTRING_INDEX(c.ripeness, ',', -1) AS UNSIGNED)) AS total
--   FROM capture c JOIN region r ON r.id = c.region_id;


-- ============================================================================
--  从旧结构升级（如果你的库还是 count_unripe / count_turning / ... 那四列）
-- ============================================================================
--  ⚠️ 执行前先备份：mysqldump -uroot -p persimmon > persimmon_backup.sql
--
-- ALTER TABLE capture
--   ADD COLUMN species  VARCHAR(16) NOT NULL DEFAULT 'persimmon'
--       COMMENT '品种：persimmon / apple' AFTER region_id,
--   ADD COLUMN ripeness VARCHAR(32) NOT NULL DEFAULT '0,0,0,0'
--       COMMENT '各级果实数量，逗号分隔' AFTER image_path;
--
-- UPDATE capture
--    SET ripeness = CONCAT_WS(',', count_unripe, count_turning, count_coloring, count_full);
--
-- ALTER TABLE capture
--   DROP COLUMN count_unripe,  DROP COLUMN count_turning,
--   DROP COLUMN count_coloring, DROP COLUMN count_full,
--   DROP COLUMN detect_ms,     DROP COLUMN classify_ms,
--   ADD KEY idx_species_time (species, captured_at);
--
-- 旧数据全是柿子（苹果是后接的），所以 species 用默认值 'persimmon' 是对的。
-- ⚠️ 但旧数据里苹果那几行也被标成了 persimmon、且 3_mature 当年并进了第 4 位，
--    严格说无法还原。数据量小、且都是测试数据，忽略即可。
-- ============================================================================
