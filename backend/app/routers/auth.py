"""认证路由：为主站授权账号建立、恢复与撤销 HTTP-only 服务端会话。"""

from urllib.parse import urlsplit

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import UserRole
from app.sales_coverage import included_provinces
from app.schemas import AuthorizedUserCoverageScopeRead, CurrentUserRead, LoginInput
from app.services.auth import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME, SESSION_DURATION, get_current_user, login_user, logout_user
from app.services.account_access import account_data_scope

router = APIRouter(prefix="/auth", tags=["认证"])
settings = get_settings()


def _read_current_user(user) -> CurrentUserRead:
    """集中返回当前账号的可公开权限摘要，超级管理员能力只由服务端角色决定。"""

    scopes = sorted(
        getattr(user, "coverage_scopes", []),
        key=lambda item: (item.scope_level.value, item.scope_name, str(item.id)),
    )
    return CurrentUserRead(
        username=user.username,
        role=user.role,
        salesperson_id=getattr(user, "salesperson_id", None),
        coverage_scopes=[AuthorizedUserCoverageScopeRead(
            id=item.id,
            scope_level=item.scope_level,
            scope_name=item.scope_name,
            province=item.province,
            city=item.city,
            amap_adcode=item.amap_adcode,
            included_provinces=included_provinces(item.scope_level, item.scope_name, item.province),
        ) for item in scopes],
        can_manage_users=user.role == UserRole.admin,
        can_manage_salespeople=account_data_scope(user).unrestricted,
    )


def _validate_login_origin(request: Request) -> None:
    """接受配置来源或 Origin/Host 严格同主机请求，兼容受信反向代理的动态域名。"""

    origin = request.headers.get("origin")
    allowed_origins = {item.strip() for item in settings.cors_origins.split(",") if item.strip()}
    request_host = request.headers.get("host", "").lower()
    origin_host = urlsplit(origin).netloc.lower() if origin else ""
    if origin and origin not in allowed_origins and origin_host != request_host:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="不允许从当前来源登录")


@router.post("/login", response_model=CurrentUserRead)
def login(payload: LoginInput, request: Request, response: Response, db: Session = Depends(get_db)) -> CurrentUserRead:
    """验证授权账号来源与凭据，并写入服务端会话及双提交 CSRF Cookie。"""

    _validate_login_origin(request)
    token, csrf_token, user = login_user(db, payload.username, payload.password)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=True,
        secure=settings.admin_cookie_secure,
        samesite="lax",
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=False,
        secure=settings.admin_cookie_secure,
        samesite="strict",
        path="/",
    )
    return _read_current_user(user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
    _user=Depends(get_current_user),
) -> Response:
    """撤销当前会话并返回显式 204 响应，确保浏览器可靠清除共享电脑上的登录 cookie。"""

    logout_user(db, session_token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path="/",
        httponly=True,
        secure=settings.admin_cookie_secure,
        samesite="lax",
    )
    response.delete_cookie(
        key=CSRF_COOKIE_NAME,
        path="/",
        secure=settings.admin_cookie_secure,
        samesite="strict",
    )
    return response


@router.get("/me", response_model=CurrentUserRead)
def current_user(user=Depends(get_current_user)) -> CurrentUserRead:
    """让前端在加载时确认授权会话与角色，避免把登录状态只存在浏览器内存。"""

    return _read_current_user(user)
