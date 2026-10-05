package org.ymg.persimmon.common;

/**
 * 统一响应体 —— 所有接口都返回这个结构。
 *
 * <pre>
 * 成功: { "code": 0,    "message": "ok",       "data": { ... } }
 * 失败: { "code": 4001, "message": "图片太大", "data": null    }
 * </pre>
 *
 * <p><b>⚠️ 这个结构不能随便改 —— 前端已经写好了。</b>
 * {@code web/src/api/request.js} 里的响应拦截器是这样处理的：
 * <pre>
 *   if (body.code !== 0) { 弹错误提示; 抛异常 }
 *   return body.data          // 剥掉外壳，调用方直接拿到 data
 * </pre>
 * 也就是说，前端的每个页面拿到的都是<b>剥过壳的 data</b>。
 * 你这里一旦把字段名改了（比如 code 改成 status），前端所有页面一起挂。
 *
 * <p><b>为什么 code 用 0 表示成功，而不是看 HTTP 200：</b>
 * HTTP 状态码说的是"这次 HTTP 传输"的结果，业务状态码说的是
 * "这次操作"的结果，两者不是一回事。典型例子：用户参数错了，
 * HTTP 是 200（请求成功到达并处理了），业务上却是失败。
 */
public class R<T> {

    /** 业务状态码。0 = 成功，非 0 = 失败。取值见 {@link ErrorCode} */
    private int code;

    /** 给用户看的提示信息 */
    private String message;

    /** 真正的业务数据。失败时为 null */
    private T data;

    public R() {
    }

    public R(int code, String message, T data) {
        this.code = code;
        this.message = message;
        this.data = data;
    }

    public static <T> R<T> ok(T data) {
        return new R<>(0, "ok", data);
    }

    public static <T> R<T> ok() {
        return new R<>(0, "ok", null);
    }

    public static <T> R<T> fail(int code, String message) {
        return new R<>(code, message, null);
    }

    // 用了 Lombok 的话，下面这四个 getter/setter 可以用 @Data 代替。
    // 这里故意手写出来，让你看清楚 Jackson 序列化靠的就是它们 ——
    // 没有 getter，字段就不会出现在 JSON 里（而且不报错）。
    // 如果以后改用 @Data，确认 Lombok 在 IDEA 里装好了（需要开注解处理器）。

    public int getCode() {
        return code;
    }

    public void setCode(int code) {
        this.code = code;
    }

    public String getMessage() {
        return message;
    }

    public void setMessage(String message) {
        this.message = message;
    }

    public T getData() {
        return data;
    }

    public void setData(T data) {
        this.data = data;
    }
}
