"""导入省属重点本科第 05 批：保存桂琼渝川官方证据并排队定位主校区。"""

from app.cli.import_verified_provincial_key_universities_batch_01 import (
    MOE_UNIVERSITY_DIRECTORY,
    VerifiedProvincialKeySeed,
)
from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


GUANGXI_PLAN_URL = "https://jyt.gxzf.gov.cn/zfxxgk/fdzdgknr/tzgg_58179/t16361991.shtml"
HAINAN_PLAN_URL = (
    "https://en.hainan.gov.cn/hainan/qjcqhghqw/202106/"
    "3a93447f099d49cba0f66a9e4a0d16bd/files/255196ea06c842d38b8c29766b5f2126.pdf"
)
CHONGQING_PLAN_URL = (
    "https://fzggw.cq.gov.cn/zfxxgk/fdzdgknr/ghxx/zxgh/202112/"
    "t20211216_10178875.html"
)
CHONGQING_FOUR_NEW_URL = "https://www.cq.gov.cn/ywdt/jrcq/202201/t20220115_10305490.html"


# 先纳入省级建设身份与目标学科证据均清晰的公办本科；四川证据分散项留到后续困难批。
VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_05 = (
    # 广西：严格采用自治区教育厅一流学科 A/B 类名单中的目标学科及共建学校。
    VerifiedProvincialKeySeed(
        "广西师范大学", "广西壮族自治区", "桂林市", "https://www.gxnu.edu.cn/",
        "广西一流学科建设项目名单", GUANGXI_PLAN_URL,
        "自治区教育厅一流学科 A 类名单列有广西师范大学化学学科。",
        "自治区一流学科建设本科；具有化学及相关分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "广西医科大学", "广西壮族自治区", "南宁市", "https://www.gxmu.edu.cn/",
        "广西一流学科建设项目名单", GUANGXI_PLAN_URL,
        "自治区名单列有临床医学、药学、口腔医学、基础医学、公共卫生与预防医学和生物医学工程。",
        "自治区一流学科建设医科本科；具有药学、生物医学、公共卫生与医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "广西民族大学", "广西壮族自治区", "南宁市", "https://www.gxmzu.edu.cn/",
        "广西一流学科建设项目名单", GUANGXI_PLAN_URL,
        "自治区一流学科 B 类名单列有化学工程与技术，并与广西中医药大学中药学交叉共建。",
        "自治区一流学科建设本科；具有化学工程、中药与分析检测交叉方向。",
    ),
    VerifiedProvincialKeySeed(
        "桂林电子科技大学", "广西壮族自治区", "桂林市", "https://www.guet.edu.cn/",
        "广西一流学科建设项目名单", GUANGXI_PLAN_URL,
        "自治区名单列有材料科学与工程及仪器科学与技术共建学科。",
        "自治区一流学科建设本科；具有材料与仪器分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "桂林理工大学", "广西壮族自治区", "桂林市", "https://www.glut.edu.cn/",
        "广西一流学科建设项目名单", GUANGXI_PLAN_URL,
        "自治区名单列有环境科学与工程、材料科学与工程及地质资源与地质工程。",
        "自治区一流学科建设本科；具有环境、材料、地质资源与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "广西中医药大学", "广西壮族自治区", "南宁市", "https://www.gxtcmu.edu.cn/",
        "广西一流学科建设项目名单", GUANGXI_PLAN_URL,
        "自治区名单列有中医学、中药学、中西医结合及化学工程与技术交叉共建学科。",
        "自治区一流学科建设医药本科；具有中药质量、药学与化学分析方向。",
    ),
    VerifiedProvincialKeySeed(
        "广西科技大学", "广西壮族自治区", "柳州市", "https://www.gxust.edu.cn/",
        "广西一流学科建设项目名单", GUANGXI_PLAN_URL,
        "自治区一流学科 B 类名单列有化学工程与技术。",
        "自治区一流学科建设本科；具有化学化工与材料检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "南宁师范大学", "广西壮族自治区", "南宁市", "https://www.nnnu.edu.cn/",
        "广西一流学科建设项目名单", GUANGXI_PLAN_URL,
        "自治区名单列有地理学，并与北部湾大学海洋科学、桂林理工大学测绘科学交叉共建。",
        "自治区一流学科建设本科；具有地理环境、海洋环境与资源监测方向。",
    ),
    VerifiedProvincialKeySeed(
        "北部湾大学", "广西壮族自治区", "钦州市", "https://www.bbgu.edu.cn/",
        "广西一流学科建设项目名单", GUANGXI_PLAN_URL,
        "自治区名单列有海洋科学，并与地理学、测绘科学与技术交叉共建。",
        "自治区一流学科建设本科；具有海洋生物、生态环境与食品检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "右江民族医学院", "广西壮族自治区", "百色市", "https://www.ymun.edu.cn/",
        "广西一流学科建设项目名单", GUANGXI_PLAN_URL,
        "自治区名单列有临床医学，并与广西医科大学共建公共卫生与预防医学。",
        "自治区一流学科建设医科本科；具有公共卫生、生物医学与医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "桂林医科大学", "广西壮族自治区", "桂林市", "https://www.glmc.edu.cn/",
        "广西一流学科建设项目名单", GUANGXI_PLAN_URL,
        "自治区名单以更名前的桂林医学院列有临床医学和药学；教育部底表使用现名桂林医科大学。",
        "自治区一流学科建设医科本科；具有临床、药学与医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "贺州学院", "广西壮族自治区", "贺州市", "https://www.hzxy.edu.cn/",
        "广西一流学科建设项目名单", GUANGXI_PLAN_URL,
        "自治区一流学科 B 类名单列有食品科学与工程。",
        "自治区一流学科建设本科；具有食品质量、生物与理化检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "百色学院", "广西壮族自治区", "百色市", "https://www.bsuc.edu.cn/",
        "广西一流学科建设项目名单", GUANGXI_PLAN_URL,
        "自治区名单明确百色学院农业资源与环境参与广西大学作物学共建。",
        "自治区一流学科共建本科；具有农业资源、环境与作物检测方向。",
    ),

    # 海南：按省级“1+2+X”高校布局筛选两所重点支持高校和热带海洋特色高校。
    VerifiedProvincialKeySeed(
        "海南师范大学", "海南省", "海口市", "https://www.hainnu.edu.cn/",
        "海南省教育事业发展十四五规划", HAINAN_PLAN_URL,
        "省级规划将海南师范大学列入重点支持高校；学校设化学、生物科学、生态学和环境相关方向。",
        "海南重点支持本科；具有化学、生物、生态与环境监测方向。",
    ),
    VerifiedProvincialKeySeed(
        "海南医科大学", "海南省", "海口市", "https://www.hainmc.edu.cn/",
        "海南省教育事业发展十四五规划", HAINAN_PLAN_URL,
        "省级规划将原海南医学院列入重点支持高校；教育部底表使用现名海南医科大学。",
        "海南重点支持医科本科；具有药学、公共卫生、生物医学与医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "海南热带海洋学院", "海南省", "三亚市", "https://www.hntou.edu.cn/",
        "海南省教育事业发展十四五规划", HAINAN_PLAN_URL,
        "省级规划将学校纳入特色应用型本科布局，优势覆盖海洋科学、水产、生态和食品。",
        "海南特色应用型本科；具有海洋生物、生态环境、水产与食品检测方向。",
    ),

    # 重庆：采用市级高水平“四新”建设名单，另纳入新设公办中医药本科。
    VerifiedProvincialKeySeed(
        "重庆医科大学", "重庆市", "重庆市", "https://www.cqmu.edu.cn/",
        "重庆高水平新医科建设高校名单", CHONGQING_FOUR_NEW_URL,
        "市级高水平四新建设名单将重庆医科大学列为高水平新医科建设高校。",
        "重庆高水平新医科本科；具有药学、公共卫生、生物医学与医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "重庆师范大学", "重庆市", "重庆市", "https://www.cqnu.edu.cn/",
        "重庆市教育事业发展十四五规划", CHONGQING_PLAN_URL,
        "市级规划将重庆师范大学列入重点支持高校，学校设化学、生物科学、材料和环境相关方向。",
        "重庆重点支持本科；具有化学、生物、材料与环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "重庆邮电大学", "重庆市", "重庆市", "https://www.cqupt.edu.cn/",
        "重庆高水平新工科建设高校名单", CHONGQING_FOUR_NEW_URL,
        "市级名单将重庆邮电大学列为高水平新工科建设高校，学校设材料、化学与生物医学工程方向。",
        "重庆高水平新工科本科；具有材料、化学与生物医学交叉方向。",
    ),
    VerifiedProvincialKeySeed(
        "重庆交通大学", "重庆市", "重庆市", "https://www.cqjtu.edu.cn/",
        "重庆高水平新工科建设高校名单", CHONGQING_FOUR_NEW_URL,
        "市级名单将重庆交通大学列为高水平新工科建设高校，优势覆盖材料、资源与环境工程。",
        "重庆高水平新工科本科；具有材料、资源环境与工程检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "重庆理工大学", "重庆市", "重庆市", "https://www.cqut.edu.cn/",
        "重庆高水平新工科建设高校名单", CHONGQING_FOUR_NEW_URL,
        "市级名单将重庆理工大学列为高水平新工科建设高校，学校设材料、化学化工和药学方向。",
        "重庆高水平新工科本科；具有材料、化学化工、生物医药与检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "重庆科技大学", "重庆市", "重庆市", "https://www.cqust.edu.cn/",
        "重庆高水平新工科建设高校名单", CHONGQING_FOUR_NEW_URL,
        "市级名单以更名前的重庆科技学院列入高水平新工科建设高校，优势覆盖材料、化工、环境和安全。",
        "重庆高水平新工科本科；具有材料、化工、环境与安全检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "重庆文理学院", "重庆市", "重庆市", "https://www.cqwu.edu.cn/",
        "重庆高水平新工科建设高校名单", CHONGQING_FOUR_NEW_URL,
        "市级名单将重庆文理学院列为高水平新工科建设高校，学校设材料、化学、环境和药学相关方向。",
        "重庆高水平新工科本科；具有材料、化学、环境与药学方向。",
    ),
    VerifiedProvincialKeySeed(
        "重庆中医药学院", "重庆市", "重庆市", "https://www.cqctcm.edu.cn/",
        "重庆高等教育年度建设情况", "https://www.cq.gov.cn/zwgk/zfxxgkml/zdlyxxgk/jy1/jy/202401/t20240117_12831496.html",
        "市政府公开信息确认重庆中医药学院为新设置公办本科院校，办学聚焦中医药。",
        "重庆公办中医药本科；具有中药资源、药物质量与分析检测方向。",
    ),

    # 四川：本批只收录学校官网可直接核验贡嘎计划及目标学科的 13 所，慢证据项后置。
    VerifiedProvincialKeySeed(
        "西南科技大学", "四川省", "绵阳市", "https://www.swust.edu.cn/",
        "西南科技大学人才招聘公告", "https://rsc.swust.edu.cn/2025/0127/c3035a211555/page.htm",
        "官网明确 5 个学科入选贡嘎计划，材料、化学、环境生态及动植物科学进入 ESI 前1%。",
        "四川贡嘎计划建设本科；具有材料、化学、环境生态与生命科学方向。",
    ),
    VerifiedProvincialKeySeed(
        "成都信息工程大学", "四川省", "成都市", "https://www.cuit.edu.cn/",
        "成都信息工程大学学科与专业设置", "https://www.cuit.edu.cn/__local/2/B8/D3/763383E51F5D7047D193843DFCB_0EE38431_2B6EA.pdf",
        "官网资料列出贡嘎计划大气科学、计算机科学与技术、信息与通信工程及环境科学省重点学科。",
        "四川贡嘎计划建设本科；具有大气环境、环境科学与监测仪器方向。",
    ),
    VerifiedProvincialKeySeed(
        "四川轻化工大学", "四川省", "自贡市", "https://www.suse.edu.cn/",
        "四川轻化工大学学校概况", "https://www.suse.edu.cn/14/list.htm",
        "官网明确食品科学与工程、化学工程与技术入选贡嘎计划，化学、材料、农业科学进入 ESI 前1%。",
        "四川贡嘎计划建设本科；具有食品、化学化工、材料与生物医药检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "西华大学", "四川省", "成都市", "https://www.xhu.edu.cn/",
        "西华大学学校简介", "https://rsc.xhu.edu.cn/bd/77/c10776a245111/pagem.htm",
        "官网明确 3 个学科入选贡嘎计划，材料、化学、农业科学进入 ESI 前1%，重点建设食品学科群。",
        "四川贡嘎计划建设本科；具有食品、材料、化学与农业检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "西南医科大学", "四川省", "泸州市", "https://www.swmu.edu.cn/",
        "西南医科大学药学院简介", "https://yxy.swmu.edu.cn/xygk/xyjj.htm",
        "官网明确药学为贡嘎计划Ⅱ类学科，并设药物分析、微生物与生化药学等教学科研方向。",
        "四川贡嘎计划医科本科；具有药学、药物分析、生物医学与检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "川北医学院", "四川省", "南充市", "https://www.nsmc.edu.cn/",
        "川北医学院学校简介", "https://www.nsmc.edu.cn/xxgk/xxjj.htm",
        "官网明确建有 2 个四川省双一流建设学科及医学重点学科体系。",
        "四川省级双一流医科本科；具有基础医学、药学、公共卫生与医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "成都医学院", "四川省", "成都市", "https://www.cmc.edu.cn/",
        "成都医学院公共卫生学院简介", "https://ggwsx.cmc.edu.cn/xygk/xyjj.htm",
        "官网明确公共卫生与预防医学为贡嘎计划Ⅱ类学科，并设置卫生检验与检疫本科专业。",
        "四川贡嘎计划医科本科；具有公共卫生、卫生检验、药学与生物医学方向。",
    ),
    VerifiedProvincialKeySeed(
        "成都大学", "四川省", "成都市", "https://www.cdu.edu.cn/",
        "成都大学学校简介", "https://www.cdu.edu.cn/xxgk/xxjj.htm",
        "官网明确 3 个学科入选贡嘎计划，并设药学、材料、材料与化工、生物与医药等学位点。",
        "四川重点建设本科；具有药学、材料、化工、生物医药与食品方向。",
    ),
    VerifiedProvincialKeySeed(
        "中国民用航空飞行学院", "四川省", "德阳市", "https://www.cafuc.edu.cn/",
        "中国民用航空飞行学院简介", "https://www.cafuc.edu.cn/info/1050/39698.htm",
        "官网明确安全科学与工程入选贡嘎计划，并建设航空医学、火灾安全和航空油料质量检测实验平台。",
        "四川高水平行业本科；具有资源环境、航空油料质量、安全与材料检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "攀枝花学院", "四川省", "攀枝花市", "https://www.pzhu.edu.cn/",
        "攀枝花学院钒钛学院简介", "https://ftxy.pzhu.cn/xygk/xyjj.htm",
        "官网明确材料科学与工程获批贡嘎计划Ⅱ类学科，并设资源环境、检测中心和材料化工平台。",
        "四川贡嘎计划建设本科；具有钒钛材料、资源环境与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "四川文理学院", "四川省", "达州市", "https://www.sasu.edu.cn/",
        "四川文理学院化学工程与技术学科建设说明", "https://hgxy.sasu.edu.cn/info/1070/3986.htm",
        "官网明确化学工程与技术入选贡嘎计划，形成能源化工、低碳循环和化工新材料方向。",
        "四川贡嘎计划建设本科；具有化学化工、环境、材料与制药方向。",
    ),
    VerifiedProvincialKeySeed(
        "内江师范学院", "四川省", "内江市", "https://www.njtc.edu.cn/",
        "内江师范学院水产学科建设说明", "https://yjs.njtc.edu.cn/info/1412/1552.htm",
        "官网明确水产学科入选贡嘎计划，依托生命科学开展水产养殖、生态修复与饲料研究。",
        "四川贡嘎计划建设本科；具有水产生物、生态环境与食品饲料检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "乐山师范学院", "四川省", "乐山市", "https://www.lsnu.edu.cn/",
        "乐山师范学院林学学科建设说明", "https://www.lsnu.edu.cn/info/1038/5126.htm",
        "官网明确林学入选贡嘎计划，覆盖生物技术、生态保护修复和生物多样性研究。",
        "四川贡嘎计划建设本科；具有林学、生物技术、生态环境与资源检测方向。",
    ),
)


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把第 05 批核验种子转为正式候选，并以城市和校名严格检索主校区。"""

    assert len(VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_05) == 37
    assert len({seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_05}) == 37
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
            tags=("高校", "省属重点本科", "官网专业证据", "省属重点第05批"),
        )
        for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_05
    )


def main() -> None:
    """幂等创建桂琼渝川第 05 批，不覆盖重复项或人工核验结果。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 省属重点本科生化环材核验第05批",
            source_scope=(
                "广西、海南、重庆、四川省级一流/高水平/贡嘎计划建设公办本科；结合省级官方名单"
                "与学校官网确认生物、环境、化学、材料、医药、食品农业、安全质量或检测方向，"
                "排除既有、纯文财经、艺术、民办和证据尚不完整院校。"
            ),
            source_url=MOE_UNIVERSITY_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-provincial-key-import",
        )
    print(
        f"省属重点本科第05批完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
