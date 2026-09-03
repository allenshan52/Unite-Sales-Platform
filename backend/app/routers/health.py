"""健康检查路由：区分进程存活与 PostgreSQL/Redis 生产就绪状态。"""

from fastapi import APIRouter, Depends, HTTPException, status
from redis import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db

router = APIRouter(tags=["系统"])
settings = get_settings()


@router.get("/health")
def health_check() -> dict[str, str]:
    """保留原有兼容入口，仅表示 API 进程仍可响应。"""

    return {"status": "ok"}


@router.get("/health/live")
def liveness_check() -> dict[str, str]:
    """返回无外部依赖的存活状态，避免依赖故障触发无意义重启。"""

    return {"status": "ok"}


def _redis_is_ready() -> bool:
    """仅在配置 Redis 时执行短超时 PING，并保证客户端及时关闭。"""

    if not settings.redis_url:
        return True
    client = Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
    try:
        return bool(client.ping())
    finally:
        client.close()


@router.get("/health/ready")
def readiness_check(db: Session = Depends(get_db)) -> dict[str, object]:
    """确认数据库与已配置 Redis 可用；失败只返回统一信息，不泄露连接配置。"""

    try:
        db.execute(text("SELECT 1"))
        redis_ready = _redis_is_ready()
    except (SQLAlchemyError, RedisError, OSError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="服务依赖尚未就绪") from None
    if not redis_ready:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="服务依赖尚未就绪")
    return {"status": "ready", "checks": {"database": "ok", "redis": "ok" if settings.redis_url else "未配置"}}
