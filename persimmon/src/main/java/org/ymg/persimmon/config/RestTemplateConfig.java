package org.ymg.persimmon.config;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestTemplate;

import java.time.Duration;

/**
 * 调用 Python AI 服务用的 HTTP 客户端。
 *
 * <p><b>RestTemplate 是什么：</b>Spring 提供的"在 Java 里发 HTTP 请求"的工具，
 * 相当于 Java 版的 Postman。我们用它去调 Python 的 {@code POST /api/predict}。
 *
 * <p><b>为什么要自定义超时：</b>RestTemplate 默认<b>没有超时</b>，会一直等下去。
 * Python 服务一卡死，Java 的请求线程就被永久占住，请求一多线程池耗尽，
 * 整个后端跟着假死。<b>给所有外部调用设超时是硬性要求。</b>
 *
 * <hr>
 *
 * <p><b>⚠️ 这是我整份框架里最没把握的一处。</b>
 *
 * <p>你用的是 Spring Boot 4.0（对应 Spring Framework 7），
 * 而我熟悉的是 3.x / Framework 6。Boot 3.4 之后
 * {@code RestTemplateBuilder.setConnectTimeout(...)} 这类写法被标记为过时，
 * 官方建议改用 {@code ClientHttpRequestFactorySettings}。
 * 到了 7.0 那些老方法**是否还存在，我不能确定**。
 *
 * <p>所以我选了相对底层、变化较小的 {@link SimpleClientHttpRequestFactory}
 * 来设超时，绕开 {@code RestTemplateBuilder} 的 API 变动。
 *
 * <p><b>如果这段编译不过</b>，把报错整段贴出来 —— 大概率是某个方法签名改了，
 * 一眼就能看出来怎么改。别自己猜。
 */
@Configuration
public class RestTemplateConfig {

    @Value("${ai.service.connect-timeout-ms}")
    private long connectTimeoutMs;

    @Value("${ai.service.read-timeout-ms}")
    private long readTimeoutMs;

    @Bean
    public RestTemplate restTemplate() {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();

        // 连接超时：TCP 握手多久算失败。本地服务 3 秒足够。
        factory.setConnectTimeout(Duration.ofMillis(connectTimeoutMs));

        // 读取超时：连上之后等响应体多久。给足 —— 模型冷启动要十几秒。
        factory.setReadTimeout(Duration.ofMillis(readTimeoutMs));

        return new RestTemplate(factory);
    }
}
