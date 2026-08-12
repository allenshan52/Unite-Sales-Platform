"""健康检查路由：供 Docker、反向代理和部署系统确认 API 可响应。"""

from fastapi import APIRouter

router = APIRouter(tags=["系统"])


@router.get("/health")
def health_check() -> dict[str, str]:
    """返回无需认证的最小存活状态，避免探针依赖数据库业务数据。"""

    return {"status": "ok"}
