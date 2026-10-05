"""
请求 / 响应模型 —— 这就是前后端之间的【接口契约】。

前端只需按这里的结构解析，后端只管往里填。
以后加第 3 层、换模型、换算法，只要这个结构不变，前端一个字都不用改。

FastAPI 会用这些模型自动生成 /docs 接口文档。
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


# ==============================================================================
# 响应模型
# ==============================================================================
class ImageInfo(BaseModel):
    width: int = Field(..., description="图片宽度（像素）")
    height: int = Field(..., description="图片高度（像素）")


class Detection(BaseModel):
    """一个柿子 = 一个框 + 一个成熟度判定。"""

    box: List[int] = Field(..., description="像素坐标 [x1, y1, x2, y2]，原点在左上角")
    det_conf: float = Field(..., ge=0, le=1, description="第 1 层（检测）置信度")
    ripeness: str = Field(..., description="第 2 层类别（英文），如 3_coloring")
    ripeness_label: str = Field(..., description="第 2 层类别（中文），如 着色期（橙红）")
    ripeness_conf: float = Field(..., ge=0, le=1, description="第 2 层（成熟度）置信度")

    model_config = {
        "json_schema_extra": {
            "example": {
                "box": [392, 754, 833, 1129],
                "det_conf": 0.976,
                "ripeness": "3_coloring",
                "ripeness_label": "着色期（橙红）",
                "ripeness_conf": 0.897,
            }
        }
    }


class Timing(BaseModel):
    detect_ms: float = Field(..., description="第 1 层检测耗时（毫秒）")
    classify_ms: float = Field(..., description="第 2 层分类总耗时（毫秒，所有框累加）")


class PredictResponse(BaseModel):
    """识别一张图的完整结果。"""

    ok: bool = Field(..., description="是否成功。false 时看 error")
    image: ImageInfo
    detections: List[Detection] = Field(default_factory=list, description="检出的每个柿子")
    counts: Dict[str, int] = Field(
        default_factory=dict,
        description="各类成熟度的数量统计，键为 1_unripe/2_turning/3_coloring/4_full",
    )
    timing: Timing
    error: Optional[str] = Field(None, description="失败原因；成功时为 null")

    model_config = {
        "json_schema_extra": {
            "example": {
                "ok": True,
                "image": {"width": 1280, "height": 1714},
                "detections": [
                    {
                        "box": [392, 754, 833, 1129],
                        "det_conf": 0.976,
                        "ripeness": "3_coloring",
                        "ripeness_label": "着色期（橙红）",
                        "ripeness_conf": 0.897,
                    }
                ],
                "counts": {"1_unripe": 0, "2_turning": 0, "3_coloring": 1, "4_full": 0},
                "timing": {"detect_ms": 42.1, "classify_ms": 86.3},
                "error": None,
            }
        }
    }


class HealthResponse(BaseModel):
    status: str = Field(..., description="ok / degraded")
    models_ready: bool = Field(..., description="两个模型文件是否都在")
    detail: Dict[str, str] = Field(default_factory=dict, description="各层的权重路径")


class ErrorResponse(BaseModel):
    ok: bool = False
    error: str
