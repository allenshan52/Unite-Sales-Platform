"""导入普通公办本科第 06 批：核验豫鄂湘粤目标专业并排队定位主校区。"""

from app.cli.import_verified_provincial_key_universities_batch_01 import VerifiedProvincialKeySeed
from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


MOE_2026_UNIVERSITY_DIRECTORY = (
    "https://www.moe.gov.cn/jyb_xxgk/s5743/s5744/202606/t20260618_1441074.html"
)

# 新设学校或同城多校区容易被 POI 简称误导，优先采用官网公开的主办学地址。
OFFICIAL_MAIN_CAMPUS_ADDRESSES = {
    "大湾区大学": "广东省东莞市松山湖高新技术产业开发区大学路16号",
    "长沙工业学院": "湖南省长沙市望城区旺旺西路366号",
}


def _seed(
    name: str,
    province: str,
    city: str,
    website: str,
    evidence_url: str,
    focus: str,
) -> VerifiedProvincialKeySeed:
    """把精简核验行转为统一证据记录，避免批量清单重复模板字段。"""

    return VerifiedProvincialKeySeed(
        name,
        province,
        city,
        website,
        f"{name}官网专业或院系证据",
        evidence_url,
        f"学校或主管部门官网确认其本科培养、学院或科研平台覆盖{focus}。",
        f"公办普通本科；具有{focus}，符合生化环材、医药、食品或检测客户筛选口径。",
    )


# 每行均以教育部底表确认学校边界，并用学校/主管部门官网补充目标专业证据。
_VERIFIED_ROWS = (
    ("信阳农林学院", "河南省", "信阳市", "https://www.xyafu.edu.cn/", "https://www.xyafu.edu.cn/zsxxw/zyjs.htm", "生物、食品、动物医学与检验检测方向"),
    ("信阳师范大学", "河南省", "信阳市", "https://www.xynu.edu.cn/", "https://zs.xynu.edu.cn/info/1007/1282.htm", "生物、化学、分子技术与仪器分析方向"),
    ("南阳师范学院", "河南省", "南阳市", "https://www.nynu.edu.cn/", "https://www2.nynu.edu.cn/huaxue/info/1046/4666.htm", "化学、材料与分析测试方向"),
    ("南阳理工学院", "河南省", "南阳市", "https://www.nyist.edu.cn/", "https://zsw.nyist.edu.cn/info/1230/9456.htm", "生物、食品、化工与制药方向"),
    ("河南国医学院", "河南省", "南阳市", "https://www.nymc.edu.cn/", "https://www.moe.gov.cn/srcsite/A03/s181/202606/t20260616_1440878.html", "中药学、食品科学与工程及食品营养方向"),
    ("周口师范学院", "河南省", "周口市", "https://www.zknu.edu.cn/", "https://www.zknu.edu.cn/", "化学、生物科学与实验教学方向"),
    ("商丘师范学院", "河南省", "商丘市", "https://www.sqnu.edu.cn/", "https://zsmobile.sqnu.edu.cn/info/1003/3314.htm", "化学、材料、制药与生物食品方向"),
    ("安阳工学院", "河南省", "安阳市", "https://www.ayit.edu.cn/", "https://xxgk.ayit.edu.cn/info/1198/2554.htm", "应用化学、生物、食品、环境与新材料方向"),
    ("安阳师范学院", "河南省", "安阳市", "https://www.aynu.edu.cn/", "https://huaxue.aynu.edu.cn/xygk.htm", "化学、应用化学、材料与制药方向"),
    ("平顶山学院", "河南省", "平顶山市", "https://www.pdsu.edu.cn/", "https://hxhg.pdsu.edu.cn/info/1318/4632.htm", "化学、化工、制药与新能源材料方向"),
    ("河南城建学院", "河南省", "平顶山市", "https://www.huuc.edu.cn/", "https://www.huuc.edu.cn/xyzy1.htm", "化工、材料、生物制药与环境检测方向"),
    ("新乡学院", "河南省", "新乡市", "https://www.xxu.edu.cn/", "https://sk.xxu.edu.cn/info/1080/5262.htm", "食品安全、检测与制药方向"),
    ("河南医药大学", "河南省", "新乡市", "https://www.hamu.edu.cn/", "https://www.xxmu.edu.cn/xxgk1/xxjj.htm", "医学检验、药学、生物与生物化学方向"),
    ("河南工学院", "河南省", "新乡市", "https://www.hait.edu.cn/", "https://clxnew.hait.edu.cn/xygk.htm", "材料、环境与分析测试方向"),
    ("河南科技学院", "河南省", "新乡市", "https://www.hist.edu.cn/", "https://spxy.hist.edu.cn/info/1413/5994.htm", "食品质量安全、生物与检验检测方向"),
    ("洛阳师范学院", "河南省", "洛阳市", "https://www.lynu.edu.cn/", "https://sites.lynu.edu.cn/hxxy/info/1010/7426.htm", "化学、材料、制药与实验分析方向"),
    ("洛阳理工学院", "河南省", "洛阳市", "https://www.lit.edu.cn/", "https://www.lit.edu.cn/hhxy/info/1102/4447.htm", "环境、应用化学、生物与材料方向"),
    ("许昌学院", "河南省", "许昌市", "https://www.xcu.edu.cn/", "https://shipin.xcu.edu.cn/xygk1/xyjj.htm", "食品安全、生物制药、化学与材料方向"),
    ("中原工学院", "河南省", "郑州市", "https://www.zut.edu.cn/", "https://mees.zut.edu.cn/bksjy/zysz.htm", "化学工程、应用化学、材料与环境方向"),
    ("河南工程学院", "河南省", "郑州市", "https://www.haue.edu.cn/", "https://www.haue.edu.cn/__local/8/B1/DA/2854EE86F5D5F4B454922457141_7846AFDF_11F492.pdf", "化工、材料、环境与资源检测方向"),
    ("河南牧业经济学院", "河南省", "郑州市", "https://www.hnuahe.edu.cn/", "https://zhaosheng.hnuahe.edu.cn/info/1447/3744.htm", "食品质量安全、生物工程与仪器分析方向"),
    ("郑州工程技术学院", "河南省", "郑州市", "https://www.zzut.edu.cn/", "https://pgddc.zzut.edu.cn/__local/F/E6/7A/EEF6B2F3EB025EBBCC6D52AAD0B_FB4A2CF7_2AC217.pdf", "食品科学、食品安全与化学工程方向"),
    ("郑州师范学院", "河南省", "郑州市", "https://www.zznu.edu.cn/", "https://www.zznu.edu.cn/jyjx/bksjy.htm", "化学、应用化学与生物科学方向"),
    ("郑州航空工业管理学院", "河南省", "郑州市", "https://www.zua.edu.cn/", "https://mse.zua.edu.cn/xygk.htm", "材料科学、功能材料与分析测试方向"),
    ("郑州轻工业大学", "河南省", "郑州市", "https://www.zzuli.edu.cn/", "https://jwc.zzuli.edu.cn/3110/list.htm", "食品科学、化学工程、材料与生物方向"),
    ("黄淮学院", "河南省", "驻马店市", "https://www.huanghuai.edu.cn/", "https://www.huanghuai.edu.cn/", "化学工程、材料、生物与食品方向"),
    ("汉江师范学院", "湖北省", "十堰市", "https://www.hjnu.edu.cn/", "https://zjc.hjnu.edu.cn/info/1015/1589.htm", "化学、应用化学、环境工程与生物科学方向"),
    ("湖北汽车工业学院", "湖北省", "十堰市", "https://www.huat.edu.cn/", "https://clxy.huat.edu.cn/", "材料科学、高分子材料与新能源材料方向"),
    ("湖北科技学院", "湖北省", "咸宁市", "https://www.hbust.edu.cn/", "https://xxgkw.hbust.edu.cn/__local/0/C4/82/CBAA299DB308E3E976BC635527D_B95D909C_23193.pdf", "化学、应用化学、生物科学与医学检验方向"),
    ("湖北工程学院", "湖北省", "孝感市", "https://www.hbeu.edu.cn/", "https://xxgk.hbeu.edu.cn/info/1506/15743.htm", "化学、材料、生物、食品与环境方向"),
    ("湖北民族大学", "湖北省", "恩施市", "https://www.hbmzu.edu.cn/", "https://www.hbmzu.edu.cn/xxgkw/info/1137/4871.htm", "化学工程、生物工程与食品科学方向"),
    ("武汉商学院", "湖北省", "武汉市", "https://www.wbu.edu.cn/", "https://zs.wbu.edu.cn/2026/0618/c1351a89856/page.htm", "食品质量安全、食品检测与营养方向"),
    ("湖北第二师范学院", "湖北省", "武汉市", "https://www.hue.edu.cn/", "https://xxgk.hue.edu.cn/2025/0716/c15498a190031/page.htm", "化学、生物科学与新能源材料方向"),
    ("荆楚理工学院", "湖北省", "荆门市", "https://www.jcut.edu.cn/", "https://spswxy.jcut.edu.cn/info/1070/2333.htm", "食品、生物、化工、制药与新能源材料方向"),
    ("湖北文理学院", "湖北省", "襄阳市", "https://www.hbuas.edu.cn/", "https://www.hbuas.edu.cn/info/1411/159901.htm", "食品科学、化学工程与医学检验方向"),
    ("黄冈师范学院", "湖北省", "黄冈市", "https://www.hgnu.edu.cn/", "https://shengwu.hgnu.edu.cn/2025/1103/c122a119553/page.htm", "生物、食品、化学与制药方向"),
    ("湖北理工学院", "湖北省", "黄石市", "https://www.hbpu.edu.cn/", "https://www.hbpu.edu.cn/rcpy/zysz.htm", "化工、生物制药、材料与环境方向"),
    ("湖南人文科技学院", "湖南省", "娄底市", "https://www.huhst.edu.cn/", "https://www.huhst.edu.cn/jwc2019/info/1084/10762.htm", "食品、化学、环境与材料方向"),
    ("湖南文理学院", "湖南省", "常德市", "https://www.huas.edu.cn/", "https://www.huas.edu.cn/info/1017/15757.htm", "化学、材料、制药、生物与食品方向"),
    ("怀化学院", "湖南省", "怀化市", "https://www.hhtc.edu.cn/", "https://jy.hhtc.edu.cn/detail/jobfair?id=28499", "生物、食品、制药、化学与材料方向"),
    ("湖南医药学院", "湖南省", "怀化市", "https://www.hnmu.com.cn/", "https://www.hnmu.com.cn/", "医学检验、药学与生物医学方向"),
    ("湖南科技学院", "湖南省", "永州市", "https://www.huse.edu.cn/", "https://www.huse.edu.cn/hxyswgcxy/xygk1/xyjj.htm", "化学、生物、食品安全、制药与材料方向"),
    ("湖南工程学院", "湖南省", "湘潭市", "https://www.hnie.edu.cn/", "https://www.hnie.edu.cn/info/1044/11332.htm", "化学工程、高分子材料与生物工程方向"),
    ("湖南城市学院", "湖南省", "益阳市", "https://www.hncu.edu.cn/", "https://xchy.hncu.edu.cn/info/1242/7282.htm", "环境工程、化学工程与材料方向"),
    ("湖南工学院", "湖南省", "衡阳市", "https://www.hnit.edu.cn/", "https://www.hnit.edu.cn/info/1324/84672.htm", "化工、应用化学、环境与无机材料方向"),
    ("衡阳师范学院", "湖南省", "衡阳市", "https://www.hynu.edu.cn/", "https://zs.hynu.edu.cn/zyjs/hxyclkxxy.htm", "化学、生物、食品、环境与材料方向"),
    ("邵阳学院", "湖南省", "邵阳市", "https://www.hnsyu.edu.cn/", "https://yxjs.hnsyu.edu.cn/info/1030/15021.htm", "医学检验、食品、化学、生物与制药方向"),
    ("湘南学院", "湖南省", "郴州市", "https://www.xnu.edu.cn/", "https://www.xnu.edu.cn/html/781/", "医学检验、药学、化学与环境方向"),
    ("长沙学院", "湖南省", "长沙市", "https://www.ccsu.cn/", "https://www.ccsu.cn/2.7.1.2025.pdf", "生物、生物制药、应用化学、功能材料与环境方向"),
    ("长沙工业学院", "湖南省", "长沙市", "https://www.ccsut.edu.cn/", "https://www.ccsut.edu.cn/html/43/20250620/769.html", "生物技术、制药工程与化学工程方向"),
    ("大湾区大学", "广东省", "东莞市", "https://www.gbu.edu.cn/", "https://www.gbu.edu.cn/undergraduate.html", "材料科学、电子信息材料与环境科学方向"),
    ("广东第二师范学院", "广东省", "广州市", "https://www.gdei.edu.cn/", "https://www.gdei.edu.cn/", "化学、材料、生物、食品质量安全与环境生态方向"),
    ("深圳技术大学", "广东省", "深圳市", "https://www.sztu.edu.cn/", "https://cop.sztu.edu.cn/info/1017/2931.htm", "药学、中药学、生物制药与材料方向"),
    ("深圳理工大学", "广东省", "深圳市", "https://www.suat-sz.edu.cn/", "https://synbio.suat-sz.edu.cn/xygk/xydsj.htm", "生物技术、合成生物学与生物医学方向"),
    ("肇庆医学院", "广东省", "肇庆市", "https://www.zqmc.edu.cn/", "https://zhaosheng.zqmc.edu.cn/xxgk/xxjj.htm", "医学检验、药学、中药学与食品卫生方向"),
)

VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_06 = tuple(_seed(*row) for row in _VERIFIED_ROWS)


# 记录本轮教育部底表内所有未纳入学校，避免“未出现”被误解为漏采。
ORDINARY_UNDERGRADUATE_BATCH_06_EXCLUSION_REASONS = {
    "河南应用工程学院": "新设公办本科；本轮未找到可追溯的生化环材、医药、食品或检测本科专业证据，暂不纳入。",
    "河南工业职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "黄河水利职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "河南能源化工学院": "新设公办本科；检索结果易与河南城建学院同名院系混淆，本轮证据不足，暂不纳入。",
    "河南财政金融学院": "财经类院校，未发现符合口径的目标本科专业证据。",
    "河南财经政法大学": "财经政法类院校，未发现符合口径的目标本科专业证据。",
    "郑州铁路职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "河南信息科技学院": "信息技术类院校，未发现符合口径的目标本科专业证据。",
    "湖北三峡职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "中南财经政法大学": "财经政法类院校，未发现符合口径的目标本科专业证据。",
    "武汉职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "武汉音乐学院": "艺术类院校，未发现符合口径的目标本科专业证据。",
    "湖北经济学院": "财经类院校，未发现符合口径的目标本科专业证据。",
    "湖北美术学院": "艺术类院校，未发现符合口径的目标本科专业证据。",
    "网络空间安全学院": "网络安全专门院校，未发现符合口径的目标本科专业证据。",
    "襄阳职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "黄冈职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "湖南化工职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "湖南汽车工程职业大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "湖南工艺美术职业大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "湖南女子学院": "现行专业以人文、管理、教育和艺术为主，未找到目标本科专业证据。",
    "湖南工商大学": "财经管理类院校，未发现符合口径的目标本科专业证据。",
    "湖南第一师范学院": "现行专业以教师教育和人文信息类为主，未找到目标本科专业证据。",
    "湖南财政经济学院": "财经类院校，未发现符合口径的目标本科专业证据。",
    "长沙师范学院": "现行专业以教师教育、人文和艺术类为主，未找到目标本科专业证据。",
    "香港城市大学（东莞）": "内地与港澳合作办学机构；本轮普通公办本科批次按既有口径暂不纳入。",
    "顺德职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "广东外语外贸大学": "语言经贸类院校，未发现符合口径的目标本科专业证据。",
    "广东财经大学": "财经类院校，未发现符合口径的目标本科专业证据。",
    "广东轻工职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "广东金融学院": "财经类院校，未发现符合口径的目标本科专业证据。",
    "广州美术学院": "艺术类院校，未发现符合口径的目标本科专业证据。",
    "广州职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "广州航海学院": "航运类院校，未发现符合口径的目标本科专业证据。",
    "星海音乐学院": "艺术类院校，未发现符合口径的目标本科专业证据。",
    "香港科技大学（广州）": "内地与港澳合作办学机构；本轮普通公办本科批次按既有口径暂不纳入。",
    "广东以色列理工学院": "中外合作办学机构；本轮普通公办本科批次按既有口径暂不纳入。",
    "深圳信息职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "深圳北理莫斯科大学": "中外合作办学机构；本轮普通公办本科批次按既有口径暂不纳入。",
    "深圳职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "香港中文大学（深圳）": "内地与港澳合作办学机构；本轮普通公办本科批次按既有口径暂不纳入。",
    "北师香港浸会大学": "内地与港澳合作办学机构；本轮普通公办本科批次按既有口径暂不纳入。",
}


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把官网核验结果交给既有低并发、严格主校区 POI 地理编码流程。"""

    assert len(VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_06) == 55
    assert len({seed.name for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_06}) == 55
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
            tags=("高校", "普通公办本科", "官网专业证据", "普通本科第06批"),
        )
        for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_06
    )


def main() -> None:
    """幂等创建第 06 批；重复执行返回原批次，不覆盖人工核验档案。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 普通公办本科生化环材核验第06批",
            source_scope=(
                "河南、湖北、湖南、广东教育部2026高校底表中尚未进入正式库的公办普通本科；逐校核验生物、"
                "环境、化学、材料、医药、食品或检测方向，排除职业本科、纯财经艺术信息院校及合作办学机构。"
            ),
            source_url=MOE_2026_UNIVERSITY_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-ordinary-undergraduate-import",
        )
    print(
        f"普通公办本科第06批完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
