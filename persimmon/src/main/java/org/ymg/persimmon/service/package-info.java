/**
 * 业务层（Service）—— 系统的核心，业务规则都在这。
 *
 * <p>你这段要写的核心逻辑在这：
 * <pre>
 *   收到上传的图片
 *     → 调 AiClient 拿识别结果
 *     → 把结果转成 Capture 对象（AI 的 Map → 表的四个列）
 *     → 存进数据库
 *     → 返回给 Controller
 * </pre>
 *
 * <p><b>四个成熟度 key 一字不能错</b>（和 Python 端 inference.py 的
 * RIPENESS_CLASSES 必须完全一致）：
 * <pre>
 *   1_unripe   2_turning   3_coloring   4_full
 * </pre>
 * 取值用 {@code AiPredictResponse.countOf("1_unripe")}，
 * 它已经帮你兜底了 null 和 0，不用自己判空。
 *
 * <p><b>这一层该做什么、不该做什么：</b>
 * <ul>
 *   <li>该做：校验参数、编排流程、决定什么时候抛 {@code BizException}、记日志</li>
 *   <li>不该做：HTTP 细节（那是 AiClient 的事）、响应格式化（那是 Controller 的事）、
 *       拼 SQL（那是 Mapper 的事）</li>
 * </ul>
 *
 * <p>类上加 {@code @Service} 注解，Spring 才会把它注册成 Bean。
 */
package org.ymg.persimmon.service;
