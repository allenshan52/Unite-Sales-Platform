/** 成交订单后台：统一展示并直接增改删优纳特与同行订单，提供组合筛选和产品明细。 */

import { useEffect, useMemo, useState } from "react";
import { Check, CircleAlert, PackageSearch, Pencil, Plus, Search, Trash2 } from "lucide-react";

import { AdminDealDeleteDialog, AdminDealFormDialog, type AdminDealWriteRequest } from "@/components/admin-deal-form-dialog";
import { apiFetch, queryString, type AdminDealFilterOptions, type AdminDealItem, type AdminDealPage, type AdminDealSeller } from "@/lib/api";

const emptyOptions: AdminDealFilterOptions = { competitors: [], suppliers: [], years: [] };

/** 使用中国地区规则展示订单金额。 */
function currency(value: string): string {
  return new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 2 }).format(Number(value));
}

/** 汇总一笔订单中已填写的去重品牌，供折叠前快速浏览。 */
function productBrands(products: AdminDealItem["products"]): string {
  return Array.from(new Set(products.map((item) => item.brand?.trim()).filter((value): value is string => Boolean(value)))).join("、") || "未填写";
}

/** 渲染统一订单筛选、分页列表及每笔订单的多产品明细。 */
export function AdminDealWorkspace() {
  const [seller, setSeller] = useState<AdminDealSeller>("all");
  const [supplier, setSupplier] = useState("");
  const [competitorId, setCompetitorId] = useState("");
  const [product, setProduct] = useState("");
  const [debouncedProduct, setDebouncedProduct] = useState("");
  const [year, setYear] = useState("");
  const [pageNumber, setPageNumber] = useState(1);
  const [options, setOptions] = useState(emptyOptions);
  const [page, setPage] = useState<AdminDealPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState<AdminDealItem | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<AdminDealItem | null>(null);
  const [revision, setRevision] = useState(0);

  useEffect(() => { const timer = window.setTimeout(() => setDebouncedProduct(product.trim()), 250); return () => window.clearTimeout(timer); }, [product]);
  useEffect(() => { void apiFetch<AdminDealFilterOptions>("/admin-deals/options").then(setOptions).catch(() => setOptions(emptyOptions)); }, [revision]);
  useEffect(() => { if (!notice) return; const timer = window.setTimeout(() => setNotice(null), 2200); return () => window.clearTimeout(timer); }, [notice]);

  const query = useMemo(() => queryString({
    seller, supplier: supplier || undefined,
    competitor_id: seller === "unite" ? undefined : competitorId || undefined,
    product: debouncedProduct || undefined, year: year || undefined,
    page: String(pageNumber), page_size: "20",
  }), [competitorId, debouncedProduct, pageNumber, seller, supplier, year]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(null);
    void apiFetch<AdminDealPage>(`/admin-deals${query}`, { signal: controller.signal })
      .then(setPage)
      .catch((requestError: unknown) => { if (!(requestError instanceof DOMException && requestError.name === "AbortError")) setError(requestError instanceof Error ? requestError.message : "成交订单加载失败"); })
      .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [query, revision]);

  const totalPages = Math.max(1, Math.ceil((page?.total ?? 0) / 20));
  const updateFilter = (action: () => void) => { action(); setPageNumber(1); };

  /** 使用两类订单既有写入接口保存同一份公共数据，并刷新当前筛选页。 */
  async function saveDeal(request: AdminDealWriteRequest) {
    const target = editing;
    const path = request.sellerType === "unite"
      ? `/admin-deals/unite${target ? `/${target.id}` : ""}`
      : `/admin-data/competitor_deals${target ? `/${target.id}` : ""}`;
    await apiFetch(path, {
      method: target ? "PUT" : "POST",
      body: JSON.stringify(request.sellerType === "competitor" ? { data: request.data } : request.data),
    });
    setNotice(target ? "订单修改已保存" : "成交订单已添加");
    setEditing(null); setCreating(false); setRevision((value) => value + 1);
  }

  /** 二次确认后删除单笔订单；同行和优纳特都删除各自原表记录。 */
  async function deleteDeal() {
    if (!deleteTarget) return;
    const path = deleteTarget.seller_type === "unite" ? `/admin-deals/unite/${deleteTarget.id}` : `/admin-data/competitor_deals/${deleteTarget.id}`;
    await apiFetch<void>(path, { method: "DELETE" });
    setDeleteTarget(null); setNotice("成交订单已删除");
    if ((page?.items.length ?? 0) === 1 && pageNumber > 1) setPageNumber((value) => value - 1);
    else setRevision((value) => value + 1);
  }

  return (
    <section className="admin-deal-workspace">
      <header className="admin-deal-header"><h1>成交订单</h1><div className="admin-deal-count" aria-label={`成交订单数量 ${page?.total ?? 0}`}><strong>{page?.total ?? 0}</strong></div><button type="button" className="admin-deal-create" onClick={() => setCreating(true)}><Plus size={15} />添加订单</button></header>
      <div className="admin-deal-filters" aria-label="成交订单筛选">
        <label><span>订单归属</span><select value={seller} onChange={(event) => updateFilter(() => { setSeller(event.target.value as AdminDealSeller); if (event.target.value === "unite") setCompetitorId(""); })}><option value="all">全部订单</option><option value="unite">优纳特</option><option value="competitor">同行</option></select></label>
        <label><span>供应商</span><select value={supplier} onChange={(event) => updateFilter(() => setSupplier(event.target.value))}><option value="">全部供应商</option>{options.suppliers.map((item) => <option key={item}>{item}</option>)}</select></label>
        <label><span>同行公司</span><select value={competitorId} disabled={seller === "unite"} onChange={(event) => updateFilter(() => setCompetitorId(event.target.value))}><option value="">全部同行</option>{options.competitors.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
        <label><span>年份</span><select value={year} onChange={(event) => updateFilter(() => setYear(event.target.value))}><option value="">全部年份</option>{options.years.map((item) => <option key={item}>{item}</option>)}</select></label>
        <label className="admin-deal-product-search"><span>产品</span><div><Search size={16} /><input value={product} onChange={(event) => { setProduct(event.target.value); setPageNumber(1); }} placeholder="搜索产品名称" /></div></label>
      </div>

      {notice ? <p className="admin-page-notice" role="status"><Check size={16} />{notice}</p> : null}

      {error ? <div className="admin-deal-state error" role="alert"><CircleAlert size={20} /><span>{error}</span></div> : loading ? <div className="admin-deal-state">正在加载成交订单…</div> : page?.items.length === 0 ? <div className="admin-deal-state"><PackageSearch size={24} /><span>没有符合当前条件的成交订单。</span></div> : (
        <div className="admin-deal-list">
          {page?.items.map((item) => <article key={`${item.seller_type}-${item.id}`}>
            <div className="admin-deal-row-main"><span className={`admin-deal-seller ${item.seller_type}`}>{item.seller_name}</span><div><h2>{item.project_name}</h2><p>{item.customer_name} · {[item.province, item.city].filter(Boolean).join(" ") || "地区未填写"}</p></div><div className="admin-deal-amount"><strong>{currency(item.total_amount)}</strong><span>{item.signed_at ?? "签约时间未填写"}</span><div className="admin-deal-row-actions"><button type="button" onClick={() => setEditing(item)}><Pencil size={13} />修改</button><button type="button" className="danger" onClick={() => setDeleteTarget(item)}><Trash2 size={13} />删除</button></div></div></div>
            <div className="admin-deal-meta"><span>供应商：{item.supplier_name || "未填写"}</span><span>品牌：{productBrands(item.products)}</span>{item.salesperson_name ? <span>销售：{item.salesperson_name}</span> : null}{item.deal_type ? <span>类型：{item.deal_type}</span> : null}<span>产品：{item.products.length} 项</span></div>
            <details><summary>查看产品与订单详情</summary><dl className="admin-deal-detail-grid"><div><dt>成交单位</dt><dd>{item.customer_name}</dd></div><div><dt>省市</dt><dd>{[item.province, item.city].filter(Boolean).join(" ") || "未填写"}</dd></div><div><dt>签约日期</dt><dd>{item.signed_at || "未填写"}</dd></div><div><dt>项目总价</dt><dd>{currency(item.total_amount)}</dd></div><div><dt>供应商</dt><dd>{item.supplier_name || "未填写"}</dd></div><div><dt>负责销售</dt><dd>{item.salesperson_name || "未填写"}</dd></div><div><dt>成交类型</dt><dd>{item.deal_type || "未填写"}</dd></div><div><dt>产品数量</dt><dd>{item.products.length} 项</dd></div></dl><div className="admin-deal-products">{item.products.length ? item.products.map((productItem, index) => <div key={productItem.id}><strong>{index + 1}. {productItem.product_name}</strong><span>品牌：{productItem.brand || "未填写"}</span><span>规格：{productItem.specification_model || "未填写"}</span><span>单价：{productItem.unit_price ? currency(productItem.unit_price) : "未填写"}</span><span>数量：{productItem.quantity || "未填写"}</span><span>产品总价：{currency(productItem.line_total)}</span></div>) : <p>尚未添加产品明细。</p>}</div><div className="admin-deal-detail-copy"><p><strong>来源</strong>{item.source_reference || "未填写"}{item.source_url ? <> · <a href={item.source_url} target="_blank" rel="noreferrer">查看原始链接</a></> : null}</p><p><strong>备注</strong>{item.notes || "未填写"}</p></div></details>
          </article>)}
        </div>
      )}
      <nav className="admin-deal-pagination" aria-label="成交订单分页"><span>第 {pageNumber} / {totalPages} 页</span><button type="button" disabled={pageNumber <= 1 || loading} onClick={() => setPageNumber((value) => Math.max(1, value - 1))}>上一页</button><button type="button" disabled={pageNumber >= totalPages || loading} onClick={() => setPageNumber((value) => Math.min(totalPages, value + 1))}>下一页</button></nav>
      {creating ? <AdminDealFormDialog defaultSeller={seller === "competitor" ? "competitor" : "unite"} item={null} onCancel={() => setCreating(false)} onSaved={saveDeal} /> : null}
      {editing ? <AdminDealFormDialog key={`${editing.seller_type}-${editing.id}`} defaultSeller={editing.seller_type} item={editing} onCancel={() => setEditing(null)} onSaved={saveDeal} /> : null}
      {deleteTarget ? <AdminDealDeleteDialog key={`${deleteTarget.seller_type}-${deleteTarget.id}`} item={deleteTarget} onCancel={() => setDeleteTarget(null)} onConfirm={deleteDeal} /> : null}
    </section>
  );
}
