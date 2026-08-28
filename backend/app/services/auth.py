"""站点认证服务：使用密码哈希、角色和服务端会话保护主站与管理员后台。"""

from datetime import UTC, datetime, timedelta
from hmac import compare_digest
from hashlib import sha256
from secrets import token_urlsafe

from fastapi import Cookie, Depends, Header, HTTPException, Request, status
from pwdlib import PasswordHash
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.config import get_settings
from app.database import get_db
from app.models import AdminSession, AdminUser, AdminUserCoverageScope, UserRole
from app.sales_coverage import SalesCoverageLevel
from app.services.account_access import account_data_scope

password_hasher = PasswordHash.recommended()
SESSION_COOKIE_NAME = "unite_admin_session"
CSRF_COOKIE_NAME = "unite_csrf_token"
SESSION_DURATION = timedelta(hours=12)


def _hash_token(token: str) -> str:
    """仅保存随机会话 token 的 SHA-256 摘要，数据库泄露时不能直接登录。"""

    return sha256(token.encode("utf-8")).hexdigest()


def ensure_initial_admin(db: Session) -> AdminUser:
    """按环境变量创建或修复唯一超级管理员，并确保其固定拥有全国范围。"""

    settings = get_settings()
    user = db.scalar(select(AdminUser).where(AdminUser.username == settings.admin_username))
    if user:
        changed = False
        if user.role != UserRole.admin:
            user.role = UserRole.admin
            changed = True
        scopes = list(user.coverage_scopes)
        if len(scopes) != 1 or scopes[0].scope_level != SalesCoverageLevel.national:
            user.coverage_scopes[:] = [AdminUserCoverageScope(
                scope_level=SalesCoverageLevel.national,
                scope_name="全国",
            )]
            changed = True
        if changed:
            db.commit()
            db.refresh(user)
        return user
    user = AdminUser(
        username=settings.admin_username,
        password_hash=password_hasher.hash(settings.admin_password),
        role=UserRole.admin,
        coverage_scopes=[AdminUserCoverageScope(
            scope_level=SalesCoverageLevel.national,
            scope_name="全国",
        )],
    )
    try:
        db.add(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(AdminUser).where(AdminUser.username == settings.admin_username))
        if existing:
            return existing
        raise
    db.refresh(user)
    return user


def login_user(db: Session, username: str, password: str) -> tuple[str, str, AdminUser]:
    """验证任一授权账号、执行失败锁定，并创建绑定 CSRF 凭据的服务端会话。"""

    ensure_initial_admin(db)
    settings = get_settings()
    now = datetime.now(UTC)
    # 锁住当前账号行，避免并发失败登录互相覆盖计数而绕过账户锁定。
    user = db.scalar(select(AdminUser).where(AdminUser.username == username).with_for_update())
    if user and user.locked_until and user.locked_until > now:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="登录尝试过多，请稍后重试")
    if not user or not user.is_active or not password_hasher.verify(password, user.password_hash):
        if user:
            user.failed_login_attempts += 1
            if user.failed_login_attempts >= settings.admin_login_max_attempts:
                user.locked_until = now + timedelta(seconds=settings.admin_login_lock_seconds)
            db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码不正确")
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    # 成功登录时顺带回收全部过期会话，避免长期运行积累历史行。
    db.execute(delete(AdminSession).where(AdminSession.expires_at <= now))
    token = token_urlsafe(32)
    csrf_token = token_urlsafe(32)
    db.add(AdminSession(
        user_id=user.id,
        token_hash=_hash_token(token),
        csrf_token_hash=_hash_token(csrf_token),
        expires_at=now + SESSION_DURATION,
    ))
    db.commit()
    return token, csrf_token, user


def get_current_user(
    request: Request,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    csrf_token: str | None = Header(default=None, alias="X-CSRF-Token"),
    db: Session = Depends(get_db),
) -> AdminUser:
    """恢复任一有效授权会话，并为所有写请求校验与会话绑定的 CSRF token。"""

    if not session_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="请先登录")
    session = db.scalar(
        select(AdminSession)
        .options(joinedload(AdminSession.user).options(selectinload(AdminUser.coverage_scopes)))
        .where(
            AdminSession.token_hash == _hash_token(session_token),
            AdminSession.expires_at > datetime.now(UTC),
        )
    )
    if not session or not session.user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        csrf_hash = _hash_token(csrf_token) if csrf_token else ""
        if not compare_digest(csrf_hash, session.csrf_token_hash):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="安全校验失败，请刷新页面后重试")
    return session.user


def get_current_admin(user: AdminUser = Depends(get_current_user)) -> AdminUser:
    """兼容既有后台路由名称，并允许所有已登录账号进入区域化数据后台。"""

    return user


def get_current_super_admin(user: AdminUser = Depends(get_current_admin)) -> AdminUser:
    """只允许超级管理员维护授权账号，和普通数据后台访问权限保持隔离。"""

    if getattr(user, "role", UserRole.admin) != UserRole.admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号没有超级管理员权限")
    return user


def get_current_national_user(user: AdminUser = Depends(get_current_admin)) -> AdminUser:
    """仅允许超级管理员或全国覆盖账号进入销售人员管理数据库。"""

    if not account_data_scope(user).unrestricted:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前账号没有销售数据库管理权限")
    return user


def logout_user(db: Session, token: str | None) -> None:
    """删除当前会话记录，使浏览器 cookie 即刻失效。"""

    if token:
        session = db.scalar(select(AdminSession).where(AdminSession.token_hash == _hash_token(token)))
        if session:
            db.delete(session)
            db.commit()
