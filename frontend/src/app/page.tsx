"use client";

/**
 * 销售地图仪表盘主页面：组合 React、GSAP、AMap 点位地图与省级单位热力组件。
 * 首页右侧标签切换两种单位地图；演示洞察数据与真实单位数据保持明确分离。
 */
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import Image from "next/image";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";
import { AdminOrganizationMap } from "@/components/admin-organization-map";
import { HomeOrganizationDatabase } from "@/components/home-organization-database";
import { HomeOrganizationHeatmap } from "@/components/home-organization-heatmap";
import { apiFetch, queryString, type ChannelPartnerMapPoint, type FilterOptions, type MapPoint, type ProvinceOrganizationSummary, type SalesOfficeLocation } from "@/lib/api";

gsap.registerPlugin(useGSAP);

type Screen = "map" | "data" | "test";
type UnitMapView = "points" | "heat";
type UnitMapFilters = {
  province: string;
  city: string;
  district: string;
  organizationType: string;
  customerStatus: string;
};
const highlights = [
  {
    label: "实际销售",
    value: "3,570",
    unit: "万元",
    trend: "+18.6%",
    color: "orange",
  },
  {
    label: "预计销售",
    value: "2,871",
    unit: "万元",
    trend: "+24.2%",
    color: "purple",
  },
  {
    label: "活跃项目",
    value: "34",
    unit: "个",
    trend: "8 个待推进",
    color: "blue",
  },
  {
    label: "签约转化",
    value: "42.7",
    unit: "%",
    trend: "+4.9pt",
    color: "ink",
  },
];

const emptyUnitMapFilters: UnitMapFilters = {
  province: "",
  city: "",
  district: "",
  organizationType: "",
  customerStatus: "",
};

/** 从后端点位字段生成稳定的降级选项，避免高德加载失败时筛选菜单为空。 */
function uniqueMapValues(values: Array<string | null>): string[] {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort((left, right) => left.localeCompare(right, "zh-CN"));
}

/** 统一渲染页面使用的内联 SVG 图标，避免引入额外图标资源请求。 */
function Icon({ name, size = 16 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    arrow: <path d="M4 12h15m-6-6 6 6-6 6" />,
    bell: (
      <>
        <path d="M7 17h10l-1.2-2.3V10a3.8 3.8 0 0 0-7.6 0v4.7z" />
        <path d="M10 20h4" />
      </>
    ),
    down: <path d="m7 10 5 5 5-5" />,
    pin: (
      <>
        <path d="M12 21s6-5.5 6-11a6 6 0 1 0-12 0c0 5.5 6 11 6 11Z" />
        <circle cx="12" cy="10" r="2" />
      </>
    ),
    focus: (
      <>
        <circle cx="12" cy="12" r="4" />
        <path d="M12 2v3m0 14v3M2 12h3m14 0h3" />
      </>
    ),
    link: (
      <>
        <circle cx="6" cy="6" r="2" />
        <circle cx="18" cy="6" r="2" />
        <circle cx="12" cy="18" r="2" />
        <path d="m7.6 7.2 3.1 8.1m5.7-8.1-3.1 8.1M8 6h8" />
      </>
    ),
    map: (
      <>
        <path d="m9 18-6 3V6l6-3 6 3 6-3v15l-6 3z" />
        <path d="M9 3v15m6-12v15" />
      </>
    ),
    chart: (
      <>
        <path d="M4 19V5m0 14h16" />
        <path d="m7 15 4-4 3 2 5-6" />
      </>
    ),
    database: (
      <>
        <ellipse cx="12" cy="5" rx="7" ry="3" />
        <path d="M5 5v7c0 1.7 3.1 3 7 3s7-1.3 7-3V5m-14 7v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6" />
      </>
    ),
    test: (
      <>
        <path d="M8 3h8m-7 0v5l-4.8 8.2A3 3 0 0 0 6.8 21h10.4a3 3 0 0 0 2.6-4.8L15 8V3" />
        <path d="M8 15h8" />
      </>
    ),
  };
  return (
    <svg
      className="ui-icon"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[name] ?? paths.arrow}
    </svg>
  );
}

/** 渲染数据洞察页的静态演示柱状图，展示实际与预计销售额对比。 */
function MiniBarChart() {
  const actual = [1268, 462, 426, 358, 290, 216],
    forecast = [732, 198, 498, 120, 340, 186],
    labels = ["浙江", "江苏", "广东", "上海", "北京", "山东"];
  return (
    <div
      className="mini-chart"
      aria-label="六大核心市场的实际与预计销售额柱状图"
    >
      <div className="chart-grid" />
      {labels.map((label, index) => (
        <div className="bar-group" key={label}>
          <div className="bars">
            <span
              className="bar actual"
              style={{ height: `${(actual[index] / 1300) * 100}%` }}
            />
            <span
              className="bar forecast"
              style={{ height: `${(forecast[index] / 1300) * 100}%` }}
            />
          </div>
          <small>{label}</small>
        </div>
      ))}
    </div>
  );
}

/**
 * 应用根页面组件：管理页面、两种单位地图和数据洞察状态，并用 GSAP 编排视图切换动效。
 * 点位与热力数据分别复用现有公开 API，右侧标签只负责切换呈现方式。
 */
export default function Home() {
  const [screen, setScreen] = useState<Screen>("map"),
    [analytics, setAnalytics] = useState("区域贡献"),
    [unitMapView, setUnitMapView] = useState<UnitMapView>("points"),
    [universityPoints, setUniversityPoints] = useState<MapPoint[]>([]),
    [mapFilterOptions, setMapFilterOptions] = useState<FilterOptions | null>(null),
    [unitMapFilters, setUnitMapFilters] = useState<UnitMapFilters>(emptyUnitMapFilters),
    [selectedOrganizationId, setSelectedOrganizationId] = useState<string | null>(null),
    [mapLoading, setMapLoading] = useState(true),
    [mapRequestError, setMapRequestError] = useState<string | null>(null),
    [provinceSummaries, setProvinceSummaries] = useState<ProvinceOrganizationSummary[]>([]),
    [heatLoading, setHeatLoading] = useState(true),
    [heatRequestError, setHeatRequestError] = useState<string | null>(null),
    [salesOfficeLocations, setSalesOfficeLocations] = useState<SalesOfficeLocation[]>([]),
    [salesOfficeLoading, setSalesOfficeLoading] = useState(true),
    [salesOfficeRequestError, setSalesOfficeRequestError] = useState<string | null>(null),
    [channelPartnerLocations, setChannelPartnerLocations] = useState<ChannelPartnerMapPoint[]>([]),
    [channelPartnerLoading, setChannelPartnerLoading] = useState(true),
    [channelPartnerRequestError, setChannelPartnerRequestError] = useState<string | null>(null);
  const root = useRef<HTMLElement>(null);
  useGSAP(
    () => {
      const media = gsap.matchMedia();
      media.add(
        { motion: "(prefers-reduced-motion: no-preference)" },
        (context) => {
          if (!context.conditions?.motion) return;
          const timeline = gsap.timeline({ defaults: { ease: "power3.out" } });
          timeline
            .fromTo(
              ".workspace-panel.is-active",
              { autoAlpha: 0, y: 18 },
              { autoAlpha: 1, y: 0, duration: 0.55 },
            )
            .fromTo(
              ".workspace-panel.is-active .panel-enter",
              { autoAlpha: 0, y: 18 },
              { autoAlpha: 1, y: 0, duration: 0.5, stagger: 0.07 },
              "<.08",
            );
        },
      );
      return () => media.revert();
    },
    { scope: root, dependencies: [screen], revertOnUpdate: true },
  );

  const mapPointQuery = useMemo(() => queryString({
    province: unitMapFilters.province || undefined,
    city: unitMapFilters.city || undefined,
    district: unitMapFilters.district || undefined,
    types: unitMapFilters.organizationType ? [unitMapFilters.organizationType] : undefined,
    customer_statuses: unitMapFilters.customerStatus ? [unitMapFilters.customerStatus] : undefined,
  }), [unitMapFilters]);
  const mapFilterOptionsQuery = useMemo(() => queryString({
    province: unitMapFilters.province || undefined,
    city: unitMapFilters.city || undefined,
  }), [unitMapFilters.city, unitMapFilters.province]);

  useEffect(() => {
    const controller = new AbortController();

    // 点位筛选交给后端处理，避免浏览器只在当前结果中二次过滤。
    void apiFetch<MapPoint[]>(`/public/organizations/map-points${mapPointQuery}`, { signal: controller.signal })
      .then((points) => {
        setUniversityPoints(points);
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setMapRequestError(error instanceof Error ? error.message : "全国单位地图数据加载失败");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setMapLoading(false);
      });

    return () => controller.abort();
  }, [mapPointQuery]);

  useEffect(() => {
    const controller = new AbortController();

    // 筛选菜单独立读取数据库枚举，即使高德底图请求失败也能完整显示。
    void apiFetch<FilterOptions>(`/public/organizations/filters${mapFilterOptionsQuery}`, { signal: controller.signal })
      .then((options) => {
        setMapFilterOptions(options);
      })
      .catch(() => {
        // 已加载点位仍可作为筛选选项的降级来源。
      });

    return () => controller.abort();
  }, [mapFilterOptionsQuery]);

  useEffect(() => {
    if (unitMapView !== "heat" || provinceSummaries.length > 0) return;
    const controller = new AbortController();

    // 省级聚合由服务端一次完成，避免公开主站下载全部单位明细再统计。
    void apiFetch<ProvinceOrganizationSummary[]>("/public/organizations/province-summaries", { signal: controller.signal })
      .then((summaries) => {
        setProvinceSummaries(summaries);
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setHeatRequestError(error instanceof Error ? error.message : "省级单位热力数据加载失败");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setHeatLoading(false);
      });

    return () => controller.abort();
  }, [provinceSummaries.length, unitMapView]);

  useEffect(() => {
    if (unitMapView !== "heat" || salesOfficeLocations.length > 0) return;
    const controller = new AbortController();

    // 常驻点独立读取，热力统计成功时即使辅助网络失败也不影响主图。
    void apiFetch<SalesOfficeLocation[]>("/public/sales-office-locations", { signal: controller.signal })
      .then((locations) => {
        setSalesOfficeLocations(locations);
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setSalesOfficeRequestError(error instanceof Error ? error.message : "销售常驻点加载失败");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setSalesOfficeLoading(false);
      });

    return () => controller.abort();
  }, [salesOfficeLocations.length, unitMapView]);

  useEffect(() => {
    if (unitMapView !== "heat" || channelPartnerLocations.length > 0) return;
    const controller = new AbortController();

    // 渠道覆盖点独立读取，任一辅助网络失败都不阻断省级热力主图。
    void apiFetch<ChannelPartnerMapPoint[]>("/public/channel-partner-locations", { signal: controller.signal })
      .then((locations) => {
        setChannelPartnerLocations(locations);
      })
      .catch((error: unknown) => {
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setChannelPartnerRequestError(error instanceof Error ? error.message : "渠道覆盖网络加载失败");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setChannelPartnerLoading(false);
      });

    return () => controller.abort();
  }, [channelPartnerLocations.length, unitMapView]);

  /** 在用户事件内重置点位请求状态，effect 仅同步外部地图数据。 */
  function updateUnitMapFilters(changes: Partial<UnitMapFilters>) {
    setMapLoading(true);
    setMapRequestError(null);
    setSelectedOrganizationId(null);
    setUnitMapFilters((current) => ({ ...current, ...changes }));
  }

  /** 切换地图模式时只初始化尚未成功读取的热力辅助数据。 */
  function selectUnitMapView(view: UnitMapView) {
    if (view === "heat") {
      if (provinceSummaries.length === 0) { setHeatLoading(true); setHeatRequestError(null); }
      if (salesOfficeLocations.length === 0) { setSalesOfficeLoading(true); setSalesOfficeRequestError(null); }
      if (channelPartnerLocations.length === 0) { setChannelPartnerLoading(true); setChannelPartnerRequestError(null); }
    }
    setUnitMapView(view);
  }

  const provinceOptions = useMemo(
    () => mapFilterOptions?.provinces ?? uniqueMapValues(universityPoints.map((point) => point.province)),
    [mapFilterOptions, universityPoints],
  );
  const cityOptions = mapFilterOptions?.cities ?? [];
  const districtOptions = mapFilterOptions?.districts ?? [];
  const organizationTypeOptions = useMemo(
    () => mapFilterOptions?.organization_types ?? uniqueMapValues(universityPoints.map((point) => point.organization_type)),
    [mapFilterOptions, universityPoints],
  );
  const customerStatusOptions = useMemo(
    () => mapFilterOptions?.customer_statuses ?? uniqueMapValues(universityPoints.map((point) => point.customer_status)),
    [mapFilterOptions, universityPoints],
  );
  return (
    <main ref={root} className="app-shell">
      <header className="topbar">
        <a className="brand" href="#">
          <Image className="brand-logo" src="/brand/unite-logo.png" alt="优纳特" width={148} height={36} priority />
          <span className="system-title">全国销售网络作战地图系统</span>
        </a>
        <nav className="screen-switch" role="tablist" aria-label="主界面切换">
          <button
            id="screen-tab-map"
            className={screen === "map" ? "active" : ""}
            onClick={() => setScreen("map")}
            role="tab"
            aria-selected={screen === "map"}
            aria-controls="screen-panel-map"
          >
            <Icon name="map" size={16} />
            全国单位地图
          </button>
          <button
            id="screen-tab-data"
            className={screen === "data" ? "active" : ""}
            onClick={() => setScreen("data")}
            role="tab"
            aria-selected={screen === "data"}
            aria-controls="screen-panel-data"
          >
            <Icon name="chart" size={16} />
            数据洞察
          </button>
          <button
            id="screen-tab-test"
            className={screen === "test" ? "active" : ""}
            onClick={() => setScreen("test")}
            role="tab"
            aria-selected={screen === "test"}
            aria-controls="screen-panel-test"
          >
            <Icon name="database" size={16} />
            单位数据库
          </button>
        </nav>
        <div className="topbar-meta">
          <a className="admin-entry-link" href="/admin/organizations">
            管理员入口
            <Icon name="arrow" size={14} />
          </a>
          <span>2026 · Q3</span>
          <button aria-label="通知">
            <Icon name="bell" size={18} />
          </button>
          <button className="avatar" aria-label="管理员">
            Y
          </button>
        </div>
      </header>
      <section
        id="screen-panel-map"
        className={`workspace-panel map-workspace ${screen === "map" ? "is-active" : ""}`}
        role="tabpanel"
        aria-labelledby="screen-tab-map"
        aria-hidden={screen !== "map"}
      >
        <div className="monitor-card map-card panel-enter">
          <div className="map-titlebar">
            <div className="map-caption">
              <span>2026 / 全国单位</span>
              <h1>全国行业单位</h1>
              <p>{unitMapView === "points" ? "仅展示已有可靠地理编码的单位，并按地图缩放层级聚合。" : "按单位主地点汇总省级数量，橙红深浅表示单位密度档位。"}</p>
            </div>
          </div>
          <div className="map-content unit-map-content">
            {unitMapView === "points" ? (
              <>
                <aside className="map-controls unit-map-filters" aria-label="全国行业单位筛选">
                  <label>
                    <span>省份</span>
                    <select value={unitMapFilters.province} onChange={(event) => updateUnitMapFilters({ province: event.target.value, city: "", district: "" })}>
                      <option value="">全部省份</option>
                      {provinceOptions.map((province) => <option key={province} value={province}>{province}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>市</span>
                    <select value={unitMapFilters.city} disabled={!unitMapFilters.province} onChange={(event) => updateUnitMapFilters({ city: event.target.value, district: "" })}>
                      <option value="">全部市</option>
                      {cityOptions.map((city) => <option key={city} value={city}>{city}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>区</span>
                    <select value={unitMapFilters.district} disabled={!unitMapFilters.city} onChange={(event) => updateUnitMapFilters({ district: event.target.value })}>
                      <option value="">全部区</option>
                      {districtOptions.map((district) => <option key={district} value={district}>{district}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>单位类型</span>
                    <select value={unitMapFilters.organizationType} onChange={(event) => updateUnitMapFilters({ organizationType: event.target.value })}>
                      <option value="">全部类型</option>
                      {organizationTypeOptions.map((organizationType) => <option key={organizationType} value={organizationType}>{organizationType}</option>)}
                    </select>
                  </label>
                  <label>
                    <span>客户状态</span>
                    <select value={unitMapFilters.customerStatus} onChange={(event) => updateUnitMapFilters({ customerStatus: event.target.value })}>
                      <option value="">全部客户状态</option>
                      {customerStatusOptions.map((customerStatus) => <option key={customerStatus} value={customerStatus}>{customerStatus}</option>)}
                    </select>
                  </label>
                </aside>
                <div style={{ display: "grid", minHeight: 0, position: "relative" }}>
                  {mapLoading ? <div className="organization-map-message">正在读取可信单位坐标…</div> : null}
                  {mapRequestError ? <div className="organization-map-message">{mapRequestError}</div> : null}
                  {!mapLoading && !mapRequestError ? (
                    <AdminOrganizationMap
                      points={universityPoints}
                      selectedId={selectedOrganizationId}
                      onSelectPoint={(point) => setSelectedOrganizationId(point.id)}
                    />
                  ) : null}
                </div>
              </>
            ) : null}
            <div className={`unit-map-mode ${unitMapView === "heat" ? "" : "is-hidden"}`}>
              <HomeOrganizationHeatmap
                summaries={provinceSummaries}
                loading={heatLoading}
                error={heatRequestError}
                salesOffices={salesOfficeLocations}
                salesOfficesLoading={salesOfficeLoading}
                salesOfficesError={salesOfficeRequestError}
                channelPartners={channelPartnerLocations}
                channelPartnersLoading={channelPartnerLoading}
                channelPartnersError={channelPartnerRequestError}
              />
            </div>
            <aside className="map-view-rail">
              <div className="map-switch" role="tablist" aria-label="单位地图切换">
                <button className={unitMapView === "points" ? "selected" : ""} type="button" role="tab" aria-selected={unitMapView === "points"} onClick={() => selectUnitMapView("points")}>
                  <Icon name="pin" size={18} />
                  <span><b>全国单位地图</b><small>全国可信单位点位</small></span>
                </button>
                <button className={unitMapView === "heat" ? "selected" : ""} type="button" role="tab" aria-selected={unitMapView === "heat"} onClick={() => selectUnitMapView("heat")}>
                  <Icon name="focus" size={18} />
                  <span><b>全国单位热力地图</b><small>五档省级单位密度</small></span>
                </button>
                <button type="button" disabled>
                  <Icon name="link" size={18} />
                  <span><b>省份详情</b><small>点击省份查看统计</small></span>
                </button>
              </div>
            </aside>
          </div>
          <div className="map-footer">
            <span>
              <i className="legend-actual" />
              {unitMapView === "points" ? "已定位单位" : "单位数量热力"}
            </span>
            <span>
              <i className="legend-forecast" />
              {unitMapView === "points" ? "缩放自动聚合" : "五档可多选"}
            </span>
            <span>{unitMapView === "points" ? "未定位记录不会显示在地图中" : "点击省份查看类型与客户状态构成"}</span>
          </div>
        </div>
      </section>
      <section
        id="screen-panel-test"
        className={`workspace-panel database-workspace ${screen === "test" ? "is-active" : ""}`}
        role="tabpanel"
        aria-labelledby="screen-tab-test"
        aria-hidden={screen !== "test"}
      >
        {screen === "test" && <HomeOrganizationDatabase />}
      </section>
      <section
        id="screen-panel-data"
        className={`workspace-panel data-workspace ${screen === "data" ? "is-active" : ""}`}
        role="tabpanel"
        aria-labelledby="screen-tab-data"
        aria-hidden={screen !== "data"}
      >
        <div className="data-header panel-enter">
          <div className="data-topline">
            <span>数据洞察</span>
            <h1>核心销售数据</h1>
          </div>
          <div className="highlight-grid">
            {highlights.map((highlight) => (
              <article
                className={`highlight-card ${highlight.color}`}
                key={highlight.label}
              >
                <span>{highlight.label}</span>
                <strong>
                  {highlight.value}
                  <small>{highlight.unit}</small>
                </strong>
                <div>
                  <i />
                  {highlight.trend}
                  <Icon name="arrow" size={14} />
                </div>
              </article>
            ))}
          </div>
        </div>
        <div className="analytics-grid panel-enter">
          <aside className="analytics-legend">
            <span>分析维度</span>
            {["区域贡献", "产品结构", "推进节奏", "项目清单"].map(
              (name, index) => (
                <button
                  key={name}
                  className={analytics === name ? "active" : ""}
                  onClick={() => setAnalytics(name)}
                >
                  <i>{String(index + 1).padStart(2, "0")}</i>
                  {name}
                  <Icon name="arrow" size={14} />
                </button>
              ),
            )}
            <div className="legend-bottom">
              <Icon name="database" size={18} />
              <span>
                累计
                <br />
                <b>6,441 万</b>
              </span>
            </div>
          </aside>
          <article className="chart-panel">
            <div className="chart-head">
              <div>
                <span>{analytics}</span>
                <h2>六大核心市场</h2>
              </div>
              <div className="chart-legend">
                <span>
                  <i className="legend-actual" />
                  实际
                </span>
                <span>
                  <i className="legend-forecast" />
                  预计
                </span>
              </div>
            </div>
            <MiniBarChart />
          </article>
          <article className="pipeline-card">
            <div>
              <span>推进中的项目</span>
              <button aria-label="展开项目">
                <Icon name="arrow" size={17} />
              </button>
            </div>
            <strong>
              08 <small>条</small>
            </strong>
            <ul>
              <li>
                <span className="bubble blue" />
                北京高校危化品安全柜 <b>75%</b>
              </li>
              <li>
                <span className="bubble orange" />
                广东生物样本存储项目 <b>62%</b>
              </li>
              <li>
                <span className="bubble purple" />
                上海标准品管理系统 <b>51%</b>
              </li>
            </ul>
          </article>
        </div>
      </section>
    </main>
  );
}
