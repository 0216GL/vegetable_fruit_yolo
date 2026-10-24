package org.ymg.persimmon.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;
import org.ymg.persimmon.ai.AiClient;
import org.ymg.persimmon.common.R;

import java.util.LinkedHashMap;
import java.util.Map;

/**
 * 健康检查。
 *
 * <p>{@code GET /api/health} —— 一次告诉你"Java 活着吗、Python 活着吗"。
 * 排障时第一个该打的接口：如果 {@code aiService} 是 {@code down}，
 * 那所有识别都会失败，不用再往下查了。
 *
 * <p>注意：这里是<b>报告</b> AI 服务的状态，而不是<b>因为</b>它挂了就报错。
 * 所以 AI 服务连不上时，这个接口本身仍然返回 {@code code:0}，
 * 只是 {@code data.aiService} 的值变成 {@code "down"}。
 * "健康检查这个操作成功了，结论是不健康"——这两件事要分开。
 */
@RestController
public class HealthController {

    private final AiClient aiClient;

    public HealthController(AiClient aiClient) {
        this.aiClient = aiClient;
    }

    @GetMapping("/api/health")
    public R<Map<String, Object>> health() {
        Map<String, Object> data = new LinkedHashMap<>();
        data.put("java", "ok");
        data.put("aiService", aiClient.isHealthy() ? "ok" : "down");
        return R.ok(data);
    }
}
