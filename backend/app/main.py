"""FastAPI 应用入口：组合授权主站数据、管理员 API、CORS 与数据库服务。"""

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.routers import (
    admin_competitors,
    admin_customer_groups,
    admin_data,
    admin_deals,
    admin_salespeople,
    admin_typical_cases,
    auth,
    authorized_users,
    channel_partner_locations,
    competitors,
    customer_groups,
    deal_heatmap,
    health,
    insights,
    location_search,
    organizations,
    sales_office_locations,
    salespeople,
    typical_cases,
)
from app.services.auth import get_current_user

settings = get_settings()
app = FastAPI(title="优纳特目标单位管理 API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-CSRF-Token", "X-Request-ID"],
)
app.include_router(health.router, prefix="/api/v1")
app.include_router(auth.router, prefix="/api/v1")
app.include_router(authorized_users.router, prefix="/api/v1")
app.include_router(admin_competitors.router, prefix="/api/v1")
app.include_router(admin_customer_groups.router, prefix="/api/v1")
app.include_router(admin_data.router, prefix="/api/v1")
app.include_router(admin_deals.router, prefix="/api/v1")
app.include_router(admin_salespeople.router, prefix="/api/v1")
app.include_router(admin_typical_cases.router, prefix="/api/v1")
app.include_router(location_search.router, prefix="/api/v1")
viewer_dependencies = [Depends(get_current_user)]
app.include_router(organizations.public_router, prefix="/api/v1", dependencies=viewer_dependencies)
app.include_router(organizations.router, prefix="/api/v1")
app.include_router(sales_office_locations.public_router, prefix="/api/v1", dependencies=viewer_dependencies)
app.include_router(sales_office_locations.router, prefix="/api/v1")
app.include_router(channel_partner_locations.public_router, prefix="/api/v1", dependencies=viewer_dependencies)
app.include_router(channel_partner_locations.router, prefix="/api/v1")
app.include_router(customer_groups.public_router, prefix="/api/v1", dependencies=viewer_dependencies)
app.include_router(insights.public_router, prefix="/api/v1", dependencies=viewer_dependencies)
app.include_router(deal_heatmap.public_router, prefix="/api/v1", dependencies=viewer_dependencies)
app.include_router(competitors.public_router, prefix="/api/v1", dependencies=viewer_dependencies)
app.include_router(salespeople.public_router, prefix="/api/v1", dependencies=viewer_dependencies)
app.include_router(typical_cases.public_router, prefix="/api/v1", dependencies=viewer_dependencies)
