"""教育部普通高校底表导入：使用标准库抓取官方查询接口并写入可追溯的筛选队列。"""

from __future__ import annotations

import math
import re
from functools import partial
from html.parser import HTMLParser

from app.database import SessionLocal
from app.services.official_sources import OfficialSourceFetchPolicy, fetch_official_text, fetch_ordered_pages, get_official_source_fetch_policy
from app.services.imports import OfficialUniversityDirectoryRow, import_moe_university_directory

OFFICIAL_DIRECTORY_URL = "https://www.moe.gov.cn/jyb_xxgk/s5743/s5744/202606/t20260618_1441074.html"
OFFICIAL_QUERY_BASE_URL = "https://hudong.moe.gov.cn/school/wcmdata"
DIRECTORY_LIST_ID = "10000101"
DIRECTORY_PAGE_SIZE = 20
DIRECTORY_BATCH_NAME = "2026-06 教育部全国普通高校底表"


class DirectoryTableParser(HTMLParser):
    """解析教育部查询接口返回的表格片段，仅接受完整的七列表格行。"""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[list[str]] = []
        self._current_row: list[str] | None = None
        self._current_cell: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        """追踪 tr/td 层级，忽略接口片段中的样式属性与其他节点。"""

        if tag == "tr":
            self._current_row = []
        elif tag == "td" and self._current_row is not None:
            self._current_cell = []

    def handle_data(self, data: str) -> None:
        """累积单元格文本，保留学校名称和主管部门中的中文字符。"""

        if self._current_cell is not None:
            self._current_cell.append(data)

    def handle_endtag(self, tag: str) -> None:
        """在单元格和行结束时提交文本，避免依赖第三方 HTML 解析库。"""

        if tag == "td" and self._current_cell is not None and self._current_row is not None:
            self._current_row.append("".join(self._current_cell).strip())
            self._current_cell = None
        elif tag == "tr" and self._current_row is not None:
            if len(self._current_row) == 7:
                self.rows.append(self._current_row)
            self._current_row = None


def request_official_fragment(path: str, *, policy: OfficialSourceFetchPolicy) -> str:
    """通过共享官方来源服务读取教育部接口片段，使网络边界可由 .env 统一调整。"""

    return fetch_official_text(f"{OFFICIAL_QUERY_BASE_URL}/{path}", policy=policy)


def parse_directory_rows(fragment: str) -> list[OfficialUniversityDirectoryRow]:
    """将一页官方 HTML 表格转换为强类型目录行，保证字段顺序可被测试。"""

    parser = DirectoryTableParser()
    parser.feed(fragment)
    return [
        OfficialUniversityDirectoryRow(
            sequence=int(cells[0]),
            name=cells[1],
            institution_code=cells[2],
            supervising_department=cells[3],
            locality=cells[4],
            education_level=cells[5],
            remark=cells[6],
        )
        for cells in parser.rows
    ]


def fetch_result_count(*, policy: OfficialSourceFetchPolicy) -> int:
    """读取教育部接口公布的总条数，作为完整性校验而非写死的业务数据。"""

    fragment = request_official_fragment(f"getCounts.jsp?listid={DIRECTORY_LIST_ID}&page=1", policy=policy)
    match = re.search(r"(\d+)\s*条结果", fragment)
    if not match:
        raise ValueError("教育部接口未返回高校目录总条数")
    return int(match.group(1))


def fetch_directory_page(page: int, *, policy: OfficialSourceFetchPolicy) -> str:
    """读取指定页的官方表格片段，使低并发调度不复制 URL 拼接逻辑。"""

    return request_official_fragment(f"getDataIndex.jsp?listid={DIRECTORY_LIST_ID}&page={page}", policy=policy)


def fetch_moe_university_directory(*, policy: OfficialSourceFetchPolicy | None = None) -> list[OfficialUniversityDirectoryRow]:
    """按共享低并发策略分页获取教育部目录，并在入库前校验数量和学校标识码的唯一性。"""

    effective_policy = policy or get_official_source_fetch_policy()
    result_count = fetch_result_count(policy=effective_policy)
    all_rows: list[OfficialUniversityDirectoryRow] = []
    total_pages = math.ceil(result_count / DIRECTORY_PAGE_SIZE)
    fragments = fetch_ordered_pages(
        range(1, total_pages + 1),
        fetch_page=partial(fetch_directory_page, policy=effective_policy),
        policy=effective_policy,
    )
    for page, fragment in enumerate(fragments, start=1):
        all_rows.extend(parse_directory_rows(fragment))
        if page % 20 == 0 or page == total_pages:
            print(f"已读取教育部目录第 {page}/{total_pages} 页", flush=True)

    if len(all_rows) != result_count:
        raise ValueError(f"教育部目录条数不完整：接口公布 {result_count} 条，实际获取 {len(all_rows)} 条")
    codes = [row.institution_code for row in all_rows]
    if len(codes) != len(set(codes)):
        raise ValueError("教育部目录出现重复学校标识码，已停止导入")
    return all_rows


def main() -> None:
    """创建 2026 年教育部普通高校底表批次；重复运行时复用已有批次，不覆盖人工数据。"""

    rows = fetch_moe_university_directory()
    with SessionLocal() as db:
        batch = import_moe_university_directory(
            db,
            batch_name=DIRECTORY_BATCH_NAME,
            source_scope="教育部 2026 年全国普通高等学校名单（仅普通高校；不含成人高校及港澳台高校）。",
            source_url=OFFICIAL_DIRECTORY_URL,
            rows=rows,
        )
    print(f"教育部普通高校底表完成：{batch.total_rows} 条，已有正式单位 {batch.duplicate_rows} 条，批次 ID：{batch.id}")


if __name__ == "__main__":
    main()
