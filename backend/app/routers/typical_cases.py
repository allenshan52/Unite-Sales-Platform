"""典型案例公开路由：返回第六地图的省级覆盖与去敏案例详情。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.typical_cases import (
    get_public_typical_case,
    list_public_typical_case_map,
)
from app.typical_case_schemas import TypicalCaseMapResponse, TypicalCasePublicDetail

public_router = APIRouter(prefix="/public/typical-cases", tags=["公开典型案例地图"])


@public_router.get("", response_model=TypicalCaseMapResponse)
def public_typical_case_map(
    db: Annotated[Session, Depends(get_db)],
) -> TypicalCaseMapResponse:
    """匿名返回大陆省级案例覆盖及已发布摘要。"""

    return list_public_typical_case_map(db)


@public_router.get("/{case_id}", response_model=TypicalCasePublicDetail)
def public_typical_case_detail(
    case_id: UUID,
    db: Annotated[Session, Depends(get_db)],
) -> TypicalCasePublicDetail:
    """匿名按 ID 读取一条已发布、去敏后的完整案例。"""

    return get_public_typical_case(db, case_id)
