package org.ymg.persimmon.common;

/**
 * 业务异常 —— 表达"这次操作因为业务原因失败了"。
 *
 * <p><b>为什么不直接用 RuntimeException：</b>
 * 它不带业务状态码。抛出去之后，全局异常处理器分不清
 * "用户图片太大"和"数据库连不上"，只能统一返回 5000，前端给不出准确提示。
 *
 * <p>继承 {@code RuntimeException} 而不是 {@code Exception}，
 * 是为了不用在每一层写 {@code throws} —— 业务校验失败是"正常会发生的情况"，
 * 不是"调用方必须处理的意外"。
 *
 * <p>用法：
 * <pre>
 * Region region = regionMapper.findById(id);
 * if (region == null) {
 *     throw new BizException(ErrorCode.REGION_NOT_FOUND, "区域不存在：" + id);
 * }
 * </pre>
 */
public class BizException extends RuntimeException {

    private final int code;

    public BizException(int code, String message) {
        super(message);
        this.code = code;
    }

    /** 不给码时默认算参数错误 */
    public BizException(String message) {
        this(ErrorCode.BAD_REQUEST, message);
    }

    public int getCode() {
        return code;
    }
}
