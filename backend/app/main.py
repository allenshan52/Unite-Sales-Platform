"""FastAPI 应用入口：组合公开目录、管理员 API、CORS 与数据库服务。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import auth, channel_partner_locations, health, organizations, sales_office_locations

settings = get_settings()
app = FastAPI(title="优纳特目标单位管理 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type"],
)
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(organizations.public_router, prefix="/api/v1")
app.include_router(organizations.router, prefix="/api/v1")
app.include_router(sales_office_locations.public_router, prefix="/api/v1")
app.include_router(sales_office_locations.router, prefix="/api/v1")
app.include_router(channel_partner_locations.public_router, prefix="/api/v1")
app.include_router(channel_partner_locations.router, prefix="/api/v1")
