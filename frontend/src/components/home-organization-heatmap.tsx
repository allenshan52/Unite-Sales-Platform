"use client";

/** 首页省级业务热力图：在实际成交额与优纳特采购意向两个互斥指标间切换，并保留既有渠道点位。 */
import { useEffect, useMemo, useState, type CSSProperties } from "react";
import chinaMap from "@svg-maps/china";
import Image from "next/image";
import {
  apiFetch,
  queryString,
  type ChannelPartnerMapPoint,
  type ChannelPartnerType,
  type CooperationLevel,
  type DealHeatmapOrder,
  type DealHeatmapProvinceDetail,
  type DealHeatmapSeller,
  type DealHeatmapSummary,
  type SalesOfficeLocation,
} from "@/lib/api";

type HeatLevelKey = "very-high" | "high" | "medium" | "low" | "very-low";
type HeatmapMetric = "signed" | "intention";

type HeatLevel = {
  key: HeatLevelKey;
  label: string;
  rangeLabel: string;
  min: number;
  max: number;
  color: string;
};

/** 固定金额档位让不同公司与不同时间的省份颜色保持可直接比较。 */
export const dealHeatLevels: readonly HeatLevel[] = [
  { key: "very-high", label: "极高", rangeLabel: "400万元+", min: 4_000_000, max: Number.POSITIVE_INFINITY, color: "#a93420" },
  { key: "high", label: "高", rangeLabel: "300–400万元", min: 3_000_000, max: 3_999_999.99, color: "#d95230" },
  { key: "medium", label: "中", rangeLabel: "250–300万元", min: 2_500_000, max: 2_999_999.99, color: "#ed8057" },
  { key: "low", label: "低", rangeLabel: "150–250万元", min: 1_500_000, max: 2_499_999.99, color: "#f4b091" },
  { key: "very-low", label: "较低", rangeLabel: "1–150万元", min: 0.01, max: 1_499_999.99, color: "#f9d9c8" },
];

/** 意向模式使用由浅到深的相对色阶，避免把成交金额档位错误套用于预计采购额。 */
const intentionHeatColors = ["#dcefe9", "#b6ddd1", "#7fc5b3", "#429d86", "#14735f"] as const;

export const provinceNames: Record<string, string> = {
  anhui: "安徽省", beijing: "北京市", chongqing: "重庆市", fujian: "福建省", gansu: "甘肃省",
  guangdong: "广东省", "guangxi-zhuang": "广西壮族自治区", guizhou: "贵州省", hainan: "海南省",
  hebei: "河北省", heilongjiang: "黑龙江省", henan: "河南省", "hong-kong": "香港特别行政区",
  hubei: "湖北省", hunan: "湖南省", jiangsu: "江苏省", jiangxi: "江西省", jilin: "吉林省",
  liaoning: "辽宁省", macau: "澳门特别行政区", "nei-mongol": "内蒙古自治区",
  "ningxia-hui": "宁夏回族自治区", quinghai: "青海省", shaanxi: "陕西省", shandong: "山东省",
  shanghai: "上海市", shanxi: "山西省", sichuan: "四川省", tianjin: "天津市",
  "xinjiang-uygur": "新疆维吾尔自治区", xizang: "西藏自治区", yunnan: "云南省", zhejiang: "浙江省",
};

const allLevelKeys = dealHeatLevels.map((level) => level.key);
const heatmapZoomMin = 1;
const heatmapZoomMax = 1.75;
const heatmapZoomStep = 0.15;
const salesCoverageKmPerSvgUnit = 8.5;
const mapLongitudeOffset = -975.007848;
const mapLongitudeScale = 13.038228;
const mapLatitudeOffset = 807.719623;
const mapMercatorScale = -735.840147;
const channelPartnerTypes: readonly ChannelPartnerType[] = ["经销商", "代理商", "合作伙伴"];
const cooperationLevels: readonly CooperationLevel[] = ["一级", "二级", "三级"];
const channelPartnerColors: Record<ChannelPartnerType, string> = { 经销商: "#15967f", 代理商: "#875bd4", 合作伙伴: "#ffffff" };
const channelPartnerContrastColors: Record<ChannelPartnerType, string> = { 经销商: "#ffffff", 代理商: "#ffffff", 合作伙伴: "#6f6259" };
const currencyFormatter = new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 });
const wanAmountFormatter = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 1 });

type ProjectedSalesOffice = SalesOfficeLocation & { x: number; y: number; radius: number };
type ProjectedChannelPartner = ChannelPartnerMapPoint & { x: number; y: number };

/** 将 API 的十进制金额字符串转换为仅用于展示分档的数值。 */
function amountValue(amount: string): number {
  const value = Number(amount);
  return Number.isFinite(value) ? value : 0;
}

/** 按固定业务阈值返回实际成交金额档位。 */
function levelForAmount(amount: string): HeatLevel | undefined {
  const value = amountValue(amount);
  return dealHeatLevels.find((level) => value >= level.min && value <= level.max);
}

/** 按当前意向数据最大值生成五档绿色，保证不同数据规模下仍可辨认区域差异。 */
function intentionColorForAmount(amount: string, maximum: number): string {
  const value = amountValue(amount);
  if (value <= 0 || maximum <= 0) return "#f1ece8";
  const index = Math.min(intentionHeatColors.length - 1, Math.max(0, Math.ceil(value / maximum * intentionHeatColors.length) - 1));
  return intentionHeatColors[index];
}

/** 将相对绿色档位换算为万元区间，使图例金额与地图着色边界保持一致。 */
function intentionRangeLabel(index: number, maximum: number): string {
  const lower = maximum * index / intentionHeatColors.length / 10_000;
  const upper = maximum * (index + 1) / intentionHeatColors.length / 10_000;
  return `${wanAmountFormatter.format(lower)}–${wanAmountFormatter.format(upper)}万元`;
}

/** 使用中国地区货币格式展示合同与预计金额。 */
function formatCurrency(amount: string | null): string {
  return amount === null ? "—" : currencyFormatter.format(amountValue(amount));
}

/** 统一详情日期显示，空日期不制造虚假时间。 */
function formatDate(value: string | null): string {
  return value ? new Intl.DateTimeFormat("zh-CN").format(new Date(`${value}T00:00:00`)) : "待确认";
}

/** 识别请求取消，避免切换公司或省份时把旧请求误报为错误。 */
function isAbortError(error: unknown): boolean {
  return error instanceof DOMException && error.name === "AbortError";
}

/** 复用底图校准后的 Mercator 投影，将城市经纬度转换为 SVG 坐标。 */
export function projectMapCoordinates(longitude: number, latitude: number): { x: number; y: number } {
  const latitudeRadians = latitude * Math.PI / 180;
  const mercatorLatitude = Math.log(Math.tan(Math.PI / 4 + latitudeRadians / 2));
  return {
    x: mapLongitudeOffset + mapLongitudeScale * longitude,
    y: mapLatitudeOffset + mapMercatorScale * mercatorLatitude,
  };
}

/** 投影销售常驻点并保留现有覆盖半径表现。 */
function projectSalesOffice(office: SalesOfficeLocation): ProjectedSalesOffice {
  return { ...office, ...projectMapCoordinates(office.longitude, office.latitude), radius: Math.max(18, office.coverage_radius_km / salesCoverageKmPerSvgUnit) };
}

/** 投影公开渠道点，使三类渠道继续以 Pin 标记位置。 */
function projectChannelPartner(partner: ChannelPartnerMapPoint): ProjectedChannelPartner {
  return { ...partner, ...projectMapCoordinates(partner.map_longitude, partner.map_latitude) };
}

/** 渲染同行成交的客户位置、官网、产品、来源与备注等公开详情。 */
function CompetitorOrderFields({ order, websiteUrl }: { order: DealHeatmapOrder; websiteUrl: string | null }) {
  const customerLocation = [order.customer_province, order.customer_city].filter(Boolean).join(" · ");
  const products = order.products?.length ? order.products : order.product_name ? [{ id: `${order.id}-legacy`, product_name: order.product_name, specification_model: order.specification_model ?? null, product_image_url: order.product_image_url ?? null, unit_price: order.unit_price ?? null, quantity: order.quantity ?? null, line_total: order.amount }] : [];

  return (
    <dl className="deal-order-fields">
      <div><dt>省市</dt><dd>{customerLocation || "未记录"}</dd></div>
      {products.map((product, index) => <div className="deal-order-wide" key={product.id}><dt>产品 {index + 1}</dt><dd>{product.product_name} · 品牌 {product.brand || "未记录"} · {product.specification_model || "规格未记录"} · 单价 {formatCurrency(product.unit_price)} · 数量 {product.quantity || "未记录"} · 总价 {formatCurrency(product.line_total)}</dd></div>)}
      <div><dt>供应商</dt><dd>{order.supplier_name ?? "未记录"}</dd></div>
      <div><dt>来源</dt><dd>{order.source_type ?? "未记录"}{order.confidence ? ` · 置信度${order.confidence}` : ""}</dd></div>
      <div className="deal-order-wide"><dt>同行官网</dt><dd>{websiteUrl ? <a href={websiteUrl} target="_blank" rel="noreferrer">访问官网</a> : "未记录"}</dd></div>
      {order.source_reference ? <div className="deal-order-wide"><dt>来源说明</dt><dd>{order.source_reference}</dd></div> : null}
      {order.source_url ? <div className="deal-order-wide"><dt>来源链接</dt><dd><a href={order.source_url} target="_blank" rel="noreferrer">打开来源</a></dd></div> : null}
      <div className="deal-order-wide"><dt>备注</dt><dd>{order.notes || "未记录"}</dd></div>
    </dl>
  );
}

/** 渲染成交与意向数据控制、SVG 热力层以及按需读取的省份逐笔详情。 */
export function HomeOrganizationHeatmap({
  active,
  salesOffices,
  salesOfficesLoading,
  salesOfficesError,
  channelPartners,
  channelPartnersLoading,
  channelPartnersError,
}: {
  active: boolean;
  salesOffices: SalesOfficeLocation[];
  salesOfficesLoading: boolean;
  salesOfficesError: string | null;
  channelPartners: ChannelPartnerMapPoint[];
  channelPartnersLoading: boolean;
  channelPartnersError: string | null;
}) {
  const [sellers, setSellers] = useState<DealHeatmapSeller[]>([]);
  const [sellerId, setSellerId] = useState("unite");
  const [selectedYear, setSelectedYear] = useState<number | null>(null);
  const [summary, setSummary] = useState<DealHeatmapSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const [selectedLevels, setSelectedLevels] = useState<HeatLevelKey[]>([...allLevelKeys]);
  const [metric, setMetric] = useState<HeatmapMetric>("signed");
  const [selectedProvince, setSelectedProvince] = useState<string | null>(null);
  const [detail, setDetail] = useState<DealHeatmapProvinceDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailRetryKey, setDetailRetryKey] = useState(0);
  const [zoom, setZoom] = useState(heatmapZoomMin);
  const [showSalesOffices, setShowSalesOffices] = useState(false);
  const [visibleChannelTypes, setVisibleChannelTypes] = useState<ChannelPartnerType[]>([]);
  const [cooperationLevel, setCooperationLevel] = useState<CooperationLevel | "">("");

  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();

    /** 卖方列表独立读取，使公司下拉菜单直接反映数据库中的启用同行。 */
    void apiFetch<DealHeatmapSeller[]>("/public/deal-heatmap/sellers", { signal: controller.signal })
      .then(setSellers)
      .catch((requestError: unknown) => {
        if (!isAbortError(requestError)) setError(requestError instanceof Error ? requestError.message : "成交公司列表加载失败");
      });
    return () => controller.abort();
  }, [active, retryKey]);

  useEffect(() => {
    if (!active) return;
    const controller = new AbortController();

    /** 公司或年份切换都从聚合接口读取同一金额口径，避免前端硬编码统计值。 */
    void apiFetch<DealHeatmapSummary>(`/public/deal-heatmap/provinces${queryString({ seller_id: sellerId, year: selectedYear ? String(selectedYear) : undefined })}`, { signal: controller.signal })
      .then(setSummary)
      .catch((requestError: unknown) => {
        if (!isAbortError(requestError)) setError(requestError instanceof Error ? requestError.message : "省级成交金额加载失败");
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [active, retryKey, selectedYear, sellerId]);

  useEffect(() => {
    if (!active || !selectedProvince) return;
    const controller = new AbortController();

    /** 省份点击后才读取同年份逐笔订单，控制首屏负载并防止详情串线。 */
    void apiFetch<DealHeatmapProvinceDetail>(
      `/public/deal-heatmap/provinces/${encodeURIComponent(selectedProvince)}${queryString({ seller_id: sellerId, year: selectedYear ? String(selectedYear) : undefined })}`,
      { signal: controller.signal },
    )
      .then(setDetail)
      .catch((requestError: unknown) => {
        if (!isAbortError(requestError)) setDetailError(requestError instanceof Error ? requestError.message : "省份订单明细加载失败");
      })
      .finally(() => {
        if (!controller.signal.aborted) setDetailLoading(false);
      });
    return () => controller.abort();
  }, [active, detailRetryKey, selectedProvince, selectedYear, sellerId]);

  useEffect(() => {
    if (!selectedProvince) return;
    /** Escape 为遮挡地图的详情卡提供稳定关闭路径。 */
    function closeDetail(event: KeyboardEvent) {
      if (event.key === "Escape") setSelectedProvince(null);
    }
    window.addEventListener("keydown", closeDetail);
    return () => window.removeEventListener("keydown", closeDetail);
  }, [selectedProvince]);

  const summariesByProvince = useMemo(
    () => new Map((summary?.provinces ?? []).map((province) => [province.province, province])),
    [summary],
  );
  const maximumIntentionAmount = useMemo(
    () => Math.max(0, ...(summary?.provinces ?? []).map((province) => amountValue(province.intention_amount))),
    [summary],
  );
  const selectedLocation = selectedProvince
    ? chinaMap.locations.find((location: { id: string; name: string; path: string }) => (provinceNames[location.id] ?? location.name) === selectedProvince)
    : undefined;
  const allSelected = selectedLevels.length === dealHeatLevels.length;
  const selectedLevelLabel = allSelected ? "全部金额档位" : selectedLevels.length === 0 ? "未选择档位" : `已选 ${selectedLevels.length} 个档位`;
  const zoomStyle = { "--heatmap-zoom": zoom } as CSSProperties;
  const projectedSalesOffices = useMemo(() => salesOffices.map(projectSalesOffice), [salesOffices]);
  const projectedChannelPartners = useMemo(
    () => channelPartners.map(projectChannelPartner).filter((partner) => visibleChannelTypes.includes(partner.partner_type) && (!cooperationLevel || partner.cooperation_level === cooperationLevel)),
    [channelPartners, cooperationLevel, visibleChannelTypes],
  );

  /** 同步某一金额档位的复选状态。 */
  function toggleLevel(key: HeatLevelKey, checked: boolean) {
    setSelectedLevels((current) => checked ? [...current, key] : current.filter((item) => item !== key));
  }

  /** 公司切换先清理旧汇总与详情，再由 effect 读取新卖方的数据库聚合。 */
  function selectSeller(nextSellerId: string) {
    setLoading(true);
    setError(null);
    setSummary(null);
    setSelectedProvince(null);
    setDetail(null);
    setSelectedYear(null);
    setSellerId(nextSellerId);
  }

  /** 年份切换保留旧图至新聚合返回，同时关闭已失效的省份详情。 */
  function selectYear(value: string) {
    setLoading(true);
    setError(null);
    setSelectedProvince(null);
    setDetail(null);
    setSelectedYear(value ? Number(value) : null);
  }

  /** 省份选择先进入加载态，避免旧省份详情在新请求期间短暂残留。 */
  function selectProvince(province: string) {
    setDetailLoading(true);
    setDetailError(null);
    setDetail(null);
    setSelectedProvince(province);
  }

  /** 明确重置汇总请求状态后递增重试键。 */
  function retrySummary() {
    setLoading(true);
    setError(null);
    setSummary(null);
    setRetryKey((key) => key + 1);
  }

  /** 保留当前省份并仅重试其逐笔明细。 */
  function retryDetail() {
    setDetailLoading(true);
    setDetailError(null);
    setDetail(null);
    setDetailRetryKey((key) => key + 1);
  }

  /** 指标切换时关闭旧弹窗，避免把上一种指标的详情误认为当前结果。 */
  function selectMetric(nextMetric: HeatmapMetric) {
    setSelectedProvince(null);
    setDetail(null);
    setMetric(nextMetric);
  }

  /** 同步三类渠道网络的独立显示状态。 */
  function toggleChannelType(partnerType: ChannelPartnerType, checked: boolean) {
    setVisibleChannelTypes((current) => checked ? [...current, partnerType] : current.filter((item) => item !== partnerType));
  }

  return (
    <>
      <aside className="map-controls unit-heat-filters" aria-label="全国成交热力图筛选">
        <p>地图指标</p>
        <div className="deal-heat-metric" role="group" aria-label="热力图指标">
          <button type="button" aria-pressed={metric === "signed"} onClick={() => selectMetric("signed")}>成交金额</button>
          <button type="button" aria-pressed={metric === "intention"} onClick={() => selectMetric("intention")}>采购意向</button>
        </div>
        {metric === "signed" ? (
          <>
            <p className="deal-heat-section-title">成交公司</p>
            <label className="deal-heat-company">
              <span>查看公司</span>
              <select aria-label="选择成交公司" value={sellerId} onChange={(event) => selectSeller(event.target.value)} disabled={sellers.length === 0}>
                {sellers.length === 0 ? <option value="unite">优纳特</option> : sellers.map((seller) => <option key={seller.id} value={seller.id}>{seller.name}</option>)}
              </select>
            </label>
            <p className="deal-heat-section-title">成交总金额档位</p>
            <details className="heat-level-dropdown">
              <summary><span>{selectedLevelLabel}</span><i aria-hidden="true" /></summary>
              <div className="heat-level-menu">
                <label className="heat-check-row">
                  <input type="checkbox" checked={allSelected} onChange={(event) => setSelectedLevels(event.target.checked ? [...allLevelKeys] : [])} />
                  <span>全部</span>
                </label>
                {dealHeatLevels.map((level) => (
                  <label className="heat-check-row" key={level.key}>
                    <input type="checkbox" checked={selectedLevels.includes(level.key)} onChange={(event) => toggleLevel(level.key, event.target.checked)} />
                    <i style={{ "--heat-swatch": level.color } as CSSProperties} />
                    <span>{level.label}<small>{level.rangeLabel}</small></span>
                  </label>
                ))}
              </div>
            </details>
          </>
        ) : (
          <div className="intention-heat-note">
            <strong>优纳特采购意向</strong>
            <span>仅显示当前有效、尚未成交的意向；颜色越深，预计金额越高。</span>
          </div>
        )}
        <div className="sales-network-divider" />
        <label className="heat-check-row sales-network-check">
          <input type="checkbox" checked={showSalesOffices} disabled={salesOfficesLoading || Boolean(salesOfficesError)} onChange={(event) => setShowSalesOffices(event.target.checked)} />
          <i aria-hidden="true" />
          <span>显示销售常驻点</span>
        </label>
        {salesOfficesLoading ? <small className="sales-network-status">正在读取常驻点…</small> : null}
        {salesOfficesError ? <small className="sales-network-status is-error">{salesOfficesError}</small> : null}
        <div className="channel-network-divider" />
        <p className="channel-network-title">渠道点位网络</p>
        {channelPartnerTypes.map((partnerType) => (
          <label className="heat-check-row channel-partner-check" key={partnerType} style={{ "--channel-color": channelPartnerColors[partnerType], "--channel-contrast": channelPartnerContrastColors[partnerType] } as CSSProperties}>
            <input type="checkbox" checked={visibleChannelTypes.includes(partnerType)} disabled={channelPartnersLoading || Boolean(channelPartnersError)} onChange={(event) => toggleChannelType(partnerType, event.target.checked)} />
            <i aria-hidden="true" />
            <span>显示{partnerType}</span>
          </label>
        ))}
        <label className="channel-level-filter">
          <span>合作等级</span>
          <select value={cooperationLevel} onChange={(event) => setCooperationLevel(event.target.value as CooperationLevel | "")}>
            <option value="">全部等级</option>
            {cooperationLevels.map((level) => <option value={level} key={level}>{level}</option>)}
          </select>
        </label>
        {channelPartnersLoading ? <small className="sales-network-status">正在读取渠道点…</small> : null}
        {channelPartnersError ? <small className="sales-network-status is-error">{channelPartnersError}</small> : null}
      </aside>
      <div className="organization-heatmap-stage">
        {loading ? <div className="organization-map-message" role="status">正在汇总省级{metric === "signed" ? "成交金额" : "采购意向"}…</div> : null}
        {error ? <div className="organization-map-message deal-heat-error" role="alert"><span>{error}</span><button type="button" onClick={retrySummary}>重新加载</button></div> : null}
        {!loading && !error && summary?.provinces.length === 0 ? <div className="organization-map-message">所选公司暂无成交或采购意向数据。</div> : null}
        {!loading && !error && summary && summary.provinces.length > 0 ? (
          <svg className="organization-heatmap" style={zoomStyle} viewBox={chinaMap.viewBox} role="group" aria-label={metric === "signed" ? `${summary.seller.name}全国成交总金额热力图` : "优纳特全国采购意向热力图"}>
            <g>
              {chinaMap.locations.map((location: { id: string; name: string; path: string }) => {
                const province = provinceNames[location.id] ?? location.name;
                const provinceSummary = summariesByProvince.get(province);
                const level = provinceSummary ? levelForAmount(provinceSummary.signed_amount) : undefined;
                const actualVisible = Boolean(level && selectedLevels.includes(level.key));
                const intentionVisible = Boolean(provinceSummary && amountValue(provinceSummary.intention_amount) > 0);
                const interactive = metric === "signed" ? actualVisible : intentionVisible;
                const fill = metric === "signed"
                  ? (actualVisible ? level?.color : "#f1ece8")
                  : intentionColorForAmount(provinceSummary?.intention_amount ?? "0", maximumIntentionAmount);
                return (
                  <path
                    key={location.id}
                    d={location.path}
                    className={`organization-heat-province ${interactive ? "is-visible" : "is-filtered"}`}
                    data-province={province}
                    style={{ "--heat-fill": interactive ? fill : "#f1ece8" } as CSSProperties}
                    tabIndex={interactive ? 0 : -1}
                    role={interactive ? "button" : undefined}
                    aria-pressed={interactive ? province === selectedProvince : undefined}
                    aria-label={interactive ? `查看${province}${metric === "signed" ? "成交" : "采购意向"}明细` : undefined}
                    onClick={() => { if (interactive) selectProvince(province); }}
                    onKeyDown={(event) => {
                      if (interactive && (event.key === "Enter" || event.key === " ")) {
                        event.preventDefault();
                        selectProvince(province);
                      }
                    }}
                  >
                    <title>{metric === "signed" ? `${province} · ${summary.seller.name}成交 ${formatCurrency(provinceSummary?.signed_amount ?? "0")}` : `${province} · 优纳特采购意向 ${formatCurrency(provinceSummary?.intention_amount ?? "0")}`}</title>
                  </path>
                );
              })}
            </g>
          </svg>
        ) : null}
        {showSalesOffices && projectedSalesOffices.length > 0 ? (
          <svg className="organization-heatmap sales-network-overlay" style={zoomStyle} viewBox={chinaMap.viewBox} aria-label="销售常驻点及覆盖范围">
            <g>
              {projectedSalesOffices.map((office) => (
                <g className="sales-office-coverage" key={office.id}>
                  <circle cx={office.x} cy={office.y} r={office.radius} />
                  <g className="sales-office-pin" transform={`translate(${office.x} ${office.y})`}>
                    <path d="M0 9C-2.2 5.5-7.5 1.1-7.5-4.2A7.5 7.5 0 0 1 7.5-4.2C7.5 1.1 2.2 5.5 0 9Z" />
                    <circle cy="-4.2" r="2.4" />
                  </g>
                  <text x={office.x + 10} y={office.y - 7}>{office.city.replace(/市$/, "")}</text>
                  <title>{`${office.name}\n${office.address ?? office.city}\n覆盖半径 ${office.coverage_radius_km} 公里`}</title>
                </g>
              ))}
            </g>
          </svg>
        ) : null}
        {projectedChannelPartners.length > 0 ? (
          <svg className="organization-heatmap channel-partner-overlay" style={zoomStyle} viewBox={chinaMap.viewBox} aria-label="经销商、代理商及合作伙伴位置标记">
            <g>
              {projectedChannelPartners.map((partner) => (
                <g className="channel-partner-coverage" key={partner.id} style={{ "--channel-color": channelPartnerColors[partner.partner_type], "--channel-contrast": channelPartnerContrastColors[partner.partner_type] } as CSSProperties}>
                  <g className="channel-partner-pin" transform={`translate(${partner.x} ${partner.y})`}>
                    <path d="M0 9C-2.2 5.5-7.5 1.1-7.5-4.2A7.5 7.5 0 0 1 7.5-4.2C7.5 1.1 2.2 5.5 0 9Z" />
                    <circle cy="-4.2" r="2.4" />
                  </g>
                  <text x={partner.x + 10} y={partner.y - 7}>{partner.name}</text>
                  <title>{`${partner.name} · ${partner.partner_type}\n${partner.address}\n${partner.cooperation_level}`}</title>
                </g>
              ))}
            </g>
          </svg>
        ) : null}
        {selectedLocation ? (
          <svg className="organization-heatmap organization-heatmap-selection" style={zoomStyle} viewBox={chinaMap.viewBox} aria-hidden="true">
            <path className="organization-heat-selection-path" d={selectedLocation.path} />
          </svg>
        ) : null}
        {selectedProvince ? (
          <aside className="heatmap-detail deal-heatmap-detail" role="dialog" aria-label={`${selectedProvince}${metric === "signed" ? "订单" : "采购意向"}明细`}>
            <header>
              <div><span>{metric === "signed" ? `${summary?.seller.name ?? "所选公司"} · 成交明细` : "优纳特 · 当前采购意向"}</span><h2>{selectedProvince}</h2></div>
              <button type="button" onClick={() => setSelectedProvince(null)} aria-label="关闭省份明细">×</button>
            </header>
            {detailLoading ? <p className="deal-detail-status" role="status">正在读取{metric === "signed" ? "逐笔订单" : "采购意向"}…</p> : null}
            {detailError ? <div className="deal-detail-status is-error" role="alert"><span>{detailError}</span><button type="button" onClick={retryDetail}>重试</button></div> : null}
            {detail ? (
              <>
                <div className="deal-detail-totals is-single">
                  {metric === "signed"
                    ? <div><span>已成交总额</span><strong>{formatCurrency(detail.signed_amount)}</strong><small>{detail.signed_order_count} 笔订单</small></div>
                    : <div className="is-intention"><span>预计采购金额</span><strong>{formatCurrency(detail.intention_amount)}</strong><small>{detail.intention_count} 条有效意向</small></div>}
                </div>
                {metric === "signed" ? (
                  <section className="deal-detail-section">
                    <h3>成交订单</h3>
                    {detail.orders.length === 0 ? <p className="deal-empty">该公司在本省暂无成交订单。</p> : (
                      <ol className="deal-order-list">
                        {detail.orders.map((order) => (
                          <li key={order.id}>
                            <div className="deal-order-heading"><div><strong>{order.project_name}</strong><span>{order.customer_name}</span></div><b>{formatCurrency(order.amount)}</b></div>
                            <div className="deal-order-meta"><span>{detail.seller.kind === "unite" ? "合同总金额" : "项目总价"}</span><span>{formatDate(order.signed_at)}</span>{order.deal_type ? <span>{order.deal_type}</span> : null}</div>
                            {detail.seller.kind === "competitor" ? (
                              <>
                                {(order.products?.[0]?.product_image_url || order.product_image_url) ? <Image className="deal-order-image" src={order.products?.[0]?.product_image_url || order.product_image_url || ""} alt={`${order.project_name}产品图片`} width={340} height={100} unoptimized /> : <div className="deal-order-image is-empty" role="img" aria-label="暂无产品图片">暂无产品图片</div>}
                                <CompetitorOrderFields order={order} websiteUrl={detail.seller.website_url} />
                              </>
                            ) : null}
                          </li>
                        ))}
                      </ol>
                    )}
                  </section>
                ) : (
                  <section className="deal-detail-section is-intention">
                    <h3>优纳特采购意向</h3>
                    {detail.intentions.length === 0 ? <p className="deal-empty">本省暂无有效未成交意向。</p> : (
                      <ol className="deal-intention-list">
                        {detail.intentions.map((intention) => (
                          <li key={intention.id}>
                            <div><strong>{intention.title}</strong><span>{intention.customer_name}</span></div>
                            <b>{formatCurrency(intention.estimated_amount)}</b>
                            <p><span>{intention.stage}</span><span>下次行动：{formatDate(intention.next_action_at)}</span></p>
                          </li>
                        ))}
                      </ol>
                    )}
                  </section>
                )}
              </>
            ) : null}
          </aside>
        ) : null}
        {!error && summary ? (
          <div className="heatmap-map-tools">
            <div className="heatmap-color-legend" aria-label={metric === "signed" ? "成交金额热力颜色图例" : "采购意向金额热力颜色图例"}>
              {metric === "signed"
                ? dealHeatLevels.map((level) => <span key={level.key}><i style={{ "--heat-swatch": level.color } as CSSProperties} />{level.rangeLabel}</span>)
                : intentionHeatColors.map((color, index) => <span key={color}><i style={{ "--heat-swatch": color } as CSSProperties} />{intentionRangeLabel(index, maximumIntentionAmount)}</span>)}
            </div>
            <div className="heatmap-bottom-tools">
              {metric === "signed" ? (
                <label className="heatmap-year-filter">
                  <span>成交年份</span>
                  <select aria-label="成交年份" value={selectedYear ?? ""} onChange={(event) => selectYear(event.target.value)} disabled={loading}>
                    <option value="">全部年份</option>
                    {summary.available_years.map((year) => <option value={year} key={year}>{year} 年</option>)}
                  </select>
                </label>
              ) : <div className="heatmap-snapshot-label"><span>统计口径</span><strong>当前有效意向</strong></div>}
              <div className="map-zoom heatmap-zoom" role="group" aria-label="热力图缩放">
                <button type="button" disabled={zoom <= heatmapZoomMin} onClick={() => setZoom((current) => Math.max(heatmapZoomMin, Number((current - heatmapZoomStep).toFixed(2))))} aria-label="缩小热力图">−</button>
                <button type="button" className="zoom-reset" disabled={zoom === heatmapZoomMin} onClick={() => setZoom(heatmapZoomMin)} aria-label="恢复默认大小">默认</button>
                <button type="button" disabled={zoom >= heatmapZoomMax} onClick={() => setZoom((current) => Math.min(heatmapZoomMax, Number((current + heatmapZoomStep).toFixed(2))))} aria-label="放大热力图">＋</button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </>
  );
}
