package org.ymg.persimmon.common;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.multipart.MaxUploadSizeExceededException;

/**
 * 全局异常处理器 —— 把所有异常收口成统一的 {@link R} 结构。
 *
 * <p><b>{@code @RestControllerAdvice} 做了什么：</b>
 * 它给所有 Controller 加了一层"环绕的 try-catch"。Controller 里抛出的异常
 * 都会被这里接住，所以你的 Controller 里<b>一个 try-catch 都不用写</b>。
 *
 * <p><b>不写这个类会怎样：</b>抛异常时 Spring 返回它默认的错误结构
 * （{@code {timestamp, status, error, path}}），和成功时的结构完全不同，
 * 前端的拦截器认不出，用户看到的就是"请求失败"四个字，不知道发生了什么。
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    /** 业务异常：我们自己主动抛的，属于"正常会发生的情况"，记 warn 不记堆栈 */
    @ExceptionHandler(BizException.class)
    public ResponseEntity<R<Void>> handleBiz(BizException e) {
        log.warn("业务异常 code={} msg={}", e.getCode(), e.getMessage());
        return ResponseEntity.ok(R.fail(e.getCode(), e.getMessage()));
    }

    /** 上传文件超过限制。这个异常在进 Controller 之前就被 Spring 抛出来了 */
    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ResponseEntity<R<Void>> handleTooLarge(MaxUploadSizeExceededException e) {
        log.warn("上传文件超过限制: {}", e.getMessage());
        return ResponseEntity.ok(
                R.fail(ErrorCode.FILE_TOO_LARGE, "图片太大，请压缩后再上传（上限 20MB）"));
    }

    /**
     * 兜底：所有没被上面接住的异常。
     *
     * <p>必须记 error + 完整堆栈 —— 走到这里说明是我们没预料到的问题，
     * 排障全靠这条日志。同时<b>不能把堆栈返回给前端</b>，
     * 那会泄露内部结构，也帮不到用户。
     */
    @ExceptionHandler(Exception.class)
    public ResponseEntity<R<Void>> handleUnexpected(Exception e) {
        log.error("未预料到的异常", e);
        return ResponseEntity.status(HttpStatus.INTERNAL_SERVER_ERROR)
                .body(R.fail(ErrorCode.INTERNAL_ERROR, "服务器内部错误：" + e.getMessage()));
    }
}
