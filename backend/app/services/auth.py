"""管理员认证服务：使用密码哈希和服务端会话，不在客户端保存明文 token。"""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe

from fastapi import Cookie, Depends, HTTPException, status
from pwdlib import PasswordHash
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import get_db
from app.models import AdminSession, AdminUser

password_hasher = PasswordHash.recommended()
SESSION_COOKIE_NAME = "unite_admin_session"
SESSION_DURATION = timedelta(hours=12)


def _hash_token(token: str) -> str:
    """仅保存随机会话 token 的 SHA-256 摘要，数据库泄露时不能直接登录。"""

    return sha256(token.encode("utf-8")).hexdigest()


def ensure_initial_admin(db: Session) -> AdminUser:
    """首次登录前按环境变量创建管理员，后续不会覆盖既有密码哈希。"""

    settings = get_settings()
    user = db.scalar(select(AdminUser).where(AdminUser.username == settings.admin_username))
    if user:
        return user
    user = AdminUser(username=settings.admin_username, password_hash=password_hasher.hash(settings.admin_password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def login_admin(db: Session, username: str, password: str) -> str:
    """验证管理员并创建可撤销的服务端会话，返回仅用于 HTTP-only cookie 的随机 token。"""

    ensure_initial_admin(db)
    user = db.scalar(select(AdminUser).where(AdminUser.username == username, AdminUser.is_active.is_(True)))
    if not user or not password_hasher.verify(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码不正确")
    token = token_urlsafe(32)
    db.add(AdminSession(user_id=user.id, token_hash=_hash_token(token), expires_at=datetime.now(UTC) + SESSION_DURATION))
    db.commit()
    return token


def get_current_admin(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> AdminUser:
    """从 HTTP-only cookie 恢复有效管理员会话，并统一返回中文权限错误。"""

    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录管理后台")
    session = db.scalar(
        select(AdminSession).where(
            AdminSession.token_hash == _hash_token(session_token),
            AdminSession.expires_at > datetime.now(UTC),
        )
    )
    if not session or not session.user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")
    return session.user


def logout_admin(db: Session, token: str | None) -> None:
    """删除当前会话记录，使浏览器 cookie 即刻失效。"""

    if token:
        session = db.scalar(select(AdminSession).where(AdminSession.token_hash == _hash_token(token)))
        if session:
            db.delete(session)
            db.commit()
