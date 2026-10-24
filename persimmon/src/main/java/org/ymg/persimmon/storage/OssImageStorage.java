package org.ymg.persimmon.storage;

import com.aliyun.oss.OSS;
import com.aliyun.oss.OSSClientBuilder;
import com.aliyun.oss.model.ObjectMetadata;
import jakarta.annotation.PreDestroy;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

import java.io.ByteArrayInputStream;

/**
 * 阿里云 OSS 实现 —— {@code storage.mode=oss} 时生效（默认）。
 *
 * <p><b>⚠️ 这里最要紧的一条：AK 绝对不能进公开仓库。</b>
 * 配置用环境变量占位（{@code ${OSS_AK:}}），泄露的后果是别人拿你的账号上传/刷流量，
 * 账单是你的。见 {@code application.yaml} 里的注释。
 *
 * <p><b>★ 故意做成"配置不全也不让应用起不来"：</b>
 * 构造函数只记一个 {@code ready} 标志 + 打一条醒目的警告。
 * 真正上传时才抛异常，而 {@code CaptureService} 会接住它——
 * 结果就是：<b>图片没存上，但识别结果和数据库记录照常保存</b>。
 * 演示现场网络抽风，不该让整个系统瘫痪。
 *
 * <p><b>为什么用官方 SDK 而不是手写签名：</b>OSS 的签名（HMAC-SHA1 + CanonicalizedResource）
 * 手写容易出错，而且以后上 STS/S3 兼容存储、分片上传还要重写。
 * SDK 只多一个 jar，省下的坑值这个体积。
 */
@Slf4j
@Component
@ConditionalOnProperty(name = "storage.mode", havingValue = "oss", matchIfMissing = true)
public class OssImageStorage implements ImageStorage {

    private final StorageProperties props;
    private final OSS client;
    private final boolean ready;

    public OssImageStorage(StorageProperties props) {
        this.props = props;
        StorageProperties.Oss cfg = props.getOss();

        if (!cfg.complete()) {
            this.client = null;
            this.ready = false;
            log.warn("""
                    
                    ================================================================
                     OSS 配置不完整，图片将不会被保存（识别与数据库记录不受影响）。
                     请在 application.yaml 的 storage.oss 下补齐：
                       endpoint / access-key-id / access-key-secret / bucket
                     或者把 storage.mode 改成 local，先存本机磁盘。
                    ================================================================""");
            return;
        }

        this.client = new OSSClientBuilder()
                .build(cfg.getEndpoint(), cfg.getAccessKeyId(), cfg.getAccessKeySecret());
        this.ready = true;
        log.info("OSS 图片存储已就绪：bucket={} endpoint={} 前缀={}",
                cfg.getBucket(), cfg.getEndpoint(), cfg.getDir());
    }

    @Override
    public String store(byte[] bytes, String originalFilename) {
        if (!ready) {
            throw new IllegalStateException("OSS 未配置完整（见启动日志的警告）");
        }
        StorageProperties.Oss cfg = props.getOss();
        String key = ImageStorage.buildKey(cfg.getDir(), originalFilename);

        ObjectMetadata meta = new ObjectMetadata();
        meta.setContentLength(bytes.length);
        meta.setContentType(contentTypeOf(key));

        // putObject 是同步阻塞的（网络 IO），大图会有几十到几百毫秒
        client.putObject(cfg.getBucket(), key, new ByteArrayInputStream(bytes), meta);
        log.info("图片已上传 OSS：{}（{} KB）", key, bytes.length / 1024);
        return key;
    }

    @Override
    public String urlOf(String key) {
        if (key == null || key.isBlank()) {
            return null;
        }
        StorageProperties.Oss cfg = props.getOss();
        if (cfg.getUrlPrefix() != null && !cfg.getUrlPrefix().isBlank()) {
            String prefix = cfg.getUrlPrefix();
            return (prefix.endsWith("/") ? prefix : prefix + "/") + key;
        }
        // 默认域名规则：https://<bucket>.<endpoint>/<key>
        return "https://" + cfg.getBucket() + "." + cfg.getEndpoint() + "/" + key;
    }

    @Override
    public String mode() {
        return "oss";
    }

    /** 给对象带上正确的 Content-Type，浏览器才会直接当图片显示而不是下载。 */
    private static String contentTypeOf(String key) {
        String k = key.toLowerCase();
        if (k.endsWith(".webp")) {
            return "image/webp";
        }
        if (k.endsWith(".png")) {
            return "image/png";
        }
        return "image/jpeg";
    }

    @PreDestroy
    public void close() {
        if (client != null) {
            client.shutdown();
        }
    }
}
