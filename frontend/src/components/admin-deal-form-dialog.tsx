"use client";

/** 成交订单表单：维护两类订单字段，并允许编辑时切换归属。 */

import { FormEvent, useEffect, useId, useRef, useState } from "react";
import { CircleAlert, Save, Trash2, X } from "lucide-react";

import { AmapLocationSearch } from "@/components/amap-location-search";
import { AdminProductItemsEditor, emptyProductItem, productItemFromApi, productItemPayload, type ProductItemDraft } from "@/components/admin-product-items-editor";
import { apiFetch, queryString, type AdminDealItem, type AdminDealSeller, type IntelligenceConfidence, type IntelligenceSourceType, type Organization, type OrganizationOpportunity } from "@/lib/api";

interface DealReferenceOption { value: string; label: string }

interface DealDraft {
  sellerType: Exclude<AdminDealSeller, "all">;
  customerId: string;
  customerName: string;
  competitorId: string;
  competitorName: string;
  opportunityId: string;
  salespersonId: string;
  projectName: string;
  totalAmount: string;
  supplierName: string;
  locationName: string;
  province: string;
  city: string;
  signedAt: string;
  dealType: string;
  sourceType: IntelligenceSourceType | "";
  sourceReference: string;
  sourceUrl: string;
  confidence: IntelligenceConfidence | "";
  notes: string;
  products: ProductItemDraft[];
}

export interface AdminDealWriteRequest {
  sellerType: Exclude<AdminDealSeller, "all">;
  data: Record<string, unknown>;
}

/** 从统一列表项生成隔离草稿；新订单默认提供一条空产品行。 */
function initialDraft(item: AdminDealItem | null, defaultSeller: Exclude<AdminDealSeller, "all">): DealDraft {
  return {
    sellerType: item?.seller_type ?? defaultSeller,
    customerId: item?.organization_id ?? (item?.seller_type === "unite" ? item.customer_id : ""),
    customerName: item?.customer_name ?? "",
    competitorId: item?.seller_id ?? "",
    competitorName: item?.seller_type === "competitor" ? item.seller_name : "",
    opportunityId: item?.opportunity_id ?? "",
    salespersonId: item?.salesperson_id ?? "",
    projectName: item?.project_name ?? "",
    totalAmount: item?.total_amount ?? "",
    supplierName: item?.supplier_name ?? "",
    locationName: item?.location_name ?? "",
    province: item?.province ?? "",
    city: item?.city ?? "",
    signedAt: item?.signed_at ?? "",
    dealType: item?.deal_type ?? "",
    sourceType: item?.source_type ?? "",
    sourceReference: item?.source_reference ?? "",
    sourceUrl: item?.source_url ?? "",
    confidence: item?.confidence ?? "",
    notes: item?.notes ?? "",
    products: item?.products.map((product) => productItemFromApi(product as unknown as Record<string, unknown>)) ?? [emptyProductItem()],
  };
}

/** 将空文本归一为 null，避免数据库中出现只含空格的可选值。 */
function optionalText(value: string): string | null {
  return value.trim() || null;
}

/** 用一个可输入的原生联想框选择已有主档；未命中时保留名称供后端自动建档。 */
function DealEntityField({ label, resource, value, selectedId, required = false, onChange }: { label: string; resource: "organizations" | "competitors"; value: string; selectedId: string; required?: boolean; onChange: (name: string, id: string) => void }) {
  const listId = useId();
  const [options, setOptions] = useState<DealReferenceOption[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      setLoading(true);
      void apiFetch<DealReferenceOption[]>(`/admin-data/${resource}/options${queryString({ search: value || undefined, selected_id: selectedId || undefined })}`, { signal: controller.signal })
        .then(setOptions)
        .catch((error: unknown) => { if (!(error instanceof DOMException && error.name === "AbortError")) setOptions([]); })
        .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, 220);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [resource, selectedId, value]);

  return <label className="admin-deal-entity-field"><span>{label}{required ? <b aria-hidden="true">*</b> : null}</span><input aria-label={label} list={listId} value={value} minLength={2} maxLength={255} required={required} autoComplete="off" placeholder={`输入或选择${label}`} onChange={(event) => { const name = event.target.value; const match = options.find((option) => option.label === name); onChange(name, match?.value ?? ""); }} /><datalist id={listId}>{options.map((option) => <option key={option.value} value={option.label} />)}</datalist><small>{loading ? "正在匹配已有数据…" : selectedId ? "已选择现有记录" : value.trim().length >= 2 ? "未选择现有项时，保存后自动建档待审核" : `输入至少 2 个字搜索${label}`}</small></label>;
}

/** 加载只允许选择既有记录的普通外键，销售人员等主档不在订单页自动创建。 */
function DealReferenceField({ label, resource, value, selectedLabel, onChange }: { label: string; resource: string; value: string; selectedLabel?: string; onChange: (value: string) => void }) {
  const [options, setOptions] = useState<DealReferenceOption[]>([]);
  useEffect(() => {
    const controller = new AbortController();
    void apiFetch<DealReferenceOption[]>(`/admin-data/${resource}/options${queryString({ selected_id: value || undefined })}`, { signal: controller.signal })
      .then(setOptions)
      .catch((error: unknown) => { if (!(error instanceof DOMException && error.name === "AbortError")) setOptions([]); });
    return () => controller.abort();
  }, [resource, value]);
  const hasSelectedOption = options.some((option) => option.value === value);
  return <label><span>{label}</span><select aria-label={label} value={value} onChange={(event) => onChange(event.target.value)}><option value="">未选择</option>{value && !hasSelectedOption ? <option value={value}>{selectedLabel || "当前已选记录"}</option> : null}{options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}</select></label>;
}

/** 把当前草稿转换成对应公共数据库接口的完整订单合同。 */
function requestFromDraft(draft: DealDraft): AdminDealWriteRequest {
  const products = draft.products.map(productItemPayload);
  if (draft.sellerType === "unite") {
    const uniteProducts = products.map((product) => { const item = { ...product }; delete item.product_image_url; return item; });
    return { sellerType: "unite", data: {
      organization_id: draft.customerId || null,
      organization_name: draft.customerName.trim(),
      opportunity_id: optionalText(draft.opportunityId),
      salesperson_id: optionalText(draft.salespersonId),
      project_name: draft.projectName.trim(),
      total_amount: Number(draft.totalAmount),
      supplier_name: optionalText(draft.supplierName),
      location_name: optionalText(draft.locationName),
      province: optionalText(draft.province),
      city: optionalText(draft.city),
      signed_at: optionalText(draft.signedAt),
      notes: optionalText(draft.notes),
      products: uniteProducts,
    } };
  }
  return { sellerType: "competitor", data: {
    competitor_id: draft.competitorId || null,
    competitor_name: draft.competitorName.trim(),
    organization_id: draft.customerId || null,
    organization_name: draft.customerName.trim(),
    project_name: draft.projectName.trim(),
    deal_type: optionalText(draft.dealType),
    products,
    supplier_name: optionalText(draft.supplierName),
    amount: Number(draft.totalAmount),
    signed_at: optionalText(draft.signedAt),
    location_name: optionalText(draft.locationName),
    province: optionalText(draft.province),
    city: optionalText(draft.city),
    source_type: draft.sourceType || null,
    source_reference: optionalText(draft.sourceReference),
    source_url: optionalText(draft.sourceUrl),
    confidence: draft.confidence || null,
    notes: optionalText(draft.notes),
  } };
}

/** 渲染订单完整字段表单，并按卖方显示对应字段与产品图片能力。 */
export function AdminDealFormDialog({ item, defaultSeller, onCancel, onSaved }: { item: AdminDealItem | null; defaultSeller: Exclude<AdminDealSeller, "all">; onCancel: () => void; onSaved: (request: AdminDealWriteRequest) => Promise<void> }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [draft, setDraft] = useState(() => initialDraft(item, defaultSeller));
  const [opportunities, setOpportunities] = useState<OrganizationOpportunity[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => { const dialog = dialogRef.current; dialog?.showModal(); return () => { if (dialog?.open) dialog.close(); }; }, []);
  useEffect(() => {
    if (draft.sellerType !== "unite" || !draft.customerId) return;
    const controller = new AbortController();
    void apiFetch<Organization>(`/organizations/${draft.customerId}`, { signal: controller.signal })
      .then((organization) => setOpportunities(organization.opportunities))
      .catch((requestError: unknown) => { if (!(requestError instanceof DOMException && requestError.name === "AbortError")) setOpportunities([]); });
    return () => controller.abort();
  }, [draft.customerId, draft.sellerType]);
  const visibleOpportunities = draft.sellerType === "unite" && draft.customerId ? opportunities : [];
  const locationRequired = item === null;

  /** 更新单个草稿字段，避免改写传入的列表对象。 */
  function update<K extends keyof DealDraft>(field: K, value: DealDraft[K]) {
    setDraft((current) => ({ ...current, [field]: value }));
  }

  /** 校验浏览器字段后提交完整订单，失败时保留草稿。 */
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (locationRequired && (!draft.locationName || !draft.province || !draft.city)) {
      setError("请先搜索并选择成交单位所在地");
      return;
    }
    setSubmitting(true); setError(null);
    try { await onSaved(requestFromDraft(draft)); }
    catch (saveError) { setError(saveError instanceof Error ? saveError.message : "订单保存失败，请检查字段后重试"); setSubmitting(false); }
  }

  return (
    <dialog ref={dialogRef} className="organization-edit-dialog admin-data-dialog admin-deal-dialog" aria-labelledby="admin-deal-dialog-title" onCancel={(event) => { event.preventDefault(); if (!submitting) onCancel(); }}>
      <form onSubmit={submit}>
        <header><div><span>{item ? "编辑完整订单" : "新增完整订单"}</span><h2 id="admin-deal-dialog-title">{item ? `修改${item.project_name}` : "添加成交订单"}</h2><p>订单主字段统一保存，产品按明细逐条维护。</p></div><button type="button" onClick={onCancel} disabled={submitting} aria-label="关闭订单表单"><X size={18} /></button></header>
        <div className="organization-edit-body">
          <section><h3>全部订单字段</h3><div className="organization-edit-grid">
            <label><span>订单归属<b aria-hidden="true">*</b></span><select value={draft.sellerType} onChange={(event) => { update("sellerType", event.target.value as DealDraft["sellerType"]); update("opportunityId", ""); }}><option value="unite">优纳特</option><option value="competitor">同行</option></select>{item && draft.sellerType !== item.seller_type ? <small>保存后将原子转换订单归属，原订单不会重复保留</small> : null}</label>
            {draft.sellerType === "competitor" ? <DealEntityField label="成交同行" resource="competitors" value={draft.competitorName} selectedId={draft.competitorId} required onChange={(name, id) => { update("competitorName", name); update("competitorId", id); }} /> : null}
            <DealEntityField label="成交单位" resource="organizations" value={draft.customerName} selectedId={draft.customerId} required onChange={(name, id) => { update("customerName", name); update("customerId", id); update("opportunityId", ""); }} />
            <label className="field-wide"><span>项目名称<b aria-hidden="true">*</b></span><input value={draft.projectName} onChange={(event) => update("projectName", event.target.value)} maxLength={255} required /></label>
            <label><span>项目总价（元）<b aria-hidden="true">*</b></span><input type="number" min={draft.sellerType === "unite" ? "0" : "0.01"} step="0.01" value={draft.totalAmount} onChange={(event) => update("totalAmount", event.target.value)} required /></label>
            <label><span>供应商名称</span><input value={draft.supplierName} onChange={(event) => update("supplierName", event.target.value)} maxLength={255} /></label>
            <label><span>签约 / 中标时间</span><input type="date" value={draft.signedAt} onChange={(event) => update("signedAt", event.target.value)} /></label>
            {draft.sellerType === "unite" ? <>
              <DealReferenceField label="负责销售" resource="salespeople" value={draft.salespersonId} selectedLabel={item?.salesperson_name ?? undefined} onChange={(value) => update("salespersonId", value)} />
              <label><span>关联商机</span><select value={draft.opportunityId} onChange={(event) => update("opportunityId", event.target.value)}><option value="">未选择</option>{visibleOpportunities.map((opportunity) => <option key={opportunity.id} value={opportunity.id}>{opportunity.title}</option>)}</select></label>
            </> : <>
              <label><span>成交类型</span><input value={draft.dealType} onChange={(event) => update("dealType", event.target.value)} maxLength={80} /></label>
              <label><span>来源类型</span><select value={draft.sourceType} onChange={(event) => update("sourceType", event.target.value as DealDraft["sourceType"])}><option value="">未填写</option><option>公开信息</option><option>一线反馈</option><option>推测</option></select></label>
              <label><span>置信度</span><select value={draft.confidence} onChange={(event) => update("confidence", event.target.value as DealDraft["confidence"])}><option value="">未填写</option><option>高</option><option>中</option><option>低</option></select></label>
              <label className="field-wide"><span>来源说明</span><input value={draft.sourceReference} onChange={(event) => update("sourceReference", event.target.value)} maxLength={500} /></label>
              <label className="field-wide"><span>来源网址</span><input value={draft.sourceUrl} onChange={(event) => update("sourceUrl", event.target.value)} maxLength={1000} /></label>
            </>}
            <AmapLocationSearch
              label="成交单位所在地"
              description="搜索并选择地点后，仅保留所在地名称、省份和城市"
              queryHint={draft.locationName || draft.customerName}
              value={{ name: draft.locationName }}
              required={locationRequired}
              disabled={submitting}
              onSelect={(location) => {
                update("locationName", location.name);
                update("province", location.province);
                update("city", location.city);
              }}
            />
            <label><span>所在地名称{locationRequired ? <b aria-hidden="true">*</b> : null}</span><input value={draft.locationName} readOnly required={locationRequired} placeholder="请从高德搜索结果中选择" /></label>
            <label><span>省份{locationRequired ? <b aria-hidden="true">*</b> : null}</span><input value={draft.province} readOnly required={locationRequired} /></label>
            <label><span>城市{locationRequired ? <b aria-hidden="true">*</b> : null}</span><input value={draft.city} readOnly required={locationRequired} /></label>
            <label className="field-wide"><span>备注</span><textarea value={draft.notes} onChange={(event) => update("notes", event.target.value)} maxLength={5000} rows={4} /></label>
          </div></section>
          <section><h3>产品明细</h3><AdminProductItemsEditor value={draft.products} onChange={(products) => update("products", products)} showImage={draft.sellerType === "competitor"} /></section>
        </div>
        {error ? <p className="organization-dialog-error" role="alert"><CircleAlert size={16} />{error}</p> : null}
        <footer><button type="button" className="organization-dialog-cancel" onClick={onCancel} disabled={submitting}>取消</button><button className="organization-dialog-save" disabled={submitting}><Save size={16} />{submitting ? "正在保存…" : item ? "保存修改" : "添加订单"}</button></footer>
      </form>
    </dialog>
  );
}

/** 二次确认单笔订单删除，失败时保留对话框和错误信息。 */
export function AdminDealDeleteDialog({ item, onCancel, onConfirm }: { item: AdminDealItem; onCancel: () => void; onConfirm: () => Promise<void> }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => { const dialog = dialogRef.current; dialog?.showModal(); return () => { if (dialog?.open) dialog.close(); }; }, []);

  /** 删除确认后执行父级写操作，接口失败时允许重试。 */
  async function confirm(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setDeleting(true); setError(null);
    try { await onConfirm(); }
    catch (deleteError) { setError(deleteError instanceof Error ? deleteError.message : "删除订单失败，请稍后重试"); setDeleting(false); }
  }

  return <dialog ref={dialogRef} className="organization-delete-dialog" aria-labelledby="admin-deal-delete-title" onCancel={(event) => { event.preventDefault(); if (!deleting) onCancel(); }}><form onSubmit={confirm}><div className="delete-dialog-icon"><Trash2 size={22} /></div><h2 id="admin-deal-delete-title">确认删除成交订单？</h2><p>“{item.project_name}”及其 {item.products.length} 条产品明细将从公共数据库永久删除。</p>{error ? <p className="organization-dialog-error" role="alert"><CircleAlert size={16} />{error}</p> : null}<footer><button type="button" className="organization-dialog-cancel" onClick={onCancel} disabled={deleting} autoFocus>取消</button><button className="organization-dialog-delete" disabled={deleting}><Trash2 size={16} />{deleting ? "正在删除…" : "确认删除"}</button></footer></form></dialog>;
}
