package org.ymg.persimmon.storage;

import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;

/**
 * 本机磁盘实现 —— {@code storage.mode=local} 时生效。
 *
 * <p><b>它是干什么用的：</b>答辩/演示现场网络不通、或者 OSS 还没配好时，
 * 把 {@code storage.mode} 改成 {@code local} 就能继续存图，代码其它地方一行不用改。
 * 这就是抽 {@link ImageStorage} 接口最直接的收益。
 *
 * <p>存盘位置见 {@code storage.local.dir}，对外通过 WebConfig 里的
 * {@code /files/**} 静态映射访问，例如
 * {@code http://127.0.0.1:8080/files/2026/10/24/xxx.jpg}。
 */
@Slf4j
@Component
@ConditionalOnProperty(name = "storage.mode", havingValue = "local")
public class LocalImageStorage implements ImageStorage {

    private final StorageProperties props;

    public LocalImageStorage(StorageProperties props) {
        this.props = props;
        log.info("图片存储：本机磁盘 {}（对外前缀 {}）",
                props.getLocal().getDir(), props.getLocal().getUrlPrefix());
    }

    @Override
    public String store(byte[] bytes, String originalFilename) {
        String key = ImageStorage.buildKey("", originalFilename);
        Path root = Paths.get(props.getLocal().getDir()).toAbsolutePath().normalize();
        Path target = root.resolve(key).normalize();

        // 防目录穿越：key 是我们自己生成的，理论上不会出问题，但检查一次不花钱
        if (!target.startsWith(root)) {
            throw new IllegalStateException("非法存储路径：" + key);
        }
        try {
            Files.createDirectories(target.getParent());
            Files.write(target, bytes);
        } catch (IOException e) {
            throw new IllegalStateException("写图片失败：" + e.getMessage(), e);
        }
        log.info("图片已存本机：{}（{} KB）", target, bytes.length / 1024);
        return key;
    }

    @Override
    public String urlOf(String key) {
        if (key == null || key.isBlank()) {
            return null;
        }
        String prefix = props.getLocal().getUrlPrefix();
        if (prefix == null || prefix.isBlank()) {
            prefix = "/files/";
        }
        return (prefix.endsWith("/") ? prefix : prefix + "/") + key;
    }

    @Override
    public String mode() {
        return "local";
    }
}
