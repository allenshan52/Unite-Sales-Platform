"use client";

/** 典型案例管理工作台：固定展示 31 个省份入口，并在原位详情页维护完整案例与图片。 */

import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Image from "next/image";
import {
  ArrowDown,
  ArrowLeft,
  ArrowUp,
  Check,
  CircleAlert,
  ImagePlus,
  MapPin,
  Plus,
  Save,
  Search,
  Star,
  Trash2,
} from "lucide-react";

import {
  apiFetch,
  apiUpload,
  queryString,
  type TypicalCaseAdminDetail,
  type TypicalCaseAdminListItem,
  type TypicalCaseAdminOverview,
  type TypicalCaseAdminStatus,
  type TypicalCaseImage,
  type TypicalCaseImageUploadRead,
  type TypicalCaseInput,
  type TypicalCaseMetric,
  type TypicalCaseProjectOption,
} from "@/lib/api";

interface CaseForm {
  salesProjectId: string;
  city: string;
  title: string;
  subtitle: string;
  customerDisplayName: string;
  industryLabel: string;
  summary: string;
  challenge: string;
  solution: string;
  outcome: string;
  productScope: string;
  customerQuote: string;
  quoteAttribution: string;
  showContractAmount: boolean;
  isPublished: boolean;
  isFeatured: boolean;
  images: TypicalCaseImage[];
  metrics: TypicalCaseMetric[];
}

const statusOptions: Array<TypicalCaseAdminStatus | "全部"> = ["全部", "未配置", "草稿", "已上线"];

/** 创建一个省份已锁定、其余字段待管理员补齐的新案例草稿。 */
function emptyForm(): CaseForm {
  return {
    salesProjectId: "", city: "", title: "", subtitle: "", customerDisplayName: "", industryLabel: "",
    summary: "", challenge: "", solution: "", outcome: "", productScope: "", customerQuote: "",
    quoteAttribution: "", showContractAmount: false, isPublished: false, isFeatured: false, images: [], metrics: [],
  };
}

/** 将后端完整详情转换成受控表单，避免列表摘要承担编辑数据源。 */
function detailToForm(detail: TypicalCaseAdminDetail): CaseForm {
  return {
    salesProjectId: detail.sales_project_id ?? "", city: detail.city, title: detail.title, subtitle: detail.subtitle ?? "",
    customerDisplayName: detail.customer_display_name, industryLabel: detail.industry_label, summary: detail.summary,
    challenge: detail.challenge, solution: detail.solution, outcome: detail.outcome, productScope: detail.product_scope,
    customerQuote: detail.customer_quote ?? "", quoteAttribution: detail.quote_attribution ?? "",
    showContractAmount: detail.show_contract_amount, isPublished: detail.is_published, isFeatured: detail.is_featured,
    images: detail.images, metrics: detail.metrics,
  };
}

/** 把编辑状态整理为一次原子写入的后端合同。 */
function formToPayload(form: CaseForm, slot: TypicalCaseAdminListItem): TypicalCaseInput {
  const optional = (value: string) => value.trim() || null;
  return {
    sales_project_id: form.salesProjectId || null,
    province: slot.province,
    province_adcode: slot.province_adcode,
    city: form.city.trim(),
    title: form.title.trim(),
    subtitle: optional(form.subtitle),
    customer_display_name: form.customerDisplayName.trim(),
    industry_label: form.industryLabel.trim(),
    summary: form.summary.trim(),
    challenge: form.challenge.trim(),
    solution: form.solution.trim(),
    outcome: form.outcome.trim(),
    product_scope: form.productScope.trim(),
    customer_quote: optional(form.customerQuote),
    quote_attribution: optional(form.quoteAttribution),
    show_contract_amount: form.showContractAmount,
    is_published: form.isPublished,
    is_featured: form.isFeatured,
    images: form.images.map((image) => ({ ...image, caption: image.caption?.trim() || null })),
    metrics: form.metrics.map((metric) => ({ ...metric, unit: metric.unit?.trim() || null, note: metric.note?.trim() || null })),
  };
}

/** 统一显示中国地区日期，未配置记录保留明确占位。 */
function displayDate(value: string | null): string {
  return value ? new Intl.DateTimeFormat("zh-CN", { dateStyle: "medium" }).format(new Date(value)) : "尚未配置";
}

/** 删除案例必须经过原生模态确认，明确数据会恢复为未配置槽位。 */
function CaseDeleteDialog({ province, deleting, error, onCancel, onConfirm }: { province: string; deleting: boolean; error: string | null; onCancel: () => void; onConfirm: () => void }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => { const dialog = dialogRef.current; dialog?.showModal(); return () => { if (dialog?.open) dialog.close(); }; }, []);
  return <dialog ref={dialogRef} className="organization-delete-dialog" aria-labelledby="case-delete-title" onCancel={(event) => { event.preventDefault(); if (!deleting) onCancel(); }}><form onSubmit={(event) => { event.preventDefault(); onConfirm(); }}><div className="delete-dialog-icon"><Trash2 size={22} /></div><h2 id="case-delete-title">确认删除{province}案例？</h2><p>案例正文、图片引用和展示指标会从数据库删除；该省份仍保留在列表中，并恢复为“未配置”。已上传的图片文件不会自动删除。</p>{error ? <p className="organization-dialog-error" role="alert"><CircleAlert size={16} />{error}</p> : null}<footer><button type="button" className="organization-dialog-cancel" onClick={onCancel} disabled={deleting} autoFocus>取消</button><button className="organization-dialog-delete" disabled={deleting}><Trash2 size={16} />{deleting ? "正在删除…" : "确认删除"}</button></footer></form></dialog>;
}

/** 固定省份列表与完整编辑页共用一个工作区，不创建独立的草稿或发布列表。 */
export function AdminTypicalCaseWorkspace() {
  const [overview, setOverview] = useState<TypicalCaseAdminOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<TypicalCaseAdminStatus | "全部">("全部");
  const [slot, setSlot] = useState<TypicalCaseAdminListItem | null>(null);
  const [form, setForm] = useState<CaseForm | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [projectSearch, setProjectSearch] = useState("");
  const [projectOptions, setProjectOptions] = useState<TypicalCaseProjectOption[]>([]);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);
  const [initialSnapshot, setInitialSnapshot] = useState("");

  /** 重新读取轻量 31 省列表及状态统计。 */
  const loadOverview = useCallback(async () => {
    setLoading(true); setError(null);
    try { setOverview(await apiFetch<TypicalCaseAdminOverview>("/admin-typical-cases")); }
    catch (requestError) { setError(requestError instanceof Error ? requestError.message : "无法读取典型案例列表"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => void loadOverview(), 0);
    return () => window.clearTimeout(timeoutId);
  }, [loadOverview]);

  const dirty = Boolean(form && initialSnapshot && JSON.stringify(form) !== initialSnapshot);
  useEffect(() => {
    /** 浏览器离开时保护尚未保存的长表单。 */
    function warnBeforeUnload(event: BeforeUnloadEvent) { if (dirty) event.preventDefault(); }
    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [dirty]);

  useEffect(() => {
    if (!slot) return;
    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      void apiFetch<TypicalCaseProjectOption[]>(`/admin-typical-cases/project-options${queryString({ province: slot.province, search: projectSearch || undefined, selected_id: form?.salesProjectId || undefined })}`, { signal: controller.signal })
        .then(setProjectOptions)
        .catch((requestError) => { if (!(requestError instanceof DOMException && requestError.name === "AbortError")) setError(requestError instanceof Error ? requestError.message : "无法读取成交项目"); });
    }, 220);
    return () => { controller.abort(); window.clearTimeout(timeout); };
  }, [form?.salesProjectId, projectSearch, slot]);

  const filteredItems = useMemo(() => (overview?.items ?? []).filter((item) => {
    const keyword = search.trim().toLocaleLowerCase("zh-CN");
    const matchesStatus = status === "全部" || item.status === status;
    const haystack = [item.province, item.city, item.title, item.customer_display_name, item.industry_label].filter(Boolean).join(" ").toLocaleLowerCase("zh-CN");
    return matchesStatus && (!keyword || haystack.includes(keyword));
  }), [overview, search, status]);

  /** 点击省份后才读取完整详情；未配置省份直接创建本地空表单。 */
  async function openCase(item: TypicalCaseAdminListItem) {
    setSlot(item); setNotice(null); setError(null); setProjectSearch(""); setProjectOptions([]);
    if (!item.id) {
      const next = emptyForm(); setForm(next); setInitialSnapshot(JSON.stringify(next)); return;
    }
    setDetailLoading(true); setForm(null);
    try {
      const detail = await apiFetch<TypicalCaseAdminDetail>(`/admin-typical-cases/${item.id}`);
      const next = detailToForm(detail); setForm(next); setInitialSnapshot(JSON.stringify(next));
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "无法读取案例详情"); }
    finally { setDetailLoading(false); }
  }

  /** 返回唯一列表前检查未保存改动。 */
  function closeDetail() {
    if (dirty && !window.confirm("当前修改尚未保存，确定返回省份列表吗？")) return;
    setSlot(null); setForm(null); setProjectOptions([]); setInitialSnapshot(""); setError(null);
  }

  /** 保存新建或现有案例，成功后保持详情打开并刷新省份状态。 */
  async function saveCase(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!slot || !form) return;
    setSaving(true); setError(null); setNotice(null);
    try {
      const path = slot.id ? `/admin-typical-cases/${slot.id}` : "/admin-typical-cases";
      const detail = await apiFetch<TypicalCaseAdminDetail>(path, { method: slot.id ? "PATCH" : "POST", body: JSON.stringify(formToPayload(form, slot)) });
      const next = detailToForm(detail); setForm(next); setInitialSnapshot(JSON.stringify(next));
      setSlot((current) => current ? { ...current, id: detail.id, status: detail.is_published ? "已上线" : "草稿", title: detail.title } : current);
      setNotice(`已保存${slot.province}案例${detail.is_published ? "并上线" : "草稿"}`);
      await loadOverview();
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "保存失败，请检查必填字段"); }
    finally { setSaving(false); }
  }

  /** 校验数量后上传图片，并立即加入当前表单的图片序列。 */
  async function uploadImages(event: ChangeEvent<HTMLInputElement>) {
    const files = Array.from(event.target.files ?? []); event.target.value = "";
    if (!slot || !form || files.length === 0) return;
    if (form.images.length + files.length > 5) { setError("每个案例最多 5 张图片，请先移除多余图片"); return; }
    setUploading(true); setError(null);
    try {
      const uploaded: TypicalCaseImage[] = [];
      for (const file of files) {
        const data = new FormData(); data.append("file", file);
        const result = await apiUpload<TypicalCaseImageUploadRead>("/admin-typical-cases/images", data);
        uploaded.push({ path: result.path, alt_text: `${slot.province}典型案例图片`, caption: null, is_cover: form.images.length === 0 && uploaded.length === 0 });
      }
      setForm((current) => current ? { ...current, images: [...current.images, ...uploaded] } : current);
    } catch (requestError) { setError(requestError instanceof Error ? requestError.message : "图片上传失败"); }
    finally { setUploading(false); }
  }

  /** 永久删除数据库案例，并把当前省份恢复为未配置。 */
  async function deleteCase() {
    if (!slot?.id) return;
    setDeleting(true); setDeleteError(null);
    try {
      await apiFetch<void>(`/admin-typical-cases/${slot.id}`, { method: "DELETE" });
      setDeleteOpen(false); setSlot(null); setForm(null); setInitialSnapshot("");
      setNotice(`已删除${slot.province}案例，该省份已恢复为未配置`);
      await loadOverview();
    } catch (requestError) { setDeleteError(requestError instanceof Error ? requestError.message : "删除失败，请稍后重试"); }
    finally { setDeleting(false); }
  }

  /** 修改图片元数据或封面状态，确保封面始终唯一。 */
  function updateImage(index: number, changes: Partial<TypicalCaseImage>) {
    setForm((current) => current ? { ...current, images: current.images.map((image, imageIndex) => ({ ...image, ...(changes.is_cover ? { is_cover: imageIndex === index } : imageIndex === index ? changes : {}) })) } : current);
  }

  /** 上下调整图片顺序，首页详情按该顺序展示。 */
  function moveImage(index: number, direction: -1 | 1) {
    setForm((current) => { if (!current) return current; const target = index + direction; if (target < 0 || target >= current.images.length) return current; const images = [...current.images]; [images[index], images[target]] = [images[target], images[index]]; return { ...current, images }; });
  }

  if (slot) {
    const selectedProject = projectOptions.find((item) => item.id === form?.salesProjectId);
    return <section className="admin-data-workspace case-admin-detail">
      <button type="button" className="competitor-back-button" onClick={closeDetail}><ArrowLeft size={15} />返回省份列表</button>
      <header className="case-detail-header"><div><h2>{slot.province}典型案例</h2><p>省份与行政区编码创建后不可修改；所有展示内容都在此页维护。</p></div><span className={`case-status status-${slot.status}`}>{slot.status}</span></header>
      {notice ? <p className="admin-page-notice" role="status"><Check size={16} />{notice}</p> : null}
      {error ? <p className="admin-page-error" role="alert"><CircleAlert size={16} />{error}</p> : null}
      {detailLoading || !form ? <div className="admin-data-loading">正在读取完整案例…</div> : <form className="case-editor" onSubmit={saveCase}>
        <section className="case-editor-section"><div className="case-section-heading"><div><h3>案例主档</h3><p>首页入口和详情页标题使用这些识别信息。</p></div></div><div className="case-form-grid">
          <label>省份<input value={slot.province} disabled /></label><label>行政区编码<input value={slot.province_adcode} disabled /></label>
          <label>城市<span>必填</span><input required minLength={2} maxLength={60} value={form.city} onChange={(event) => setForm({ ...form, city: event.target.value })} /></label>
          <label className="wide">案例标题<span>必填</span><input required minLength={2} maxLength={160} value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} /></label>
          <label className="wide">副标题<input maxLength={240} value={form.subtitle} onChange={(event) => setForm({ ...form, subtitle: event.target.value })} /></label>
          <label>客户展示名<span>必填</span><input required minLength={2} maxLength={160} value={form.customerDisplayName} onChange={(event) => setForm({ ...form, customerDisplayName: event.target.value })} /></label>
          <label>行业标签<span>必填</span><input required minLength={2} maxLength={120} value={form.industryLabel} onChange={(event) => setForm({ ...form, industryLabel: event.target.value })} /></label>
        </div></section>

        <section className="case-editor-section"><div className="case-section-heading"><div><h3>关联成交项目</h3><p>只显示本省成交项目；关联后可选择在公开页展示真实合同金额。</p></div></div><div className="case-project-picker"><label>搜索项目<input placeholder="项目或单位名称" value={projectSearch} onChange={(event) => setProjectSearch(event.target.value)} /></label><label>成交项目<select value={form.salesProjectId} onChange={(event) => { const option = projectOptions.find((item) => item.id === event.target.value); setForm({ ...form, salesProjectId: event.target.value, city: option?.city || form.city, showContractAmount: event.target.value ? form.showContractAmount : false }); }}><option value="">不关联成交项目</option>{projectOptions.map((option) => <option key={option.id} value={option.id}>{option.organization_name} · {option.project_name}</option>)}</select></label>{selectedProject ? <p><MapPin size={14} />{selectedProject.city} · ¥{Number(selectedProject.contract_amount).toLocaleString("zh-CN")}</p> : null}<label className="case-checkbox"><input type="checkbox" checked={form.showContractAmount} disabled={!form.salesProjectId} onChange={(event) => setForm({ ...form, showContractAmount: event.target.checked })} />公开展示合同金额</label></div></section>

        <section className="case-editor-section"><div className="case-section-heading"><div><h3>案例故事</h3><p>草稿可以逐步补齐；上线前摘要、挑战、方案、成果和产品范围均为必填。</p></div></div><div className="case-story-grid">
          <label className="wide">案例摘要<textarea maxLength={2000} rows={4} value={form.summary} onChange={(event) => setForm({ ...form, summary: event.target.value })} /></label>
          <label>业务挑战<textarea maxLength={10000} rows={8} value={form.challenge} onChange={(event) => setForm({ ...form, challenge: event.target.value })} /></label>
          <label>解决方案<textarea maxLength={10000} rows={8} value={form.solution} onChange={(event) => setForm({ ...form, solution: event.target.value })} /></label>
          <label>实施成果<textarea maxLength={10000} rows={8} value={form.outcome} onChange={(event) => setForm({ ...form, outcome: event.target.value })} /></label>
          <label>产品与服务范围<textarea maxLength={5000} rows={8} value={form.productScope} onChange={(event) => setForm({ ...form, productScope: event.target.value })} /></label>
        </div></section>

        <section className="case-editor-section"><div className="case-section-heading"><div><h3>成果指标</h3><p>最多 4 项，使用短标签和值帮助访客快速理解成果。</p></div><button type="button" disabled={form.metrics.length >= 4} onClick={() => setForm({ ...form, metrics: [...form.metrics, { label: "", value: "", unit: null, note: null }] })}><Plus size={14} />添加指标</button></div><div className="case-metric-list">{form.metrics.length === 0 ? <p className="case-inline-empty">尚未添加成果指标。</p> : form.metrics.map((metric, index) => <div className="case-metric-row" key={`metric-${index}`}><label>名称<input required minLength={1} maxLength={40} value={metric.label} onChange={(event) => setForm({ ...form, metrics: form.metrics.map((item, itemIndex) => itemIndex === index ? { ...item, label: event.target.value } : item) })} /></label><label>数值<input required minLength={1} maxLength={40} value={metric.value} onChange={(event) => setForm({ ...form, metrics: form.metrics.map((item, itemIndex) => itemIndex === index ? { ...item, value: event.target.value } : item) })} /></label><label>单位<input maxLength={20} value={metric.unit ?? ""} onChange={(event) => setForm({ ...form, metrics: form.metrics.map((item, itemIndex) => itemIndex === index ? { ...item, unit: event.target.value } : item) })} /></label><label>说明<input maxLength={160} value={metric.note ?? ""} onChange={(event) => setForm({ ...form, metrics: form.metrics.map((item, itemIndex) => itemIndex === index ? { ...item, note: event.target.value } : item) })} /></label><button type="button" aria-label={`删除第${index + 1}项指标`} onClick={() => setForm({ ...form, metrics: form.metrics.filter((_, itemIndex) => itemIndex !== index) })}><Trash2 size={15} /></button></div>)}</div></section>

        <section className="case-editor-section"><div className="case-section-heading"><div><h3>案例图片</h3><p>最多 5 张，自动转为 WebP。上线前必须设置一张封面并填写图片说明。</p></div><label className={`case-upload-button ${uploading || form.images.length >= 5 ? "disabled" : ""}`}><ImagePlus size={15} />{uploading ? "正在上传…" : "上传图片"}<input type="file" accept="image/png,image/jpeg,image/webp" multiple disabled={uploading || form.images.length >= 5} onChange={(event) => void uploadImages(event)} /></label></div><div className="case-image-list">{form.images.length === 0 ? <p className="case-inline-empty">尚未上传图片，草稿可保存，上线前需要封面。</p> : form.images.map((image, index) => <article className="case-image-row" key={image.path}><div className="case-image-preview"><Image src={image.path} alt="" width={296} height={184} /></div><div className="case-image-fields"><label>无障碍说明<span>必填</span><input required minLength={2} maxLength={240} value={image.alt_text} onChange={(event) => updateImage(index, { alt_text: event.target.value })} /></label><label>图片注释<input maxLength={500} value={image.caption ?? ""} onChange={(event) => updateImage(index, { caption: event.target.value })} /></label></div><div className="case-image-actions"><button type="button" className={image.is_cover ? "selected" : ""} onClick={() => updateImage(index, { is_cover: true })}><Star size={14} />{image.is_cover ? "当前封面" : "设为封面"}</button><button type="button" aria-label="上移图片" disabled={index === 0} onClick={() => moveImage(index, -1)}><ArrowUp size={14} /></button><button type="button" aria-label="下移图片" disabled={index === form.images.length - 1} onClick={() => moveImage(index, 1)}><ArrowDown size={14} /></button><button type="button" aria-label="移除图片" onClick={() => { const images = form.images.filter((_, itemIndex) => itemIndex !== index); if (image.is_cover && images[0]) images[0] = { ...images[0], is_cover: true }; setForm({ ...form, images }); }}><Trash2 size={14} /></button></div></article>)}</div></section>

        <section className="case-editor-section"><div className="case-section-heading"><div><h3>客户引语与发布</h3><p>客户引语为选填；推荐位全站仅允许一个已上线案例。</p></div></div><div className="case-form-grid"><label className="wide">客户引语<textarea maxLength={2000} rows={4} value={form.customerQuote} onChange={(event) => setForm({ ...form, customerQuote: event.target.value })} /></label><label className="wide">引语署名<input maxLength={160} value={form.quoteAttribution} onChange={(event) => setForm({ ...form, quoteAttribution: event.target.value })} /></label><label className="case-checkbox"><input type="checkbox" checked={form.isPublished} onChange={(event) => setForm({ ...form, isPublished: event.target.checked, isFeatured: event.target.checked ? form.isFeatured : false })} />发布到第六张地图</label><label className="case-checkbox"><input type="checkbox" checked={form.isFeatured} disabled={!form.isPublished} onChange={(event) => setForm({ ...form, isFeatured: event.target.checked })} />设为全国推荐案例</label></div></section>

        <footer className="case-editor-actions"><div>{slot.id ? <button type="button" className="case-delete-button" onClick={() => { setDeleteError(null); setDeleteOpen(true); }}><Trash2 size={15} />删除案例</button> : null}<span>{dirty ? "有尚未保存的修改" : "所有修改已保存"}</span></div><button type="submit" className="case-save-button" disabled={saving || uploading}><Save size={16} />{saving ? "正在保存…" : form.isPublished ? "保存并上线" : "保存草稿"}</button></footer>
      </form>}
      {deleteOpen ? <CaseDeleteDialog province={slot.province} deleting={deleting} error={deleteError} onCancel={() => setDeleteOpen(false)} onConfirm={() => void deleteCase()} /> : null}
    </section>;
  }

  return <section className="admin-data-workspace case-admin-list">
    {notice ? <p className="admin-page-notice" role="status"><Check size={16} />{notice}</p> : null}
    {error ? <p className="admin-page-error" role="alert"><CircleAlert size={16} />{error}</p> : null}
    <div className="admin-data-toolbar"><label className="admin-data-search"><Search size={15} /><input aria-label="搜索典型案例" placeholder="搜索省份、标题、客户或行业" value={search} onChange={(event) => setSearch(event.target.value)} /></label><label className="admin-data-resource-select">状态<select aria-label="按案例状态筛选" value={status} onChange={(event) => setStatus(event.target.value as TypicalCaseAdminStatus | "全部")} >{statusOptions.map((item) => <option key={item}>{item}</option>)}</select></label></div>
    <div className="admin-data-list-card organization-list-card case-list-card"><div className="card-title case-list-title"><div><span>每省一个入口</span><h2>{overview?.total_regions ?? 31} 个省份</h2></div><div className="case-title-summary" aria-label="案例配置统计"><span><b>{overview?.published_count ?? 0}</b>已上线</span><span><b>{overview?.draft_count ?? 0}</b>草稿</span><span><b>{(overview?.total_regions ?? 31) - (overview?.configured_count ?? 0)}</b>未配置</span></div></div><div className="admin-data-table case-admin-table" role="list" aria-busy={loading}><div className="admin-data-row admin-data-row-head" aria-hidden="true"><span>省份</span><span>状态</span><span>案例 / 客户</span><span>城市 / 行业</span><span>更新时间</span><span>操作</span></div>{filteredItems.map((item) => <div className="admin-data-row" role="listitem" key={item.province_adcode}><span className="case-province-cell">{item.cover_image ? <Image src={item.cover_image.path} alt="" width={76} height={76} /> : <i><MapPin size={14} /></i>}<strong>{item.province}</strong></span><span><em className={`case-status status-${item.status}`}>{item.status}</em>{item.is_featured ? <small className="case-featured"><Star size={11} />推荐</small> : null}</span><span className="case-title-cell"><strong>{item.title ?? "等待创建案例"}</strong><small>{item.customer_display_name ?? "点击进入后填写完整内容"}</small></span><span className="case-title-cell"><strong>{item.city ?? "未填写城市"}</strong><small>{item.industry_label ?? "未填写行业"}</small></span><span>{displayDate(item.updated_at)}</span><span className="organization-row-actions"><button type="button" className="organization-edit-action" onClick={() => void openCase(item)}>{item.id ? "打开详情" : "创建案例"}</button></span></div>)}</div>{!loading && filteredItems.length === 0 ? <div className="admin-data-state">没有匹配的省份案例。</div> : null}</div>
  </section>;
}
