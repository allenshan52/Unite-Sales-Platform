"""为同行成交记录补充产品字段，并扩充可重复的虚构演示数据。"""

import sqlalchemy as sa
from alembic import op

revision = "20260824_0020"
down_revision = "20260824_0019"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """新增可空产品字段，并仅对明确标记的虚构成交记录确定性补值。"""

    op.add_column("competitor_deal", sa.Column("product_name", sa.String(255)))
    op.add_column("competitor_deal", sa.Column("specification_model", sa.String(255)))
    op.add_column("competitor_deal", sa.Column("product_image_url", sa.String(1000)))
    op.add_column("competitor_deal", sa.Column("unit_price", sa.Numeric(14, 2)))
    op.create_check_constraint(
        "ck_competitor_deal_positive_unit_price",
        "competitor_deal",
        "unit_price IS NULL OR unit_price > 0",
    )
    op.execute(
        """
        WITH demo_deals AS (
            SELECT id, row_number() OVER (ORDER BY id) AS demo_number
            FROM competitor_deal
            WHERE notes = '纯虚构交易金额'
        )
        UPDATE competitor_deal AS deal
        SET
            product_name = (ARRAY[
                '台式气相色谱仪', '全自动样品前处理系统', 'ICP-MS 质谱仪',
                '高效液相色谱仪', '环境监测分析仪', '实验室纯水系统'
            ])[((demo.demo_number - 1) % 6) + 1],
            specification_model = (ARRAY[
                'GC-9860 Plus', 'AutoPrep X8', 'ICP-MS 7900D',
                'LC-3200', 'ECO-500', 'UPW-20'
            ])[((demo.demo_number - 1) % 6) + 1],
            product_image_url = CASE
                WHEN demo.demo_number % 3 = 0 THEN NULL
                ELSE (ARRAY[
                    '/cases/jiangsu-lab.webp', '/cases/zhejiang-pharma.webp',
                    '/cases/guangdong-environment.webp', '/cases/chongqing-biotech.webp'
                ])[((demo.demo_number - 1) % 4) + 1]
            END,
            unit_price = round(deal.amount / (2 + ((demo.demo_number - 1) % 8)), 2)
        FROM demo_deals AS demo
        WHERE deal.id = demo.id
        """
    )


def downgrade() -> None:
    """回退时仅移除本次新增产品字段，不改动既有项目与来源信息。"""

    op.drop_constraint("ck_competitor_deal_positive_unit_price", "competitor_deal", type_="check")
    op.drop_column("competitor_deal", "unit_price")
    op.drop_column("competitor_deal", "product_image_url")
    op.drop_column("competitor_deal", "specification_model")
    op.drop_column("competitor_deal", "product_name")
