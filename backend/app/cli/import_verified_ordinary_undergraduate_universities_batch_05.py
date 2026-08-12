"""导入普通公办本科第 05 批：筛选皖闽赣鲁目标专业并排队定位主校区。"""

from app.cli.import_verified_provincial_key_universities_batch_01 import VerifiedProvincialKeySeed
from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


MOE_2026_UNIVERSITY_DIRECTORY = (
    "https://www.moe.gov.cn/jyb_xxgk/s5743/s5744/202606/t20260618_1441074.html"
)

# 同城简称检索不能稳定返回鲁东大学主校区，因此使用学校官网公布的法定门牌地址。
OFFICIAL_MAIN_CAMPUS_ADDRESSES = {
    "鲁东大学": "山东省烟台市芝罘区红旗中路186号",
}


def _seed(
    name: str,
    province: str,
    city: str,
    website: str,
    evidence_url: str,
    evidence_excerpt: str,
    inclusion_reason: str,
) -> VerifiedProvincialKeySeed:
    """用统一证据标题构造一所已核验高校，避免大批量静态清单重复样板字段。"""

    return VerifiedProvincialKeySeed(
        name,
        province,
        city,
        website,
        f"{name}官网专业或学院证据",
        evidence_url,
        evidence_excerpt,
        inclusion_reason,
    )


# 仅纳入教育部底表中尚未入库的公办普通本科；证据优先使用当前校级、院系或招生官网。
VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_05 = (
    _seed(
        "亳州学院", "安徽省", "亳州市", "https://www.bzuu.edu.cn/", "https://www.moe.gov.cn/srcsite/A08/moe_1034/s4930/202304/W020230419336779647503.pdf?wm=%3D2223_4257",
        "学校官网院系与本科专业信息列有生物工程、制药工程等生命健康相关方向。",
        "公办普通本科；具有生物工程、制药工程与药物分析相关方向。",
    ),
    _seed(
        "皖西学院", "安徽省", "六安市", "https://www.wxc.edu.cn/", "https://hsx.wxc.edu.cn/2024/0509/c1105a185853/page.htm",
        "学院官网列有中药学、药物制剂、制药工程、生物工程和食品质量与安全等本科专业。",
        "公办普通本科；具有生物、制药、食品安全与中药检测方向。",
    ),
    _seed(
        "合肥大学", "安徽省", "合肥市", "https://www.hfuu.edu.cn/", "https://www.hfuu.edu.cn/swx/_t482/1009/list.htm",
        "学校官网设置生物食品与环境学院、能源材料与化工学院及相关本科专业。",
        "公办普通本科；具有生物、食品、环境、材料与化工方向。",
    ),
    _seed(
        "合肥师范学院", "安徽省", "合肥市", "https://www.hfnu.edu.cn/", "https://zsb.hfnu.edu.cn/__local/5/3C/95/932FCA250D634912E14477D7A79_BC6E1F9A_71688.pdf",
        "招生官网材料列有生物科学、食品质量与安全、生物制药等本科专业。",
        "公办师范本科；具有生物、食品安全、生物制药与实验教学方向。",
    ),
    _seed(
        "合肥理工学院", "安徽省", "合肥市", "https://www.hfit.edu.cn/", "https://www.hfit.edu.cn/287/list.htm",
        "学校官网介绍材料科学与工程学院，开设新能源材料与器件、材料物理本科专业并建有分析测试中心。",
        "公办普通本科；具有新能源材料、材料表征与分析测试方向。",
    ),
    _seed(
        "安徽建筑大学", "安徽省", "合肥市", "https://www.ahjzu.edu.cn/", "https://www.ahjzu.edu.cn/hnxy/6092/list.htm",
        "学校官网设置环境与能源工程学院、材料与化学工程学院及相应本科专业和实验平台。",
        "公办普通本科；具有环境、材料、化学与分析检测方向。",
    ),
    _seed(
        "安徽第二医学院", "安徽省", "合肥市", "https://www.ahyz.edu.cn/", "https://yxjsxy.ahyz.edu.cn/info/1075/3072.htm",
        "学校官网本科人才培养覆盖医学检验技术、卫生检验与检疫、药学等方向。",
        "公办医科本科；具有医学检验、卫生检疫、药学与公共卫生方向。",
    ),
    _seed(
        "巢湖学院", "安徽省", "合肥市", "https://www.chu.edu.cn/", "https://www.chu.edu.cn/hxx/2024/0611/c4598a180188/page.htm",
        "学校官网院系专业信息列有化学工程与工艺、生物工程等本科专业。",
        "公办普通本科；具有化学工程、生物工程与实验分析方向。",
    ),
    _seed(
        "安庆师范大学", "安徽省", "安庆市", "https://www.aqnu.edu.cn/", "https://hxhg.aqnu.edu.cn/xygk/xyjj.htm",
        "学校官网设置化学化工学院、生命科学学院及化学、生物、材料、环境相关专业。",
        "公办师范本科；具有化学、生物、材料与环境研究方向。",
    ),
    _seed(
        "宿州学院", "安徽省", "宿州市", "https://www.ahszu.edu.cn/", "https://www.ahszu.edu.cn/zs/info/1128/5900.htm",
        "招生官网列有生物技术、食品科学与工程、食品质量与安全等专业及检验检疫培养方向。",
        "公办普通本科；具有生物、食品质量安全与检验检疫方向。",
    ),
    _seed(
        "池州学院", "安徽省", "池州市", "https://www.czu.edu.cn/", "https://zs.czu.edu.cn/yxzy.htm",
        "学校官网设置材料与环境工程学院并开展材料、环境及化学相关本科教学。",
        "公办普通本科；具有材料、环境与化学实验方向。",
    ),
    _seed(
        "淮北师范大学", "安徽省", "淮北市", "https://www.chnu.edu.cn/", "https://zsb.chnu.edu.cn/index.php?id=364",
        "招生官网介绍生物工程本科专业，培养内容覆盖生物制造、发酵与合成生物学。",
        "公办师范本科；具有生物工程、生物制造与化学材料方向。",
    ),
    _seed(
        "淮南师范学院", "安徽省", "淮南市", "https://www.hnnu.edu.cn/", "https://www.hnnu.edu.cn/",
        "学校官网设置生物工程学院、化学与材料工程学院及相应本科专业和实验平台。",
        "公办师范本科；具有生物、化学、材料与实验检测方向。",
    ),
    _seed(
        "安徽科技工程大学", "安徽省", "滁州市", "https://www.ahstu.edu.cn/", "https://www.ahstu.edu.cn/zsc/zyjs.htm",
        "学校官网设置生命与健康科学学院、食品工程学院、资源与环境学院及材料相关专业。",
        "公办普通本科；具有生物、食品、环境、材料与农业检测方向。",
    ),
    _seed(
        "滁州学院", "安徽省", "滁州市", "https://www.chzu.edu.cn/", "https://hsx.chzu.edu.cn/2025/0611/c13777a325392/page.htm",
        "学校官网设置生物与食品工程学院、材料与化学工程学院并开展相关本科培养。",
        "公办普通本科；具有生物、食品、材料、化学与质量检测方向。",
    ),
    _seed(
        "皖南医科大学", "安徽省", "芜湖市", "https://www.wnmc.edu.cn/", "https://jyxy.wnmc.edu.cn/xygk/xyjj.htm",
        "学校官网本科专业覆盖医学检验技术、卫生检验与检疫、药学和生物医学工程。",
        "公办医科本科；具有医学检验、卫生检疫、药学与生物医学方向。",
    ),
    _seed(
        "蚌埠医科大学", "安徽省", "蚌埠市", "https://www.bbmc.edu.cn/", "https://jwc.bbmc.edu.cn/info/1059/3291.htm",
        "学校官网本科专业覆盖医学检验技术、卫生检验与检疫、药学及生物科学方向。",
        "公办医科本科；具有医学检验、卫生检疫、药学与生物方向。",
    ),
    _seed(
        "蚌埠学院", "安徽省", "蚌埠市", "https://www.bbc.edu.cn/", "https://environment.bbc.edu.cn/_t275/2022/0527/c531a86782/page.htm",
        "学校官网设置食品与生物工程学院、材料与化学工程学院及相应实验平台。",
        "公办普通本科；具有食品、生物、材料、化学与质量检测方向。",
    ),
    _seed(
        "铜陵学院", "安徽省", "铜陵市", "https://www.tlu.edu.cn/", "https://www.tlu.edu.cn/_t1106/2026/0702/c4129a130784/page.htm",
        "学校官网列有材料科学与工程学院，其博士后研究方向包含化学、化学工程与技术。",
        "公办普通本科；具有金属材料、化学工程与铜基新材料方向。",
    ),
    _seed(
        "阜阳师范大学", "安徽省", "阜阳市", "https://www.fynu.edu.cn/", "https://www.fynu.edu.cn/swyspgcold/xygk/xyjj.htm",
        "学校官网设置化学与材料工程学院、生物与食品工程学院及相关本科专业。",
        "公办师范本科；具有化学、材料、生物、食品与实验检测方向。",
    ),
    _seed(
        "黄山学院", "安徽省", "黄山市", "https://www.hsu.edu.cn/", "https://hx.hsu.edu.cn/14/4c/c385a5196/page.htm",
        "学校官网设置化学化工学院、生命与环境科学学院及生化环材相关专业。",
        "公办普通本科；具有化学、生物、环境、材料与食品方向。",
    ),
    _seed(
        "三明学院", "福建省", "三明市", "https://www.fjsmu.edu.cn/", "https://zjc.fjsmu.edu.cn/2026/0512/c3328a181097/page.htm",
        "招生官网章程和专业信息覆盖化学、生物、环境、材料及相关工程本科专业。",
        "公办普通本科；具有化学、生物、环境、材料与检测方向。",
    ),
    _seed(
        "武夷学院", "福建省", "南平市", "https://www.wuyiu.edu.cn/", "https://www.wuyiu.edu.cn/csw/2026/0623/c953a139417/page.htm",
        "学校官网食品质量与安全专业内容覆盖食品化学、微生物和仪器分析检测。",
        "公办普通本科；具有食品、茶学、生物、环境与质量检测方向。",
    ),
    _seed(
        "厦门医学院", "福建省", "厦门市", "https://www.xmmc.edu.cn/", "https://www.moe.gov.cn/srcsite/A03/s181/201604/t20160401_236258.html",
        "教育部建校批复列出药学等首批本科专业，学校现有医学检验和药学相关培养。",
        "公办医科本科；具有医学检验、药学与生物医药方向。",
    ),
    _seed(
        "宁德师范学院", "福建省", "宁德市", "https://www.ndnu.edu.cn/", "https://hxx.ndnu.edu.cn/xygk.htm",
        "学院官网设置化学、新能源材料与器件等专业及材料化学实验平台。",
        "公办师范本科；具有化学、新能源材料、生物与环境方向。",
    ),
    _seed(
        "福建商学院", "福建省", "福州市", "https://www.fjbu.edu.cn/", "https://zsb.fjbu.edu.cn/__local/7/BA/F7/E49C694562110AD5E75D7DBD96_068DF8AB_10640.pdf",
        "招生官网材料列有烹饪与营养教育本科专业，涉及食品科学、营养与质量安全。",
        "公办普通本科；具有食品科学、营养与质量安全方向。",
    ),
    _seed(
        "福建技术师范学院", "福建省", "福州市", "https://www.fpnu.edu.cn/", "https://fpnu.edu.cn/xxgk1/xxgk.htm",
        "学校官网介绍食品、海洋生物、环境等相关本科专业和应用研究平台。",
        "公办师范本科；具有食品、生物、环境与分析检测方向。",
    ),
    _seed(
        "闽江大学", "福建省", "福州市", "https://www.mju.edu.cn/", "https://zsb.mju.edu.cn/2022/0516/c2312a134073/pagem.htm",
        "招生官网专业信息列有应用化学、高分子材料等化学材料相关本科专业。",
        "公办普通本科；具有化学、材料、海洋生物与环境方向。",
    ),
    _seed(
        "莆田学院", "福建省", "莆田市", "https://www.ptu.edu.cn/", "https://www.ptu.edu.cn/zhaosheng/info/1007/2324.htm",
        "招生官网章程和专业信息覆盖医学检验、药学、生物、环境及食品相关方向。",
        "公办普通本科；具有医学检验、药学、生物、环境与食品方向。",
    ),
    _seed(
        "龙岩学院", "福建省", "龙岩市", "https://www.lyun.edu.cn/", "https://www.lyun.edu.cn/info/1071/141761.htm",
        "学校官网机构和动态确认生命科学学院、化学与材料学院，并开展动物医学等本科培养。",
        "公办普通本科；具有生命科学、化学、材料、动物医学与环境资源方向。",
    ),
    _seed(
        "上饶师范学院", "江西省", "上饶市", "https://www.sru.edu.cn/", "https://www.crs.jsj.edu.cn/aproval/detail/3921",
        "教育部中外合作办学监管信息确认学校开展生物科学本科专业培养。",
        "公办师范本科；具有生物、化学、环境与实验教学方向。",
    ),
    _seed(
        "九江学院", "江西省", "九江市", "https://www.jju.edu.cn/", "https://zcgl.jju.edu.cn/xxgk/xxjj.htm",
        "学校官网简介列有化学化工、材料、药学、生命、环境及食品相关学科专业。",
        "公办普通本科；具有生物、化学、材料、环境、医药与食品方向。",
    ),
    _seed(
        "南昌医学院", "江西省", "南昌市", "https://www.ncmc.edu.cn/", "https://www.ncmc.edu.cn/newxxgk/xxjj.htm",
        "学校官网简介列有医学检验技术、药学、中药学等本科专业和实验平台。",
        "公办医科本科；具有医学检验、药学、中药与生物医药方向。",
    ),
    _seed(
        "南昌师范学院", "江西省", "南昌市", "https://www.ncnu.edu.cn/", "https://www.ncnu.edu.cn/",
        "学校官网设置化学与食品科学学院、生命科学学院并开展相关本科培养。",
        "公办师范本科；具有化学、生物、食品与实验教学方向。",
    ),
    _seed(
        "井冈山大学", "江西省", "吉安市", "https://www.jgsu.edu.cn/", "https://www.jgsu.edu.cn/info/1041/17651.htm",
        "学校官网专业信息覆盖化学、生物、环境、材料、药学与医学检验相关方向。",
        "公办普通本科；具有生化环材、医药与医学检验方向。",
    ),
    _seed(
        "宜春学院", "江西省", "宜春市", "https://www.jxycu.edu.cn/", "https://zsw.jxycu.edu.cn/zsw/2025/0719/c3700a141756/page.htm",
        "招生官网专业信息列有药学、生物工程、食品质量与安全、环境科学等本科专业。",
        "公办普通本科；具有药学、生物、食品安全、环境与检测方向。",
    ),
    _seed(
        "抚州医药学院", "江西省", "抚州市", "https://www.jxtcms.net/", "https://hudong.moe.gov.cn/srcsite/A03/s181/202506/t20250619_1194821.html",
        "学校官网办学定位及专业设置覆盖中药学、药学和医学检验等医药健康方向。",
        "公办医药本科；具有中药、药学、医学检验与生物医药方向。",
    ),
    _seed(
        "赣东学院", "江西省", "抚州市", "https://www.gdc.edu.cn/", "https://www.gdc.edu.cn/2026/0623/c52a9950/page.htm",
        "学校官网招生专业信息列有资源环境、化学工程、材料等相关本科方向。",
        "公办普通本科；具有环境、化学工程、材料与资源检测方向。",
    ),
    _seed(
        "新余学院", "江西省", "新余市", "https://www.xyc.edu.cn/", "https://zb.xyc.edu.cn/info/1018/4471.htm",
        "招生官网专业信息覆盖新能源材料与器件、材料科学与工程等本科专业。",
        "公办普通本科；具有新能源材料、材料分析与生物健康方向。",
    ),
    _seed(
        "景德镇学院", "江西省", "景德镇市", "https://www.jdzu.edu.cn/", "https://shxy.jdzu.edu.cn/info/1111/1061.htm",
        "学院官网介绍生物与环境相关本科专业及生态、食品和实验检测培养内容。",
        "公办普通本科；具有生物、环境、食品与生态检测方向。",
    ),
    _seed(
        "萍乡学院", "江西省", "萍乡市", "https://www.pxc.jx.cn/", "https://zsw.pxc.jx.cn/info/1103/3335.htm",
        "招生官网专业信息列有环境科学与工程、无机非金属材料工程等本科专业。",
        "公办普通本科；具有环境、材料、化学与分析检测方向。",
    ),
    _seed(
        "赣南科技学院", "江西省", "赣州市", "https://www.gnust.edu.cn/", "https://zs.gnust.edu.cn/info/1022/7501.htm",
        "招生官网专业信息列有材料成型、冶金工程等材料类本科专业和实验方向。",
        "公办普通本科；具有材料、冶金、资源与分析检测方向。",
    ),
    _seed(
        "山东石油化工学院", "山东省", "东营市", "https://www.sdipct.edu.cn/", "https://hgxy.sdipct.edu.cn/xygk.htm",
        "学院官网设置化学工程与工艺、应用化学、环境工程等本科专业。",
        "公办普通本科；具有化工、应用化学、环境与分析检测方向。",
    ),
    _seed(
        "临沂大学", "山东省", "临沂市", "https://www.lyu.edu.cn/", "https://smkx.lyu.edu.cn/_upload/article/files/71/35/44f31b1e44e4a561ef7e6f89968c/13deda13-deb0-4029-8613-c04121a1de3c.pdf",
        "学校官网生物技术本科培养方案列有生物化学、微生物学和分子生物学等核心课程。",
        "公办普通本科；具有生物、化学、材料、环境与药学方向。",
    ),
    _seed(
        "德州学院", "山东省", "德州市", "https://www.dzu.edu.cn/", "https://zs.dzu.edu.cn/__local/8/3E/28/65AFEE43AA5D0685093D2698489_C20C8339_283F2.pdf",
        "招生官网材料列有化学、生物科学、环境生态工程、制药工程等本科专业。",
        "公办普通本科；具有生物、化学、环境、制药与材料方向。",
    ),
    _seed(
        "枣庄学院", "山东省", "枣庄市", "https://www.uzz.edu.cn/", "https://jwc.uzz.edu.cn/info/1130/2447.htm",
        "学校官网专业建设信息覆盖生物、化学、材料、食品及制药相关本科方向。",
        "公办普通本科；具有生物、化学、材料、食品与制药方向。",
    ),
    _seed(
        "泰山学院", "山东省", "泰安市", "https://www.tsu.edu.cn/", "https://chem.tsu.edu.cn/2025/1009/c10817a129355/page.htm",
        "学院官网确认化学及相关材料化工本科教学、实验和科研平台。",
        "公办普通本科；具有化学、材料、生物与实验分析方向。",
    ),
    _seed(
        "山东交通学院", "山东省", "济南市", "https://www.sdjtu.edu.cn/", "https://zsw.sdjtu.edu.cn/zyjs.htm",
        "招生官网专业介绍列有材料科学与工程、环境工程等本科专业。",
        "公办普通本科；具有材料、环境与工程检测方向。",
    ),
    _seed(
        "山东农业工程学院", "山东省", "济南市", "https://www.sdaeu.edu.cn/", "https://www.sdaeu.edu.cn/zsxx/info/1029/3042.htm",
        "招生官网专业信息覆盖资源环境、食品质量安全、生物与农业相关本科方向。",
        "公办普通本科；具有食品安全、生物、资源环境与农业检测方向。",
    ),
    _seed(
        "山东建筑大学", "山东省", "济南市", "https://www.sdjzu.edu.cn/", "https://www.sdjzu.edu.cn/jwc/info/1043/2014.htm",
        "学校官网专业信息列有环境工程、材料科学与工程等本科专业。",
        "公办普通本科；具有环境、材料、化学与建筑质量检测方向。",
    ),
    _seed(
        "齐鲁师范学院", "山东省", "济南市", "https://www.qlnu.edu.cn/", "https://smkx.qlnu.edu.cn/xygk/xyjj.htm",
        "学院官网设置生物科学、生物信息学、食品质量与安全等本科专业和实验室。",
        "公办师范本科；具有生物、食品安全与实验检测方向。",
    ),
    _seed(
        "济宁医学院", "山东省", "济宁市", "https://www.jnmc.edu.cn/", "https://yxy.jnmc.edu.cn/2019/0313/c154a852/page.htm",
        "药学院官网介绍药学、药物制剂、中药学等本科专业及药物分析实验平台。",
        "公办医科本科；具有医学检验、药学、药物分析与生物医学方向。",
    ),
    _seed(
        "济宁学院", "山东省", "济宁市", "https://www.jnxy.edu.cn/", "https://zs.jnxy.edu.cn/xyzy.htm",
        "招生官网专业介绍列有化学、生物工程、食品科学与工程等本科专业。",
        "公办普通本科；具有化学、生物、食品与实验分析方向。",
    ),
    _seed(
        "山东医药大学", "山东省", "泰安市", "https://www.sdmpu.edu.cn/", "https://zb.sdmpu.edu.cn/2026/0518/c2111a145737/page.htm",
        "招生官网专业信息覆盖医学检验、卫生检验、药学、生物制药等本科方向。",
        "公办医药本科；具有医学检验、卫生检疫、药学与生物制药方向。",
    ),
    _seed(
        "山东航空学院", "山东省", "滨州市", "https://www.sdua.edu.cn/", "https://smkx.sdua.edu.cn/2025/0619/c23076a286220/page.htm",
        "生命科学学院官网专业信息列有生物技术、生态学等本科培养方向。",
        "公办普通本科；具有生物、生态、化学与环境研究方向。",
    ),
    _seed(
        "山东第二医科大学", "山东省", "潍坊市", "https://www.sdsmu.edu.cn/", "https://yxxy.sdsmu.edu.cn/2024/0929/c4717a141161/page.htm",
        "学校官网学院专业信息覆盖医学检验、卫生检验、药学和生物医学相关方向。",
        "公办医科本科；具有医学检验、卫生检疫、药学与生物医学方向。",
    ),
    _seed(
        "潍坊学院", "山东省", "潍坊市", "https://www.wfu.edu.cn/", "https://chem.wfu.edu.cn/",
        "化学化工与环境工程学院官网展示化学、化工、环境及相关实验教学科研平台。",
        "公办普通本科；具有化学、化工、环境、生物与材料方向。",
    ),
    _seed(
        "鲁东大学", "山东省", "烟台市", "https://www.ldu.edu.cn/", "https://mse.ldu.edu.cn/yxgk/xyjj.htm",
        "材料与工程学院官网介绍高分子材料、新能源材料等本科专业和表征平台。",
        "公办普通本科；具有材料、化学、生物、环境与食品方向。",
    ),
    _seed(
        "聊城大学", "山东省", "聊城市", "https://www.lcu.edu.cn/", "https://hxhgxy.lcu.edu.cn/yjsjy1/pyfa2/52ce74ddd8464e20949a6b69de36586e.htm",
        "化学化工学院官网培养方案覆盖化学、化工、材料与分析测试研究方向。",
        "公办普通本科；具有化学、材料、生物、环境与食品方向。",
    ),
    _seed(
        "康复大学", "山东省", "青岛市", "https://www.uhrs.edu.cn/", "https://www.uhrs.edu.cn/info/1050/1799.htm",
        "学校官网专业与科研信息覆盖生物医学工程、康复科学及医学检验相关平台。",
        "公办医科本科；具有生物医学、医学检验与康复科学研究方向。",
    ),
    _seed(
        "菏泽学院", "山东省", "菏泽市", "https://www.hezeu.edu.cn/", "https://yxx.hezeu.edu.cn/info/1096/4867.htm",
        "药学院官网介绍药学、制药工程等本科专业及药物分析实验教学。",
        "公办普通本科；具有药学、制药、生物、化学与食品方向。",
    ),
)


# 记录本轮未纳入的全部公办本科边界，便于后台和后续批次解释筛选差异。
ORDINARY_UNDERGRADUATE_BATCH_05_EXCLUSION_REASONS = {
    "安徽职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "安徽艺术学院": "艺术类院校，未发现符合本轮标准的生化环材、医药、食品或检测本科专业证据。",
    "安徽应用技术职业大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "芜湖职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "安徽财经大学": "财经类院校，未发现符合本轮标准的生化环材、医药、食品或检测本科专业证据。",
    "黎明职业大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "福州职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "福建江夏学院": "财经政法类院校，未发现符合本轮标准的生化环材、医药、食品或检测本科专业证据。",
    "江西职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "江西外语外贸职业大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "江西水利电力大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "江西财经大学": "财经类院校，未发现符合本轮标准的生化环材、医药、食品或检测本科专业证据。",
    "江西飞行学院": "航空运输与飞行应用类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "豫章师范学院": "现行本科专业以师范、人文和信息类为主，未找到满足口径的生化环材本科专业证据。",
    "日照职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "山东商业职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "山东女子学院": "现行本科专业以人文、管理、教育和艺术类为主，未找到满足口径的生化环材本科专业证据。",
    "山东工艺美术学院": "艺术类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "山东政法学院": "政法类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "山东管理学院": "管理类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "山东艺术学院": "艺术类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "山东财经大学": "财经类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "山东青年政治学院": "青年政治与人文管理类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "淄博职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "滨州职业技术大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "山东科技职业大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
    "山东工商学院": "财经管理类院校，未发现符合本轮标准的生化环材、医药、食品或检测本科专业证据。",
}


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把官网核验结果转为正式候选，并交给既有低并发严格主校区 POI 流程。"""

    assert len(VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_05) == 61
    assert len({seed.name for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_05}) == 61
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
            tags=("高校", "普通公办本科", "官网专业证据", "普通本科第05批"),
        )
        for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_05
    )


def main() -> None:
    """幂等创建第 05 批；重复执行返回原批次，不覆盖人工核验档案。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 普通公办本科生化环材核验第05批",
            source_scope=(
                "安徽、福建、江西、山东教育部2026高校底表中尚未进入正式库的公办普通本科；逐校核验生物、"
                "环境、化学、材料、医药、食品或检测方向，排除既有高校、职业本科及纯财经政法艺术院校。"
            ),
            source_url=MOE_2026_UNIVERSITY_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-ordinary-undergraduate-import",
        )
    print(
        f"普通公办本科第05批完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
