"use client";

/** 销售人员聚合工作台：分页管理人员，并在同一档案内维护分级覆盖范围和活动。 */

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Check, CircleAlert, Pencil, Plus, Save, Search, Trash2, X } from "lucide-react";

import {
  apiFetch,
  queryString,
  type SalesActivityType,
  type SalesCoverageLevel,
  type SalespersonProfile,
} from "@/lib/api";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useLatestRequest } from "@/hooks/use-latest-request";
import { canonicalSalesProvince, salesCoverageLevels, salesProvinces, salesRegionDescription, salesRegions } from "@/lib/sales-coverage";

type SalespersonListItem = {
  id: string;
  employee_code: string;
  display_name: string;
  color: string;
  coverage_scopes: string[];
  coverage_scope_total: number;
  actual_sales_amount: string;
  visit_count: number;
  demonstration_count: number;
  marketing_event_count: number;
  is_active: boolean;
};
type SalespersonPage = { items: SalespersonListItem[]; total: number; page: number; page_size: number };
type AdminDataOption = { value: string; label: string };
type CoverageDraft = { draftKey: string; id: string | null; scopeLevel: SalesCoverageLevel; scopeName: string; province: string; city: string; amapAdcode: string };
type ActivityDraft = { draftKey: string; id: string | null; organizationId: string; organizationName: string; activityType: SalesActivityType; occurredAt: string; province: string; city: string; amapAdcode: string; notes: string };
type ProfileForm = {
  employeeCode: string;
  displayName: string;
  color: string;
  centerLongitude: string;
  centerLatitude: string;
  isActive: boolean;
  coverageScopes: CoverageDraft[];
  activities: ActivityDraft[];
};

const pageSizeOptions = [10, 25, 50, 75, 100];
const activityTypes: SalesActivityType[] = ["拜访", "演示", "市场活动"];
const currencyFormatter = new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 2 });

/** 生成仅用于前端列表键的草稿 ID，不进入 API。 */
function draftKey(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

/** 把 ISO 时间转换为浏览器 datetime-local 值。 */
function localDateTimeValue(value: string): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

/** 创建一个默认从市级开始填写的空覆盖范围草稿。 */
function emptyCoverageScope(): CoverageDraft {
  return { draftKey: draftKey(), id: null, scopeLevel: "市", scopeName: "", province: "", city: "", amapAdcode: "" };
}

/** 切换层级时清空失效字段，避免旧城市数据混入省级、大区或全国范围。 */
function coverageLevelChanges(scopeLevel: SalesCoverageLevel): Partial<CoverageDraft> {
  return { scopeLevel, scopeName: scopeLevel === "全国" ? "全国" : "", province: "", city: "", amapAdcode: "" };
}

/** 创建一个空销售活动草稿。 */
function emptyActivity(): ActivityDraft {
  return { draftKey: draftKey(), id: null, organizationId: "", organizationName: "", activityType: "拜访", occurredAt: "", province: "", city: "", amapAdcode: "", notes: "" };
}

/** 从空白默认值或服务端完整档案创建隔离表单。 */
function initialForm(profile: SalespersonProfile | null): ProfileForm {
  if (!profile) {
    return { employeeCode: "", displayName: "", color: "#2878B5", centerLongitude: "116.4074", centerLatitude: "39.9042", isActive: true, coverageScopes: [], activities: [] };
  }
  return {
    employeeCode: profile.employee_code,
    displayName: profile.display_name,
    color: profile.color,
    centerLongitude: String(profile.coverage_center_longitude),
    centerLatitude: String(profile.coverage_center_latitude),
    isActive: profile.is_active,
    coverageScopes: profile.coverage_scopes.map((item) => ({ draftKey: draftKey(), id: item.id, scopeLevel: item.scope_level, scopeName: item.scope_name, province: canonicalSalesProvince(item.province), city: item.city ?? "", amapAdcode: item.amap_adcode ?? "" })),
    activities: profile.activities.map((item) => ({ draftKey: draftKey(), id: item.id, organizationId: item.organization_id ?? "", organizationName: item.organization_name ?? "", activityType: item.activity_type, occurredAt: localDateTimeValue(item.occurred_at), province: item.province, city: item.city, amapAdcode: item.amap_adcode, notes: item.notes ?? "" })),
  };
}

/** 不改变原数组地更新指定草稿，避免表单子记录之间共享引用。 */
function updateAt<T>(items: T[], index: number, changes: Partial<T>): T[] {
  return items.map((item, itemIndex) => itemIndex === index ? { ...item, ...changes } : item);
}

/** 把销售人员表单转换为聚合 API 所需的 snake_case JSON。 */
function profilePayload(form: ProfileForm): Record<string, unknown> {
  return {
    employee_code: form.employeeCode.trim(),
    display_name: form.displayName.trim(),
    color: form.color,
    coverage_center_longitude: Number(form.centerLongitude),
    coverage_center_latitude: Number(form.centerLatitude),
    is_active: form.isActive,
    coverage_scopes: form.coverageScopes.map((item) => ({ id: item.id, scope_level: item.scopeLevel, scope_name: item.scopeName.trim(), province: item.province.trim() || null, city: item.city.trim() || null, amap_adcode: item.amapAdcode.trim() || null })),
    activities: form.activities.map((item) => ({ id: item.id, organization_id: item.organizationId || null, activity_type: item.activityType, occurred_at: new Date(item.occurredAt).toISOString(), province: item.province.trim(), city: item.city.trim(), amap_adcode: item.amapAdcode.trim(), notes: item.notes.trim() || null })),
  };
}

/** 按关键词搜索目标单位，同时保留当前已选项，避免加载完整单位库。 */
function OrganizationReferenceField({ activity, onChange }: { activity: ActivityDraft; onChange: (changes: Partial<ActivityDraft>) => void }) {
  const [search, setSearch] = useState("");
  const [options, setOptions] = useState<AdminDataOption[]>(activity.organizationId ? [{ value: activity.organizationId, label: activity.organizationName || "已选目标单位" }] : []);
  const [loading, setLoading] = useState(false);
  const [searchEnabled, setSearchEnabled] = useState(false);

  useEffect(() => {
    if (!searchEnabled && !search.trim()) return;
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => {
      setLoading(true);
      void apiFetch<AdminDataOption[]>(`/admin-data/organizations/options${queryString({ search: search || undefined, selected_id: activity.organizationId || undefined })}`, { signal: controller.signal })
        .then(setOptions)
        .catch((error: unknown) => { if (!(error instanceof DOMException && error.name === "AbortError")) setOptions([]); })
        .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, 220);
    return () => { window.clearTimeout(timeoutId); controller.abort(); };
  }, [activity.organizationId, search, searchEnabled]);

  return <div className="admin-reference-field"><input aria-label="搜索关联目标单位" value={search} onFocus={() => setSearchEnabled(true)} onChange={(event) => setSearch(event.target.value)} placeholder="按单位名称搜索" /><select aria-label="关联目标单位" value={activity.organizationId} onChange={(event) => { const option = options.find((item) => item.value === event.target.value); onChange({ organizationId: event.target.value, organizationName: option?.label ?? "" }); }}><option value="">{loading ? "正在搜索…" : "不关联目标单位"}</option>{options.map((option) => <option value={option.value} key={option.value}>{option.label}</option>)}</select></div>;
}

/** 完整档案对话框：主档、分级覆盖范围和活动在一次提交中保存。 */
function SalespersonProfileDialog({ profile, onCancel, onSaved }: { profile: SalespersonProfile | null; onCancel: () => void; onSaved: (payload: Record<string, unknown>) => Promise<void> }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [form, setForm] = useState<ProfileForm>(() => initialForm(profile));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { const dialog = dialogRef.current; dialog?.showModal(); return () => { if (dialog?.open) dialog.close(); }; }, []);

  /** 更新销售主档的一个顶层字段。 */
  function updateField<K extends keyof ProfileForm>(field: K, value: ProfileForm[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  /** 提交完整档案；失败时保留所有内嵌草稿供继续修正。 */
  async function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onSaved(profilePayload(form));
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "保存失败，请核对字段后重试");
      setSubmitting(false);
    }
  }

  return (
    <dialog ref={dialogRef} className="organization-edit-dialog salesperson-profile-dialog" aria-labelledby="salesperson-profile-title" onCancel={(event) => { event.preventDefault(); if (!submitting) onCancel(); }}>
      <form onSubmit={submitProfile}>
        <header><div><span>销售人员完整档案</span><h2 id="salesperson-profile-title">{profile ? `管理 ${profile.display_name}` : "添加销售人员"}</h2><p>覆盖范围与销售活动随人员档案一起保存</p></div><button type="button" onClick={onCancel} disabled={submitting} aria-label="关闭销售人员档案"><X size={19} /></button></header>
        <div className="organization-edit-body">
          <section><h3>基本信息与地图 Pin</h3><div className="organization-edit-grid">
            <label><span>员工编号 *</span><input value={form.employeeCode} onChange={(event) => updateField("employeeCode", event.target.value)} maxLength={40} required autoFocus /></label>
            <label><span>姓名 *</span><input value={form.displayName} onChange={(event) => updateField("displayName", event.target.value)} minLength={2} maxLength={120} required /></label>
            <label><span>展示颜色 *</span><input type="color" value={form.color} onChange={(event) => updateField("color", event.target.value)} required /></label>
            <label className="admin-data-checkbox"><input type="checkbox" checked={form.isActive} onChange={(event) => updateField("isActive", event.target.checked)} /><span>在职启用</span></label>
            <label><span>Pin 经度 *</span><input type="number" step="any" min={72.004} max={137.8347} value={form.centerLongitude} onChange={(event) => updateField("centerLongitude", event.target.value)} required /></label>
            <label><span>Pin 纬度 *</span><input type="number" step="any" min={0.8293} max={55.8271} value={form.centerLatitude} onChange={(event) => updateField("centerLatitude", event.target.value)} required /></label>
          </div></section>

          <section>
            <div className="organization-edit-section-head"><div><h3>覆盖范围</h3><p>每条可选择市、省、大区或全国；不同销售可使用不同层级</p></div><button type="button" onClick={() => updateField("coverageScopes", [...form.coverageScopes, emptyCoverageScope()])}><Plus size={14} />新增覆盖范围</button></div>
            {form.coverageScopes.length === 0 ? <p className="organization-edit-empty">尚未添加覆盖范围。</p> : null}
            <div className="organization-edit-records">{form.coverageScopes.map((item, index) => (
              <article className="organization-edit-record" key={item.draftKey}>
                <div className="organization-edit-record-head"><strong>覆盖范围 {index + 1}</strong><button type="button" onClick={() => updateField("coverageScopes", form.coverageScopes.filter((_, itemIndex) => itemIndex !== index))}><Trash2 size={13} />移除</button></div>
                <div className="organization-edit-grid">
                  <label><span>覆盖层级 *</span><select aria-label={`覆盖层级 ${index + 1}`} value={item.scopeLevel} onChange={(event) => updateField("coverageScopes", updateAt(form.coverageScopes, index, coverageLevelChanges(event.target.value as SalesCoverageLevel)))}>{salesCoverageLevels.map((level) => <option key={level}>{level}</option>)}</select></label>
                  {item.scopeLevel === "大区" ? <><label><span>大区 *</span><select value={item.scopeName} onChange={(event) => updateField("coverageScopes", updateAt(form.coverageScopes, index, { scopeName: event.target.value }))} required><option value="">请选择大区</option>{salesRegions.map((region) => <option key={region}>{region}</option>)}</select></label><p className="salesperson-scope-provinces">{item.scopeName ? `包含：${salesRegionDescription(item.scopeName)}` : "选择后显示大区所含省份"}</p></> : null}
                  {item.scopeLevel === "省" ? <label><span>省份 *</span><select value={item.province} onChange={(event) => updateField("coverageScopes", updateAt(form.coverageScopes, index, { province: event.target.value, scopeName: event.target.value }))} required><option value="">请选择省份</option>{salesProvinces.map((province) => <option key={province}>{province}</option>)}</select></label> : null}
                  {item.scopeLevel === "市" ? <><label><span>省份 *</span><select value={item.province} onChange={(event) => updateField("coverageScopes", updateAt(form.coverageScopes, index, { province: event.target.value }))} required><option value="">请选择省份</option>{salesProvinces.map((province) => <option key={province}>{province}</option>)}</select></label><label><span>城市 *</span><input value={item.city} onChange={(event) => updateField("coverageScopes", updateAt(form.coverageScopes, index, { city: event.target.value, scopeName: event.target.value }))} maxLength={60} required /></label><label><span>高德行政区编码 *</span><input value={item.amapAdcode} onChange={(event) => updateField("coverageScopes", updateAt(form.coverageScopes, index, { amapAdcode: event.target.value }))} pattern="[0-9]{6}" maxLength={6} inputMode="numeric" required /></label></> : null}
                  {item.scopeLevel === "全国" ? <p className="salesperson-scope-provinces">覆盖全国，无需填写省市。</p> : null}
                </div>
              </article>
            ))}</div>
          </section>

          <section><div className="organization-edit-section-head"><div><h3>销售活动</h3><p>记录拜访、演示和市场活动，可关联目标单位</p></div><button type="button" onClick={() => updateField("activities", [...form.activities, emptyActivity()])}><Plus size={14} />新增销售活动</button></div>{form.activities.length === 0 ? <p className="organization-edit-empty">尚未添加销售活动。</p> : null}<div className="organization-edit-records">{form.activities.map((activity, index) => <article className="organization-edit-record" key={activity.draftKey}><div className="organization-edit-record-head"><strong>销售活动 {index + 1}</strong><button type="button" onClick={() => updateField("activities", form.activities.filter((_, itemIndex) => itemIndex !== index))}><Trash2 size={13} />移除</button></div><div className="organization-edit-grid"><label><span>活动类型 *</span><select value={activity.activityType} onChange={(event) => updateField("activities", updateAt(form.activities, index, { activityType: event.target.value as SalesActivityType }))}>{activityTypes.map((type) => <option key={type}>{type}</option>)}</select></label><label><span>发生时间 *</span><input type="datetime-local" value={activity.occurredAt} onChange={(event) => updateField("activities", updateAt(form.activities, index, { occurredAt: event.target.value }))} required /></label><label className="field-wide"><span>关联目标单位</span><OrganizationReferenceField activity={activity} onChange={(changes) => updateField("activities", updateAt(form.activities, index, changes))} /></label><label><span>省份 *</span><input value={activity.province} onChange={(event) => updateField("activities", updateAt(form.activities, index, { province: event.target.value }))} maxLength={60} required /></label><label><span>城市 *</span><input value={activity.city} onChange={(event) => updateField("activities", updateAt(form.activities, index, { city: event.target.value }))} maxLength={60} required /></label><label><span>高德行政区编码 *</span><input value={activity.amapAdcode} onChange={(event) => updateField("activities", updateAt(form.activities, index, { amapAdcode: event.target.value }))} pattern="[0-9]{6}" maxLength={6} inputMode="numeric" required /></label><label className="field-wide"><span>活动备注</span><textarea value={activity.notes} onChange={(event) => updateField("activities", updateAt(form.activities, index, { notes: event.target.value }))} maxLength={5000} rows={3} /></label></div></article>)}</div></section>
        </div>
        {error ? <p className="organization-dialog-error" role="alert"><CircleAlert size={16} />{error}</p> : null}
        <footer><button type="button" className="organization-dialog-cancel" onClick={onCancel} disabled={submitting}>取消</button><button className="organization-dialog-save" disabled={submitting}><Save size={16} />{submitting ? "正在保存…" : profile ? "保存完整档案" : "添加销售人员"}</button></footer>
      </form>
    </dialog>
  );
}

/** 二次确认删除销售档案，并说明子记录与业务引用处理规则。 */
function SalespersonDeleteDialog({ item, onCancel, onConfirm }: { item: SalespersonListItem; onCancel: () => void; onConfirm: () => Promise<void> }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { const dialog = dialogRef.current; dialog?.showModal(); return () => { if (dialog?.open) dialog.close(); }; }, []);

  /** 删除人员档案，失败时保留确认层并显示数据库保护原因。 */
  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setDeleting(true); setError(null);
    try { await onConfirm(); } catch (deleteError) { setError(deleteError instanceof Error ? deleteError.message : "删除失败，请稍后重试"); setDeleting(false); }
  }

  return <dialog ref={dialogRef} className="organization-delete-dialog" aria-labelledby="salesperson-delete-title" onCancel={(event) => { event.preventDefault(); if (!deleting) onCancel(); }}><form onSubmit={confirm}><div className="delete-dialog-icon"><Trash2 size={22} /></div><h2 id="salesperson-delete-title">确认删除销售人员？</h2><p>“{item.display_name}”及其覆盖范围、销售活动将永久删除；存在商机或成交项目引用时系统会阻止删除。</p>{error ? <p className="organization-dialog-error" role="alert"><CircleAlert size={16} />{error}</p> : null}<footer><button type="button" className="organization-dialog-cancel" onClick={onCancel} disabled={deleting} autoFocus>取消</button><button className="organization-dialog-delete" disabled={deleting}><Trash2 size={16} />{deleting ? "正在删除…" : "确认删除"}</button></footer></form></dialog>;
}

/** 销售页只保留人员列表，所有明细通过完整档案按需加载。 */
export function AdminSalesWorkspace() {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search.trim());
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [page, setPage] = useState<SalespersonPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<SalespersonProfile | null>(null);
  const [openingId, setOpeningId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<SalespersonListItem | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const { run: runDetailRequest } = useLatestRequest();
  const totalPages = Math.max(1, Math.ceil((page?.total ?? 0) / pageSize));

  useEffect(() => { if (!notice) return; const timeoutId = window.setTimeout(() => setNotice(null), 2400); return () => window.clearTimeout(timeoutId); }, [notice]);

  /** 读取当前销售人员分页，并取消已经过期的列表请求。 */
  const loadPage = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController(); abortRef.current = controller; setLoading(true); setError(null);
    try {
      const result = await apiFetch<SalespersonPage>(`/admin-salespeople${queryString({ page: String(currentPage), page_size: String(pageSize), search: debouncedSearch || undefined })}`, { signal: controller.signal });
      setPage(result);
    } catch (loadError) {
      if (!(loadError instanceof DOMException && loadError.name === "AbortError")) setError(loadError instanceof Error ? loadError.message : "销售人员列表加载失败");
    } finally { if (!controller.signal.aborted) setLoading(false); }
  }, [currentPage, debouncedSearch, pageSize]);

  useEffect(() => { const timeoutId = window.setTimeout(() => void loadPage(), 0); return () => window.clearTimeout(timeoutId); }, [loadPage]);
  useEffect(() => () => abortRef.current?.abort(), []);

  /** 按最后一次点击加载完整档案，旧请求不能覆盖后续选择。 */
  async function openProfile(item: SalespersonListItem) {
    setOpeningId(item.id); setError(null);
    try {
      const profile = await runDetailRequest((signal) => apiFetch<SalespersonProfile>(`/admin-salespeople/${item.id}`, { signal }));
      if (profile) setEditing(profile);
    }
    catch (openError) { setError(openError instanceof Error ? openError.message : "销售人员档案加载失败"); }
    finally { setOpeningId((current) => current === item.id ? null : current); }
  }

  /** 新增或更新完整档案，成功后刷新当前分页。 */
  async function saveProfile(payload: Record<string, unknown>) {
    const path = editing ? `/admin-salespeople/${editing.id}` : "/admin-salespeople";
    await apiFetch<SalespersonProfile>(path, { method: editing ? "PATCH" : "POST", body: JSON.stringify(payload) });
    setEditing(null); setCreating(false); setNotice(editing ? "销售人员完整档案已更新" : "销售人员已添加"); await loadPage();
  }

  /** 删除销售档案及内嵌记录，并在最后一页为空时回退一页。 */
  async function deleteProfile() {
    if (!deleteTarget) return;
    await apiFetch<void>(`/admin-salespeople/${deleteTarget.id}`, { method: "DELETE" });
    const shouldGoBack = (page?.items.length ?? 0) === 1 && currentPage > 1;
    setDeleteTarget(null); setNotice("销售人员档案已删除");
    if (shouldGoBack) setCurrentPage((value) => value - 1); else await loadPage();
  }

  return <section className="admin-data-workspace salesperson-admin-workspace" aria-label="销售数据管理">
    <div className="admin-data-toolbar"><label className="admin-data-search"><Search size={16} /><input aria-label="搜索销售人员" value={search} onChange={(event) => { setSearch(event.target.value); setCurrentPage(1); }} placeholder="搜索姓名或员工编号" /></label></div>
    {notice ? <p className="admin-page-notice"><Check size={16} />{notice}</p> : null}{error ? <p className="admin-page-error" role="alert"><CircleAlert size={16} />{error}</p> : null}
    <div className="organization-list-card admin-data-list-card salesperson-admin-list-card">
      <div className="card-title"><div><span>销售人员</span><h2>{page?.total.toLocaleString("zh-CN") ?? "—"} 条记录</h2><p>分级覆盖范围、实际成交金额与近三个月活动汇总；点击修改进入完整档案。</p></div><button className="organization-create-button" onClick={() => setCreating(true)}><Plus size={15} />添加销售人员</button></div>
      <div className="admin-data-table salesperson-admin-table" role="table" aria-busy={loading}>
        <div className="admin-data-row admin-data-row-head" role="row"><span role="columnheader">销售人员</span><span role="columnheader">覆盖范围（最多 10 个）</span><span role="columnheader">成交金额</span><span role="columnheader">近三个月销售活动</span><span role="columnheader">操作</span></div>
        {page?.items.map((item) => <div className="admin-data-row" role="row" key={item.id}>
          <strong className="salesperson-list-name" role="cell"><i style={{ background: item.color }} />{item.display_name}<small>{item.employee_code}</small></strong>
          <div className="salesperson-city-list" role="cell"><small className="salesperson-mobile-label">覆盖范围</small>{item.coverage_scopes.length ? item.coverage_scopes.map((scope, index) => <span key={`${scope}-${index}`}>{scope}</span>) : <em>未配置</em>}{item.coverage_scope_total > item.coverage_scopes.length ? <em>另 {item.coverage_scope_total - item.coverage_scopes.length} 个</em> : null}</div>
          <div className="salesperson-sales-summary" role="cell"><small className="salesperson-mobile-label">成交金额</small><strong className="salesperson-sales-amount">{currencyFormatter.format(Number(item.actual_sales_amount))}</strong></div>
          <div className="salesperson-activity-counts" role="cell"><small className="salesperson-mobile-label">近三个月销售活动</small><span>拜访 <b>{item.visit_count}</b></span><span>演示 <b>{item.demonstration_count}</b></span><span>市场活动 <b>{item.marketing_event_count}</b></span></div>
          <div className="organization-row-actions salesperson-list-actions" role="cell"><button className="organization-edit-action" onClick={() => void openProfile(item)} disabled={openingId === item.id}><Pencil size={14} />{openingId === item.id ? "正在打开" : "修改"}</button><button className="organization-delete-action" onClick={() => setDeleteTarget(item)}><Trash2 size={14} />删除</button></div>
        </div>)}
      </div>
      {loading ? <div className="admin-data-state" role="status">正在读取销售人员…</div> : null}{!loading && page?.items.length === 0 ? <div className="organization-empty"><Search size={21} />暂无匹配销售人员。可以清除搜索条件或添加第一名销售。</div> : null}
      {page ? <nav className="organization-pagination" aria-label="销售人员列表分页"><span>第 {currentPage} / {totalPages} 页 · 共 {page.total.toLocaleString("zh-CN")} 条</span><div><label className="organization-page-size">每页<select aria-label="每页显示销售人员数" value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setCurrentPage(1); }}>{pageSizeOptions.map((size) => <option value={size} key={size}>{size} 条</option>)}</select></label><button type="button" onClick={() => setCurrentPage((value) => Math.max(1, value - 1))} disabled={currentPage === 1}>上一页</button><button type="button" onClick={() => setCurrentPage((value) => Math.min(totalPages, value + 1))} disabled={currentPage === totalPages}>下一页</button></div></nav> : null}
    </div>
    {creating ? <SalespersonProfileDialog profile={null} onCancel={() => setCreating(false)} onSaved={saveProfile} /> : null}{editing ? <SalespersonProfileDialog key={editing.id} profile={editing} onCancel={() => setEditing(null)} onSaved={saveProfile} /> : null}{deleteTarget ? <SalespersonDeleteDialog item={deleteTarget} onCancel={() => setDeleteTarget(null)} onConfirm={deleteProfile} /> : null}
  </section>;
}
