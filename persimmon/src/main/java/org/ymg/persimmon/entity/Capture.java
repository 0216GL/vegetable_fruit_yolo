package org.ymg.persimmon.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * 采集记录 —— 对应数据库的 {@code capture} 表。
 *
 * <p><b>一行 = 一次采集</b>（一张图 + 一个区域 + 一个时刻）。
 *
 * <p><b>★ 表只有 6 列，每一列都是"必须存"的</b>：
 * <pre>
 *   id           自增主键
 *   region_id    哪个地块           （外键 → region.id）
 *   species      什么品种           persimmon / apple —— 它决定 ripeness 怎么读
 *   captured_at  什么时候拍的
 *   image_path   图在哪             （暂时存 null，图片落盘还没做）
 *   ripeness     各级多少颗         "0,2,4,17"，顺序由 species 决定
 * </pre>
 *
 * <p><b>★ 为什么不给每一级建一列（count_unripe / count_turning / …）：</b>
 * 那样等级数量就被写死在表结构里了——柿子 4 级、苹果 3 级、以后想加第 5 级，
 * 每次都要改表 + 改实体 + 改 SQL。现在等级定义只活在
 * {@link org.ymg.persimmon.common.RipenessCodec} 里，改它一处就够。
 *
 * <p><b>★ 为什么没有 total / readyRate / 各种耗时：</b>都能算出来。
 * total 是 ripeness 各位相加，readyRate 是 {@code RipenessCodec.readyRate}；
 * 耗时是性能指标，日志里有，不该进业务表。
 * <b>能算出来的不存</b>——存了就得负责让它永远和源头一致，那是自找麻烦。
 *
 * <p>注意：这个类<b>只管数据库的形状</b>，
 * 和接口返回的 {@code AiPredictResponse} 不是一回事，别合并（见那个类的注释）。
 */
@Data
public class Capture {

    /** 主键 */
    private Long id;

    /** 所属区域 id —— 外键指向 region.id */
    private Long regionId;

    /**
     * 果品品种：{@code persimmon} 或 {@code apple}。
     *
     * <p><b>存英文键而不是中文名，也不是 0/1 数字</b>，理由：
     * <ul>
     *   <li>和 Python 端 {@code config.list_species()}、接口参数 {@code species} 字面一致，
     *       从接口到数据库不用做任何翻译（少一层映射就少一处会写错的地方）</li>
     *   <li>中文名以后可能改（"柿子" → "太行柿"），键不会改</li>
     *   <li>0/1 这种数字必须靠人记住谁是谁，查库时看不懂，加第三个品种时还会乱</li>
     * </ul>
     */
    private String species;

    /** 采集时刻（设备拍这张图的时间） */
    private LocalDateTime capturedAt;

    /**
     * 原图相对路径。
     * <p><b>当前阶段存 null</b> —— 图片落盘还没做（见 CaptureService 的说明）。
     * 列本身允许 null，所以不影响。
     */
    private String imagePath;

    /**
     * 各成熟度等级的果实数量，逗号分隔，顺序由 {@link #species} 决定。
     *
     * <pre>
     *   persimmon → "0,2,4,17"  未熟0 / 转色期2 / 着色期4 / 完熟17
     *   apple     → "1,3,8"     未熟1 / 转色期3 / 成熟8
     * </pre>
     *
     * <p>读写一律走 {@link org.ymg.persimmon.common.RipenessCodec}，
     * 别在别的地方自己 split——那是把"品种→等级顺序"的表复制第二份，早晚不一致。
     */
    private String ripeness;
}
