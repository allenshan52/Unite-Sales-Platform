"""导入省属重点本科第 04 批：保存豫鄂湘粤官方建设依据，并排队定位主校区。"""

from app.cli.import_verified_provincial_key_universities_batch_01 import (
    MOE_UNIVERSITY_DIRECTORY,
    VerifiedProvincialKeySeed,
)
from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates


HUBEI_PLAN_URL = "https://jyt.hubei.gov.cn/bmdt/gxhptlm/mtjj/201801/t20180126_439516.shtml"
HUNAN_PLAN_URL = "https://jyt.hunan.gov.cn/sjyt/xxgk/tzgg/201810/t20181026_5149482.html"
GUANGDONG_PLAN_URL = "https://czt.gd.gov.cn/attachment/0/417/417024/3250078.pdf"
GUANGDONG_2018_URL = "https://www.gd.gov.cn/gdywdt/bmdt/content/post_161638.html"


# 第 04 批仅纳入省级重点/一流/高水平建设范围内且具备目标专业的公办本科。
VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_04 = (
    # 河南：省政府明确的七所“双一流”创建高校全部具备目标方向。
    VerifiedProvincialKeySeed(
        "河南理工大学", "河南省", "焦作市", "https://www.hpu.edu.cn/", "河南理工大学学校简介",
        "https://www.hpu.edu.cn/xxgk/xxjj.htm",
        "官网明确学校为河南省双一流创建高校，材料、化学、环境生态和地球科学等学科进入 ESI 前1%。",
        "河南省双一流创建本科；具有材料、化学、环境、地质和安全检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "河南农业大学", "河南省", "郑州市", "https://www.henau.edu.cn/", "河南农业大学学校简介",
        "https://www.henau.edu.cn/gaikuang/xxjj.htm",
        "官网明确学校为河南省特色骨干大学和双一流创建高校，重点覆盖农业、生命科学、动物生物安全和食品。",
        "河南省双一流创建农业本科；具有农业、生命、食品和生物安全检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "河南科技大学", "河南省", "洛阳市", "https://www.haust.edu.cn/", "河南科技大学学校简介",
        "https://www.haust.edu.cn/xxgk/kdjj.htm",
        "官网明确学校为河南省双一流创建重点高校和高水平综合性大学，办学覆盖材料、化工、农业和医学。",
        "河南省双一流创建本科；具有材料、化学化工、农业、医学和生物检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "河南师范大学", "河南省", "新乡市", "https://www.htu.edu.cn/", "河南师范大学学校简介",
        "https://www.htu.edu.cn/9057/list.htm",
        "官网列有特色骨干和省重点学科，化学、材料、环境生态及植物动物科学进入 ESI 前1%。",
        "河南省双一流创建本科；具有化学、材料、环境和生命科学方向。",
    ),
    VerifiedProvincialKeySeed(
        "河南工业大学", "河南省", "郑州市", "https://www.haut.edu.cn/", "河南工业大学学校简介",
        "https://www.haut.edu.cn/xxgk/xxjj.htm",
        "官网明确学校为河南省特色骨干大学和双一流创建高校，食品、农业、化学、材料、生物和环境学科突出。",
        "河南省双一流创建本科；具有粮油食品、化学、材料、生物和环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "华北水利水电大学", "河南省", "郑州市", "https://www.ncwu.edu.cn/", "华北水利水电大学学校简介",
        "https://www.ncwu.edu.cn/xxgk/xxjj.htm",
        "官网明确学校为河南省特色骨干大学和双一流创建高校，环境生态学进入 ESI 前1%。",
        "河南省双一流创建本科；具有水环境、生态、应用化学和资源检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "河南中医药大学", "河南省", "郑州市", "https://hactcm.edu.cn/", "河南中医药大学学校简介",
        "https://hactcm.edu.cn/xxgk/xxjj.htm",
        "官网明确学校为河南省特色骨干大学和双一流创建高校，覆盖中药、药学、药理毒理和化学。",
        "河南省双一流创建医药本科；具有中药、药学、药理毒理和质量检测方向。",
    ),

    # 湖北：省教育厅双一流名单中的非既有公办本科，排除军队、艺术和纯财经院校。
    VerifiedProvincialKeySeed(
        "湖北大学", "湖北省", "武汉市", "https://www.hubu.edu.cn/", "湖北省双一流建设高校及学科名单",
        HUBEI_PLAN_URL,
        "省教育厅将学校列为国内一流大学建设高校，建设学科包括材料科学与化学、生物学。",
        "湖北省国内一流大学建设本科；具有材料、化学和生物方向。",
    ),
    VerifiedProvincialKeySeed(
        "武汉科技大学", "湖北省", "武汉市", "https://www.wust.edu.cn/", "湖北省双一流建设高校及学科名单",
        HUBEI_PLAN_URL,
        "省教育厅将学校列为国内一流大学建设高校，建设学科包括材料、冶金与矿业工程。",
        "湖北省国内一流大学建设本科；具有材料、冶金、矿产和环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "三峡大学", "湖北省", "宜昌市", "https://www.ctgu.edu.cn/", "湖北省双一流建设高校及学科名单",
        HUBEI_PLAN_URL,
        "省教育厅将学校列为国内一流大学建设高校，重点建设水利工程；学校同时设医学、生命和环境相关专业。",
        "湖北省国内一流大学建设本科；具有水环境、生命、医学和分析检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "长江大学", "湖北省", "荆州市", "https://www.yangtzeu.edu.cn/", "湖北省双一流建设高校及学科名单",
        HUBEI_PLAN_URL,
        "省教育厅将学校列为国内一流大学建设高校，建设学科包括作物学、地质资源和石油天然气工程。",
        "湖北省国内一流大学建设本科；具有农业、生命、地质、化学和环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "中南民族大学", "湖北省", "武汉市", "https://www.scuec.edu.cn/", "湖北省双一流建设高校及学科名单",
        HUBEI_PLAN_URL,
        "省教育厅将学校列为国内一流大学建设高校，建设学科明确包含化学和药学。",
        "湖北省国内一流大学建设本科；具有化学、药学、生物和材料方向。",
    ),
    VerifiedProvincialKeySeed(
        "武汉工程大学", "湖北省", "武汉市", "https://www.wit.edu.cn/", "湖北省双一流建设高校及学科名单",
        HUBEI_PLAN_URL,
        "省教育厅将学校列为国内一流学科建设高校，重点建设化工与矿业工程。",
        "湖北省国内一流学科建设本科；具有化学化工、材料、矿业和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "湖北中医药大学", "湖北省", "武汉市", "https://www.hbtcm.edu.cn/", "湖北省双一流建设高校及学科名单",
        HUBEI_PLAN_URL,
        "省教育厅将学校列为国内一流学科建设高校，重点建设中医学并覆盖中药、药学和医学检验。",
        "湖北省国内一流学科建设医药本科；具有中药、药学和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "湖北工业大学", "湖北省", "武汉市", "https://www.hbut.edu.cn/", "湖北省双一流建设高校及学科名单",
        HUBEI_PLAN_URL,
        "省教育厅将学校列为国内一流学科建设高校，重点建设轻工技术与工程，覆盖食品、生物、材料和环境。",
        "湖北省国内一流学科建设本科；具有食品、生物、材料、化学和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "武汉纺织大学", "湖北省", "武汉市", "https://www.wtu.edu.cn/", "湖北省双一流建设高校及学科名单",
        HUBEI_PLAN_URL,
        "省教育厅将学校列为国内一流学科建设高校，重点建设纺织科学与工程并覆盖材料、化学和环境方向。",
        "湖北省国内一流学科建设本科；具有纺织材料、化学和环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "武汉轻工大学", "湖北省", "武汉市", "https://www.whpu.edu.cn/", "湖北省双一流建设高校及学科名单",
        HUBEI_PLAN_URL,
        "省教育厅将学校列为国内一流学科建设高校，重点建设食品科学与工程。",
        "湖北省国内一流学科建设本科；具有食品安全、生物、粮油和质量检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "江汉大学", "湖北省", "武汉市", "https://www.jhun.edu.cn/", "湖北省双一流建设高校及学科名单",
        HUBEI_PLAN_URL,
        "省教育厅将学校列为国内一流学科建设高校，重点建设化学工程与技术。",
        "湖北省国内一流学科建设本科；具有化学化工、材料、环境和生命方向。",
    ),
    VerifiedProvincialKeySeed(
        "湖北师范大学", "湖北省", "黄石市", "https://www.hbnu.edu.cn/", "湖北省双一流建设高校及学科名单",
        HUBEI_PLAN_URL,
        "省教育厅将学校列为国内一流学科建设高校；学校设化学化工、生命科学及材料相关专业。",
        "湖北省国内一流学科建设本科；具有化学、材料、环境和生命方向。",
    ),
    VerifiedProvincialKeySeed(
        "湖北医药学院", "湖北省", "十堰市", "https://www.hbmu.edu.cn/", "湖北省双一流建设高校及学科名单",
        HUBEI_PLAN_URL,
        "省教育厅将学校列为国内一流学科建设高校，重点建设临床医学并覆盖药学和医学检验。",
        "湖北省国内一流学科建设医科本科；具有医学检验、药学和生物医学方向。",
    ),

    # 湖南：仅取国内一流大学/学科建设层次，应用特色院校留待后续普通本科批次。
    VerifiedProvincialKeySeed(
        "湖南农业大学", "湖南省", "长沙市", "https://www.hunau.edu.cn/", "湖南省双一流建设项目名单",
        HUNAN_PLAN_URL,
        "省教育厅将学校列为国内一流大学 A 类，建设学科包含作物学、园艺学、生物学、生态学和农业资源环境。",
        "湖南省国内一流大学建设本科；具有农业、生物、生态环境和食品检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "长沙理工大学", "湖南省", "长沙市", "https://www.csust.edu.cn/", "湖南省双一流建设项目名单",
        HUNAN_PLAN_URL,
        "省教育厅将学校列为国内一流大学 A 类；学校设材料、化学化工和环境相关专业。",
        "湖南省国内一流大学建设本科；具有材料、化学化工和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "中南林业科技大学", "湖南省", "长沙市", "https://www.csuft.edu.cn/", "湖南省双一流建设项目名单",
        HUNAN_PLAN_URL,
        "省教育厅将学校列为国内一流大学 B 类，培育学科包含生物学、生态学、林业工程和食品科学。",
        "湖南省国内一流大学建设本科；具有林业、生物、生态、食品和材料检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "湖南科技大学", "湖南省", "湘潭市", "https://www.hnust.edu.cn/", "湖南省双一流建设项目名单",
        HUNAN_PLAN_URL,
        "省教育厅将学校列为国内一流大学 B 类；学校设材料、化学化工、生命和资源环境相关专业。",
        "湖南省国内一流大学建设本科；具有材料、化学、生命、资源和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "湖南中医药大学", "湖南省", "长沙市", "https://www.hnucm.edu.cn/", "湖南省双一流建设项目名单",
        HUNAN_PLAN_URL,
        "省教育厅将学校列为国内一流大学 B 类，建设方向包含中医学、中西医结合和药学。",
        "湖南省国内一流大学建设医药本科；具有中药、药学、生物医学和质量检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "南华大学", "湖南省", "衡阳市", "https://www.usc.edu.cn/", "湖南省双一流建设项目名单",
        HUNAN_PLAN_URL,
        "省教育厅将学校列为国内一流大学 B 类，建设方向包含核科学、安全和基础医学。",
        "湖南省国内一流大学建设本科；具有核检测、环境安全、医学和药学方向。",
    ),
    VerifiedProvincialKeySeed(
        "湖南工业大学", "湖南省", "株洲市", "https://www.hut.edu.cn/", "湖南省双一流建设项目名单",
        HUNAN_PLAN_URL,
        "省教育厅将学校列为国内一流学科建设高校，培育学科包含材料科学与工程。",
        "湖南省国内一流学科建设本科；具有包装材料、化学和环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "吉首大学", "湖南省", "吉首市", "https://www.jsu.edu.cn/", "湖南省双一流建设项目名单",
        HUNAN_PLAN_URL,
        "省教育厅将学校列为国内一流学科建设高校；学校同时设生物资源、化学化工和药学相关方向。",
        "湖南省国内一流学科建设本科；具有生物、化学、药学和民族医药检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "湖南理工大学", "湖南省", "岳阳市", "https://www.hnist.edu.cn/", "湖南省双一流建设项目名单",
        HUNAN_PLAN_URL,
        "原湖南理工学院入选省国内一流学科建设高校并重点建设化学工程与技术；教育部于2026年批准更名为湖南理工大学。",
        "湖南省国内一流学科建设本科；具有化学化工、材料和环境方向。",
    ),

    # 广东：覆盖冲补强计划整体、重点学科、粤东西北振兴及相关特色公办本科。
    VerifiedProvincialKeySeed(
        "广东工业大学", "广东省", "广州市", "https://www.gdut.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列为高水平大学整体建设高校，重点覆盖材料、化学工程、环境和生物医药。",
        "广东省高水平大学建设本科；具有材料、化学化工、环境和生物医药方向。",
    ),
    VerifiedProvincialKeySeed(
        "南方医科大学", "广东省", "广州市", "https://www.smu.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列为高水平大学整体建设高校，医学、药学、公共卫生和生物医学方向突出。",
        "广东省高水平医科本科；具有医学检验、药学、公共卫生和生物医学方向。",
    ),
    VerifiedProvincialKeySeed(
        "深圳大学", "广东省", "深圳市", "https://www.szu.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列为高水平大学整体建设高校，相关方向覆盖医学、材料、化学、生物和环境。",
        "广东省高水平大学建设本科；具有医学、材料、化学、生物和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "汕头大学", "广东省", "汕头市", "https://www.stu.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列为高水平大学重点学科建设高校，优势覆盖化学材料、医学和海洋生物。",
        "广东省高水平重点学科本科；具有化学、材料、医学和海洋生物方向。",
    ),
    VerifiedProvincialKeySeed(
        "广州大学", "广东省", "广州市", "https://www.gzhu.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_2018_URL,
        "省政府公布学校进入高水平大学重点学科建设范围；学校设化学、材料、环境和生命相关方向。",
        "广东省高水平重点学科本科；具有化学、材料、环境和生命方向。",
    ),
    VerifiedProvincialKeySeed(
        "广东海洋大学", "广东省", "湛江市", "https://www.gdou.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列入粤东西北高校振兴计划，优势覆盖海洋、水产、食品、生物和生态环境。",
        "广东省粤东西北振兴本科；具有海洋、水产、食品、生物和生态环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "韩山师范学院", "广东省", "潮州市", "https://www.hstc.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列入粤东西北高校振兴计划，学校设化学、材料、食品和生物相关专业。",
        "广东省粤东西北振兴本科；具有化学、材料、食品和生物方向。",
    ),
    VerifiedProvincialKeySeed(
        "嘉应学院", "广东省", "梅州市", "https://www.jyu.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列入粤东西北高校振兴计划，学校设化学、环境、生命和医学相关专业。",
        "广东省粤东西北振兴本科；具有化学、环境、生命和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "广东医科大学", "广东省", "湛江市", "https://www.gdmu.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列入粤东西北高校振兴计划，重点覆盖临床、基础医学、公共卫生和药学。",
        "广东省高水平医科本科；具有医学检验、公共卫生、药学和生物医学方向。",
    ),
    VerifiedProvincialKeySeed(
        "岭南师范学院", "广东省", "湛江市", "https://www.lingnan.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列入粤东西北高校振兴计划，学校设化学化工、生命、食品和环境相关专业。",
        "广东省粤东西北振兴本科；具有化学、生命、食品和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "韶关学院", "广东省", "韶关市", "https://www.sgu.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列入粤东西北高校振兴计划，学校设化学、生物、食品和医学相关专业。",
        "广东省粤东西北振兴本科；具有化学、生物、食品和医学检验方向。",
    ),
    VerifiedProvincialKeySeed(
        "惠州学院", "广东省", "惠州市", "https://www.hzu.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列入粤东西北高校振兴计划，学校设化学、材料、生命和环境相关专业。",
        "广东省粤东西北振兴本科；具有化学、材料、生命和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "肇庆学院", "广东省", "肇庆市", "https://www.zqu.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列入粤东西北高校振兴计划，学校设环境、生命、食品和化学相关专业。",
        "广东省粤东西北振兴本科；具有环境、生命、食品和化学方向。",
    ),
    VerifiedProvincialKeySeed(
        "广东石油化工学院", "广东省", "茂名市", "https://www.gdupt.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列入粤东西北高校振兴计划，优势覆盖石油化工、材料和环境工程。",
        "广东省粤东西北振兴本科；具有石油化工、材料和环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "五邑大学", "广东省", "江门市", "https://www.wyu.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列入特色高校提升计划，学校设材料、化学工程、环境和生物相关专业。",
        "广东省特色建设本科；具有材料、化学化工、环境和生物方向。",
    ),
    VerifiedProvincialKeySeed(
        "仲恺农业工程学院", "广东省", "广州市", "https://www.zhku.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列入特色高校提升计划，优势覆盖农业、食品、生物和资源环境。",
        "广东省特色农业本科；具有农业、食品、生物和资源环境检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "广东药科大学", "广东省", "广州市", "https://www.gdpu.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列入特色高校提升计划，重点覆盖药学、中药、生物医药和公共卫生。",
        "广东省特色医药本科；具有药学、中药、生物医药和公共卫生检测方向。",
    ),
    VerifiedProvincialKeySeed(
        "广东技术师范大学", "广东省", "广州市", "https://www.gpnu.edu.cn/", "广东省冲补强计划建设名单",
        GUANGDONG_PLAN_URL,
        "省级资金名单将学校列入特色高校提升计划，学校设材料、化学化工和环境相关专业。",
        "广东省特色建设本科；具有材料、化学化工和环境方向。",
    ),
    VerifiedProvincialKeySeed(
        "东莞理工学院", "广东省", "东莞市", "https://www.dgut.edu.cn/", "广东省高水平大学建设说明",
        "https://www.gdjct.gd.gov.cn/swxsnew/xszg82/content/post_162287.html",
        "官方通报明确学校入选广东省高水平大学重点学科建设高校，相关方向覆盖材料、化工、环境和生物医药。",
        "广东省高水平重点学科本科；具有材料、化学化工、环境和生物医药方向。",
    ),
    VerifiedProvincialKeySeed(
        "佛山大学", "广东省", "佛山市", "https://www.fosu.edu.cn/", "佛山大学高水平理工科建设说明",
        "https://edu.gd.gov.cn/attachment/0/511/511776/4083757.pdf",
        "学校官方章程说明其入选首批广东省高水平理工科大学建设高校，办学覆盖材料、化学、环境、食品和医学。",
        "广东省高水平理工科本科；具有材料、化学、环境、食品和医学检测方向。",
    ),
)


def build_candidates() -> tuple[UniversityCandidate, ...]:
    """把第 04 批已核验种子转成正式候选，仅以“城市+校名”匹配主校区。"""

    assert len(VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_04) == 49
    assert len({seed.name for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_04}) == 49
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
            tags=("高校", "省属重点本科", "官网专业证据", "省属重点第04批"),
        )
        for seed in VERIFIED_PROVINCIAL_KEY_UNIVERSITIES_BATCH_04
    )


def main() -> None:
    """幂等创建豫鄂湘粤第 04 批，不覆盖重复项或人工核验结果。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 省属重点本科生化环材核验第04批",
            source_scope=(
                "河南、湖北、湖南、广东省级重点/双一流/高水平建设公办本科；结合省级官方名单与学校官网"
                "确认生物、环境、化学、材料、医药、食品农业或检测方向，排除既有、纯文财经、艺术、"
                "中外合作和非独立分校区。"
            ),
            source_url=MOE_UNIVERSITY_DIRECTORY,
            candidates=build_candidates(),
            actor_username="system-provincial-key-import",
        )
    print(
        f"省属重点本科第04批完成：候选 {batch.total_rows}，新增 {batch.created_rows}，"
        f"重复 {batch.duplicate_rows}，批次ID：{batch.id}"
    )


if __name__ == "__main__":
    main()
