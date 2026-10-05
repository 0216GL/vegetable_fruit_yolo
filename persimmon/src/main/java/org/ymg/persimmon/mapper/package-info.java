/**
 * 数据访问层（Mapper）—— 只管和数据库打交道，不写业务逻辑。
 *
 * <p><b>这里的都是接口，没有实现类。</b>
 * MyBatis 在启动时动态生成实现，所以你不用写 {@code RegionMapperImpl} 这种东西。
 * 靠的是启动类上的 {@code @MapperScan("org.ymg.persimmon.mapper")} ——
 * <b>所以放在这个包下的接口会被自动识别，不用每个都写 {@code @Mapper}。</b>
 *
 * <p><b>两种写 SQL 的方式：</b>
 * <pre>
 *   // 方式一：注解（简单 SQL 用这个）
 *   {@code @Select("SELECT * FROM region WHERE id = #{id}")}
 *   Region findById(Long id);
 *
 *   // 方式二：XML（复杂 SQL 用这个，比如那个 GROUP BY 汇总）
 *   // 接口里只写方法签名，SQL 写到 resources/mapper/XxxMapper.xml
 * </pre>
 *
 * <p><b>⚠️ 关于参数名：</b>方法只有一个参数时可以随便起名；
 * <b>多个参数时，必须用 {@code @Param("名字")} 显式标出来</b>，
 * 否则 SQL 里的 {@code #{名字}} 会找不到，报
 * "Parameter 'xxx' not found. Available parameters are [arg0, arg1, param1, param2]"。
 *
 * <p><b>返回值：</b>查询单个对象用实体类，查询列表用 {@code List<实体类>}，
 * 统计数量用 {@code int} 或 {@code long}。查不到时返回 {@code null}（单个）
 * 或空列表（多个），<b>不会抛异常</b> —— 所以判空要在 Service 里做。
 */
package org.ymg.persimmon.mapper;
