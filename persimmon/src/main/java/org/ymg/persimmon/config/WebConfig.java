package org.ymg.persimmon.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;

/**
 * 跨域配置。
 *
 * <p><b>开发时其实用不上它 —— 但别删。</b>
 *
 * <p>前端的 {@code vite.config.js} 里配了代理，请求走的是
 * 浏览器 → 5173(Vite) → 8080，对浏览器来说**没跨域**，所以走不到这里。
 *
 * <p>那它给谁用？给**绕过浏览器的调用方**：
 * <ul>
 *   <li>Postman / curl 直接打 8080</li>
 *   <li>以后的小程序（小程序的域名白名单机制和浏览器不同）</li>
 *   <li>第三方的服务端调用</li>
 * </ul>
 * 这些场景没有"同源策略"这道墙，也就用不到 CORS。
 * 保留它是为了**前端万一不走代理、直连 8080 时能兜住**（比如部署到不同域名）。
 *
 * <p><b>上线前必须改：</b>{@code allowedOriginPatterns("*")} 表示任何网站都能调你的接口。
 * 开发方便，上线要换成具体域名。
 */
@Configuration
public class WebConfig implements WebMvcConfigurer {

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOriginPatterns("*")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true)
                .maxAge(3600);
    }
}
