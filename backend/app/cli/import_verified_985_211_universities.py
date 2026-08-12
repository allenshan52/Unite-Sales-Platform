"""已核验 985/211 高校入库：复用两轮筛选结论创建可追溯档案，再交给低并发高德编码队列。"""

from dataclasses import dataclass

from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


MOE_211_DIRECTORY = "https://www.moe.gov.cn/srcsite/A22/s7065/200512/t20051223_82762.html"
MOE_985_DIRECTORY = "https://www.moe.gov.cn/srcsite/A22/s7065/200612/t20061206_128833.html"


@dataclass(frozen=True)
class VerifiedUniversitySeed:
    """保存前两轮已确认的学校与主校区检索条件，避免把地址或坐标硬编码进源码。"""

    name: str
    province: str
    city: str
    website: str
    qualifying_direction: str


# 39 所名单以教育部 985 官方名单为准；旧库中的 11 所会作为重复候选保留而不覆盖。
VERIFIED_985_UNIVERSITIES = (
    VerifiedUniversitySeed("北京大学", "北京市", "北京市", "https://www.pku.edu.cn/", "化学、材料与生命科学"),
    VerifiedUniversitySeed("清华大学", "北京市", "北京市", "https://www.tsinghua.edu.cn/", "化学、材料与环境"),
    VerifiedUniversitySeed("中国人民大学", "北京市", "北京市", "https://www.ruc.edu.cn/", "环境与生态相关研究"),
    VerifiedUniversitySeed("北京航空航天大学", "北京市", "北京市", "https://www.buaa.edu.cn/", "材料科学与工程"),
    VerifiedUniversitySeed("北京理工大学", "北京市", "北京市", "https://www.bit.edu.cn/", "材料、化学与环境"),
    VerifiedUniversitySeed("中国农业大学", "北京市", "北京市", "https://www.cau.edu.cn/", "生物、环境与食品科学"),
    VerifiedUniversitySeed("北京师范大学", "北京市", "北京市", "https://www.bnu.edu.cn/", "化学、环境与生命科学"),
    VerifiedUniversitySeed("中央民族大学", "北京市", "北京市", "https://www.muc.edu.cn/", "生命与环境科学"),
    VerifiedUniversitySeed("南开大学", "天津市", "天津市", "https://www.nankai.edu.cn/", "化学与材料"),
    VerifiedUniversitySeed("天津大学", "天津市", "天津市", "https://www.tju.edu.cn/", "化学工程、材料与环境"),
    VerifiedUniversitySeed("大连理工大学", "辽宁省", "大连市", "https://www.dlut.edu.cn/", "化工、材料与环境"),
    VerifiedUniversitySeed("东北大学", "辽宁省", "沈阳市", "https://www.neu.edu.cn/", "材料与冶金"),
    VerifiedUniversitySeed("吉林大学", "吉林省", "长春市", "https://www.jlu.edu.cn/", "化学、材料与生命科学"),
    VerifiedUniversitySeed("哈尔滨工业大学", "黑龙江省", "哈尔滨市", "https://www.hit.edu.cn/", "化学与材料"),
    VerifiedUniversitySeed("复旦大学", "上海市", "上海市", "https://www.fudan.edu.cn/", "化学、材料与生命科学"),
    VerifiedUniversitySeed("同济大学", "上海市", "上海市", "https://www.tongji.edu.cn/", "环境、材料与生命科学"),
    VerifiedUniversitySeed("上海交通大学", "上海市", "上海市", "https://www.sjtu.edu.cn/", "化学、材料与环境"),
    VerifiedUniversitySeed("华东师范大学", "上海市", "上海市", "https://www.ecnu.edu.cn/", "化学与材料"),
    VerifiedUniversitySeed("南京大学", "江苏省", "南京市", "https://www.nju.edu.cn/", "化学、材料与环境"),
    VerifiedUniversitySeed("东南大学", "江苏省", "南京市", "https://www.seu.edu.cn/", "材料与环境"),
    VerifiedUniversitySeed("浙江大学", "浙江省", "杭州市", "https://www.zju.edu.cn/", "化学、材料与环境"),
    VerifiedUniversitySeed("中国科学技术大学", "安徽省", "合肥市", "https://www.ustc.edu.cn/", "化学、材料与生命科学"),
    VerifiedUniversitySeed("厦门大学", "福建省", "厦门市", "https://www.xmu.edu.cn/", "化学、材料与生命科学"),
    VerifiedUniversitySeed("山东大学", "山东省", "济南市", "https://www.sdu.edu.cn/", "化学、材料与环境"),
    VerifiedUniversitySeed("中国海洋大学", "山东省", "青岛市", "https://www.ouc.edu.cn/", "海洋化学与环境"),
    VerifiedUniversitySeed("武汉大学", "湖北省", "武汉市", "https://www.whu.edu.cn/", "化学、材料与生命科学"),
    VerifiedUniversitySeed("华中科技大学", "湖北省", "武汉市", "https://www.hust.edu.cn/", "材料、环境与生命科学"),
    VerifiedUniversitySeed("湖南大学", "湖南省", "长沙市", "https://www.hnu.edu.cn/", "化学、材料与环境"),
    VerifiedUniversitySeed("中南大学", "湖南省", "长沙市", "https://www.csu.edu.cn/", "材料、化学与环境"),
    VerifiedUniversitySeed("国防科技大学", "湖南省", "长沙市", "https://www.nudt.edu.cn/", "材料与化学相关研究"),
    VerifiedUniversitySeed("中山大学", "广东省", "广州市", "https://www.sysu.edu.cn/", "化学、材料与生命科学"),
    VerifiedUniversitySeed("华南理工大学", "广东省", "广州市", "https://www.scut.edu.cn/", "化工、材料与环境"),
    VerifiedUniversitySeed("四川大学", "四川省", "成都市", "https://www.scu.edu.cn/", "化学、材料与生命科学"),
    VerifiedUniversitySeed("电子科技大学", "四川省", "成都市", "https://www.uestc.edu.cn/", "材料科学与工程"),
    VerifiedUniversitySeed("重庆大学", "重庆市", "重庆市", "https://www.cqu.edu.cn/", "材料、化工与环境"),
    VerifiedUniversitySeed("西安交通大学", "陕西省", "西安市", "https://www.xjtu.edu.cn/", "化学与材料"),
    VerifiedUniversitySeed("西北工业大学", "陕西省", "西安市", "https://www.nwpu.edu.cn/", "材料科学与工程"),
    VerifiedUniversitySeed("西北农林科技大学", "陕西省", "咸阳市", "https://www.nwafu.edu.cn/", "生物、环境与食品科学"),
    VerifiedUniversitySeed("兰州大学", "甘肃省", "兰州市", "https://www.lzu.edu.cn/", "化学、材料与环境"),
)


# 60 所名单是“211 减 985”后通过前两轮生化环材或体育例外审核的新增对象；已入库两所不再列入。
VERIFIED_ONLY_211_UNIVERSITIES = (
    VerifiedUniversitySeed("北京交通大学", "北京市", "北京市", "https://www.bjtu.edu.cn/", "环境科学与工程"),
    VerifiedUniversitySeed("北京工业大学", "北京市", "北京市", "https://www.bjut.edu.cn/", "材料科学与工程"),
    VerifiedUniversitySeed("北京科技大学", "北京市", "北京市", "https://www.ustb.edu.cn/", "材料与环境"),
    VerifiedUniversitySeed("北京邮电大学", "北京市", "北京市", "https://www.bupt.edu.cn/", "材料科学与工程"),
    VerifiedUniversitySeed("北京林业大学", "北京市", "北京市", "https://www.bjfu.edu.cn/", "生物科学与环境"),
    VerifiedUniversitySeed("北京中医药大学", "北京市", "北京市", "https://www.bucm.edu.cn/", "生物工程与药学"),
    VerifiedUniversitySeed("华北电力大学", "北京市", "北京市", "https://www.ncepu.edu.cn/", "环境工程与材料"),
    VerifiedUniversitySeed("天津医科大学", "天津市", "天津市", "https://www.tmu.edu.cn/", "生物医药与药学"),
    VerifiedUniversitySeed("河北工业大学", "天津市", "天津市", "https://www.hebut.edu.cn/", "材料科学与工程"),
    VerifiedUniversitySeed("太原理工大学", "山西省", "太原市", "https://www.tyut.edu.cn/", "化学、材料与环境"),
    VerifiedUniversitySeed("内蒙古大学", "内蒙古自治区", "呼和浩特市", "https://www.imu.edu.cn/", "化学、生物与材料"),
    VerifiedUniversitySeed("辽宁大学", "辽宁省", "沈阳市", "https://www.lnu.edu.cn/", "化学、环境与生命科学"),
    VerifiedUniversitySeed("大连海事大学", "辽宁省", "大连市", "https://www.dlmu.edu.cn/", "环境科学与工程"),
    VerifiedUniversitySeed("延边大学", "吉林省", "延边朝鲜族自治州", "https://www.ybu.edu.cn/", "化学、生物与环境"),
    VerifiedUniversitySeed("东北师范大学", "吉林省", "长春市", "https://www.nenu.edu.cn/", "化学与生命科学"),
    VerifiedUniversitySeed("哈尔滨工程大学", "黑龙江省", "哈尔滨市", "https://www.hrbeu.edu.cn/", "材料与化学"),
    VerifiedUniversitySeed("东北农业大学", "黑龙江省", "哈尔滨市", "https://www.neau.edu.cn/", "生物、环境与食品科学"),
    VerifiedUniversitySeed("东北林业大学", "黑龙江省", "哈尔滨市", "https://www.nefu.edu.cn/", "生物与环境"),
    VerifiedUniversitySeed("东华大学", "上海市", "上海市", "https://www.dhu.edu.cn/", "材料与化学"),
    VerifiedUniversitySeed("上海大学", "上海市", "上海市", "https://www.shu.edu.cn/", "材料科学与工程"),
    VerifiedUniversitySeed("海军军医大学", "上海市", "上海市", "https://www.smmu.edu.cn/", "基础医学、生物与药学"),
    VerifiedUniversitySeed("苏州大学", "江苏省", "苏州市", "https://www.suda.edu.cn/", "化学与材料"),
    VerifiedUniversitySeed("南京航空航天大学", "江苏省", "南京市", "https://www.nuaa.edu.cn/", "材料科学与工程"),
    VerifiedUniversitySeed("南京理工大学", "江苏省", "南京市", "https://www.njust.edu.cn/", "化学与材料"),
    VerifiedUniversitySeed("中国矿业大学", "江苏省", "徐州市", "https://www.cumt.edu.cn/", "化学、材料与环境"),
    VerifiedUniversitySeed("河海大学", "江苏省", "南京市", "https://www.hhu.edu.cn/", "环境科学与工程"),
    VerifiedUniversitySeed("江南大学", "江苏省", "无锡市", "https://www.jiangnan.edu.cn/", "生物、食品与化学"),
    VerifiedUniversitySeed("南京农业大学", "江苏省", "南京市", "https://www.njau.edu.cn/", "生物、环境与食品科学"),
    VerifiedUniversitySeed("中国药科大学", "江苏省", "南京市", "https://www.cpu.edu.cn/", "药学与生物医药"),
    VerifiedUniversitySeed("南京师范大学", "江苏省", "南京市", "https://www.njnu.edu.cn/", "化学、生物与环境"),
    VerifiedUniversitySeed("安徽大学", "安徽省", "合肥市", "https://www.ahu.edu.cn/", "化学、材料与环境"),
    VerifiedUniversitySeed("合肥工业大学", "安徽省", "合肥市", "https://www.hfut.edu.cn/", "材料科学与工程"),
    VerifiedUniversitySeed("福州大学", "福建省", "福州市", "https://www.fzu.edu.cn/", "化学、材料与环境"),
    VerifiedUniversitySeed("南昌大学", "江西省", "南昌市", "https://www.ncu.edu.cn/", "化学、材料与生命科学"),
    VerifiedUniversitySeed("中国石油大学（华东）", "山东省", "青岛市", "https://www.upc.edu.cn/", "材料、化工与环境"),
    VerifiedUniversitySeed("郑州大学", "河南省", "郑州市", "https://www.zzu.edu.cn/", "材料、化学与环境"),
    VerifiedUniversitySeed("中国地质大学（武汉）", "湖北省", "武汉市", "https://www.cug.edu.cn/", "环境科学与材料"),
    VerifiedUniversitySeed("武汉理工大学", "湖北省", "武汉市", "https://www.whut.edu.cn/", "材料科学与工程"),
    VerifiedUniversitySeed("华中农业大学", "湖北省", "武汉市", "https://www.hzau.edu.cn/", "生物、环境与食品科学"),
    VerifiedUniversitySeed("华中师范大学", "湖北省", "武汉市", "https://www.ccnu.edu.cn/", "化学与生命科学"),
    VerifiedUniversitySeed("湖南师范大学", "湖南省", "长沙市", "https://www.hunnu.edu.cn/", "化学、材料与生命科学"),
    VerifiedUniversitySeed("暨南大学", "广东省", "广州市", "https://www.jnu.edu.cn/", "化学、材料与生命科学"),
    VerifiedUniversitySeed("华南师范大学", "广东省", "广州市", "https://www.scnu.edu.cn/", "化学、材料与生命科学"),
    VerifiedUniversitySeed("广西大学", "广西壮族自治区", "南宁市", "https://www.gxu.edu.cn/", "化学、材料与环境"),
    VerifiedUniversitySeed("海南大学", "海南省", "海口市", "https://www.hainanu.edu.cn/", "生物、环境与材料"),
    VerifiedUniversitySeed("西南交通大学", "四川省", "成都市", "https://www.swjtu.edu.cn/", "材料科学与工程"),
    VerifiedUniversitySeed("四川农业大学", "四川省", "雅安市", "https://www.sicau.edu.cn/", "生物、环境与食品科学"),
    VerifiedUniversitySeed("西南大学", "重庆市", "重庆市", "https://www.swu.edu.cn/", "化学、生物与环境"),
    VerifiedUniversitySeed("贵州大学", "贵州省", "贵阳市", "https://www.gzu.edu.cn/", "化学、材料与环境"),
    VerifiedUniversitySeed("云南大学", "云南省", "昆明市", "https://www.ynu.edu.cn/", "化学、材料与环境"),
    VerifiedUniversitySeed("西藏大学", "西藏自治区", "拉萨市", "https://www.utibet.edu.cn/", "化学、生物与环境"),
    VerifiedUniversitySeed("西北大学", "陕西省", "西安市", "https://www.nwu.edu.cn/", "化学、材料与生命科学"),
    VerifiedUniversitySeed("西安电子科技大学", "陕西省", "西安市", "https://www.xidian.edu.cn/", "材料科学与工程"),
    VerifiedUniversitySeed("长安大学", "陕西省", "西安市", "https://www.chd.edu.cn/", "材料与环境"),
    VerifiedUniversitySeed("陕西师范大学", "陕西省", "西安市", "https://www.snnu.edu.cn/", "化学、材料与生命科学"),
    VerifiedUniversitySeed("空军军医大学", "陕西省", "西安市", "https://www.fmmu.edu.cn/", "生物医学工程与生物技术"),
    VerifiedUniversitySeed("青海大学", "青海省", "西宁市", "https://www.qhu.edu.cn/", "化学、材料与环境"),
    VerifiedUniversitySeed("宁夏大学", "宁夏回族自治区", "银川市", "https://www.nxu.edu.cn/", "化学、材料与生命科学"),
    VerifiedUniversitySeed("新疆大学", "新疆维吾尔自治区", "乌鲁木齐市", "https://www.xju.edu.cn/", "化学、材料与环境"),
    VerifiedUniversitySeed("石河子大学", "新疆维吾尔自治区", "石河子市", "https://www.shzu.edu.cn/", "化学、材料与生命科学"),
)


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """将审核名单转为正式导入记录；用“城市+校名”触发高德严格同名主校区 POI 补齐地址。"""

    seeds = VERIFIED_985_UNIVERSITIES + VERIFIED_ONLY_211_UNIVERSITIES
    assert len(VERIFIED_985_UNIVERSITIES) == 39
    assert len(VERIFIED_ONLY_211_UNIVERSITIES) == 60
    assert len({seed.name for seed in seeds}) == 99
    return tuple(
        UniversityCandidate(
            name=seed.name,
            website=seed.website,
            province=seed.province,
            city=seed.city,
            district=None,
            address=f"{seed.city}{seed.name}",
            evidence_title=f"{seed.name}：前两轮筛选已核验的 {seed.qualifying_direction} 官网资料入口",
            evidence_url=seed.website,
            evidence_excerpt=(
                f"本单位已在前两轮 985/211 筛选中按官网公开的 {seed.qualifying_direction} 专业、院系或科研方向核验通过。"
                "本批次保留官网入口，供管理后台继续补充具体院系页证据。"
            ),
            inclusion_reason=f"已通过 985/211 高校筛选：存在 {seed.qualifying_direction} 相关本科专业、院系或科研方向。",
            tags=("高校", "985/211 已核验", "官网专业证据待复核"),
        )
        for seed in seeds
    )


def main() -> None:
    """创建 99 所已核验 985/211 高校批次；重复运行仅回写底表关联，绝不覆盖人工档案。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 已核验 39 所985与60所仅211高校",
            source_scope=(
                "教育部 985/211 官方名单差集与前两轮逐校官网专业筛选；"
                "本批次含 39 所985及60所仅211，主校区地址由高德严格同名 POI 低并发补齐。"
            ),
            source_url=MOE_211_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-985-211-import",
        )
    print(f"985/211 高校批次完成：新增 {batch.created_rows} 条，重复 {batch.duplicate_rows} 条，批次 ID：{batch.id}")
    print(f"名单底表：985={MOE_985_DIRECTORY}；211={MOE_211_DIRECTORY}")


if __name__ == "__main__":
    main()
