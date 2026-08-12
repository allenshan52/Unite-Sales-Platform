"""导入普通公办本科第 04 批：筛选上海、江苏、浙江目标专业并排队定位主校区。"""

from app.cli.import_verified_provincial_key_universities_batch_01 import VerifiedProvincialKeySeed
from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


MOE_2026_UNIVERSITY_DIRECTORY = (
    "https://www.moe.gov.cn/jyb_xxgk/s5743/s5744/202606/t20260618_1441074.html"
)


# 仅纳入教育部底表中尚未入库的公办普通本科；每校都保留可回查的校级、院系或招生官网专业证据。
VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_04 = (
    VerifiedProvincialKeySeed(
        "上海电机学院", "上海市", "上海市", "https://www.sdju.edu.cn/", "上海电机学院本科专业设置",
        "https://zwgk.sdju.edu.cn/2025/1215/c4244a147012/page.htm",
        "学校官网本科专业表列有材料科学与工程、材料成型及控制工程、焊接技术与工程等材料类专业。",
        "公办普通本科；具有材料科学、材料成型与焊接检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "上海海事大学", "上海市", "上海市", "https://www.shmtu.edu.cn/", "上海海事大学海洋环境与工程学院专业介绍",
        "https://oec.shmtu.edu.cn/2026/0528/c6377a293867/page.htm",
        "学院官网列有环境工程、材料科学与工程本科专业及环境监测、污染控制和材料分析方向。",
        "公办普通本科；具有环境工程、材料科学与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "上海海关学院", "上海市", "上海市", "https://www.shcc.edu.cn/", "上海海关学院海关检验检疫安全专业介绍",
        "https://www.shcc.edu.cn/1255/list.htm",
        "学校官网介绍海关检验检疫安全专业，课程覆盖化学、生物学、卫生检疫、动植物检疫和食品安全。",
        "公办普通本科；具有海关检验检疫、食品安全与生物化学检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "上海第二工业大学", "上海市", "上海市", "https://www.sspu.edu.cn/", "上海第二工业大学资源与环境工程学院简介",
        "https://zihuan.sspu.edu.cn/2021/0901/c2225a47507/page.htm",
        "学院官网列有环境工程、环保设备工程、应用化学等本科专业和环境检测实验平台。",
        "公办普通本科；具有环境、应用化学与检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "上海电力大学", "上海市", "上海市", "https://www.shiep.edu.cn/", "上海电力大学环境与化学工程学院专业介绍",
        "https://hhxy.shiep.edu.cn/f6/31/c5522a194097/page.htm",
        "学院官网介绍环境工程本科专业及环境监测、分析化学和污染控制培养内容。",
        "公办普通本科；具有环境工程、化学分析与环境监测方向。",
    ),
    VerifiedProvincialKeySeed(
        "上海商学院", "上海市", "上海市", "https://www.sbs.edu.cn/", "上海商学院食品质量与安全专业概况",
        "https://jdglxy.sbs.edu.cn/spzlyaq/zygk/82eee1e8d2554c6982f697c18098b55f.htm",
        "学院官网介绍食品质量与安全本科专业，培养内容包含食品理化、微生物与仪器分析检测。",
        "公办普通本科；具有食品质量安全与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "上海健康医学院", "上海市", "上海市", "https://www.sumhs.edu.cn/", "上海健康医学院本科专业设置",
        "https://xxgk.sumhs.edu.cn/30/0f/c2176a274447/page.htm",
        "学校官网专业表列有医学检验技术、卫生检验与检疫、药学、药物分析和生物医学工程。",
        "公办医科本科；具有医学检验、卫生检疫、药学与药物分析方向。",
    ),
    VerifiedProvincialKeySeed(
        "南京财经大学", "江苏省", "南京市", "https://www.nufe.edu.cn/", "南京财经大学食品科学与工程学院专业介绍",
        "https://spgc.nufe.edu.cn/info/1030/1610.htm",
        "学院官网列有食品科学与工程、食品质量与安全、粮食工程和应用化学等本科专业。",
        "公办普通本科；具有食品、粮油、应用化学与质量检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "南京工程学院", "江苏省", "南京市", "https://www.njit.edu.cn/", "南京工程学院学校简介",
        "https://www.njit.edu.cn/info/1185/25675.htm",
        "学校官网介绍材料科学与工程学院及材料科学与工程、功能材料等本科教学科研方向。",
        "公办普通本科；具有材料科学、功能材料与分析表征方向。",
    ),
    VerifiedProvincialKeySeed(
        "南京晓庄学院", "江苏省", "南京市", "https://www.njxzc.edu.cn/", "南京晓庄学院食品科学学院专业设置",
        "https://biofood.njxzc.edu.cn/8660/list.htm",
        "学院官网列有生物科学、食品科学与工程和食品质量与安全本科专业。",
        "公办师范本科；具有生物、食品和质量安全检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "江苏第二师范学院", "江苏省", "南京市", "https://www.jssnu.edu.cn/", "江苏第二师范学院生命科学与化学化工学院介绍",
        "https://zs.jssnu.edu.cn/2023/0522/c3707a50568/page.htm",
        "招生官网介绍生物科学、生物制药等本科专业及生命科学、化学和环境科学实验平台。",
        "公办师范本科；具有生物科学、生物制药、化学与环境研究方向。",
    ),
    VerifiedProvincialKeySeed(
        "金陵科技学院", "江苏省", "南京市", "https://www.jit.edu.cn/", "金陵科技学院学校简介",
        "https://www.jit.edu.cn/xxgk/xxjj.htm",
        "学校官网列有材料科学与工程、动物医学、动物科学等专业及相关实验教学平台。",
        "公办普通本科；具有材料、动物医学、生物与检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "宿迁学院", "江苏省", "宿迁市", "https://www.squ.edu.cn/", "宿迁学院生物与材料工程学院简介",
        "https://scxy.squ.edu.cn/xygk/xyjj.htm",
        "学院官网列有材料科学与工程、生物工程、化学等本科专业和实验中心。",
        "公办普通本科；具有材料、生物工程、化学与实验分析方向。",
    ),
    VerifiedProvincialKeySeed(
        "常州工学院", "江苏省", "常州市", "https://www.czu.cn/", "常州工学院化工与材料学院专业设置",
        "https://jwc.czu.cn/_t70/2018/0408/c8446a57235/page.htm",
        "学校官网列有材料化学、化学工程与工艺等本科专业和化工材料实验教学内容。",
        "公办普通本科；具有材料化学、化学工程与分析实验方向。",
    ),
    VerifiedProvincialKeySeed(
        "江苏理工学院", "江苏省", "常州市", "https://www.jsut.edu.cn/", "江苏理工学院材料工程学院简介",
        "https://clxy.jsut.edu.cn/2588/list.htm",
        "学院官网介绍材料成型、金属材料、高分子材料等本科专业和材料检测实验平台。",
        "公办普通本科；具有材料工程、高分子材料与检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "徐州工程学院", "江苏省", "徐州市", "https://www.xzit.edu.cn/", "徐州工程学院招生专业介绍",
        "https://zjc.xzit.edu.cn/zhaosheng/23/c0/c5418a205760/page.htm",
        "招生官网列有化学工程与工艺、生物工程、食品科学、环境工程和高分子材料等专业。",
        "公办普通本科；具有生物、化工、食品、环境与材料方向。",
    ),
    VerifiedProvincialKeySeed(
        "江苏师范大学", "江苏省", "徐州市", "https://www.jsnu.edu.cn/", "江苏师范大学综合评价招生简章",
        "https://bkzs.jsnu.edu.cn/14/25/c10717a398373/page.htm?appPrefix=jsnu",
        "招生官网明确列出化学（师范）和生物科学（师范）本科招生专业。",
        "公办师范本科；具有化学、生物科学与实验教学方向。",
    ),
    VerifiedProvincialKeySeed(
        "无锡学院", "江苏省", "无锡市", "https://www.cwxu.edu.cn/", "无锡学院环境工程学院简介",
        "https://hjgcxy.cwxu.edu.cn/xygk/xyjj.htm",
        "学院官网列有环境科学与工程、应用化学等专业及环境监测和分析实验方向。",
        "公办普通本科；具有环境、应用化学与监测检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "泰州学院", "江苏省", "泰州市", "https://www.tzu.edu.cn/", "泰州学院本科专业设置材料",
        "https://bk.tzu.edu.cn/_upload/article/files/66/f9/5d85b0fa4aa88182017a99521c27/06374cad-f355-45d3-81b1-3b692990f7ee.pdf",
        "学校官网材料列有应用化学、生物制药、制药工程和环境工程等本科专业。",
        "公办普通本科；具有应用化学、生物制药、制药工程与环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "淮安大学", "江苏省", "淮安市", "https://www.hyit.edu.cn/", "淮安大学本科教学质量报告",
        "https://xxgk.hyit.edu.cn/__local/A/ED/CA/4BF41A4C8B41EF49CC66866307D_35D315DC_3A255.pdf?e=.pdf",
        "学校官网质量报告列有材料、化学工程、生物工程等本科专业和相关实验教学平台。",
        "公办普通本科；具有材料、化工、生物与分析实验方向。",
    ),
    VerifiedProvincialKeySeed(
        "淮阴师范学院", "江苏省", "淮安市", "https://www.hytc.edu.cn/", "淮阴师范学院生命科学学院简介",
        "https://sw.hytc.edu.cn/xygk1/xyjj.htm",
        "学院官网列有生物科学、生物技术、生物工程、食品质量与安全和生物制药等专业。",
        "公办师范本科；具有生物、食品安全、生物制药与检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "盐城工学院", "江苏省", "盐城市", "https://www.ycit.edu.cn/", "盐城工学院化学化工学院专业介绍",
        "https://chem.ycit.edu.cn/info/1038/2360.htm",
        "学院官网介绍应用化学、化学工程、制药工程等本科专业及分析检测培养内容。",
        "公办普通本科；具有应用化学、化工、制药与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "盐城师范学院", "江苏省", "盐城市", "https://www.yctu.edu.cn/", "盐城师范学院化学与环境工程学院概况",
        "https://chemical.yctu.edu.cn/xygk/list.htm",
        "学院官网列有化学、应用化学、环境工程和资源环境等本科专业。",
        "公办师范本科；具有化学、应用化学、环境工程与资源环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "苏州城市学院", "江苏省", "苏州市", "https://www.szcu.edu.cn/", "苏州城市学院本科专业建设材料",
        "https://jwc.szcu.edu.cn/_upload/article/files/f1/1d/f65b5b6047499ffd7b65bc608aba/687f21e3-7f51-40b2-8621-2c06527409c2.pdf",
        "学校官网材料列有新能源材料与器件本科专业及材料制备、表征与应用培养内容。",
        "公办普通本科；具有新能源材料、材料表征与应用方向。",
    ),
    VerifiedProvincialKeySeed(
        "苏州工学院", "江苏省", "苏州市", "https://www.szut.edu.cn/", "苏州工学院生物与食品工程学院介绍",
        "https://swxy.szut.edu.cn/xygk/xyjs.htm",
        "学院官网列有生物工程、食品质量与安全、食品科学、生物制药和合成生物学本科专业。",
        "公办普通本科；具有生物、食品安全、生物制药与检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "江苏海洋大学", "江苏省", "连云港市", "https://www.jou.edu.cn/", "江苏海洋大学招生专业介绍",
        "https://zsxx.jou.edu.cn/info/1071/1942.htm",
        "招生官网列有生物技术、高分子材料、化学工程、制药工程、环境工程、食品与药物分析等专业。",
        "公办普通本科；具有海洋生物、材料、化工、环境、食品与药物分析方向。",
    ),
    VerifiedProvincialKeySeed(
        "连云港师范学院", "江苏省", "连云港市", "https://www.lygsf.edu.cn/", "连云港师范学院新增本科专业介绍",
        "https://www.lygsf.edu.cn/2026/0515/c1150a40657/page.htm",
        "学校官网介绍应用化学和制药工程本科专业，应用化学突出化学分析与仪器检测特色。",
        "公办师范本科；具有应用化学、制药工程与仪器分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "丽水学院", "浙江省", "丽水市", "https://www.lsu.edu.cn/", "丽水学院本科专业选考科目要求",
        "https://www.lsu.edu.cn/_upload/article/files/e8/02/90812bf1419881b13a4ee1b247d7/c0faff34-afb2-4090-a183-3611698852c0.pdf",
        "学校官网专业表列有应用化学、环境工程、新能源材料、生物制药和生态学等本科专业。",
        "公办普通本科；具有化学、环境、材料、生物制药与生态方向。",
    ),
    VerifiedProvincialKeySeed(
        "台州学院", "浙江省", "台州市", "https://www.tzc.edu.cn/", "台州学院应用化学专业介绍",
        "https://zs.tzc.edu.cn/zyjs/yyhgxy/yyhx.htm",
        "招生官网介绍应用化学本科专业，设置质量监控和新能源方向并覆盖仪器分析检测。",
        "公办普通本科；具有应用化学、质量监控、新能源材料与检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "嘉兴南湖学院", "浙江省", "嘉兴市", "https://www.jxnhu.edu.cn/", "嘉兴南湖学院化学工程与工艺专业介绍",
        "https://xcl.jxnhu.edu.cn/zyjs/hxgcygy.htm",
        "学院官网介绍化学工程与工艺本科专业及制药、材料、能源、食品和分析检测就业方向。",
        "公办普通本科；具有化学工程、材料、制药与分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "嘉兴大学", "浙江省", "嘉兴市", "https://www.zjxu.edu.cn/", "嘉兴大学生物与化学工程学院简介",
        "https://cbcse.zjxu.edu.cn/xygk/xyjj.htm",
        "学院官网列有化学工程、应用化学、生物工程、环境工程和制药工程五个本科专业。",
        "公办普通本科；具有生物、化学、环境、制药与材料化工方向。",
    ),
    VerifiedProvincialKeySeed(
        "宁波工程学院", "浙江省", "宁波市", "https://www.nbut.edu.cn/", "宁波工程学院化学工程与工艺专业介绍",
        "https://chxy.nbut.edu.cn/info/1088/1020.htm",
        "学院官网介绍化学工程与工艺本科专业及化学化工、聚合材料实验教学平台。",
        "公办普通本科；具有化学工程、高分子材料与分析实验方向。",
    ),
    VerifiedProvincialKeySeed(
        "浙大宁波理工学院", "浙江省", "宁波市", "https://www.nbt.edu.cn/", "浙大宁波理工学院生物工程专业介绍",
        "https://swzy.nbt.edu.cn/info/1046/4880.htm",
        "学院官网介绍生物工程本科专业及生物化学、分子生物、体外诊断和生化检验课程。",
        "公办普通本科；具有生物工程、化学工程、材料与体外诊断检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "浙江万里学院", "浙江省", "宁波市", "https://www.zwu.edu.cn/", "浙江万里学院生物科学系简介",
        "https://swxy.zwu.edu.cn/fe/fa/c8286a196346/page.htm",
        "学院官网列有生物技术、生物工程和生物制药三个本科专业及生物实验平台。",
        "公办普通本科；具有生物技术、生物工程、生物制药与环境食品方向。",
    ),
    VerifiedProvincialKeySeed(
        "杭州医学院", "浙江省", "杭州市", "https://www.hmc.edu.cn/", "杭州医学院检验医学院专业设置",
        "https://jyyxy.hmc.edu.cn/rcpy/zysz/",
        "学院官网列有医学检验技术、卫生检验与检疫和生物技术本科专业及体外诊断平台。",
        "公办医科本科；具有医学检验、卫生检疫、生物技术、药学与食品安全方向。",
    ),
    VerifiedProvincialKeySeed(
        "浙大城市学院", "浙江省", "杭州市", "https://www.hzcu.edu.cn/", "浙大城市学院本科专业设置",
        "https://www.hzcu.edu.cn/rcpy/bksjy/bkzy.htm",
        "学校官网本科专业表列有药学专业；教学建设页面同时确认其为省级一流本科专业。",
        "公办普通本科；具有药学、药物分析及生物医药方向。",
    ),
    VerifiedProvincialKeySeed(
        "浙江水利水电学院", "浙江省", "杭州市", "https://www.zjweu.edu.cn/", "浙江水利水电学院本科专业设置一览表",
        "https://jwc.zjweu.edu.cn/_upload/article/files/54/5c/0265c3ec4b3085b54658aec1b288/d9d31ef1-7a86-4675-a4ae-1526a79df4bd.pdf",
        "学校官网专业表列有环境生态工程和材料成型及控制工程本科专业。",
        "公办普通本科；具有环境生态、材料成型与水环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "浙江科技大学", "浙江省", "杭州市", "https://www.zust.edu.cn/", "浙江科技大学材料科学与工程专业介绍",
        "https://zsb.zust.edu.cn/wzxq/zs33",
        "招生官网介绍材料科学与工程本科专业，覆盖高分子、功能与生物基材料及材料检测。",
        "公办普通本科；具有材料、生物、化工、食品与环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "湖州学院", "浙江省", "湖州市", "https://www.zjhzu.edu.cn/", "湖州学院生物工程专业介绍",
        "https://smjkxy.zjhzu.edu.cn/2023/0215/c1910a16808/page.htm",
        "学院官网介绍生物工程本科专业及生物制药、食品、环保相关培养与实践方向。",
        "公办普通本科；具有生物工程、制药工程、材料化学与新能源材料方向。",
    ),
    VerifiedProvincialKeySeed(
        "湖州师范大学", "浙江省", "湖州市", "https://www.zjhu.edu.cn/", "湖州师范大学生命科学学院简介",
        "https://smkxxy.zjhu.edu.cn/6502/list.htm",
        "学院官网列有化学、生物工程、生物科学、制药工程和水产养殖等本科专业。",
        "公办师范本科；具有化学、生物、制药、水产与环境研究方向。",
    ),
    VerifiedProvincialKeySeed(
        "绍兴大学", "浙江省", "绍兴市", "https://www.usx.edu.cn/", "绍兴大学化学化工学院简介",
        "https://chem.usx.edu.cn/sjb/xygk/xyjj.htm",
        "学院官网列有应用化学、药学、高分子材料、新能源材料和科学教育等本科专业。",
        "公办普通本科；具有化学、药学、材料、生物与环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "绍兴理工学院", "浙江省", "绍兴市", "https://www.ypc.edu.cn/", "绍兴理工学院招生专业设置",
        "https://zsxx.zsit.edu.cn/",
        "学校招生官网设能源与材料化工、建筑与环境工程、医药与健康学院，并列有药学本科专业。",
        "公办普通本科；具有药学、材料化工与环境工程相关专业方向。",
    ),
    VerifiedProvincialKeySeed(
        "衢州学院", "浙江省", "衢州市", "https://www.qzc.edu.cn/", "衢州学院化学与材料工程学院简介",
        "https://hcxy.qzc.edu.cn/2025/0221/c3416a76367/page.htm",
        "学院官网列有化学工程、材料科学、高分子材料、环境工程和新能源材料五个本科专业。",
        "公办普通本科；具有化工、材料、环境与新能源材料方向。",
    ),
)


# 记录本轮未纳入的全部公办本科边界，避免后续批次重复判断。
ORDINARY_UNDERGRADUATE_BATCH_04_EXCLUSION_REASONS = {
    "上海外国语大学": "外语类院校，未发现符合本轮标准的生物、环境、化学、材料或检测本科专业证据。",
    "上海对外经贸大学": "财经外贸类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "上海戏剧学院": "艺术类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "上海政法学院": "政法类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "上海立信会计金融学院": "会计金融类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "上海财经大学": "财经类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "上海音乐学院": "艺术类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "华东政法大学": "政法类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "南京审计大学": "审计财经类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "南京特殊教育师范学院": "专业以特殊教育和康复教育为主，未发现符合本轮标准的生化环材本科专业证据。",
    "南京艺术学院": "艺术类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "中国美术学院": "艺术类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "浙江传媒学院": "传媒艺术类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "浙江外国语学院": "外语类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "浙江财经大学": "财经类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "浙江音乐学院": "艺术类院校，未发现符合本轮标准的生化环材或检测本科专业证据。",
    "温州理工学院": "现行本科专业目录未列出生物、环境、化学、材料或检测类专业，历史转设前专业不作为当前依据。",
    "浙江药科职业大学": "本科层次职业教育学校，不属于本轮普通公办本科范围。",
}


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把官网核验结果转为正式候选，并交给既有严格主校区 POI 流程。"""

    assert len(VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_04) == 43
    assert len({seed.name for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_04}) == 43
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
            tags=("高校", "普通公办本科", "官网专业证据", "普通本科第04批"),
        )
        for seed in VERIFIED_ORDINARY_UNDERGRADUATE_UNIVERSITIES_BATCH_04
    )


def main() -> None:
    """幂等创建第 04 批；重复执行返回原批次，不覆盖人工核验档案。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 普通公办本科生化环材核验第04批",
            source_scope=(
                "上海、江苏、浙江教育部2026高校底表中尚未进入正式库的公办普通本科；逐校核验生物、环境、"
                "化学、材料、医药、食品或检测方向，排除既有高校、职业本科及纯财经外语政法艺术院校。"
            ),
            source_url=MOE_2026_UNIVERSITY_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-ordinary-undergraduate-import",
        )
    print(
        f"普通公办本科第04批完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
