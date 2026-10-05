package org.ymg.persimmon;

import org.mybatis.spring.annotation.MapperScan;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

/**
 * 启动类。
 *
 * <p><b>{@code @MapperScan} 是干什么的、不加会怎样：</b>
 * MyBatis 的 Mapper 都是<b>接口</b>，没有实现类。是靠 Spring 在启动时
 * 动态生成代理对象注册成 Bean 的。这个扫描就是告诉它"去哪个包底下找"。
 *
 * <p>不加的话，一注入 Mapper 就报
 * {@code Field xxxMapper required a bean of type ... that could not be found} ——
 * 而且错误信息里不会提"你忘了加 @MapperScan"，很难往这个方向想。
 *
 * <p>另一种做法是在每个 Mapper 接口上单独写 {@code @Mapper}。
 * 两种都行，但{@code @MapperScan}写一次就够，新加 Mapper 不用记得加注解。
 */
@SpringBootApplication
@MapperScan("org.ymg.persimmon.mapper")
public class PersimmonApplication {

    public static void main(String[] args) {
        SpringApplication.run(PersimmonApplication.class, args);
    }

}
