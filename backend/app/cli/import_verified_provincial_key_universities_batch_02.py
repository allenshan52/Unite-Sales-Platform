"""导入省属重点本科第 02 批：保存华东高校官网证据，并排队定位主校区。"""

from app.cli.import_verified_provincial_key_universities_batch_01 import (
    MOE_UNIVERSITY_DIRECTORY,
    VerifiedProvincialKeySeed,
)
from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


# 第 02 批覆盖上海、江苏、浙江；仅保留官网可同时证明建设层次与目标专业的公办本科。
VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_02 = (
    VerifiedProvincialKeySeed(
        "上海理工大学", "上海市", "上海市", "https://www.usst.edu.cn/", "上海理工大学学校简介",
        "https://edp.usst.edu.cn/10932/list.htm",
        "官网明确学校为上海市属重点应用研究型大学；设有材料与化学、环境等相关学院和学科。",
        "上海市属重点本科；具有材料、化学、环境与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "上海师范大学", "上海市", "上海市", "https://www.shnu.edu.cn/", "上海师范大学学校概况",
        "https://xxgk.shnu.edu.cn/be/1d/c18118a769565/page.htm",
        "官网明确学校为上海市重点建设高校，并列出生命科学、化学与材料、环境与地理等学院。",
        "上海市重点建设本科；具有生命、化学、材料和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "上海应用技术大学", "上海市", "上海市", "https://www.sit.edu.cn/", "上海应用技术大学学校简介",
        "https://www.sit.edu.cn/xygk/xxjj_bf.htm",
        "官网明确学校为上海市重点建设的高水平地方大学，特色覆盖绿色化工、功能新材料和香料香精化妆品。",
        "上海市高水平地方本科；具有化学、材料、环境及化妆品质量检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "上海工程技术大学", "上海市", "上海市", "https://www.sues.edu.cn/", "上海工程技术大学学校简介",
        "https://www.sues.edu.cn/18/list.htm",
        "官网明确学校为上海市高水平地方应用型高校，专业覆盖化学工程、制药工程、环境工程和材料。",
        "上海市高水平地方本科；具有化工、制药、环境和材料方向。",
    ),
    VerifiedProvincialKeySeed(
        "江苏大学", "江苏省", "镇江市", "https://www.ujs.edu.cn/", "江苏大学学校简介",
        "https://oec.ujs.edu.cn/gywm/xxjj.htm",
        "官网明确学校为江苏省重点综合性大学和高水平大学建设高校；材料、化学、农业、药理毒理、生物及环境学科进入 ESI 前 1%。",
        "江苏省属重点本科；具有材料、化学、生命、医药、农业和环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "扬州大学", "江苏省", "扬州市", "https://www.yzu.edu.cn/", "扬州大学学校简介",
        "https://xxgk.yzu.edu.cn/info/1057/25556.htm",
        "官网明确学校为江苏省属重点综合性大学和高水平大学建设高峰计划 A 类高校，相关学科覆盖农业、化学、生命、材料、医药和环境。",
        "江苏省属重点本科；具有农业、化学、生命、材料、医药和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "南京工业大学", "江苏省", "南京市", "https://www.njtech.edu.cn/", "南京工业大学学校简介",
        "https://www.njtech.edu.cn/xxgk/xxjj.htm",
        "官网明确学校入选江苏高水平大学建设高峰计划 A 类建设高校，优势覆盖化学工程、材料、生物工程和环境。",
        "江苏高水平建设本科；具有化学化工、材料、生物和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "江苏科技大学", "江苏省", "镇江市", "https://www.just.edu.cn/", "江苏科技大学学校简介",
        "https://www.just.edu.cn/11982/list.htm",
        "官网明确学校为江苏高水平大学建设高校，材料、化学、环境生态和农业科学等学科进入 ESI 前 1%。",
        "江苏高水平建设本科；具有材料、化学、环境生态和农业检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "常州大学", "江苏省", "常州市", "https://www.cczu.edu.cn/", "常州大学学校简介",
        "https://www.cczu.edu.cn/10287/list.htm",
        "官网明确学校入选江苏高水平大学建设高峰计划，优势覆盖化学、材料、化学工程和环境。",
        "江苏高水平建设本科；具有化学化工、材料和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "南通大学", "江苏省", "南通市", "https://www.ntu.edu.cn/", "南通大学学校简介",
        "https://xxgk.ntu.edu.cn/9124/list.htm",
        "官网明确学校入选江苏高水平大学建设高峰计划，临床医学、药理毒理、生物化学、化学、材料和环境生态等学科进入 ESI 前 1%。",
        "江苏高水平建设本科；具有医学、药学、生命、化学、材料和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "徐州医科大学", "江苏省", "徐州市", "https://www.xzhmu.edu.cn/", "徐州医科大学学校简介",
        "https://www.xzhmu.edu.cn/xqzl/xxjj.htm",
        "官网明确学校入选江苏高水平大学建设高峰计划，设有生物医学、公共卫生、药学、法医学和医学技术方向。",
        "江苏高水平建设医科本科；具有生物医学、公共卫生、药学和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "苏州科技大学", "江苏省", "苏州市", "https://www.usts.edu.cn/", "苏州科技大学学校简介",
        "https://www.usts.edu.cn/xxgk/xxjj.htm",
        "官网明确学校建设江苏省高水平大学，省级优势和重点学科覆盖环境科学与工程、化学、材料和生态。",
        "江苏高水平建设本科；具有环境、化学、材料和生态方向。",
    ),
    VerifiedProvincialKeySeed(
        "浙江工业大学", "浙江省", "杭州市", "https://www.zjut.edu.cn/", "浙江工业大学学校简介",
        "https://zs.zjut.edu.cn/html/n569.html",
        "官网明确学校为浙江省重点建设高校，相关优势覆盖化学、材料、环境、农业和生物。",
        "浙江省重点建设本科；具有化学化工、材料、环境、农业和生物方向。",
    ),
    VerifiedProvincialKeySeed(
        "浙江师范大学", "浙江省", "金华市", "https://www.zjnu.edu.cn/", "浙江师范大学学校简介",
        "https://www.zjnu.edu.cn/3999/main.psp",
        "官网明确学校为浙江省重点建设高校和高水平大学，设有化学与材料、生命科学、地理与环境等学院。",
        "浙江省重点建设本科；具有化学、材料、生命和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "浙江理工大学", "浙江省", "杭州市", "https://www.zstu.edu.cn/", "浙江理工大学学校简介",
        "https://m.zstu.edu.cn/xxgk/xxjj.htm",
        "官网明确学校入选浙江省重点建设高校和高水平大学，优势覆盖材料、化学、生物和环境。",
        "浙江省重点建设本科；具有材料、化学、生物和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "浙江工商大学", "浙江省", "杭州市", "https://www.zjgsu.edu.cn/", "浙江工商大学学校简介",
        "https://yjszs.zjgsu.edu.cn/2024/0330/c469a169239/page.htm",
        "官网明确学校为浙江省重点建设高校，并设有食品科学与工程等相关优势学科。",
        "浙江省重点建设本科；具有食品科学、食品质量安全与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "浙江中医药大学", "浙江省", "杭州市", "https://www.zcmu.edu.cn/", "浙江中医药大学学校简介",
        "https://zsb.zcmu.edu.cn/info/1075/4812.htm",
        "官网明确学校为浙江省重点建设高校和高水平大学，覆盖中医学、中药学、药学、基础医学、公共卫生和生物科学。",
        "浙江省重点建设医药本科；具有中药、药学、生物、公共卫生和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "温州医科大学", "浙江省", "温州市", "https://www.wmu.edu.cn/", "温州医科大学学校简介",
        "https://www.wmu.edu.cn/info/1285/9364.htm",
        "官网明确学校为浙江省重点建设高校，相关方向覆盖医学、药学、生物、化学、材料和公共卫生。",
        "浙江省重点建设医科本科；具有医学、药学、生物、化学、材料和公共卫生方向。",
    ),
    VerifiedProvincialKeySeed(
        "浙江农林大学", "浙江省", "杭州市", "https://www.zafu.edu.cn/", "浙江农林大学学校简介",
        "https://iec.zafu.edu.cn/info/1008/6736.htm",
        "官网明确学校为浙江省重点建设高校和高水平大学，优势覆盖农业、林业、生物、环境、化学和材料。",
        "浙江省重点建设农林本科；具有农业、生命、环境、化学、材料和农产品检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "杭州师范大学", "浙江省", "杭州市", "https://www.hznu.edu.cn/", "杭州师范大学学校简介",
        "https://career.hznu.edu.cn/jobfair/view/id/34219",
        "官网明确学校为浙江省重点建设高校，化学、材料、环境生态、生物、临床医学和药理毒理等学科进入 ESI 前 1%。",
        "浙江省重点建设本科；具有化学、材料、环境、生命、医学和药学方向。",
    ),
    VerifiedProvincialKeySeed(
        "温州大学", "浙江省", "温州市", "https://www.wzu.edu.cn/", "温州大学学校简介",
        "https://www.wzu.edu.cn/xxgk/xxjj.htm",
        "官网明确学校为浙江省重点建设高校，相关优势覆盖化学、材料、环境生态和生命科学。",
        "浙江省重点建设本科；具有化学、材料、环境生态和生命方向。",
    ),
    VerifiedProvincialKeySeed(
        "杭州电子科技大学", "浙江省", "杭州市", "https://www.hdu.edu.cn/", "杭州电子科技大学学校简介",
        "https://www.hdu.edu.cn/659/list.htm",
        "官网明确学校入选浙江省重点建设高校和高水平大学，材料、化学和环境生态等学科进入 ESI 前 1%。",
        "浙江省重点建设本科；具有材料、化学和环境生态方向。",
    ),
    VerifiedProvincialKeySeed(
        "中国计量大学", "浙江省", "杭州市", "https://www.cjlu.edu.cn/", "中国计量大学学校总览",
        "https://www.cjlu.edu.cn/zgjlj/xwz2025/xxzl1.htm",
        "官网明确学校为浙江省重点建设大学，以计量、标准、质量、市场监管和检验检疫为特色，并设材料化学、生命、食品、药学和环境专业。",
        "浙江省重点建设本科；具有材料化学、生物、食品药品、环境与计量检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "浙江海洋大学", "浙江省", "舟山市", "https://www.zjou.edu.cn/", "浙江海洋大学学校简介",
        "https://jgxy.zjou.edu.cn/info/1059/5869.htm",
        "官网明确学校为浙江省重点建设高校，学科覆盖海洋科学、水产、食品科学、药学、资源环境和生物医药。",
        "浙江省重点建设海洋本科；具有海洋生命、水产、食品、药学和资源环境检测方向。",
    ),
)


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把官网已核验种子转成正式候选，并只用“城市+校名”触发严格主校区匹配。"""

    assert len(VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_02) == 24
    assert len({seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_02}) == 24
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
            tags=("高校", "省属重点本科", "官网专业证据", "省属重点第02批"),
        )
        for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_02
    )


def main() -> None:
    """幂等创建华东第 02 批；重复运行只返回已有批次，不覆盖人工核验结果。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 省属重点本科生化环材核验第02批",
            source_scope=(
                "上海、江苏、浙江省属重点/省内高水平建设公办本科；逐校官网确认建设层次及生物、环境、化学、"
                "材料、医药、食品农业或检测方向。官网或地址响应较慢院校留给后续补充批次。"
            ),
            source_url=MOE_UNIVERSITY_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-provincial-key-import",
        )
    print(
        f"省属重点本科第02批完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
