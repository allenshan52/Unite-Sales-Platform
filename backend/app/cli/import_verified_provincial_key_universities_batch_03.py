"""导入省属重点本科第 03 批：保存皖闽赣鲁官方建设依据，并排队定位主校区。"""

from app.cli.import_verified_provincial_key_universities_batch_01 import (
    MOE_UNIVERSITY_DIRECTORY,
    VerifiedProvincialKeySeed,
)
from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


# 第 03 批只保留四省官方重点/高水平建设名单中具备目标专业方向的公办本科。
VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_03 = (
    # 安徽：学校官网同时证明省级建设层次和生化环材、医药或食品农业方向。
    VerifiedProvincialKeySeed(
        "安徽师范大学", "安徽省", "芜湖市", "https://www.ahnu.edu.cn/", "安徽师范大学学校简介",
        "https://www.ahnu.edu.cn/xxgk/xxjj.htm",
        "官网明确学校为安徽省重点综合性大学、特色高水平大学和双一流培育高校，并设化学材料、生命、生态环境等学院。",
        "安徽省重点本科；具有化学、材料、生命和生态环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "安徽农业大学", "安徽省", "合肥市", "https://www.ahau.edu.cn/", "安徽农业大学学科专业材料",
        "https://fgc.ahau.edu.cn/__local/B/9A/C3/204E17C17E96CC302E0FDB777F1_D980EB32_2062F.pdf",
        "学校官方材料列有化学、生物学、生态学、环境科学、食品科学、生物制药和农业资源等学科专业。",
        "安徽省重点农业本科；具有生物、生态环境、食品、化学和农业检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "安徽医科大学", "安徽省", "合肥市", "https://www.ahmu.edu.cn/", "安徽医科大学学校简介",
        "https://www.ahmu.edu.cn/4356/list.htm",
        "官网明确学校为安徽省属重点大学和地方特色高水平大学，办学覆盖医学、公共卫生、药学和生命科学。",
        "安徽省重点医科本科；具有医学检验、公共卫生、药学和生物医学方向。",
    ),
    VerifiedProvincialKeySeed(
        "安徽工业大学", "安徽省", "马鞍山市", "https://www.ahut.edu.cn/", "安徽工业大学学校简介",
        "https://www.ahut.edu.cn/xxgk/xxjj.htm",
        "官网明确学校为安徽省地方特色高水平大学，材料、化学、环境与资源等学科方向符合筛选规则。",
        "安徽省高水平建设本科；具有材料、化学化工、环境和资源检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "安徽理工大学", "安徽省", "淮南市", "https://www.aust.edu.cn/", "安徽理工大学学校概况",
        "https://www.aust.edu.cn/xxgk.htm",
        "官网明确学校入选安徽省双一流培育建设，相关学科覆盖化学、材料、环境、安全和资源。",
        "安徽省双一流培育本科；具有化学、材料、环境、资源和安全检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "安徽中医药大学", "安徽省", "合肥市", "https://www.ahtcm.edu.cn/", "安徽中医药大学学校简介",
        "https://www.ahtcm.edu.cn/xxgk/xxjj.htm",
        "官网明确学校为地方特色高水平大学和安徽省双一流重点建设高校，重点覆盖中医药、中药和药学。",
        "安徽省高水平医药本科；具有中药、药学、生物医学和质量检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "安徽工程大学", "安徽省", "芜湖市", "https://www.ahpu.edu.cn/", "安徽工程大学建设与学科材料",
        "https://cee.ahpu.edu.cn/_upload/article/files/d4/36/0373db044eebbeb2257f9c993761/6341fa59-3774-47bd-aa07-b7af951b9db3.pdf",
        "学校官方材料说明其为安徽省重点建设高校，相关方向覆盖化学、环境、生物、食品和材料工程。",
        "安徽省重点建设本科；具有化学、环境、生物、食品和材料方向。",
    ),

    # 福建：以省教育厅公布的双一流建设名单为层级依据，逐校保留目标方向。
    VerifiedProvincialKeySeed(
        "华侨大学", "福建省", "泉州市", "https://www.hqu.edu.cn/", "华侨大学学校简介",
        "https://www.hqu.edu.cn/hdgk/xxjj.htm",
        "官网明确学校入选福建省双一流建设高校，化学、材料和环境生态等学科进入 ESI 前1%。",
        "福建省双一流建设本科；具有化学、材料、环境和生物方向。",
    ),
    VerifiedProvincialKeySeed(
        "福建农林大学", "福建省", "福州市", "https://www.fafu.edu.cn/", "福建农林大学学校简介",
        "https://www.fafu.edu.cn/5244/list.htm",
        "官网明确学校为福建省重点建设高水平大学和一流大学建设高校，优势覆盖农业、生命、生态、食品和生物安全。",
        "福建省高水平农业本科；具有生命、生态环境、食品和农业检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "福建师范大学", "福建省", "福州市", "https://www.fjnu.edu.cn/", "福建师范大学一流学科建设简介",
        "https://yjsy.fjnu.edu.cn/4219/list.htm",
        "官网明确学校入选福建省一流大学建设高校；学校设化学与材料、生命科学和环境相关教学科研单位。",
        "福建省一流大学建设本科；具有化学、材料、生命和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "福建理工大学", "福建省", "福州市", "https://www.fjut.edu.cn/", "福建理工大学学校简介",
        "https://www.fjut.edu.cn/2023/1130/c403a225856/page.htm",
        "官网明确学校为福建省重点建设高校、一流学科建设高校和一流应用型建设高校，材料与化学方向突出。",
        "福建省重点建设本科；具有材料、化学化工和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "集美大学", "福建省", "厦门市", "https://www.jmu.edu.cn/", "集美大学学校简介",
        "https://zsb.jmu.edu.cn/lxszs/zw.htm",
        "官网明确学校为福建省重点建设高校和双一流建设高校，优势覆盖水产、食品和生物。",
        "福建省双一流建设本科；具有水产、食品安全、生物和海洋检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "福建医科大学", "福建省", "福州市", "https://www.fjmu.edu.cn/", "福建省一流大学和一流学科建设名单",
        "https://jyt.fujian.gov.cn/jyyw/jyt/201803/t20180323_3384785.htm",
        "福建省教育厅将学校列为一流学科建设高校；医学、药学、公共卫生和医学技术符合目标方向。",
        "福建省一流学科建设医科本科；具有医学检验、药学、公共卫生和生物医学方向。",
    ),
    VerifiedProvincialKeySeed(
        "福建中医药大学", "福建省", "福州市", "https://www.fjtcm.edu.cn/", "福建省一流大学和一流学科建设名单",
        "https://jyt.fujian.gov.cn/jyyw/jyt/201803/t20180323_3384785.htm",
        "福建省教育厅将学校列为一流学科建设高校；中医药、中药、药学和医学检验符合目标方向。",
        "福建省一流学科建设医药本科；具有中药、药学、生物医学和质量检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "闽江学院", "福建省", "福州市", "https://www.mju.edu.cn/", "闽江学院学校简介",
        "https://www.mju.edu.cn/2023/0107/c1437a143781/page.htm",
        "官网明确学校为福建省一流应用型建设高校，相关方向覆盖资源环境、材料化学、海洋生态和诊断试剂。",
        "福建省一流应用型本科；具有资源环境、材料化学、海洋生态和生物检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "泉州师范学院", "福建省", "泉州市", "https://www.qztc.edu.cn/", "泉州师范学院化工与材料学院简介",
        "https://www.qztc.edu.cn/hcxy/2025/0417/c586a283948/page.htm",
        "官网说明材料与化工为省一流应用型重点建设主干学科，并覆盖化学、材料和环境相关方向。",
        "福建省一流学科建设本科；具有化学、材料和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "闽南师范大学", "福建省", "漳州市", "https://www.mnnu.edu.cn/", "闽南师范大学学校简介",
        "https://xwgk.mnnu.edu.cn/info/1022/7013.htm",
        "官网明确学校为福建省双一流建设高校，相关专业覆盖化学、应用化学、食品和生物。",
        "福建省双一流建设本科；具有化学、食品、生物和分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "厦门理工学院", "福建省", "厦门市", "https://www.xmut.edu.cn/", "福建省一流大学和一流学科建设名单",
        "https://jyt.fujian.gov.cn/jyyw/jyt/201803/t20180323_3384785.htm",
        "福建省教育厅将学校列为一流学科建设高校；材料、环境与化学工程方向符合筛选规则。",
        "福建省一流学科建设本科；具有材料、环境和化学工程方向。",
    ),

    # 江西：以省级一流学科建设名单为底表，排除既有南昌大学和纯财经高校。
    VerifiedProvincialKeySeed(
        "华东交通大学", "江西省", "南昌市", "https://www.ecjtu.edu.cn/", "华东交通大学学校简介",
        "https://www.ecjtu.edu.cn/gyjd/xxjj1.htm",
        "官网列有江西省一流学科，材料、化学和环境生态等学科方向符合筛选规则。",
        "江西省一流学科建设本科；具有材料、化学和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "东华理工大学", "江西省", "南昌市", "https://www.ecut.edu.cn/", "东华理工大学学校简介",
        "https://www.ecut.edu.cn/7560/list.htm",
        "官网介绍省级一流学科建设及水资源环境、化学材料、核科学和地质分析等优势。",
        "江西省一流学科建设本科；具有水环境、化学、材料、核与地质检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "南昌航空大学", "江西省", "南昌市", "https://www.nchu.edu.cn/", "南昌航空大学学校简介",
        "https://www.nchu.edu.cn/xxgk/xxjj",
        "官网列有省级一流学科，材料、化学、环境和仪器检测等方向符合筛选规则。",
        "江西省一流学科建设本科；具有材料、化学、环境和仪器检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "江西理工大学", "江西省", "赣州市", "https://www.jxust.edu.cn/", "江西理工大学学校简介",
        "https://www.jxust.edu.cn/sy1/xxgk/xxjj.htm",
        "官网明确冶金、矿业和材料为省一流建设学科，化学与环境生态等学科进入 ESI 前1%。",
        "江西省一流学科建设本科；具有冶金、材料、化学、矿产和环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "景德镇陶瓷大学", "江西省", "景德镇市", "https://www.jcu.edu.cn/", "景德镇陶瓷大学学校简介",
        "https://www.jcu.edu.cn/about/xxjj.htm",
        "官网介绍省一流学科建设及陶瓷材料、化学和环境相关教学科研方向。",
        "江西省一流学科建设本科；具有无机材料、化学和环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "江西农业大学", "江西省", "南昌市", "https://www.jxau.edu.cn/", "江西农业大学学校简介",
        "https://www.jxau.edu.cn/xqzl/xxjj.htm",
        "官网明确学校为江西省特色高水平大学和一流学科建设高校，优势覆盖农业、生命、食品和生态环境。",
        "江西省高水平农业本科；具有农业、生命、食品和生态环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "江西中医药大学", "江西省", "南昌市", "https://www.jxutcm.edu.cn/", "江西中医药大学学校简介",
        "https://www.jxutcm.edu.cn/info/1050/16932.htm",
        "官网介绍省一流中医药学科建设，相关方向覆盖中药、药学、化学和农业科学。",
        "江西省一流学科建设医药本科；具有中药、药学、化学和质量检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "赣南医科大学", "江西省", "赣州市", "https://www.gmu.cn/", "赣南医科大学学校简介",
        "https://www.gmu.cn/jlm/xxgk1/xxjj.htm",
        "官网明确学校为江西省一流学科建设高校，临床医学、药学、生物医学和医学技术符合筛选规则。",
        "江西省一流学科建设医科本科；具有医学检验、药学和生物医学方向。",
    ),
    VerifiedProvincialKeySeed(
        "江西师范大学", "江西省", "南昌市", "https://www.jxnu.edu.cn/", "江西师范大学学校简介",
        "https://www.jxnu.edu.cn/9/list.htm",
        "官网明确学校为江西省优先发展的省属重点师范大学，化学、材料、环境和农业科学方向符合筛选规则。",
        "江西省重点本科；具有化学、材料、环境和生命科学方向。",
    ),
    VerifiedProvincialKeySeed(
        "赣南师范大学", "江西省", "赣州市", "https://www.gnnu.edu.cn/", "赣南师范大学学校简介",
        "https://www.gnnu.edu.cn/xxgk/xxjj.htm",
        "官网明确学校进入江西省双一流建设，化学、植物动物科学和园艺农业方向符合筛选规则。",
        "江西省双一流建设本科；具有化学、生命和农业检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "江西科技师范大学", "江西省", "南昌市", "https://www.jxstnu.edu.cn/", "江西科技师范大学学校简介",
        "https://www.jxstnu.edu.cn/xxgk/xxjj.htm",
        "官网介绍省部共建高水平职业师范大学建设，专业覆盖化学、材料、生物制药和食品科学。",
        "江西省高水平建设本科；具有化学、材料、生物制药和食品方向。",
    ),
    VerifiedProvincialKeySeed(
        "南昌工程学院", "江西省", "南昌市", "https://www.nit.edu.cn/", "南昌工程学院学校简介",
        "https://www.nit.edu.cn/nggk/xyjj.htm",
        "官网明确学校为江西省一流学科建设高校，水利、环境生态和农业工程方向符合筛选规则。",
        "江西省一流学科建设本科；具有水环境、生态和农业工程检测方向。",
    ),

    # 山东：以省教育厅高水平大学名单为底表，排除纯财经高校山东财经大学。
    VerifiedProvincialKeySeed(
        "山东师范大学", "山东省", "济南市", "https://www.sdnu.edu.cn/", "山东师范大学学校简介",
        "https://www.sdnu.edu.cn/overview/introduction.htm",
        "官网明确学校为山东省属重点大学和高水平大学冲一流建设高校，化学、生物、材料和环境方向符合筛选规则。",
        "山东省高水平建设本科；具有化学、生物、材料和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "山东农业大学", "山东省", "泰安市", "https://www.sdau.edu.cn/", "山东省高水平大学建设名单",
        "https://edu.shandong.gov.cn/art/2020/12/4/art_11969_10094441.html",
        "山东省教育厅将学校列为高水平大学冲一流建设高校；农业、生物、食品和资源环境方向符合筛选规则。",
        "山东省高水平农业本科；具有农业、生物、食品和资源环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "青岛大学", "山东省", "青岛市", "https://www.qdu.edu.cn/", "青岛大学学校简介",
        "https://www.qdu.edu.cn/info/1003/15919.htm",
        "官网介绍省高水平大学建设及医学、材料、化学、药学和生物学等优势方向。",
        "山东省高水平建设本科；具有医学、材料、化学、药学和生物方向。",
    ),
    VerifiedProvincialKeySeed(
        "山东科技大学", "山东省", "青岛市", "https://www.sdust.edu.cn/", "山东科技大学学校简介",
        "https://www.sdust.edu.cn/xxgk/xxjj.htm",
        "官网明确学校为山东省高水平大学冲一流建设高校，化学、生物、材料和环境方向符合筛选规则。",
        "山东省高水平建设本科；具有化学、生物、材料、环境和资源检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "济南大学", "山东省", "济南市", "https://www.ujn.edu.cn/", "济南大学学校简介",
        "https://www.ujn.edu.cn/xxgk/xxjj.htm",
        "官网明确学校为山东省重点建设大学和高水平大学冲一流建设高校，材料、化学、环境和生物方向突出。",
        "山东省高水平建设本科；具有材料、化学、环境和生物方向。",
    ),
    VerifiedProvincialKeySeed(
        "齐鲁工业大学", "山东省", "济南市", "https://www.qlu.edu.cn/", "山东省高水平大学建设名单",
        "https://edu.shandong.gov.cn/art/2020/12/4/art_11969_10094441.html",
        "山东省教育厅将学校列为高水平大学冲一流建设高校；轻工、生物、食品、环境、化学和材料方向符合筛选规则。",
        "山东省高水平建设本科；具有生物、食品、环境、化学、材料和轻工检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "山东第一医科大学", "山东省", "济南市", "https://www.sdfmu.edu.cn/", "山东第一医科大学学校简介",
        "https://www.sdfmu.edu.cn/xxgk1/xxjj.htm",
        "官网明确学校为山东省重点建设大学和高水平大学冲一流建设高校，医学、药学、生物和医学技术方向突出。",
        "山东省高水平医科本科；具有医学检验、药学、生物医学和公共卫生方向。",
    ),
    VerifiedProvincialKeySeed(
        "曲阜师范大学", "山东省", "济宁市", "https://www.qfnu.edu.cn/", "曲阜师范大学学校简介",
        "https://www.qfnu.edu.cn/ljxx/xxjj.htm",
        "官网和省级名单确认高水平大学建设层次，化学、材料、环境和生物学方向符合筛选规则。",
        "山东省高水平建设本科；具有化学、材料、环境和生物方向。",
    ),
    VerifiedProvincialKeySeed(
        "青岛科技大学", "山东省", "青岛市", "https://www.qust.edu.cn/", "山东省高水平大学建设名单",
        "https://edu.shandong.gov.cn/art/2020/12/4/art_11969_10094441.html",
        "山东省教育厅将学校列为高水平大学强特色建设高校；材料、化学化工和环境方向符合筛选规则。",
        "山东省高水平特色本科；具有材料、化学化工和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "山东中医药大学", "山东省", "济南市", "https://www.sdutcm.edu.cn/", "山东省高水平大学建设名单",
        "https://edu.shandong.gov.cn/art/2020/12/4/art_11969_10094441.html",
        "山东省教育厅将学校列为高水平大学强特色建设高校；中医药、中药、药学和生物医学方向符合筛选规则。",
        "山东省高水平医药本科；具有中药、药学、生物医学和质量检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "山东理工大学", "山东省", "淄博市", "https://www.sdut.edu.cn/", "山东省高水平大学建设名单",
        "https://edu.shandong.gov.cn/art/2020/12/4/art_11969_10094441.html",
        "山东省教育厅将学校列为高水平大学强特色建设高校；材料、化学、农业、资源与环境方向符合筛选规则。",
        "山东省高水平特色本科；具有材料、化学、农业、资源和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "青岛理工大学", "山东省", "青岛市", "https://www.qut.edu.cn/", "山东省高水平大学建设名单",
        "https://edu.shandong.gov.cn/art/2020/12/4/art_11969_10094441.html",
        "山东省教育厅将学校列为高水平大学强特色建设高校；材料、环境和市政工程检测方向符合筛选规则。",
        "山东省高水平特色本科；具有材料、环境和市政工程检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "青岛农业大学", "山东省", "青岛市", "https://www.qau.edu.cn/", "山东省高水平大学建设名单",
        "https://edu.shandong.gov.cn/art/2020/12/4/art_11969_10094441.html",
        "山东省教育厅将学校列为高水平大学强特色建设高校；农业、水产、食品、生物和环境方向符合筛选规则。",
        "山东省高水平农业本科；具有农业、水产、食品、生物和环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "烟台大学", "山东省", "烟台市", "https://www.ytu.edu.cn/", "山东省高水平大学建设名单",
        "https://edu.shandong.gov.cn/art/2020/12/4/art_11969_10094441.html",
        "山东省教育厅将学校列为高水平大学强特色建设高校；药学、化学、生物、材料和环境方向符合筛选规则。",
        "山东省高水平特色本科；具有药学、化学、生物、材料和环境方向。",
    ),
)


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把已核验种子转成正式候选，仅以“城市+校名”交给严格主校区 POI 匹配。"""

    assert len(VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_03) == 44
    assert len({seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_03}) == 44
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
            tags=("高校", "省属重点本科", "官网专业证据", "省属重点第03批"),
        )
        for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_03
    )


def main() -> None:
    """幂等创建皖闽赣鲁第 03 批，不覆盖重复项或人工核验结果。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 省属重点本科生化环材核验第03批",
            source_scope=(
                "安徽、福建、江西、山东省级重点/高水平/一流学科建设公办本科；按省级官方名单建立边界，"
                "再逐校确认生物、环境、化学、材料、医药、食品农业或检测方向。排除既有高校与纯财经高校。"
            ),
            source_url=MOE_UNIVERSITY_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-provincial-key-import",
        )
    print(
        f"省属重点本科第03批完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
