"""客户集团公开路由：为首页提供总部首屏和单集团关系树的只读接口。"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AdminUser
from app.schemas import CustomerGroupDetailRead, CustomerGroupHeadquartersRead
from app.services.customer_groups import (
    get_public_customer_group_detail,
    list_public_customer_group_headquarters,
)
from app.services.account_access import account_data_scope
from app.services.auth import get_current_user

public_router = APIRouter(prefix="/public/customer-groups", tags=["公开客户关系网络"])


@public_router.get("", response_model=list[CustomerGroupHeadquartersRead])
def public_customer_group_headquarters(
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_user)],
) -> list[CustomerGroupHeadquartersRead]:
    """返回账号范围内集团总部，首页不提前加载全部分支。"""

    return list_public_customer_group_headquarters(db, account_data_scope(user))


@public_router.get("/{group_id}", response_model=CustomerGroupDetailRead)
def public_customer_group_detail(
    group_id: UUID,
    db: Annotated[Session, Depends(get_db)],
    user: Annotated[AdminUser, Depends(get_current_user)],
) -> CustomerGroupDetailRead:
    """返回账号范围内集团节点、层级和动态汇总，供总部点击后展开。"""

    return get_public_customer_group_detail(db, group_id, account_data_scope(user))
