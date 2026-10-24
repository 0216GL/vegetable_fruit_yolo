package org.ymg.persimmon.entity;

import lombok.Data;

import java.time.LocalDateTime;

/**
 * 区域 —— 对应数据库的 {@code region} 表。
 *
 * <p><b>实体类 = 一张表在 Java 里的样子。</b>字段名和列名一一对应，
 * 只是列名是下划线（{@code create_time}）、字段是驼峰（{@code createTime}）。
 * 这个转换靠 {@code application.yaml} 里的
 * {@code map-underscore-to-camel-case: true} 自动完成，
 * <b>不加那行的话，查出来全是 null 而且不报错</b>。
 *
 * <p>字段类型怎么选：
 * <pre>
 *   BIGINT UNSIGNED  →  Long      （id 主键）
 *   VARCHAR          →  String
 *   DATETIME         →  LocalDateTime  （Java 8 之后用它，不要用老的 java.util.Date）
 * </pre>
 *
 * <p><b>为什么用 {@code @Data}：</b>它自动生成 getter/setter/toString/equals。
 * 10 个字段手写 getter/setter 又长又没信息量。
 * ⚠️ 前提是 IDEA 里装了 Lombok 插件并开启注解处理，否则 IDE 会标红
 * （但 {@code mvnw spring-boot:run} 用 Maven 编译不受影响）。
 */
@Data
public class Region {

    /** 主键 */
    private Long id;

    /** 区域名称，如：东坡地 */
    private String name;

    /** 备注 */
    private String remark;

    /** 创建时间 */
    private LocalDateTime createTime;
}
