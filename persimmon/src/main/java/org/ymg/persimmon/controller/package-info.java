/**
 * 接口层（Controller）—— 只做三件事：接参数 → 调 Service → 包成 R 返回。
 *
 * <p><b>类上写 {@code @RestController} + {@code @RequestMapping("/api/xxx")}。</b>
 * {@code @RestController} = {@code @Controller} + {@code @ResponseBody}，
 * 表示方法返回值直接序列化成 JSON，而不是"跳转到某个页面"。
 *
 * <p><b>⚠️ 接口路径和返回结构不能随便定 —— 前端已经写好了。</b>
 * 见 {@code web/src/api/inspection.js}。改动契约 = 前端所有页面一起改。
 *
 * <p><b>Controller 里不要写 try-catch。</b>
 * 抛出的异常会被 {@code common/GlobalExceptionHandler} 统一接住并转成标准结构，
 * 这就是那个类存在的意义。
 *
 * <p><b>一旦发现自己在这里写了 if/for 之类的业务判断，说明放错位置了</b>，
 * 应该挪进 Service。这样以后换前端（网页换小程序）、加个定时任务入口，
 * 业务逻辑一份都不用重写。
 *
 * <p><b>🎯 包的位置很关键：</b>必须在这个包下才会被扫描到。
 * {@code @SpringBootApplication} 只扫描"启动类所在包及其子包"，
 * 放到 {@code org.ymg.persimmon} 之外的包里，接口会 404 且不报任何错。
 */
package org.ymg.persimmon.controller;
