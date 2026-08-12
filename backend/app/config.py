"""运行配置：从根目录 .env 或容器环境读取 FastAPI 与 PostgreSQL 设置。"""

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """集中校验服务运行所需的非公开配置，避免路由直接读取环境变量。"""

    postgres_db: str
    postgres_user: str
    postgres_password: str
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    admin_username: str
    admin_password: str
    amap_rest_api_key: str | None = None
    app_port: int = 3100
    cors_origins: str = "http://localhost:3100"
    # 所有官方名单采集共用此边界；默认 4，必要时可在根 .env 调整但不可超过 8。
    official_import_max_parallel_requests: int = Field(default=4, ge=1, le=8)
    official_import_max_request_attempts: int = Field(default=5, ge=1, le=10)
    official_import_request_timeout_seconds: int = Field(default=30, ge=5, le=120)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        """生成经过 URL 编码的 SQLAlchemy PostgreSQL 连接地址，不在日志输出凭据。"""

        user = quote_plus(self.postgres_user)
        password = quote_plus(self.postgres_password)
        return f"postgresql+psycopg://{user}:{password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"


@lru_cache
def get_settings() -> Settings:
    """缓存配置实例，保证同一进程的数据库与认证配置保持一致。"""

    return Settings()
