"""为每名销售增加一个可直接绘制的高德覆盖圆，并回填纯虚构演示参数。"""

import sqlalchemy as sa

from alembic import op

revision = "20260813_0011"
down_revision = "20260813_0010"
branch_labels = None
depends_on = None


# 圆参数仅用于演示地图表达，不代表真实人员部署或行政区域边界。
DEMO_COVERAGE_CIRCLES = (
    ("DEMO-S001", 120.35, 31.65, 330),
    ("DEMO-S002", 124.70, 43.20, 500),
    ("DEMO-S003", 113.50, 22.50, 400),
    ("DEMO-S004", 104.70, 27.80, 480),
    ("DEMO-S005", 113.40, 29.40, 550),
    ("DEMO-S006", 119.80, 29.90, 380),
)


def upgrade() -> None:
    """新增非空覆盖圆字段，并按稳定员工编号回填当前六名演示销售。"""

    op.add_column("salesperson", sa.Column("coverage_center_longitude", sa.Float(), nullable=False, server_default="104.1"))
    op.add_column("salesperson", sa.Column("coverage_center_latitude", sa.Float(), nullable=False, server_default="35.6"))
    op.add_column("salesperson", sa.Column("coverage_radius_km", sa.Integer(), nullable=False, server_default="300"))
    connection = op.get_bind()
    for employee_code, longitude, latitude, radius_km in DEMO_COVERAGE_CIRCLES:
        connection.execute(
            sa.text(
                "UPDATE salesperson SET coverage_center_longitude = :longitude, "
                "coverage_center_latitude = :latitude, coverage_radius_km = :radius_km "
                "WHERE employee_code = :employee_code"
            ),
            {"employee_code": employee_code, "longitude": longitude, "latitude": latitude, "radius_km": radius_km},
        )
    op.alter_column("salesperson", "coverage_center_longitude", server_default=None)
    op.alter_column("salesperson", "coverage_center_latitude", server_default=None)
    op.alter_column("salesperson", "coverage_radius_km", server_default=None)
    op.create_check_constraint(
        "ck_salesperson_coverage_center_gcj02_bounds",
        "salesperson",
        "coverage_center_longitude BETWEEN 72.004 AND 137.8347 "
        "AND coverage_center_latitude BETWEEN 0.8293 AND 55.8271",
    )
    op.create_check_constraint(
        "ck_salesperson_coverage_radius_km",
        "salesperson",
        "coverage_radius_km BETWEEN 1 AND 2000",
    )


def downgrade() -> None:
    """移除销售覆盖圆参数，保留原有城市覆盖和人效数据。"""

    op.drop_constraint("ck_salesperson_coverage_radius_km", "salesperson", type_="check")
    op.drop_constraint("ck_salesperson_coverage_center_gcj02_bounds", "salesperson", type_="check")
    op.drop_column("salesperson", "coverage_radius_km")
    op.drop_column("salesperson", "coverage_center_latitude")
    op.drop_column("salesperson", "coverage_center_longitude")
