"use client";

/** 同行聚合后台：以同行主档为唯一入口，按需维护据点、成交单位、交易、关联和强势区域。 */

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowLeft,
  Building2,
  Check,
  CircleAlert,
  Database,
  Link2,
  MapPin,
  Pencil,
  Plus,
  Search,
  Trash2,
} from "lucide-react";

import {
  AdminDataDeleteDialog,
  AdminDataFormDialog,
  displayValue,
  type AdminDataItem,
  type AdminDataPage,
} from "@/components/admin-data-workspace";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { ADMIN_SECTION_CONFIGS, type AdminResourceConfig } from "@/lib/admin-data-config";
import { apiFetch, queryString, type CompetitorDetail } from "@/lib/api";

interface CompetitorListItem extends AdminDataItem {
  name: string;
  website_url: string | null;
  color: string;
  description: string | null;
  is_active: boolean;
  primary_site_name: string | null;
  primary_site_city: string | null;
  site_count: number;
  customer_count: number;
  linked_customer_count: number;
  pending_link_count: number;
  deal_count: number;
  total_amount: string;
  strength_region_count: number;
  strength_regions: string[];
  created_at: string;
  updated_at: string;
}

interface CompetitorListPage {
  items: CompetitorListItem[];
  total: number;
  page: number;
  page_size: number;
}

type DetailTab = "sites" | "customers" | "regions";
const pageSizeOptions = [10, 25, 50, 75, 100];
const competitorConfigs = ADMIN_SECTION_CONFIGS.competitors.resources;

/** 按资源键读取现有完整字段配置，保证专用页面不复制业务字段定义。 */
function resourceConfig(key: string): AdminResourceConfig {
  const config = competitorConfigs.find((item) => item.key === key);
  if (!config) throw new Error(`缺少同行资源配置：${key}`);
  return config;
}

/** 使用中国地区格式显示金额，异常值回退为零。 */
function currency(value: string | number): string {
  return `¥${Number(value || 0).toLocaleString("zh-CN", { maximumFractionDigits: 2 })}`;
}

/** 显示删除同行的级联影响，避免管理员误以为只会移除主档名称。 */
function CompetitorDeleteDialog({ item, onCancel, onConfirm }: { item: CompetitorListItem; onCancel: () => void; onConfirm: () => Promise<void> }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { const dialog = dialogRef.current; dialog?.showModal(); return () => { if (dialog?.open) dialog.close(); }; }, []);

  /** 二次确认后删除完整同行档案，失败时保留对话框和恢复信息。 */
  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setDeleting(true); setError(null);
    try { await onConfirm(); } catch (deleteError) { setError(deleteError instanceof Error ? deleteError.message : "删除失败，请稍后重试"); setDeleting(false); }
  }

  return <dialog ref={dialogRef} className="organization-delete-dialog" aria-labelledby="competitor-delete-title" onCancel={(event) => { event.preventDefault(); if (!deleting) onCancel(); }}><form onSubmit={confirm}><div className="delete-dialog-icon"><Trash2 size={22} /></div><h2 id="competitor-delete-title">确认删除同行？</h2><p>“{item.name}”及其 {item.site_count} 个据点、{item.customer_count} 个成交单位、{item.deal_count} 笔交易和 {item.strength_region_count} 条人工区域将永久删除。</p>{error ? <p className="organization-dialog-error" role="alert"><CircleAlert size={16} />{error}</p> : null}<footer><button type="button" className="organization-dialog-cancel" onClick={onCancel} disabled={deleting} autoFocus>取消</button><button className="organization-dialog-delete" disabled={deleting}><Trash2 size={16} />{deleting ? "正在删除…" : "确认删除"}</button></footer></form></dialog>;
}

interface ResourcePanelProps {
  configKey: string;
  ownerField: "competitor_id" | "competitor_customer_id";
  ownerId: string;
  listFields: string[];
  emptyText: string;
  maxRecords?: number;
  onChanged: () => void;
  onManage?: (item: AdminDataItem) => void;
}

/** 在详情分区内分页维护一种子资源，并通过隐藏父键确保新增记录归属当前档案。 */
function CompetitorResourcePanel({ configKey, ownerField, ownerId, listFields, emptyText, maxRecords, onChanged, onManage }: ResourcePanelProps) {
  const baseConfig = resourceConfig(configKey);
  const config = useMemo(() => ({ ...baseConfig, filters: { ...baseConfig.filters, [ownerField]: ownerId } }), [baseConfig, ownerField, ownerId]);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search.trim());
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [page, setPage] = useState<AdminDataPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<AdminDataItem | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AdminDataItem | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const fields = listFields.map((name) => config.fields.find((field) => field.name === name) ?? { name, label: name, kind: "text" as const });
  const totalPages = Math.max(1, Math.ceil((page?.total ?? 0) / pageSize));

  useEffect(() => { if (!notice) return; const timer = window.setTimeout(() => setNotice(null), 2200); return () => window.clearTimeout(timer); }, [notice]);

  /** 取消旧请求并读取当前父记录下的一页子资源。 */
  const loadPage = useCallback(async () => {
    abortRef.current?.abort(); const controller = new AbortController(); abortRef.current = controller;
    setLoading(true); setError(null);
    try {
      const result = await apiFetch<AdminDataPage>(`/admin-data/${configKey}${queryString({ page: String(currentPage), page_size: String(pageSize), search: debouncedSearch || undefined, parent_id: ownerId })}`, { signal: controller.signal });
      if (!controller.signal.aborted) setPage(result);
    } catch (requestError) {
      if (!(requestError instanceof DOMException && requestError.name === "AbortError")) setError(requestError instanceof Error ? requestError.message : `无法加载${config.label}`);
    } finally { if (!controller.signal.aborted) setLoading(false); }
  }, [config.label, configKey, currentPage, debouncedSearch, ownerId, pageSize]);

  useEffect(() => { const timer = window.setTimeout(() => void loadPage(), 0); return () => window.clearTimeout(timer); }, [loadPage]);
  useEffect(() => () => abortRef.current?.abort(), []);

  /** 新增或完整编辑当前子资源，随后刷新本分区和同行汇总。 */
  async function saveRecord(payload: Record<string, unknown>, item: AdminDataItem | null) {
    const path = item ? `/admin-data/${configKey}/${item.id}` : `/admin-data/${configKey}`;
    await apiFetch(path, { method: item ? "PUT" : "POST", body: JSON.stringify({ data: payload }) });
    setEditing(null); setCreating(false); setNotice(`已${item ? "保存" : "添加"}${config.singular}`);
    await loadPage(); onChanged();
  }

  /** 删除一条子资源，并在删除当前页末项时自动回到有效页。 */
  async function deleteRecord() {
    if (!deleteTarget) return;
    await apiFetch(`/admin-data/${configKey}/${deleteTarget.id}`, { method: "DELETE" });
    setDeleteTarget(null); setNotice(`已删除${config.singular}`); onChanged();
    if ((page?.items.length ?? 0) === 1 && currentPage > 1) setCurrentPage((value) => value - 1); else await loadPage();
  }

  return <section className="competitor-resource-panel" aria-label={config.label}>
    <div className="competitor-resource-heading"><div><h3>{config.label}</h3><p>{config.description}</p></div><button className="organization-create-button" onClick={() => setCreating(true)} disabled={maxRecords !== undefined && (page?.total ?? 0) >= maxRecords}><Plus size={15} />添加{config.label}</button></div>
    <label className="admin-data-search competitor-resource-search"><Search size={15} /><input aria-label={`搜索${config.label}`} value={search} onChange={(event) => { setSearch(event.target.value); setCurrentPage(1); }} placeholder={`搜索${config.label}`} /></label>
    {notice ? <p className="admin-page-notice"><Check size={15} />{notice}</p> : null}{error ? <p className="admin-page-error" role="alert"><CircleAlert size={15} />{error}</p> : null}
    <div className="competitor-resource-table" role="table" aria-busy={loading}>
      <div className="competitor-resource-row competitor-resource-row-head" role="row">{fields.map((field) => <span key={field.name} role="columnheader">{field.label}</span>)}<span role="columnheader">操作</span></div>
      {page?.items.map((item) => <div className="competitor-resource-row" role="row" key={item.id}>{fields.map((field, index) => <span key={field.name} role="cell" className={index === 0 ? "admin-data-primary-cell" : undefined}>{displayValue(item, field)}</span>)}<div className="organization-row-actions" role="cell">{onManage ? <button className="competitor-manage-action" onClick={() => onManage(item)}><Link2 size={14} />交易与关联</button> : null}<button className="organization-edit-action" onClick={() => setEditing(item)}><Pencil size={14} />修改</button><button className="organization-delete-action" onClick={() => setDeleteTarget(item)}><Trash2 size={14} />删除</button></div></div>)}
    </div>
    {loading ? <div className="admin-data-state" role="status">正在读取{config.label}…</div> : null}
    {!loading && page?.items.length === 0 ? <div className="organization-empty"><Database size={19} />{emptyText}</div> : null}
    {page ? <nav className="organization-pagination competitor-resource-pagination" aria-label={`${config.label}分页`}><span>第 {currentPage} / {totalPages} 页 · 共 {page.total.toLocaleString("zh-CN")} 条</span><div><label className="organization-page-size">每页<select aria-label={`每页显示${config.label}数`} value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setCurrentPage(1); }}>{pageSizeOptions.map((size) => <option key={size} value={size}>{size} 条</option>)}</select></label><button type="button" onClick={() => setCurrentPage((value) => Math.max(1, value - 1))} disabled={currentPage === 1}>上一页</button><button type="button" onClick={() => setCurrentPage((value) => Math.min(totalPages, value + 1))} disabled={currentPage === totalPages}>下一页</button></div></nav> : null}
    {creating ? <AdminDataFormDialog config={config} item={null} hiddenFields={[ownerField]} onCancel={() => setCreating(false)} onSaved={(payload) => saveRecord(payload, null)} /> : null}
    {editing ? <AdminDataFormDialog key={editing.id} config={config} item={editing} hiddenFields={[ownerField]} onCancel={() => setEditing(null)} onSaved={(payload) => saveRecord(payload, editing)} /> : null}
    {deleteTarget ? <AdminDataDeleteDialog key={deleteTarget.id} config={config} item={deleteTarget} onCancel={() => setDeleteTarget(null)} onConfirm={deleteRecord} /> : null}
  </section>;
}

/** 在详情工作区按需组合据点、客户交易关联和两类强势区域。 */
function CompetitorDetailWorkspace({ competitor, onBack, onEdit, onDelete, onChanged }: { competitor: CompetitorListItem; onBack: () => void; onEdit: () => void; onDelete: () => void; onChanged: () => void }) {
  const [activeTab, setActiveTab] = useState<DetailTab>("sites");
  const [selectedCustomer, setSelectedCustomer] = useState<AdminDataItem | null>(null);
  const [computed, setComputed] = useState<CompetitorDetail | null>(null);
  const [computedLoading, setComputedLoading] = useState(false);
  const [computedError, setComputedError] = useState<string | null>(null);

  useEffect(() => {
    if (activeTab !== "regions" || computed) return;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setComputedLoading(true); setComputedError(null);
      void apiFetch<CompetitorDetail>(`/public/competitors/${competitor.id}`, { signal: controller.signal })
        .then(setComputed)
        .catch((error: unknown) => { if (!(error instanceof DOMException && error.name === "AbortError")) setComputedError(error instanceof Error ? error.message : "无法计算强势区域"); })
        .finally(() => { if (!controller.signal.aborted) setComputedLoading(false); });
    }, 0);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [activeTab, computed, competitor.id]);

  /** 切换详情分区时关闭仅属于成交单位的二级工作区。 */
  function changeTab(tab: DetailTab) { setActiveTab(tab); if (tab !== "customers") setSelectedCustomer(null); }

  /** 子资源变化后同时刷新列表摘要并使公开区域快照失效。 */
  function handleResourceChanged() {
    setComputed(null);
    onChanged();
  }

  return <section className="admin-data-workspace competitor-detail-workspace" aria-label={`${competitor.name}同行档案`}>
    <button className="competitor-back-button" onClick={onBack}><ArrowLeft size={16} />返回同行列表</button>
    <div className="competitor-detail-header"><div className="competitor-detail-main"><div className="competitor-detail-identity"><i style={{ background: competitor.color }} /><div><h2>{competitor.name}</h2><p>{competitor.description || "暂无同行说明"}</p>{competitor.website_url ? <a className="competitor-detail-website" href={competitor.website_url} target="_blank" rel="noreferrer"><Link2 size={13} />公司官网</a> : <small className="competitor-detail-website is-empty">官网未填写</small>}</div><span className={competitor.is_active ? "is-active" : "is-inactive"}>{competitor.is_active ? "启用" : "停用"}</span></div><div className="competitor-summary-strip" aria-label="同行档案摘要"><span><MapPin size={15} /><b>{competitor.site_count}</b> 个据点</span><span><Building2 size={15} /><b>{competitor.customer_count}</b> 个成交单位</span><span><Link2 size={15} /><b>{competitor.linked_customer_count}</b> 个正式关联</span><span><b>{competitor.deal_count}</b> 笔交易 · {currency(competitor.total_amount)}</span></div></div><div className="organization-row-actions"><button className="organization-edit-action" onClick={onEdit}><Pencil size={14} />修改主档</button><button className="organization-delete-action" onClick={onDelete}><Trash2 size={14} />删除</button></div></div>
    <nav className="competitor-detail-tabs" role="tablist" aria-label="同行档案分区"><button role="tab" aria-selected={activeTab === "sites"} className={activeTab === "sites" ? "selected" : ""} onClick={() => changeTab("sites")}>基本资料与据点</button><button role="tab" aria-selected={activeTab === "customers"} className={activeTab === "customers" ? "selected" : ""} onClick={() => changeTab("customers")}>成交单位与交易</button><button role="tab" aria-selected={activeTab === "regions"} className={activeTab === "regions" ? "selected" : ""} onClick={() => changeTab("regions")}>强势区域</button></nav>
    {activeTab === "sites" ? <CompetitorResourcePanel configKey="competitor_sites" ownerField="competitor_id" ownerId={competitor.id} listFields={["name", "site_type", "city", "is_primary"]} emptyText="暂无据点，可以添加总部、分部或服务点。" onChanged={handleResourceChanged} /> : null}
    {activeTab === "customers" ? <div className="competitor-customer-workspace"><CompetitorResourcePanel configKey="competitor_customers" ownerField="competitor_id" ownerId={competitor.id} listFields={["name", "customer_level", "city", "confidence"]} emptyText="暂无同行成交单位，可以从已核验情报开始录入。" onChanged={handleResourceChanged} onManage={setSelectedCustomer} />{selectedCustomer ? <section className="competitor-customer-detail" aria-label={`${String(selectedCustomer.name)}交易与关联`}><div className="competitor-customer-detail-heading"><div><h3>{String(selectedCustomer.name)}</h3><p>只显示当前成交单位的逐笔交易和正式目标单位关联。</p></div><button onClick={() => setSelectedCustomer(null)}>关闭</button></div><CompetitorResourcePanel configKey="competitor_deals" ownerField="competitor_customer_id" ownerId={selectedCustomer.id} listFields={["project_name", "products", "amount", "signed_at"]} emptyText="暂无逐笔交易记录。" onChanged={handleResourceChanged} /><CompetitorResourcePanel configKey="competitor_links" ownerField="competitor_customer_id" ownerId={selectedCustomer.id} listFields={["organization_id", "match_status", "match_method", "match_confidence"]} emptyText="尚未关联全国目标单位。" maxRecords={1} onChanged={handleResourceChanged} /></section> : null}</div> : null}
    {activeTab === "regions" ? <div className="competitor-region-workspace"><CompetitorResourcePanel configKey="competitor_strength_regions" ownerField="competitor_id" ownerId={competitor.id} listFields={["province", "city", "strength_level", "confidence"]} emptyText="暂无人工确认区域，可以录入省级或市级判断。" onChanged={handleResourceChanged} /><section className="competitor-computed-regions"><div><h3>公开地图计算结果</h3><p>依据据点、成交单位和交易金额自动计算，仅供查看；人工区域仍在上方维护。</p></div>{computedLoading ? <div className="admin-data-state" role="status">正在计算强势区域…</div> : null}{computedError ? <p className="admin-page-error" role="alert"><CircleAlert size={15} />{computedError}</p> : null}{computed && computed.strength_regions.length === 0 ? <div className="organization-empty">当前数据不足以计算强势区域。</div> : null}<div className="competitor-computed-region-list">{computed?.strength_regions.map((region) => <article key={region.id}><strong>{region.province}{region.city ? ` · ${region.city}` : ""}</strong><span className={`strength-${region.strength_level}`}>{region.strength_level}</span><p>得分 {region.score} · {region.site_count} 个据点 · {region.customer_count} 个单位 · {currency(region.total_amount)}</p></article>)}</div></section></div> : null}
  </section>;
}

/** 同行页面：维护唯一主列表，并把复杂子数据放入选中同行的原位详情工作区。 */
export function AdminCompetitorWorkspace() {
  const mainConfig = resourceConfig("competitors");
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebouncedValue(search.trim());
  const [activeFilter, setActiveFilter] = useState("all");
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [page, setPage] = useState<CompetitorListPage | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<CompetitorListItem | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<CompetitorListItem | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const selected = page?.items.find((item) => item.id === selectedId) ?? null;
  const totalPages = Math.max(1, Math.ceil((page?.total ?? 0) / pageSize));

  useEffect(() => { if (!notice) return; const timer = window.setTimeout(() => setNotice(null), 2200); return () => window.clearTimeout(timer); }, [notice]);

  /** 读取同行聚合页；详情子资源变化后复用该函数刷新摘要。 */
  const loadPage = useCallback(async () => {
    abortRef.current?.abort(); const controller = new AbortController(); abortRef.current = controller;
    setLoading(true); setError(null);
    try {
      const result = await apiFetch<CompetitorListPage>(`/admin-competitors${queryString({ page: String(currentPage), page_size: String(pageSize), search: debouncedSearch || undefined, is_active: activeFilter === "all" ? undefined : activeFilter })}`, { signal: controller.signal });
      if (!controller.signal.aborted) setPage(result);
    } catch (requestError) {
      if (!(requestError instanceof DOMException && requestError.name === "AbortError")) setError(requestError instanceof Error ? requestError.message : "无法加载同行列表");
    } finally { if (!controller.signal.aborted) setLoading(false); }
  }, [activeFilter, currentPage, debouncedSearch, pageSize]);

  useEffect(() => { const timer = window.setTimeout(() => void loadPage(), 0); return () => window.clearTimeout(timer); }, [loadPage]);
  useEffect(() => () => abortRef.current?.abort(), []);

  /** 新增或编辑同行主档，并同步当前详情头部与聚合列表。 */
  async function saveCompetitor(payload: Record<string, unknown>, item: CompetitorListItem | null) {
    const path = item ? `/admin-data/competitors/${item.id}` : "/admin-data/competitors";
    const saved = await apiFetch<AdminDataItem>(path, { method: item ? "PUT" : "POST", body: JSON.stringify({ data: payload }) });
    if (item) setPage((current) => current ? { ...current, items: current.items.map((row) => row.id === item.id ? { ...row, ...saved } as CompetitorListItem : row) } : current);
    setEditing(null); setCreating(false); setNotice(`已${item ? "保存" : "添加"}同行`); await loadPage();
  }

  /** 删除同行及其数据库级联明细，并修正分页或退出已删除详情。 */
  async function deleteCompetitor() {
    if (!deleteTarget) return;
    await apiFetch(`/admin-data/competitors/${deleteTarget.id}`, { method: "DELETE" });
    if (selectedId === deleteTarget.id) setSelectedId(null);
    setDeleteTarget(null); setNotice("已删除同行档案");
    if ((page?.items.length ?? 0) === 1 && currentPage > 1) setCurrentPage((value) => value - 1); else await loadPage();
  }

  if (selected) return <>{notice ? <p className="admin-page-notice"><Check size={16} />{notice}</p> : null}<CompetitorDetailWorkspace competitor={selected} onBack={() => setSelectedId(null)} onEdit={() => setEditing(selected)} onDelete={() => setDeleteTarget(selected)} onChanged={() => void loadPage()} />{editing ? <AdminDataFormDialog key={editing.id} config={mainConfig} item={editing} onCancel={() => setEditing(null)} onSaved={(payload) => saveCompetitor(payload, editing)} /> : null}{deleteTarget ? <CompetitorDeleteDialog item={deleteTarget} onCancel={() => setDeleteTarget(null)} onConfirm={deleteCompetitor} /> : null}</>;

  return <section className="admin-data-workspace competitor-admin-workspace" aria-label="同行数据管理">
    <div className="admin-data-toolbar"><label className="admin-data-search"><Search size={16} /><input aria-label="搜索同行" value={search} onChange={(event) => { setSearch(event.target.value); setCurrentPage(1); }} placeholder="搜索同行名称或说明" /></label><label className="admin-data-resource-select"><span>状态</span><select aria-label="按同行状态筛选" value={activeFilter} onChange={(event) => { setActiveFilter(event.target.value); setCurrentPage(1); }}><option value="all">全部同行</option><option value="true">仅启用</option><option value="false">仅停用</option></select></label></div>
    {notice ? <p className="admin-page-notice"><Check size={16} />{notice}</p> : null}{error ? <p className="admin-page-error" role="alert"><CircleAlert size={16} />{error}</p> : null}
    <div className="organization-list-card admin-data-list-card competitor-admin-list-card"><div className="card-title"><div><h2>{page?.total.toLocaleString("zh-CN") ?? "—"} 个同行</h2><p>在一张列表查看业务规模；进入档案后维护据点、成交单位、逐笔交易、正式关联和强势区域。</p></div><button className="organization-create-button" onClick={() => setCreating(true)}><Plus size={15} />添加同行</button></div>
      <div className="admin-data-table competitor-admin-table" role="table" aria-busy={loading}><div className="admin-data-row admin-data-row-head" role="row"><span role="columnheader">同行</span><span role="columnheader">主要据点</span><span role="columnheader">业务规模</span><span role="columnheader">成交概览</span><span role="columnheader">强势区域</span><span role="columnheader">操作</span></div>{page?.items.map((item) => <div className="admin-data-row" role="row" key={item.id}><div className="competitor-list-name" role="cell"><i style={{ background: item.color }} /><strong>{item.name}</strong><span className={item.is_active ? "is-active" : "is-inactive"}>{item.is_active ? "启用" : "停用"}</span><small>{item.description || "暂无说明"}</small></div><div className="competitor-primary-site" role="cell"><strong>{item.primary_site_name || "未设置"}</strong><span>{item.primary_site_city || "暂无主要据点"}</span></div><div className="competitor-scale" role="cell"><span><b>{item.site_count}</b> 据点</span><span><b>{item.customer_count}</b> 单位</span><span><b>{item.linked_customer_count}</b> 已关联</span>{item.pending_link_count ? <span><b>{item.pending_link_count}</b> 待确认</span> : null}</div><div className="competitor-deals" role="cell"><strong>{currency(item.total_amount)}</strong><span>{item.deal_count} 笔交易</span></div><div className="competitor-region-tags" role="cell">{item.strength_regions.map((region) => <span key={region}>{region}</span>)}{item.strength_region_count > item.strength_regions.length ? <em>+{item.strength_region_count - item.strength_regions.length}</em> : null}{item.strength_region_count === 0 ? <small>未录入</small> : null}</div><div className="organization-row-actions competitor-list-actions" role="cell"><button className="organization-edit-action" onClick={() => setSelectedId(item.id)}><Pencil size={14} />修改</button><button className="organization-delete-action" onClick={() => setDeleteTarget(item)}><Trash2 size={14} />删除</button></div></div>)}</div>
      {loading ? <div className="admin-data-state" role="status">正在读取同行列表…</div> : null}{!loading && page?.items.length === 0 ? <div className="organization-empty"><Building2 size={21} />暂无匹配同行，可以清除筛选或添加第一条档案。</div> : null}
      {page ? <nav className="organization-pagination" aria-label="同行列表分页"><span>第 {currentPage} / {totalPages} 页 · 共 {page.total.toLocaleString("zh-CN")} 条</span><div><label className="organization-page-size">每页<select aria-label="每页显示同行数" value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setCurrentPage(1); }}>{pageSizeOptions.map((size) => <option value={size} key={size}>{size} 条</option>)}</select></label><button type="button" onClick={() => setCurrentPage((value) => Math.max(1, value - 1))} disabled={currentPage === 1}>上一页</button><button type="button" onClick={() => setCurrentPage((value) => Math.min(totalPages, value + 1))} disabled={currentPage === totalPages}>下一页</button></div></nav> : null}
    </div>
    {creating ? <AdminDataFormDialog config={mainConfig} item={null} onCancel={() => setCreating(false)} onSaved={(payload) => saveCompetitor(payload, null)} /> : null}{deleteTarget ? <CompetitorDeleteDialog item={deleteTarget} onCancel={() => setDeleteTarget(null)} onConfirm={deleteCompetitor} /> : null}
  </section>;
}
