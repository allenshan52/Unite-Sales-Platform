"""导入普通公办本科第 02 批：筛选内蒙古、辽宁目标专业并排队定位主校区。"""

from app.cli.import_verified_provincial_key_universities_batch_01 import VerifiedProvincialKeySeed
from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


MOE_2026_UNIVERSITY_DIRECTORY = (
    "https://www.moe.gov.cn/jyb_xxgk/s5743/s5744/202606/t20260618_1441074.html"
)


# 仅纳入教育部底表中的公办普通本科；每所学校另有学校官网或官方招生材料的专业证据。
VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_02 = (
    VerifiedProvincialKeySeed(
        "内蒙古科技大学", "内蒙古自治区", "包头市", "https://www.imust.edu.cn/", "内蒙古科技大学材料类专业介绍",
        "https://zhaosheng.imust.edu.cn/xyzy/zyjs/clkxygcxy.htm",
        "官网介绍材料科学与工程、材料化学等本科专业及材料分析测试培养内容。",
        "公办普通本科；具有材料、化学与分析测试方向。",
    ),
    VerifiedProvincialKeySeed(
        "内蒙古工业大学", "内蒙古自治区", "呼和浩特市", "https://www.imut.edu.cn/", "内蒙古工业大学本科专业设置",
        "https://jwch.imut.edu.cn/info/1011/5883.htm",
        "官网本科专业设置包含无机非金属材料工程、应用化学、环境科学与工程等方向。",
        "公办普通本科；具有材料、化学化工与环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "内蒙古医科大学", "内蒙古自治区", "呼和浩特市", "https://www.immu.edu.cn/", "内蒙古医科大学本科专业设置",
        "https://jwc.immu.edu.cn/info/1049/11922.htm",
        "官网专业设置包含医学检验技术、临床药学、药学及生物医学相关本科培养。",
        "公办医科本科；具有药学、生物医学与医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "内蒙古师范大学", "内蒙古自治区", "呼和浩特市", "https://www.imnu.edu.cn/", "内蒙古师范大学化学与环境科学学院简介",
        "https://hxxy.imnu.edu.cn/xygk/xyjj.htm",
        "官网列有化学、环境科学和环境工程等本科专业与实验教学平台。",
        "公办普通本科；具有化学、环境与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "内蒙古民族大学", "内蒙古自治区", "通辽市", "https://www.imun.edu.cn/", "内蒙古民族大学农业硕士学位点报告",
        "https://nongxue.imun.edu.cn/upload/files/2025/3/45c64acb9b15f744.pdf",
        "官网报告列有生物学依托学科及农艺种业、畜牧、食品加工与安全培养方向。",
        "公办普通本科；具有生物、农业、食品安全与检验检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "赤峰大学", "内蒙古自治区", "赤峰市", "https://www.cfxy.cn/", "赤峰大学招生专业介绍",
        "https://www.cfxy.cn/zs/xyzy/index.htm",
        "官网招生专业包含药学、医学检验技术、生物科学、食品质量与安全、化学工程与工艺等。",
        "公办普通本科；具有生物、化学化工、药学、食品与医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "呼伦贝尔学院", "内蒙古自治区", "呼伦贝尔市", "https://www.hlbrc.cn/", "呼伦贝尔学院招生章程",
        "https://zsjy.hlbrc.cn/info/1013/2146.htm",
        "官网招生材料列有化学工程与工艺、生物科学、环境科学、农学和应用化学等本科专业。",
        "公办普通本科；具有生物、化学化工、环境与农业检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "集宁师范学院", "内蒙古自治区", "乌兰察布市", "https://www.jnnu.edu.cn/", "集宁师范学院生命科学学院专业介绍",
        "https://www.jnnu.edu.cn/zsb/zyjs/smkxxy.htm",
        "官网专业介绍列有生物科学方向；学校另设化学与化工学院和应用化学本科专业。",
        "公办普通本科；具有生物、化学与应用化学实验方向。",
    ),
    VerifiedProvincialKeySeed(
        "河套学院", "内蒙古自治区", "巴彦淖尔市", "https://www.htxy.edu.cn/", "河套学院农学与食品科研材料",
        "https://www.htxy.edu.cn/__local/8/4F/71/A9C64F63EADCA85E397C748B147_AE33AFB0_5C1FB7.pdf?e=.pdf",
        "学校官网学报材料记录农学系动物科学本科、食品微生物实验室和农畜产品研究。",
        "公办普通本科；具有动物科学、食品微生物与农产品检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "呼和浩特民族学院", "内蒙古自治区", "呼和浩特市", "https://www.imnc.edu.cn/", "呼和浩特民族学院环境工程专业介绍",
        "https://www.imnc.edu.cn/zs/zyjs1/hxyhjxy.htm",
        "官网介绍环境工程本科专业、环境监测课程与相关实验平台。",
        "公办普通本科；具有环境工程、环境监测与化学分析方向。",
    ),
    VerifiedProvincialKeySeed(
        "鄂尔多斯应用技术学院", "内蒙古自治区", "鄂尔多斯市", "https://www.oit.edu.cn/", "鄂尔多斯应用技术学院本科教学质量报告",
        "https://www.oit.edu.cn/__local/D/D4/C2/CC4351124A8ED16B14BA11FED8D_D24ED8A1_AA334.pdf",
        "官网质量报告列有化学工程与工艺、材料化学和应用化学等本科专业。",
        "公办普通本科；具有化学化工、材料与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "沈阳工业大学", "辽宁省", "沈阳市", "https://www.sut.edu.cn/", "沈阳工业大学材料科学与工程学院介绍",
        "https://zsxxw.sut.edu.cn/yxzl1/yxzl/clkxygcxy.htm",
        "官网列有材料成型及控制工程、焊接技术与工程、金属材料工程和功能材料本科专业。",
        "公办普通本科；具有材料制备、表征与质量检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "沈阳航空航天大学", "辽宁省", "沈阳市", "https://www.sau.edu.cn/", "沈阳航空航天大学材料科学与工程学院介绍",
        "https://zs.sau.edu.cn/zyjs/clkxygcxy.htm",
        "官网介绍材料类本科专业及材料力学性能、材料焊接性等实验课程。",
        "公办普通本科；具有航空材料、复合材料与分析测试方向。",
    ),
    VerifiedProvincialKeySeed(
        "沈阳理工大学", "辽宁省", "沈阳市", "https://www.sylu.edu.cn/", "沈阳理工大学环境与化工专业设置",
        "https://www.sylu.edu.cn/",
        "学校官网院系专业包含化学工程与工艺、环境工程、应用化学及材料类本科方向。",
        "公办普通本科；具有材料、化学化工、环境与检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "辽宁科技大学", "辽宁省", "鞍山市", "https://www.ustl.edu.cn/", "辽宁科技大学化学工程学院简介",
        "https://www.ustl.edu.cn/hgxy/xygk/xyjj.htm",
        "官网列有化学工程与工艺、应用化学、储能科学与工程、环境工程和生物工程本科专业。",
        "公办普通本科；具有化学化工、环境、生物与材料检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "辽宁工程技术大学", "辽宁省", "阜新市", "https://www.lntu.edu.cn/", "辽宁工程技术大学环境科学与工程学院简介",
        "https://hjxy.lntu.edu.cn/index/zjhjxy.htm",
        "官网列有环境工程、环境生态工程、环境科学和水土保持与荒漠化防治本科专业。",
        "公办普通本科；具有环境监测、生态修复与环保材料方向。",
    ),
    VerifiedProvincialKeySeed(
        "辽宁石油化工大学", "辽宁省", "抚顺市", "https://www.lnpu.edu.cn/", "辽宁石油化工大学材料化学专业介绍",
        "https://zhaosheng.lnpu.edu.cn/info/1038/2936.htm",
        "官网介绍材料化学本科专业及化学、材料分析和能源化工培养内容。",
        "公办普通本科；具有化学化工、材料与环境安全检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "沈阳化工大学", "辽宁省", "沈阳市", "https://www.syuct.edu.cn/", "沈阳化工大学本科专业设置",
        "https://jiaowu.syuct.edu.cn/info/1077/2828.htm",
        "官网专业设置覆盖化学化工、材料、环境工程、生物工程和制药等方向。",
        "公办普通本科；具有化学化工、材料、环境、生物与制药检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "大连交通大学", "辽宁省", "大连市", "https://www.djtu.edu.cn/", "大连交通大学本科教学质量报告",
        "https://www.djtu.edu.cn/Upload/file/20221215/a3983635-7cc5-4596-8a3f-f7fa2d9f75e1.pdf",
        "官网质量报告列有环境工程和材料类本科专业及相关实验教学。",
        "公办普通本科；具有材料、环境与轨道交通材料检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "沈阳建筑大学", "辽宁省", "沈阳市", "https://www.sjzu.edu.cn/", "沈阳建筑大学材料科学与工程学院介绍",
        "https://zs.sjzu.edu.cn/zyjs/clkxygcxy/xyjs.htm",
        "官网介绍无机非金属材料、高分子材料等本科培养与建筑材料测试平台。",
        "公办普通本科；具有建筑材料、环境与材料分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "辽宁工业大学", "辽宁省", "锦州市", "https://www.lnut.edu.cn/", "辽宁工业大学专业设置",
        "https://jwc.lnut.edu.cn/zyjs/zysz.htm",
        "官网专业设置列有材料、化学工程与工艺、应用化学和环境科学与工程方向。",
        "公办普通本科；具有材料、化学化工、环境与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "中国医科大学", "辽宁省", "沈阳市", "https://www.cmu.edu.cn/", "中国医科大学本科专业体系",
        "https://www.cmu.edu.cn/",
        "学校官网本科培养覆盖生物科学、生物技术、生物医学、药学、预防医学和医学检验技术等方向。",
        "公办医科本科；具有生物医学、药学、公共卫生与医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "锦州医科大学", "辽宁省", "锦州市", "https://www.jzmu.edu.cn/", "锦州医科大学本科专业设置",
        "https://jwc.jzmu.edu.cn/info/1246/1084.htm",
        "官网列有医学检验技术、药学、食品科学与工程、食品质量与安全和动植物检疫等专业。",
        "公办医科本科；具有医学检验、药学、食品安全与检疫方向。",
    ),
    VerifiedProvincialKeySeed(
        "辽宁中医药大学", "辽宁省", "沈阳市", "https://www.lnutcm.edu.cn/", "辽宁中医药大学本科专业设置",
        "https://jwc.lnutcm.edu.cn/info/1037/2451.htm",
        "官网本科专业表列有中药学、药学、药物制剂、中药制药和中药资源与开发等专业。",
        "公办医药本科；具有中药、药学、制药与药物分析方向。",
    ),
    VerifiedProvincialKeySeed(
        "沈阳医学院", "辽宁省", "沈阳市", "https://www.symc.edu.cn/", "沈阳医学院医学检验技术专业介绍",
        "https://www.symc.edu.cn/info/1032/35581.htm",
        "官网介绍医学检验技术本科及临床生化、免疫、微生物、分子生物学检测培养内容。",
        "公办医科本科；具有医学检验、生物技术与卫生检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "辽宁师范大学", "辽宁省", "大连市", "https://www.lnnu.edu.cn/", "辽宁师范大学生命科学学院",
        "https://smkx.lnnu.edu.cn/",
        "学校官网设生命科学学院，开展生物科学本科教学与生命科学研究。",
        "公办普通本科；具有生物科学、生命科学实验与生态研究方向。",
    ),
    VerifiedProvincialKeySeed(
        "沈阳师范大学", "辽宁省", "沈阳市", "https://www.synu.edu.cn/", "沈阳师范大学化学化工学院",
        "https://hxhg.synu.edu.cn/",
        "官网学院承担化学、能源化学工程等本科培养，并开展仪器分析与环境相关研究。",
        "公办普通本科；具有化学化工、仪器分析、环境与生命科学方向。",
    ),
    VerifiedProvincialKeySeed(
        "渤海大学", "辽宁省", "锦州市", "https://www.bhu.edu.cn/", "渤海大学化学与材料工程学院招生目录",
        "https://yjszsxxw.bhu.edu.cn/engine/upload/engine/2025-03/202503281634426737.pdf",
        "官网招生目录设化学与材料工程学院，并列有化学、材料与相关分析研究方向。",
        "公办普通本科；具有化学、材料与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "鞍山师范学院", "辽宁省", "鞍山市", "https://www.asnc.edu.cn/", "鞍山师范学院化学与生命科学学院简介",
        "https://hx.asnc.edu.cn/xygk/xyjj/c821e7ba384c4db58c6e83577c688f44.htm",
        "官网列有化学、应用化学、食品营养与检验教育、食品科学与工程和生物科学本科专业。",
        "公办普通本科；具有化学、生物、食品与检验检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "沈阳大学", "辽宁省", "沈阳市", "https://www.syu.edu.cn/", "沈阳大学院系设置",
        "https://www.syu.edu.cn/yxsz.htm",
        "官网院系设置列有生命科学与工程学院的生物科学、生物工程专业及材料科学系。",
        "公办普通本科；具有生物、材料、环境与实验分析方向。",
    ),
    VerifiedProvincialKeySeed(
        "大连大学", "辽宁省", "大连市", "https://www.dlu.edu.cn/", "大连大学环境与化学工程学院简介",
        "https://hhxy.dlu.edu.cn/xygk/xyjj.htm",
        "官网列有化学、化学工程与工艺、环境工程本科专业及污染治理、功能材料研究方向。",
        "公办普通本科；具有化学化工、环境、生物与功能材料检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "辽宁科技学院", "辽宁省", "本溪市", "https://www.lnist.edu.cn/", "辽宁科技学院生物医药与化学工程学院简介",
        "https://swyyyhxgc.lnist.edu.cn/xygk/xyjj.htm",
        "官网列有制药工程、应用化学、环境工程、生物技术和能源化学工程五个本科专业。",
        "公办普通本科；具有生物医药、化学化工、环境与材料方向。",
    ),
    VerifiedProvincialKeySeed(
        "沈阳工程学院", "辽宁省", "沈阳市", "https://www.sie.edu.cn/", "沈阳工程学院新能源学院简介",
        "https://xnyxy.sie.edu.cn/xygk/xyjj.htm",
        "官网列有新能源材料与器件、应用化学和储能科学与工程，并覆盖水处理、燃料化验和环境保护。",
        "公办普通本科；具有新能源材料、应用化学、环境与燃料检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "辽东学院", "辽宁省", "丹东市", "https://www.elnu.edu.cn/", "辽东学院化学工程与工艺专业介绍",
        "https://www.elnu.edu.cn/",
        "学校官网专业体系包含化学工程与工艺、医学检验技术、动物医学和食品相关本科方向。",
        "公办普通本科；具有化学化工、医学检验、生物与食品检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "营口理工学院", "辽宁省", "营口市", "https://www.yku.edu.cn/", "营口理工学院本科专业设置",
        "http://www.yku.edu.cn/zsxxw/wzsy.htm",
        "官网招生专业覆盖应用化学、化学工程与工艺、材料科学与工程、环境科学与工程等方向。",
        "公办普通本科；具有化学化工、材料、环境与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "朝阳师范学院", "辽宁省", "朝阳市", "https://www.cynu.edu.cn/", "朝阳师范学院2026年招生章程",
        "https://zsgz.cynu.edu.cn/info/1034/1910.htm",
        "官网招生章程列有食品科学与工程、生物科学、食品质量与安全和化学工程与工艺本科专业。",
        "公办普通本科；具有生物、化学化工、食品质量与检验检测方向。",
    ),
)


# 明确记录本轮底表中不纳入的学校，区分专业不匹配、艺术类和职业本科边界。
ORDINARY_UNDERGRADUATE_BATCH_02_EXCLUSION_REASONS = {
    "内蒙古财经大学": "财经经管类院校，未发现符合本轮标准的生物、环境、化学、材料或检测专业证据。",
    "内蒙古艺术学院": "艺术类院校，未发现符合本轮标准的生物、环境、化学、材料或检测专业证据。",
    "内蒙古建筑职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "兴安职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "呼和浩特职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "大连外国语大学": "外语类院校，未发现符合本轮标准的生物、环境、化学、材料或检测专业证据。",
    "东北财经大学": "财经经管类院校，未发现符合本轮标准的生物、环境、化学、材料或检测专业证据。",
    "沈阳音乐学院": "艺术类院校，未发现符合本轮标准的生物、环境、化学、材料或检测专业证据。",
    "鲁迅美术学院": "艺术类院校，未发现符合本轮标准的生物、环境、化学、材料或检测专业证据。",
}


# 新升格学校采用招生章程中的法定校址，避免旧校名 POI 把点位落到历史校区。
OFFICIAL_MAIN_CAMPUS_ADDRESSES = {
    "朝阳师范学院": "辽宁省朝阳市双塔区龙山街四段966号",
}


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把官网核验结果转为正式候选，并使用城市加校名触发严格主校区 POI 匹配。"""

    assert len(VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_02) == 36
    assert len({seed.name for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_02}) == 36
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
            tags=("高校", "普通公办本科", "官网专业证据", "普通本科第02批"),
        )
        for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_02
    )


def main() -> None:
    """幂等创建普通本科第 02 批；重复运行只返回原批次，不覆盖人工核验档案。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 普通公办本科生化环材核验第02批",
            source_scope=(
                "内蒙古、辽宁教育部2026高校底表中尚未进入正式库的公办普通本科；逐校核验生物、环境、"
                "化学、材料、医药、食品农业或检测方向，排除既有高校、职业本科及纯财经、外语、艺术院校。"
            ),
            source_url=MOE_2026_UNIVERSITY_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-ordinary-undergraduate-import",
        )
    print(
        f"普通公办本科第02批完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
