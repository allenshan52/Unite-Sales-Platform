"""导入普通公办本科第 03 批：筛选吉林、黑龙江目标专业并排队定位主校区。"""

from app.cli.import_verified_provincial_key_universities_batch_01 import VerifiedProvincialKeySeed
from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


MOE_2026_UNIVERSITY_DIRECTORY = (
    "https://www.moe.gov.cn/jyb_xxgk/s5743/s5744/202606/t20260618_1441074.html"
)


# 仅纳入教育部底表中的公办普通本科；每所学校另有学校官网、招生网或教学质量报告的专业证据。
VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_03 = (
    VerifiedProvincialKeySeed(
        "东北电力大学", "吉林省", "吉林市", "https://www.neepu.edu.cn/", "东北电力大学化学工程学院专业介绍",
        "https://zs.neepu.edu.cn/info/1040/2268.htm",
        "官网介绍环境工程、化学工程与工业生物工程及绿色生物材料、分析测试等本科培养方向。",
        "公办普通本科；具有化学化工、环境、生物工程、材料与分析测试方向。",
    ),
    VerifiedProvincialKeySeed(
        "北华大学", "吉林省", "吉林市", "https://www.beihua.edu.cn/", "北华大学院系与专业概况",
        "https://www.beihua.edu.cn/",
        "学校官网院系体系包含化学与生物、林学、医学和药学相关本科教学科研单位。",
        "公办普通本科；具有化学、生物、林学、医学与药学检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "吉林农业科技学院", "吉林省", "吉林市", "https://www.jlnku.edu.cn/", "吉林农业科技学院2026年招生章程",
        "https://zs.jlnku.edu.cn/info/1029/1160.htm",
        "官网章程列有生物技术、生物制药、食品科学与工程、食品质量与安全、动物医学和动植物检疫等本科专业。",
        "公办农业本科；具有生物、制药、食品安全、动物医学与检疫方向。",
    ),
    VerifiedProvincialKeySeed(
        "吉林医药学院", "吉林省", "吉林市", "https://www.jlmu.edu.cn/", "吉林医药学院药学专业介绍",
        "https://xzs.jlmu.cn/info/1321/3399.htm",
        "官网介绍药学本科的药物分析、质量控制、生物化学、微生物学及药品检验培养内容。",
        "公办医药本科；具有药学、生物制药、医学检验与药品质量控制方向。",
    ),
    VerifiedProvincialKeySeed(
        "吉林师范大学", "吉林省", "四平市", "https://www.jlnu.edu.cn/", "吉林师范大学本科专业设置一览表",
        "https://www.jlnu.edu.cn/__local/4/08/11/4F43632A1AB84041DABA8FAF6F8_D728F9FD_144CB6.pdf",
        "官网本科专业表列有化学学院化学专业和生命科学学院生物科学专业。",
        "公办师范本科；具有化学、生物科学、功能材料与环境研究方向。",
    ),
    VerifiedProvincialKeySeed(
        "白城师范学院", "吉林省", "白城市", "https://www.bcnu.edu.cn/", "白城师范学院官网专业与院系信息",
        "https://www.bcnu.edu.cn/",
        "学校官网专业与院系信息包含化学、生物科学及相关实验教学方向。",
        "公办师范本科；具有化学、生物科学与实验教学方向。",
    ),
    VerifiedProvincialKeySeed(
        "通化师范学院", "吉林省", "通化市", "https://www.thnu.edu.cn/", "通化师范学院化学学院简介",
        "https://hxxy.thnu.edu.cn/news/?131.html=",
        "官网介绍化学本科，并记录中药学、药物制剂和食品科学与工程等相关专业建设基础。",
        "公办师范本科；具有化学、中药、药物制剂、食品与生物方向。",
    ),
    VerifiedProvincialKeySeed(
        "吉林工商学院", "吉林省", "长春市", "https://www.jlbtc.edu.cn/", "吉林工商学院粮食工程与营养科学学院概况",
        "https://lsxy1.jlbtc.edu.cn/xygk.htm",
        "官网列有食品科学与工程、生物工程、食品质量与安全等六个普通本科专业及食品安全检测方向。",
        "公办普通本科；具有粮食、食品、生物工程、质量安全与检验检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "吉林工程技术师范学院", "吉林省", "长春市", "https://www.jlenu.edu.cn/", "吉林工程技术师范学院生物与食品学院简介",
        "https://spgc.jlenu.edu.cn/xygk/xyjj.htm",
        "官网列有食品科学与工程、食品营养与检验教育和生物工程本科专业及食品检验平台。",
        "公办普通本科；具有食品、生物工程、营养与检验检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "吉林建筑大学", "吉林省", "长春市", "https://www.jlju.edu.cn/", "吉林建筑大学学校简介",
        "https://www.jlju.edu.cn/info/1009/25214.htm",
        "官网列有材料科学与工程、环境科学与工程优势特色学科，并建有材料和环境实验平台。",
        "公办普通本科；具有建筑材料、化学、环境与分析测试方向。",
    ),
    VerifiedProvincialKeySeed(
        "长春大学", "吉林省", "长春市", "https://www.ccu.edu.cn/", "长春大学食品科学与工程专业介绍",
        "https://spxy.ccu.edu.cn/info/1060/9449.htm",
        "官网介绍食品科学与工程本科的生物化学、微生物、食品化学和食品分析实验培养。",
        "公办普通本科；具有食品、生物化学、微生物与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "长春工程学院", "吉林省", "长春市", "https://www.ccit.edu.cn/", "长春工程学院环境工程系简介",
        "https://szhjgc.ccit.edu.cn/info/1051/1152.htm",
        "官网介绍环境工程四年制本科及水环境治理、环境监测和相关实验研究。",
        "公办普通本科；具有环境工程、水处理、材料与监测检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "长春师范大学", "吉林省", "长春市", "https://www.ccsfu.edu.cn/", "长春师范大学教学科研单位信息",
        "https://www.ccsfu.edu.cn/ggfw/dhcha_x.htm",
        "官网列有化学学院分析实验室，以及生命科学学院生物技术、分子生物和食品科学教研室。",
        "公办师范本科；具有化学分析、生物技术、分子生物与食品科学方向。",
    ),
    VerifiedProvincialKeySeed(
        "佳木斯大学", "黑龙江省", "佳木斯市", "https://www.jmsu.edu.cn/", "佳木斯大学2026年招生章程",
        "https://zs.jmsu.edu.cn/info/1002/3212.htm",
        "官网章程列有化学、制药工程、药学、药物分析、生物科学、医学检验和无机非金属材料等专业。",
        "公办普通本科；具有化学、材料、生物、药学与医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "哈尔滨商业大学", "黑龙江省", "哈尔滨市", "https://www.hrbcu.edu.cn/", "哈尔滨商业大学食品工程学院",
        "http://spxy.hrbcu.edu.cn/",
        "官网设食品工程学院，开展食品科学、粮油、农产品加工、食品营养安全及生物与医药研究。",
        "公办普通本科；具有食品、药学、生物医药、质量安全与检验检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "哈尔滨学院", "黑龙江省", "哈尔滨市", "https://www.hrbu.edu.cn/", "哈尔滨学院食品科学与工程专业简介",
        "https://www.hrbu.edu.cn/lxy/info/1090/2143.htm",
        "官网介绍食品生物化学、微生物、食品分析、安全卫生及仪器分析检测技术等本科课程。",
        "公办普通本科；具有食品、化学、生物与仪器分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "哈尔滨师范大学", "黑龙江省", "哈尔滨市", "https://www.hrbnu.edu.cn/", "哈尔滨师范大学生命科学与技术学院简介",
        "https://smkxxy.hrbnu.edu.cn/xygk/xyjj.htm",
        "官网列有生物科学、生物技术和生态学本科专业，以及分子细胞和生物多样性科研平台。",
        "公办师范本科；具有生物、生态、化学化工与实验检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "黑龙江工程学院", "黑龙江省", "哈尔滨市", "https://www.hljit.edu.cn/", "黑龙江工程学院一流本科专业一览表",
        "https://www.hljit.edu.cn/jwc/info/1007/12817.htm",
        "官网一流本科专业表列有材料科学与工程；学校另设资源与环境、道路材料和环境工程研究方向。",
        "公办普通本科；具有材料、资源环境、道路工程材料与分析测试方向。",
    ),
    VerifiedProvincialKeySeed(
        "黑龙江科技大学", "黑龙江省", "哈尔滨市", "https://usth.edu.cn/", "黑龙江科技大学专业设置",
        "https://usth.edu.cn/rcpy/zysz.htm",
        "官网本科专业表列有化学工程与工艺、材料成型及控制工程等环境化工与材料方向。",
        "公办普通本科；具有材料、化学化工、环境、安全与资源检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "大庆师范学院", "黑龙江省", "大庆市", "https://www.dqnu.edu.cn/", "大庆师范学院校级重点专业",
        "https://www.dqnu.edu.cn/rcpy/bkjy/xjzdzy.htm",
        "官网重点专业表列有化学工程与工艺和生物技术，学校设化学工程学院与生物工程学院。",
        "公办师范本科；具有化学化工、生物工程、生物技术与分析实验方向。",
    ),
    VerifiedProvincialKeySeed(
        "黑龙江八一农垦大学", "黑龙江省", "大庆市", "https://www.byau.edu.cn/", "黑龙江八一农垦大学专业建设情况统计表",
        "https://jiaowu.byau.edu.cn/2025/1029/c2360a140942/page.htm",
        "官网专业表列有农业资源与环境、食品科学与工程、生物技术及农学、动植物检疫等本科方向。",
        "公办农业本科；具有生物、农业资源环境、食品安全与动植物检疫方向。",
    ),
    VerifiedProvincialKeySeed(
        "牡丹江医科大学", "黑龙江省", "牡丹江市", "https://www.mdjmu.cn/", "牡丹江医科大学学科专业",
        "https://www.mdjmu.cn/bkzsw/xkzy1/xkzy.htm",
        "官网列有药学、制药工程、生物技术、卫生检验与检疫和医学检验技术等本科专业。",
        "公办医科本科；具有药学、生物技术、公共卫生、医学检验与检疫方向。",
    ),
    VerifiedProvincialKeySeed(
        "牡丹江师范学院", "黑龙江省", "牡丹江市", "https://www.mdjnu.cn/", "牡丹江师范学院化学化工学院专业介绍",
        "https://zs.mdjnu.cn/zyjs/hxhgxy__.htm",
        "官网介绍化学和应用化学本科，并设置工业分析方向及化学实验实践课程。",
        "公办师范本科；具有化学、应用化学、工业分析与生物科学方向。",
    ),
    VerifiedProvincialKeySeed(
        "绥化学院", "黑龙江省", "绥化市", "https://www.shxy.edu.cn/", "绥化学院本科专业设置",
        "https://www.shxy.edu.cn/rcpy/zysz.htm",
        "官网本科专业表列有化学、食品科学与工程、制药工程和食品质量与安全等方向。",
        "公办普通本科；具有化学、食品、制药、质量安全与检验检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "黑龙江工业学院", "黑龙江省", "鸡西市", "https://www.hljut.edu.cn/", "黑龙江工业学院本科教学质量报告",
        "https://zs.hljut.edu.cn/uploads/soft/241204/1-241204143323.pdf",
        "官网质量报告列有材料科学与工程、矿物加工工程和食品质量与安全等本科专业。",
        "公办普通本科；具有材料、矿物加工、食品质量安全与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "黑河学院", "黑龙江省", "黑河市", "https://www.hhxy.edu.cn/", "黑河学院招生专业设置",
        "https://zsxx.hhxy.edu.cn/zysz.htm",
        "官网招生专业介绍列有生物技术、应用化学和化学本科培养方向。",
        "公办普通本科；具有生物技术、化学、应用化学与实验分析方向。",
    ),
    VerifiedProvincialKeySeed(
        "齐齐哈尔医学院", "黑龙江省", "齐齐哈尔市", "https://www.qmu.edu.cn/", "齐齐哈尔医学院专业介绍",
        "https://www.qmu.edu.cn/zyjs/list.htm",
        "官网专业介绍包含药学、中药学、临床药学和药品质量检验、质量控制培养方向。",
        "公办医科本科；具有药学、中药学、生物医学与医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "齐齐哈尔大学", "黑龙江省", "齐齐哈尔市", "https://www.qqhru.edu.cn/", "齐齐哈尔大学食品质量与安全培养方案",
        "https://www.qqhru.edu.cn/info/1570/10087.htm",
        "官网培养方案包含食品分析检测、质量控制与安全评价，并设化学、材料、生物和食品相关专业。",
        "公办普通本科；具有化学化工、材料、生物、食品安全与分析检测方向。",
    ),
)


# 记录本轮不纳入的公办本科；民办本科不属于本轮公办范围，无需逐校重复登记。
ORDINARY_UNDERGRADUATE_BATCH_03_EXCLUSION_REASONS = {
    "吉林财经大学": "财经类院校，未发现符合本轮标准的生物、环境、化学、材料或检测专业证据。",
    "吉林艺术学院": "艺术类院校，未发现符合本轮标准的生物、环境、化学、材料或检测专业证据。",
    "吉林铁道职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "长春汽车职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "长春职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "哈尔滨金融学院": "金融财经类院校，未发现符合本轮标准的生物、环境、化学、材料或检测专业证据。",
    "哈尔滨音乐学院": "艺术类院校，未发现符合本轮标准的生物、环境、化学、材料或检测专业证据。",
    "哈尔滨建筑科技职业大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "哈尔滨职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "黑龙江农业工程职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
}


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把逐校官网核验结果转为正式候选，并交给既有严格主校区 POI 流程。"""

    assert len(VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_03) == 28
    assert len({seed.name for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_03}) == 28
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
            tags=("高校", "普通公办本科", "官网专业证据", "普通本科第03批"),
        )
        for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_03
    )


def main() -> None:
    """幂等创建普通本科第 03 批；重复运行只返回原批次，不覆盖人工核验档案。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 普通公办本科生化环材核验第03批",
            source_scope=(
                "吉林、黑龙江教育部2026高校底表中尚未进入正式库的公办普通本科；逐校核验生物、环境、"
                "化学、材料、医药、食品农业或检测方向，排除既有高校、职业本科及纯财经、艺术院校。"
            ),
            source_url=MOE_2026_UNIVERSITY_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-ordinary-undergraduate-import",
        )
    print(
        f"普通公办本科第03批完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
