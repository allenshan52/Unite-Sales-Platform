"""教育部高校底表导入测试：验证目录解析、体育分流及正式单位回写，不访问外部网络或真实数据库。"""

from uuid import uuid4

from app.cli.import_moe_university_directory import parse_directory_rows
from app.models import ImportBatch, ImportRow, Organization
from app.services.imports import (
    UniversityCandidate,
    import_university_candidates,
    is_sports_higher_education,
    university_directory_screening_status,
)
from app.services.organizations import normalize_name


class _ScalarRows:
    """为离线测试返回预置底表行，避免连接真实 PostgreSQL。"""

    def __init__(self, rows: list[ImportRow]) -> None:
        self._rows = rows

    def all(self) -> list[ImportRow]:
        """模拟 SQLAlchemy scalar result 的 all 接口。"""

        return self._rows


class _FakeImportSession:
    """模拟首次批次中的最小 Session 行为，以核验重复单位仍会关联教育部底表。"""

    def __init__(self, organization: Organization, pending_row: ImportRow) -> None:
        self._scalar_values = iter((None, organization))
        self._pending_row = pending_row
        self.added: list[object] = []

    def scalar(self, _statement: object) -> object | None:
        """依次返回无既有批次和已有正式单位。"""

        return next(self._scalar_values)

    def scalars(self, _statement: object) -> _ScalarRows:
        """返回等待回写的教育部目录行。"""

        return _ScalarRows([self._pending_row])

    def add(self, value: object) -> None:
        """记录待写对象，供 flush 设置数据库默认值。"""

        self.added.append(value)

    def flush(self) -> None:
        """模拟数据库为批次填充主键和计数默认值。"""

        for value in self.added:
            if isinstance(value, ImportBatch) and value.id is None:
                value.id = uuid4()
                value.created_rows = 0
                value.duplicate_rows = 0
                value.failed_rows = 0

    def commit(self) -> None:
        """离线测试无需持久化。"""

    def refresh(self, _value: object) -> None:
        """离线测试对象已保留最终状态。"""


def test_parse_directory_rows_preserves_official_columns() -> None:
    """官方接口表格的七列必须完整进入筛选底表，避免错位造成错误单位或学校标识码。"""

    rows = parse_directory_rows(
        "<tr><td>1</td><td>北京体育大学</td><td>4111010043</td><td>国家体育总局</td><td>北京市</td><td>本科</td><td></td></tr>"
    )
    assert rows[0].name == "北京体育大学"
    assert rows[0].institution_code == "4111010043"
    assert rows[0].education_level == "本科"


def test_sports_higher_education_is_routed_to_exception_evidence() -> None:
    """体育高校需要保留但不能跳过取证，因此先进入体育例外证据队列。"""

    row = parse_directory_rows(
        "<tr><td>1</td><td>北京体育大学</td><td>4111010043</td><td>国家体育总局</td><td>北京市</td><td>本科</td><td></td></tr>"
    )[0]
    assert is_sports_higher_education(row) is True
    assert university_directory_screening_status(row) == "待体育例外证据"


def test_first_import_links_existing_organization_back_to_directory_row() -> None:
    """首次创建专批遇到既有单位时，也必须回写底表去向而不是只标记重复。"""

    normalized_name = normalize_name("中国人民公安大学")
    organization = Organization(id=uuid4(), name="中国人民公安大学", normalized_name=normalized_name)
    pending_row = ImportRow(normalized_name=normalized_name, processing_status="本科待官网证据（批量源受限）")
    db = _FakeImportSession(organization, pending_row)

    batch = import_university_candidates(
        db,  # type: ignore[arg-type]
        batch_name="公安本科离线测试批",
        source_scope="离线测试",
        source_url="https://www.moe.gov.cn/example.html",
        candidates=(
            UniversityCandidate(
                name="中国人民公安大学",
                website="https://www.ppsuc.edu.cn/",
                province="北京市",
                city="北京市",
                district=None,
                address="北京市中国人民公安大学",
                evidence_title="教育部名录",
                evidence_url="https://www.moe.gov.cn/example.html",
                evidence_excerpt="列为本科院校。",
            ),
        ),
        actor_username="test",
    )

    assert batch.duplicate_rows == 1
    assert batch.created_rows == 0
    assert pending_row.organization_id == organization.id
    assert pending_row.processing_status == "已纳入正式单位（待核验/待编码）"
