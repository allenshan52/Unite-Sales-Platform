"""导入省属重点本科第 07 批：核验贵州、云南、西藏目标高校并排队定位主校区。"""

from app.cli.import_verified_provincial_key_universities_batch_01 import (
    MOE_UNIVERSITY_DIRECTORY,
    VerifiedProvincialKeySeed,
)
from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


# 只纳入建设层次和生化环材、医药、农林或检测方向均有官方公开依据的公办普通本科。
VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_07 = (
    VerifiedProvincialKeySeed(
        "贵州师范大学", "贵州省", "贵阳市", "https://www.gznu.edu.cn/",
        "贵州师范大学一流建设学科", "https://www.gznu.edu.cn/xkjs/yljsxk.htm",
        "官网列有国内一流建设学科和区域一流建设学科，地理学、生物学、化学等方向具有明确建设基础。",
        "贵州省一流学科建设本科；具有生物、化学、地理环境与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "贵州医科大学", "贵州省", "贵阳市", "https://www.gmc.edu.cn/",
        "贵州医科大学学校简介", "https://www.gmc.edu.cn/xxgk/xxjj.htm",
        "官网明确学校建有贵州省国内一流建设学科群和省级一流学科，覆盖基础医学、公共卫生、药学及生物化学方向。",
        "贵州省重点建设医科本科；具有药学、生物医学、公共卫生和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "遵义医科大学", "贵州省", "遵义市", "https://www.zmu.edu.cn/",
        "遵义医科大学学科建设介绍", "https://fzghc.zmu.edu.cn/info/1103/2245.htm",
        "官网列有临床医学、基础医学、药学和生物学建设基础，化学等学科进入 ESI 全球前1%。",
        "贵州省重点建设医科本科；具有基础医学、药学、生物、化学和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "贵州中医药大学", "贵州省", "贵阳市", "https://www.gzy.edu.cn/",
        "贵州中医药大学学校简介", "https://www.gzy.edu.cn/info/1055/7750.htm",
        "官网介绍学校为省级重点支持高校，中医学和中药学学科群进入贵州省国内一流建设范围。",
        "贵州省重点建设中医药本科；具有中药学、药物分析、质量控制和生物医药方向。",
    ),
    VerifiedProvincialKeySeed(
        "贵州民族大学", "贵州省", "贵阳市", "https://www.gzmu.edu.cn/",
        "贵州民族大学学校简介", "https://www.gzmu.edu.cn/xxjj/xxjj.htm",
        "官网列有贵州省国内一流建设学科群和区域一流建设学科，并建有喀斯特环境、民族医药等科研平台。",
        "贵州省一流学科建设本科；具有环境生态、民族医药、生物资源和分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "贵州理工学院", "贵州省", "贵阳市", "https://www.git.edu.cn/",
        "贵州理工学院材料与能源工程学院简介", "https://www.git.edu.cn/clxy/bmgk/xyjj.htm",
        "官网明确材料科学与工程入选贵州省第二批区域内一流建设学科，并设材料、化工与资源环境相关方向。",
        "贵州省区域一流学科建设本科；具有材料、化学化工、资源环境和质量检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "贵州师范学院", "贵州省", "贵阳市", "https://www.gznc.edu.cn/",
        "贵州师范学院学校简介", "https://www.gznc.edu.cn/xxgk/xxjj.htm",
        "官网明确学校为贵州省双一流建设单位，设有区域一流建设学科及生物、化学、地理资源环境相关专业。",
        "贵州省双一流建设本科；具有生物、化学、资源环境与实验检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "昆明理工大学", "云南省", "昆明市", "https://www.kmust.edu.cn/",
        "昆明理工大学学校简介", "https://www.kmust.edu.cn/xxgk/xxjj.htm",
        "官网明确学校是云南省规模最大、办学层次齐全的重点大学，材料、冶金、环境和化学工程为重要学科方向。",
        "云南省重点本科；具有材料、冶金、环境、化学化工和分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "云南农业大学", "云南省", "昆明市", "https://www.ynau.edu.cn/",
        "云南农业大学学校简介", "https://www.ynau.edu.cn/info/1404/21431.htm",
        "官网明确学校为云南省属重点大学，形成农学、生物、食品、资源环境和质量安全相关学科体系。",
        "云南省属重点农业本科；具有生物、食品安全、资源环境和农业检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "云南师范大学", "云南省", "昆明市", "https://www.ynnu.edu.cn/",
        "云南师范大学学校简介", "https://www.ynnu.edu.cn/ysgk/xxjj.htm",
        "官网列有云南省一流建设学科，化学、环境生态学和生物学与生物化学等进入 ESI 全球前1%。",
        "云南省一流学科建设本科；具有化学、生物、环境生态和材料检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "昆明医科大学", "云南省", "昆明市", "https://www.kmmc.cn/",
        "昆明医科大学学校简介", "https://www.kmmc.cn/mpages_2588_54245.aspx",
        "官网明确学校是云南省重点大学和一流学科建设高校，基础医学、药学和公共卫生等方向基础完整。",
        "云南省重点医科本科；具有基础医学、药学、公共卫生和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "西南林业大学", "云南省", "昆明市", "https://www.swfu.edu.cn/",
        "西南林业大学学校简介", "https://www.swfu.edu.cn/xxgk/xxjj.htm",
        "官网列有云南省重点支持的一流建设学科，生态、生物、环境、林产化工及材料等方向特色明确。",
        "云南省一流学科建设林业本科；具有生态、生物、环境、化学和生物质材料检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "云南中医药大学", "云南省", "昆明市", "https://www.ynucm.edu.cn/",
        "云南中医药大学学校简介", "https://www.ynucm.edu.cn/xxgk/yzjj.htm",
        "官网列有云南省一流建设学科和中医药高水平建设任务，中药学与药物质量研究方向明确。",
        "云南省一流学科建设中医药本科；具有中药学、药物分析、质量控制和生物医药方向。",
    ),
    VerifiedProvincialKeySeed(
        "大理大学", "云南省", "大理市", "https://www.dali.edu.cn/",
        "教育部教育质量评估中心大理大学简介", "https://heec.cahe.edu.cn/school/330/jianjie",
        "教育部评估中心介绍学校为省州共建本科，以医药学、生物学和生态学为优势，并为省级新增博士建设单位。",
        "云南省重点建设本科；具有医药、生物、生态环境和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "云南民族大学", "云南省", "昆明市", "https://www.ymu.edu.cn/",
        "云南民族大学学校简介", "https://www.ymu.edu.cn/xxgk/xxjj.htm",
        "官网列有省级重点和优势特色学科，并建有民族医药、生物资源、化学及生物基材料科研方向。",
        "云南省重点学科建设本科；具有化学、民族医药、生物资源和生物基材料方向。",
    ),
    VerifiedProvincialKeySeed(
        "西藏农牧大学", "西藏自治区", "林芝市", "https://www.xza.edu.cn/",
        "西藏自治区政府西藏农牧大学预算公开", "https://www.xizang.gov.cn/zwgk/zdxxlygk/czyjsgk/202602/t20260211_524544.html",
        "自治区政府公开资料列有11个省部级及以上重点学科，覆盖作物、林学、兽医、食品、生物与医药等方向。",
        "西藏自治区重点农林本科；具有生物、生态、食品安全、资源环境和农牧检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "西藏藏医药大学", "西藏自治区", "拉萨市", "https://ttmc.edu.cn/",
        "西藏藏医药大学博士招生简章", "https://ttmc.edu.cn/info/1004/9558.htm",
        "官网列有国家中医药管理局和自治区重点学科，以及藏医药基础、藏药质量控制和高原生物科研平台。",
        "西藏自治区重点藏医药本科；具有藏药、药物分析、质量控制和高原生物方向。",
    ),
)


# 对本批未纳入的公办、职业本科、公安及民办院校保留边界原因，方便后续普通本科或专类批次复核。
PROVINCIAL_KEY_BATCH_07_EXCLUSION_REASONS = {
    "贵州大学": "已在此前 211/双一流批次进入正式单位，本批不重复创建。",
    "云南大学": "已在此前 211/双一流批次进入正式单位，本批不重复创建。",
    "西藏大学": "已在此前 211/双一流批次进入正式单位，本批不重复创建。",
    "贵州财经大学": "财经类办学为主，未发现符合本批标准的生化环材重点建设学科证据。",
    "贵州商学院": "商科类办学为主，未发现符合本批标准的生化环材重点建设学科证据。",
    "云南财经大学": "财经类办学为主，未发现符合本批标准的生化环材重点建设学科证据。",
    "云南艺术学院": "艺术类院校，本轮未发现符合标准的生化环材专业或研究方向。",
    "贵州警察学院": "按公安单位全量规则留待公安专批，避免误标为普通高校客户类型。",
    "云南警官学院": "按公安单位全量规则留待公安专批，避免误标为普通高校客户类型。",
    "西藏民族大学": "基础医学方向符合，但主校区位于陕西咸阳；为保证地图省市字段真实，转陕西跨省校址批处理。",
    "贵州交通职业大学": "职业本科，不属于当前普通本科筛选范围。",
    "贵州工业职业技术大学": "职业本科，不属于当前普通本科筛选范围。",
    "贵州轻工职业大学": "职业本科，不属于当前普通本科筛选范围。",
    "贵阳康养职业大学": "职业本科，不属于当前普通本科筛选范围。",
    "铜仁职业技术大学": "职业本科，不属于当前普通本科筛选范围。",
    "云南交通职业技术大学": "职业本科，不属于当前普通本科筛选范围。",
    "昆明冶金职业大学": "职业本科，不属于当前普通本科筛选范围。",
}

for name in (
    "六盘水师范学院", "兴义民族师范学院", "凯里学院", "安顺学院", "贵州工程应用技术学院",
    "贵阳学院", "遵义师范学院", "铜仁学院", "黔南民族师范学院",
    "丽江师范学院", "保山学院", "德宏师范学院", "文山学院", "昆明学院", "昭通学院",
    "普洱学院", "曲靖健康医学院", "曲靖师范学院", "楚雄师范学院", "滇西应用技术大学",
    "滇西科技师范学院", "玉溪师范学院", "红河学院", "拉萨师范学院",
):
    PROVINCIAL_KEY_BATCH_07_EXCLUSION_REASONS[name] = (
        "存在本科专业或地方服务方向，但本轮未取得省属重点、一流建设身份与目标学科同时成立的充分证据，暂缓到普通本科补充批。"
    )

for name in (
    "茅台学院", "贵州中医药大学时珍学院", "贵州医科大学神奇民族医药学院", "贵州工商职业大学",
    "贵州黔南科技学院", "贵州黔南经济学院", "贵阳人文科技学院", "贵阳信息科技学院",
    "遵义医科大学医学与科技学院", "丽江文化旅游学院", "云南工商学院", "云南经济管理学院",
    "昆明传媒学院", "昆明医科大学海源学院", "昆明城市学院", "昆明文理学院",
    "昆明理工大学津桥学院", "昆明科技职业大学", "滇池学院",
):
    PROVINCIAL_KEY_BATCH_07_EXCLUSION_REASONS[name] = (
        "民办本科，不属于当前省属重点公办普通本科筛选范围。"
    )


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把第 07 批核验种子转换为候选，并用城市加校名形成严格的主校区 POI 查询。"""

    assert len(VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_07) == 17
    assert len({seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_07}) == 17
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
            tags=("高校", "省属重点本科", "官网专业证据", "省属重点第07批"),
        )
        for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_07
    )


def main() -> None:
    """幂等创建贵云藏核验批；重复项只留批次记录，不覆盖既有或人工核验数据。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 省属重点本科生化环材核验第07批",
            source_scope=(
                "贵州、云南、西藏公办普通本科；结合教育主管部门、自治区政府和学校官网，"
                "确认省属重点/一流建设身份及生物、环境、化学、材料、医药、农林食品或检测方向。"
                "排除既有、纯财经艺术、民办、职业本科和公安专批；证据不足项留到普通本科补充批。"
            ),
            source_url=MOE_UNIVERSITY_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-provincial-key-import",
        )
    print(
        f"省属重点本科第07批完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
