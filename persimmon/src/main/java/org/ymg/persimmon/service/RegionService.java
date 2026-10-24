package org.ymg.persimmon.service;

import org.springframework.stereotype.Service;
import org.ymg.persimmon.common.BizException;
import org.ymg.persimmon.common.ErrorCode;
import org.ymg.persimmon.entity.Region;
import org.ymg.persimmon.mapper.RegionMapper;

import java.util.List;

/**
 * 区域的业务逻辑。
 *
 * <p><b>Service 层该干什么：</b>它就是"业务规则"待的地方。
 * Mapper 只管把数据读出来、写进去；"这个区域不存在时该怎么办"
 * 这种判断属于业务，放在这里。Controller 只负责收发，也不写业务。
 *
 * <p><b>为什么用构造器注入而不是 {@code @Autowired} 字段注入：</b>
 * 构造器注入能保证依赖<b>不为 null</b>（对象一造出来依赖就齐了），
 * 字段注入可能拿到 null 才发现。这也是 Spring 官方现在推荐的做法。
 */
@Service
public class RegionService {

    private final RegionMapper regionMapper;

    public RegionService(RegionMapper regionMapper) {
        this.regionMapper = regionMapper;
    }

    /** 所有区域 —— 给上传页的下拉框 */
    public List<Region> listAll() {
        return regionMapper.findAll();
    }

    /**
     * 按 id 取区域，取不到就抛业务异常。
     *
     * <p><b>谁会调它：</b>上传接口。上传时前端会带一个 regionId，
     * 我们必须确认这个区域真实存在，否则会往 capture 表里写一个指向不存在区域的脏数据
     * （虽然有外键约束挡着，但那时报的是数据库错误，用户看不懂；
     * 这里主动校验，能给出"区域不存在：5"这种能看懂的提示）。
     *
     * <p>抛出 {@link BizException} 后不用管 —— GlobalExceptionHandler 会把它
     * 转成 {@code {code:4004, message:"区域不存在：5"}} 返回给前端。
     */
    public Region getById(Long id) {
        if (id == null) {
            throw new BizException(ErrorCode.BAD_REQUEST, "regionId 不能为空");
        }
        Region region = regionMapper.findById(id);
        if (region == null) {
            throw new BizException(ErrorCode.REGION_NOT_FOUND, "区域不存在：" + id);
        }
        return region;
    }
}
