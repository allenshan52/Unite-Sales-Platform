"use client";

/** 单位审核工作台：管理登录、筛选列表、按需地图、单位编辑删除与审核。 */

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Check, CircleAlert, Download, LogOut, MapPinned, Pencil, Plus, Save, Search, ShieldCheck, Trash2, X } from "lucide-react";

import { AdminOrganizationMap } from "@/components/admin-organization-map";
import {
  apiDownload,
  apiFetch,
  queryString,
  type CooperationLevel,
  type CustomerStatus,
  type EvidenceKind,
  type FilterOptions,
  type GeocodeStatus,
  type MapPoint,
  type Organization,
  type OrganizationCreateInput,
  type OrganizationPage,
  type OrganizationType,
  type OrganizationUpdateInput,
  type OpportunityStage,
  type ReviewStatus,
} from "@/lib/api";

type Filters = { search: string; type: string; customerStatus: string; reviewStatus: string; province: string; verifiedOnly: boolean };
type ContactEditForm = { draftKey: string; id: string | null; name: string; department: string; title: string; mobile: string; email: string; isPrimary: boolean; isActive: boolean; notes: string };
type SalesProjectEditForm = { draftKey: string; id: string | null; opportunityId: string; name: string; contractAmount: string; signedAt: string; projectDetail: string };
type OpportunityEditForm = { draftKey: string; id: string | null; title: string; stage: OpportunityStage; estimatedAmount: string; aiSummary: string; nextAction: string; nextActionAt: string };
type EvidenceCreateForm = { draftKey: string; evidenceKind: EvidenceKind; title: string; sourceUrl: string; publishedAt: string; excerpt: string };
type OrganizationEditForm = {
  name: string;
  organizationType: OrganizationType | "";
  industry: string;
  customerStatus: CustomerStatus;
  reviewStatus: ReviewStatus;
  inclusionReason: string;
  isSportsException: boolean;
  parentGroup: string;
  website: string;
  unifiedSocialCreditCode: string;
  recentFollowUpAt: string;
  recentFollowUpContent: string;
  followUpOwner: string;
  cooperationIntent: string;
  cooperationLevel: CooperationLevel | "";
  notes: string;
  contacts: ContactEditForm[];
  salesProjects: SalesProjectEditForm[];
  opportunities: OpportunityEditForm[];
  evidences: EvidenceCreateForm[];
  siteName: string;
  rawAddress: string;
  address: string;
  province: string;
  city: string;
  district: string;
  amapAdcode: string;
  geocodeStatus: GeocodeStatus;
  geocodeConfidence: string;
  longitude: string;
  latitude: string;
};

const emptyFilters: Filters = { search: "", type: "", customerStatus: "", reviewStatus: "", province: "", verifiedOnly: false };
const organizationPageSizeOptions = [10, 25, 50, 75, 100];
const geocodeStatuses: GeocodeStatus[] = ["待编码", "已定位", "低置信度", "待补地址"];
const cooperationLevels: CooperationLevel[] = ["一级", "二级", "三级"];
const opportunityStages: OpportunityStage[] = ["已识别", "资格确认", "方案/报价", "商务谈判", "已关闭失单"];
const evidenceKinds: EvidenceKind[] = ["官方名录", "院系/专业目录", "研究方向/实验室", "体育例外依据", "官方地址", "其他"];
// 新增单位必填项集中配置，后续业务调整时只需改这里和对应后端 schema。
const createFieldRequirements = { name: true, organizationType: true, province: true, city: true } as const;

/** 把可空文本统一转换为 API 使用的 null，避免保存只有空格的字段。 */
function optionalText(value: string): string | null {
  const normalized = value.trim();
  return normalized || null;
}

/** 把可空数字输入转换为 number/null；浏览器负责范围与数字格式校验。 */
function optionalNumber(value: string): number | null {
  return value.trim() ? Number(value) : null;
}

/** 把 API 时间转换成 datetime-local 接受的本地时间文本。 */
function localDateTimeValue(value: string | null): string {
  if (!value) return "";
  const date = new Date(value);
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

/** 为新建的表单子记录生成只在当前草稿使用的稳定 React key。 */
function draftKey(): string {
  return crypto.randomUUID();
}

/** 创建空联系人草稿，默认启用但不默认设为主要联系人。 */
function emptyContact(): ContactEditForm {
  return { draftKey: draftKey(), id: null, name: "", department: "", title: "", mobile: "", email: "", isPrimary: false, isActive: true, notes: "" };
}

/** 创建空成交项目草稿，成交金额由管理员明确填写。 */
function emptySalesProject(): SalesProjectEditForm {
  return { draftKey: draftKey(), id: null, opportunityId: "", name: "", contractAmount: "", signedAt: "", projectDetail: "" };
}

/** 创建空商机草稿，并使用最早推进阶段作为默认值。 */
function emptyOpportunity(): OpportunityEditForm {
  return { draftKey: draftKey(), id: null, title: "", stage: "已识别", estimatedAmount: "", aiSummary: "", nextAction: "", nextActionAt: "" };
}

/** 创建空来源证据草稿，只有管理员主动添加时才进入新增请求。 */
function emptyEvidence(): EvidenceCreateForm {
  return { draftKey: draftKey(), evidenceKind: "官方名录", title: "", sourceUrl: "", publishedAt: "", excerpt: "" };
}

/** 创建新增单位的隔离草稿；枚举使用安全默认值，业务文本和关联记录保持为空。 */
function emptyOrganizationForm(): OrganizationEditForm {
  return {
    name: "", organizationType: "", industry: "", customerStatus: "潜在客户", reviewStatus: "待核验",
    inclusionReason: "", isSportsException: false, parentGroup: "", website: "", unifiedSocialCreditCode: "",
    recentFollowUpAt: "", recentFollowUpContent: "", followUpOwner: "", cooperationIntent: "", cooperationLevel: "", notes: "",
    contacts: [], salesProjects: [], opportunities: [], evidences: [], siteName: "", rawAddress: "", address: "",
    province: "", city: "", district: "", amapAdcode: "", geocodeStatus: "待编码", geocodeConfidence: "", longitude: "", latitude: "",
  };
}

/** 不修改原数组地更新一条重复表单记录。 */
function updateAt<T>(items: T[], index: number, changes: Partial<T>): T[] {
  return items.map((item, itemIndex) => itemIndex === index ? { ...item, ...changes } : item);
}

/** 不修改原数组地移除一条重复表单记录。 */
function removeAt<T>(items: T[], index: number): T[] {
  return items.filter((_item, itemIndex) => itemIndex !== index);
}

/** 从完整单位档案创建隔离的表单状态，取消时不会污染列表数据。 */
function editFormFromOrganization(organization: Organization): OrganizationEditForm {
  const site = organization.sites.find((item) => item.is_primary) ?? organization.sites[0];
  return {
    name: organization.name,
    organizationType: organization.organization_type,
    industry: organization.industry ?? "",
    customerStatus: organization.customer_status,
    reviewStatus: organization.review_status,
    inclusionReason: organization.inclusion_reason ?? "",
    isSportsException: organization.is_sports_exception,
    parentGroup: organization.parent_group ?? "",
    website: organization.website ?? "",
    unifiedSocialCreditCode: organization.unified_social_credit_code ?? "",
    recentFollowUpAt: localDateTimeValue(organization.recent_follow_up_at),
    recentFollowUpContent: organization.recent_follow_up_content ?? "",
    followUpOwner: organization.follow_up_owner ?? "",
    cooperationIntent: organization.cooperation_intent ?? "",
    cooperationLevel: organization.cooperation_level ?? "",
    notes: organization.notes ?? "",
    contacts: (organization.contacts ?? []).map((contact) => ({
      draftKey: contact.id, id: contact.id, name: contact.name, department: contact.department ?? "", title: contact.title ?? "",
      mobile: contact.mobile ?? "", email: contact.email ?? "", isPrimary: contact.is_primary, isActive: contact.is_active, notes: contact.notes ?? "",
    })),
    salesProjects: (organization.sales_projects ?? []).map((project) => ({
      draftKey: project.id, id: project.id, opportunityId: project.opportunity_id ?? "", name: project.name,
      contractAmount: project.contract_amount, signedAt: project.signed_at ?? "", projectDetail: project.project_detail ?? "",
    })),
    opportunities: (organization.opportunities ?? []).map((opportunity) => ({
      draftKey: opportunity.id, id: opportunity.id, title: opportunity.title, stage: opportunity.stage,
      estimatedAmount: opportunity.estimated_amount ?? "", aiSummary: opportunity.ai_summary ?? "",
      nextAction: opportunity.next_action ?? "", nextActionAt: opportunity.next_action_at ?? "",
    })),
    evidences: [],
    siteName: site?.site_name ?? "",
    rawAddress: site?.raw_address ?? "",
    address: site?.address ?? "",
    province: site?.province ?? "",
    city: site?.city ?? "",
    district: site?.district ?? "",
    amapAdcode: site?.amap_adcode ?? "",
    geocodeStatus: site?.geocode_status ?? "待编码",
    geocodeConfidence: site?.geocode_confidence?.toString() ?? "",
    longitude: site?.longitude?.toString() ?? "",
    latitude: site?.latitude?.toString() ?? "",
  };
}

/** 将表单状态整理成后端 PATCH 合同，只提交单位主档和主地点字段。 */
function updatePayloadFromForm(form: OrganizationEditForm): OrganizationUpdateInput {
  if (!form.organizationType) throw new Error("请选择单位类型");
  return {
    name: form.name.trim(),
    organization_type: form.organizationType,
    industry: optionalText(form.industry),
    customer_status: form.customerStatus,
    review_status: form.reviewStatus,
    inclusion_reason: optionalText(form.inclusionReason),
    is_sports_exception: form.isSportsException,
    parent_group: optionalText(form.parentGroup),
    website: optionalText(form.website),
    unified_social_credit_code: optionalText(form.unifiedSocialCreditCode),
    recent_follow_up_at: form.recentFollowUpAt ? new Date(form.recentFollowUpAt).toISOString() : null,
    recent_follow_up_content: optionalText(form.recentFollowUpContent),
    follow_up_owner: optionalText(form.followUpOwner),
    cooperation_intent: optionalText(form.cooperationIntent),
    cooperation_level: form.cooperationLevel || null,
    notes: optionalText(form.notes),
    contacts: form.contacts.map((contact) => ({
      id: contact.id, name: contact.name.trim(), department: optionalText(contact.department), title: optionalText(contact.title),
      mobile: optionalText(contact.mobile), email: optionalText(contact.email), is_primary: contact.isPrimary,
      is_active: contact.isActive, notes: optionalText(contact.notes),
    })),
    sales_projects: form.salesProjects.map((project) => ({
      id: project.id, opportunity_id: optionalText(project.opportunityId), name: project.name.trim(),
      contract_amount: Number(project.contractAmount), signed_at: optionalText(project.signedAt), project_detail: optionalText(project.projectDetail),
    })),
    opportunities: form.opportunities.map((opportunity) => ({
      id: opportunity.id, title: opportunity.title.trim(), stage: opportunity.stage,
      estimated_amount: optionalNumber(opportunity.estimatedAmount), ai_summary: optionalText(opportunity.aiSummary),
      next_action: optionalText(opportunity.nextAction), next_action_at: optionalText(opportunity.nextActionAt),
    })),
    primary_site: {
      site_name: optionalText(form.siteName),
      raw_address: optionalText(form.rawAddress),
      address: optionalText(form.address),
      province: optionalText(form.province),
      city: optionalText(form.city),
      district: optionalText(form.district),
      amap_adcode: optionalText(form.amapAdcode),
      geocode_status: form.geocodeStatus,
      geocode_confidence: optionalNumber(form.geocodeConfidence),
      longitude: optionalNumber(form.longitude),
      latitude: optionalNumber(form.latitude),
    },
  };
}

/** 将新增草稿整理为单次 POST 合同，关联记录均以新记录形式提交。 */
function createPayloadFromForm(form: OrganizationEditForm): OrganizationCreateInput {
  return {
    ...updatePayloadFromForm(form),
    evidences: form.evidences.map((evidence) => ({
      evidence_kind: evidence.evidenceKind,
      title: evidence.title.trim(),
      source_url: evidence.sourceUrl.trim(),
      published_at: optionalText(evidence.publishedAt),
      excerpt: optionalText(evidence.excerpt),
    })),
  };
}

/** 登录表单：凭据只提交给同源 FastAPI，成功后由 HTTP-only cookie 维持会话。 */
function LoginPanel({ onLoggedIn }: { onLoggedIn: (username: string) => void }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  /** 提交管理员凭据并把已认证用户名交给工作台。 */
  async function submitLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const user = await apiFetch<{ username: string }>("/auth/login", { method: "POST", body: JSON.stringify({ username, password }) });
      onLoggedIn(user.username);
    } catch (loginError) {
      setError(loginError instanceof Error ? loginError.message : "登录失败");
    } finally {
      setSubmitting(false);
    }
  }

  return <main className="admin-login-page"><form className="admin-login-card" onSubmit={submitLogin}><div className="admin-kicker"><ShieldCheck size={16} />内部数据审核</div><h1>目标单位数据库</h1><p>登录后核查来源、地址、筛选条件和商业机会。联系人仅在权限范围内显示。</p><label>管理员账号<input value={username} onChange={(event) => setUsername(event.target.value)} autoComplete="username" required /></label><label>管理员密码<input value={password} onChange={(event) => setPassword(event.target.value)} type="password" autoComplete="current-password" required /></label>{error ? <p className="admin-form-error"><CircleAlert size={15} />{error}</p> : null}<button className="admin-primary" disabled={submitting}>{submitting ? "正在验证…" : "进入审核工作台"}</button></form></main>;
}

/** 单位详情抽屉：统一展示列表和地图选中的档案，并保留快速审核动作。 */
function OrganizationDrawer({ organization, onClose, onReview }: { organization: Organization | null; onClose: () => void; onReview: (status: ReviewStatus) => void }) {
  if (!organization) return null;
  const primarySite = organization.sites.find((site) => site.is_primary) ?? organization.sites[0];
  return <aside className="organization-drawer" aria-label="单位详情"><div className="drawer-head"><div><span>{organization.organization_type}</span><h2>{organization.name}</h2></div><button onClick={onClose} aria-label="关闭详情"><X size={18} /></button></div><div className="drawer-status"><b className={`status-${organization.customer_status}`}>{organization.customer_status}</b><b className={`review-${organization.review_status}`}>{organization.review_status}</b>{organization.is_sports_exception ? <b className="sports-tag">体育例外</b> : null}</div><section><h3>地点与地图</h3><p>{[primarySite?.province, primarySite?.city, primarySite?.district, primarySite?.address].filter(Boolean).join(" · ") || "尚待补充地址"}</p><p className="muted">{primarySite?.geocode_status ?? "待编码"}{primarySite?.longitude ? " · 已有地图坐标" : " · 不展示地图 pin"}</p></section><section><h3>纳入依据</h3>{organization.evidences.length ? <ul className="evidence-list">{organization.evidences.map((evidence) => <li key={evidence.id}><a href={evidence.source_url} target="_blank" rel="noreferrer">{evidence.title}</a><span>{evidence.evidence_kind} · {evidence.retrieved_at}</span></li>)}</ul> : <p className="muted">尚未附来源依据。</p>}</section><section><h3>业务信息</h3><p>{organization.inclusion_reason || "暂无纳入说明"}</p><p className="muted">所属集团：{organization.parent_group || "未填写"}</p><p className="muted">行业：{organization.industry || "未填写"}</p></section><div className="drawer-actions"><button className="admin-secondary" onClick={() => onReview("已核验")}><Check size={15} />标记已核验</button><button className="admin-danger" onClick={() => onReview("不纳入")}>标记不纳入</button></div></aside>;
}

/** 单位新增/编辑对话框：复用同一字段布局，并按模式生成独立 API 合同。 */
function OrganizationFormDialog({ organization, options, onCancel, onCreate, onSave }: { organization: Organization | null; options: FilterOptions | null; onCancel: () => void; onCreate?: (payload: OrganizationCreateInput) => Promise<void>; onSave?: (payload: OrganizationUpdateInput) => Promise<void> }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [form, setForm] = useState(() => organization ? editFormFromOrganization(organization) : emptyOrganizationForm());
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => { if (dialog?.open) dialog.close(); };
  }, []);

  /** 更新一个草稿字段，不改写传入的单位对象。 */
  function updateField<K extends keyof OrganizationEditForm>(field: K, value: OrganizationEditForm[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  /** 移除商机时同时清空成交项目中的旧关联，避免提交悬空外键。 */
  function removeOpportunity(index: number) {
    setForm((current) => {
      const removedId = current.opportunities[index]?.id;
      return {
        ...current,
        opportunities: removeAt(current.opportunities, index),
        salesProjects: removedId
          ? current.salesProjects.map((project) => project.opportunityId === removedId ? { ...project, opportunityId: "" } : project)
          : current.salesProjects,
      };
    });
  }

  /** 校验浏览器表单后按模式新增或修改；失败时保留草稿就地修正。 */
  async function submitOrganization(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      if (organization) {
        if (!onSave) throw new Error("缺少修改处理程序");
        await onSave(updatePayloadFromForm(form));
      } else {
        if (!onCreate) throw new Error("缺少新增处理程序");
        await onCreate(createPayloadFromForm(form));
      }
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : "保存失败，请检查字段后重试");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <dialog ref={dialogRef} className="organization-edit-dialog" aria-labelledby="organization-form-title" onCancel={(event) => { event.preventDefault(); if (!submitting) onCancel(); }}>
      <form onSubmit={submitOrganization}>
        <header>
          <div><h2 id="organization-form-title">{organization ? "修改单位档案" : "添加单位"}</h2><p>{organization?.name ?? "填写单位档案与可选关联记录"}</p></div>
          <button type="button" onClick={onCancel} disabled={submitting} aria-label={organization ? "取消修改" : "取消添加"}><X size={19} /></button>
        </header>
        <div className="organization-edit-body">
          <section>
            <h3>基本信息与合作进展</h3>
            <div className="organization-edit-grid">
              <label className="field-wide"><span>单位名称{!organization && createFieldRequirements.name ? " *" : ""}</span><input value={form.name} onChange={(event) => updateField("name", event.target.value)} minLength={2} maxLength={255} required autoFocus /></label>
              <label><span>单位类型{!organization && createFieldRequirements.organizationType ? " *" : ""}</span><select value={form.organizationType} required={!organization && createFieldRequirements.organizationType} onChange={(event) => { const organizationType = event.target.value as OrganizationType | ""; setForm((current) => ({ ...current, organizationType, isSportsException: organizationType === "高校" ? current.isSportsException : false })); }}><option value="">请选择单位类型</option>{options?.organization_types.map((item) => <option key={item}>{item}</option>)}</select></label>
              <label><span>行业</span><input value={form.industry} onChange={(event) => updateField("industry", event.target.value)} maxLength={120} /></label>
              <label><span>客户状态</span><select value={form.customerStatus} onChange={(event) => updateField("customerStatus", event.target.value as CustomerStatus)}>{options?.customer_statuses.map((item) => <option key={item}>{item}</option>)}</select></label>
              <label><span>审核状态</span><select value={form.reviewStatus} onChange={(event) => updateField("reviewStatus", event.target.value as ReviewStatus)}>{options?.review_statuses.map((item) => <option key={item}>{item}</option>)}</select></label>
              <label><span>所属集团</span><input value={form.parentGroup} onChange={(event) => updateField("parentGroup", event.target.value)} maxLength={255} /></label>
              <label><span>统一社会信用代码</span><input value={form.unifiedSocialCreditCode} onChange={(event) => updateField("unifiedSocialCreditCode", event.target.value)} minLength={18} maxLength={18} /></label>
              <label className="field-wide"><span>网站</span><input type="url" value={form.website} onChange={(event) => updateField("website", event.target.value)} maxLength={500} placeholder="https://" /></label>
              <label className="field-check"><input type="checkbox" checked={form.isSportsException} disabled={form.organizationType !== "高校"} onChange={(event) => updateField("isSportsException", event.target.checked)} /><span>体育类高校例外</span></label>
              <label><span>最近跟进时间</span><input type="datetime-local" value={form.recentFollowUpAt} onChange={(event) => updateField("recentFollowUpAt", event.target.value)} /></label>
              <label><span>跟进负责人</span><input value={form.followUpOwner} onChange={(event) => updateField("followUpOwner", event.target.value)} maxLength={120} /></label>
              <label><span>合作等级</span><select value={form.cooperationLevel} onChange={(event) => updateField("cooperationLevel", event.target.value as CooperationLevel | "")}><option value="">未设置</option>{cooperationLevels.map((level) => <option key={level}>{level}</option>)}</select></label>
              <label className="field-wide"><span>合作意向</span><input value={form.cooperationIntent} onChange={(event) => updateField("cooperationIntent", event.target.value)} maxLength={500} /></label>
              <label className="field-wide"><span>最近跟进内容</span><textarea value={form.recentFollowUpContent} onChange={(event) => updateField("recentFollowUpContent", event.target.value)} maxLength={5000} rows={3} /></label>
              <label className="field-wide"><span>纳入说明</span><textarea value={form.inclusionReason} onChange={(event) => updateField("inclusionReason", event.target.value)} maxLength={2000} rows={3} /></label>
              <label className="field-wide"><span>管理员备注</span><textarea value={form.notes} onChange={(event) => updateField("notes", event.target.value)} maxLength={5000} rows={3} /></label>
            </div>
          </section>

          {!organization ? <section className="organization-create-evidence">
            <div className="organization-edit-section-head"><h3>公开来源 / 证据</h3><button type="button" onClick={() => updateField("evidences", [...form.evidences, emptyEvidence()])}><Plus size={14} />新增证据</button></div>
            {form.evidences.length === 0 ? <p className="organization-edit-empty">可稍后补充官方名录、专业目录或地址来源。</p> : null}
            <div className="organization-edit-records">
              {form.evidences.map((evidence, index) => (
                <article className="organization-edit-record" key={evidence.draftKey}>
                  <div className="organization-edit-record-head"><strong>来源证据 {index + 1}</strong><button type="button" onClick={() => updateField("evidences", removeAt(form.evidences, index))}><Trash2 size={13} />移除</button></div>
                  <div className="organization-edit-grid">
                    <label><span>证据类型</span><select value={evidence.evidenceKind} onChange={(event) => updateField("evidences", updateAt(form.evidences, index, { evidenceKind: event.target.value as EvidenceKind }))}>{evidenceKinds.map((kind) => <option key={kind}>{kind}</option>)}</select></label>
                    <label><span>发布日期</span><input type="date" value={evidence.publishedAt} onChange={(event) => updateField("evidences", updateAt(form.evidences, index, { publishedAt: event.target.value }))} /></label>
                    <label className="field-wide"><span>来源标题</span><input value={evidence.title} onChange={(event) => updateField("evidences", updateAt(form.evidences, index, { title: event.target.value }))} minLength={2} maxLength={255} required /></label>
                    <label className="field-wide"><span>来源网址</span><input type="url" value={evidence.sourceUrl} onChange={(event) => updateField("evidences", updateAt(form.evidences, index, { sourceUrl: event.target.value }))} placeholder="https://" required /></label>
                    <label className="field-wide"><span>来源摘要</span><textarea value={evidence.excerpt} onChange={(event) => updateField("evidences", updateAt(form.evidences, index, { excerpt: event.target.value }))} maxLength={2000} rows={2} /></label>
                  </div>
                </article>
              ))}
            </div>
          </section> : null}

          <section>
            <div className="organization-edit-section-head"><h3>联系人</h3><button type="button" onClick={() => updateField("contacts", [...form.contacts, emptyContact()])}><Plus size={14} />新增联系人</button></div>
            {form.contacts.length === 0 ? <p className="organization-edit-empty">尚未添加联系人。</p> : null}
            <div className="organization-edit-records">
              {form.contacts.map((contact, index) => (
                <article className="organization-edit-record" key={contact.draftKey}>
                  <div className="organization-edit-record-head"><strong>联系人 {index + 1}</strong><button type="button" onClick={() => updateField("contacts", removeAt(form.contacts, index))}><Trash2 size={13} />移除</button></div>
                  <div className="organization-edit-grid">
                    <label><span>姓名</span><input value={contact.name} onChange={(event) => updateField("contacts", updateAt(form.contacts, index, { name: event.target.value }))} maxLength={120} required /></label>
                    <label><span>部门</span><input value={contact.department} onChange={(event) => updateField("contacts", updateAt(form.contacts, index, { department: event.target.value }))} maxLength={160} /></label>
                    <label><span>职位</span><input value={contact.title} onChange={(event) => updateField("contacts", updateAt(form.contacts, index, { title: event.target.value }))} maxLength={160} /></label>
                    <label><span>手机</span><input type="tel" value={contact.mobile} onChange={(event) => updateField("contacts", updateAt(form.contacts, index, { mobile: event.target.value }))} maxLength={40} /></label>
                    <label><span>邮箱</span><input type="email" value={contact.email} onChange={(event) => updateField("contacts", updateAt(form.contacts, index, { email: event.target.value }))} maxLength={254} /></label>
                    <label className="field-check"><input type="checkbox" checked={contact.isPrimary} onChange={(event) => updateField("contacts", updateAt(form.contacts, index, { isPrimary: event.target.checked }))} /><span>主要联系人</span></label>
                    <label className="field-check"><input type="checkbox" checked={contact.isActive} onChange={(event) => updateField("contacts", updateAt(form.contacts, index, { isActive: event.target.checked }))} /><span>联系人有效</span></label>
                    <label className="field-wide"><span>联系人备注</span><textarea value={contact.notes} onChange={(event) => updateField("contacts", updateAt(form.contacts, index, { notes: event.target.value }))} maxLength={5000} rows={2} /></label>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section>
            <div className="organization-edit-section-head"><h3>成交项目</h3><button type="button" onClick={() => updateField("salesProjects", [...form.salesProjects, emptySalesProject()])}><Plus size={14} />新增成交项目</button></div>
            {form.salesProjects.length === 0 ? <p className="organization-edit-empty">尚未添加成交项目。</p> : null}
            <div className="organization-edit-records">
              {form.salesProjects.map((project, index) => (
                <article className="organization-edit-record" key={project.draftKey}>
                  <div className="organization-edit-record-head"><strong>成交项目 {index + 1}</strong><button type="button" onClick={() => updateField("salesProjects", removeAt(form.salesProjects, index))}><Trash2 size={13} />移除</button></div>
                  <div className="organization-edit-grid">
                    <label><span>项目名称</span><input value={project.name} onChange={(event) => updateField("salesProjects", updateAt(form.salesProjects, index, { name: event.target.value }))} maxLength={255} required /></label>
                    <label><span>实际成交金额（元）</span><input type="number" min={0} step="0.01" value={project.contractAmount} onChange={(event) => updateField("salesProjects", updateAt(form.salesProjects, index, { contractAmount: event.target.value }))} required /></label>
                    <label><span>签约日期</span><input type="date" value={project.signedAt} onChange={(event) => updateField("salesProjects", updateAt(form.salesProjects, index, { signedAt: event.target.value }))} /></label>
                    <label><span>关联商机</span><select value={project.opportunityId} onChange={(event) => updateField("salesProjects", updateAt(form.salesProjects, index, { opportunityId: event.target.value }))}><option value="">不关联</option>{form.opportunities.filter((item) => item.id).map((item) => <option value={item.id ?? ""} key={item.draftKey}>{item.title || "未命名商机"}</option>)}</select></label>
                    <label className="field-wide"><span>项目详情</span><textarea value={project.projectDetail} onChange={(event) => updateField("salesProjects", updateAt(form.salesProjects, index, { projectDetail: event.target.value }))} maxLength={5000} rows={3} /></label>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section>
            <div className="organization-edit-section-head"><h3>商机</h3><button type="button" onClick={() => updateField("opportunities", [...form.opportunities, emptyOpportunity()])}><Plus size={14} />新增商机</button></div>
            {form.opportunities.length === 0 ? <p className="organization-edit-empty">尚未添加商机。</p> : null}
            <div className="organization-edit-records">
              {form.opportunities.map((opportunity, index) => (
                <article className="organization-edit-record" key={opportunity.draftKey}>
                  <div className="organization-edit-record-head"><strong>商机 {index + 1}</strong><button type="button" onClick={() => removeOpportunity(index)}><Trash2 size={13} />移除</button></div>
                  <div className="organization-edit-grid">
                    <label><span>商机名称</span><input value={opportunity.title} onChange={(event) => updateField("opportunities", updateAt(form.opportunities, index, { title: event.target.value }))} maxLength={255} required /></label>
                    <label><span>商机阶段</span><select value={opportunity.stage} onChange={(event) => updateField("opportunities", updateAt(form.opportunities, index, { stage: event.target.value as OpportunityStage }))}>{opportunityStages.map((stage) => <option key={stage}>{stage}</option>)}</select></label>
                    <label><span>预计金额（元）</span><input type="number" min={0} step="0.01" value={opportunity.estimatedAmount} onChange={(event) => updateField("opportunities", updateAt(form.opportunities, index, { estimatedAmount: event.target.value }))} /></label>
                    <label><span>下一步动作日期</span><input type="date" value={opportunity.nextActionAt} onChange={(event) => updateField("opportunities", updateAt(form.opportunities, index, { nextActionAt: event.target.value }))} /></label>
                    <label className="field-wide"><span>商机摘要</span><textarea value={opportunity.aiSummary} onChange={(event) => updateField("opportunities", updateAt(form.opportunities, index, { aiSummary: event.target.value }))} maxLength={5000} rows={3} /></label>
                    <label className="field-wide"><span>下一步动作</span><textarea value={opportunity.nextAction} onChange={(event) => updateField("opportunities", updateAt(form.opportunities, index, { nextAction: event.target.value }))} maxLength={2000} rows={2} /></label>
                  </div>
                </article>
              ))}
            </div>
          </section>

          <section>
            <h3>主地点与定位</h3>
            <div className="organization-edit-grid">
              <label><span>地点名称</span><input value={form.siteName} onChange={(event) => updateField("siteName", event.target.value)} maxLength={160} /></label>
              <label><span>高德区域编码</span><input value={form.amapAdcode} onChange={(event) => updateField("amapAdcode", event.target.value)} maxLength={12} /></label>
              <label><span>省份{!organization && createFieldRequirements.province ? " *" : ""}</span><input value={form.province} onChange={(event) => updateField("province", event.target.value)} maxLength={60} required={!organization && createFieldRequirements.province} /></label>
              <label><span>城市{!organization && createFieldRequirements.city ? " *" : ""}</span><input value={form.city} onChange={(event) => updateField("city", event.target.value)} maxLength={60} required={!organization && createFieldRequirements.city} /></label>
              <label><span>区县</span><input value={form.district} onChange={(event) => updateField("district", event.target.value)} maxLength={80} /></label>
              <label><span>定位状态</span><select value={form.geocodeStatus} onChange={(event) => updateField("geocodeStatus", event.target.value as GeocodeStatus)}>{geocodeStatuses.map((item) => <option key={item}>{item}</option>)}</select></label>
              <label className="field-wide"><span>原始地址</span><input value={form.rawAddress} onChange={(event) => updateField("rawAddress", event.target.value)} maxLength={500} /></label>
              <label className="field-wide"><span>标准地址</span><input value={form.address} onChange={(event) => updateField("address", event.target.value)} maxLength={500} /></label>
              <label><span>经度</span><input type="number" min={73} max={136} step="any" value={form.longitude} onChange={(event) => updateField("longitude", event.target.value)} /></label>
              <label><span>纬度</span><input type="number" min={3} max={54} step="any" value={form.latitude} onChange={(event) => updateField("latitude", event.target.value)} /></label>
              <label><span>定位置信度</span><input type="number" min={0} max={100} step={1} value={form.geocodeConfidence} onChange={(event) => updateField("geocodeConfidence", event.target.value)} /></label>
            </div>
          </section>
        </div>
        {error ? <p className="organization-dialog-error"><CircleAlert size={16} />{error}</p> : null}
        <footer>
          <button type="button" className="organization-dialog-cancel" onClick={onCancel} disabled={submitting}>取消</button>
          <button className="organization-dialog-save" disabled={submitting}><Save size={16} />{submitting ? "正在保存…" : organization ? "保存修改" : "添加单位"}</button>
        </footer>
      </form>
    </dialog>
  );
}

/** 删除确认对话框：默认聚焦取消，只有再次确认才调用永久删除 API。 */
function DeleteConfirmationDialog({ organization, onCancel, onConfirm }: { organization: Organization; onCancel: () => void; onConfirm: () => Promise<void> }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => { if (dialog?.open) dialog.close(); };
  }, []);

  /** 执行不可逆删除；失败时保留对话框与错误说明供管理员重试。 */
  async function confirmDelete(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setDeleting(true);
    setError(null);
    try {
      await onConfirm();
    } catch (deleteError) {
      setError(deleteError instanceof Error ? deleteError.message : "删除失败，请稍后重试");
      setDeleting(false);
    }
  }

  return <dialog ref={dialogRef} className="organization-delete-dialog" aria-labelledby="organization-delete-title" onCancel={(event) => { event.preventDefault(); if (!deleting) onCancel(); }}><form onSubmit={confirmDelete}><div className="delete-dialog-icon"><Trash2 size={22} /></div><h2 id="organization-delete-title">确认删除单位？</h2><p>“{organization.name}”将从数据库永久删除，关联地点、证据、联系人和商机也会一并移除。此操作无法撤销。</p>{error ? <p className="organization-dialog-error"><CircleAlert size={16} />{error}</p> : null}<footer><button type="button" className="organization-dialog-cancel" onClick={onCancel} disabled={deleting} autoFocus>取消</button><button className="organization-dialog-delete" disabled={deleting}><Trash2 size={16} />{deleting ? "正在删除…" : "确认删除"}</button></footer></form></dialog>;
}

/** 主审核页面：列表始终为主视图，地图仅在管理员主动打开时加载。 */
export function AdminOrganizationWorkspace() {
  const [username, setUsername] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(emptyFilters);
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [options, setOptions] = useState<FilterOptions | null>(null);
  const [page, setPage] = useState<OrganizationPage | null>(null);
  const [points, setPoints] = useState<MapPoint[]>([]);
  const [showMap, setShowMap] = useState(false);
  const [selected, setSelected] = useState<Organization | null>(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<Organization | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Organization | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const workspaceAbortRef = useRef<AbortController | null>(null);

  const listFilters = useMemo(() => ({ search: debouncedSearch || undefined, types: filters.type || undefined, customer_statuses: filters.customerStatus || undefined, review_statuses: filters.reviewStatus || undefined, province: filters.province || undefined }), [debouncedSearch, filters.customerStatus, filters.province, filters.reviewStatus, filters.type]);
  const mapFilters = useMemo(() => ({ ...listFilters, verified_only: filters.verifiedOnly }), [filters.verifiedOnly, listFilters]);
  const effectivePageSize = showMap ? 10 : pageSize;
  const totalPages = Math.max(1, Math.ceil((page?.total ?? 0) / effectivePageSize));

  useEffect(() => { apiFetch<{ username: string }>("/auth/me").then((user) => setUsername(user.username)).catch(() => setUsername(null)).finally(() => setLoading(false)); }, []);
  /** 搜索词短暂停顿后再查询，减少键入过程中的重复数据库请求。 */
  useEffect(() => {
    const timeoutId = window.setTimeout(() => setDebouncedSearch(filters.search.trim()), 250);
    return () => window.clearTimeout(timeoutId);
  }, [filters.search]);

  /** 后台枚举与省份选项只读取一次；失败不阻断列表和地图的独立请求。 */
  useEffect(() => {
    if (!username || options) return;
    const controller = new AbortController();
    void apiFetch<FilterOptions>("/organizations/filters", { signal: controller.signal })
      .then((nextOptions) => setOptions(nextOptions))
      .catch((requestError: unknown) => {
        if (!(requestError instanceof DOMException && requestError.name === "AbortError")) {
          setError(requestError instanceof Error ? requestError.message : "筛选选项加载失败");
        }
      });
    return () => controller.abort();
  }, [options, username]);

  /** 成功提示只悬浮两秒，并在新提示或组件卸载时清理旧计时器。 */
  useEffect(() => {
    if (!notice) return;
    const timeoutId = window.setTimeout(() => setNotice(null), 2000);
    return () => window.clearTimeout(timeoutId);
  }, [notice]);

  /** 同步列表和可选点位；取消旧请求且隔离地图辅助请求失败。 */
  const loadWorkspace = useCallback(async () => {
    if (!username) return;
    workspaceAbortRef.current?.abort();
    const controller = new AbortController();
    workspaceAbortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const listQuery = queryString({ ...listFilters, page: String(currentPage), page_size: String(effectivePageSize) });
      const pointsRequest = showMap ? apiFetch<MapPoint[]>(`/organizations/map-points${queryString(mapFilters)}`, { signal: controller.signal }) : Promise.resolve([]);
      const [pageResult, pointsResult] = await Promise.allSettled([
        apiFetch<OrganizationPage>(`/organizations${listQuery}`, { signal: controller.signal }),
        pointsRequest,
      ]);
      if (controller.signal.aborted) return;
      if (pageResult.status === "rejected") throw pageResult.reason;
      setPage(pageResult.value);
      if (pointsResult.status === "fulfilled") setPoints(pointsResult.value);
      else if (showMap) setError(pointsResult.reason instanceof Error ? pointsResult.reason.message : "地图点位加载失败");
    } catch (requestError) {
      if (!(requestError instanceof DOMException && requestError.name === "AbortError")) {
        setError(requestError instanceof Error ? requestError.message : "无法加载审核数据");
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [currentPage, effectivePageSize, listFilters, mapFilters, showMap, username]);

  useEffect(() => {
    // 延后到当前提交结束再同步外部数据，避免 effect 内同步触发级联渲染。
    const timeoutId = window.setTimeout(() => void loadWorkspace(), 0);
    return () => window.clearTimeout(timeoutId);
  }, [loadWorkspace]);

  useEffect(() => () => workspaceAbortRef.current?.abort(), []);

  /** 原子更新筛选并重置页码，避免用旧页码发出一次无效请求。 */
  function updateFilters(changes: Partial<Filters>) {
    setLoading(true);
    setError(null);
    setCurrentPage(1);
    setFilters((current) => ({ ...current, ...changes }));
  }

  /** 在分页事件中先标记加载态，数据 effect 只负责网络同步。 */
  function changePage(nextPage: number) {
    setLoading(true);
    setError(null);
    setCurrentPage(nextPage);
  }

  /** 从列表或地图读取完整档案，供详情抽屉展示。 */
  const selectOrganization = useCallback(async (id: string) => {
    try {
      setSelected(await apiFetch<Organization>(`/organizations/${id}`));
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "无法读取单位详情");
    }
  }, []);

  /** 提交审核状态；排除时先收集必填原因。 */
  const reviewOrganization = useCallback(async (status: ReviewStatus) => {
    if (!selected) return;
    const note = status === "不纳入" ? window.prompt("请填写不纳入原因（必填）：") : undefined;
    if (status === "不纳入" && !note) return;
    try {
      const updated = await apiFetch<Organization>(`/organizations/${selected.id}/review`, { method: "POST", body: JSON.stringify({ review_status: status, note }) });
      setSelected(updated);
      setNotice(`已更新“${updated.name}”的审核状态`);
      void loadWorkspace();
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : "审核操作失败");
    }
  }, [loadWorkspace, selected]);

  /** 保存编辑表单并刷新当前页；失败交给对话框就地显示。 */
  const saveOrganization = useCallback(async (payload: OrganizationUpdateInput) => {
    if (!editing) return;
    const updated = await apiFetch<Organization>(`/organizations/${editing.id}`, { method: "PATCH", body: JSON.stringify(payload) });
    setSelected((current) => current?.id === updated.id ? updated : current);
    setNotice(`已保存“${updated.name}”`);
    await loadWorkspace();
    setEditing(null);
  }, [editing, loadWorkspace]);

  /** 原子新增完整单位档案，成功后关闭表单、提示两秒并刷新当前列表。 */
  const createOrganization = useCallback(async (payload: OrganizationCreateInput) => {
    const created = await apiFetch<Organization>("/organizations", { method: "POST", body: JSON.stringify(payload) });
    setNotice(`已添加“${created.name}”`);
    await loadWorkspace();
    setCreating(false);
  }, [loadWorkspace]);

  /** 永久删除确认目标，并在最后一条被删时回到上一页。 */
  const deleteOrganization = useCallback(async () => {
    if (!deleteTarget) return;
    await apiFetch<void>(`/organizations/${deleteTarget.id}`, { method: "DELETE" });
    const deletedName = deleteTarget.name;
    setDeleteTarget(null);
    setSelected((current) => current?.id === deleteTarget.id ? null : current);
    setNotice(`已删除“${deletedName}”`);
    if ((page?.items.length ?? 0) === 1 && currentPage > 1) setCurrentPage((value) => value - 1);
    else await loadWorkspace();
  }, [currentPage, deleteTarget, loadWorkspace, page?.items.length]);

  /** 导出当前列表筛选结果，不把仅作用于地图 pin 的开关带入文件。 */
  const exportCurrentFilters = useCallback(async () => {
    setExporting(true);
    setError(null);
    try {
      await apiDownload(`/organizations/export${queryString(listFilters)}`, "优纳特单位候选.xlsx");
    } catch (exportError) {
      setError(exportError instanceof Error ? exportError.message : "无法导出单位数据");
    } finally {
      setExporting(false);
    }
  }, [listFilters]);

  /** 切换地图视图；保留当前分页批次，关闭时立即释放点位数据。 */
  function toggleMap() {
    setLoading(true);
    setError(null);
    if (showMap) {
      setPoints([]);
    }
    setShowMap(!showMap);
  }

  /** 清除服务端会话并回到登录页。 */
  async function logout() {
    await apiFetch<void>("/auth/logout", { method: "POST" });
    setUsername(null);
    setSelected(null);
  }

  if (loading && username === null) return <main className="admin-loading">正在确认管理员会话…</main>;
  if (!username) return <LoginPanel onLoggedIn={setUsername} />;

  return (
    <main className="organization-admin">
      <header className="organization-admin-header"><div><h1>全国目标单位</h1></div><div className="admin-user"><span>{username}</span><button onClick={() => void exportCurrentFilters()} disabled={exporting}><Download size={15} />{exporting ? "正在导出" : "导出当前筛选"}</button><button onClick={() => void logout()}><LogOut size={15} />退出</button></div></header>
      <section className="organization-filter-bar"><label><Search size={15} /><input placeholder="搜索单位名称" value={filters.search} onChange={(event) => updateFilters({ search: event.target.value })} /></label><select value={filters.type} onChange={(event) => updateFilters({ type: event.target.value })}><option value="">全部单位类型</option>{options?.organization_types.map((item) => <option key={item}>{item}</option>)}</select><select value={filters.customerStatus} onChange={(event) => updateFilters({ customerStatus: event.target.value })}><option value="">全部客户状态</option>{options?.customer_statuses.map((item) => <option key={item}>{item}</option>)}</select><select value={filters.reviewStatus} onChange={(event) => updateFilters({ reviewStatus: event.target.value })}><option value="">全部审核状态</option>{options?.review_statuses.map((item) => <option key={item}>{item}</option>)}</select><select value={filters.province} onChange={(event) => updateFilters({ province: event.target.value })}><option value="">全部省份</option>{options?.provinces.map((item) => <option key={item}>{item}</option>)}</select></section>
      {notice ? <p className="admin-page-notice"><Check size={16} />{notice}</p> : null}
      {error ? <p className="admin-page-error"><CircleAlert size={16} />{error}</p> : null}
      <section className={`organization-workbench ${showMap ? "map-visible" : "map-hidden"}`}>
        <div className="organization-list-card">
          <div className="card-title"><div><span>核验队列</span><h2>{page?.total.toLocaleString("zh-CN") ?? "—"} 条单位记录</h2></div><div className="card-title-actions"><button className="organization-create-button" onClick={() => setCreating(true)}><Plus size={15} />添加单位</button><button className="map-visibility-button" onClick={toggleMap}>{showMap ? <X size={15} /> : <MapPinned size={15} />}{showMap ? "关闭地图" : "显示地图"}</button></div></div>
          <div className="organization-table" role="table" aria-busy={loading}>
            <div className="organization-row organization-row-head" role="row"><div className="organization-row-main"><span role="columnheader">单位</span><span role="columnheader">类型 / 客户</span><span role="columnheader">省市区</span><span role="columnheader">地址 / 坐标</span><span role="columnheader">审核</span></div>{!showMap ? <span className="organization-actions-head" role="columnheader">操作</span> : null}</div>
            {page?.items.map((organization) => { const site = organization.sites.find((item) => item.is_primary) ?? organization.sites[0]; return <div className={`organization-row ${selected?.id === organization.id ? "selected" : ""}`} role="row" key={organization.id}><button className="organization-row-main organization-row-select" onClick={() => void selectOrganization(organization.id)} aria-label={`查看${organization.name}详情`}><strong role="cell">{organization.name}{organization.is_sports_exception ? <small>体育例外</small> : null}</strong><span role="cell">{organization.organization_type}<em>{organization.customer_status}</em></span><span role="cell">{[site?.province, site?.city, site?.district].filter(Boolean).join(" · ") || "未补齐"}</span><span role="cell">{site?.geocode_status ?? "待编码"}<em>{site?.address ? "地址已录入" : "待补地址"}</em></span><span role="cell" className={`review-${organization.review_status}`}>{organization.review_status}</span></button>{!showMap ? <div className="organization-row-actions" role="cell"><button className="organization-edit-action" onClick={() => setEditing(organization)}><Pencil size={14} />修改</button><button className="organization-delete-action" onClick={() => setDeleteTarget(organization)}><Trash2 size={14} />删除</button></div> : null}</div>; })}
          </div>
          {!loading && page?.items.length === 0 ? <div className="organization-empty"><MapPinned size={21} />暂无匹配单位。首次导入官方名单后会在此逐条核验。</div> : null}
          {page ? <nav className="organization-pagination" aria-label="单位列表分页"><span>第 {currentPage} / {totalPages} 页 · 共 {page.total.toLocaleString("zh-CN")} 条</span><div>{!showMap ? <label className="organization-page-size">每页<select aria-label="每页显示单位数" value={pageSize} onChange={(event) => { setLoading(true); setError(null); setCurrentPage(1); setPageSize(Number(event.target.value)); }}>{organizationPageSizeOptions.map((size) => <option key={size} value={size}>{size} 条</option>)}</select></label> : null}<button type="button" onClick={() => changePage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>上一页</button><button type="button" onClick={() => changePage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages}>下一页</button></div></nav> : null}
        </div>
        {showMap ? <div className="organization-map-card"><div className="card-title"><div><span>可信地址点位</span><h2>缩放聚合地图</h2></div><label className="verified-toggle verified-toggle-map"><input type="checkbox" checked={filters.verifiedOnly} onChange={(event) => updateFilters({ verifiedOnly: event.target.checked })} />仅已核验地图 pin</label></div><AdminOrganizationMap points={points} selectedId={selected?.id ?? null} onSelectPoint={(point) => void selectOrganization(point.id)} /></div> : null}
      </section>
      <OrganizationDrawer organization={selected} onClose={() => setSelected(null)} onReview={(status) => void reviewOrganization(status)} />
      {creating ? <OrganizationFormDialog organization={null} options={options} onCancel={() => setCreating(false)} onCreate={createOrganization} /> : null}
      {editing ? <OrganizationFormDialog key={editing.id} organization={editing} options={options} onCancel={() => setEditing(null)} onSave={saveOrganization} /> : null}
      {deleteTarget ? <DeleteConfirmationDialog key={deleteTarget.id} organization={deleteTarget} onCancel={() => setDeleteTarget(null)} onConfirm={deleteOrganization} /> : null}
    </main>
  );
}
