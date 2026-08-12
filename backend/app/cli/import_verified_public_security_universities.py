"""导入公安/公共安全本科专批：按教育部官方目录全量纳入并排队定位主校区。"""

from dataclasses import dataclass

from app.database import SessionLocal
from app.models import EvidenceKind
from app.services.imports import UniversityCandidate, import_university_candidates


MOE_2026_UNIVERSITY_DIRECTORY = (
    "https://www.moe.gov.cn/jyb_xxgk/s5743/s5744/202606/t20260618_1441074.html"
)


@dataclass(frozen=True)
class PublicSecurityUniversitySeed:
    """保存公安本科院校的目录身份、官网和主校区定位输入，避免把专科警校混入本批。"""

    name: str
    province: str
    city: str
    website: str
    category: str = "公安警察"


# 教育部 2026 普通高校名录中名称明确属于公安、警察、刑事、司法警官或消防救援的本科院校。
VERIFIED_PUBLIC_SECURITY_UNIVERSITIES = (
    PublicSecurityUniversitySeed("上海公安学院", "上海市", "上海市", "https://www.shpc.edu.cn/"),
    PublicSecurityUniversitySeed("新疆警察学院", "新疆维吾尔自治区", "乌鲁木齐市", "https://www.xjpc.edu.cn/"),
    PublicSecurityUniversitySeed("中央司法警官学院", "河北省", "保定市", "https://www.cicp.edu.cn/", "司法警官"),
    PublicSecurityUniversitySeed("甘肃警察学院", "甘肃省", "兰州市", "https://www.gsjcxy.edu.cn/"),
    PublicSecurityUniversitySeed("中国人民公安大学", "北京市", "北京市", "https://www.ppsuc.edu.cn/"),
    PublicSecurityUniversitySeed("中国消防救援学院", "北京市", "北京市", "https://www.cfri.edu.cn/", "消防救援"),
    PublicSecurityUniversitySeed("北京警察学院", "北京市", "北京市", "https://www.bjpc.edu.cn/"),
    PublicSecurityUniversitySeed("南京警察学院", "江苏省", "南京市", "https://www.njpu.edu.cn/"),
    PublicSecurityUniversitySeed("江苏警官学院", "江苏省", "南京市", "https://www.jspi.cn/"),
    PublicSecurityUniversitySeed("广西警察学院", "广西壮族自治区", "南宁市", "https://www.gxjcxy.com/"),
    PublicSecurityUniversitySeed("江西警察学院", "江西省", "南昌市", "https://www.jxga.edu.cn/"),
    PublicSecurityUniversitySeed("安徽公安学院", "安徽省", "合肥市", "https://gaxy.ahpc.edu.cn/"),
    PublicSecurityUniversitySeed("内蒙古警察学院", "内蒙古自治区", "呼和浩特市", "https://www.impc.edu.cn/"),
    PublicSecurityUniversitySeed("辽宁警察学院", "辽宁省", "大连市", "https://www.lnpc.cn/"),
    PublicSecurityUniversitySeed("天津警察学院", "天津市", "天津市", "https://www.tjjingyuan.cn/"),
    PublicSecurityUniversitySeed("山西警察学院", "山西省", "太原市", "https://www.sxpc.edu.cn/"),
    PublicSecurityUniversitySeed("广东警官学院", "广东省", "广州市", "https://www.gdppla.edu.cn/"),
    PublicSecurityUniversitySeed("中国人民警察大学", "河北省", "廊坊市", "https://www.cppu.edu.cn/"),
    PublicSecurityUniversitySeed("云南警官学院", "云南省", "昆明市", "https://www.ynpc.edu.cn/"),
    PublicSecurityUniversitySeed("浙江警察学院", "浙江省", "杭州市", "https://www.zjjcxy.cn/"),
    PublicSecurityUniversitySeed("湖北警官学院", "湖北省", "武汉市", "https://www.hbpa.edu.cn/"),
    PublicSecurityUniversitySeed("中国刑事警察学院", "辽宁省", "沈阳市", "https://www.cipuc.edu.cn/", "刑事警察"),
    PublicSecurityUniversitySeed("四川警察学院", "四川省", "泸州市", "https://www.scpolicec.edu.cn/"),
    PublicSecurityUniversitySeed("山东警察学院", "山东省", "济南市", "https://www.sdpc.edu.cn/"),
    PublicSecurityUniversitySeed("海南警察学院", "海南省", "海口市", "https://www.hipolice.edu.cn/"),
    PublicSecurityUniversitySeed("福建警察学院", "福建省", "福州市", "https://www.fjpsc.edu.cn/"),
    PublicSecurityUniversitySeed("陕西警察学院", "陕西省", "西安市", "https://www.snpc.edu.cn/"),
    PublicSecurityUniversitySeed("贵州警察学院", "贵州省", "贵阳市", "https://www.gzjgxy.cn/"),
    PublicSecurityUniversitySeed("河南警察学院", "河南省", "郑州市", "https://www.hnp.edu.cn/"),
    PublicSecurityUniversitySeed("郑州警察学院", "河南省", "郑州市", "https://www.rpc.edu.cn/"),
    PublicSecurityUniversitySeed("重庆警察学院", "重庆市", "重庆市", "https://www.cqpc.edu.cn/"),
    PublicSecurityUniversitySeed("吉林警察学院", "吉林省", "长春市", "https://www.jljcxy.com/"),
    PublicSecurityUniversitySeed("湖南警察学院", "湖南省", "长沙市", "https://www.hnpolice.com/"),
)


# 新升本或同城多校区院校使用公开主校区地址，其余由“城市+校名”命中高德官方 POI。
OFFICIAL_MAIN_CAMPUS_ADDRESSES = {
    "中央司法警官学院": "河北省保定市莲池区七一中路103号",
    "甘肃警察学院": "甘肃省兰州市皋兰县北辰南路1717号",
    "南京警察学院": "江苏省南京市栖霞区文澜路28号",
    "安徽公安学院": "安徽省合肥市巢湖市半岛生态科学城治中路1号",
    "内蒙古警察学院": "内蒙古自治区呼和浩特市新城区兴安北路11号",
    "天津警察学院": "天津市西青区精武镇陈台子路88号",
    "中国人民警察大学": "河北省廊坊市安次区西昌路220号",
    "中国刑事警察学院": "辽宁省沈阳市皇姑区塔湾街83号",
    "四川警察学院": "四川省泸州市江阳区龙透关路186号",
    "海南警察学院": "海南省海口市秀英区定海大道1号",
    "郑州警察学院": "河南省郑州市金水区农业路31号",
}


DEFERRED_PUBLIC_SECURITY_COLLEGES = (
    "新疆司法警官职业学院", "江苏司法警官职业学院", "江西司法警官职业学院", "安徽公安职业学院",
    "安徽警官职业学院", "黑龙江公安警官职业学院", "黑龙江司法警官职业学院", "山西警官职业学院",
    "广东司法警官职业学院", "四川司法警官职业学院", "西藏警官高等专科学校", "云南司法警官职业学院",
    "公安消防部队高等专科学校", "浙江警官职业学院", "武汉警官职业学院", "山东司法警官职业学院",
    "河北公安警察职业学院", "青海警官职业学院", "河北司法警官职业学院", "河南司法警官职业学院",
    "宁夏警官职业学院", "吉林司法警官职业学院", "湖南司法警官职业学院",
)


def _inclusion_reason(category: str) -> str:
    """按院校业务类别生成可审核的纳入理由，说明全量规则及仪器合作场景。"""

    if category == "消防救援":
        return "教育部2026普通本科高校；公共安全单位全量纳入，存在火灾调查、燃烧分析、消防材料与安全检测业务机会。"
    if category == "司法警官":
        return "教育部2026普通本科高校；司法警官单位全量纳入，存在司法鉴定、禁毒、监所安全与数据警务技术业务机会。"
    if category == "刑事警察":
        return "教育部2026普通本科高校；公安单位全量纳入，存在刑事科学技术、物证鉴定、毒物与痕迹检验业务机会。"
    return "教育部2026普通本科高校；公安/警察院校按业务规则全量纳入，存在刑事科学技术、物证鉴定与检验检测业务机会。"


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把 33 所本科公安院校转成正式候选，并把教育部名录标记为官方目录证据。"""

    assert len(VERIFIED_PUBLIC_SECURITY_UNIVERSITIES) == 33
    assert len({seed.name for seed in VERIFIED_PUBLIC_SECURITY_UNIVERSITIES}) == 33
    return tuple(
        UniversityCandidate(
            name=seed.name,
            website=seed.website,
            province=seed.province,
            city=seed.city,
            district=None,
            address=OFFICIAL_MAIN_CAMPUS_ADDRESSES.get(seed.name, f"{seed.city}{seed.name}"),
            evidence_title="教育部2026年全国普通高等学校名单",
            evidence_url=MOE_2026_UNIVERSITY_DIRECTORY,
            evidence_excerpt=f"教育部2026年全国普通高等学校名单将{seed.name}列为本科院校。",
            evidence_kind=EvidenceKind.official_directory,
            inclusion_reason=_inclusion_reason(seed.category),
            tags=("高校", "公安公共安全本科", "教育部官方名录", "公安高校全量批"),
        )
        for seed in VERIFIED_PUBLIC_SECURITY_UNIVERSITIES
    )


def main() -> None:
    """幂等创建公安本科专批；既有单位只补目录关联，不覆盖人工档案。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 公安公共安全本科院校专批",
            source_scope=(
                "教育部2026全国普通高校名单中的公办本科公安、警察、刑事、司法警官及消防救援院校；"
                "按公安/公共安全单位全量规则纳入，专科和高职警校留待后续专批。"
            ),
            source_url=MOE_2026_UNIVERSITY_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-public-security-university-import",
        )
    print(
        f"公安公共安全本科专批完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
