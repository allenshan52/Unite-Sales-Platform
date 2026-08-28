"use client";

/** 同行市场地图：以高德 Marker 叠加同行据点、成交单位与优纳特客户。 */

import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";

import {
  apiFetch,
  type CompetitorCustomer,
  type CompetitorDeal,
  type CompetitorDetail,
  type CompetitorMapItem,
  type PublicWonCustomerMapPoint,
} from "@/lib/api";
import { destroyAmapMap, loadAmapNamespace } from "@/lib/amap";
import { escapeHtml } from "@/lib/html";

interface ClickableOverlay {
  on(event: "click", handler: () => void): void;
}

interface CompetitorAmapMap {
  add(overlays: unknown | unknown[]): void;
  addControl(control: unknown): void;
  destroy(): void;
  remove(overlays: unknown | unknown[]): void;
  setFitView(overlays?: unknown[], immediately?: boolean, avoid?: number[], maxZoom?: number): void;
  setZoomAndCenter(zoom: number, center: [number, number]): void;
  zoomIn(): void;
  zoomOut(): void;
}

interface CompetitorAmapNamespace {
  getConfig(): { appname?: string };
  Map: new (container: HTMLElement, options: Record<string, unknown>) => CompetitorAmapMap;
  Marker: new (options: Record<string, unknown>) => ClickableOverlay;
  Scale: new () => unknown;
}

type PanelTab = "sites" | "customers" | "regions";
type Runtime = { AMap: CompetitorAmapNamespace; map: CompetitorAmapMap; overlays: unknown[] };

const currencyFormatter = new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 });
const dateFormatter = new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" });

/** 汇总同行单位的逐笔交易额，保持展示口径与后端 NUMERIC 数据一致。 */
function customerAmount(customer: CompetitorCustomer): number {
  return customer.deals.reduce((total, deal) => total + Number(deal.amount), 0);
}

/** 将接口日期转换为中文日期，空值继续显示明确的待补状态。 */
function formatDealDate(value: string | null): string {
  return value ? dateFormatter.format(new Date(`${value}T00:00:00`)) : "日期待补";
}

/** 提供关闭与重置动作所需的同一套线性图标。 */
function CompetitorIcon({ name }: { name: "close" | "customer" | "reset" | "radar" }) {
  const paths = {
    close: <path d="m5 5 14 14M19 5 5 19" />,
    customer: <><circle cx="9" cy="8" r="3" /><path d="M3.5 19c.5-4 2.4-6 5.5-6s5 2 5.5 6" /><circle cx="17" cy="9" r="2" /><path d="M15.5 14.5c2.8-.7 4.7.7 5 3.5" /></>,
    reset: <><path d="M4 12a8 8 0 1 0 2.3-5.7L4 8" /><path d="M4 3v5h5" /></>,
    radar: <><circle cx="12" cy="12" r="8" /><circle cx="12" cy="12" r="3" /><path d="M12 4v3m0 10v3m8-8h-3M7 12H4" /></>,
  };
  return <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

/** 统一呈现情报来源和置信度，避免把区域强度误当作信息可信度。 */
function IntelligenceMeta({ source, reference, confidence }: { source: string; reference: string; confidence: string }) {
  return <div className="competitor-intelligence-meta"><span>{source}</span><span>置信度 {confidence}</span><p>{reference}</p></div>;
}

/** 逐笔展示同行项目、产品、数量、供应商、价格和完整来源，缺图记录保留可辨识占位。 */
function CompetitorDealCard({ deal }: { deal: CompetitorDeal }) {
  const products = deal.products?.length ? deal.products : [{ id: `${deal.id}-legacy`, product_name: deal.product_name || "产品名称待补", specification_model: deal.specification_model ?? null, product_image_url: deal.product_image_url ?? null, unit_price: deal.unit_price ?? null, quantity: deal.quantity ?? null, line_total: deal.amount }];
  const firstProduct = products[0];
  const productLabel = firstProduct?.product_name || "产品名称待补";
  return (
    <article className="competitor-deal-card">
      <div className="competitor-deal-overview">
        {firstProduct?.product_image_url
          ? <img className="competitor-product-image" src={firstProduct.product_image_url} alt={`${productLabel}产品图片`} width="112" height="78" />
          : <div className="competitor-product-image is-empty" role="img" aria-label="暂无产品图片">暂无产品图片</div>}
        <div><small>项目名称</small><h4>{deal.project_name}</h4><span>{deal.deal_type}</span></div>
      </div>
      {products.map((product, index) => <dl className="competitor-deal-fields" key={product.id}>
        <div><dt>产品 {index + 1}</dt><dd>{product.product_name}</dd></div><div><dt>品牌</dt><dd>{product.brand || "未记录"}</dd></div>
        <div><dt>规格型号</dt><dd>{product.specification_model || "规格型号待补"}</dd></div>
        <div><dt>产品单价</dt><dd>{product.unit_price ? currencyFormatter.format(Number(product.unit_price)) : "单价待补"}</dd></div>
        <div><dt>数量</dt><dd>{product.quantity ? Number(product.quantity).toLocaleString("zh-CN", { maximumFractionDigits: 3 }) : "数量待补"}</dd></div>
        <div><dt>产品总价</dt><dd>{currencyFormatter.format(Number(product.line_total))}</dd></div>
      </dl>)}
      <dl className="competitor-deal-fields">
        <div><dt>供应商</dt><dd>{deal.supplier_name || "供应商待补"}</dd></div>
        <div><dt>项目总价</dt><dd className="is-amount">{currencyFormatter.format(Number(deal.amount))}</dd></div>
        <div><dt>中标时间</dt><dd>{formatDealDate(deal.signed_at)}</dd></div>
        <div><dt>成交类型</dt><dd>{deal.deal_type}</dd></div>
      </dl>
      <div className="competitor-deal-source">
        <span>来源：{deal.source_type}</span><span>置信度 {deal.confidence}</span>
        <p>{deal.source_reference}</p>
        {deal.source_url ? <a href={deal.source_url} target="_blank" rel="noreferrer">查看来源</a> : <small>暂无来源链接</small>}
        {deal.notes ? <p>备注：{deal.notes}</p> : null}
      </div>
    </article>
  );
}

/** 优纳特客户浮层只展示正式单位、主地点和实际成交项目，避免混入预计商机。 */
function UniteCustomerPanel({ customer, onClose }: { customer: PublicWonCustomerMapPoint; onClose: () => void }) {
  const latestSignedAt = customer.deals.find((deal) => deal.signed_at)?.signed_at ?? "日期待补";
  const location = [customer.province, customer.city, customer.district].filter(Boolean).join(" · ");
  return (
    <aside className="competitor-panel unite-customer-panel" aria-label={`${customer.name}优纳特客户详情`}>
      <header>
        <div><i /><h2>{customer.name}</h2><p>优纳特已成交客户 · 数据来自正式单位库</p></div>
        <button type="button" aria-label="关闭优纳特客户详情" onClick={onClose}><CompetitorIcon name="close" /></button>
      </header>
      <div className="competitor-summary-strip">
        <span><b>{customer.deal_count}</b> 笔成交</span>
        <span><b>{latestSignedAt}</b> 最近签约</span>
        <span><b>{currencyFormatter.format(Number(customer.actual_sales_amount))}</b> 实际成交额</span>
      </div>
      <div className="competitor-panel-body">
        <section className="competitor-focus-detail">
          <div className="competitor-customer-heading"><span className="competitor-entity-type">{customer.customer_status}</span><span className="is-linked">{customer.review_status}</span></div>
          <h3>{customer.name}</h3>
          <p>{customer.address || location || "地址待补"}</p>
          <dl>
            <div><dt>单位类型</dt><dd>{customer.organization_type}</dd></div>
            <div><dt>所属行业</dt><dd>{customer.industry || "行业待补"}</dd></div>
            <div><dt>所在区域</dt><dd>{location || "区域待补"}</dd></div>
          </dl>
        </section>
        <section className="competitor-deals">
          <h3>优纳特成交记录</h3>
          {customer.deals.map((deal) => <article key={deal.id}><div><b>{deal.name}</b><strong>{currencyFormatter.format(Number(deal.contract_amount))}</strong></div><p>{deal.project_detail || "暂无项目说明"}</p><small>{deal.signed_at || "日期待补"} · 实际成交</small></article>)}
        </section>
      </div>
      <button className="competitor-reset-button" type="button" onClick={onClose}><CompetitorIcon name="reset" />关闭客户详情</button>
    </aside>
  );
}

/** 同行浮层通过三个 Tab 展示据点、成交单位下拉详情和算法生成的竞争区域。 */
function CompetitorPanel({ detail, activeTab, selectedId, onTab, onSelect, onClose }: {
  detail: CompetitorDetail;
  activeTab: PanelTab;
  selectedId: string | null;
  onTab: (tab: PanelTab) => void;
  onSelect: (tab: PanelTab, id: string) => void;
  onClose: () => void;
}) {
  const selectedSite = detail.sites.find((site) => site.id === selectedId) ?? detail.sites[0];
  const selectedCustomer = detail.customers.find((customer) => customer.id === selectedId) ?? detail.customers[0];
  const selectedRegion = detail.strength_regions.find((region) => region.id === selectedId) ?? detail.strength_regions[0];

  return (
    <aside className="competitor-panel" aria-label={`${detail.name}同行市场详情`}>
      <header>
        <div><i style={{ background: detail.color }} /><h2>{detail.name}</h2><p>{detail.description}</p>{detail.website_url ? <a href={detail.website_url} target="_blank" rel="noreferrer">访问公司官网</a> : null}</div>
        <button type="button" aria-label="关闭同行市场详情" onClick={onClose}><CompetitorIcon name="close" /></button>
      </header>
      <div className="competitor-summary-strip">
        <span><b>{detail.summary.customer_count}</b> 个成交单位</span>
        <span><b>{detail.summary.deal_count}</b> 笔交易</span>
        <span><b>{currencyFormatter.format(Number(detail.summary.total_amount))}</b> 交易额</span>
      </div>
      <nav className="competitor-panel-tabs" aria-label="同行详情分类">
        <button type="button" className={activeTab === "sites" ? "selected" : ""} onClick={() => onTab("sites")}>同行据点 <b>{detail.summary.site_count}</b></button>
        <button type="button" className={activeTab === "customers" ? "selected" : ""} onClick={() => onTab("customers")}>成交单位 <b>{detail.summary.customer_count}</b></button>
        <button type="button" className={activeTab === "regions" ? "selected" : ""} onClick={() => onTab("regions")}>竞争区域 <b>{detail.strength_regions.length}</b></button>
      </nav>

      {activeTab === "sites" && selectedSite ? (
        <div className="competitor-panel-body">
          <section className="competitor-focus-detail">
            <span className="competitor-entity-type">{selectedSite.site_type}</span>
            <h3>{selectedSite.name}</h3>
            <p>{selectedSite.address}</p>
            <dl><div><dt>位置</dt><dd>{selectedSite.province} · {selectedSite.city}</dd></div><div><dt>备注</dt><dd>{selectedSite.notes || "暂无备注"}</dd></div></dl>
            <IntelligenceMeta source={selectedSite.source_type} reference={selectedSite.source_reference} confidence={selectedSite.confidence} />
          </section>
          <div className="competitor-entity-list" aria-label="同行据点列表">
            {detail.sites.map((site) => <button type="button" className={site.id === selectedSite.id ? "selected" : ""} key={site.id} onClick={() => onSelect("sites", site.id)}><i style={{ background: detail.color }} /><span><b>{site.name}</b><small>{site.site_type} · {site.city}</small></span></button>)}
          </div>
        </div>
      ) : null}

      {activeTab === "customers" && selectedCustomer ? (
        <div className="competitor-panel-body">
          <label className="competitor-customer-dropdown">
            <span>选择成交单位</span>
            <select aria-label="选择同行成交单位" value={selectedCustomer.id} onChange={(event) => onSelect("customers", event.target.value)}>
              {detail.customers.map((customer) => <option value={customer.id} key={customer.id}>{customer.name} · {customer.city} · {currencyFormatter.format(customerAmount(customer))}</option>)}
            </select>
          </label>
          <section className="competitor-focus-detail">
            <div className="competitor-customer-heading"><span className="competitor-entity-type">{selectedCustomer.customer_level}</span><span className={selectedCustomer.linked_organization_id ? "is-linked" : "is-unlinked"}>{selectedCustomer.linked_organization_id ? "已关联正式单位" : "尚未关联正式单位"}</span></div>
            <h3>{selectedCustomer.name}</h3>
            <p>{selectedCustomer.address}</p>
            {selectedCustomer.linked_organization_name ? <p className="competitor-linked-org">单位数据库：{selectedCustomer.linked_organization_name} · 匹配置信度 {selectedCustomer.match_confidence}</p> : null}
          </section>
          <section className="competitor-deals">
            <h3>成交记录</h3>
            {selectedCustomer.deals.map((deal) => <CompetitorDealCard deal={deal} key={deal.id} />)}
          </section>
        </div>
      ) : null}

      {activeTab === "regions" && selectedRegion ? (
        <div className="competitor-panel-body">
          <section className="competitor-focus-detail">
            <span className={`competitor-strength-tag strength-${selectedRegion.strength_level}`}>{selectedRegion.strength_level}势区域</span>
            <h3>{selectedRegion.city || selectedRegion.province}</h3>
            <p>{selectedRegion.region_level}级活动聚合 · {selectedRegion.basis}</p>
            <dl>
              <div><dt>综合评分</dt><dd>{(Number(selectedRegion.score) * 100).toFixed(2)}%</dd></div>
              <div><dt>区域证据</dt><dd>{selectedRegion.site_count} 个据点 · {selectedRegion.customer_count} 个成交单位</dd></div>
              <div><dt>区域交易额</dt><dd>{currencyFormatter.format(Number(selectedRegion.total_amount))}</dd></div>
            </dl>
            <IntelligenceMeta source={selectedRegion.source_type} reference={selectedRegion.source_reference} confidence={selectedRegion.confidence} />
          </section>
          <div className="competitor-entity-list" aria-label="同行竞争区域列表">
            {detail.strength_regions.map((region) => <button type="button" className={region.id === selectedRegion.id ? "selected" : ""} key={region.id} onClick={() => onSelect("regions", region.id)}><span className={`competitor-region-swatch strength-${region.strength_level}`} style={{ "--competitor-color": detail.color } as CSSProperties} /><span><b>{region.city || region.province}</b><small>{region.strength_level}势 · 评分 {(Number(region.score) * 100).toFixed(1)}%</small></span></button>)}
          </div>
        </div>
      ) : null}

      <button className="competitor-reset-button" type="button" onClick={onClose}><CompetitorIcon name="reset" />返回全国同行</button>
    </aside>
  );
}

/** 第四地图入口负责同行情报与正式已成交客户双图层的加载、点击和清理闭环。 */
export function HomeCompetitorMarketMap() {
  const containerRef = useRef<HTMLDivElement>(null);
  const runtimeRef = useRef<Runtime | null>(null);
  const detailRequestRef = useRef(0);
  const customerRequestRef = useRef(0);
  const [mapStatus, setMapStatus] = useState<"loading" | "ready" | "error">("loading");
  const [mapAttempt, setMapAttempt] = useState(0);
  const [items, setItems] = useState<CompetitorMapItem[]>([]);
  const [detail, setDetail] = useState<CompetitorDetail | null>(null);
  const [activeTab, setActiveTab] = useState<PanelTab>("sites");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [listStatus, setListStatus] = useState<"loading" | "ready" | "error">("loading");
  const [detailStatus, setDetailStatus] = useState<"idle" | "loading" | "error">("idle");
  const [wonCustomers, setWonCustomers] = useState<PublicWonCustomerMapPoint[]>([]);
  const [showUniteCustomers, setShowUniteCustomers] = useState(false);
  const [selectedUniteCustomer, setSelectedUniteCustomer] = useState<PublicWonCustomerMapPoint | null>(null);
  const [customerStatus, setCustomerStatus] = useState<"idle" | "loading" | "error" | "empty">("idle");
  const [customerMessage, setCustomerMessage] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [listAttempt, setListAttempt] = useState(0);

  /** 清除单同行覆盖物状态，恢复固定十个主要据点。 */
  const resetCompetitor = useCallback(() => {
    detailRequestRef.current += 1;
    setDetail(null);
    setSelectedId(null);
    setActiveTab("sites");
    setDetailStatus("idle");
    setSelectedUniteCustomer(null);
    setMessage(null);
  }, []);

  /** 按需读取正式单位库中的已成交客户；再次点击仅隐藏图层并保留本地缓存。 */
  const toggleUniteCustomers = useCallback(async () => {
    if (showUniteCustomers) {
      setShowUniteCustomers(false);
      setSelectedUniteCustomer(null);
      return;
    }
    if (wonCustomers.length > 0) {
      setShowUniteCustomers(true);
      setCustomerStatus("idle");
      return;
    }
    const requestId = customerRequestRef.current + 1;
    customerRequestRef.current = requestId;
    setCustomerStatus("loading");
    setCustomerMessage(null);
    try {
      const customers = await apiFetch<PublicWonCustomerMapPoint[]>("/public/organizations/won-customers");
      if (customerRequestRef.current !== requestId) return;
      if (customers.length === 0) {
        setCustomerStatus("empty");
        setCustomerMessage("暂无已成交客户点位，请先在单位数据库维护成交状态、项目和主地点");
        return;
      }
      setWonCustomers(customers);
      setShowUniteCustomers(true);
      setCustomerStatus("idle");
    } catch (error: unknown) {
      if (customerRequestRef.current !== requestId) return;
      setCustomerStatus("error");
      setCustomerMessage(error instanceof Error ? error.message : "优纳特客户加载失败");
    }
  }, [showUniteCustomers, wonCustomers]);

  /** 点击或筛选同行后按需读取其完整竞争情报，避免首屏传输全部成交记录。 */
  const openCompetitor = useCallback(async (
    competitorId: string,
    initialSelection?: { tab: PanelTab; id: string },
  ) => {
    const requestId = detailRequestRef.current + 1;
    detailRequestRef.current = requestId;
    setDetailStatus("loading");
    setSelectedUniteCustomer(null);
    setMessage(null);
    try {
      const nextDetail = await apiFetch<CompetitorDetail>(`/public/competitors/${competitorId}`);
      if (detailRequestRef.current !== requestId) return;
      setDetail(nextDetail);
      setActiveTab(initialSelection?.tab ?? "sites");
      setSelectedId(initialSelection?.id ?? nextDetail.sites[0]?.id ?? null);
      setDetailStatus("idle");
    } catch (error: unknown) {
      if (detailRequestRef.current !== requestId) return;
      setDetailStatus("error");
      setMessage(error instanceof Error ? error.message : "同行详情加载失败");
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    void apiFetch<CompetitorMapItem[]>("/public/competitors", { signal: controller.signal })
      .then((data) => { setItems(data); setListStatus("ready"); })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setListStatus("error");
        setMessage(error instanceof Error ? error.message : "同行据点加载失败");
      });
    return () => controller.abort();
  }, [listAttempt]);

  useEffect(() => {
    let disposed = false;
    if (!containerRef.current) return;
    setMapStatus("loading");
    void loadAmapNamespace<CompetitorAmapNamespace>(["AMap.Scale"])
      .then((AMap) => {
        if (disposed || !containerRef.current) return;
        const map = new AMap.Map(containerRef.current, { viewMode: "2D", zoom: 4.35, center: [104.1, 35.6], mapStyle: "amap://styles/light", showLabel: true });
        map.addControl(new AMap.Scale());
        runtimeRef.current = { AMap, map, overlays: [] };
        setMapStatus("ready");
      })
      .catch((error: unknown) => { if (!disposed) { setMapStatus("error"); setMessage(error instanceof Error ? error.message : "同行地图加载失败"); } });
    return () => {
      disposed = true;
      destroyAmapMap(runtimeRef.current?.map ?? null);
      runtimeRef.current = null;
    };
  }, [mapAttempt]);

  useEffect(() => {
    const runtime = runtimeRef.current;
    if (!runtime || mapStatus !== "ready" || listStatus !== "ready") return;
    if (runtime.overlays.length) runtime.map.remove(runtime.overlays);
    runtime.overlays = [];

    // 优纳特客户保持为独立可叠加图层，同行视野调整不把全国客户误算进边界。
    const uniteMarkers = showUniteCustomers ? wonCustomers.map((customer) => {
      const marker = new runtime.AMap.Marker({
        position: [customer.longitude, customer.latitude],
        anchor: "bottom-center",
        zIndex: 145,
        content: `<div class="unite-customer-marker"><b>${escapeHtml(customer.name)}</b><span></span></div>`,
      });
      marker.on("click", () => setSelectedUniteCustomer(customer));
      return marker;
    }) : [];

    if (!detail) {
      const markers = items.map((item) => {
        const marker = new runtime.AMap.Marker({ position: [item.primary_site.longitude, item.primary_site.latitude], anchor: "bottom-center", zIndex: 120, content: `<div class="competitor-marker is-primary" style="--competitor-color:${item.color}"><span></span><b>${escapeHtml(item.name)}</b></div>` });
        marker.on("click", () => { void openCompetitor(item.id, { tab: "sites", id: item.primary_site.id }); });
        return marker;
      });
      const overviewOverlays = [...markers, ...uniteMarkers];
      runtime.map.add(overviewOverlays);
      runtime.overlays = overviewOverlays;
      runtime.map.setZoomAndCenter(4.35, [104.1, 35.6]);
      return;
    }

    const markers: unknown[] = [];
    detail.sites.forEach((site) => {
      const isHeadquarters = site.is_primary || site.site_type === "总部";
      const abbreviation = site.site_type === "分部" ? "分" : "服";
      const markerLabel = isHeadquarters ? detail.name : site.name;
      const markerMeta = isHeadquarters ? "" : `<small>${escapeHtml(site.site_type)}</small>`;
      const marker = new runtime.AMap.Marker({ position: [site.longitude, site.latitude], anchor: "bottom-center", zIndex: 130, content: `<div class="competitor-marker ${isHeadquarters ? "is-primary" : "is-site"}" style="--competitor-color:${detail.color}"><span>${isHeadquarters ? "" : abbreviation}</span><b>${escapeHtml(markerLabel)}</b>${markerMeta}</div>` });
      marker.on("click", () => { setSelectedUniteCustomer(null); setActiveTab("sites"); setSelectedId(site.id); });
      markers.push(marker);
    });
    detail.customers.forEach((customer) => {
      const marker = new runtime.AMap.Marker({ position: [customer.longitude, customer.latitude], anchor: "center", zIndex: 115, content: `<div class="competitor-customer-marker" style="--competitor-color:${detail.color}"><span>${escapeHtml(customer.customer_level.slice(0, 1))}</span><b>${escapeHtml(customer.name)}</b></div>` });
      marker.on("click", () => { setSelectedUniteCustomer(null); setActiveTab("customers"); setSelectedId(customer.id); });
      markers.push(marker);
    });
    runtime.map.add([...markers, ...uniteMarkers]);
    runtime.overlays = [...markers, ...uniteMarkers];
    // 按当前同行的据点与成交单位联合聚焦，独立客户图层不改变同行视野。
    const avoid = window.innerWidth <= 900 ? [96, 430, 80, 80] : [160, 140, 140, 500];
    runtime.map.setFitView(markers, false, avoid, 10);
  }, [detail, items, listStatus, mapStatus, openCompetitor, showUniteCustomers, wonCustomers]);

  useEffect(() => {
    /** Esc 优先关闭当前详情，其次恢复同行总览，最后隐藏独立客户图层。 */
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (selectedUniteCustomer) setSelectedUniteCustomer(null);
      else if (detail) resetCompetitor();
      else if (showUniteCustomers) setShowUniteCustomers(false);
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [detail, resetCompetitor, selectedUniteCustomer, showUniteCustomers]);

  /** 同步面板 Tab 与当前实体选择，保证地图 Pin 和详情列表共用同一状态。 */
  function selectEntity(tab: PanelTab, id: string) {
    setActiveTab(tab);
    setSelectedId(id);
  }

  return (
    <div className="home-competitor-market-map">
      <div ref={containerRef} className="competitor-map-canvas" aria-label="全国同行市场点位地图" />
      <section className="group-map-title-card competitor-map-title-card" aria-labelledby="competitor-map-title">
        <div className="group-map-heading">
          <span>2026 / 同行市场</span>
          <h1 id="competitor-map-title">同行市场版图</h1>
        </div>
        {mapStatus === "ready" && listStatus === "ready" && items.length > 0 ? (
          <>
            <div className="competitor-map-toolbar">
              <button className={`competitor-customer-toggle ${showUniteCustomers ? "selected" : ""}`} type="button" aria-pressed={showUniteCustomers} disabled={customerStatus === "loading"} onClick={() => { void toggleUniteCustomers(); }}><CompetitorIcon name="customer" /><span>{customerStatus === "loading" ? "正在加载客户…" : showUniteCustomers ? "隐藏优纳特客户" : "显示优纳特客户"}</span></button>
            </div>
            <label className="group-map-selector competitor-map-selector">
              <span><CompetitorIcon name="radar" />选择同行</span>
              <select aria-label="按同行名称筛选" value={detail?.id ?? ""} onChange={(event) => { const item = items.find((candidate) => candidate.id === event.target.value); if (item) void openCompetitor(item.id, { tab: "sites", id: item.primary_site.id }); else resetCompetitor(); }}><option value="">全部同行据点（{items.length}）</option>{items.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select>
            </label>
          </>
        ) : null}
      </section>
      {mapStatus === "ready" ? (
        <div className={`group-map-zoom competitor-map-zoom ${detail || selectedUniteCustomer ? "has-panel" : ""}`} role="group" aria-label="同行地图缩放">
          <button type="button" aria-label="放大同行地图" onClick={() => runtimeRef.current?.map.zoomIn()}>＋</button>
          <button type="button" aria-label="缩小同行地图" onClick={() => runtimeRef.current?.map.zoomOut()}>−</button>
        </div>
      ) : null}
      {detailStatus === "loading" ? <div className="group-map-loading" role="status"><i />正在展开同行市场版图…</div> : null}
      {detailStatus === "error" ? <div className="group-map-loading is-error" role="alert"><b>{message}</b><button type="button" onClick={() => setDetailStatus("idle")}>关闭</button></div> : null}
      {customerStatus === "loading" ? <div className="group-map-loading" role="status"><i />正在读取优纳特已成交客户…</div> : null}
      {customerStatus === "error" || customerStatus === "empty" ? <div className="group-map-loading is-error" role="alert"><b>{customerMessage}</b><button type="button" onClick={() => { setCustomerStatus("idle"); setCustomerMessage(null); }}>关闭</button></div> : null}
      {mapStatus !== "ready" || listStatus !== "ready" || items.length === 0 ? (
        <div className="group-map-state" aria-live="polite"><CompetitorIcon name="radar" /><strong>{mapStatus === "loading" || listStatus === "loading" ? "正在读取同行主要据点" : mapStatus === "error" || listStatus === "error" ? "同行市场地图暂不可用" : "暂无同行市场数据"}</strong><span>{mapStatus === "loading" || listStatus === "loading" ? "正在连接地图和同行数据库" : message ?? "请先维护同行与主要据点"}</span>{mapStatus === "error" || listStatus === "error" ? <button type="button" onClick={() => { setMessage(null); if (listStatus === "error") { setListStatus("loading"); setListAttempt((value) => value + 1); } if (mapStatus === "error") { setMapStatus("loading"); setMapAttempt((value) => value + 1); } }}>重新加载</button> : null}</div>
      ) : null}
      {selectedUniteCustomer
        ? <UniteCustomerPanel customer={selectedUniteCustomer} onClose={() => setSelectedUniteCustomer(null)} />
        : detail ? <CompetitorPanel detail={detail} activeTab={activeTab} selectedId={selectedId} onTab={(tab) => { setActiveTab(tab); setSelectedId(null); }} onSelect={selectEntity} onClose={resetCompetitor} /> : null}
    </div>
  );
}
