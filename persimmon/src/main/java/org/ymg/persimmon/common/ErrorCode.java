package org.ymg.persimmon.common;

/**
 * 业务状态码表 —— 所有 code 集中在这里定义。
 *
 * <p><b>为什么集中：</b>前端要按 code 做不同处理，如果 code 散落在各个
 * Service 里写成魔法数字，改一个忘一个，前端就跟着错。
 *
 * <p><b>分段规则：</b>
 * <pre>
 *   0      成功
 *   4xxx   客户端的问题（参数错、文件不合法）—— 用户自己能改
 *   5xxx   服务端的问题（AI 挂了、内部异常）—— 用户改了也没用
 * </pre>
 * 看首位就知道该怪谁。
 *
 * <p>用 {@code final class} + 私有构造，防止有人 new 它或继承它。
 */
public final class ErrorCode {

    public static final int OK = 0;

    // ---- 4xxx 客户端的问题 ----
    public static final int BAD_REQUEST = 4000;
    public static final int FILE_TOO_LARGE = 4001;
    public static final int UNSUPPORTED_FORMAT = 4002;
    public static final int EMPTY_FILE = 4003;
    public static final int REGION_NOT_FOUND = 4004;

    // ---- 5xxx 服务端的问题 ----
    public static final int INTERNAL_ERROR = 5000;
    public static final int AI_SERVICE_UNAVAILABLE = 5001;
    public static final int AI_INFERENCE_FAILED = 5002;

    private ErrorCode() {
    }
}
