"""官方来源获取服务测试：验证编码、重试、并发边界和页序，不建立真实网络连接。"""

from http.client import IncompleteRead

import pytest

from app.services.official_sources import OfficialSourceFetchPolicy, decode_official_response, fetch_official_text, fetch_ordered_pages


def test_official_response_decoder_accepts_legacy_chinese_encoding() -> None:
    """政府旧页面可能使用 GB18030，通用服务必须保留中文单位字段。"""

    assert decode_official_response("北京体育大学".encode("gb18030")) == "北京体育大学"


def test_official_request_retries_incomplete_response() -> None:
    """分页流中断时应重试固定来源，避免将瞬时网络故障误判为名单不完整。"""

    attempts = 0

    def fake_opener(*_args: object, **_kwargs: object) -> object:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise IncompleteRead(b"", 20)
        return _FakeResponse(b"<tr><td>1</td></tr>")

    assert fetch_official_text(
        "https://example.test/official-directory",
        policy=OfficialSourceFetchPolicy(max_request_attempts=2),
        opener=fake_opener,
        sleep_function=lambda _seconds: None,
    ) == "<tr><td>1</td></tr>"
    assert attempts == 2


def test_ordered_pages_keeps_source_order_under_low_concurrency() -> None:
    """低并发提速不能改变页序，否则原始行的可追溯顺序会被破坏。"""

    pages = fetch_ordered_pages(
        [3, 1, 2],
        fetch_page=lambda page: f"page-{page}",
        policy=OfficialSourceFetchPolicy(max_parallel_requests=2),
    )
    assert pages == ["page-3", "page-1", "page-2"]


@pytest.mark.parametrize("parallel_requests", [0, 9])
def test_fetch_policy_rejects_unsafe_parallelism(parallel_requests: int) -> None:
    """并发数超出 1–8 必须在启动前失败，保护官方站点和本地导入任务。"""

    with pytest.raises(ValueError, match="并发数"):
        OfficialSourceFetchPolicy(max_parallel_requests=parallel_requests)


class _FakeResponse:
    """为网络重试测试提供最小响应上下文，不建立外部连接。"""

    def __init__(self, payload: bytes) -> None:
        self.payload = payload

    def __enter__(self) -> "_FakeResponse":
        """模拟 urlopen 返回的可关闭响应对象。"""

        return self

    def __exit__(self, *_args: object) -> None:
        """测试对象没有网络资源，保留与真实响应一致的上下文接口。"""

    def read(self) -> bytes:
        """返回预设片段，供共享解码与重试路径验证。"""

        return self.payload
