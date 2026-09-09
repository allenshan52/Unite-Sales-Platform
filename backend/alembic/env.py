"""Alembic 迁移环境：读取 ORM 元数据与安全配置，生成/执行 PostGIS 迁移。"""

from logging.config import fileConfig

from alembic import context
from geoalchemy2 import alembic_helpers
from sqlalchemy import engine_from_config, pool, text

from app.config import get_settings
from app.database import Base
from app import models  # noqa: F401  # 导入模型以注册全部 metadata。

config = context.config
config.set_main_option("sqlalchemy.url", get_settings().database_url)
if config.config_file_name is not None:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def _include_non_extension_object(extension_relation_names: set[str]):
    """生成 Alembic 对象过滤器，仅排除 PostgreSQL 明确归属于扩展的表和索引。"""

    def include_object(obj, name, object_type, reflected, compare_to):
        """保留全部业务对象，同时忽略 PostGIS/TIGER 自带关系造成的伪漂移。"""

        relation = obj.table if object_type == "index" else obj
        relation_name = getattr(relation, "name", name)
        application_relation_names = {table.name for table in target_metadata.tables.values()}
        if reflected and relation_name in extension_relation_names and relation_name not in application_relation_names:
            return False
        return alembic_helpers.include_object(obj, name, object_type, reflected, compare_to)

    return include_object


def run_migrations_offline() -> None:
    """在不连接数据库时生成 SQL，便于部署审查。"""

    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=alembic_helpers.include_object,
        process_revision_directives=alembic_helpers.writer,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """使用短生命周期迁移连接执行版本升级。"""

    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        extension_relation_names = set(connection.scalars(text("""
            SELECT relation.relname
            FROM pg_depend AS dependency
            JOIN pg_extension AS extension ON extension.oid = dependency.refobjid
            JOIN pg_class AS relation ON relation.oid = dependency.objid
            WHERE dependency.deptype = 'e'
            UNION
            SELECT relation.relname
            FROM pg_extension AS extension
            CROSS JOIN LATERAL unnest(extension.extconfig) AS config_relation(oid)
            JOIN pg_class AS relation ON relation.oid = config_relation.oid
        """)).all())
        # SQLAlchemy 2 的只读查询也会自动开启事务；先结束它，避免包住迁移事务后在连接关闭时回滚。
        connection.commit()
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=_include_non_extension_object(extension_relation_names),
            process_revision_directives=alembic_helpers.writer,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
