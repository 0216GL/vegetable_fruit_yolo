package org.ymg.persimmon.storage;

import java.time.LocalDate;
import java.util.Locale;
import java.util.UUID;

/**
 * 图片存储的统一入口 —— <b>业务代码只认这个接口，不认"存哪儿"</b>。
 *
 * <p>两个实现：
 * <pre>
 *   OssImageStorage     → 上传到阿里云 OSS（当前默认，storage.mode=oss）
 *   LocalImageStorage   → 存本机磁盘（storage.mode=local，离线演示兜底）
 * </pre>
 *
 * <p><b>为什么要抽接口：</b>存哪儿是"部署方式"，不是业务逻辑。抽出来以后，
 * 换存储只是换一个实现类 + 改一行配置，{@code CaptureService} 一行都不用动。
 * 这也是面试常问的"依赖倒置"落到实处的样子。
 *
 * <p><b>约定：数据库 {@code capture.image_path} 里存的是 key（不是完整 URL）。</b>
 * 好处是以后换 bucket、换域名、加 CDN，历史数据不用改；
 * 需要 URL 的地方调 {@link #urlOf(String)} 现算。
 */
public interface ImageStorage {

    /**
     * 存一张图，返回要写进 {@code capture.image_path} 的 key。
     *
     * @param bytes            图片原始字节
     * @param originalFilename 原始文件名（只用来取扩展名，不参与命名）
     * @return 形如 {@code captures/2026/10/24/9f2c...e1.jpg}
     */
    String store(byte[] bytes, String originalFilename);

    /**
     * key → 前端能直接访问的 URL。key 为 null 返回 null。
     */
    String urlOf(String key);

    /** 当前实现的名字，打日志/健康检查用：{@code oss} 或 {@code local}。 */
    String mode();

    /**
     * 生成存储 key：{@code 前缀/年/月/日/随机串.扩展名}。
     *
     * <p><b>为什么用 UUID 而不是原文件名：</b>
     * <ul>
     *   <li>中文名、空格、emoji 在 URL 里都要转义，坑多</li>
     *   <li>同一天传两张都叫 {@code IMG_0001.jpg} 会互相覆盖</li>
     *   <li>原文件名可能带用户隐私信息</li>
     * </ul>
     * 按 年/月/日 分目录是为了：单目录文件数不会无限膨胀（OSS 和控制台都更好管理），
     * 也方便按时间清理。
     */
    static String buildKey(String prefix, String originalFilename) {
        String ext = "jpg";
        if (originalFilename != null) {
            int dot = originalFilename.lastIndexOf('.');
            if (dot >= 0 && dot < originalFilename.length() - 1) {
                String raw = originalFilename.substring(dot + 1).toLowerCase(Locale.ROOT);
                // 只留字母数字，防止奇怪扩展名拼进 key
                if (raw.matches("[a-z0-9]{1,5}")) {
                    ext = raw;
                }
            }
        }
        String dir = (prefix == null || prefix.isBlank()) ? "" : prefix;
        if (!dir.isEmpty() && !dir.endsWith("/")) {
            dir = dir + "/";
        }
        LocalDate d = LocalDate.now();
        String uuid = UUID.randomUUID().toString().replace("-", "");
        return String.format("%s%d/%02d/%02d/%s.%s",
                dir, d.getYear(), d.getMonthValue(), d.getDayOfMonth(), uuid, ext);
    }
}
