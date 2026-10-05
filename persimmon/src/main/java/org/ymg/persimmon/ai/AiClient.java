package org.ymg.persimmon.ai;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;
import org.ymg.persimmon.common.BizException;
import org.ymg.persimmon.common.ErrorCode;

/**
 * AI 服务客户端 —— Java 侧唯一一个"知道 Python 服务长什么样"的地方。
 *
 * <p><b>★ 这个类你要读一遍。</b>它是整个后端最不好想的部分 ——
 * 不是因为难，而是因为<b>实际会遇到的坑都在这里</b>，
 * 你自己从零写大概率会踩，而且踩了不容易查。
 *
 * <p><b>为什么要单独抽一个类：</b>把"怎么调 Python"关在一个盒子里。
 * Service 只调 {@code aiClient.predict(bytes, name)}，
 * 不关心 HTTP、地址、字段映射。以后 Python 换实现或换机器，只改这个类。
 *
 * <hr>
 *
 * <p><b>它处理了三种返回情况（这三种实际都会遇到）：</b>
 * <ol>
 *   <li><b>正常契约结构</b>：Python 的 {@code inference.py} 无论成功失败，
 *       都返回 {@code {ok, image, detections, counts, timing, error}}，
 *       {@code ok=false} 时 error 里有原因。</li>
 *   <li><b>FastAPI 的参数校验错误</b>：比如文件格式不对，FastAPI 自己会返回
 *       {@code {"detail": "..."}}。<b>结构和第 1 种完全不同</b>，
 *       直接按 {@code AiPredictResponse} 解析会失败。</li>
 *   <li><b>彻底连不上</b>：Python 服务没启动。</li>
 * </ol>
 * 所以不能简单写 {@code postForObject(..., AiPredictResponse.class)}，
 * 必须先把响应当字符串拿回来，看清楚是什么再解析。
 */
@Component
public class AiClient {

    private static final Logger log = LoggerFactory.getLogger(AiClient.class);

    private final RestTemplate restTemplate;
    private final ObjectMapper objectMapper;
    private final String predictUrl;
    private final String healthUrl;

    public AiClient(RestTemplate restTemplate,
                    ObjectMapper objectMapper,
                    @Value("${ai.service.base-url}") String baseUrl,
                    @Value("${ai.service.predict-path}") String predictPath,
                    @Value("${ai.service.health-path}") String healthPath) {
        this.restTemplate = restTemplate;
        this.objectMapper = objectMapper;
        this.predictUrl = baseUrl + predictPath;
        this.healthUrl = baseUrl + healthPath;
        log.info("AI 服务地址  predict={}  health={}", predictUrl, healthUrl);
    }

    /**
     * 把一张图交给 AI 服务做「检测 + 成熟度分类」。
     *
     * @param bytes    图片原始字节
     * @param filename 原始文件名。<b>不能省</b> —— Python 端靠它的后缀判断格式，
     *                 传 null 会被当成没有后缀。
     * @return 识别结果（{@code detections} 可能为空数组，表示图里没有柿子，
     *         这<b>不是</b>错误）
     * @throws BizException AI 服务连不上，或推理失败
     */
    public AiPredictResponse predict(byte[] bytes, String filename) {
        long t0 = System.currentTimeMillis();

        // ---- 构造 multipart/form-data 请求体 ----
        // 对应 Postman 里的 "form-data"，字段名必须是 file，
        // 因为 Python 端声明的是 file: UploadFile = File(...)
        MultiValueMap<String, Object> body = new LinkedMultiValueMap<>();
        body.add("file", new NamedByteArrayResource(bytes, filename));

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.MULTIPART_FORM_DATA);

        HttpEntity<MultiValueMap<String, Object>> request = new HttpEntity<>(body, headers);

        ResponseEntity<String> response;
        try {
            // responseType 用 String.class 而不是 AiPredictResponse.class，
            // 原因见类注释里的"三种返回情况"
            response = restTemplate.postForEntity(predictUrl, request, String.class);

        } catch (HttpStatusCodeException e) {
            // 4xx / 5xx：RestTemplate 把响应体放在异常里了，取出来解析。
            // 这正是我们要拿到错误详情的原因 —— 只看 "500 Internal Server Error"
            // 是查不出问题的。
            log.debug("AI 服务返回 HTTP {}，响应体：{}",
                    e.getStatusCode().value(), truncate(e.getResponseBodyAsString()));
            return parse(e.getResponseBodyAsString(), e.getStatusCode().value());

        } catch (RestClientException e) {
            // 连 TCP 都没建立起来，说明服务根本没起
            log.error("无法连接 AI 服务 {}：{}", predictUrl, e.getMessage());
            throw new BizException(ErrorCode.AI_SERVICE_UNAVAILABLE,
                    "AI 服务连不上。请先启动 Python 服务（双击项目根目录的 run_server.bat）");
        }

        log.debug("AI 调用完成，HTTP {}，耗时 {} ms",
                response.getStatusCode().value(), System.currentTimeMillis() - t0);

        return parse(response.getBody(), response.getStatusCode().value());
    }

    /**
     * AI 服务是否健康。
     *
     * <p>注意：这里<b>吞掉了所有异常</b>并返回 false。健康检查的语义就是
     * "能用吗"，"连不上"本身就是它要回答的答案之一，不该往外抛。
     */
    public boolean isHealthy() {
        try {
            ResponseEntity<String> resp = restTemplate.getForEntity(healthUrl, String.class);
            if (!resp.getStatusCode().is2xxSuccessful() || resp.getBody() == null) {
                return false;
            }
            JsonNode node = objectMapper.readTree(resp.getBody());
            return "ok".equals(node.path("status").asText());
        } catch (Exception e) {
            log.debug("AI 健康检查失败：{}", e.getMessage());
            return false;
        }
    }

    // ==========================================================================
    // 内部：解析响应
    // ==========================================================================
    private AiPredictResponse parse(String rawBody, int statusCode) {
        if (rawBody == null || rawBody.isBlank()) {
            throw new BizException(ErrorCode.AI_INFERENCE_FAILED,
                    "AI 服务返回了空响应（HTTP " + statusCode + "）");
        }

        JsonNode node;
        try {
            node = objectMapper.readTree(rawBody);
        } catch (Exception e) {
            throw new BizException(ErrorCode.AI_INFERENCE_FAILED,
                    "AI 服务返回的不是合法 JSON（HTTP " + statusCode + "）：" + truncate(rawBody));
        }

        // 情况 1：标准契约结构（含成功与"模型内部失败"两种）
        if (node.has("ok")) {
            AiPredictResponse parsed = objectMapper.convertValue(node, AiPredictResponse.class);
            if (!parsed.ok()) {
                throw new BizException(ErrorCode.AI_INFERENCE_FAILED,
                        "AI 推理失败：" + parsed.error());
            }
            return parsed;
        }

        // 情况 2：FastAPI 自己抛的 HTTPException，形如 {"detail": "..."}
        if (node.has("detail")) {
            throw new BizException(ErrorCode.AI_INFERENCE_FAILED,
                    "AI 服务拒绝了这次请求：" + node.get("detail").asText());
        }

        // 情况 3：认不出来。截断返回，方便排查又不泄露太多
        throw new BizException(ErrorCode.AI_INFERENCE_FAILED,
                "AI 服务返回了无法识别的结构（HTTP " + statusCode + "）：" + truncate(rawBody));
    }

    private static String truncate(String s) {
        if (s == null) {
            return "";
        }
        return s.length() <= 200 ? s : s.substring(0, 200) + "...";
    }

    /**
     * 带文件名的字节资源。
     *
     * <p><b>为什么要单独写这个内部类：</b>Spring 上传 multipart 时会调用资源的
     * {@code getFilename()}。直接塞 {@code ByteArrayResource} 的话文件名是 null，
     * 请求里<b>就不会有 filename 字段</b>，Python 端拿到的文件名是空，无法做后缀校验。
     */
    static class NamedByteArrayResource extends ByteArrayResource {

        private final String filename;

        NamedByteArrayResource(byte[] bytes, String filename) {
            super(bytes);
            this.filename = (filename == null || filename.isBlank()) ? "upload.jpg" : filename;
        }

        @Override
        public String getFilename() {
            return filename;
        }
    }
}
