"""导入省属重点本科第 06 批：保存四川困难批证据、筛选结论并排队定位主校区。"""

from app.cli.import_verified_provincial_key_universities_batch_01 import (
    MOE_UNIVERSITY_DIRECTORY,
    VerifiedProvincialKeySeed,
)
from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


# 本批只纳入省级建设身份和目标学科均有官方证据的普通公办本科。
VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_06 = (
    VerifiedProvincialKeySeed(
        "西昌学院", "四川省", "西昌市", "https://www.xcc.edu.cn/",
        "西昌学院校情总览", "https://xcc.edu.cn/xy/xygk3668/xqzl7/index.html",
        "官网明确作物学为四川省高等学校“双一流”建设贡嘎计划建设学科，并形成农科与生态研究特色。",
        "四川贡嘎计划建设本科；具有作物、生物、农业资源与生态环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "四川师范大学", "四川省", "成都市", "https://www.sicnu.edu.cn/",
        "四川师范大学学校简介", "https://www.sicnu.edu.cn/xxgk/sdjj.htm",
        "官网明确 5 个学科入选贡嘎计划；化学、材料科学和环境/生态学进入 ESI 全球前1%。",
        "四川贡嘎计划建设本科；具有化学、材料、环境生态与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "西华师范大学", "四川省", "南充市", "https://www.cwnu.edu.cn/",
        "教育部评估中心西华师范大学简介", "https://heec.cahe.edu.cn/school/236/jianjie",
        "官方院校简介列有生态学与生态治理省级一流学科领域，化学进入 ESI 全球前1%，并建有生态研究院及重点实验室。",
        "四川省级一流学科建设本科；具有生态、生物、化学、环境与材料检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "绵阳师范学院", "四川省", "绵阳市", "https://www.mtc.edu.cn/",
        "绵阳师范学院招生信息网学校简介", "https://zs.mtc.edu.cn/school_view.php?action_type=1",
        "官网明确环境科学与工程为四川省贡嘎计划重点建设学科，并具有环境工程研究生培养基础。",
        "四川贡嘎计划建设本科；具有环境科学、污染治理、资源监测与材料化学方向。",
    ),
    VerifiedProvincialKeySeed(
        "宜宾学院", "四川省", "宜宾市", "https://www.yibinu.edu.cn/",
        "宜宾学院生物与医药硕士招生目录", "https://yjsc.yibinu.edu.cn/info/1101/2101.htm",
        "官网招生目录列有生物技术与工程、食品工程方向，考试与培养内容包含生物化学、微生物学和食品工程。",
        "四川贡嘎计划建设本科；具有生物技术、食品工程、质量检验与材料化工方向。",
    ),
    VerifiedProvincialKeySeed(
        "西南民族大学", "四川省", "成都市", "https://www.swun.edu.cn/",
        "西南民族大学2026年人才引进公告", "https://www.swun.edu.cn/__local/3/C3/D3/F37271E5AE62D7A2764895C609C_4937246C_2FF8D.pdf",
        "官网公告明确 10 个学科入选四川省贡嘎计划，工程学和化学进入 ESI 全球前1%。",
        "四川贡嘎计划建设本科；具有化学、材料、生物、农牧与药学检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "四川旅游学院", "四川省", "成都市", "https://www.sctu.edu.cn/",
        "四川旅游学院学校简介", "https://www.sctu.edu.cn/xxgk2/xxjj1.htm",
        "官网明确食品科学与工程入选四川省贡嘎计划，建有食品加工与检测实验教学平台。",
        "四川贡嘎计划建设本科；具有食品质量安全、微生物、营养与理化检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "四川民族学院", "四川省", "康定市", "https://www.scun.edu.cn/",
        "四川民族学院2024年度单位决算公开", "https://czt.sc.gov.cn/scczt/c082814/2025/9/12/c829c9977717468383d7281143d91748/files/2024%E5%B9%B4%E5%BA%A6%E5%9B%9B%E5%B7%9D%E6%B0%91%E6%97%8F%E5%AD%A6%E9%99%A2%E5%8D%95%E4%BD%8D%E5%86%B3%E7%AE%97%E5%85%AC%E5%BC%80.pdf",
        "省财政厅公开决算明确生态学立项为省“双一流”建设贡嘎计划学科，学校设生态与农学院。",
        "四川贡嘎计划建设本科；具有高原生态、农牧生物与资源环境检测方向。",
    ),
)


# 把未纳入原因固化为可测试审计项，区分不符合与留待其他批次，避免把证据不足误写成无专业。
PROVINCIAL_KEY_BATCH_06_EXCLUSION_REASONS = {
    "西南财经大学": "财经类办学为主，未发现符合本轮标准的生化环材重点学科证据。",
    "四川音乐学院": "艺术类院校，本轮未发现符合标准的生化环材专业或研究方向。",
    "成都美术学院": "艺术类院校，本轮未发现符合标准的生化环材专业或研究方向。",
    "阿坝师范学院": "有资源环境和生物学方向，但省级重点或贡嘎计划身份依据不足，暂缓到普通本科补充批。",
    "成都工业学院": "有材料与环境专业，但省级重点或贡嘎计划身份依据不足，暂缓到普通本科补充批。",
    "成都师范学院": "有化学与生命科学专业，但省级重点或贡嘎计划身份依据不足，暂缓到普通本科补充批。",
    "广安理工学院": "新设公办本科，专业与省级重点建设公开证据尚不完整，暂缓核验。",
    "四川警察学院": "按公安单位全量规则留待公安专批，避免在数据库中误标为普通高校客户类型。",
    "四川工程职业技术大学": "职业本科，不属于当前普通本科筛选范围。",
    "成都航空职业技术大学": "职业本科，不属于当前普通本科筛选范围。",
    "成都轻工职业技术大学": "职业本科，不属于当前普通本科筛选范围。",
    "四川建筑职业技术大学": "职业本科，不属于当前普通本科筛选范围。",
    "四川交通职业技术大学": "职业本科，不属于当前普通本科筛选范围。",
    "成都东软学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "成都艺术职业大学": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "电子科技大学成都学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "成都理工大学工程技术学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "四川传媒学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "成都银杏酒店管理学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "成都文理学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "四川工商学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "成都外国语学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "四川工业科技学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "成都锦城学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "西南财经大学天府学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "四川大学锦江学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "四川文化艺术学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "绵阳城市学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "西南交通大学希望学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "四川电影电视学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
    "吉利学院": "民办本科，不属于当前省属重点公办本科筛选范围。",
}


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把第 06 批核验种子转成候选，并使用城市加校名的严格主校区检索输入。"""

    assert len(VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_06) == 8
    assert len({seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_06}) == 8
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
            tags=("高校", "省属重点本科", "官网专业证据", "省属重点第06批"),
        )
        for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_06
    )


def main() -> None:
    """幂等创建四川困难证据批，不覆盖重复项或人工核验结果。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 省属重点本科生化环材核验第06批",
            source_scope=(
                "四川省剩余公办普通本科困难证据批；结合政府公开文件、教育主管部门和学校官网"
                "确认省级一流/贡嘎计划建设身份及生物、环境、化学、材料、食品农业或检测方向，"
                "排除既有、纯财经艺术、民办和职业本科，证据不足项保留到后续专批。"
            ),
            source_url=MOE_UNIVERSITY_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-provincial-key-import",
        )
    print(
        f"省属重点本科第06批完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
