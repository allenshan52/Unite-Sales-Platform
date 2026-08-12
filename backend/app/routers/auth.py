"""认证路由：为单管理员后台建立与撤销 HTTP-only 服务端会话。"""

from fastapi import APIRouter, Cookie, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import CurrentUserRead, LoginInput
from app.services.auth import SESSION_COOKIE_NAME, SESSION_DURATION, get_current_admin, login_admin, logout_admin

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=CurrentUserRead)
def login(payload: LoginInput, response: Response, db: Session = Depends(get_db)) -> CurrentUserRead:
    """验证环境变量初始化的管理员，并把随机会话写入 HTTP-only cookie。"""

    token = login_admin(db, payload.username, payload.password)
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=int(SESSION_DURATION.total_seconds()),
        httponly=True,
        secure=False,
        samesite="lax",
        path="/",
    )
    return CurrentUserRead(username=payload.username)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> Response:
    """撤销当前会话并清除浏览器 cookie，适用于共享电脑的管理后台退出。"""

    logout_admin(db, session_token)
    response.delete_cookie(key=SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/me", response_model=CurrentUserRead)
def current_user(user=Depends(get_current_admin)) -> CurrentUserRead:
    """让前端在加载时确认管理员会话，避免把登录状态只存在浏览器内存。"""

    return CurrentUserRead(username=user.username)
