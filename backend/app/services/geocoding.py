"""高德 Web 服务地理编码：将可信地址写为 AMap 点位，并同步维护 PostGIS 空间坐标。"""

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from math import cos, pi, sin, sqrt
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import urlopen

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.models import AuditLog, GeocodeStatus, OrganizationSite

AMAP_GEOCODE_ENDPOINT = "https://restapi.amap.com/v3/geocode/geo"
AMAP_POI_SEARCH_ENDPOINT = "https://restapi.amap.com/v3/place/text"
# 高德不同版本会用“门牌号”或“门址”表示同一精度；两者都足以安全生成单位 pin。
EXACT_LEVELS = frozenset({"门牌号", "门址", "兴趣点", "道路", "交叉路口", "建筑", "社区"})
_A = 6378245.0
_EE = 0.00669342162296594323


class AmapGeocodeError(RuntimeError):
    """表示不可安全写入数据库的高德地理编码服务错误。"""


@dataclass(frozen=True)
class GeocodeMatch:
    """封装单个高德候选点，保留匹配精度以避免低可信度点进入地图。"""

    longitude: float
    latitude: float
    adcode: str | None
    level: str | None
    formatted_address: str | None = None
    province: str | None = None
    city: str | None = None
    district: str | None = None

    @property
    def is_exact(self) -> bool:
        """仅接受足以代表具体单位地点的匹配等级。"""

        return self.level in EXACT_LEVELS


@dataclass(frozen=True)
class GeocodeRunSummary:
    """汇总一次编码任务的结果，便于 CLI 和后续批次页安全展示。"""

    resolved: int = 0
    low_confidence: int = 0
    failed: int = 0
    deferred: int = 0


def _transform_lat(latitude: float, longitude: float) -> float:
    """计算 GCJ-02 到 WGS84 反算中纬度方向的偏移量。"""

    value = -100.0 + 2.0 * longitude + 3.0 * latitude + 0.2 * latitude * latitude + 0.1 * longitude * latitude + 0.2 * sqrt(abs(longitude))
    value += (20.0 * sin(6.0 * longitude * pi) + 20.0 * sin(2.0 * longitude * pi)) * 2.0 / 3.0
    value += (20.0 * sin(latitude * pi) + 40.0 * sin(latitude / 3.0 * pi)) * 2.0 / 3.0
    return value + (160.0 * sin(latitude / 12.0 * pi) + 320.0 * sin(latitude * pi / 30.0)) * 2.0 / 3.0


def _transform_lng(latitude: float, longitude: float) -> float:
    """计算 GCJ-02 到 WGS84 反算中经度方向的偏移量。"""

    value = 300.0 + longitude + 2.0 * latitude + 0.1 * longitude * longitude + 0.1 * longitude * latitude + 0.1 * sqrt(abs(longitude))
    value += (20.0 * sin(6.0 * longitude * pi) + 20.0 * sin(2.0 * longitude * pi)) * 2.0 / 3.0
    value += (20.0 * sin(longitude * pi) + 40.0 * sin(longitude / 3.0 * pi)) * 2.0 / 3.0
    return value + (150.0 * sin(longitude / 12.0 * pi) + 300.0 * sin(longitude / 30.0 * pi)) * 2.0 / 3.0


def gcj02_to_wgs84(longitude: float, latitude: float) -> tuple[float, float]:
    """将高德返回的 GCJ-02 坐标近似转换为 PostGIS 标准 WGS84 坐标。"""

    if not (72.004 <= longitude <= 137.8347 and 0.8293 <= latitude <= 55.8271):
        return longitude, latitude
    delta_lat = _transform_lat(latitude - 35.0, longitude - 105.0)
    delta_lng = _transform_lng(latitude - 35.0, longitude - 105.0)
    rad_lat = latitude / 180.0 * pi
    magic = 1 - _EE * sin(rad_lat) * sin(rad_lat)
    sqrt_magic = sqrt(magic)
    delta_lat = (delta_lat * 180.0) / ((_A * (1 - _EE)) / (magic * sqrt_magic) * pi)
    delta_lng = (delta_lng * 180.0) / (_A / sqrt_magic * cos(rad_lat) * pi)
    return longitude - delta_lng, latitude - delta_lat


def _request_amap_json(endpoint: str, query: dict[str, str], *, timeout: int = 5) -> dict[str, object]:
    """调用高德 Web 服务并隐藏请求细节，防止日志意外泄露服务端 Key。"""

    settings = get_settings()
    api_key = settings.amap_rest_api_key
    if not api_key:
        raise AmapGeocodeError("未配置高德 Web 服务 Key，无法执行地址编码。")
    request_query = {**query, "key": api_key, "output": "JSON"}
    request_url = f"{settings.amap_service_base_url.rstrip('/')}{urlsplit(endpoint).path}?{urlencode(request_query)}"
    try:
        # 单次请求最多等待五秒，避免少数异常 POI 阻塞低并发队列；超时记录留在待编码而非猜测坐标。
        with urlopen(request_url, timeout=timeout) as response:  # noqa: S310
            payload = json.load(response)
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as error:
        raise AmapGeocodeError("高德地址编码服务暂不可用；本次记录保持待编码。") from error
    if payload.get("status") != "1":
        raise AmapGeocodeError("高德地址编码服务返回异常；本次记录保持待编码。")
    return payload


def _amap_text(value: object) -> str:
    """把高德可能返回的字符串或空数组统一为干净文本。"""

    if isinstance(value, list):
        return "".join(str(item).strip() for item in value if item)
    return value.strip() if isinstance(value, str) else ""


def _amap_full_address(province: str, city: str, district: str, address: str) -> str:
    """拼接 POI 行政区与门址，并去除直辖市等相邻重复片段。"""

    parts = [province, city, district, address]
    return "".join(part for index, part in enumerate(parts) if part and (index == 0 or part != parts[index - 1]))


def search_amap_places(keyword: str, limit: int = 8) -> list[dict[str, str]]:
    """使用服务端 Web 服务 Key 搜索公司地点，避免把 REST Key 暴露给浏览器。"""

    payload = _request_amap_json(AMAP_POI_SEARCH_ENDPOINT, {
        "keywords": keyword.strip(),
        "extensions": "all",
        "offset": str(limit),
        "page": "1",
    }, timeout=15)
    results: list[dict[str, str]] = []
    for raw_poi in payload.get("pois") or []:
        if not isinstance(raw_poi, dict):
            continue
        location = _amap_text(raw_poi.get("location"))
        try:
            longitude_text, latitude_text = location.split(",", maxsplit=1)
            longitude, latitude = float(longitude_text), float(latitude_text)
        except (TypeError, ValueError):
            continue
        if not (72.004 <= longitude <= 137.8347 and 0.8293 <= latitude <= 55.8271):
            continue
        province = _amap_text(raw_poi.get("pname"))
        city = _amap_text(raw_poi.get("cityname")) or province
        district = _amap_text(raw_poi.get("adname"))
        address = _amap_full_address(province, city, district, _amap_text(raw_poi.get("address")))
        name = _amap_text(raw_poi.get("name")) or address
        if not name:
            continue
        results.append({
            "name": name,
            "address": address,
            "province": province,
            "city": city,
            "district": district,
            "amap_adcode": _amap_text(raw_poi.get("adcode")),
            "longitude": f"{longitude:.6f}",
            "latitude": f"{latitude:.6f}",
        })
    return results


def geocode_address(address: str, city: str | None) -> GeocodeMatch | None:
    """请求高德地址编码 API，并返回其原始地址匹配结果。"""

    query = {"address": address}
    if city:
        query["city"] = city
    payload = _request_amap_json(AMAP_GEOCODE_ENDPOINT, query)
    geocodes = payload.get("geocodes") or []
    if not geocodes or not geocodes[0].get("location"):
        return None
    longitude_text, latitude_text = geocodes[0]["location"].split(",", maxsplit=1)
    return GeocodeMatch(
        longitude=float(longitude_text),
        latitude=float(latitude_text),
        adcode=geocodes[0].get("adcode") or None,
        level=geocodes[0].get("level") or None,
        formatted_address=geocodes[0].get("formatted_address") or None,
        province=geocodes[0].get("province") or None,
        city=geocodes[0].get("city") or None,
        district=geocodes[0].get("district") or None,
    )


def _normalized_name(name: str) -> str:
    """将名称压缩为可比较形式，避免空格等展示差异阻碍严格的 POI 名称匹配。"""

    return "".join(character for character in name if character.isalnum())


def _is_verified_poi_name(organization_name: str, poi_name: str) -> bool:
    """允许主名称或校区名称，明确排除附属机构、独立学院等不同法人主体。"""

    normalized_organization = _normalized_name(organization_name)
    normalized_poi = _normalized_name(poi_name)
    if normalized_poi == normalized_organization:
        return True
    suffix = normalized_poi.removeprefix(normalized_organization)
    return bool(suffix) and "校区" in suffix and not any(word in suffix for word in ("医学院", "附属", "城市学院", "研究院"))


def _has_matching_street_number(source_address: str, poi_address: str) -> bool:
    """要求 POI 地址包含原始地址的门牌数字，避免把同校不同校区误写入数据库。"""

    numbers = re.findall(r"\d+", source_address)
    normalized_poi_address = _normalized_name(poi_address)
    return bool(numbers) and all(number in normalized_poi_address for number in numbers)


def _is_name_only_address(source_address: str, organization_name: str) -> bool:
    """识别历史导入的“城市加单位名”粗地址，允许以严格同名主 POI 补齐其缺失门牌。"""

    normalized_address = _normalized_name(source_address)
    normalized_name = _normalized_name(organization_name)
    return bool(normalized_name) and normalized_address.endswith(normalized_name) and not re.search(r"\d", source_address)


def find_exact_organization_poi(name: str, address: str, city: str | None) -> GeocodeMatch | None:
    """只接受同名或同校校区且门牌号一致的 POI，作为低精度地址编码的安全补充。"""

    query = {"keywords": name, "offset": "10", "page": "1", "citylimit": "true"}
    if city:
        query["city"] = city
    payload = _request_amap_json(AMAP_POI_SEARCH_ENDPOINT, query)
    normalized_name = _normalized_name(name)
    name_only_address = _is_name_only_address(address, name)
    campus_fallback: GeocodeMatch | None = None
    for poi in payload.get("pois") or []:
        poi_name = str(poi.get("name") or "")
        poi_address = str(poi.get("address") or "")
        exact_name = _normalized_name(poi_name) == normalized_name
        main_campus_name = _normalized_name(poi_name).removeprefix(normalized_name)
        is_main_campus = bool(main_campus_name) and "主校区" in main_campus_name
        has_verified_address = _has_matching_street_number(address, poi_address)
        if not _is_verified_poi_name(normalized_name, poi_name) or not (has_verified_address or name_only_address):
            continue
        location = poi.get("location")
        if not location:
            continue
        longitude_text, latitude_text = str(location).split(",", maxsplit=1)
        match = GeocodeMatch(
            longitude=float(longitude_text),
            latitude=float(latitude_text),
            adcode=poi.get("adcode") or None,
            level="兴趣点",
            formatted_address=poi_address or None,
            province=poi.get("pname") or None,
            city=poi.get("cityname") or None,
            district=poi.get("adname") or None,
        )
        # 粗地址优先采用学校同名或标注“主校区”的 POI；高德无此命名时才回退到同校其他校区。
        if exact_name or is_main_campus or not name_only_address:
            return match
        campus_fallback = campus_fallback or match
    return campus_fallback


def geocode_pending_sites(db: Session, limit: int, actor_username: str) -> GeocodeRunSummary:
    """编码待处理地点；低精度地址仅可由同名 POI 精确校验后生成 pin。"""

    sites = db.scalars(
        select(OrganizationSite)
        .options(joinedload(OrganizationSite.organization))
        .where(OrganizationSite.geocode_status.in_((GeocodeStatus.pending, GeocodeStatus.low_confidence)))
        .where(OrganizationSite.address.is_not(None))
        .order_by(OrganizationSite.updated_at, OrganizationSite.created_at)
        .limit(limit)
    ).unique().all()
    resolved = low_confidence = failed = deferred = 0
    for site in sites:
        address = site.address or site.raw_address
        if not address:
            continue
        poi_verified = False
        # “城市+单位名”不是可用门址，直接查询同名主 POI 可避免一次慢速且无意义的地址编码请求。
        if _is_name_only_address(address, site.organization.name):
            try:
                match = find_exact_organization_poi(site.organization.name, address, site.city)
            except AmapGeocodeError:
                deferred += 1
                site.updated_at = datetime.now(timezone.utc)
                db.commit()
                continue
            poi_verified = match is not None
        else:
            try:
                match = geocode_address(address, site.city)
            except AmapGeocodeError:
                deferred += 1
                site.updated_at = datetime.now(timezone.utc)
                db.commit()
                continue
            if match is None or not match.is_exact:
                try:
                    poi_match = find_exact_organization_poi(site.organization.name, address, site.city)
                except AmapGeocodeError:
                    poi_match = None
                    deferred += 1
                if poi_match:
                    match = poi_match
                    poi_verified = True
        if match is None:
            site.geocode_status = GeocodeStatus.failed
            site.geocode_confidence = 0
            failed += 1
        elif not match.is_exact:
            site.geocode_status = GeocodeStatus.low_confidence
            site.geocode_confidence = 40
            low_confidence += 1
        else:
            wgs_longitude, wgs_latitude = gcj02_to_wgs84(match.longitude, match.latitude)
            site.longitude = match.longitude
            site.latitude = match.latitude
            site.location = WKTElement(f"POINT({wgs_longitude} {wgs_latitude})", srid=4326)
            site.amap_adcode = match.adcode
            # 仅在旧数据没有细化地址时写回 POI 地址；已有人工地址永远不被外部服务覆盖。
            if _is_name_only_address(address, site.organization.name) and match.formatted_address:
                site.address = f"{match.city or site.city or ''}{match.formatted_address}"
            site.province = site.province or match.province
            site.city = site.city or match.city
            site.district = site.district or match.district
            site.geocode_status = GeocodeStatus.resolved
            site.geocode_confidence = 90
            resolved += 1
            db.add(AuditLog(organization_id=site.organization_id, actor_username=actor_username, action="高德地址编码", detail={"地点": site.site_name or "主地点", "匹配等级": match.level, "POI 名称校验": poi_verified}))
        # 每条记录独立提交：低并发外部调用可被中断，但已验证坐标不得因后续慢请求而回滚。
        db.commit()
    return GeocodeRunSummary(resolved=resolved, low_confidence=low_confidence, failed=failed, deferred=deferred)
