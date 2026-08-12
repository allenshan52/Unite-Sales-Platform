"""导入省属重点本科第 09 批：核验北京、天津目标高校并排队定位主校区。"""

from app.cli.import_verified_provincial_key_universities_batch_01 import VerifiedProvincialKeySeed
from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


MOE_2026_UNIVERSITY_DIRECTORY = (
    "https://www.moe.gov.cn/jyb_xxgk/s5743/s5744/202606/t20260618_1441074.html"
)

# 高德无法稳定命中长校名时使用学校官网公开的法定主校区地址，避免生成错误 pin。
OFFICIAL_MAIN_CAMPUS_ADDRESSES = {
    "天津职业技术师范大学": "天津市河西区大沽南路1310号",
}


# 仅保留重点/一流建设身份与生化环材、医药、食品或检测方向均有官方依据的公办普通本科。
VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_09 = (
    VerifiedProvincialKeySeed(
        "中国矿业大学（北京）", "北京市", "北京市", "https://www.cumtb.edu.cn/",
        "中国矿业大学（北京）化学与环境工程学院简介",
        "https://scee.cumtb.edu.cn/xygk/xyjj.htm",
        "官网列明学校为双一流全国重点高校，学院设化学工程、环境科学与工程、矿物材料和分析测试中心。",
        "双一流公办本科；具有化学化工、环境、矿物材料和分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "中国石油大学（北京）", "北京市", "北京市", "https://www.cup.edu.cn/",
        "中国石油大学（北京）学校简介", "https://www.cup.edu.cn/xxgk/xxjj/",
        "官网明确学校为双一流全国重点高校，化学、材料科学及环境与生态学进入 ESI 全球前1%。",
        "双一流公办本科；具有石油化学、材料、环境污染控制和分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "中国地质大学（北京）", "北京市", "北京市", "https://www.cugb.edu.cn/",
        "中国地质大学（北京）学校简介", "https://www.cugb.edu.cn/xxjj.jhtml",
        "官网明确学校为双一流全国重点高校，环境与生态学、化学进入 ESI 前1‰，并建有地质微生物与环境全国重点实验室。",
        "双一流公办本科；具有环境生态、化学、地质材料和资源检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "北方工业大学", "北京市", "北京市", "https://www.ncut.edu.cn/",
        "北方工业大学材料科学与工程专业", "https://cmm.ncut.edu.cn/bkjy/zyjs/clkxygc.htm",
        "官网列有材料科学与工程本科专业、材料工程硕士点及材料制备、检测和数据工程方向。",
        "北京市高精尖学科建设本科；具有材料制备、性能分析和材料检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "北京工商大学", "北京市", "北京市", "https://www.btbu.edu.cn/",
        "北京工商大学食品与健康学院简介", "https://spxy.btbu.edu.cn/xygk/xyjj/index.htm",
        "官网列明食品科学与工程为北京高校高精尖学科，设食品质量与安全、食品营养与健康及省部级检测平台。",
        "北京市高精尖学科建设本科；具有食品科学、质量安全、生物医药和环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "北京服装学院", "北京市", "北京市", "https://www.bift.edu.cn/",
        "北京服装学院材料设计与工程学院简介", "https://cly.bift.edu.cn/xyjs/xyjj/index.htm",
        "官网列有高分子材料与工程、轻化工程及材料学等北京市重点建设学科，并建有 CNAS 服装安全检测中心。",
        "北京市高水平特色本科；具有高分子材料、纺织化学、服装安全和材料检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "北京印刷学院", "北京市", "北京市", "https://www.bigc.edu.cn/",
        "北京印刷学院材料科学与工程学科简介",
        "https://gs.bigc.edu.cn/docs/2021-06/35c128a0628342b2a68ac627696113a2.pdf",
        "官网培养资料列明材料科学与工程聚焦印刷包装、印刷电子及材料物理化学、加工和检测方向。",
        "北京市高精尖学科建设本科；具有印刷包装材料、材料化学和质量检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "北京建筑大学", "北京市", "北京市", "https://www.bucea.edu.cn/",
        "北京建筑大学学校简介", "https://www.bucea.edu.cn/gbxxgk/gbxxjj/index.htm",
        "官网明确学校为市属高水平特色型大学，建有城市雨水系统与水环境教育部重点实验室等科研平台。",
        "北京市高水平特色本科；具有水环境、建筑材料、城市生态和工程检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "北京石油化工学院", "北京市", "北京市", "https://www.bipt.edu.cn/",
        "北京石油化工学院研究生培养方案",
        "https://www.bipt.edu.cn/publish/graduate/docs//2023-09/062288192a5945b1a14a4fed3ea9e01b.pdf",
        "官网培养方案列有化学工程与技术、环境科学与工程、材料与化工、资源与环境及生物与医药方向。",
        "北京市高水平应用型本科；具有化学化工、材料、环境和生物医药检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "北京农学院", "北京市", "北京市", "https://www.bua.edu.cn/",
        "北京农学院生物与资源环境学院简介", "https://swkgxy.bua.edu.cn/xygk/xyjj.htm",
        "官网列有生物工程、应用化学、植物保护和农业资源与环境本科专业，并与国家环境分析测试中心共建实践基地。",
        "北京市高精尖学科建设农林本科；具有生物、应用化学、资源环境、食品和农业检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "首都医科大学", "北京市", "北京市", "https://www.ccmu.edu.cn/",
        "首都医科大学学校简介", "https://www.ccmu.edu.cn/xxgk/xxjj/index.htm",
        "官网明确学校为北京市重点高等院校，设基础医学、药学、公共卫生、医学技术及卫生检验与检疫等方向。",
        "北京市重点医科本科；具有生物医学、药学、公共卫生、医学检验和卫生检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "北京联合大学", "北京市", "北京市", "https://www.buu.edu.cn/",
        "北京联合大学食品科学与工程学科简介",
        "https://www.bec.buu.edu.cn/art/2022/8/23/art_36248_685263.html",
        "官网明确食品科学与工程为北京市重点建设学科，依托生物活性物质、功能食品和保健食品功能检测平台。",
        "北京市高水平应用型本科；具有食品、生物、制药、环境和功能检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "中国民航大学", "天津市", "天津市", "https://www.cauc.edu.cn/",
        "中国研究生招生信息网中国民航大学专业目录",
        "https://yz.chsi.com.cn/sch/viewZszc--infoId-2413282509,categoryId-10460864,schId-367953,mindex-12.dhtml",
        "教育部研招平台列有材料科学与工程及航空表面工程、复合材料损伤、新材料设计和功能材料研究方向。",
        "民航局、天津市和教育部共建本科；具有航空材料、材料化学、无损检测和表面工程方向。",
    ),
    VerifiedProvincialKeySeed(
        "天津科技大学", "天津市", "天津市", "https://www.tust.edu.cn/",
        "天津科技大学学校简介", "https://www.tust.edu.cn/xxgk/xxgk_1.html",
        "官网列有轻工、食品、化学工程、海洋科学、生物与医药学位点及食品营养安全、发酵和生物基材料平台。",
        "天津市一流学科建设本科；具有食品、生物、化学、材料、海洋环境和质量检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "天津理工大学", "天津市", "天津市", "https://www.tjut.edu.cn/",
        "天津理工大学材料科学与工程学院简介", "https://clxy.tjut.edu.cn/info/1031/3232.htm",
        "官网列明材料科学与工程为天津市一流学科，并建有新能源材料、低碳技术和功能晶体研究平台。",
        "天津市一流学科建设本科；具有材料、新能源、低碳化学和性能检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "天津师范大学", "天津市", "天津市", "https://www.tjnu.edu.cn/",
        "天津师范大学学校简介", "https://www.tjnu.edu.cn/xxgk/xxjj.htm",
        "官网列明化学为天津市一流学科，化学、材料科学、环境与生态学进入 ESI 全球前1%。",
        "天津市一流学科建设本科；具有化学、化学生物学、材料和环境生态检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "天津农学院", "天津市", "天津市", "https://www.tjau.edu.cn/",
        "天津农学院农学与资源环境学院简介", "https://nx.tjau.edu.cn/xygk/xyjj.htm",
        "官网列有生物技术、环境科学等本科专业，作物学为天津市重点学科，并设置环境监测课程与科研平台。",
        "天津市一流学科建设农林本科；具有生物、环境、食品、水产和农业检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "天津职业技术师范大学", "天津市", "天津市", "https://www.tute.edu.cn/",
        "天津职业技术师范大学材料科学与工程学科",
        "https://yzb.tute.edu.cn/info/1131/6872.htm",
        "官网列明学校为天津市高水平特色大学，材料科学与工程形成材料成形、增材制造和表面工程等方向。",
        "天津市高水平特色普通本科；具有材料成形、增材制造、表面工程和质量检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "天津商业大学", "天津市", "天津市", "https://www.tjcu.edu.cn/",
        "天津商业大学生物技术与食品科学学院简介", "https://zs.tjcu.edu.cn/info/1038/1157.htm",
        "官网列有食品科学与工程天津市重点学科，以及生物工程、制药、食品质量安全、应用化学和食品药品实验平台。",
        "天津市重点学科建设本科；具有食品、生物、制药、应用化学和食品药品检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "天津城建大学", "天津市", "天津市", "https://www.tcu.edu.cn/",
        "天津城建大学本科专业目录", "https://www.tcu.edu.cn/rcpy/bkjy.htm",
        "官网本科目录列有材料科学与工程、环境工程和给排水科学与工程，并建有水质与绿色建筑材料科研平台。",
        "天津市一流培育学科建设本科；具有环境、水质、建筑材料和工程检测方向。",
    ),
)


# 原因区分既有、行业不符、公安专批、普通本科待补证、职业和民办，避免把“未核验”写成“无专业”。
PROVINCIAL_KEY_BATCH_09_EXCLUSION_REASONS: dict[str, str] = {}

for name in (
    "北京大学", "中国人民大学", "清华大学", "北京交通大学", "北京工业大学", "北京航空航天大学",
    "北京理工大学", "北京科技大学", "北京化工大学", "北京邮电大学", "中国农业大学", "北京林业大学",
    "北京协和医学院", "北京中医药大学", "北京师范大学", "首都师范大学", "中央民族大学", "中国科学院大学",
    "华北电力大学", "北京体育大学", "首都体育学院", "中国人民公安大学", "南开大学", "天津大学",
    "天津工业大学", "天津医科大学", "天津中医药大学", "河北工业大学", "天津体育学院",
):
    PROVINCIAL_KEY_BATCH_09_EXCLUSION_REASONS[name] = "已在此前重点/双一流/体育批次进入正式单位，本批不重复创建。"

for name in (
    "北京外国语大学", "中国传媒大学", "中央财经大学", "对外经济贸易大学", "外交学院", "中国政法大学",
    "中央音乐学院", "中国音乐学院", "中央美术学院", "中央戏剧学院", "北京电影学院", "北京舞蹈学院",
    "中国戏曲学院", "北京第二外国语学院", "首都经济贸易大学", "北京物资学院", "北京语言大学",
    "国际关系学院", "中华女子学院", "中国社会科学院大学", "天津外国语大学", "天津财经大学",
    "天津音乐学院", "天津美术学院",
):
    PROVINCIAL_KEY_BATCH_09_EXCLUSION_REASONS[name] = "以财经、政法、语言、传媒或艺术学科为主，未发现符合本批标准的生化环材重点建设证据。"

for name in ("北京警察学院", "中国消防救援学院", "天津公安警官职业学院"):
    PROVINCIAL_KEY_BATCH_09_EXCLUSION_REASONS[name] = "按公安及公共安全单位全量规则留待专批，避免误标为普通高校客户类型。"

for name in (
    "北京信息科技大学", "北京电子科技学院", "中国劳动关系学院", "天津中德应用技术大学",
):
    PROVINCIAL_KEY_BATCH_09_EXCLUSION_REASONS[name] = (
        "存在本科专业或行业服务方向，但本轮未取得重点/一流建设身份与目标学科同时成立的充分证据，暂缓到普通本科补充批。"
    )

for name in ("北京青年政治学院", "北京体育职业学院", "天津体育职业学院", "天津职业大学"):
    PROVINCIAL_KEY_BATCH_09_EXCLUSION_REASONS[name] = "职业教育院校，不属于当前公办普通本科筛选范围。"

for name in (
    "北京城市学院", "北京金融科技学院", "北京邮电大学世纪学院", "首都师范大学科德学院",
    "北京工业大学耿丹学院", "北京第二外国语学院中瑞酒店管理学院", "天津天狮学院", "天津传媒学院",
    "天津仁爱学院",
):
    PROVINCIAL_KEY_BATCH_09_EXCLUSION_REASONS[name] = "民办本科或独立学院，不属于当前省属重点公办普通本科范围。"


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把京津核验种子转换为正式候选，并以“城市+校名”形成严格主校区 POI 查询。"""

    assert len(VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_09) == 20
    assert len({seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_09}) == 20
    return tuple(
        UniversityCandidate(
            name=seed.name,
            website=seed.website,
            province=seed.province,
            city=seed.city,
            district=None,
            address=OFFICIAL_MAIN_CAMPUS_ADDRESSES.get(seed.name, f"{seed.city}{seed.name}"),
            evidence_title=seed.evidence_title,
            evidence_url=seed.evidence_url,
            evidence_excerpt=seed.evidence_excerpt,
            inclusion_reason=seed.inclusion_reason,
            tags=("高校", "省属重点本科", "官网专业证据", "省属重点第09批"),
        )
        for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_09
    )


def main() -> None:
    """幂等创建京津核验批；重复运行仅回写名录关联，不覆盖既有或人工核验数据。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 省属重点本科生化环材核验第09批",
            source_scope=(
                "北京、天津重点/双一流/高水平建设公办普通本科；逐校核验生物、环境、化学、材料、医药、"
                "食品或检测方向。排除既有、财经政法语言艺术、民办和职业院校；公安及证据不足项留待专批。"
            ),
            source_url=MOE_2026_UNIVERSITY_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-provincial-key-import",
        )
    print(
        f"省属重点本科第09批完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
