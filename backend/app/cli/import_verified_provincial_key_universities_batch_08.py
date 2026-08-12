"""导入省属重点本科第 08 批：核验陕甘青宁新目标高校并排队定位主校区。"""

from app.cli.import_verified_provincial_key_universities_batch_01 import VerifiedProvincialKeySeed
from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


MOE_2026_UNIVERSITY_DIRECTORY = (
    "https://www.moe.gov.cn/jyb_xxgk/s5743/s5744/202606/t20260618_1441074.html"
)


# 本批只保留省级重点/一流建设身份与目标学科证据同时成立的公办普通本科。
VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_08 = (
    VerifiedProvincialKeySeed(
        "西安理工大学", "陕西省", "西安市", "https://www.xaut.edu.cn/",
        "西安理工大学学校简介", "https://www.xaut.edu.cn/xxgk/xxjj.htm",
        "官网明确学校是陕西省重点建设高水平大学和国家双一流培育高校，材料、环境生态、化学等学科进入 ESI 全球前1%。",
        "陕西省重点高水平本科；具有材料、环境、化学和水资源检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "西安建筑科技大学", "陕西省", "西安市", "https://www.xauat.edu.cn/",
        "西安建筑科技大学学校简介", "https://cn.xauat.edu.cn/jdgk/xxjj.htm",
        "官网明确学校连续两轮入选陕西省国家双一流培育高校，环境、材料、化学和生物学与生物化学等学科基础突出。",
        "陕西省双一流培育本科；具有环境、材料、化学和生态检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "陕西科技大学", "陕西省", "西安市", "https://www.sust.edu.cn/",
        "陕西科技大学本科教学质量报告", "https://xxgk.sust.edu.cn/__local/7/DE/AD/1DCA7B40E938BC32373859E113D_80795002_A4756.pdf",
        "学校官方质量报告明确其为陕西省国内一流大学建设高校，材料科学、化学、工程学等目标学科进入 ESI 全球前1%。",
        "陕西省国内一流大学建设本科；具有轻工材料、化学化工、生物和环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "西安科技大学", "陕西省", "西安市", "https://www.xust.edu.cn/",
        "西安科技大学学校简介", "https://www.xust.edu.cn/xyjj/xxgk.htm",
        "官网明确学校是陕西省国家双一流培育高校，材料、环境生态、化学等学科进入 ESI 全球前1%。",
        "陕西省双一流培育本科；具有材料、环境、化学、矿产和安全检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "西安工业大学", "陕西省", "西安市", "https://www.xatu.edu.cn/",
        "西安工业大学学校简介", "https://www.xatu.edu.cn/xxgk/xxjj.htm",
        "官网明确学校是陕西省重点建设高水平大学和国内一流学科建设高校，材料科学和化学进入 ESI 全球前1%。",
        "陕西省重点高水平本科；具有材料、化学、光电材料和精密检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "西安工程大学", "陕西省", "西安市", "https://www.xpu.edu.cn/",
        "西安工程大学学校简介", "https://www.xpu.edu.cn/xue_xiao_gai_kuang/xxjj.htm",
        "官网明确学校入选陕西省第二轮双一流培育高校，工程、材料、化学进入 ESI 全球前1%，并设环境与化学工程方向。",
        "陕西省双一流培育本科；具有纺织材料、化学、环境和质量检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "西安石油大学", "陕西省", "西安市", "https://www.xsyu.edu.cn/",
        "西安石油大学学校概况", "https://www.xsyu.edu.cn/xxgk/xxgk.htm",
        "官网明确学校是陕西省双一流培育和高水平大学建设高校，化学、材料科学进入 ESI 全球前1%。",
        "陕西省双一流培育本科；具有石油化学、材料、环境污染控制和分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "延安大学", "陕西省", "延安市", "https://www.yau.edu.cn/",
        "延安大学学校简介", "https://yau.edu.cn/xqzl/xxjj.htm",
        "官网列有省级一流学科建设任务，化学工程、生态学、基础医学及生物科学等目标专业和科研方向完整。",
        "陕西省一流学科建设本科；具有化学、生态、生物、基础医学和分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "陕西理工大学", "陕西省", "汉中市", "https://www.snut.edu.cn/",
        "陕西理工大学学校简介", "https://www.snut.edu.cn/xxgk/xxjj.htm",
        "官网介绍学校建有省级重点学科与重点实验室，设置生物科学、化学与环境、材料科学等教学科研单位。",
        "陕西省重点学科建设本科；具有生物、化学、环境和材料检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "陕西中医药大学", "陕西省", "咸阳市", "https://www.sntcm.edu.cn/",
        "陕西中医药大学学校简介", "https://zbb.sntcm.edu.cn/xmsmh/588.chtml",
        "学校官网明确其为全国重点建设中医院校和省部共建高校，以中医药为主体并设药学院、医学技术和公共卫生等单位。",
        "陕西省重点中医药本科；具有中药、药物分析、医学检验和质量控制方向。",
    ),
    VerifiedProvincialKeySeed(
        "西安医学院", "陕西省", "西安市", "https://www.xiyi.edu.cn/",
        "西安医学院学校简介", "https://www.xiyi.edu.cn/xxgk/xxjj.htm",
        "官网明确学校为陕西省一流应用型本科建设单位，临床医学、药理毒理、生物学与生物化学进入 ESI 全球前1%。",
        "陕西省一流应用型医科本科；具有药学、生物医学、医学检验和公共卫生方向。",
    ),
    VerifiedProvincialKeySeed(
        "西藏民族大学", "陕西省", "咸阳市", "https://www.xzmu.edu.cn/",
        "西藏民族大学基础医学重点学科", "https://www.xzmu.edu.cn/xzmu/getcontent?id=61516&url=show",
        "官网明确基础医学获批国家民委重点学科，并建有医学检验、高原医学、分子遗传和藏药检测研究平台。",
        "隶属西藏但主校区位于陕西咸阳；具有基础医学、医学检验、高原医学和药理检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "兰州理工大学", "甘肃省", "兰州市", "https://www.lut.edu.cn/",
        "兰州理工大学学校简介", "https://www.lut.edu.cn/xxgk/xxjj.htm",
        "官网明确学校是甘肃省高水平大学，材料学科入选省属高校国家一流学科突破工程，化学和环境生态进入 ESI 前1%。",
        "甘肃省高水平本科；具有材料、化学、环境和分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "兰州交通大学", "甘肃省", "兰州市", "https://www.lzjtu.edu.cn/",
        "兰州交通大学学校简介", "https://www.lzjtu.edu.cn/info/1017/2123.htm",
        "官网明确学校是甘肃省高水平和一流学科建设高校，化学、材料、环境生态进入 ESI 前1%。",
        "甘肃省高水平与一流学科建设本科；具有环境、材料、化学和交通工程检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "西北师范大学", "甘肃省", "兰州市", "https://www.nwnu.edu.cn/",
        "西北师范大学学校概况", "https://www.nwnu.edu.cn/2018/1119/c3329a180016/page.htm",
        "官网明确学校是甘肃省支持进入国家一流大学建设行列的省属高校，设化学、生物学、地理学等博士点。",
        "甘肃省一流大学建设本科；具有化学、生物、地理环境和实验检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "甘肃农业大学", "甘肃省", "兰州市", "https://www.gsau.edu.cn/",
        "甘肃农业大学资源与环境学院简介", "https://zh.gsau.edu.cn/info/1030/15668.htm",
        "官网明确生态学和农业资源与环境为甘肃省高等学校重点学科，并建有国家和省部级实验平台。",
        "甘肃省重点农业本科；具有生态、生物、资源环境、食品和农业检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "甘肃中医药大学", "甘肃省", "兰州市", "https://www.gszy.edu.cn/",
        "甘肃中医药大学学校简介", "https://www.gszy.edu.cn/xxgk/xxjj.htm",
        "学校为甘肃省与国家中医药管理局共建高校，设置中药、药学、医学技术和公共卫生等目标学科专业。",
        "甘肃省部共建中医药本科；具有中药、药物分析、医学检验和质量控制方向。",
    ),
    VerifiedProvincialKeySeed(
        "天水师范大学", "甘肃省", "天水市", "https://www.tsnu.edu.cn/",
        "天水师范大学学校概况", "https://bkzs.tsnu.edu.cn/xxgk2.htm",
        "官网列有生态学省级一流特色学科，以及生态学、化学等省级重点学科，并设生物和食品质量安全方向。",
        "甘肃省一流特色学科建设本科；具有生态、化学、生物、食品安全和材料检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "河西学院", "甘肃省", "张掖市", "https://www.hxu.edu.cn/",
        "河西学院学校简介", "https://www.hxu.edu.cn/info/1158/1060.htm",
        "官网列有农业资源与环境省级重点学科，并形成生态农业、医疗卫生及生物资源科研平台。",
        "甘肃省重点学科建设本科；具有农业资源环境、生物、医学和食品检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "青海师范大学", "青海省", "西宁市", "https://www.qhnu.edu.cn/",
        "青海师范大学学校简介", "https://www.qhnu.edu.cn/xxgk/xxjj.htm",
        "官网列有国内一流、省内一流和省级重点学科，设置生命科学、地理科学和化学化工等学院及高原生态平台。",
        "青海省一流学科建设本科；具有高原生态、生物、地理环境和化学检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "青海理工学院", "青海省", "西宁市", "https://www.qhit.edu.cn/",
        "青海理工学院学校简介", "https://www.qhit.edu.cn/xygk1/xxjj.htm",
        "官网明确学校为公办理工本科，重点建设高原生态环境、新材料新能源、大气与环境科学等理工学科群。",
        "青海省新建公办理工本科；具有生态环境、材料、能源化学和气象监测方向。",
    ),
    VerifiedProvincialKeySeed(
        "宁夏医科大学", "宁夏回族自治区", "银川市", "https://www.nxmu.edu.cn/",
        "宁夏医科大学学校简介", "https://www.nxmu.edu.cn/xxgk/xxjj.htm",
        "官网列有自治区一流、重点及优势特色学科，覆盖基础医学、药学、生物化学、化学和医学检验。",
        "宁夏自治区一流学科建设医科本科；具有药学、生物医学、公共卫生和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "塔里木大学", "新疆维吾尔自治区", "阿拉尔市", "https://www.taru.edu.cn/",
        "塔里木大学学校简介", "https://www.taru.edu.cn/xxgk/xxjj.htm",
        "官网明确学校为兵团与教育部共建高校，以农科和生命科学为特色，拥有自治区与兵团重点学科和生物资源重点实验室。",
        "兵团与教育部共建重点本科；具有生物、农业资源、食品、生态环境和质量检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "新疆农业大学", "新疆维吾尔自治区", "乌鲁木齐市", "https://www.xjau.edu.cn/",
        "新疆农业大学学校概况", "https://www.xjau.edu.cn/_t301/134/list.htm",
        "官网明确学校为自治区、教育部及农业农村部等共建高校，建有国家和自治区优势特色学科，覆盖生态环境、食品和农业。",
        "新疆自治区重点农业本科；具有生物、生态环境、食品药学和农业检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "新疆医科大学", "新疆维吾尔自治区", "乌鲁木齐市", "https://www.xjmu.edu.cn/",
        "新疆医科大学学校概况", "https://www.xjmu.edu.cn/xqzl1/xxgkxin.htm",
        "官网列有临床医学、药理毒理、生物学与生物化学、免疫学等 ESI 前1%学科及药学、基础医学建设体系。",
        "新疆自治区重点医科本科；具有药学、生物医学、公共卫生和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "新疆师范大学", "新疆维吾尔自治区", "乌鲁木齐市", "https://www.xjnu.edu.cn/",
        "新疆师范大学学校章程", "https://www.xjnu.edu.cn/xxgk/xxzc.htm",
        "官网明确学校是自治区重点建设高等师范院校，设生物、化学、环境科学与工程及资源环境相关科研方向。",
        "新疆自治区重点师范本科；具有生物、化学、环境和资源检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "昌吉学院", "新疆维吾尔自治区", "昌吉回族自治州", "https://www.cjc.edu.cn/",
        "昌吉学院学校简介", "https://www.cjc.edu.cn/xygk/xxjj.htm",
        "官网明确材料科学与工程为自治区重点学科，并建有低阶煤绿色利用、应用化学、水处理和能源环境材料平台。",
        "新疆自治区重点学科建设本科；具有材料、化学化工、环境水处理和能源检测方向。",
    ),
)


# 未纳入原因区分既有、专类、办学层次和证据不足，避免把“未核验”误写成“无相关专业”。
PROVINCIAL_KEY_BATCH_08_EXCLUSION_REASONS = {
    "西北大学": "已在此前 211/双一流批次进入正式单位，本批不重复创建。",
    "青海大学": "已在此前 211/双一流批次进入正式单位，本批不重复创建。",
    "宁夏大学": "已在此前 211/双一流批次进入正式单位，本批不重复创建。",
    "新疆大学": "已在此前 211/双一流批次进入正式单位，本批不重复创建。",
    "石河子大学": "已在此前 211/双一流批次进入正式单位，本批不重复创建。",
    "西安体育学院": "已按体育例外规则进入正式单位，本批不重复创建。",
    "西北政法大学": "政法类办学为主，未发现符合本批标准的生化环材重点建设学科证据。",
    "西安外国语大学": "语言类办学为主，未发现符合本批标准的生化环材重点建设学科证据。",
    "西安戏剧学院": "艺术类院校，本轮未发现符合标准的生化环材专业或研究方向。",
    "西安美术学院": "艺术类院校，本轮未发现符合标准的生化环材专业或研究方向。",
    "西安音乐学院": "艺术类院校，本轮未发现符合标准的生化环材专业或研究方向。",
    "西安财经大学": "财经类办学为主，未发现符合本批标准的生化环材重点建设学科证据。",
    "兰州财经大学": "财经类办学为主，未发现符合本批标准的生化环材重点建设学科证据。",
    "甘肃政法大学": "政法类办学为主，未发现符合本批标准的生化环材重点建设学科证据。",
    "新疆财经大学": "财经类办学为主，未发现符合本批标准的生化环材重点建设学科证据。",
    "新疆艺术学院": "艺术类院校，本轮未发现符合标准的生化环材专业或研究方向。",
    "新疆政法学院": "政法类办学为主，未发现符合本批标准的生化环材重点建设学科证据。",
    "陕西警察学院": "按公安单位全量规则留待公安专批，避免误标为普通高校客户类型。",
    "甘肃警察学院": "按公安单位全量规则留待公安专批，避免误标为普通高校客户类型。",
    "新疆警察学院": "按公安单位全量规则留待公安专批，避免误标为普通高校客户类型。",
}

for name in (
    "咸阳师范学院", "商洛学院", "安康学院", "宝鸡文理学院", "榆林大学", "渭南师范学院",
    "西安文理学院", "西安航空学院", "西安邮电大学", "陕西学前师范学院", "兰州城市学院",
    "兰州工业学院", "兰州文理学院", "甘肃医学院", "甘肃民族师范学院", "陇东学院",
    "陇南师范学院", "青海民族大学", "宁夏师范大学", "新疆工业学院", "伊犁师范大学",
    "喀什大学", "新疆和田学院", "新疆工程学院", "新疆理工学院", "新疆科技学院", "新疆第二医学院",
):
    PROVINCIAL_KEY_BATCH_08_EXCLUSION_REASONS[name] = (
        "存在相关本科专业或地方服务方向，但本轮未取得省属重点/一流建设身份与目标学科同时成立的充分官方证据，暂缓到普通本科补充批。"
    )

for name in (
    "陕西农林职业技术大学", "陕西工业职业技术大学", "兰州石化职业技术大学", "兰州资源环境职业技术大学",
    "武威职业技术大学", "甘肃工业职业技术大学", "甘肃林业职业技术大学", "酒泉职业技术大学",
    "青海职业技术大学", "宁夏工商职业技术大学", "宁夏职业技术大学", "乌鲁木齐职业大学",
    "新疆交通职业技术大学", "新疆农业职业技术大学", "新疆工业职业技术大学", "新疆能源铁道职业技术大学",
    "新疆工程职业大学", "新疆理工职业大学", "石河子职业技术大学",
):
    PROVINCIAL_KEY_BATCH_08_EXCLUSION_REASONS[name] = "职业本科，不属于当前普通本科筛选范围。"

for name in (
    "延安大学西安创新学院", "西京学院", "西北大学现代学院", "西安交通大学城市学院", "西安交通工程学院",
    "西安信息职业大学", "西安培华学院", "西安外事学院", "西安工商学院", "西安建筑科技大学华清学院",
    "西安思源学院", "西安明德理工学院", "西安欧亚学院", "西安汽车职业大学", "西安理工大学高科学院",
    "西安电子科技大学长安学院", "西安科技大学高新学院", "西安翻译学院", "西安财经大学行知学院",
    "长安大学兴华学院", "陕西国际商贸学院", "陕西服装工程学院", "陕西科技大学镐京学院",
    "兰州信息科技学院", "兰州博文科技学院", "兰州工商学院", "青海大学昆仑学院",
    "宁夏大学新华学院", "宁夏应用技术学院", "宁夏理工学院", "银川科技学院", "银川能源学院",
    "塔里木理工学院", "新疆昆仑科技学院", "新疆农业大学科学技术学院", "新疆天山职业技术大学",
):
    PROVINCIAL_KEY_BATCH_08_EXCLUSION_REASONS[name] = "民办本科，不属于当前省属重点公办普通本科筛选范围。"


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把第 08 批核验种子转换为候选，并用城市加校名形成严格主校区 POI 查询。"""

    assert len(VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_08) == 27
    assert len({seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_08}) == 27
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
            tags=("高校", "省属重点本科", "官网专业证据", "省属重点第08批"),
        )
        for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_08
    )


def main() -> None:
    """幂等创建西北五省区核验批；重复项只留批次记录，不覆盖既有或人工核验数据。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 省属重点本科生化环材核验第08批",
            source_scope=(
                "陕西、甘肃、青海、宁夏、新疆公办普通本科；结合教育主管部门、政府和学校官网，"
                "确认省属重点/一流建设身份及生物、环境、化学、材料、医药、农林食品或检测方向。"
                "排除既有、纯文财经艺术、民办、职业本科和公安专批；证据不足项留到普通本科补充批。"
            ),
            source_url=MOE_2026_UNIVERSITY_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-provincial-key-import",
        )
    print(
        f"省属重点本科第08批完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
