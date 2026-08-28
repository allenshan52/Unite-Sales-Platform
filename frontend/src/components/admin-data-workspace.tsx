"use client";

/** 通用管理员数据工作台：按配置复用分页列表、外键搜索、完整字段表单和删除确认。 */

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Check, CircleAlert, Database, Pencil, Plus, Save, Search, Trash2, X } from "lucide-react";

import { apiFetch, queryString } from "@/lib/api";
import { AdminProductItemsEditor, productItemFromApi, productItemPayload, type ProductItemDraft } from "@/components/admin-product-items-editor";
import { useDebouncedValue } from "@/hooks/use-debounced-value";
import {
  ADMIN_SECTION_CONFIGS,
  type AdminFieldConfig,
  type AdminResourceConfig,
  type AdminSection,
} from "@/lib/admin-data-config";

type DataSection = Exclude<AdminSection, "organizations" | "deals" | "groups" | "cases" | "accounts">;
export type AdminDataItem = Record<string, unknown> & { id: string };
type FormValue = string | boolean | ProductItemDraft[];
type FormValues = Record<string, FormValue>;

export interface AdminDataPage {
  items: AdminDataItem[];
  total: number;
  page: number;
  page_size: number;
}

interface AdminDataOption {
  value: string;
  label: string;
}

const pageSizeOptions = [10, 25, 50, 75, 100];

/** 把服务端时间转换为 datetime-local 使用的本地文本。 */
function localDateTimeValue(value: unknown): string {
  if (!value) return "";
  const date = new Date(String(value));
  if (Number.isNaN(date.getTime())) return "";
  const local = new Date(date.getTime() - date.getTimezoneOffset() * 60_000);
  return local.toISOString().slice(0, 16);
}

/** 从新建默认值或既有记录生成隔离表单，取消时不会修改列表对象。 */
function initialFormValues(config: AdminResourceConfig, item: AdminDataItem | null): FormValues {
  return Object.fromEntries(config.fields.map((field) => {
    const value = item?.[field.name];
    if (value === undefined && config.filters?.[field.name] !== undefined) return [field.name, config.filters[field.name]];
    if (field.kind === "checkbox") return [field.name, typeof value === "boolean" ? value : Boolean(field.defaultValue)];
    if (field.kind === "product-list") return [field.name, Array.isArray(value) ? value.map((item) => productItemFromApi(item as Record<string, unknown>)) : []];
    if (field.kind === "string-list") return [field.name, Array.isArray(value) ? value.join("\n") : ""];
    if (field.kind === "datetime") return [field.name, localDateTimeValue(value)];
    if (field.kind === "date" && value) return [field.name, String(value).slice(0, 10)];
    if (value !== null && value !== undefined) return [field.name, String(value)];
    if (field.defaultValue !== undefined) return [field.name, String(field.defaultValue)];
    if (field.kind === "select" && field.required) return [field.name, field.options?.[0] ?? ""];
    return [field.name, ""];
  }));
}

/** 将浏览器表单转换为资源专属 JSON，空可选字段统一发送 null。 */
function payloadFromValues(config: AdminResourceConfig, values: FormValues): Record<string, unknown> {
  return Object.fromEntries(config.fields.map((field) => {
    const value = values[field.name];
    if (field.kind === "checkbox") return [field.name, Boolean(value)];
    if (field.kind === "product-list") return [field.name, Array.isArray(value) ? value.map(productItemPayload) : []];
    const text = String(value ?? "").trim();
    if (field.kind === "number") return [field.name, text ? Number(text) : null];
    if (field.kind === "string-list") {
      const items = text.split(/\r?\n/).map((item) => item.trim()).filter(Boolean);
      return [field.name, items.length ? items : null];
    }
    if (field.kind === "datetime") return [field.name, text ? new Date(text).toISOString() : null];
    return [field.name, text || (field.nullable ? null : "")];
  }));
}

/** 为列表单元格生成紧凑中文显示，保留原始表单值用于编辑。 */
export function displayValue(item: AdminDataItem, field: AdminFieldConfig): string {
  const foreignLabel = item[`${field.name}_label`];
  if (foreignLabel) return String(foreignLabel);
  const value = item[field.name];
  if (field.kind === "checkbox") return value ? "启用 / 是" : "停用 / 否";
  if (value === null || value === undefined || value === "") return "未填写";
  if (field.kind === "product-list" && Array.isArray(value)) return value.map((product) => String((product as Record<string, unknown>).product_name ?? "")).filter(Boolean).join("、") || "未填写";
  if (Array.isArray(value)) return value.join("、") || "未填写";
  if (field.kind === "datetime") return new Date(String(value)).toLocaleString("zh-CN", { hour12: false });
  if (field.kind === "date") return new Date(`${String(value).slice(0, 10)}T00:00:00`).toLocaleDateString("zh-CN");
  if (field.kind === "number" && /amount/.test(field.name)) return `¥${Number(value).toLocaleString("zh-CN", { maximumFractionDigits: 2 })}`;
  return String(value);
}

/** 外键搜索控件按输入词请求少量候选，避免一次加载两万条目标单位。 */
function ReferenceField({ field, value, onChange }: { field: AdminFieldConfig; value: string; onChange: (value: string) => void }) {
  const [search, setSearch] = useState("");
  const [options, setOptions] = useState<AdminDataOption[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!field.foreignResource) return;
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => {
      setLoading(true);
      void apiFetch<AdminDataOption[]>(`/admin-data/${field.foreignResource}/options${queryString({ search: search || undefined, selected_id: value || undefined })}`, { signal: controller.signal })
        .then(setOptions)
        .catch((error: unknown) => {
          if (!(error instanceof DOMException && error.name === "AbortError")) setOptions([]);
        })
        .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, 220);
    return () => { window.clearTimeout(timeoutId); controller.abort(); };
  }, [field.foreignResource, search, value]);

  return (
    <div className="admin-reference-field">
      <input aria-label={`搜索${field.label}`} value={search} onChange={(event) => setSearch(event.target.value)} placeholder={`搜索${field.label}`} />
      <select aria-label={field.label} value={value} onChange={(event) => onChange(event.target.value)} required={field.required}>
        <option value="">{loading ? "正在搜索…" : field.nullable ? "未选择" : "请选择"}</option>
        {options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
      </select>
    </div>
  );
}

/** 渲染一个完整业务字段，统一标签、帮助文案和必填语义。 */
function AdminDataField({ field, value, onChange }: { field: AdminFieldConfig; value: FormValue; onChange: (value: FormValue) => void }) {
  if (field.kind === "product-list") {
    return <AdminProductItemsEditor value={Array.isArray(value) ? value : []} onChange={onChange} showImage />;
  }
  if (field.kind === "checkbox") {
    return <label className="admin-data-checkbox"><input type="checkbox" checked={Boolean(value)} onChange={(event) => onChange(event.target.checked)} /><span>{field.label}</span></label>;
  }
  const textValue = String(value ?? "");
  let control;
  if (field.kind === "textarea" || field.kind === "string-list") {
    control = <textarea value={textValue} onChange={(event) => onChange(event.target.value)} required={field.required} maxLength={field.maxLength} rows={field.kind === "string-list" ? 4 : 5} />;
  } else if (field.kind === "select") {
    control = <select value={textValue} onChange={(event) => onChange(event.target.value)} required={field.required}><option value="">{field.nullable ? "未选择" : "请选择"}</option>{field.options?.map((option) => <option key={option}>{option}</option>)}</select>;
  } else if (field.kind === "foreign") {
    control = <ReferenceField field={field} value={textValue} onChange={onChange} />;
  } else {
    const inputType = field.kind === "datetime" ? "datetime-local" : field.kind;
    control = <input type={inputType} value={textValue} onChange={(event) => onChange(event.target.value)} required={field.required} step={field.step} min={field.min} max={field.max} maxLength={field.maxLength} />;
  }
  return <label className={field.wide ? "field-wide" : undefined}><span>{field.label}{field.required ? <b aria-hidden="true">*</b> : null}</span>{control}{field.help ? <small>{field.help}</small> : null}</label>;
}

/** 完整字段对话框：浏览器先校验必填和范围，后端继续执行权威业务校验。 */
export function AdminDataFormDialog({ config, item, hiddenFields = [], onCancel, onSaved }: { config: AdminResourceConfig; item: AdminDataItem | null; hiddenFields?: string[]; onCancel: () => void; onSaved: (payload: Record<string, unknown>) => Promise<void> }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [values, setValues] = useState<FormValues>(() => initialFormValues(config, item));
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { const dialog = dialogRef.current; dialog?.showModal(); return () => { if (dialog?.open) dialog.close(); }; }, []);

  /** 提交当前资源全部业务字段，失败时保留草稿供管理员修正。 */
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await onSaved(payloadFromValues(config, values));
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : "保存失败，请核对字段后重试");
      setSubmitting(false);
    }
  }

  return (
    <dialog ref={dialogRef} className="organization-edit-dialog admin-data-dialog" aria-labelledby="admin-data-dialog-title" onCancel={(event) => { event.preventDefault(); if (!submitting) onCancel(); }}>
      <form onSubmit={submit}>
        <header><div><span>{item ? "编辑完整记录" : "新增完整记录"}</span><h2 id="admin-data-dialog-title">{item ? `编辑${config.singular}` : `添加${config.singular}`}</h2><p>{config.description}</p></div><button type="button" onClick={onCancel} disabled={submitting} aria-label="关闭表单"><X size={18} /></button></header>
        <div className="organization-edit-body"><section><h3>全部业务字段</h3><div className="organization-edit-grid">{config.fields.filter((field) => !hiddenFields.includes(field.name)).map((field) => <AdminDataField key={field.name} field={field} value={values[field.name]} onChange={(value) => setValues((current) => ({ ...current, [field.name]: value }))} />)}</div></section></div>
        {error ? <p className="organization-dialog-error" role="alert"><CircleAlert size={16} />{error}</p> : null}
        <footer><button type="button" className="organization-dialog-cancel" onClick={onCancel} disabled={submitting}>取消</button><button className="organization-dialog-save" disabled={submitting}><Save size={16} />{submitting ? "正在保存…" : item ? "保存修改" : `添加${config.singular}`}</button></footer>
      </form>
    </dialog>
  );
}

/** 通用删除确认：明确关联约束可能阻止删除，并要求二次确认。 */
export function AdminDataDeleteDialog({ config, item, onCancel, onConfirm }: { config: AdminResourceConfig; item: AdminDataItem; onCancel: () => void; onConfirm: () => Promise<void> }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const titleField = config.fields.find((field) => field.name === config.listFields[0]);
  const title = titleField ? displayValue(item, titleField) : config.singular;

  useEffect(() => { const dialog = dialogRef.current; dialog?.showModal(); return () => { if (dialog?.open) dialog.close(); }; }, []);

  /** 删除当前记录；数据库关联冲突会在对话框内显示恢复建议。 */
  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setDeleting(true);
    setError(null);
    try { await onConfirm(); } catch (deleteError) { setError(deleteError instanceof Error ? deleteError.message : "删除失败，请稍后重试"); setDeleting(false); }
  }

  return <dialog ref={dialogRef} className="organization-delete-dialog" aria-labelledby="admin-data-delete-title" onCancel={(event) => { event.preventDefault(); if (!deleting) onCancel(); }}><form onSubmit={confirm}><div className="delete-dialog-icon"><Trash2 size={22} /></div><h2 id="admin-data-delete-title">确认删除{config.singular}？</h2><p>“{title}”将从数据库永久删除。存在关联记录时系统会阻止删除，请先处理依赖数据。</p>{error ? <p className="organization-dialog-error" role="alert"><CircleAlert size={16} />{error}</p> : null}<footer><button type="button" className="organization-dialog-cancel" onClick={onCancel} disabled={deleting} autoFocus>取消</button><button className="organization-dialog-delete" disabled={deleting}><Trash2 size={16} />{deleting ? "正在删除…" : "确认删除"}</button></footer></form></dialog>;
}

/** 非目标单位数据页：分类切换后复用同一分页、表格和 CRUD 交互。 */
export function AdminDataWorkspace({ section }: { section: DataSection }) {
  const sectionConfig = ADMIN_SECTION_CONFIGS[section];
  const [resourceKey, setResourceKey] = useState(sectionConfig.resources[0].key);
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
  const resourceConfig = useMemo(() => sectionConfig.resources.find((resource) => resource.key === resourceKey) ?? sectionConfig.resources[0], [resourceKey, sectionConfig.resources]);
  const totalPages = Math.max(1, Math.ceil((page?.total ?? 0) / pageSize));
  const apiResource = resourceConfig.resource ?? resourceConfig.key;
  const listFields = resourceConfig.listFields.map((name) => resourceConfig.fields.find((field) => field.name === name) ?? { name, label: name, kind: "text" as const });

  useEffect(() => { if (!notice) return; const timeoutId = window.setTimeout(() => setNotice(null), 2200); return () => window.clearTimeout(timeoutId); }, [notice]);

  /** 读取当前分类分页，并取消前一次尚未完成的请求。 */
  const loadPage = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch<AdminDataPage>(`/admin-data/${apiResource}${queryString({ page: String(currentPage), page_size: String(pageSize), search: debouncedSearch || undefined, ...resourceConfig.filters })}`, { signal: controller.signal });
      if (!controller.signal.aborted) setPage(result);
    } catch (requestError) {
      if (!(requestError instanceof DOMException && requestError.name === "AbortError")) setError(requestError instanceof Error ? requestError.message : "无法加载后台数据");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [apiResource, currentPage, debouncedSearch, pageSize, resourceConfig.filters]);

  useEffect(() => { const timeoutId = window.setTimeout(() => void loadPage(), 0); return () => window.clearTimeout(timeoutId); }, [loadPage]);
  useEffect(() => () => abortRef.current?.abort(), []);

  /** 切换子表时回到第一页并关闭旧资源对话框。 */
  function changeResource(nextKey: string) {
    setResourceKey(nextKey); setCurrentPage(1); setSearch(""); setPage(null); setEditing(null); setDeleteTarget(null); setCreating(false);
  }

  /** 新增或编辑后刷新当前分类，并保留安全的分页边界。 */
  async function saveRecord(payload: Record<string, unknown>, item: AdminDataItem | null) {
    const path = item ? `/admin-data/${apiResource}/${item.id}` : `/admin-data/${apiResource}`;
    await apiFetch<AdminDataItem>(path, { method: item ? "PUT" : "POST", body: JSON.stringify({ data: payload }) });
    setNotice(`已${item ? "保存" : "添加"}${resourceConfig.singular}`);
    await loadPage();
    setEditing(null); setCreating(false);
  }

  /** 永久删除确认项；删除当前页最后一条时退回上一页。 */
  async function deleteRecord() {
    if (!deleteTarget) return;
    await apiFetch<void>(`/admin-data/${apiResource}/${deleteTarget.id}`, { method: "DELETE" });
    setDeleteTarget(null); setNotice(`已删除${resourceConfig.singular}`);
    if ((page?.items.length ?? 0) === 1 && currentPage > 1) setCurrentPage((value) => value - 1); else await loadPage();
  }

  return (
    <section className="admin-data-workspace" aria-label={`${sectionConfig.label}数据管理`}>
      <div className="admin-data-toolbar">
        <label className="admin-data-search"><Search size={16} /><input aria-label={`搜索${resourceConfig.label}`} placeholder={`搜索${resourceConfig.label}`} value={search} onChange={(event) => { setSearch(event.target.value); setCurrentPage(1); }} /></label>
        <label className="admin-data-resource-select"><span>数据分类</span><select aria-label="选择数据分类" value={resourceKey} onChange={(event) => changeResource(event.target.value)}>{sectionConfig.resources.map((resource) => <option key={resource.key} value={resource.key}>{resource.label}</option>)}</select></label>
      </div>
      {notice ? <p className="admin-page-notice"><Check size={16} />{notice}</p> : null}
      {error ? <p className="admin-page-error" role="alert"><CircleAlert size={16} />{error}</p> : null}
      <div className="organization-list-card admin-data-list-card">
        <div className="card-title"><div><span>{resourceConfig.label}</span><h2>{page?.total.toLocaleString("zh-CN") ?? "—"} 条记录</h2><p>{resourceConfig.description}</p></div><button className="organization-create-button" onClick={() => setCreating(true)}><Plus size={15} />添加{resourceConfig.singular}</button></div>
        <div className="admin-data-table" role="table" aria-busy={loading}>
          <div className="admin-data-row admin-data-row-head" role="row">{listFields.map((field) => <span key={field.name} role="columnheader">{field.label}</span>)}<span role="columnheader">操作</span></div>
          {page?.items.map((item) => <div className="admin-data-row" role="row" key={item.id}>{listFields.map((field, index) => <span key={field.name} role="cell" className={index === 0 ? "admin-data-primary-cell" : undefined}>{displayValue(item, field)}</span>)}<div className="organization-row-actions" role="cell"><button className="organization-edit-action" onClick={() => setEditing(item)}><Pencil size={14} />修改</button><button className="organization-delete-action" onClick={() => setDeleteTarget(item)}><Trash2 size={14} />删除</button></div></div>)}
        </div>
        {loading ? <div className="admin-data-state" role="status">正在读取{resourceConfig.label}…</div> : null}
        {!loading && page?.items.length === 0 ? <div className="organization-empty"><Database size={21} />暂无匹配记录。可以清除搜索条件或添加第一条数据。</div> : null}
        {page ? <nav className="organization-pagination" aria-label={`${resourceConfig.label}分页`}><span>第 {currentPage} / {totalPages} 页 · 共 {page.total.toLocaleString("zh-CN")} 条</span><div><label className="organization-page-size">每页<select aria-label="每页显示记录数" value={pageSize} onChange={(event) => { setPageSize(Number(event.target.value)); setCurrentPage(1); }}>{pageSizeOptions.map((size) => <option key={size} value={size}>{size} 条</option>)}</select></label><button type="button" onClick={() => setCurrentPage((value) => Math.max(1, value - 1))} disabled={currentPage === 1}>上一页</button><button type="button" onClick={() => setCurrentPage((value) => Math.min(totalPages, value + 1))} disabled={currentPage === totalPages}>下一页</button></div></nav> : null}
      </div>
      {creating ? <AdminDataFormDialog config={resourceConfig} item={null} onCancel={() => setCreating(false)} onSaved={(payload) => saveRecord(payload, null)} /> : null}
      {editing ? <AdminDataFormDialog key={editing.id} config={resourceConfig} item={editing} onCancel={() => setEditing(null)} onSaved={(payload) => saveRecord(payload, editing)} /> : null}
      {deleteTarget ? <AdminDataDeleteDialog key={deleteTarget.id} config={resourceConfig} item={deleteTarget} onCancel={() => setDeleteTarget(null)} onConfirm={deleteRecord} /> : null}
    </section>
  );
}
