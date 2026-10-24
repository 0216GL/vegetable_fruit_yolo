package org.ymg.persimmon.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import org.ymg.persimmon.ai.AiPredictResponse;
import org.ymg.persimmon.common.R;
import org.ymg.persimmon.service.CaptureService;

import java.util.Map;

/**
 * 巡检接口 —— 前端所有页面主要就靠这两个。
 */
@RestController
@RequestMapping("/api/inspection")
public class CaptureController {

    private final CaptureService captureService;

    public CaptureController(CaptureService captureService) {
        this.captureService = captureService;
    }

    /**
     * 上传图片识别。
     *
     * <p>{@code POST /api/inspection/predict}，multipart/form-data。
     *
     * <p><b>★ 两个 {@code @RequestParam} 的名字必须和前端对得上：</b>
     * <ul>
     *   <li>{@code "file"} —— 前端 {@code form.append('file', file)}。
     *       <b>名字对不上会直接 400</b>："Required request part 'file' is not present"，
     *       这是上传接口最常见的坑。</li>
     *   <li>{@code "regionId"} —— 前端 {@code form.append('regionId', regionId)}。</li>
     * </ul>
     *
     * <p>注意这里<b>一个 try-catch 都没有</b> —— 校验失败、AI 挂了，
     * Service 抛的异常会被 GlobalExceptionHandler 统一接住转成 {@code R}。
     */
    @PostMapping("/predict")
    public R<AiPredictResponse> predict(
            @RequestParam("file") MultipartFile file,
            @RequestParam("regionId") Long regionId,
            @RequestParam(value = "species", defaultValue = "persimmon") String species) {
        return R.ok(captureService.predict(file, regionId, species));
    }

    /**
     * 历史列表。
     *
     * <p>{@code GET /api/inspection/list?page=1&size=20}
     *
     * <p>{@code defaultValue} 的好处：前端不传这两个参数也能跑，
     * 等价于 {@code page=1&size=20}。比一进来就校验参数少写不少代码。
     */
    @GetMapping("/list")
    public R<Map<String, Object>> list(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size) {
        return R.ok(captureService.list(page, size));
    }
}
