"""数据库会话：为 FastAPI 请求提供 SQLAlchemy PostgreSQL 事务边界。"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    """全部 ORM 模型共享的声明式基类，供 Alembic 收集数据库元数据。"""


def get_db() -> Generator[Session, None, None]:
    """每个 HTTP 请求创建并最终关闭一个数据库会话，防止连接泄漏。"""

    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
