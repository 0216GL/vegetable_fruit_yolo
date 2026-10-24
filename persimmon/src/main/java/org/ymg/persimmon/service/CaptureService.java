package org.ymg.persimmon.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;
import org.ymg.persimmon.ai.AiClient;
import org.ymg.persimmon.ai.AiPredictResponse;
import org.ymg.persimmon.common.BizException;
import org.ymg.persimmon.common.ErrorCode;
import org.ymg.persimmon.common.RipenessCodec;
import org.ymg.persimmon.dto.CaptureListItem;
import org.ymg.persimmon.entity.Capture;
import org.ymg.persimmon.mapper.CaptureMapper;
import org.ymg.persimmon.storage.ImageStorage;

import java.io.IOException;
import java.time.LocalDateTime;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * 采集记录的业务逻辑 —— <b>整个后端最核心的一个类</b>。
 *
 * <p>它干两件事：
 * <ol>
 *   <li>{@link #predict} —— 收图 → 存图 → 调 AI → 把结果落库 → 把 AI 结果返回给前端</li>
 *   <li>{@link #list}    —— 分页查历史，顺手把 total / readyRate / 图片 URL 算出来</li>
 * </ol>
 */
@Slf4j
@Service
public class CaptureService {

    private final CaptureMapper captureMapper;
    private final RegionService regionService;
    private final AiClient aiClient;
    private final ImageStorage imageStorage;

    public CaptureService(CaptureMapper captureMapper,
                          RegionService regionService,
                          AiClient aiClient,
                          ImageStorage imageStorage) {
        this.captureMapper = captureMapper;
        this.regionService = regionService;
        this.aiClient = aiClient;
        this.imageStorage = imageStorage;
    }

    /**
     * 上传一张图：识别 + 落库。
     *
     * <p><b>★ 顺序很重要，想清楚每一步为什么在这个位置：</b>
     * <pre>
     *   1. 先校验区域        —— 最便宜，不合法就早点失败，别浪费一次模型推理
     *   2. 再校验文件        —— 同上
     *   3. 调 AI（最贵）     —— 前面都过了才做这件花钱的事
     *   4. 落库             —— 有结果才存
     * </pre>
     * 如果顺序反了（先调 AI 再校验区域），一个不存在的区域也会白跑一次推理。
     *
     * @return AI 的原始返回。前端要的框、成熟度、计数，全在它里面 ——
     *         我们<b>原样透传</b>，不重新组装（组装容易漏字段）。
     */
    public AiPredictResponse predict(MultipartFile file, Long regionId, String species) {

        // ---- 1. 区域必须真实存在 ----
        regionService.getById(regionId);

        // ---- 2. 文件校验 ----
        if (file == null || file.isEmpty()) {
            throw new BizException(ErrorCode.EMPTY_FILE, "请上传一张图片");
        }

        byte[] bytes;
        try {
            bytes = file.getBytes();
        } catch (IOException e) {
            throw new BizException(ErrorCode.INTERNAL_ERROR, "读取上传文件失败：" + e.getMessage());
        }

        // ---- 3. 调 AI（带上品种，Python 端据此选对应的检测 + 分类模型）----
        // 品种先归一化：不认识的（null / 空 / 拼错）一律当柿子，别把 500 甩给前端。
        // 真正严格的校验在 Python 端（它会返回 400），这里只做兜底。
        String sp = RipenessCodec.normalize(species);

        // 失败时 AiClient 会抛 BizException（连不上 / 推理失败），这里不用管
        AiPredictResponse result = aiClient.predict(bytes, file.getOriginalFilename(), sp);

        // ---- 4. 落库 ----
        Capture capture = new Capture();
        capture.setRegionId(regionId);
        capture.setCapturedAt(LocalDateTime.now());

        // 品种以 AI 实际用的那个为准（AI 会回显 species），回显缺失才用请求里的
        String usedSpecies = RipenessCodec.normalize(
                result.species() != null ? result.species() : sp);
        capture.setSpecies(usedSpecies);

        // ★ 先把原图存到对象存储（OSS）/ 本机磁盘，拿回 key 再落库。
        //   注意顺序：先存图后写库 —— 存图失败时就是"没有图但有记录"，
        //   反过来（先写库再存图）失败会留下一条 image_path 永远为空的记录，更难处理。
        capture.setImagePath(storeImageQuietly(bytes, file.getOriginalFilename()));

        // ★ 把 AI 返回的 counts 编码成一列字符串，顺序由品种决定：
        //     柿子 "0,2,4,17" → 未熟/转色期/着色期/完熟
        //     苹果 "1,3,8"    → 未熟/转色期/成熟
        //   编码规则只在 RipenessCodec 里有一份，这里不自己拼字符串。
        capture.setRipeness(RipenessCodec.encode(usedSpecies, result.counts()));

        captureMapper.insert(capture);

        // ---- 5. 把 AI 结果原样给前端 ----
        return result;
    }

    /**
     * 历史列表（分页）。
     *
     * <p><b>返回的是 Map，不是专门的类。</b>为什么这里可以偷这个懒：
     * 返回结构很简单（就 list 和 total 两个 key），
     * 而且它只在这一处出现，没有复用和类型校验的需求。
     * 用 {@code LinkedHashMap} 而不是 {@code HashMap}：保证 JSON 里
     * key 的顺序是 list 在前、total 在后，看着舒服（HashMap 顺序随机）。
     *
     * <p><b>★ 三个算出来的字段在这里补齐：</b>
     * {@code total}（各级相加）、{@code readyRate}（可采收比例）、
     * {@code gradeText}（中文摘要）。它们都不进数据库。
     */
    public Map<String, Object> list(int page, int size) {
        // 参数兜底：防止前端传 0 或负数，导致 LIMIT 出错
        if (page < 1) {
            page = 1;
        }
        if (size < 1) {
            size = 20;
        }
        // mysql 的 LIMIT 是 "跳过 offset 条，取 size 条"，offset 从 0 开始
        int offset = (page - 1) * size;

        List<CaptureListItem> list = captureMapper.findList(offset, size);
        long total = captureMapper.countAll();

        // 一页最多 20 条，在内存里按品种解码，比在 SQL 里拆逗号串好读也好改
        for (CaptureListItem item : list) {
            String sp = item.getSpecies();
            String code = item.getRipeness();
            item.setTotal(RipenessCodec.total(sp, code));
            item.setReadyRate(RipenessCodec.readyRate(sp, code));
            item.setGradeText(RipenessCodec.describe(sp, code));
            // key → 前端能直接 <img src> 的 URL（OSS 域名或 /files/ 前缀）
            item.setImageUrl(imageStorage.urlOf(item.getImagePath()));
        }

        Map<String, Object> data = new LinkedHashMap<>();
        data.put("list", list);
        data.put("total", total);
        return data;
    }

    /**
     * 存图，失败不抛异常。
     *
     * <p><b>这是有意做的取舍：</b>识别的钱已经花了（模型跑完了），
     * 结果也拿到了，这时候因为"OSS 网络抖了一下"就把整个请求变成 500，
     * 用户重传一次还得再推理一遍。<b>图片丢了是小事，结果丢了才是大事。</b>
     *
     * @return 存储 key；失败返回 null（数据库里 image_path 就是 null，前端显示占位即可）
     */
    private String storeImageQuietly(byte[] bytes, String originalFilename) {
        try {
            return imageStorage.store(bytes, originalFilename);
        } catch (Exception e) {
            log.warn("图片存储失败（存储方式={}，文件={}）：{}。本条记录将不含图片，其余结果正常保存。",
                    imageStorage.mode(), originalFilename, e.getMessage());
            return null;
        }
    }
}
