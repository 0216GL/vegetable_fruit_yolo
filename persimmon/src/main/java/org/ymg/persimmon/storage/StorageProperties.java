package org.ymg.persimmon.storage;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * 图片存储配置 —— 对应 {@code application.yaml} 里的 {@code storage:} 段。
 *
 * <pre>
 * storage:
 *   mode: oss          # oss / local
 *   oss:
 *     endpoint: oss-cn-beijing.aliyuncs.com
 *     access-key-id: ...
 *     access-key-secret: ...
 *     bucket: ...
 *     dir: taihang/captures/
 *     url-prefix:      # 可选：绑了自定义域名/CDN 才填，填了就用它拼 URL
 *   local:
 *     dir: D:/vegetable_fruit_yolo/data/images
 *     url-prefix: /files/
 * </pre>
 *
 * <p><b>⚠️ AccessKey 不要写进 git。</b>要么用环境变量
 * （{@code ${OSS_AK:}} 这种写法，启动前 set 环境变量），
 * 要么填了之后确认 {@code application.yaml} 不进公开仓库。
 * AK 泄露 = 别人可以拿你的钱和流量。
 */
@Data
@Component
@ConfigurationProperties(prefix = "storage")
public class StorageProperties {

    /** oss = 阿里云对象存储；local = 本机磁盘 */
    private String mode = "oss";

    private Oss oss = new Oss();

    private Local local = new Local();

    @Data
    public static class Oss {
        /** 地域节点，如 oss-cn-beijing.aliyuncs.com（不要带 bucket 名） */
        private String endpoint = "";

        private String accessKeyId = "";

        private String accessKeySecret = "";

        /** Bucket 名 */
        private String bucket = "";

        /** 对象名前缀，建议 taihang/captures/ 这样带项目名，避免和别的项目混在一个 bucket */
        private String dir = "taihang/captures/";

        /** 自定义域名 / CDN 域名，留空则用 bucket 自带域名 */
        private String urlPrefix = "";

        /** 配置齐全了没 */
        public boolean complete() {
            return notBlank(endpoint) && notBlank(accessKeyId)
                    && notBlank(accessKeySecret) && notBlank(bucket);
        }

        private static boolean notBlank(String s) {
            return s != null && !s.isBlank();
        }
    }

    @Data
    public static class Local {
        /** 落盘目录 */
        private String dir = "data/images";

        /** 对外访问前缀，配合 WebConfig 里 /files/** 的静态映射 */
        private String urlPrefix = "/files/";
    }
}
