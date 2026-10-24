r"""
P0 —— Python 推理服务（FastAPI）

把两层模型包成 HTTP 接口，给前端 / Java 后端调用。

    POST /api/predict       上传一张图 → 返回检测 + 成熟度结果
    GET  /api/health        健康检查（含模型是否就绪）
    GET  /                 临时测试页（浏览器里直接拖图试）
    GET  /docs              ★ FastAPI 自动生成的接口文档，答辩/联调时直接打开

"""

import logging
import sys
import time
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

# 保证不管从哪个目录启动，都能 import 到 ai 包。
# app.py 在 ai/server/ 下，往上退两层才是项目根目录（ai 包的父目录）。
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from ai import config, inference
from ai.server.schemas import ErrorResponse, HealthResponse, PredictResponse  # noqa: E402

STATIC_DIR = Path(__file__).resolve().parent / "static"
MAX_UPLOAD_MB = 20
ALLOWED_SUFFIX = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("persimmon")

MODELS_READY = False


# ==============================================================================
# 启动 / 关闭
# ==============================================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """服务启动时把两个模型预加载好，之后请求就不用等加载了。"""
    global MODELS_READY
    log.info("正在预加载模型（第一次要十几秒，请稍等）...")
    t0 = time.time()
    try:
        inference.load(verbose=False)
        MODELS_READY = True
        log.info(f"模型预加载完成，用时 {time.time() - t0:.1f} 秒")
        log.info(f"  第 1 层 检测  {config.DETECT['weights'].name}")
        log.info(f"  第 2 层 分类  {config.get_model_info()['weights'].name}")
    except Exception as e:
        # 不直接退出：让 /api/health 能报告问题，方便排查
        log.error(f"模型加载失败：{e}")
        log.error("服务仍会启动，但 /api/predict 会返回错误。")
    yield
    log.info("服务关闭")


app = FastAPI(
    title="柿子成熟度识别 API",
    description=(
        "两层结构：第 1 层检测出每个柿子的位置，第 2 层判断它的成熟度。\n\n"
        "- 第 1 层：YOLO11n 检测（单类别 persimmon）\n"
        "- 第 2 层：YOLO11n-cls 分类（4 个成熟度）"
    ),
    version="0.1.0",
    lifespan=lifespan,
)

# 前端 Vue 开发时端口不同（如 5173），需要放开跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # 开发阶段放开；上线要改成具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==============================================================================
# 接口
# ==============================================================================
@app.get("/api/health", response_model=HealthResponse, tags=["系统"])
def health():
    """健康检查。前端和容器探针都用它。"""
    default = config.ACTIVE_MODEL
    info = config.get_model_info(default)
    return HealthResponse(
        status="ok" if MODELS_READY else "degraded",
        models_ready=inference.is_ready(default),
        detail={
            "detect": str(info.get("det")),
            "classify": str(info["weights"]),
            "default_species": default,
            "supported_species": config.list_species(),
        },
    )


@app.post(
    "/api/predict",
    response_model=PredictResponse,
    tags=["识别"],
    summary="上传一张图，返回果实位置 + 成熟度（按品种路由）",
)
async def predict(
    file: UploadFile = File(..., description="图片文件"),
    species: str = Form("persimmon", description="果品品种：persimmon / apple"),
):
    """
    上传一张图片，按 `species` 指定的品种做识别，返回：

    - `species`：本次用的品种
    - `detections`：每个果实的框坐标 + 检测置信度 + 成熟度 + 成熟度置信度
    - `counts`：各成熟度等级的数量统计（键跟着该品种的类别走）
    - `timing`：两层的耗时

    注意：**即使一个果实都没检测到，也返回 200**（`detections` 是空数组），
    因为"图里没有果实"是一个正常结果，不是错误。
    """
    # ---- 校验品种 ----
    supported = config.list_species()
    if species not in supported:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的品种 {species!r}，可选：{supported}",
        )

    # ---- 校验扩展名 ----
    suffix = Path(file.filename or "").suffix.lower()
    if suffix and suffix not in ALLOWED_SUFFIX:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的格式 {suffix}，只接受 {', '.join(sorted(ALLOWED_SUFFIX))}",
        )

    # ---- 读上传内容，并限制大小 ----
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="上传的文件是空的")

    size_mb = len(data) / 1024 / 1024
    if size_mb > MAX_UPLOAD_MB:
        raise HTTPException(
            status_code=413,
            detail=f"图片太大（{size_mb:.1f} MB），上限 {MAX_UPLOAD_MB} MB。"
                   f"请先压缩，或在前端缩放后再上传。",
        )

    # ---- 解码（用 imdecode 而不是 imread，能处理任意字节流）----
    import cv2
    frame = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if frame is None:
        raise HTTPException(status_code=400, detail="图片解码失败（文件损坏或不是图片）")

    # ---- 推理（按品种路由到对应的检测 + 分类模型）----
    t0 = time.time()
    out = inference.predict(frame, key=species)
    cost = (time.time() - t0) * 1000

    if not out["ok"]:
        log.warning(f"[{species}] {file.filename}  推理失败：{out['error']}")
        return JSONResponse(status_code=500, content=out)

    log.info(
        f"[{species}] {file.filename}  {out['image']['width']}x{out['image']['height']}  "
        f"检出 {len(out['detections'])} 个  "
        f"检测 {out['timing']['detect_ms']:.0f}ms + 分类 {out['timing']['classify_ms']:.0f}ms  "
        f"合计 {cost:.0f}ms"
    )
    return out


# ==============================================================================
# 临时测试页（正式的 Vue 前端在 P2 阶段做）
# ==============================================================================
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
def index():
    page = STATIC_DIR / "index.html"
    if not page.exists():
        return HTMLResponse("<h1>测试页缺失</h1><p>接口文档在 <a href='/docs'>/docs</a></p>")
    return HTMLResponse(page.read_text(encoding="utf-8"))


# ==============================================================================
# 统一异常处理：任何未捕获异常都返回统一结构，而不是 FastAPI 默认格式
# ==============================================================================
@app.exception_handler(Exception)
async def unhandled(request, exc):
    log.exception("未处理异常")
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(error=f"服务器内部错误：{exc}").model_dump(),
    )
