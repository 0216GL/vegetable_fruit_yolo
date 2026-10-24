package org.ymg.persimmon.mapper;

import org.apache.ibatis.annotations.Insert;
import org.apache.ibatis.annotations.Options;
import org.apache.ibatis.annotations.Param;
import org.apache.ibatis.annotations.Select;
import org.ymg.persimmon.dto.CaptureListItem;
import org.ymg.persimmon.entity.Capture;

import java.util.List;

/**
 * 采集记录的数据访问接口。
 *
 * <p>三件事：存一条、查一页、数总数。
 *
 * <p><b>★ 这一层只负责"搬数据"，不做计算。</b>
 * {@code total} 和 {@code readyRate} 依赖"哪个品种的哪几级算可采收"，
 * 那是业务规则，写在 SQL 里就等于把它复制一份到数据库侧——
 * 以后苹果改分级标准，你还得去改 SQL 字符串。所以这类计算统一放
 * {@link org.ymg.persimmon.service.CaptureService}，用
 * {@link org.ymg.persimmon.common.RipenessCodec} 算。
 */
public interface CaptureMapper {

    /**
     * 插入一条采集记录。
     *
     * <p><b>{@code @Options(useGeneratedKeys = true, keyProperty = "id")} 是干什么的：</b>
     * 插入时我们没给 id（数据库自增的）。这个配置让 MyBatis 在插入之后，
     * <b>把数据库生成的 id 回填到传入的 {@code capture.id} 上</b>。
     * 不加的话，插入后对象里 id 还是 null，想返回新记录 id 就拿不到。
     *
     * <p>{@code ripeness} 传进来的是已经编码好的字符串（{@code "0,2,4,17"}），
     * 这一层不需要知道里面是什么。
     */
    @Insert("""
            INSERT INTO capture
              (region_id, species, captured_at, image_path, ripeness)
            VALUES
              (#{regionId}, #{species}, #{capturedAt}, #{imagePath}, #{ripeness})
            """)
    @Options(useGeneratedKeys = true, keyProperty = "id")
    int insert(Capture capture);

    /**
     * 分页查历史列表，按采集时间倒序（新的在前）。
     *
     * <p><b>★ 这是你写的第一个 JOIN。</b>原因：前端要显示区域名，
     * 但 capture 表里只有 {@code region_id}，名字在 region 表 —— 所以要 JOIN 出来。
     *
     * <p><b>★ 查出来的 {@code species} / {@code ripeness} 是"原料"</b>，
     * total / readyRate / 中文摘要由 Service 拿到这一页之后现算。
     * 一页最多 20 条，在内存里算比在 SQL 里拆逗号字符串清楚得多。
     *
     * <p><b>为什么要 {@code @Param}：</b>方法有两个参数时，
     * 必须用 {@code @Param("名字")} 把名字和 SQL 里的 {@code #{名字}} 对上，
     * 否则会报 "Parameter 'offset' not found"。
     *
     * <p>返回的 {@link CaptureListItem} 是接口形状，字段靠
     * {@code map-underscore-to-camel-case} 自动映射
     * （{@code region_name → regionName}）。
     */
    @Select("""
            SELECT c.id,
                   r.name AS region_name,
                   c.species,
                   c.ripeness,
                   c.image_path,
                   c.captured_at
            FROM capture c
            JOIN region r ON r.id = c.region_id
            ORDER BY c.captured_at DESC, c.id DESC
            LIMIT #{offset}, #{size}
            """)
    List<CaptureListItem> findList(@Param("offset") int offset, @Param("size") int size);

    /**
     * 记录总数 —— 给分页用。
     * <p>返回 {@code long} 而不是 {@code int}：COUNT 在大表上可能超过 int 范围。
     */
    @Select("SELECT COUNT(*) FROM capture")
    long countAll();
}
