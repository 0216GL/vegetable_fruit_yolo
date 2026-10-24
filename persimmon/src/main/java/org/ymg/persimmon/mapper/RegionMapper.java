package org.ymg.persimmon.mapper;

import org.apache.ibatis.annotations.Select;
import org.ymg.persimmon.entity.Region;

import java.util.List;

/**
 * 区域的数据访问接口。
 *
 * <p><b>这是接口，没有实现类。</b>MyBatis 启动时动态生成实现，
 * 靠的是启动类上的 {@code @MapperScan("org.ymg.persimmon.mapper")} ——
 * 所以这个包下的接口会被自动识别，不用写 {@code @Mapper}。
 *
 * <p>SQL 直接用 {@code @Select} 注解写在方法上（简单 SQL 用注解，复杂 SQL 才上 XML）。
 */
public interface RegionMapper {

    /**
     * 查出所有区域，按 id 排。
     * <p>给上传页的下拉框用。区域就那么几条，不分页。
     */
    @Select("SELECT id, name, remark, create_time FROM region ORDER BY id")
    List<Region> findAll();

    /**
     * 按 id 查一个区域。
     * <p><b>查不到返回 null，不抛异常</b> —— 判空和报错是 Service 的事。
     * 上传时用它来确认"这个区域真的存在"，防止写进脏数据。
     */
    @Select("SELECT id, name, remark, create_time FROM region WHERE id = #{id}")
    Region findById(Long id);
}
