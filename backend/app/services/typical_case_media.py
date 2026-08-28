"""典型案例图片服务：校验管理员上传并去除元数据后统一保存为 WebP。"""

from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

from app.config import get_settings
from app.typical_case_schemas import TypicalCaseImageUploadRead

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/avif"}
MAX_IMAGE_PIXELS = 40_000_000


def _normalize_image(raw: bytes, target_dir: Path) -> TypicalCaseImageUploadRead:
    """解码而非信任扩展名，并重新编码以移除 EXIF 和潜在附加数据。"""

    try:
        with Image.open(BytesIO(raw)) as source:
            width, height = source.size
            if width * height > MAX_IMAGE_PIXELS:
                raise HTTPException(status_code=413, detail="图片像素过大，请上传不超过 4000 万像素的图片")
            # 先检查图片头中的尺寸再解码，避免高压缩比位图绕过内存保护。
            source.load()
            normalized = source.convert("RGBA" if source.mode in {"RGBA", "LA"} else "RGB")
    except Image.DecompressionBombError as error:
        raise HTTPException(status_code=413, detail="图片像素过大，请上传不超过 4000 万像素的图片") from error
    except (UnidentifiedImageError, OSError) as error:
        raise HTTPException(status_code=422, detail="无法识别图片内容，请上传有效的 PNG、JPEG、WebP 或 AVIF") from error

    output = BytesIO()
    normalized.save(output, format="WEBP", quality=86, method=6)
    encoded = output.getvalue()
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid4()}.webp"
    temporary_path = target_dir / f".{filename}.tmp"
    final_path = target_dir / filename
    temporary_path.write_bytes(encoded)
    temporary_path.replace(final_path)
    return TypicalCaseImageUploadRead(
        path=f"/cases/{filename}", width=width, height=height, size_bytes=len(encoded),
    )


async def store_typical_case_image(upload: UploadFile) -> TypicalCaseImageUploadRead:
    """限制文件类型和体积，再在线程池执行图片解码与磁盘写入。"""

    settings = get_settings()
    if upload.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=422, detail="图片仅支持 PNG、JPEG、WebP 或 AVIF")
    raw = await upload.read(settings.typical_case_upload_max_bytes + 1)
    await upload.close()
    if not raw:
        raise HTTPException(status_code=422, detail="上传图片不能为空")
    if len(raw) > settings.typical_case_upload_max_bytes:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="图片不能超过 8MB")
    return await run_in_threadpool(_normalize_image, raw, settings.typical_case_media_dir)
