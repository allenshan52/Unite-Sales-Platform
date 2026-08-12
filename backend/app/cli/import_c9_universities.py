"""C9 高校首批导入：用九所高校的官方化学/材料证据验证真实名单入库与筛选流程。"""

from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates

MOE_HIGHER_EDUCATION_DIRECTORY = "https://www.moe.gov.cn/jyb_xxgk/s5743/s5744/A03/"

C9_UNIVERSITIES = (
    UniversityCandidate(
        name="北京大学",
        website="https://www.pku.edu.cn/",
        province="北京市",
        city="北京市",
        district="海淀区",
        address="北京市海淀区颐和园路5号",
        evidence_title="北京大学化学与分子工程学院：学院简介",
        evidence_url="https://www.chem.pku.edu.cn/xygk/xyjj/index.htm",
        evidence_excerpt="学院设有化学生物学系、高分子科学与工程系、应用化学系及多个化学研究所。",
    ),
    UniversityCandidate(
        name="清华大学",
        website="https://www.tsinghua.edu.cn/",
        province="北京市",
        city="北京市",
        district="海淀区",
        address="北京市海淀区清华大学化学系何添楼",
        evidence_title="清华大学化学系：化学系介绍",
        evidence_url="https://www.chem.tsinghua.edu.cn/info/1012/1021.htm",
        evidence_excerpt="化学系设有无机、有机、分析、物理、高分子等研究所及材料化学、化学生物学等交叉学科。",
    ),
    UniversityCandidate(
        name="复旦大学",
        website="https://www.fudan.edu.cn/",
        province="上海市",
        city="上海市",
        district="杨浦区",
        address="上海市杨浦区邯郸路220号",
        evidence_title="复旦大学化学系（官方站）",
        evidence_url="https://chemistry.fudan.edu.cn/",
        evidence_excerpt="化学系公开展示无机化学、有机化学、物理化学、分析化学及化学生物学等学科团队。",
    ),
    UniversityCandidate(
        name="上海交通大学",
        website="https://www.sjtu.edu.cn/",
        province="上海市",
        city="上海市",
        district="闵行区",
        address="上海市闵行区东川路800号",
        evidence_title="上海交通大学化学化工学院：学院简介",
        evidence_url="https://scce.sjtu.edu.cn/ddscce.html",
        evidence_excerpt="学院前身为交通大学化学系，设有化学、化工相关教学与研究平台。",
    ),
    UniversityCandidate(
        name="南京大学",
        website="https://www.nju.edu.cn/",
        province="江苏省",
        city="南京市",
        district="栖霞区",
        address="江苏省南京市栖霞区仙林大道163号",
        evidence_title="南京大学化学化工学院：学院简介",
        evidence_url="https://chem.nju.edu.cn/d7/56/c12554a251734/page.htm",
        evidence_excerpt="学院化学学科为一级学科国家重点学科，化学与化学工程与技术入选双一流建设学科。",
    ),
    UniversityCandidate(
        name="浙江大学",
        website="https://www.zju.edu.cn/",
        province="浙江省",
        city="杭州市",
        district="西湖区",
        address="浙江省杭州市西湖区余杭塘路866号",
        evidence_title="浙江大学化学系（官方院系介绍）",
        evidence_url="https://atc.zju.edu.cn/about/detail-29.html",
        evidence_excerpt="浙江大学化学系是面向国际科学前沿和国家战略需求开展化学人才培养与科学研究的平台。",
    ),
    UniversityCandidate(
        name="中国科学技术大学",
        website="https://www.ustc.edu.cn/",
        province="安徽省",
        city="合肥市",
        district="蜀山区",
        address="安徽省合肥市蜀山区金寨路96号",
        evidence_title="中国科学技术大学化学与材料科学学院培养方案",
        evidence_url="https://catalog.ustc.edu.cn/program/206",
        evidence_excerpt="学院包括化学系、材料科学与工程系、高分子科学与工程系，并开展化学与材料相关研究。",
    ),
    UniversityCandidate(
        name="哈尔滨工业大学",
        website="https://www.hit.edu.cn/",
        province="黑龙江省",
        city="哈尔滨市",
        district="南岗区",
        address="黑龙江省哈尔滨市南岗区西大直街92号",
        evidence_title="哈尔滨工业大学化工与化学学院（官方站）",
        evidence_url="https://chemeng.hit.edu.cn/",
        evidence_excerpt="学院开展化工与化学人才培养和科研，并公开列示化学国家级实验教学示范中心。",
    ),
    UniversityCandidate(
        name="西安交通大学",
        website="https://www.xjtu.edu.cn/",
        province="陕西省",
        city="西安市",
        district="碑林区",
        address="陕西省西安市碑林区咸宁西路28号",
        evidence_title="西安交通大学化学学院：院系介绍",
        evidence_url="https://www.xjtu.edu.cn/xynr.jsp?urltype=tree.TreeTempUrl&wbtreeid=2072",
        evidence_excerpt="化学学院下设应用化学系、化学系、大学化学部和化学实验教学中心，并建设材料与化学科研平台。",
    ),
)


def main() -> None:
    """创建 C9 首批导入批次并输出数量，便于在 Docker 中安全、重复地执行。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 C9高校化学/材料筛选验证",
            source_scope="C9九所高校；高校官方化学/材料相关院系证据；用于首批真实导入与筛选验证。",
            source_url=MOE_HIGHER_EDUCATION_DIRECTORY,
            candidates=C9_UNIVERSITIES,
            actor_username="system-import",
        )
    print(f"导入批次完成：新增 {batch.created_rows} 条，重复 {batch.duplicate_rows} 条，批次 ID：{batch.id}")


if __name__ == "__main__":
    main()
