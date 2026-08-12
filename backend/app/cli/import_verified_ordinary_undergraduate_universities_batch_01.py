"""导入普通公办本科第 01 批：筛选河北、山西目标专业并排队定位主校区。"""

from app.cli.import_verified_provincial_key_universities_batch_01 import VerifiedProvincialKeySeed
from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


MOE_2026_UNIVERSITY_DIRECTORY = (
    "https://www.moe.gov.cn/jyb_xxgk/s5743/s5744/202606/t20260618_1441074.html"
)


# 只纳入教育部底表中的公办普通本科；每所学校另有学校、教育部或官方教育平台的专业证据。
VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_01 = (
    VerifiedProvincialKeySeed(
        "保定学院", "河北省", "保定市", "https://www.bdu.edu.cn/", "保定学院生化学院概况",
        "https://shxy.bdu.edu.cn/ybgk.htm", "官网列有化学、生物科学、环境生态工程和制药工程等专业。",
        "公办普通本科；具有生物、化学、环境生态和制药检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "华北理工大学", "河北省", "唐山市", "https://www.ncst.edu.cn/", "华北理工大学本科招生专业",
        "https://zsjyc.ncst.edu.cn/col/1589180017916/index.html", "本科招生信息包含化学、材料、环境、公共卫生和医学相关专业。",
        "公办普通本科；具有化学、材料、环境、医药和公共卫生检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "唐山学院", "河北省", "唐山市", "https://www.tsc.edu.cn/", "唐山学院院系设置",
        "https://www.tsc.edu.cn/", "官网院系设置列有新材料与化学工程学院。",
        "公办普通本科；具有新材料与化学工程方向。",
    ),
    VerifiedProvincialKeySeed(
        "唐山师范学院", "河北省", "唐山市", "https://www.tstc.edu.cn/", "唐山师范学院化学科学系简介",
        "https://hxx.tstc.edu.cn/yxgk/yxjs.htm", "官网列有化学、应用化学、材料化学和能源化学工程专业。",
        "公办普通本科；具有化学、材料和能源化工方向。",
    ),
    VerifiedProvincialKeySeed(
        "北华航天工业学院", "河北省", "廊坊市", "https://www.nciae.edu.cn/", "北华航天工业学院院系设置",
        "https://www.nciae.edu.cn/", "官网院系设置列有材料工程学院，并建设热防护材料科研平台。",
        "公办普通本科；具有金属材料、复合材料和材料分析测试方向。",
    ),
    VerifiedProvincialKeySeed(
        "应急管理大学", "河北省", "廊坊市", "https://www.ncist.edu.cn/", "应急管理大学本科招生专业",
        "https://uem.yz.cangfenginfo.com/htmls/index.html", "学校本科招生网列有应用化学、化学工程与工艺、材料科学与工程和环境工程专业。",
        "应急管理部直属公办本科；具有化学、材料、环境、安全与灾害检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "廊坊师范学院", "河北省", "廊坊市", "https://www.lfnu.edu.cn/", "廊坊师范学院化学与材料科学学院简介",
        "https://www.lfnu.edu.cn/hxyclkx/col/1387181266921/index.html", "官网介绍化学、应用化学、材料化学等专业与实验平台。",
        "公办普通本科；具有化学、材料与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "张家口学院", "河北省", "张家口市", "https://www.zjku.edu.cn/", "张家口学院院系专业",
        "https://www.zjku.edu.cn/", "官网院系专业包含医学、药学及医学检验相关培养方向。",
        "公办普通本科；具有药学、医学检验与生物医学方向。",
    ),
    VerifiedProvincialKeySeed(
        "河北北方学院", "河北省", "张家口市", "https://www.hebeinu.edu.cn/", "河北北方学院本科专业",
        "https://zs.hebeinu.edu.cn/web/major/index.html", "官网本科专业目录列有生物信息学、药学、动物医学等专业。",
        "公办普通本科；具有生物、药学、动物医学和检验检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "河北建筑工程学院", "河北省", "张家口市", "https://www.hebiace.edu.cn/", "河北建筑工程学院学校简介",
        "https://www.hebiace.edu.cn/xygk/xxgk.htm", "官网介绍资源与环境、建筑环境与能源等学科专业。",
        "公办普通本科；具有环境、资源与建筑材料检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "承德医学院", "河北省", "承德市", "https://www.cdmc.edu.cn/", "承德医学院本科专业信息",
        "https://xxgk.cdmc.edu.cn/module/download/downfile.jsp?classid=0&filename=d4e25e61dcaa44d68f03af0855ad0dd9.pdf",
        "官网公开材料列有药学、医学检验技术和应用生物科学等专业。",
        "公办医科本科；具有药学、生物医学和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "河北民族师范学院", "河北省", "承德市", "https://www.hbun.edu.cn/", "河北民族师范学院专业设置",
        "https://www.hbun.edu.cn/", "官网专业设置包含化学和生物科学本科专业。",
        "公办普通本科；具有化学、生物科学及实验教学方向。",
    ),
    VerifiedProvincialKeySeed(
        "沧州师范学院", "河北省", "沧州市", "https://www.caztc.edu.cn/", "沧州师范学院生命科学学院简介",
        "https://www.caztc.edu.cn/info/1006/10134.htm", "官网介绍生物科学和生态学相关专业与科研方向。",
        "公办普通本科；具有生物、生态与环境监测方向。",
    ),
    VerifiedProvincialKeySeed(
        "河北水利电力学院", "河北省", "沧州市", "https://www.hbwe.edu.cn/", "河北水利电力学院专业介绍",
        "https://zsb.hbwe.edu.cn/zyjs.htm", "官网专业介绍包含水利、建筑环境与能源等资源环境方向。",
        "公办普通本科；具有水环境、资源与工程检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "河北中医药大学", "河北省", "石家庄市", "https://www.hebcm.edu.cn/", "河北中医药大学专业设置",
        "https://www.hebcm.edu.cn/", "官网专业设置包含中药学、药学、中药制药、医学检验技术和生物工程。",
        "公办医药本科；具有中药、药学、生物与医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "河北地质大学", "河北省", "石家庄市", "https://www.hgu.edu.cn/", "河北地质大学学科概况",
        "https://www.hgu.edu.cn/xkjs/xkgk.htm", "官网列有材料科学与工程、环境科学与工程等学科方向。",
        "公办普通本科；具有材料、环境、地质资源与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "河北师范大学", "河北省", "石家庄市", "https://www.hebtu.edu.cn/", "河北师范大学化学与材料科学学院",
        "https://huaxue.hebtu.edu.cn/", "学院官网展示化学、材料及分析检测教学科研体系。",
        "公办普通本科；具有化学、材料、生物与实验检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "河北科技大学", "河北省", "石家庄市", "https://www.hebust.edu.cn/", "河北科技大学材料学院简介",
        "https://clxy.web.hebust.edu.cn/xygk/xyjj/index.htm", "官网列有材料科学与工程、高分子材料等五个材料类专业。",
        "公办普通本科；具有材料、化学化工、环境与生物工程方向。",
    ),
    VerifiedProvincialKeySeed(
        "石家庄学院", "河北省", "石家庄市", "https://www.sjzc.edu.cn/", "石家庄学院化工学院专业设置",
        "https://www.sjzc.edu.cn/hgxy/col/1657857052165/index.html", "官网列有化学、制药、生物和材料等八个相关专业。",
        "公办普通本科；具有化学、制药、生物和材料方向。",
    ),
    VerifiedProvincialKeySeed(
        "石家庄铁道大学", "河北省", "石家庄市", "https://www.stdu.edu.cn/", "石家庄铁道大学招生专业目录",
        "https://yjs.stdu.edu.cn/sitedata/yjs/files/zhaosheng/2024/shuoshi/%E9%99%84%E4%BB%B61_2025%E5%B9%B4%E6%8E%A5%E6%94%B6%E6%8E%A8%E5%85%8D%E7%9B%B4%E5%8D%9A%E7%94%9F%E5%92%8C%E7%A1%95%E5%A3%AB%E7%94%9F%E4%B8%93%E4%B8%9A%E7%9B%AE%E5%BD%95.pdf",
        "官网目录包含环境友好高分子、材料与化工等研究方向。",
        "公办普通本科；具有材料、环境与工程分析方向。",
    ),
    VerifiedProvincialKeySeed(
        "河北环境工程学院", "河北省", "秦皇岛市", "https://www.hebuee.edu.cn/", "教育部同意建立河北环境工程学院的函",
        "https://www.moe.gov.cn/srcsite/A03/s181/201604/t20160401_236241.html", "教育部批复明确首批设置环境科学、环境工程和环境生态工程专业。",
        "公办环境本科；具有环境监测、污染治理与生态检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "河北科技师范学院", "河北省", "秦皇岛市", "https://www.hevttc.edu.cn/", "河北科技师范学院本科专业",
        "https://www.hevttc.edu.cn/xkzy/bkzy.htm", "官网本科目录列有生物科学、化学、食品与农学相关专业。",
        "公办普通本科；具有生物、化学、食品和农业检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "衡水学院", "河北省", "衡水市", "https://www.hsnc.edu.cn/", "衡水学院专业设置",
        "https://www.hsnc.edu.cn/", "官网专业设置包含化学工程与工艺及相关实验教学方向。",
        "公办普通本科；具有化学工程、材料与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "邢台医学院", "河北省", "邢台市", "https://www.xtmc.edu.cn/", "邢台医学院药学专业",
        "https://yaoxuexi.xtmc.edu.cn/info/1039/7564.htm", "官网介绍药学本科专业及药物分析、质量控制培养内容。",
        "公办医科本科；具有药学、医学检验和卫生检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "邢台学院", "河北省", "邢台市", "https://www.xttc.edu.cn/", "邢台学院院系设置",
        "https://www.xttc.edu.cn/", "官网院系设置包含化学与化工学院、生物科学与工程学院和资源环境方向。",
        "公办普通本科；具有化学、生物、资源与环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "河北工程大学", "河北省", "邯郸市", "https://www.hebeu.edu.cn/", "河北工程大学院系设置",
        "https://www.hebeu.edu.cn/", "官网院系设置包含生命科学与食品工程、材料、能源与环境等相关单位。",
        "公办普通本科；具有生物、食品、材料、环境与检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "邯郸学院", "河北省", "邯郸市", "https://www.hdc.edu.cn/", "邯郸学院相关专业教学材料",
        "https://dept.hdc.edu.cn/filecenter/file/main%3A%3Addd081a74f3d44439de015e913cbd4f4", "官网教学材料包含食品、环境生态和仪器分析课程方向。",
        "公办普通本科；具有食品、环境生态与仪器分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "山西电子科技学院", "山西省", "临汾市", "https://www.sxdzkj.edu.cn/", "山西电子科技学院新能源与材料方向",
        "https://www.sxdzkj.edu.cn/", "官网展示新能源与材料工程学院及高分子材料、碳材料和水处理研究方向。",
        "公办普通本科；具有新能源材料、高分子材料与环境水处理方向。",
    ),
    VerifiedProvincialKeySeed(
        "吕梁学院", "山西省", "吕梁市", "https://www.llu.edu.cn/", "吕梁学院化学化工系专业设置",
        "https://hxhgx.llu.edu.cn/xbgk/zysz.htm", "官网列有化学、化学工程、材料和环境相关专业。",
        "公办普通本科；具有化学、材料、环境和食品生物方向。",
    ),
    VerifiedProvincialKeySeed(
        "山西医药学院", "山西省", "吕梁市", "https://www.sxmufyc.edu.cn/", "山西医药学院专业介绍",
        "https://www.sxmufyc.edu.cn/bkszs/info/1306/1892.htm", "官网介绍药学、医学检验技术和公共卫生相关本科培养。",
        "公办医药本科；具有药学、医学检验和公共卫生检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "山西大同大学", "山西省", "大同市", "https://www.sxdtdx.edu.cn/", "山西大同大学专业设置",
        "https://jwc.sxdtdx.edu.cn/news-show-1797.html", "官网专业表列有生物科学、功能材料、制药工程和医学检验技术。",
        "公办普通本科；具有生物、材料、制药和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "太原学院", "山西省", "太原市", "https://www.tyu.edu.cn/", "太原学院院系专业",
        "https://www.tyu.edu.cn/", "官网院系专业包含化学工程与工业生物工程、新能源材料和园林生态方向。",
        "公办普通本科；具有化学工程、生物工程、新能源材料与生态方向。",
    ),
    VerifiedProvincialKeySeed(
        "太原工业学院", "山西省", "太原市", "https://www.tit.edu.cn/", "太原工业学院环境生态工程专业",
        "https://zsxx.tit.edu.cn/info/1039/2878.htm", "官网介绍环境生态工程及环境化学、环境监测等课程。",
        "公办普通本科；具有化学化工、材料、环境生态与监测方向。",
    ),
    VerifiedProvincialKeySeed(
        "太原师范学院", "山西省", "晋中市", "https://www.tynu.edu.cn/", "太原师范学院院系专业",
        "https://zs.tynu.edu.cn/Newlist/626/5.html", "官网招生院系包含化学与材料、生物和地理环境相关专业。",
        "公办普通本科；具有化学、材料、生物和环境教育研究方向。",
    ),
    VerifiedProvincialKeySeed(
        "太原科技大学", "山西省", "太原市", "https://www.tyust.edu.cn/", "太原科技大学环境与资源学院简介",
        "https://hj.tyust.edu.cn/xygk/xyjj.htm", "官网列有环境科学、环境工程、环境生态工程和生物工程等专业。",
        "公办普通本科；具有环境、生物、材料与资源检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "山西中医药大学", "山西省", "晋中市", "https://www.sxtcm.edu.cn/", "山西中医药大学中药与食品工程学院简介",
        "https://ipfe.sxtcm.edu.cn/xygk/xyjj.htm", "官网列有中药、药学、制药工程、食品科学和生物制药等八个本科专业。",
        "公办医药本科；具有中药、药学、制药、食品和生物检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "山西师范大学", "山西省", "太原市", "https://www.sxnu.edu.cn/", "山西师范大学院系专业",
        "https://www.sxnu.edu.cn/", "官网院系专业包含化学与材料科学、生命科学和食品科学方向。",
        "公办普通本科；具有化学、材料、生物和食品质量安全方向。",
    ),
    VerifiedProvincialKeySeed(
        "忻州师范学院", "山西省", "忻州市", "https://www.xztu.edu.cn/", "忻州师范学院招生专业",
        "https://zs.xztu.edu.cn/yxzy.htm", "官网列有化学、生物科学、生物技术和生态学专业。",
        "公办普通本科；具有化学、生物与生态方向。",
    ),
    VerifiedProvincialKeySeed(
        "山西能源学院", "山西省", "晋中市", "https://www.sxie.edu.cn/", "山西能源学院招生专业简介",
        "https://www.sxie.edu.cn/xny/info/1151/2811.htm", "官网介绍能源化学工程、新能源材料及相关环境保护培养方向。",
        "公办普通本科；具有能源化学、材料、资源环境与检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "晋中学院", "山西省", "晋中市", "https://www.jzxy.edu.cn/", "晋中学院生物科学与技术系简介",
        "https://bio.jzxy.edu.cn/xbjj.html", "官网介绍生物科学专业及生物学实验技能培养。",
        "公办普通本科；具有生物、化学、复合材料和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "山西科技学院", "山西省", "晋城市", "https://www.sxist.edu.cn/", "山西科技学院化学工程学院简介",
        "https://hgxy.sxist.edu.cn/xygk/xyjj.htm", "官网介绍能源化工专业及化工、医药、环保和环境监测就业方向。",
        "公办普通本科；具有化学化工、材料、环境和能源检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "山西工学院", "山西省", "朔州市", "http://www.sxct.edu.cn/", "山西工学院本科招生专业",
        "http://www.sxct.edu.cn/", "官网招生专业包含化学工程与工艺、应用化学、环境工程和新能源材料。",
        "公办普通本科；具有化学化工、材料、环境与资源检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "运城学院", "山西省", "运城市", "https://www.ycu.edu.cn/", "运城学院院系专业",
        "https://www.ycu.edu.cn/", "官网院系专业包含应用化学、生物科学及检验检测培养方向。",
        "公办普通本科；具有化学、生物与检验检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "长治医学院", "山西省", "长治市", "https://www.czmc.edu.cn/", "长治医学院专业介绍",
        "https://zsjy.czmc.edu.cn/zyjs.htm", "官网列有药学、医学实验技术和医学检验技术等本科培养方案。",
        "公办医科本科；具有药学、生物医学和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "长治学院", "山西省", "长治市", "https://www.czc.edu.cn/", "长治学院化学系简介",
        "https://hxx.czc.edu.cn/xbgk/hxxjj.htm", "官网列有化学、化学生物学、药物化学和能源化学工程专业。",
        "公办普通本科；具有化学、生物、药物和环境生态方向。",
    ),
    VerifiedProvincialKeySeed(
        "山西工程技术学院", "山西省", "阳泉市", "https://www.sxit.edu.cn/", "山西工程技术学院招生专业介绍",
        "https://www.sxit.edu.cn/zsjyc/info/1006/2234.htm", "官网介绍材料科学与工程及物理化学、材料分析、新能源材料课程。",
        "公办普通本科；具有材料、化学、资源与环境检测方向。",
    ),
)


# 明确记录本轮目录中不纳入的公办本科，便于后续复核时区分“已筛除”和“尚未处理”。
ORDINARY_UNDERGRADUATE_BATCH_01_EXCLUSION_REASONS = {
    "河北金融学院": "财经类院校，未发现符合本轮标准的生物、环境、化学、材料或检测专业证据。",
    "河北经贸大学": "财经经管类院校，未发现符合本轮标准的生物、环境、化学、材料或检测专业证据。",
    "山西传媒学院": "传媒艺术类院校，未发现符合本轮标准的生物、环境、化学、材料或检测专业证据。",
    "山西财经大学": "财经类院校，未发现符合本轮标准的生物、环境、化学、材料或检测专业证据。",
}


# 新更名院校尚未形成稳定同名 POI，使用招生官网公布的法定主校区地址避免城市级模糊匹配。
OFFICIAL_MAIN_CAMPUS_ADDRESSES = {
    "应急管理大学": "河北省三河市燕郊高新技术产业开发区学院大街467号",
}


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把官网取证结果转为正式候选，并使用城市加校名触发严格主校区 POI 匹配。"""

    assert len(VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_01) == 46
    assert len({seed.name for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_01}) == 46
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
            tags=("高校", "普通公办本科", "官网专业证据", "普通本科第01批"),
        )
        for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_01
    )


def main() -> None:
    """幂等创建普通本科第 01 批；重复运行只返回原批次，不覆盖人工核验档案。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 普通公办本科生化环材核验第01批",
            source_scope=(
                "河北、山西教育部2026高校底表中尚未进入正式库的公办普通本科；逐校核验生物、环境、"
                "化学、材料、医药、食品农业或检测方向，排除既有高校及纯财经、传媒院校。"
            ),
            source_url=MOE_2026_UNIVERSITY_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-ordinary-undergraduate-import",
        )
    print(
        f"普通公办本科第01批完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
