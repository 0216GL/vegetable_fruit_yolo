package org.ymg.persimmon.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.ymg.persimmon.common.R;
import org.ymg.persimmon.entity.Region;
import org.ymg.persimmon.service.RegionService;

import java.util.List;

/**
 * 区域接口。
 *
 * <p><b>Controller 层只做三件事：</b>接参数、调 Service、把结果包成 {@link R}。
 * <b>不写业务逻辑</b> —— 如果一个 if 判断是在讲业务规则，它应该在 Service 里。
 *
 * <p>路径前有没有 {@code /api}：
 * 这里写 {@code /api/region}，因为前端 axios 的 baseURL 虽然是 {@code /api}，
 * 但 Vite 代理转发的是带 {@code /api} 的完整路径，所以 Controller 要含 {@code /api}。
 * （别只写 {@code /region}，那样会对不上。）
 */
@RestController
@RequestMapping("/api/region")
public class RegionController {

    private final RegionService regionService;

    public RegionController(RegionService regionService) {
        this.regionService = regionService;
    }

    /**
     * 区域列表 —— 上传页的下拉框数据源。
     *
     * <p>{@code GET /api/region/list}
     * <p>返回 {@code R<List<Region>>}，前端拿到的是剥过壳的数组。
     */
    @GetMapping("/list")
    public R<List<Region>> list() {
        return R.ok(regionService.listAll());
    }
}
