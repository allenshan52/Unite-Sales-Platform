"""运行配置：从根目录 .env 或容器环境读取 FastAPI 与 PostgreSQL 设置。"""

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import Field, model_validator
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
    admin_cookie_secure: bool = False
    app_environment: str = "development"
    redis_url: str | None = None
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=10, ge=0, le=100)
    database_pool_timeout_seconds: int = Field(default=30, ge=1, le=120)
    database_pool_recycle_seconds: int = Field(default=1800, ge=60, le=86_400)
    database_connect_timeout_seconds: int = Field(default=5, ge=1, le=30)
    database_statement_timeout_ms: int = Field(default=15_000, ge=1_000, le=300_000)
    admin_login_max_attempts: int = Field(default=5, ge=3, le=20)
    admin_login_lock_seconds: int = Field(default=900, ge=60, le=86_400)
    amap_rest_api_key: str | None = None
    amap_service_base_url: str = "https://restapi.amap.com"
    app_port: int = 3100
    cors_origins: str = "http://localhost:3100"
    typical_case_media_dir: Path = Path("/case-media")
    typical_case_upload_max_bytes: int = Field(default=8 * 1024 * 1024, ge=1_048_576, le=20 * 1024 * 1024)
    # 所有官方名单采集共用此边界；默认 4，必要时可在根 .env 调整但不可超过 8。
    official_import_max_parallel_requests: int = Field(default=4, ge=1, le=8)
    official_import_max_request_attempts: int = Field(default=5, ge=1, le=10)
    official_import_request_timeout_seconds: int = Field(default=30, ge=5, le=120)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def require_secure_cookie_in_production(self) -> "Settings":
        """拒绝不安全生产 Cookie 及与凭据请求不兼容的通配 CORS 来源。"""

        if self.app_environment.lower() == "production" and not self.admin_cookie_secure:
            raise ValueError("生产环境必须设置 ADMIN_COOKIE_SECURE=true")
        if "*" in {origin.strip() for origin in self.cors_origins.split(",")}:
            raise ValueError("CORS_ORIGINS 不能使用通配符，必须显式列出可信来源")
        return self

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
