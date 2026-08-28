"""补齐六家优纳特已成交演示公司、主地点和实际成交项目。"""

from datetime import UTC, date, datetime
from decimal import Decimal

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "20260813_0008"
down_revision = "20260812_0007"
branch_labels = None
depends_on = None


def _uuid(number: int) -> str:
    """生成稳定 UUID，保证演示数据可验证并可安全回滚。"""

    return f"00000000-0000-4000-8000-{number:012d}"


CUSTOMERS = (
    (1, "公司1", "华东实验室设备", "上海市", "上海市", "浦东新区", 121.4917, 31.2174, 121.4872399874631, 31.219400058174497, "二级"),
    (2, "公司2", "华北食品检测", "北京市", "北京市", "海淀区", 116.4254, 39.8912, 116.4191748922385, 39.889808378924684, "一级"),
    (3, "公司3", "华南环境监测", "广东省", "广州市", "天河区", 113.2824, 23.1161, 113.2770533530674, 23.11876643007988, "一级"),
    (4, "公司4", "华北生物技术", "天津市", "天津市", "滨海新区", 117.2009, 39.0842, 117.19460215656956, 39.08319405250946, "三级"),
    (5, "公司5", "华东医药研发", "浙江省", "杭州市", "滨江区", 120.1551, 30.2741, 120.15040552070364, 30.276428776799747, "二级"),
    (6, "公司6", "华南新材料", "广东省", "深圳市", "南山区", 114.0579, 22.5431, 114.05278600143454, 22.545817185777537, "一级"),
)

PROJECTS = (
    (1, 1, "公司1实验室设备一期", "680000.00", date(2025, 3, 18), "演示成交：实验室分析设备与安装培训"),
    (2, 1, "公司1耗材年度供应", "240000.00", date(2026, 1, 12), "演示成交：年度配套耗材框架协议"),
    (3, 2, "公司2食品安全检测平台", "560000.00", date(2025, 8, 6), "演示成交：食品检测设备与方法开发服务"),
    (4, 3, "公司3环境监测系统", "1080000.00", date(2025, 6, 21), "演示成交：多参数环境监测系统"),
    (5, 3, "公司3技术服务续约", "320000.00", date(2026, 2, 9), "演示成交：年度校准与技术服务"),
    (6, 4, "公司4生物样品前处理项目", "430000.00", date(2025, 11, 15), "演示成交：样品前处理设备与验证"),
    (7, 5, "公司5研发中心分析平台", "760000.00", date(2025, 9, 27), "演示成交：研发分析平台一期"),
    (8, 5, "公司5应用培训服务", "180000.00", date(2026, 3, 5), "演示成交：应用培训与方法转移"),
    (9, 6, "公司6新材料检测产线", "1250000.00", date(2026, 4, 16), "演示成交：新材料检测设备集成"),
)


def upgrade() -> None:
    """升级现有三家公司并新增三家公司，使实际成交完全由项目记录汇总。"""

    organization_table = sa.table(
        "organization",
        sa.column("id"),
        sa.column("name"),
        sa.column("normalized_name"),
        sa.column("organization_type"),
        sa.column("industry"),
        sa.column("customer_status"),
        sa.column("review_status"),
        sa.column("inclusion_reason"),
        sa.column("is_sports_exception"),
        sa.column("recent_follow_up_at"),
        sa.column("recent_follow_up_content"),
        sa.column("cooperation_intent"),
        sa.column("cooperation_level"),
        sa.column("attributes", postgresql.JSONB()),
        sa.column("notes"),
    )
    site_table = sa.table(
        "organization_site",
        *[sa.column(name) for name in ("id", "organization_id", "site_name", "raw_address", "address", "province", "city", "district", "amap_adcode", "geocode_status", "geocode_confidence", "longitude", "latitude", "is_primary")],
    )
    project_table = sa.table(
        "sales_project",
        *[sa.column(name) for name in ("id", "organization_id", "opportunity_id", "name", "contract_amount", "signed_at", "project_detail")],
    )
    connection = op.get_bind()
    now = datetime(2026, 8, 13, tzinfo=UTC)

    for number, name, industry, province, city, district, longitude, latitude, wgs_longitude, wgs_latitude, cooperation_level in CUSTOMERS:
        organization_id = _uuid(5000 + number)
        if number <= 3:
            connection.execute(
                sa.text("""
                    UPDATE organization
                    SET customer_status = '已成交客户', industry = :industry,
                        recent_follow_up_at = :recent_follow_up_at,
                        recent_follow_up_content = :recent_follow_up_content,
                        cooperation_intent = :cooperation_intent,
                        cooperation_level = :cooperation_level,
                        attributes = attributes || '{"demo": true, "won_customer_demo": true}'::jsonb,
                        notes = :notes
                    WHERE id = :organization_id
                """),
                {
                    "organization_id": organization_id,
                    "industry": industry,
                    "recent_follow_up_at": now,
                    "recent_follow_up_content": "演示跟进：已完成交付并进入持续服务阶段",
                    "cooperation_intent": "演示合作：维护已成交项目并跟进复购",
                    "cooperation_level": cooperation_level,
                    "notes": "纯虚构已成交单位，仅用于优纳特客户地图演示",
                },
            )
            connection.execute(
                sa.text("""
                    UPDATE organization_site
                    SET district = :district,
                        location = ST_SetSRID(ST_MakePoint(:wgs_longitude, :wgs_latitude), 4326)
                    WHERE id = :site_id
                """),
                {"site_id": _uuid(5100 + number), "district": district, "wgs_longitude": wgs_longitude, "wgs_latitude": wgs_latitude},
            )
            continue

        op.bulk_insert(organization_table, [{
            "id": organization_id,
            "name": name,
            "normalized_name": name.lower(),
            "organization_type": "企业",
            "industry": industry,
            "customer_status": "已成交客户",
            "review_status": "已核验",
            "inclusion_reason": "优纳特已成交客户地图演示",
            "is_sports_exception": False,
            "recent_follow_up_at": now,
            "recent_follow_up_content": "演示跟进：已完成交付并进入持续服务阶段",
            "cooperation_intent": "演示合作：维护已成交项目并跟进复购",
            "cooperation_level": cooperation_level,
            "attributes": {"demo": True, "won_customer_demo": True},
            "notes": "纯虚构已成交单位，仅用于优纳特客户地图演示",
        }])
        address = f"{city}{district}演示产业园{number}号"
        op.bulk_insert(site_table, [{
            "id": _uuid(5100 + number),
            "organization_id": organization_id,
            "site_name": f"{name}主地点",
            "raw_address": address,
            "address": address,
            "province": province,
            "city": city,
            "district": district,
            "amap_adcode": None,
            "geocode_status": "已定位",
            "geocode_confidence": 100,
            "longitude": longitude,
            "latitude": latitude,
            "is_primary": True,
        }])
        connection.execute(
            sa.text("UPDATE organization_site SET location = ST_SetSRID(ST_MakePoint(:longitude, :latitude), 4326) WHERE id = :site_id"),
            {"site_id": _uuid(5100 + number), "longitude": wgs_longitude, "latitude": wgs_latitude},
        )

    op.bulk_insert(project_table, [{
        "id": _uuid(5300 + project_number),
        "organization_id": _uuid(5000 + company_number),
        "opportunity_id": None,
        "name": name,
        "contract_amount": Decimal(amount),
        "signed_at": signed_at,
        "project_detail": detail,
    } for project_number, company_number, name, amount, signed_at, detail in PROJECTS])


def downgrade() -> None:
    """删除本迁移成交项目和新增公司，并把原三家公司恢复为潜在客户。"""

    project_ids = ", ".join(f"'{_uuid(5300 + number)}'" for number in range(1, len(PROJECTS) + 1))
    op.execute(sa.text(f"DELETE FROM sales_project WHERE id IN ({project_ids})"))
    op.execute(sa.text("DELETE FROM organization WHERE id IN (:company4, :company5, :company6)").bindparams(
        company4=_uuid(5004), company5=_uuid(5005), company6=_uuid(5006)
    ))
    op.execute(sa.text("""
        UPDATE organization
        SET customer_status = '潜在客户', industry = '演示行业',
            recent_follow_up_at = NULL, recent_follow_up_content = NULL,
            cooperation_intent = NULL, cooperation_level = NULL,
            attributes = attributes - 'won_customer_demo',
            notes = '纯虚构单位，仅用于同行关联演示'
        WHERE id IN (:company1, :company2, :company3)
    """).bindparams(company1=_uuid(5001), company2=_uuid(5002), company3=_uuid(5003)))
    op.execute(sa.text("UPDATE organization_site SET district = NULL, location = NULL WHERE id IN (:site1, :site2, :site3)").bindparams(
        site1=_uuid(5101), site2=_uuid(5102), site3=_uuid(5103)
    ))
