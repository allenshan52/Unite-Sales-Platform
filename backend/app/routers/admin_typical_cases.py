"""典型案例管理路由：提供受管理员会话保护的聚合增删改查。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AdminUser
from app.services.account_access import account_data_scope, require_location_access
from app.services.auth import get_current_admin
from app.services.typical_case_media import store_typical_case_image
from app.services.typical_cases import (
    create_typical_case,
    delete_typical_case,
    get_admin_typical_case,
    list_admin_typical_case_overview,
    list_typical_case_project_options,
    to_admin_read,
    update_typical_case,
)
from app.typical_case_schemas import (
    TypicalCaseAdminOverview,
    TypicalCaseAdminRead,
    TypicalCaseImageUploadRead,
    TypicalCaseInput,
    TypicalCaseProjectOption,
)

router = APIRouter(prefix="/admin-typical-cases", tags=["典型案例管理"])


@router.get("/project-options", response_model=list[TypicalCaseProjectOption])
def project_options(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
    search: Annotated[str | None, Query(max_length=120)] = None,
    selected_id: UUID | None = None,
    province: Annotated[str | None, Query(max_length=60)] = None,
) -> list[TypicalCaseProjectOption]:
    """搜索账号范围内可关联成交项目，并保留授权已选项。"""

    return list_typical_case_project_options(
        db,
        search=search,
        selected_id=selected_id,
        province=province,
        data_scope=account_data_scope(user),
    )


@router.get("", response_model=TypicalCaseAdminOverview)
def list_cases(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> TypicalCaseAdminOverview:
    """只返回账号负责省份的轻量案例槽位，案例正文仍按需读取。"""

    return list_admin_typical_case_overview(db, account_data_scope(user))


@router.post("/images", response_model=TypicalCaseImageUploadRead, status_code=status.HTTP_201_CREATED)
async def upload_image(
    file: Annotated[UploadFile, File()],
    _user: Annotated[AdminUser, Depends(get_current_admin)],
) -> TypicalCaseImageUploadRead:
    """保存一张经过解码和去元数据处理的案例图片。"""

    return await store_typical_case_image(file)


@router.get("/{case_id}", response_model=TypicalCaseAdminRead)
def get_case(
    case_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> TypicalCaseAdminRead:
    """只读取账号负责区域内的一条可编辑完整案例。"""

    return to_admin_read(get_admin_typical_case(db, case_id, account_data_scope(user)))


@router.post("", response_model=TypicalCaseAdminRead, status_code=status.HTTP_201_CREATED)
def create_case(
    payload: TypicalCaseInput,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> TypicalCaseAdminRead:
    """在账号负责区域内写入案例故事、图片元数据及成果指标。"""

    require_location_access(account_data_scope(user), payload.province, payload.city)
    return create_typical_case(db, payload, user.username)


@router.patch("/{case_id}", response_model=TypicalCaseAdminRead)
def update_case(
    case_id: UUID,
    payload: TypicalCaseInput,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> TypicalCaseAdminRead:
    """只允许账号覆盖原案例区域和提交区域时覆盖完整案例。"""

    data_scope = account_data_scope(user)
    current = get_admin_typical_case(db, case_id)
    require_location_access(data_scope, current.province, current.city)
    require_location_access(data_scope, payload.province, payload.city)
    return update_typical_case(db, case_id, payload, user.username)


@router.delete("/{case_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_case(
    case_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_admin)],
) -> Response:
    """确认案例位于账号范围后删除；前端负责二次确认。"""

    current = get_admin_typical_case(db, case_id)
    require_location_access(account_data_scope(user), current.province, current.city)
    delete_typical_case(db, case_id, user.username)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
