"""新增“双一流”高校导入：保存逐校官网专业证据，并交由低并发高德队列定位主校区。"""

from dataclasses import dataclass

from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


MOE_DOUBLE_FIRST_CLASS_DIRECTORY = "https://www.moe.gov.cn/srcsite/A22/s7065/202202/t20220211_598710.html"


@dataclass(frozen=True)
class VerifiedDoubleFirstClassSeed:
    """描述一所已通过官网生化环材/医药/公安技术证据核验的新增“双一流”高校。"""

    name: str
    province: str
    city: str
    website: str
    evidence_title: str
    evidence_url: str
    evidence_excerpt: str
    inclusion_reason: str


@dataclass(frozen=True)
class ExcludedDoubleFirstClassSeed:
    """保留不入库高校及排除原因，使第二轮名单差集的筛选结论可以复核。"""

    name: str
    reason: str


# 31 所新增建设高校逐校核验后有 25 所符合；985/211 和体育院校已由既有批次覆盖。
VERIFIED_DOUBLE_FIRST_CLASS_UNIVERSITIES = (
    VerifiedDoubleFirstClassSeed(
        "北京协和医学院", "北京市", "北京市", "https://www.pumc.edu.cn/",
        "北京协和医学院重点学科",
        "https://www.pumc.edu.cn/jyjx/zdxk/index.htm",
        "官网列有生物学、药学、基础医学和生物医学工程等学科。",
        "新增双一流高校；具有生物、药学及生物医学工程相关教学科研方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "中国科学院大学", "北京市", "北京市", "https://www.ucas.ac.cn/",
        "中国科学院大学化学科学学院",
        "https://chem.ucas.ac.cn/index.php/zh-cn/",
        "官网设化学科学学院，并开展化学、化学生物学和高分子材料等教学科研。",
        "新增双一流高校；具有化学、材料、生物和环境相关学院及研究方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "首都师范大学", "北京市", "北京市", "https://www.cnu.edu.cn/",
        "首都师范大学化学系",
        "https://hxx.cnu.edu.cn/",
        "学校官网设化学系，并设生命科学学院开展生命科学教学科研。",
        "新增双一流高校；具有化学和生命科学相关本科教学与科研方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "中国人民公安大学", "北京市", "北京市", "https://www.ppsuc.edu.cn/",
        "中国人民公安大学刑事科学技术专业",
        "https://www.ppsuc.edu.cn/xkzy/bks1/xskxjs.htm",
        "官网刑事科学技术专业培养现场勘查、物证检验鉴定和刑事技术应用能力。",
        "公安高校例外；具有物证检验、法医学及刑事科学技术业务机会。",
    ),
    VerifiedDoubleFirstClassSeed(
        "天津工业大学", "天津市", "天津市", "https://www.tiangong.edu.cn/",
        "天津工业大学材料科学与工程专业",
        "https://clxy.tiangong.edu.cn/2017/0911/c3671a28208/page.htm",
        "官网材料科学与工程专业包含高分子及无机非金属材料等培养方向。",
        "新增双一流高校；具有材料、化学工程与环境相关专业。",
    ),
    VerifiedDoubleFirstClassSeed(
        "天津中医药大学", "天津市", "天津市", "https://www.tjutcm.edu.cn/",
        "天津中医药大学中药学院简介",
        "https://zhongyao.tjutcm.edu.cn/xygk/xyjj.htm",
        "官网中药学院开展中药化学、中药药理、药用植物和现代中药分析教学科研。",
        "新增双一流高校；具有中药学、药物化学和分析检测方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "山西大学", "山西省", "太原市", "https://www.sxu.edu.cn/",
        "山西大学生命科学学院简介",
        "https://life.sxu.edu.cn/xygk/xyjj/index.htm",
        "官网生命科学学院拥有化学生物学与分子工程教育部重点实验室等平台。",
        "新增双一流高校；具有生命科学、化学及环境相关学院。",
    ),
    VerifiedDoubleFirstClassSeed(
        "上海海洋大学", "上海市", "上海市", "https://www.shou.edu.cn/",
        "上海海洋大学水产与生命学院",
        "https://smxy.shou.edu.cn/",
        "官网设水产与生命学院，并设海洋科学与生态环境、食品科学等相关学院。",
        "新增双一流高校；具有水产生命、生态环境和食品检测方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "上海中医药大学", "上海市", "上海市", "https://www.shutcm.edu.cn/",
        "上海中医药大学中药学院",
        "https://zyxy.shutcm.edu.cn/",
        "官网中药学院设中药学、药学本科专业和药理学、药剂学等学位点。",
        "新增双一流高校；具有中药、药学和生物化学检测方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "上海科技大学", "上海市", "上海市", "https://www.shanghaitech.edu.cn/",
        "上海科技大学学院设置",
        "https://www.shanghaitech.edu.cn/1009/list.htm",
        "官网设生命科学与技术学院，物质学院开展材料、化学和材料生物学研究。",
        "新增双一流高校；具有材料、化学和生命科学相关教学科研方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "南京邮电大学", "江苏省", "南京市", "https://www.njupt.edu.cn/",
        "南京邮电大学材料科学与工程学院简介",
        "https://iam.njupt.edu.cn/6401/listm.htm",
        "官网材料学院融合材料、化学、生物及医学等领域开展信息材料研究。",
        "新增双一流高校；具有材料科学、化学与生命交叉研究方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "南京林业大学", "江苏省", "南京市", "https://www.njfu.edu.cn/",
        "南京林业大学生态与环境学院简介",
        "https://cee.njfu.edu.cn/xygk/xyjj/",
        "官网设生态学、环境科学、环境工程本科专业及环境科学与工程学位点。",
        "新增双一流高校；具有生态环境、生物和材料相关专业。",
    ),
    VerifiedDoubleFirstClassSeed(
        "南京信息工程大学", "江苏省", "南京市", "https://www.nuist.edu.cn/",
        "南京信息工程大学环境科学与工程学院简介",
        "https://sese.nuist.edu.cn/xygk/xyjj.htm",
        "官网环境学院设环境科学与工程博士点、环境科学和环境工程专业。",
        "新增双一流高校；具有环境科学、环境工程及环境监测方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "南京医科大学", "江苏省", "南京市", "https://www.njmu.edu.cn/",
        "南京医科大学生物医学工程与信息学院简介",
        "https://bmei.njmu.edu.cn/10121/list.htm",
        "官网生物医学工程学院建设智能诊疗器械、医用纳米材料等研究平台。",
        "新增双一流高校；具有生物医学工程、公共卫生和药学方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "南京中医药大学", "江苏省", "南京市", "https://www.njucm.edu.cn/",
        "南京中医药大学药学院简介",
        "https://yxy.njucm.edu.cn/510/listm.htm",
        "官网药学院设中药学、药学、制药工程、生物制药和食品质量安全等本科专业。",
        "新增双一流高校；具有中药、药学、生物制药和食品检测方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "宁波大学", "浙江省", "宁波市", "https://www.nbu.edu.cn/",
        "宁波大学化学专业介绍",
        "https://zsb.nbu.edu.cn/info/1021/2755.htm",
        "官网本科专业介绍列有化学、材料科学与工程、环境工程和生物科学类。",
        "新增双一流高校；具有化学、材料、环境及生物相关本科专业。",
    ),
    VerifiedDoubleFirstClassSeed(
        "河南大学", "河南省", "开封市", "https://www.henu.edu.cn/",
        "河南大学本科招生学院专业汇总",
        "https://zs.henu.edu.cn/info/1021/9183.htm",
        "官网列有生物科学、化学、应用化学、能源化学和环境科学等本科专业。",
        "新增双一流高校；具有生物、化学和环境相关本科专业。",
    ),
    VerifiedDoubleFirstClassSeed(
        "湘潭大学", "湖南省", "湘潭市", "https://www.xtu.edu.cn/",
        "湘潭大学材料科学与工程学院概况",
        "https://clxy.xtu.edu.cn/xygk.htm",
        "官网材料学院依托材料科学与工程博士点开展材料设计、制备与应用研究。",
        "新增双一流高校；具有材料、化学及环境相关专业和科研方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "华南农业大学", "广东省", "广州市", "https://www.scau.edu.cn/",
        "华南农业大学生命科学学院简介",
        "https://life.scau.edu.cn/10091/list.htm",
        "官网生命学院开展生物教学科研，学校化学、环境、材料及生物学科进入 ESI 前列。",
        "新增双一流高校；具有生命、环境、化学、材料和食品相关方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "广州医科大学", "广东省", "广州市", "https://www.gzhmu.edu.cn/",
        "广州医科大学生物医学工程学科简介",
        "https://www.gzhmu.edu.cn/info/2771/44701.htm",
        "官网生物医学工程学科聚焦生物医学材料、组织工程和智能诊疗技术。",
        "新增双一流高校；具有生物医学工程、药学及医学检测方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "广州中医药大学", "广东省", "广州市", "https://www.gzucm.edu.cn/",
        "广州中医药大学中药学院概况",
        "https://cctm.gzucm.edu.cn/xygk.htm",
        "官网中药学院设药物化学、药理、中药资源及分子生物等教学科研方向。",
        "新增双一流高校；具有中药、药学、化学及生物检测方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "南方科技大学", "广东省", "深圳市", "https://www.sustech.edu.cn/",
        "南方科技大学院系与专业设置",
        "https://sustech.edu.cn/zh/college.html",
        "官网设化学、材料、生物医学工程、环境科学与工程和化学生物学等院系专业。",
        "新增双一流高校；具有化学、材料、生物和环境相关专业。",
    ),
    VerifiedDoubleFirstClassSeed(
        "西南石油大学", "四川省", "成都市", "https://www.swpu.edu.cn/",
        "西南石油大学化学化工学院本科专业",
        "https://www.swpu.edu.cn/hgy/bkszszl/bkzyjs.htm",
        "官网化学化工学院开设化学工程与工艺、环境工程等本科专业。",
        "新增双一流高校；具有化学化工、环境和新能源材料方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "成都理工大学", "四川省", "成都市", "https://www.cdut.edu.cn/",
        "成都理工大学材料与化学化工学院学科专业",
        "https://cmcc.cdut.edu.cn/xkzy.htm",
        "官网材料与化学化工学院以化学工程与工艺、材料科学与工程为主体。",
        "新增双一流高校；具有材料、化学化工、生态环境及分析检测方向。",
    ),
    VerifiedDoubleFirstClassSeed(
        "成都中医药大学", "四川省", "成都市", "https://www.cdutcm.edu.cn/",
        "成都中医药大学学校简介",
        "https://www.cdutcm.edu.cn/xxgk/xxjj.htm",
        "官网列有中药学双一流学科及化学、生物学与生物化学等相关学科。",
        "新增双一流高校；具有中药、药学、化学及生物检测方向。",
    ),
)


EXCLUDED_NEW_DOUBLE_FIRST_CLASS_UNIVERSITIES = (
    ExcludedDoubleFirstClassSeed("外交学院", "外交与国际关系类院校，未发现符合范围的生化环材专业依据。"),
    ExcludedDoubleFirstClassSeed("中国音乐学院", "音乐类院校，不符合生化环材或体育例外范围。"),
    ExcludedDoubleFirstClassSeed("中央美术学院", "美术类院校，不符合生化环材或体育例外范围。"),
    ExcludedDoubleFirstClassSeed("中央戏剧学院", "戏剧艺术类院校，不符合生化环材或体育例外范围。"),
    ExcludedDoubleFirstClassSeed("上海音乐学院", "音乐类院校，不符合生化环材或体育例外范围。"),
    ExcludedDoubleFirstClassSeed("中国美术学院", "美术类院校，不符合生化环材或体育例外范围。"),
)


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把 25 所合格高校转换为正式候选；粗地址仅用于高德严格同名主校区 POI 检索。"""

    assert len(VERIFIED_DOUBLE_FIRST_CLASS_UNIVERSITIES) == 25
    assert len(EXCLUDED_NEW_DOUBLE_FIRST_CLASS_UNIVERSITIES) == 6
    assert len({seed.name for seed in VERIFIED_DOUBLE_FIRST_CLASS_UNIVERSITIES}) == 25
    return tuple(
        UniversityCandidate(
            name=seed.name,
            website=seed.website,
            province=seed.province,
            city=seed.city,
            district=None,
            address=f"{seed.city}{seed.name}",
            evidence_title=seed.evidence_title,
            evidence_url=seed.evidence_url,
            evidence_excerpt=seed.evidence_excerpt,
            inclusion_reason=seed.inclusion_reason,
            tags=("高校", "双一流", "官网专业证据"),
        )
        for seed in VERIFIED_DOUBLE_FIRST_CLASS_UNIVERSITIES
    )


def main() -> None:
    """创建 25 所新增“双一流”高校批次；重复运行不覆盖既有档案或人工修改。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 双一流新增高校生化环材核验",
            source_scope=(
                "教育部第二轮双一流名单与既有985/211名单差集共31所；逐校官网核验后纳入25所，"
                "排除6所艺术/外交类高校。主校区由高德严格同名POI低并发补齐。"
            ),
            source_url=MOE_DOUBLE_FIRST_CLASS_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-double-first-class-import",
        )
    print(
        f"双一流新增高校批次完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次 ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
