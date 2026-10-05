/**
 * 实体层 —— 每个类对应数据库里的一张表。
 *
 * <p>这里放三个类，字段必须和 {@code db/schema.sql} 里建出来的表一一对应：
 * <ul>
 *   <li>{@code Region} —— region 表</li>
 *   <li>{@code Capture} —— capture 表（最重要的一张）</li>
 *   <li>{@code Notification} —— notification 表</li>
 * </ul>
 *
 * <p><b>一条规则：字段名用驼峰，MyBatis 会自动对上数据库的下划线。</b>
 * <pre>
 *   数据库  count_unripe        Java  countUnripe
 *   数据库  captured_at         Java  capturedAt
 * </pre>
 * 靠的是 {@code application.yaml} 里那行
 * {@code mybatis.configuration.map-underscore-to-camel-case: true}。
 * <b>那行没了，所有字段都会变成 null，而且不报错。</b>
 *
 * <p><b>时间一律用 {@code java.time.LocalDateTime}</b>，不要用
 * {@code java.util.Date}（老的，面试会被问"为什么不用新 API"）。
 *
 * <p>用了 Lombok 的话，类上写 {@code @Data} 就够了，不用手写 getter/setter。
 */
package org.ymg.persimmon.entity;
