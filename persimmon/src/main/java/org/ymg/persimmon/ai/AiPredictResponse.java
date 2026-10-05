package org.ymg.persimmon.ai;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;

import java.util.List;
import java.util.Map;

/**
 * AI 服务的返回结构 —— 对应 Python 端 {@code server/schemas.py} 里的
 * {@code PredictResponse}。
 *
 * <p><b>⚠️ 这个类不是数据库实体。别和 {@code Capture} 合并。</b>
 *
 * <p>新手最容易犯的错：觉得"字段差不多"就把接口对象和数据库实体合成一个类。
 * 一旦合并，表加个字段、或者接口改个结构，两边就互相牵扯，改一个坏一个。
 * <b>数据库的形状和接口的形状，本来就该不一样：</b>
 *
 * <pre>
 * 表 capture 里有的：   id、create_time        ← AI 不返回
 * AI 返回但表里不存的：  detections[]（每颗果的框）← 我们决定不存
 * 两边名字不同的：       counts{...} → 四个 count_xxx 列
 * </pre>
 *
 * 转换在 Service 里做，两个类各管各的。
 *
 * <p><b>@JsonProperty 是干什么的：</b>Python 返回的 JSON 是下划线命名
 * （{@code det_conf}），Java 习惯驼峰（{@code detConf}）。名字对不上就填不进值。
 * 这里每个字段都显式标了名字，包括那些本来就同名的 ——
 * 多写几个注解，换来的是不依赖编译器的"保留参数名"设置。
 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record AiPredictResponse(

        @JsonProperty("ok")
        boolean ok,

        @JsonProperty("image")
        Image image,

        @JsonProperty("detections")
        List<Detection> detections,

        @JsonProperty("counts")
        Map<String, Integer> counts,

        @JsonProperty("timing")
        Timing timing,

        @JsonProperty("error")
        String error
) {

    /** 图片尺寸 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Image(
            @JsonProperty("width") int width,
            @JsonProperty("height") int height
    ) {
    }

    /** 一个果实 = 一个检测框 + 一个成熟度判定。我们不存这个，但接口会返回 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Detection(
            @JsonProperty("box") List<Integer> box,
            @JsonProperty("det_conf") double detConf,
            @JsonProperty("ripeness") String ripeness,
            @JsonProperty("ripeness_label") String ripenessLabel,
            @JsonProperty("ripeness_conf") double ripenessConf
    ) {
    }

    /** 两层各自的耗时（毫秒）—— 这两个要落库 */
    @JsonIgnoreProperties(ignoreUnknown = true)
    public record Timing(
            @JsonProperty("detect_ms") double detectMs,
            @JsonProperty("classify_ms") double classifyMs
    ) {
    }

    /**
     * 按成熟度 key 取数量。
     *
     * <p><b>为什么要有这个方法：</b>接口返回的 counts 是个 Map，直接
     * {@code counts.get("1_unripe")} 会拿到 {@code Integer}，
     * 而 counts 可能为 null，取出来再拆箱就 NPE。
     * 这里统一兜底成 0，Service 里就不用到处写判空了。
     *
     * <p>key 必须和 Python 端 {@code inference.py} 的 RIPENESS_CLASSES 一致。
     */
    public int countOf(String ripenessKey) {
        if (counts == null) {
            return 0;
        }
        Integer v = counts.get(ripenessKey);
        return v == null ? 0 : v;
    }

    /** 检出果实总数 */
    public int fruitCount() {
        return detections == null ? 0 : detections.size();
    }
}
