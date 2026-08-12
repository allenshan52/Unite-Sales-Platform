"""导入省属重点本科首批高校：保存官方办学层次与生化环材/医药证据，并排队定位主校区。"""

from dataclasses import dataclass

from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


MOE_UNIVERSITY_DIRECTORY = "https://www.moe.gov.cn/jyb_xxgk/s5743/s5744/A03/"


@dataclass(frozen=True)
class VerifiedProvincialKeySeed:
    """描述一所经学校官网确认建设层次和目标专业方向的省属重点本科高校。"""

    name: str
    province: str
    city: str
    website: str
    evidence_title: str
    evidence_url: str
    evidence_excerpt: str
    inclusion_reason: str


# 第 01 批先覆盖华北、东北证据清晰的公办本科；官网响应慢或证据不完整的院校留给后续批次。
VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_01 = (
    VerifiedProvincialKeySeed(
        "河北大学", "河北省", "保定市", "https://www.hbu.edu.cn/", "河北大学学校简介",
        "https://www.hbu.edu.cn/xxgk/xxjj.htm",
        "官网明确学校为河北省重点支持的国家一流大学建设一层次高校；化学、材料、环境生态、药理等学科进入 ESI 前1%。",
        "省属重点本科；具有化学、材料、环境、生命与药学检测相关方向。",
    ),
    VerifiedProvincialKeySeed(
        "燕山大学", "河北省", "秦皇岛市", "https://www.ysu.edu.cn/", "燕山大学学校简介",
        "https://www.ysu.edu.cn/xxgk/xxjj.htm",
        "官网列有省级重点学科，并设置材料科学与工程、环境与化学工程等教学科研单位。",
        "省属重点本科；具有材料、化学化工与环境相关方向。",
    ),
    VerifiedProvincialKeySeed(
        "河北农业大学", "河北省", "保定市", "https://www.hebau.edu.cn/", "河北农业大学招生章程",
        "https://yanjiusheng.hebau.edu.cn/__local/1/29/BA/F4A2F090F1362F8D3E9768697B1_9F85C022_2DE9C.pdf",
        "官网招生章程明确学校是省属重点骨干大学；学校设生命、食品、资源与环境等相关学院和学科。",
        "省属重点骨干本科；具有生命、食品安全、资源环境与农业检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "河北医科大学", "河北省", "石家庄市", "https://www.hebmu.edu.cn/", "河北医科大学学校简介",
        "https://www.hebmu.edu.cn/a/xxgk/xxjj/index.html",
        "官网介绍医学、药学、公共卫生及省级学科重点实验室等教学科研体系。",
        "省属重点医科本科；具有药学、生物医学、公共卫生和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "中北大学", "山西省", "太原市", "https://www.nuc.edu.cn/", "中北大学学校简介",
        "https://www.nuc.edu.cn/xxgk.htm",
        "官网介绍省部共建和重点学科建设，并设材料、化学化工、环境与安全等相关学科。",
        "省属重点本科；具有材料、化学化工、环境与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "山西农业大学", "山西省", "晋中市", "https://www.sxau.edu.cn/", "山西农业大学学校简介",
        "https://www.sxau.edu.cn/xxgk2/xxjj.htm",
        "官网明确学校曾为全国重点大学，形成生物—农业—食品学科链，并拥有农业资源与环境等省级重点学科。",
        "省属重点农业本科；具有生物、资源环境、食品质量与农业检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "山西医科大学", "山西省", "太原市", "https://www.sxmu.edu.cn/", "山西医科大学学校简介",
        "https://www.sxmu.edu.cn/xxgk/xxjj.htm",
        "官网介绍医学、公共卫生、药学和基础医学等本科与科研体系。",
        "省属重点医科本科；具有药学、公共卫生、生物医学和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "内蒙古农业大学", "内蒙古自治区", "呼和浩特市", "https://www.imau.edu.cn/", "内蒙古农业大学概况",
        "https://www.imau.edu.cn/ndgk.htm",
        "官网明确学校为一省一校重点支持、省部共建高校，农业科学、动植物科学和环境生态进入 ESI 前1%。",
        "自治区重点本科；具有生命、环境生态、食品质量与农牧检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "大连医科大学", "辽宁省", "大连市", "https://www.dmu.edu.cn/", "大连医科大学简介",
        "https://www.dmu.edu.cn/xxgk/dyjj.htm",
        "官网明确学校是辽宁省一流大学重点建设高校，以医学为主并开展基础医学、药学和公共卫生研究。",
        "省一流大学重点建设本科；具有药学、生物医学、公共卫生和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "沈阳药科大学", "辽宁省", "沈阳市", "https://www.syphu.edu.cn/", "沈阳药科大学学校简介",
        "https://www.syphu.edu.cn/xxgk/xxjj.htm",
        "官网介绍药学、中药学、制药工程、生命科学与生物制药等优势学科专业。",
        "省属重点药科本科；具有药物化学、分析检测、生物制药和中药质量研究方向。",
    ),
    VerifiedProvincialKeySeed(
        "沈阳农业大学", "辽宁省", "沈阳市", "https://www.syau.edu.cn/", "沈阳农业大学学校简介",
        "https://www.syau.edu.cn/xxgk/xxjj.htm",
        "官网明确多学科入选辽宁省新一轮双一流建设，环境生态、化学、生物与生物化学进入 ESI 前1%。",
        "省属重点农业本科；具有生命、环境、化学、食品安全和农业检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "大连工业大学", "辽宁省", "大连市", "https://www.dlpu.edu.cn/", "大连工业大学简介",
        "https://www.dlpu.edu.cn/pages/introduce/",
        "官网明确食品科学入选辽宁省新一轮双一流建设，学校具有食品、化学、材料、生物和质量安全科研平台。",
        "省双一流学科建设本科；具有食品安全、生物、化学、材料与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "大连海洋大学", "辽宁省", "大连市", "https://www.dlou.edu.cn/", "大连海洋大学学校简介",
        "https://www.dlou.edu.cn/5/list.htm",
        "官网明确学校是辽宁省双一流建设高校，水产、动植物科学和环境生态为优势方向。",
        "省双一流建设本科；具有水产生命、海洋环境、食品安全与生物检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "长春理工大学", "吉林省", "长春市", "https://www.cust.edu.cn/", "长春理工大学学校简介",
        "https://www.cust.edu.cn/xxgk2026/xxjj2026/index.htm",
        "官网明确学校为吉林省重点大学，并设材料科学与工程、化学与环境工程等相关学科。",
        "省属重点本科；具有材料、化学与环境相关教学科研方向。",
    ),
    VerifiedProvincialKeySeed(
        "吉林农业大学", "吉林省", "长春市", "https://www.jlau.edu.cn/", "吉林农业大学学校简介",
        "https://www.jlau.edu.cn/xxgk/xxjj.htm",
        "官网明确学校为吉林省省属重点大学，拥有生物、环境、食品和农业质量安全相关学科平台。",
        "省属重点农业本科；具有生命、环境、食品安全与农业检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "长春中医药大学", "吉林省", "长春市", "https://www.ccucm.edu.cn/", "长春中医药大学学校概况",
        "https://www.ccucm.edu.cn/xqzl/xxgk.htm",
        "官网明确学校为吉林省重点大学，中药学、药学及相关实验研究为核心方向。",
        "省属重点医药本科；具有中药、药学、化学分析和生物检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "长春工业大学", "吉林省", "长春市", "https://www.ccut.edu.cn/", "长春工业大学概况",
        "https://www.ccut.edu.cn/gdgl.htm",
        "官网明确学校为吉林省重点大学，并设材料、化学与生命科学等相关学科专业。",
        "省属重点本科；具有材料、化学化工与生命科学方向。",
    ),
    VerifiedProvincialKeySeed(
        "吉林化工大学", "吉林省", "吉林市", "https://www.jlict.edu.cn/", "吉林化工大学学校简介",
        "https://www.jlict.edu.cn/xxgk/xxjj.htm",
        "官网明确学校为吉林省高水平应用研究型高校建设项目 A 类，优势覆盖化学、材料、环境和生物化工。",
        "省高水平建设本科；具有化学化工、材料、环境与生物工程方向。",
    ),
    VerifiedProvincialKeySeed(
        "哈尔滨医科大学", "黑龙江省", "哈尔滨市", "https://www.hrbmu.edu.cn/", "哈尔滨医科大学学校概况",
        "https://www.hrbmu.edu.cn/xyjj/xxgk.htm",
        "官网明确学校为黑龙江省国内一流大学建设高校，覆盖基础医学、公共卫生、药学与生物医学方向。",
        "省内一流大学建设本科；具有药学、生物医学、公共卫生和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "黑龙江中医药大学", "黑龙江省", "哈尔滨市", "https://www.hljucm.net/", "黑龙江中医药大学学校简介",
        "https://www.hljucm.net/xxgk/xxjj.htm",
        "官网介绍中药学、药学和中医药现代分析研究体系及大量国家、省部级科研项目平台。",
        "省属重点医药本科；具有中药、药学、化学分析和生物检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "东北石油大学", "黑龙江省", "大庆市", "https://www.nepu.edu.cn/", "东北石油大学学校简介",
        "https://www.nepu.edu.cn/xxgk/xxjj.htm",
        "官网介绍省部共建重点办学基础，化学、材料科学进入 ESI 前1%，并设化学化工与环境工程方向。",
        "省属重点本科；具有化学化工、材料、环境监测与石化分析方向。",
    ),
    VerifiedProvincialKeySeed(
        "哈尔滨理工大学", "黑龙江省", "哈尔滨市", "https://www.hrbust.edu.cn/", "哈尔滨理工大学学校简介",
        "https://www.hrbust.edu.cn/xxgklink/xxjj.htm",
        "官网明确学校为黑龙江省国内双一流建设高校，材料和化学进入 ESI 前1%，并设环境相关专业。",
        "省内双一流建设本科；具有材料、化学化工与环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "黑龙江大学", "黑龙江省", "哈尔滨市", "https://www.hlju.edu.cn/", "黑龙江大学学校简介",
        "https://www.hlju.edu.cn/xqzl/xxjj.htm",
        "官网介绍省属高校重点建设基础，拥有化学、能源环境材料、农业微生物和产品质量安全科研平台。",
        "省属重点综合本科；具有化学、材料、生物、环境与质量安全检测方向。",
    ),
)


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把已核验学校转换为正式候选，并以“城市+校名”交给严格主校区 POI 匹配。"""

    assert len(VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_01) == 23
    assert len({seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_01}) == 23
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
            tags=("高校", "省属重点本科", "官网专业证据", "省属重点第01批"),
        )
        for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_01
    )


def main() -> None:
    """幂等创建省属重点第 01 批；重复运行只返回既有批次，不覆盖人工核验结果。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 省属重点本科生化环材核验第01批",
            source_scope=(
                "华北和东北省属重点/省内双一流/高水平建设公办本科首批；逐校官网确认办学层次及"
                "生物、环境、化学、材料、医药或检测方向。官网或地址慢响应院校留给后续批次处理。"
            ),
            source_url=MOE_UNIVERSITY_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-provincial-key-import",
        )
    print(
        f"省属重点本科第01批完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
