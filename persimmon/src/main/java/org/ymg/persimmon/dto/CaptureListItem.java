package org.ymg.persimmon.dto;

import com.fasterxml.jackson.annotation.JsonFormat;
import lombok.Data;

import java.time.LocalDateTime;

/**
 * 历史列表的"一行" —— 这是<b>返回给前端的形状</b>，不是数据库表的形状。
 *
 * <p><b>为什么要单独搞一个类，不直接用 {@link org.ymg.persimmon.entity.Capture}：</b>
 * 因为前端要的字段和表里对不上。看这个对比：
 *
 * <pre>
 *   前端要的        表里有没有        从哪来
 *   -------------  --------------  ---------------------------------------
 *   id             有              capture.id
 *   regionName     ★ 没有           JOIN region 表取 name
 *   species        有              capture.species
 *   capturedAt     有              capture.captured_at
 *   ripeness       有              capture.ripeness（原始串，留给想自己算的前端）
 *   gradeText      ★ 没有           RipenessCodec.describe() 编码成中文
 *   total          ★ 没有           ripeness 各位相加
 *   readyRate      ★ 没有           可采收颗数 / total × 100
 * </pre>
 *
 * <p>硬拿 Capture 去接这个查询，regionName / total / readyRate 三个字段没地方放，
 * 查出来就是 null。所以专门定义一个"列表行"来装。
 *
 * <p><b>这种"专为某个接口定制的对象"在企业里叫 VO（View Object，视图对象）。</b>
 * 它和 Entity（表实体）、DTO（层间传输对象）是三个不同的概念，
 * 分清楚是为了：表改了不会自动影响接口，接口改了也不会自动影响表。
 *
 * <p><b>{@code @JsonFormat} 那行是干什么的：</b>
 * Java 的 {@code LocalDateTime} 默认序列化成 {@code "2026-10-03T15:22:01"}（中间带 T），
 * 而接口契约里定的是 {@code "2026-10-03 15:22:01"}（中间是空格）。
 * 不加这个注解，前端拿到的字符串会多一个 T，和契约对不上。
 */
@Data
public class CaptureListItem {

    /** capture.id */
    private Long id;

    /** 区域名 —— 从 region 表 JOIN 来的 */
    private String regionName;

    /** 品种：persimmon / apple —— 前端要按品种显示等级名时用得上 */
    private String species;

    /** 采集时刻 */
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private LocalDateTime capturedAt;

    /** 原始编码串，如 "0,2,4,17"（想自己算的前端可以拿它，一般不用管） */
    private String ripeness;

    /** 图片 key（存库的那一列；OSS 模式下是对象名，local 模式下是相对路径） */
    private String imagePath;

    /** 图片可访问 URL —— 由存储层现算（Service 填），null 表示这条没有图 */
    private String imageUrl;

    /** 中文摘要，如 "未熟 0 / 转色期 2 / 着色期 4 / 完熟 17"（Service 现算） */
    private String gradeText;

    /** 检出果实总数 = 各级数量相加（表里没这列，现算） */
    private Integer total;

    /** 可采收率，0~100 的整数 = 可采收颗数 / total × 100（表里没这列，现算） */
    private Integer readyRate;
}
