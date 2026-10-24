package org.ymg.persimmon.config;

import org.springframework.context.annotation.Configuration;
import org.springframework.http.CacheControl;
import org.springframework.web.servlet.config.annotation.CorsRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import org.ymg.persimmon.storage.StorageProperties;

import java.nio.file.Paths;
import java.util.concurrent.TimeUnit;

/**
 * 跨域配置 + 本机图片的静态映射。
 *
 * <p><b>跨域：开发时其实用不上它 —— 但别删。</b>
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
 * <p>⚠️ 另外：前端静态站跑在 8089，调 8080 的接口是真跨域，靠的就是下面这段。
 *
 * <p><b>上线前必须改：</b>{@code allowedOriginPatterns("*")} 表示任何网站都能调你的接口。
 * 开发方便，上线要换成具体域名。
 */
@Configuration
public class WebConfig implements WebMvcConfigurer {

    private final StorageProperties storageProperties;

    public WebConfig(StorageProperties storageProperties) {
        this.storageProperties = storageProperties;
    }

    @Override
    public void addCorsMappings(CorsRegistry registry) {
        registry.addMapping("/api/**")
                .allowedOriginPatterns("*")
                .allowedMethods("GET", "POST", "PUT", "DELETE", "OPTIONS")
                .allowedHeaders("*")
                .allowCredentials(true)
                .maxAge(3600);
    }

    /**
     * 本机图片的静态映射：{@code /files/**} → {@code storage.local.dir}。
     *
     * <p>只有 {@code storage.mode=local} 才真的有文件，但这段映射常驻也不碍事
     * （目录不存在就是 404）。用 OSS 时前端直接拿 OSS 的 URL，根本不走这里。
     *
     * <p><b>为什么要把路径转成 {@code file:} 形式的 URI：</b>
     * Windows 路径里的反斜杠和盘符冒号，Spring 不认，
     * 必须写成 {@code file:///D:/.../}，用 {@code Paths.get(dir).toUri()} 最稳。
     */
    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry) {
        String dir = storageProperties.getLocal().getDir();
        if (dir == null || dir.isBlank()) {
            return;
        }
        registry.addResourceHandler("/files/**")
                .addResourceLocations(Paths.get(dir).toAbsolutePath().normalize().toUri().toString())
                // 图片内容不会变（文件名带 uuid），可以放心让浏览器缓存一天
                .setCacheControl(CacheControl.maxAge(1, TimeUnit.DAYS));
    }
}
