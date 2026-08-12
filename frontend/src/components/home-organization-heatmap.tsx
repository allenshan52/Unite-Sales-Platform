"use client";

/** 首页省级单位热力图：展示数据库聚合档位，并按需叠加销售与三类渠道覆盖网络。 */
import { useMemo, useState, type CSSProperties } from "react";
import chinaMap from "@svg-maps/china";
import type { ChannelPartnerMapPoint, ChannelPartnerType, CooperationLevel, ProvinceOrganizationSummary, SalesOfficeLocation } from "@/lib/api";

type HeatLevelKey = "very-high" | "high" | "medium" | "low" | "very-low";

type HeatLevel = {
  key: HeatLevelKey;
  label: string;
  min: number;
  max: number;
  color: string;
};

// 约 700 条单位、当前省级分布为 3—47 条；后续只需修改此处即可调整五档阈值和颜色。
export const organizationHeatLevels: readonly HeatLevel[] = [
  { key: "very-high", label: "极高", min: 40, max: Number.POSITIVE_INFINITY, color: "#b9361f" },
  { key: "high", label: "高", min: 30, max: 39, color: "#df552f" },
  { key: "medium", label: "中", min: 20, max: 29, color: "#ed8057" },
  { key: "low", label: "低", min: 10, max: 19, color: "#f4b091" },
  { key: "very-low", label: "极低", min: 1, max: 9, color: "#f9d9c8" },
];

const provinceNames: Record<string, string> = {
  anhui: "安徽省", beijing: "北京市", chongqing: "重庆市", fujian: "福建省", gansu: "甘肃省",
  guangdong: "广东省", "guangxi-zhuang": "广西壮族自治区", guizhou: "贵州省", hainan: "海南省",
  hebei: "河北省", heilongjiang: "黑龙江省", henan: "河南省", "hong-kong": "香港特别行政区",
  hubei: "湖北省", hunan: "湖南省", jiangsu: "江苏省", jiangxi: "江西省", jilin: "吉林省",
  liaoning: "辽宁省", macau: "澳门特别行政区", "nei-mongol": "内蒙古自治区",
  "ningxia-hui": "宁夏回族自治区", quinghai: "青海省", shaanxi: "陕西省", shandong: "山东省",
  shanghai: "上海市", shanxi: "山西省", sichuan: "四川省", tianjin: "天津市",
  "xinjiang-uygur": "新疆维吾尔自治区", xizang: "西藏自治区", yunnan: "云南省", zhejiang: "浙江省",
};

const organizationTypeOrder = ["高校", "研究院", "疾控", "食药", "环保", "公安"];
const customerStatusOrder = ["潜在客户", "商机客户", "已成交客户"];
const allLevelKeys = organizationHeatLevels.map((level) => level.key);
const heatmapZoomMin = 1;
const heatmapZoomMax = 1.75;
const heatmapZoomStep = 0.15;
const salesCoverageKmPerSvgUnit = 8.5;
// 由当前 MapSVG 中国底图的北京、天津、上海、香港、澳门边界校准，避免保存视图专用坐标。
const mapLongitudeOffset = -975.007848;
const mapLongitudeScale = 13.038228;
const mapLatitudeOffset = 807.719623;
const mapMercatorScale = -735.840147;
const channelPartnerTypes: readonly ChannelPartnerType[] = ["经销商", "代理商", "合作伙伴"];
const cooperationLevels: readonly CooperationLevel[] = ["一级", "二级", "三级"];
const channelPartnerColors: Record<ChannelPartnerType, string> = {
  经销商: "#15967f",
  代理商: "#875bd4",
  合作伙伴: "#ffffff",
};
const channelPartnerContrastColors: Record<ChannelPartnerType, string> = {
  经销商: "#ffffff",
  代理商: "#ffffff",
  合作伙伴: "#6f6259",
};

type ProjectedSalesOffice = SalesOfficeLocation & { x: number; y: number; radius: number };
type ProjectedChannelPartner = ChannelPartnerMapPoint & { x: number; y: number; radius: number };

/** 按集中配置的阈值返回单位数量所属档位。 */
function levelForCount(count: number): HeatLevel | undefined {
  return organizationHeatLevels.find((level) => count >= level.min && count <= level.max);
}

/** 以固定业务顺序补齐零值，确保省份弹层完整展示每种单位类型和客户状态。 */
function completeCounts(order: string[], counts: Record<string, number>): Array<[string, number]> {
  return order.map((label) => [label, counts[label] ?? 0]);
}

/** 复用底图校准后的 Mercator 投影，将任一城市中心经纬度转换为 SVG 坐标。 */
function projectMapCoordinates(longitude: number, latitude: number): { x: number; y: number } {
  const latitudeRadians = latitude * Math.PI / 180;
  const mercatorLatitude = Math.log(Math.tan(Math.PI / 4 + latitudeRadians / 2));
  const x = mapLongitudeOffset + mapLongitudeScale * longitude;
  const y = mapLatitudeOffset + mapMercatorScale * mercatorLatitude;
  return { x, y };
}

/** 投影销售常驻点并把公里覆盖半径转换为当前底图单位。 */
function projectSalesOffice(office: SalesOfficeLocation): ProjectedSalesOffice {
  return { ...office, ...projectMapCoordinates(office.longitude, office.latitude), radius: Math.max(18, office.coverage_radius_km / salesCoverageKmPerSvgUnit) };
}

/** 投影公开渠道点并复用销售网络相同的覆盖半径换算。 */
function projectChannelPartner(partner: ChannelPartnerMapPoint): ProjectedChannelPartner {
  return { ...partner, ...projectMapCoordinates(partner.map_longitude, partner.map_latitude), radius: Math.max(18, partner.coverage_radius_km / salesCoverageKmPerSvgUnit) };
}

/** 渲染左侧多选档位、省级热力图及可选销售网络，并保持省份统计弹层位于所有地图图层之上。 */
export function HomeOrganizationHeatmap({
  summaries,
  loading,
  error,
  salesOffices,
  salesOfficesLoading,
  salesOfficesError,
  channelPartners,
  channelPartnersLoading,
  channelPartnersError,
}: {
  summaries: ProvinceOrganizationSummary[];
  loading: boolean;
  error: string | null;
  salesOffices: SalesOfficeLocation[];
  salesOfficesLoading: boolean;
  salesOfficesError: string | null;
  channelPartners: ChannelPartnerMapPoint[];
  channelPartnersLoading: boolean;
  channelPartnersError: string | null;
}) {
  const [selectedLevels, setSelectedLevels] = useState<HeatLevelKey[]>([...allLevelKeys]);
  const [selectedProvince, setSelectedProvince] = useState<string | null>(null);
  const [zoom, setZoom] = useState(heatmapZoomMin);
  const [showSalesOffices, setShowSalesOffices] = useState(false);
  const [visibleChannelTypes, setVisibleChannelTypes] = useState<ChannelPartnerType[]>([]);
  const [cooperationLevel, setCooperationLevel] = useState<CooperationLevel | "">("");
  const summariesByProvince = useMemo(
    () => new Map(summaries.map((summary) => [summary.province, summary])),
    [summaries],
  );
  const selectedProvinceSummary = selectedProvince ? summariesByProvince.get(selectedProvince) : undefined;
  const selectedSummaryLevel = selectedProvinceSummary ? levelForCount(selectedProvinceSummary.total) : undefined;
  const selectedSummary = selectedSummaryLevel && selectedLevels.includes(selectedSummaryLevel.key) ? selectedProvinceSummary : undefined;
  const selectedLocation = selectedProvince
    ? chinaMap.locations.find((location: { id: string; name: string; path: string }) => (provinceNames[location.id] ?? location.name) === selectedProvince)
    : undefined;
  const allSelected = selectedLevels.length === organizationHeatLevels.length;
  const selectedLevelLabel = allSelected ? "全部档位" : selectedLevels.length === 0 ? "未选择档位" : `已选 ${selectedLevels.length} 档`;
  const zoomStyle = { "--heatmap-zoom": zoom } as CSSProperties;
  const projectedSalesOffices = useMemo(() => salesOffices.map(projectSalesOffice), [salesOffices]);
  const projectedChannelPartners = useMemo(
    () => channelPartners.map(projectChannelPartner).filter((partner) => visibleChannelTypes.includes(partner.partner_type) && (!cooperationLevel || partner.cooperation_level === cooperationLevel)),
    [channelPartners, cooperationLevel, visibleChannelTypes],
  );

  /** 同步某一档位的复选状态，同时支持多个热力档位并行展示。 */
  function toggleLevel(key: HeatLevelKey, checked: boolean) {
    setSelectedLevels((current) => checked ? [...current, key] : current.filter((item) => item !== key));
  }

  /** 同步三类渠道网络的独立显示状态，允许任意组合叠加。 */
  function toggleChannelType(partnerType: ChannelPartnerType, checked: boolean) {
    setVisibleChannelTypes((current) => checked ? [...current, partnerType] : current.filter((item) => item !== partnerType));
  }

  return (
    <>
      <aside className="map-controls unit-heat-filters" aria-label="全国单位热力档位筛选">
        <p>单位数量档位</p>
        <details className="heat-level-dropdown">
          <summary><span>{selectedLevelLabel}</span><i aria-hidden="true" /></summary>
          <div className="heat-level-menu">
            <label className="heat-check-row">
              <input type="checkbox" checked={allSelected} onChange={(event) => setSelectedLevels(event.target.checked ? [...allLevelKeys] : [])} />
              <span>全部</span>
            </label>
            {organizationHeatLevels.map((level) => (
              <label className="heat-check-row" key={level.key}>
                <input type="checkbox" checked={selectedLevels.includes(level.key)} onChange={(event) => toggleLevel(level.key, event.target.checked)} />
                <i style={{ "--heat-swatch": level.color } as CSSProperties} />
                <span>{level.label}<small>{Number.isFinite(level.max) ? `${level.min}–${level.max}` : `${level.min}+`} 个</small></span>
              </label>
            ))}
          </div>
        </details>
        <div className="sales-network-divider" />
        <label className="heat-check-row sales-network-check">
          <input type="checkbox" checked={showSalesOffices} disabled={salesOfficesLoading || Boolean(salesOfficesError)} onChange={(event) => setShowSalesOffices(event.target.checked)} />
          <i aria-hidden="true" />
          <span>显示销售常驻点</span>
        </label>
        {salesOfficesLoading ? <small className="sales-network-status">正在读取常驻点…</small> : null}
        {salesOfficesError ? <small className="sales-network-status is-error">{salesOfficesError}</small> : null}
        <div className="channel-network-divider" />
        <p className="channel-network-title">渠道覆盖网络</p>
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
        {loading ? <div className="organization-map-message">正在汇总省级单位数据…</div> : null}
        {error ? <div className="organization-map-message">{error}</div> : null}
        {!loading && !error && summaries.length === 0 ? <div className="organization-map-message">暂无可用于省级汇总的单位主地点。</div> : null}
        {!loading && !error && summaries.length > 0 ? (
          <svg className="organization-heatmap" style={zoomStyle} viewBox={chinaMap.viewBox} role="img" aria-label="全国单位数量五档热力图">
            <g>
              {chinaMap.locations.map((location: { id: string; name: string; path: string }) => {
                const province = provinceNames[location.id] ?? location.name;
                const summary = summariesByProvince.get(province);
                const level = summary ? levelForCount(summary.total) : undefined;
                const visible = Boolean(level && selectedLevels.includes(level.key));
                return (
                  <path
                    key={location.id}
                    d={location.path}
                    className={`organization-heat-province ${visible ? "is-visible" : "is-filtered"}`}
                    data-province={province}
                    style={{ "--heat-fill": visible ? level?.color : "#f1ece8" } as CSSProperties}
                    tabIndex={visible ? 0 : -1}
                    role={visible ? "button" : undefined}
                    aria-pressed={visible ? province === selectedProvince : undefined}
                    aria-label={visible ? `查看${province}${level?.label}档单位统计` : undefined}
                    onClick={() => { if (visible) setSelectedProvince(province); }}
                    onKeyDown={(event) => { if (visible && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); setSelectedProvince(province); } }}
                  >
                    <title>{level ? `${province} · ${level.label}档` : province}</title>
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
          <svg className="organization-heatmap channel-partner-overlay" style={zoomStyle} viewBox={chinaMap.viewBox} aria-label="经销商、代理商及合作伙伴覆盖范围">
            <g>
              {projectedChannelPartners.map((partner) => (
                <g className="channel-partner-coverage" key={partner.id} style={{ "--channel-color": channelPartnerColors[partner.partner_type], "--channel-contrast": channelPartnerContrastColors[partner.partner_type] } as CSSProperties}>
                  <circle cx={partner.x} cy={partner.y} r={partner.radius} />
                  <g className="channel-partner-pin" transform={`translate(${partner.x} ${partner.y})`}>
                    <path d="M0 9C-2.2 5.5-7.5 1.1-7.5-4.2A7.5 7.5 0 0 1 7.5-4.2C7.5 1.1 2.2 5.5 0 9Z" />
                    <circle cy="-4.2" r="2.4" />
                  </g>
                  <text x={partner.x + 10} y={partner.y - 7}>{partner.name}</text>
                  <title>{`${partner.name} · ${partner.partner_type}\n${partner.address}\n${partner.cooperation_level} · 覆盖半径 ${partner.coverage_radius_km} 公里`}</title>
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
        {selectedSummary ? (
          <aside className="heatmap-detail" role="dialog" aria-label={`${selectedSummary.province}单位统计`}>
            <header>
              <div><span>省份单位概览</span><h2>{selectedSummary.province}</h2></div>
              <button type="button" onClick={() => setSelectedProvince(null)} aria-label="关闭省份统计">×</button>
            </header>
            <div className="heatmap-total"><strong>{selectedSummary.total.toLocaleString("zh-CN")}</strong><span>个单位</span></div>
            <section>
              <h3>单位类型</h3>
              <dl>{completeCounts(organizationTypeOrder, selectedSummary.organization_types).map(([label, count]) => <div key={label}><dt>{label}</dt><dd>{count}</dd></div>)}</dl>
            </section>
            <section>
              <h3>客户 / 成交状态</h3>
              <dl>{completeCounts(customerStatusOrder, selectedSummary.customer_statuses).map(([label, count]) => <div key={label}><dt>{label}</dt><dd>{count}</dd></div>)}</dl>
            </section>
          </aside>
        ) : null}
        {!loading && !error && summaries.length > 0 ? (
          <div className="heatmap-map-tools">
            <div className="heatmap-color-legend" aria-label="单位数量热力颜色图例">
              {organizationHeatLevels.map((level) => <span key={level.key}><i style={{ "--heat-swatch": level.color } as CSSProperties} />{level.label}</span>)}
            </div>
            <div className="map-zoom heatmap-zoom" role="group" aria-label="热力图缩放">
              <button type="button" disabled={zoom <= heatmapZoomMin} onClick={() => setZoom((current) => Math.max(heatmapZoomMin, Number((current - heatmapZoomStep).toFixed(2))))} aria-label="缩小热力图">−</button>
              <button type="button" className="zoom-reset" disabled={zoom === heatmapZoomMin} onClick={() => setZoom(heatmapZoomMin)} aria-label="恢复默认大小">默认</button>
              <button type="button" disabled={zoom >= heatmapZoomMax} onClick={() => setZoom((current) => Math.min(heatmapZoomMax, Number((current + heatmapZoomStep).toFixed(2))))} aria-label="放大热力图">＋</button>
            </div>
          </div>
        ) : null}
      </div>
    </>
  );
}
