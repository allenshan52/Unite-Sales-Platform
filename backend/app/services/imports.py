"""名单导入服务：把可追溯候选批量写入 PostgreSQL，并保留原始行和重复判定。"""

from dataclasses import asdict, dataclass
from typing import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AuditLog, CustomerStatus, EvidenceKind, GeocodeStatus, ImportBatch, ImportRow, Organization, OrganizationEvidence, OrganizationSite, OrganizationType, ReviewStatus
from app.services.organizations import normalize_name


@dataclass(frozen=True)
class UniversityCandidate:
    """高校候选的最小可追溯输入；地址和专业证据均来自公开的官方页面。"""

    name: str
    website: str
    province: str
    city: str
    district: str | None
    address: str
    evidence_title: str
    evidence_url: str
    evidence_excerpt: str
    evidence_kind: EvidenceKind = EvidenceKind.department
    inclusion_reason: str = "高校官网公开的生物、环境、化学或材料相关院系、专业或科研方向依据，符合目标单位筛选规则。"
    tags: tuple[str, ...] = ("高校", "官网专业证据")
    is_sports_exception: bool = False


@dataclass(frozen=True)
class OfficialUniversityDirectoryRow:
    """教育部普通高校目录的一行原始数据；它是筛选底表，不等同于已纳入的目标单位。"""

    sequence: int
    name: str
    institution_code: str
    supervising_department: str
    locality: str
    education_level: str
    remark: str


def is_sports_higher_education(row: OfficialUniversityDirectoryRow) -> bool:
    """只将名称明确为体育高校的目录行送入体育例外取证队列，避免把普通院校的体育专业误纳入。"""

    return "体育" in row.name and row.name.endswith(("大学", "学院", "职业学院", "职业技术学院"))


def university_directory_screening_status(row: OfficialUniversityDirectoryRow) -> str:
    """为底表记录标注下一步取证路径；没有官方专业证据时不创建正式 organization。"""

    if is_sports_higher_education(row):
        return "待体育例外证据"
    return "待生环化材专业证据"


def _link_pending_directory_rows(
    db: Session,
    *,
    normalized_name: str,
    organization: Organization,
    directory_source_url: str | None,
) -> None:
    """将已核验高校回写至同一教育部底表行，令审核后台能显示从底表到正式档案的去向。"""

    if not directory_source_url:
        return
    pending_rows = db.scalars(
        select(ImportRow)
        .join(ImportBatch)
        .where(ImportBatch.source_url == directory_source_url)
        .where(ImportRow.normalized_name == normalized_name)
        .where(ImportRow.organization_id.is_(None))
    ).all()
    for row in pending_rows:
        row.organization_id = organization.id
        row.processing_status = "已纳入正式单位（待核验/待编码）"


def import_university_candidates(
    db: Session,
    *,
    batch_name: str,
    source_scope: str,
    source_url: str | None,
    candidates: Iterable[UniversityCandidate],
    actor_username: str,
) -> ImportBatch:
    """导入符合高校筛选规则的候选，重复时只记录批次行而不修改已有正式档案。"""

    candidate_list = list(candidates)
    existing_batch = db.scalar(select(ImportBatch).where(ImportBatch.name == batch_name))
    if existing_batch:
        # 重跑同一取证批次时仅补回教育部底表关联，不重复创建批次行或覆盖人工档案。
        existing_batch.source_url = source_url
        for candidate in candidate_list:
            organization = db.scalar(select(Organization).where(Organization.normalized_name == normalize_name(candidate.name)))
            if organization:
                _link_pending_directory_rows(
                    db,
                    normalized_name=organization.normalized_name,
                    organization=organization,
                    directory_source_url=source_url,
                )
        db.commit()
        # commit 会使 ORM 属性过期；刷新后 CLI 可在会话关闭后安全输出既有批次统计。
        db.refresh(existing_batch)
        return existing_batch

    batch = ImportBatch(name=batch_name, source_scope=source_scope, source_url=source_url, total_rows=len(candidate_list))
    db.add(batch)
    db.flush()

    for candidate in candidate_list:
        normalized_name = normalize_name(candidate.name)
        existing = db.scalar(select(Organization).where(Organization.normalized_name == normalized_name))
        raw_payload = asdict(candidate)
        if existing:
            db.add(
                ImportRow(
                    batch_id=batch.id,
                    raw_payload=raw_payload,
                    normalized_name=normalized_name,
                    processing_status="重复候选（未覆盖）",
                    organization_id=existing.id,
                )
            )
            _link_pending_directory_rows(
                db,
                normalized_name=normalized_name,
                organization=existing,
                directory_source_url=source_url,
            )
            batch.duplicate_rows += 1
            continue

        organization = Organization(
            name=candidate.name,
            normalized_name=normalized_name,
            organization_type=OrganizationType.university,
            industry="高校科研与检测",
            customer_status=CustomerStatus.potential,
            review_status=ReviewStatus.pending,
            inclusion_reason=candidate.inclusion_reason,
            is_sports_exception=candidate.is_sports_exception,
            website=candidate.website,
            attributes={"tags": list(candidate.tags), "collection_scope": source_scope},
        )
        organization.sites = [
            OrganizationSite(
                site_name="主校区/官方地址",
                raw_address=candidate.address,
                address=candidate.address,
                province=candidate.province,
                city=candidate.city,
                district=candidate.district,
                geocode_status=GeocodeStatus.pending,
                is_primary=True,
            )
        ]
        organization.evidences = [
            OrganizationEvidence(
                evidence_kind=candidate.evidence_kind,
                title=candidate.evidence_title,
                source_url=candidate.evidence_url,
                excerpt=candidate.evidence_excerpt,
            )
        ]
        db.add(organization)
        db.flush()
        db.add(
            ImportRow(
                batch_id=batch.id,
                raw_payload=raw_payload,
                normalized_name=normalized_name,
                processing_status="已创建，待核验/待编码",
                organization_id=organization.id,
            )
        )
        _link_pending_directory_rows(
            db,
            normalized_name=normalized_name,
            organization=organization,
            directory_source_url=source_url,
        )
        db.add(AuditLog(organization_id=organization.id, actor_username=actor_username, action="批次导入单位", detail={"批次": batch_name, "证据": candidate.evidence_url}))
        batch.created_rows += 1

    db.commit()
    db.refresh(batch)
    return batch


def import_moe_university_directory(
    db: Session,
    *,
    batch_name: str,
    source_scope: str,
    source_url: str,
    rows: Iterable[OfficialUniversityDirectoryRow],
) -> ImportBatch:
    """将教育部普通高校底表写入导入队列，供后续逐校取证筛选且不以校名猜测替代证据。"""

    directory_rows = list(rows)
    existing_batch = db.scalar(select(ImportBatch).where(ImportBatch.name == batch_name))
    if existing_batch:
        return existing_batch

    batch = ImportBatch(
        name=batch_name,
        source_scope=source_scope,
        source_url=source_url,
        total_rows=len(directory_rows),
        notes="本批次仅为教育部普通高校筛选底表。高校需补充官方生物、环境、化学或材料专业/院系证据后，才会进入正式单位档案；体育高校需补充体育例外依据。",
    )
    db.add(batch)
    db.flush()

    existing_names = set(db.scalars(select(Organization.normalized_name)).all())
    sports_candidates = 0
    duplicate_rows = 0
    import_rows: list[ImportRow] = []
    for row in directory_rows:
        normalized_name = normalize_name(row.name)
        screening_status = university_directory_screening_status(row)
        if screening_status == "待体育例外证据":
            sports_candidates += 1

        processing_status = screening_status
        if normalized_name in existing_names:
            processing_status = "已有正式单位（不覆盖）"
            duplicate_rows += 1

        import_rows.append(
            ImportRow(
                batch_id=batch.id,
                raw_payload={
                    "序号": row.sequence,
                    "学校名称": row.name,
                    "学校标识码": row.institution_code,
                    "主管部门": row.supervising_department,
                    "所在地": row.locality,
                    "办学层次": row.education_level,
                    "备注": row.remark,
                    "初筛状态": screening_status,
                    "采集来源": source_url,
                },
                normalized_name=normalized_name,
                processing_status=processing_status,
            )
        )

    db.add_all(import_rows)
    batch.duplicate_rows = duplicate_rows
    batch.notes = f"{batch.notes} 体育例外待取证 {sports_candidates} 条；已有正式单位 {duplicate_rows} 条。"
    db.commit()
    db.refresh(batch)
    return batch
