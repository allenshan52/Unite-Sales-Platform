"use client";

/** 客户集团聚合工作台：分页管理集团，并在同一档案内维护总部和完整分支树。 */

import { FormEvent, useCallback, useEffect, useRef, useState } from "react";
import { Building2, Check, CircleAlert, Pencil, Plus, Save, Search, Trash2, X } from "lucide-react";

import { apiFetch, queryString, type CustomerGroupProfile, type OpportunityStage } from "@/lib/api";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { useLatestRequest } from "@/hooks/use-latest-request";

type CustomerGroupListItem = {
  id: string;
  name: string;
  color: string;
  headquarters_name: string | null;
  headquarters_city: string | null;
  branch_count: number;
  won_unit_count: number;
  active_opportunity_count: number;
  actual_sales_amount: string;
  estimated_opportunity_amount: string;
};
type CustomerGroupPage = { items: CustomerGroupListItem[]; total: number; page: number; page_size: number };
type UnitDraft = {
  draftKey: string;
  id: string | null;
  parentDraftKey: string;
  name: string;
  isHeadquarters: boolean;
  address: string;
  province: string;
  city: string;
  longitude: string;
  latitude: string;
  isWon: boolean;
  actualSalesAmount: string;
  opportunityStage: OpportunityStage | "";
  estimatedOpportunityAmount: string;
};
type GroupForm = { name: string; color: string; units: UnitDraft[] };

const pageSizeOptions = [10, 25, 50, 75, 100];
const opportunityStages: OpportunityStage[] = ["已识别", "资格确认", "方案/报价", "商务谈判", "已关闭失单"];
const currencyFormatter = new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 2 });

/** 生成同一表单会话内稳定的单位草稿键，用于新节点父子关系。 */
function createDraftKey(): string {
  return globalThis.crypto?.randomUUID?.() ?? `${Date.now()}-${Math.random()}`;
}

/** 创建总部或分支的完整空白草稿，并为分支默认选中总部。 */
function emptyUnit(isHeadquarters: boolean, parentDraftKey = ""): UnitDraft {
  return {
    draftKey: createDraftKey(), id: null, parentDraftKey, name: "", isHeadquarters,
    address: "", province: "", city: "", longitude: "116.4074", latitude: "39.9042",
    isWon: false, actualSalesAmount: "0", opportunityStage: "", estimatedOpportunityAmount: "",
  };
}

/** 从空白默认值或服务端完整档案创建隔离表单，历史缺总部档案会进入可修复状态。 */
function initialForm(profile: CustomerGroupProfile | null): GroupForm {
  if (!profile) return { name: "", color: "#2F8F72", units: [emptyUnit(true)] };
  const units: UnitDraft[] = profile.units.map((unit) => ({
    draftKey: unit.draft_key,
    id: unit.id,
    parentDraftKey: unit.parent_draft_key ?? "",
    name: unit.name,
    isHeadquarters: unit.is_headquarters,
    address: unit.address,
    province: unit.province,
    city: unit.city,
    longitude: String(unit.longitude),
    latitude: String(unit.latitude),
    isWon: unit.is_won,
    actualSalesAmount: unit.actual_sales_amount,
    opportunityStage: unit.opportunity_stage ?? "",
    estimatedOpportunityAmount: unit.estimated_opportunity_amount ?? "",
  }));
  return { name: profile.name, color: profile.color, units: units.length ? units : [emptyUnit(true)] };
}

/** 不改变原数组地更新指定单位草稿，避免兄弟节点共享引用。 */
function updateUnit(units: UnitDraft[], index: number, changes: Partial<UnitDraft>): UnitDraft[] {
  return units.map((unit, unitIndex) => unitIndex === index ? { ...unit, ...changes } : unit);
}

/** 把集团表单转换为聚合 API 所需的完整 snake_case 单位树。 */
function profilePayload(form: GroupForm): Record<string, unknown> {
  return {
    name: form.name.trim(),
    color: form.color,
    units: form.units.map((unit) => ({
      id: unit.id,
      draft_key: unit.draftKey,
      parent_draft_key: unit.parentDraftKey || null,
      name: unit.name.trim(),
      is_headquarters: unit.isHeadquarters,
      address: unit.address.trim(),
      province: unit.province.trim(),
      city: unit.city.trim(),
      longitude: Number(unit.longitude),
      latitude: Number(unit.latitude),
      is_won: unit.isWon,
      actual_sales_amount: unit.isWon ? Number(unit.actualSalesAmount) : 0,
      opportunity_stage: unit.opportunityStage || null,
      estimated_opportunity_amount: unit.estimatedOpportunityAmount === "" ? null : Number(unit.estimatedOpportunityAmount),
    })),
  };
}

/** 完整档案对话框：集团主档和任意层级单位树在一次提交中保存。 */
function CustomerGroupProfileDialog({ profile, onCancel, onSaved }: { profile: CustomerGroupProfile | null; onCancel: () => void; onSaved: (payload: Record<string, unknown>) => Promise<void> }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [form, setForm] = useState<GroupForm>(() => initialForm(profile));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { const dialog = dialogRef.current; dialog?.showModal(); return () => { if (dialog?.open) dialog.close(); }; }, []);

  /** 更新集团主档的一个顶层字段。 */
  function updateField<K extends keyof GroupForm>(field: K, value: GroupForm[K]) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  /** 新增一个默认挂在总部下的分支节点。 */
  function addBranch() {
    const headquarters = form.units.find((unit) => unit.isHeadquarters);
    updateField("units", [...form.units, emptyUnit(false, headquarters?.draftKey ?? "")]);
  }

  /** 删除分支并把其直接子节点安全改挂到被删节点的父级。 */
  function removeBranch(index: number) {
    const target = form.units[index];
    if (target.isHeadquarters) return;
    updateField("units", form.units
      .filter((_, unitIndex) => unitIndex !== index)
      .map((unit) => unit.parentDraftKey === target.draftKey ? { ...unit, parentDraftKey: target.parentDraftKey } : unit));
  }

  /** 提交完整档案；失败时保留全部单位草稿供继续修正。 */
  async function submitProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSubmitting(true); setError(null);
    try { await onSaved(profilePayload(form)); }
    catch (submitError) { setError(submitError instanceof Error ? submitError.message : "保存失败，请核对单位层级和金额后重试"); setSubmitting(false); }
  }

  return <dialog ref={dialogRef} className="organization-edit-dialog customer-group-profile-dialog" aria-labelledby="customer-group-profile-title" onCancel={(event) => { event.preventDefault(); if (!submitting) onCancel(); }}>
    <form onSubmit={submitProfile}>
      <header><div><span>客户集团完整档案</span><h2 id="customer-group-profile-title">{profile ? `管理 ${profile.name}` : "添加客户集团"}</h2><p>集团主档、总部与所有分支在一次操作中保存</p></div><button type="button" onClick={onCancel} disabled={submitting} aria-label="关闭客户集团档案"><X size={19} /></button></header>
      <div className="organization-edit-body">
        <section><h3>集团主档</h3><div className="organization-edit-grid"><label className="field-wide"><span>集团名称 *</span><input value={form.name} onChange={(event) => updateField("name", event.target.value)} minLength={2} maxLength={255} required autoFocus /></label><label><span>关系网络展示颜色 *</span><input type="color" value={form.color} onChange={(event) => updateField("color", event.target.value)} required /></label></div></section>
        <section><div className="organization-edit-section-head"><div><h3>总部与分支</h3><p>总部固定为唯一根节点，分支可选择任意上级单位</p></div><button type="button" onClick={addBranch}><Plus size={14} />新增分支单位</button></div><div className="organization-edit-records">{form.units.map((unit, index) => <article className="organization-edit-record customer-group-unit-record" key={unit.draftKey}>
          <div className="organization-edit-record-head"><strong>{unit.isHeadquarters ? "集团总部" : `分支单位 ${index}`}</strong>{unit.isHeadquarters ? <span>唯一根节点</span> : <button type="button" onClick={() => removeBranch(index)}><Trash2 size={13} />移除</button>}</div>
          <div className="organization-edit-grid">
            <label className="field-wide"><span>单位名称 *</span><input value={unit.name} onChange={(event) => updateField("units", updateUnit(form.units, index, { name: event.target.value }))} minLength={2} maxLength={255} required /></label>
            {!unit.isHeadquarters ? <label><span>父级单位 *</span><select value={unit.parentDraftKey} onChange={(event) => updateField("units", updateUnit(form.units, index, { parentDraftKey: event.target.value }))} required><option value="">请选择父级</option>{form.units.filter((option) => option.draftKey !== unit.draftKey).map((option) => <option key={option.draftKey} value={option.draftKey}>{option.name || (option.isHeadquarters ? "未命名总部" : "未命名分支")}</option>)}</select></label> : null}
            <label className="field-wide"><span>详细地址 *</span><input value={unit.address} onChange={(event) => updateField("units", updateUnit(form.units, index, { address: event.target.value }))} minLength={2} maxLength={500} required /></label>
            <label><span>省份 *</span><input value={unit.province} onChange={(event) => updateField("units", updateUnit(form.units, index, { province: event.target.value }))} minLength={2} maxLength={60} required /></label>
            <label><span>城市 *</span><input value={unit.city} onChange={(event) => updateField("units", updateUnit(form.units, index, { city: event.target.value }))} minLength={2} maxLength={60} required /></label>
            <label><span>经度 *</span><input type="number" step="any" min={72.004} max={137.8347} value={unit.longitude} onChange={(event) => updateField("units", updateUnit(form.units, index, { longitude: event.target.value }))} required /></label>
            <label><span>纬度 *</span><input type="number" step="any" min={0.8293} max={55.8271} value={unit.latitude} onChange={(event) => updateField("units", updateUnit(form.units, index, { latitude: event.target.value }))} required /></label>
            <label className="admin-data-checkbox"><input type="checkbox" checked={unit.isWon} onChange={(event) => updateField("units", updateUnit(form.units, index, { isWon: event.target.checked, actualSalesAmount: event.target.checked ? unit.actualSalesAmount : "0" }))} /><span>该单位已成交</span></label>
            <label><span>实际销售额（元）*</span><input type="number" step="0.01" min={unit.isWon ? 0.01 : 0} value={unit.actualSalesAmount} onChange={(event) => updateField("units", updateUnit(form.units, index, { actualSalesAmount: event.target.value }))} disabled={!unit.isWon} required /></label>
            <label><span>商机阶段</span><select value={unit.opportunityStage} onChange={(event) => updateField("units", updateUnit(form.units, index, { opportunityStage: event.target.value as OpportunityStage | "" }))}><option value="">暂无商机</option>{opportunityStages.map((stage) => <option key={stage}>{stage}</option>)}</select></label>
            <label><span>预计商机金额（元）</span><input type="number" step="0.01" min={0} value={unit.estimatedOpportunityAmount} onChange={(event) => updateField("units", updateUnit(form.units, index, { estimatedOpportunityAmount: event.target.value }))} /></label>
          </div>
        </article>)}</div></section>
      </div>
      {error ? <p className="organization-dialog-error" role="alert"><CircleAlert size={16} />{error}</p> : null}
      <footer><button type="button" className="organization-dialog-cancel" onClick={onCancel} disabled={submitting}>取消</button><button className="organization-dialog-save" disabled={submitting}><Save size={16} />{submitting ? "正在保存…" : profile ? "保存完整档案" : "添加客户集团"}</button></footer>
    </form>
  </dialog>;
}

/** 二次确认删除集团档案，并明确全部单位树会随主档级联删除。 */
function CustomerGroupDeleteDialog({ item, onCancel, onConfirm }: { item: CustomerGroupListItem; onCancel: () => void; onConfirm: () => Promise<void> }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { const dialog = dialogRef.current; dialog?.showModal(); return () => { if (dialog?.open) dialog.close(); }; }, []);

  /** 删除集团档案，失败时保留确认层并显示恢复建议。 */
  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setDeleting(true); setError(null);
    try { await onConfirm(); } catch (deleteError) { setError(deleteError instanceof Error ? deleteError.message : "删除失败，请稍后重试"); setDeleting(false); }
  }

  return <dialog ref={dialogRef} className="organization-delete-dialog" aria-labelledby="customer-group-delete-title" onCancel={(event) => { event.preventDefault(); if (!deleting) onCancel(); }}><form onSubmit={confirm}><div className="delete-dialog-icon"><Trash2 size={22} /></div><h2 id="customer-group-delete-title">确认删除客户集团？</h2><p>“{item.name}”及总部、{item.branch_count} 个分支单位将永久删除，此操作无法撤销。</p>{error ? <p className="organization-dialog-error" role="alert"><CircleAlert size={16} />{error}</p> : null}<footer><button type="button" className="organization-dialog-cancel" onClick={onCancel} disabled={deleting} autoFocus>取消</button><button className="organization-dialog-delete" disabled={deleting}><Trash2 size={16} />{deleting ? "正在删除…" : "确认删除"}</button></footer></form></dialog>;
}

/** 客户集团页只保留集团列表，全部单位树通过完整档案按需加载。 */
export function AdminCustomerGroupWorkspace() {
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search.trim());
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [page, setPage] = useState<CustomerGroupPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<CustomerGroupProfile | null>(null);
  const [openingId, setOpeningId] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CustomerGroupListItem | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const { run: runDetailRequest } = useLatestRequest();
  const totalPages = Math.max(1, Math.ceil((page?.total ?? 0) / pageSize));

  useEffect(() => { if (!notice) return; const timeoutId = window.setTimeout(() => setNotice(null), 2400); return () => window.clearTimeout(timeoutId); }, [notice]);

  /** 读取当前集团分页，并取消已经过期的列表请求。 */
  const loadPage = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController(); abortRef.current = controller; setLoading(true); setError(null);
    try { setPage(await apiFetch<CustomerGroupPage>(`/admin-customer-groups${queryString({ page: String(currentPage), page_size: String(pageSize), search: debouncedSearch || undefined })}`, { signal: controller.signal })); }
    catch (loadError) { if (!(loadError instanceof DOMException && loadError.name === "AbortError")) setError(loadError instanceof Error ? loadError.message : "客户集团列表加载失败"); }
    finally { if (!controller.signal.aborted) setLoading(false); }
  }, [currentPage, debouncedSearch, pageSize]);

  useEffect(() => { const timeoutId = window.setTimeout(() => void loadPage(), 0); return () => window.clearTimeout(timeoutId); }, [loadPage]);
  useEffect(() => () => abortRef.current?.abort(), []);

  /** 按最后一次点击加载完整档案，旧请求不能覆盖后续选择。 */
  async function openProfile(item: CustomerGroupListItem) {
    setOpeningId(item.id); setError(null);
    try {
      const profile = await runDetailRequest((signal) => apiFetch<CustomerGroupProfile>(`/admin-customer-groups/${item.id}`, { signal }));
      if (profile) setEditing(profile);
    }
    catch (openError) { setError(openError instanceof Error ? openError.message : "客户集团档案加载失败"); }
    finally { setOpeningId((current) => current === item.id ? null : current); }
  }

  /** 新增或更新完整集团档案，成功后刷新当前分页。 */
  async function saveProfile(payload: Record<string, unknown>) {
    const path = editing ? `/admin-customer-groups/${editing.id}` : "/admin-customer-groups";
    await apiFetch<CustomerGroupProfile>(path, { method: editing ? "PATCH" : "POST", body: JSON.stringify(payload) });
    setEditing(null); setCreating(false); setNotice(editing ? "客户集团完整档案已更新" : "客户集团已添加"); await loadPage();
  }

  /** 删除集团及单位树，并在最后一页为空时回退一页。 */
  async function deleteProfile() {
    if (!deleteTarget) return;
    await apiFetch<void>(`/admin-customer-groups/${deleteTarget.id}`, { method: "DELETE" });
    const shouldGoBack = (page?.items.length ?? 0) === 1 && currentPage > 1;
    setDeleteTarget(null); setNotice("客户集团档案已删除");
    if (shouldGoBack) setCurrentPage((value) => value - 1); else await loadPage();
  }

  return <section className="admin-data-workspace customer-group-admin-workspace" aria-label="客户集团数据管理">
    <div className="admin-data-toolbar"><label className="admin-data-search"><Search size={16} /><input aria-label="搜索客户集团" value={search} onChange={(event) => { setSearch(event.target.value); setCurrentPage(1); }} placeholder="搜索集团名称" /></label></div>
    {notice ? <p className="admin-page-notice"><Check size={16} />{notice}</p> : null}{error ? <p className="admin-page-error" role="alert"><CircleAlert size={16} />{error}</p> : null}
    <div className="organization-list-card admin-data-list-card customer-group-admin-list-card">
      <div className="card-title"><div><span>客户集团</span><h2>{page?.total.toLocaleString("zh-CN") ?? "—"} 条记录</h2><p>总部、分支规模、实际成交和商机汇总；点击修改进入完整集团档案。</p></div><button className="organization-create-button" onClick={() => setCreating(true)}><Plus size={15} />添加客户集团</button></div>
      <div className="admin-data-table customer-group-admin-table" role="table" aria-busy={loading}>
        <div className="admin-data-row admin-data-row-head" role="row"><span role="columnheader">客户集团</span><span role="columnheader">集团总部</span><span role="columnheader">单位规模</span><span role="columnheader">实际成交</span><span role="columnheader">预计商机</span><span role="columnheader">操作</span></div>
        {page?.items.map((item) => <div className="admin-data-row" role="row" key={item.id}>
          <strong className="customer-group-list-name" role="cell"><i style={{ background: item.color }} />{item.name}</strong>
          <div className="customer-group-headquarters" role="cell"><small className="customer-group-mobile-label">集团总部</small><strong>{item.headquarters_name ?? "尚未配置"}</strong>{item.headquarters_city ? <span>{item.headquarters_city}</span> : null}</div>
          <div className="customer-group-counts" role="cell"><small className="customer-group-mobile-label">单位规模</small><span>分支 <b>{item.branch_count}</b></span><span>已成交 <b>{item.won_unit_count}</b></span><span>商机 <b>{item.active_opportunity_count}</b></span></div>
          <div className="customer-group-amount" role="cell"><small className="customer-group-mobile-label">实际成交</small><strong>{currencyFormatter.format(Number(item.actual_sales_amount))}</strong></div>
          <div className="customer-group-amount customer-group-opportunity-amount" role="cell"><small className="customer-group-mobile-label">预计商机</small><strong>{currencyFormatter.format(Number(item.estimated_opportunity_amount))}</strong></div>
          <div className="organization-row-actions customer-group-list-actions" role="cell"><button className="organization-edit-action" onClick={() => void openProfile(item)} disabled={openingId === item.id}><Pencil size={14} />{openingId === item.id ? "正在打开" : "修改"}</button><button className="organization-delete-action" onClick={() => setDeleteTarget(item)}><Trash2 size={14} />删除</button></div>
        </div>)}
      </div>
      {loading ? <div className="admin-data-state" role="status">正在读取客户集团…</div> : null}{!loading && page?.items.length === 0 ? <div className="organization-empty"><Building2 size={21} />暂无匹配客户集团。可以清除搜索条件或添加第一个集团。</div> : null}
      {page ? <nav className="organization-pagination" aria-label="客户集团列表分页"><span>第 {currentPage} / {totalPages} 页 · 共 {page.total.toLocaleString("zh-CN")} 条</span><div><label className="organization-page-size">每页<select aria-label="每页显示客户集团数" value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setCurrentPage(1); }}>{pageSizeOptions.map((size) => <option value={size} key={size}>{size} 条</option>)}</select></label><button type="button" onClick={() => setCurrentPage((value) => Math.max(1, value - 1))} disabled={currentPage === 1}>上一页</button><button type="button" onClick={() => setCurrentPage((value) => Math.min(totalPages, value + 1))} disabled={currentPage === totalPages}>下一页</button></div></nav> : null}
    </div>
    {creating ? <CustomerGroupProfileDialog profile={null} onCancel={() => setCreating(false)} onSaved={saveProfile} /> : null}{editing ? <CustomerGroupProfileDialog key={editing.id} profile={editing} onCancel={() => setEditing(null)} onSaved={saveProfile} /> : null}{deleteTarget ? <CustomerGroupDeleteDialog item={deleteTarget} onCancel={() => setDeleteTarget(null)} onConfirm={deleteProfile} /> : null}
  </section>;
}
