"""官方来源获取服务：用 Python 标准库为各类名单导入提供低并发、重试和顺序保留的网络读取。"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from http.client import IncompleteRead
from time import sleep
from typing import TypeVar
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import get_settings

PageResult = TypeVar("PageResult")


@dataclass(frozen=True)
class OfficialSourceFetchPolicy:
    """官方站点请求边界；默认低并发，避免名单采集对主管部门站点造成突发压力。"""

    max_parallel_requests: int = 4
    max_request_attempts: int = 5
    request_timeout_seconds: int = 30

    def __post_init__(self) -> None:
        """在命令启动前拒绝不安全的并发、重试和超时设置，避免采集任务失控。"""

        if not 1 <= self.max_parallel_requests <= 8:
            raise ValueError("官方来源并发数必须在 1 到 8 之间")
        if not 1 <= self.max_request_attempts <= 10:
            raise ValueError("官方来源请求次数必须在 1 到 10 之间")
        if not 5 <= self.request_timeout_seconds <= 120:
            raise ValueError("官方来源请求超时必须在 5 到 120 秒之间")


def get_official_source_fetch_policy() -> OfficialSourceFetchPolicy:
    """从统一 Settings 读取可调整的采集参数，使未来单位导入沿用相同安全默认值。"""

    settings = get_settings()
    return OfficialSourceFetchPolicy(
        max_parallel_requests=settings.official_import_max_parallel_requests,
        max_request_attempts=settings.official_import_max_request_attempts,
        request_timeout_seconds=settings.official_import_request_timeout_seconds,
    )


def decode_official_response(payload: bytes) -> str:
    """兼容政府旧页面常见的 UTF-8 与 GB18030 编码，避免中文名称或地址损坏。"""

    for encoding in ("utf-8", "gb18030"):
        try:
            return payload.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("官方来源响应无法按 UTF-8 或 GB18030 解码")


def fetch_official_text(
    url: str,
    *,
    policy: OfficialSourceFetchPolicy,
    opener: Callable[..., object] = urlopen,
    sleep_function: Callable[[float], None] = sleep,
) -> str:
    """读取一个固定官方 URL；仅对临时网关和传输错误进行有限线性退避重试。"""

    request = Request(url, headers={"User-Agent": "UniteSalesDirectoryImporter/1.0 (+internal-data-review)"})
    for attempt in range(1, policy.max_request_attempts + 1):
        try:
            with opener(request, timeout=policy.request_timeout_seconds) as response:  # type: ignore[union-attr]
                return decode_official_response(response.read())  # type: ignore[union-attr]
        except (HTTPError, URLError, TimeoutError, IncompleteRead) as error:
            if attempt == policy.max_request_attempts:
                raise RuntimeError(f"官方来源连续 {policy.max_request_attempts} 次请求失败：{url}") from error
            sleep_function(attempt)
    raise RuntimeError("官方来源重试流程意外结束")


def fetch_ordered_pages(
    page_numbers: Iterable[int],
    *,
    fetch_page: Callable[[int], PageResult],
    policy: OfficialSourceFetchPolicy,
) -> list[PageResult]:
    """在安全并发上限内获取分页结果，并按页码顺序返回以保证原始目录可追溯。"""

    with ThreadPoolExecutor(max_workers=policy.max_parallel_requests) as executor:
        return list(executor.map(fetch_page, page_numbers))
