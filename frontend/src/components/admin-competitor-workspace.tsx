"use client";

/** 成交订单同行抽屉：按账号范围展示成交信息，并维护公司主档与可见据点。 */

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Building2, Check, CircleAlert, ExternalLink, MapPin, Pencil, Plus, Save, Trash2, X } from "lucide-react";

import {
  AdminDataDeleteDialog,
  AdminDataFormDialog,
  type AdminDataItem,
} from "@/components/admin-data-workspace";
import { ADMIN_SECTION_CONFIGS, type AdminResourceConfig } from "@/lib/admin-data-config";
import { apiFetch, type AdminCompetitorDetail, type CompetitorSite } from "@/lib/api";

interface CompetitorDrawerProps {
  competitorId: string;
  onClose: () => void;
  onFilterOrders: (competitorId: string) => void;
  onSaved: (name: string) => void;
}

type ProfileForm = {
  name: string;
  websiteUrl: string;
  color: string;
  description: string;
  isActive: boolean;
};

const emptyProfile: ProfileForm = { name: "", websiteUrl: "", color: "#6B7280", description: "", isActive: false };
const competitorConfigs = ADMIN_SECTION_CONFIGS.competitors.resources;

/** 读取同行资源的既有字段配置，避免抽屉复制据点校验规则。 */
function resourceConfig(key: string): AdminResourceConfig {
  const config = competitorConfigs.find((item) => item.key === key);
  if (!config) throw new Error(`缺少同行资源配置：${key}`);
  return config;
}

/** 使用中国地区规则显示同行成交金额。 */
function currency(value: string | number): string {
  return new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 2 }).format(Number(value || 0));
}

/** 把接口主档同步到可编辑表单，保证刷新后不保留旧同行内容。 */
function formFromDetail(detail: AdminCompetitorDetail): ProfileForm {
  return {
    name: detail.name,
    websiteUrl: detail.website_url ?? "",
    color: detail.color,
    description: detail.description ?? "",
    isActive: detail.is_active,
  };
}

/** 在成交订单上方打开同行公司资料，并把订单、据点和编辑权限绑定到账号范围。 */
export function AdminCompetitorDrawer({ competitorId, onClose, onFilterOrders, onSaved }: CompetitorDrawerProps) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const [detail, setDetail] = useState<AdminCompetitorDetail | null>(null);
  const [form, setForm] = useState<ProfileForm>(emptyProfile);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [creatingSite, setCreatingSite] = useState(false);
  const [editingSite, setEditingSite] = useState<CompetitorSite | null>(null);
  const [deleteSite, setDeleteSite] = useState<CompetitorSite | null>(null);
  const baseSiteConfig = resourceConfig("competitor_sites");
  const siteConfig = useMemo(() => ({ ...baseSiteConfig, filters: { ...baseSiteConfig.filters, competitor_id: competitorId } }), [baseSiteConfig, competitorId]);

  useEffect(() => {
    const dialog = dialogRef.current;
    dialog?.showModal();
    return () => { if (dialog?.open) dialog.close(); };
  }, []);

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(null), 2400);
    return () => window.clearTimeout(timer);
  }, [notice]);

  /** 取消旧请求并重新读取当前同行的区域裁剪详情。 */
  const loadProfile = useCallback(async () => {
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setLoading(true); setError(null);
    try {
      const result = await apiFetch<AdminCompetitorDetail>(`/admin-competitors/${competitorId}`, { signal: controller.signal });
      if (!controller.signal.aborted) { setDetail(result); setForm(formFromDetail(result)); }
    } catch (requestError) {
      if (!(requestError instanceof DOMException && requestError.name === "AbortError")) setError(requestError instanceof Error ? requestError.message : "同行公司详情加载失败");
    } finally {
      if (!controller.signal.aborted) setLoading(false);
    }
  }, [competitorId]);

  useEffect(() => {
    const timer = window.setTimeout(() => void loadProfile(), 0);
    return () => { window.clearTimeout(timer); abortRef.current?.abort(); };
  }, [loadProfile]);

  /** 保存同行公司主档；后端会再次验证当前账号是否有可见同行订单。 */
  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setSaving(true); setError(null);
    try {
      const result = await apiFetch<AdminCompetitorDetail>(`/admin-competitors/${competitorId}`, {
        method: "PUT",
        body: JSON.stringify({
          name: form.name,
          website_url: form.websiteUrl || null,
          color: form.color,
          description: form.description || null,
          is_active: form.isActive,
        }),
      });
      setDetail(result); setForm(formFromDetail(result)); setNotice("同行公司资料已保存"); onSaved(result.name);
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "同行公司资料保存失败");
    } finally { setSaving(false); }
  }

  /** 新增或修改当前账号范围内的同行据点，并刷新抽屉汇总。 */
  async function saveSite(payload: Record<string, unknown>, item: CompetitorSite | null) {
    const path = item ? `/admin-data/competitor_sites/${item.id}` : "/admin-data/competitor_sites";
    await apiFetch(path, { method: item ? "PUT" : "POST", body: JSON.stringify({ data: payload }) });
    setCreatingSite(false); setEditingSite(null); setNotice(`同行据点已${item ? "保存" : "添加"}`); await loadProfile();
  }

  /** 删除管理员二次确认的单个可见据点。 */
  async function confirmDeleteSite() {
    if (!deleteSite) return;
    await apiFetch(`/admin-data/competitor_sites/${deleteSite.id}`, { method: "DELETE" });
    setDeleteSite(null); setNotice("同行据点已删除"); await loadProfile();
  }

  const visibleOrders = detail?.customers.flatMap((customer) => customer.deals) ?? [];

  return <>
    <dialog ref={dialogRef} className="competitor-order-drawer" aria-labelledby="competitor-drawer-title" onCancel={(event) => { event.preventDefault(); onClose(); }}>
      <div className="competitor-drawer-head"><div><h2 id="competitor-drawer-title">{detail?.name ?? "同行公司详情"}</h2><p>{detail?.scope_limited ? "仅展示当前账号覆盖范围内的成交信息" : "展示全部同行成交信息"}</p></div><button type="button" onClick={onClose} aria-label="关闭同行公司详情" autoFocus><X size={18} /></button></div>

      {loading ? <div className="competitor-drawer-state" role="status">正在加载同行公司详情…</div> : error && !detail ? <div className="competitor-drawer-state is-error" role="alert"><CircleAlert size={18} />{error}<button type="button" onClick={() => void loadProfile()}>重新加载</button></div> : detail ? <div className="competitor-drawer-body">
        <div className="competitor-drawer-summary" aria-label="覆盖范围内同行摘要"><span><Building2 size={15} /><b>{detail.summary.customer_count}</b> 个成交单位</span><span><b>{detail.summary.deal_count}</b> 笔订单</span><span><MapPin size={15} /><b>{detail.summary.site_count}</b> 个可见据点</span><span><b>{currency(detail.summary.total_amount)}</b> 成交额</span></div>

        {notice ? <p className="admin-page-notice" role="status"><Check size={15} />{notice}</p> : null}
        {error ? <p className="admin-page-error" role="alert"><CircleAlert size={15} />{error}</p> : null}

        <form className="competitor-profile-form" onSubmit={saveProfile}>
          <div className="competitor-drawer-section-head"><div><h3>公司资料</h3><p>自动建档后可在这里补齐官网、说明、颜色和审核状态。</p></div><button className="competitor-profile-save" disabled={saving}><Save size={15} />{saving ? "正在保存…" : "保存公司资料"}</button></div>
          <div className="competitor-profile-fields">
            <label><span>公司名称<b aria-hidden="true">*</b></span><input value={form.name} minLength={2} maxLength={255} required onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))} /></label>
            <label><span>公司官网</span><input type="url" value={form.websiteUrl} maxLength={1000} placeholder="https://example.com" onChange={(event) => setForm((current) => ({ ...current, websiteUrl: event.target.value }))} /></label>
            <label className="competitor-color-field"><span>展示颜色</span><input type="color" value={form.color} onChange={(event) => setForm((current) => ({ ...current, color: event.target.value }))} /></label>
            <label className="competitor-active-field"><input type="checkbox" checked={form.isActive} onChange={(event) => setForm((current) => ({ ...current, isActive: event.target.checked }))} /><span>资料已审核，启用公开展示</span></label>
            <label className="competitor-description-field"><span>公司说明</span><textarea value={form.description} maxLength={5000} rows={4} onChange={(event) => setForm((current) => ({ ...current, description: event.target.value }))} /></label>
          </div>
          {detail.website_url ? <a className="competitor-profile-link" href={detail.website_url} target="_blank" rel="noreferrer"><ExternalLink size={14} />打开当前官网</a> : null}
        </form>

        <section className="competitor-drawer-section">
          <div className="competitor-drawer-section-head"><div><h3>公司据点</h3><p>{detail.scope_limited ? "仅显示并允许维护当前覆盖范围内的据点。" : "维护总部、分部和服务点。"}</p></div><button type="button" className="competitor-section-action" onClick={() => setCreatingSite(true)}><Plus size={14} />添加据点</button></div>
          {detail.sites.length ? <div className="competitor-site-list">{detail.sites.map((site) => <article key={site.id}><i style={{ background: detail.color }} /><div><strong>{site.name}</strong><span>{site.site_type} · {site.province} {site.city}</span><small>{site.address}</small></div><div><button type="button" onClick={() => setEditingSite(site)}><Pencil size={13} />修改</button><button type="button" className="danger" onClick={() => setDeleteSite(site)}><Trash2 size={13} />删除</button></div></article>)}</div> : <p className="competitor-drawer-empty">当前覆盖范围内暂无公司据点。</p>}
        </section>

        <section className="competitor-drawer-section">
          <div className="competitor-drawer-section-head"><div><h3>成交单位与订单</h3><p>金额和订单数量均按当前账号可见范围实时汇总。</p></div><button type="button" className="competitor-section-action" onClick={() => { onFilterOrders(competitorId); onClose(); }}>筛选全部订单</button></div>
          {detail.customers.length ? <div className="competitor-customer-list">{detail.customers.map((customer) => <details key={customer.id}><summary><span><strong>{customer.name}</strong><small>{customer.province} {customer.city} · {customer.customer_level}</small></span><b>{customer.deals.length} 笔 · {currency(customer.deals.reduce((total, deal) => total + Number(deal.amount), 0))}</b></summary><ul>{customer.deals.map((deal) => <li key={deal.id}><span><strong>{deal.project_name}</strong><small>{deal.signed_at ?? "日期未填写"} · {deal.supplier_name || "供应商未填写"}</small></span><b>{currency(deal.amount)}</b></li>)}</ul></details>)}</div> : <p className="competitor-drawer-empty">当前覆盖范围内暂无成交单位。</p>}
          <p className="competitor-visible-count">当前可见 {visibleOrders.length} 笔订单；其他区域订单不会加载到浏览器。</p>
        </section>
      </div> : null}
    </dialog>
    {creatingSite ? <AdminDataFormDialog config={siteConfig} item={null} hiddenFields={["competitor_id"]} onCancel={() => setCreatingSite(false)} onSaved={(payload) => saveSite(payload, null)} /> : null}
    {editingSite ? <AdminDataFormDialog key={editingSite.id} config={siteConfig} item={editingSite as unknown as AdminDataItem} hiddenFields={["competitor_id"]} onCancel={() => setEditingSite(null)} onSaved={(payload) => saveSite(payload, editingSite)} /> : null}
    {deleteSite ? <AdminDataDeleteDialog key={deleteSite.id} config={siteConfig} item={deleteSite as unknown as AdminDataItem} onCancel={() => setDeleteSite(null)} onConfirm={confirmDeleteSite} /> : null}
  </>;
}
