"""高校官网取证首批入库：将已逐校核验的非 C9 高校写入正式单位并交给高德编码队列。"""

from app.database import SessionLocal
from app.services.imports import UniversityCandidate, import_university_candidates

# 必须与教育部底表批次的 source_url 一致，才能安全回写对应 import_row。
MOE_HIGHER_EDUCATION_DIRECTORY = "https://www.moe.gov.cn/jyb_xxgk/s5743/s5744/202606/t20260618_1441074.html"

VERIFIED_UNIVERSITIES = (
    UniversityCandidate(
        name="北京化工大学",
        website="https://www.buct.edu.cn/",
        province="北京市",
        city="北京市",
        district="朝阳区",
        address="北京市朝阳区北三环东路15号",
        evidence_title="北京化工大学化学工程学院：学院概况",
        evidence_url="https://chem.buct.edu.cn/xyjj/list.htm",
        evidence_excerpt="学院设有化学工程与技术、环境科学与工程博士点，并设化学工程与工艺、环境工程、能源化学工程等本科专业。",
        tags=("高校", "官网专业证据", "化学", "环境", "首批逐校核验"),
    ),
    UniversityCandidate(
        name="华东理工大学",
        website="https://www.ecust.edu.cn/",
        province="上海市",
        city="上海市",
        district="徐汇区",
        address="上海市徐汇区梅陇路130号",
        evidence_title="华东理工大学化学与分子工程学院：院史简介",
        evidence_url="https://chem.ecust.edu.cn/xyzc/list.htm",
        evidence_excerpt="学院下设化学系、精细化工系及应用化学、工业催化等研究所，并建设先进功能材料重点实验室和分析测试中心。",
        tags=("高校", "官网专业证据", "化学", "材料", "首批逐校核验"),
    ),
    UniversityCandidate(
        name="四川大学",
        website="https://www.scu.edu.cn/",
        province="四川省",
        city="成都市",
        district="武侯区",
        address="四川省成都市武侯区一环路南一段24号",
        evidence_title="四川大学化学学院：学院简介",
        evidence_url="https://chem.scu.edu.cn/xygk/xyjj.htm",
        evidence_excerpt="学院化学学科覆盖无机、分析、有机、物理、高分子化学与物理及化学生物学等方向，并建设绿色化学与技术等科研平台。",
        tags=("高校", "官网专业证据", "化学", "材料", "生物", "首批逐校核验"),
    ),
    UniversityCandidate(
        name="华东师范大学",
        website="https://www.ecnu.edu.cn/",
        province="上海市",
        city="上海市",
        district="普陀区",
        address="上海市普陀区中山北路3663号",
        evidence_title="华东师范大学化学与分子工程学院：学院简介",
        evidence_url="https://chem.ecnu.edu.cn/26569/list.htm",
        evidence_excerpt="学院拥有化学一级学科博士点，涵盖无机、分析、有机、物理、高分子化学和物理等方向，并建有化学相关重点实验室。",
        tags=("高校", "官网专业证据", "化学", "材料", "首批逐校核验"),
    ),
)


def main() -> None:
    """创建首批逐校官网取证批次；重复运行不覆盖正式档案，并回写教育部底表关联。"""

    with SessionLocal() as db:
        batch = import_university_candidates(
            db,
            batch_name="2026-08 高校官网专业证据核验第01批",
            source_scope="教育部 2026 年普通高校底表中的非 C9 高校；逐校使用学校官网院系/专业页面核验后入库。",
            source_url=MOE_HIGHER_EDUCATION_DIRECTORY,
            candidates=VERIFIED_UNIVERSITIES,
            actor_username="system-university-evidence",
        )
    print(f"高校官网取证第01批完成：批次累计新增 {batch.created_rows} 条，累计重复 {batch.duplicate_rows} 条，批次 ID：{batch.id}")


if __name__ == "__main__":
    main()
