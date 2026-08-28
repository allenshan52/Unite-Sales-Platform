"use client";

/**
 * 销售地图仪表盘主页面：组合 React、GSAP、AMap 点位地图与省级成交热力组件。
 * 首页右侧当前开放五种业务地图；同行市场版图实现保留但暂不开放主页面入口。
 */
import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import Image from "next/image";
import dynamic from "next/dynamic";
import { gsap } from "gsap";
import { useGSAP } from "@gsap/react";
import { AccessLoginPanel } from "@/components/access-login-panel";
import { AdminOrganizationMap } from "@/components/admin-organization-map";
import { HomeOrganizationHeatmap } from "@/components/home-organization-heatmap";
import { apiFetch, queryString, type ChannelPartnerMapPoint, type CurrentUser, type FilterOptions, type MapPoint, type SalesOfficeLocation } from "@/lib/api";

gsap.registerPlugin(useGSAP);

const HomeCompetitorMarketMap = dynamic(() => import("@/components/home-competitor-market-map").then((module) => module.HomeCompetitorMarketMap), { loading: LazyPanelLoading });
const HomeDataInsights = dynamic(() => import("@/components/home-data-insights").then((module) => module.HomeDataInsights), { loading: LazyPanelLoading });
const HomeGroupNetworkMap = dynamic(() => import("@/components/home-group-network-map").then((module) => module.HomeGroupNetworkMap), { loading: LazyPanelLoading });
const HomeOrganizationDatabase = dynamic(() => import("@/components/home-organization-database").then((module) => module.HomeOrganizationDatabase), { loading: LazyPanelLoading });
const HomeSalespersonCoverageMap = dynamic(() => import("@/components/home-salesperson-coverage-map").then((module) => module.HomeSalespersonCoverageMap), { loading: LazyPanelLoading });
const HomeTypicalCaseMap = dynamic(() => import("@/components/home-typical-case-map").then((module) => module.HomeTypicalCaseMap), { loading: LazyPanelLoading });

type Screen = "map" | "data" | "test";
type UnitMapView = "points" | "heat" | "groups" | "competitors" | "salespeople" | "cases";

/** 临时隐藏同行市场版图入口；改为 true 即可恢复原按钮和完整视图。 */
const showCompetitorMarketMapEntry = false;

type UnitMapFilters = {
  province: string;
  city: string;
  district: string;
  organizationType: string;
  customerStatus: string;
};
const emptyUnitMapFilters: UnitMapFilters = {
  province: "",
  city: "",
  district: "",
  organizationType: "",
  customerStatus: "",
};

/** 为非首屏业务面板预留固定状态，避免切换标签时出现无反馈空白。 */
function LazyPanelLoading() {
  return <div className="organization-map-message" role="status">正在加载业务地图…</div>;
}

/** 从后端点位字段生成稳定的降级选项，避免高德加载失败时筛选菜单为空。 */
function uniqueMapValues(values: Array<string | null>): string[] {
  return Array.from(new Set(values.filter((value): value is string => Boolean(value)))).sort((left, right) => left.localeCompare(right, "zh-CN"));
}

/** 统一渲染页面使用的内联 SVG 图标，避免引入额外图标资源请求。 */
function Icon({ name, size = 16 }: { name: string; size?: number }) {
  const paths: Record<string, ReactNode> = {
    arrow: <path d="M4 12h15m-6-6 6 6-6 6" />,
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
    people: (
      <>
        <circle cx="9" cy="8" r="3" />
        <path d="M3.5 19c.4-4 2.1-6 5.5-6s5.1 2 5.5 6M16 5.5a2.5 2.5 0 0 1 0 5M16 13c2.7.2 4.1 2.1 4.5 5" />
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

/**
 * 应用根页面组件：管理页面、两种单位地图和数据洞察状态，并用 GSAP 编排视图切换动效。
 * 点位与热力数据分别复用现有公开 API，右侧标签只负责切换呈现方式。
 */
export default function HomePage() {
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null);
  const [checkingSession, setCheckingSession] = useState(true);

  /** 在挂载任何业务视图前恢复会话，避免匿名浏览器提前请求或看到主站内容。 */
  useEffect(() => {
    const controller = new AbortController();
    void apiFetch<CurrentUser>("/auth/me", { signal: controller.signal })
      .then(setCurrentUser)
      .catch((requestError: unknown) => {
        if (!(requestError instanceof DOMException && requestError.name === "AbortError")) setCurrentUser(null);
      })
      .finally(() => { if (!controller.signal.aborted) setCheckingSession(false); });
    return () => controller.abort();
  }, []);

  /** 撤销服务端会话后卸载全部业务组件，防止共享电脑继续显示缓存数据。 */
  async function logout() {
    await apiFetch<void>("/auth/logout", { method: "POST" });
    setCurrentUser(null);
  }

  if (checkingSession) return <main className="admin-loading">正在确认访问权限…</main>;
  if (!currentUser) return <AccessLoginPanel audience="site" onLoggedIn={setCurrentUser} />;
  return <Home currentUser={currentUser} onLogout={logout} />;
}

/** 已授权主站内容：只有外层会话确认成功后才挂载并请求业务数据。 */
function Home({ currentUser, onLogout }: { currentUser: CurrentUser; onLogout: () => Promise<void> }) {
  const [screen, setScreen] = useState<Screen>("map"),
    [unitMapView, setUnitMapView] = useState<UnitMapView>("points"),
    [universityPoints, setUniversityPoints] = useState<MapPoint[]>([]),
    [mapFilterOptions, setMapFilterOptions] = useState<FilterOptions | null>(null),
    [unitMapFilters, setUnitMapFilters] = useState<UnitMapFilters>(emptyUnitMapFilters),
    [selectedOrganizationId, setSelectedOrganizationId] = useState<string | null>(null),
    [mapLoading, setMapLoading] = useState(true),
    [mapRequestError, setMapRequestError] = useState<string | null>(null),
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

  /** 切换地图模式时只初始化尚未成功读取的辅助点位，成交热力数据由独立组件按需加载。 */
  function selectUnitMapView(view: UnitMapView) {
    if (view === "heat") {
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
            数据后台
            <Icon name="arrow" size={14} />
          </a>
          <span>{currentUser.username}</span>
          <button className="site-logout-button" type="button" onClick={() => void onLogout()}>退出</button>
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
          {unitMapView !== "groups" && unitMapView !== "competitors" && unitMapView !== "salespeople" && unitMapView !== "cases" ? (
            <div className="map-titlebar">
              <div className="map-caption">
                <span>2026 / 全国单位</span>
                <h1>全国行业单位</h1>
                <p>{unitMapView === "points" ? "仅展示已有可靠地理编码的单位，并按地图缩放层级聚合。" : "按单位主地点汇总省级数量，橙红深浅表示单位密度档位。"}</p>
              </div>
            </div>
          ) : null}
          <div className={`map-content unit-map-content ${unitMapView === "groups" ? "group-network-mode" : unitMapView === "competitors" ? "competitor-market-mode" : unitMapView === "salespeople" ? "salesperson-coverage-mode" : unitMapView === "cases" ? "typical-case-mode" : ""}`}>
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
                  {mapLoading ? <div className="organization-map-message" role="status">正在读取可信单位坐标…</div> : null}
                  {mapRequestError ? <div className="organization-map-message" role="alert">{mapRequestError}</div> : null}
                  {!mapLoading && !mapRequestError ? (
                    <AdminOrganizationMap
                      points={universityPoints}
                      selectedId={selectedOrganizationId}
                      onSelectPoint={(point) => setSelectedOrganizationId(point.id)}
                      focusRegion={Boolean(unitMapFilters.province || unitMapFilters.city || unitMapFilters.district)}
                      showPointPopup
                    />
                  ) : null}
                </div>
              </>
            ) : null}
            <div className={`unit-map-mode ${unitMapView === "heat" ? "" : "is-hidden"}`}>
              <HomeOrganizationHeatmap
                active={unitMapView === "heat"}
                salesOffices={salesOfficeLocations}
                salesOfficesLoading={salesOfficeLoading}
                salesOfficesError={salesOfficeRequestError}
                channelPartners={channelPartnerLocations}
                channelPartnersLoading={channelPartnerLoading}
                channelPartnersError={channelPartnerRequestError}
              />
            </div>
            {unitMapView === "groups" ? <HomeGroupNetworkMap /> : null}
            {unitMapView === "competitors" ? <HomeCompetitorMarketMap /> : null}
            {unitMapView === "salespeople" ? <HomeSalespersonCoverageMap /> : null}
            {unitMapView === "cases" ? <HomeTypicalCaseMap /> : null}
            <aside className="map-view-rail">
              <div className="map-switch" role="tablist" aria-label="单位地图切换">
                <button className={unitMapView === "points" ? "selected" : ""} type="button" role="tab" aria-selected={unitMapView === "points"} onClick={() => selectUnitMapView("points")}>
                  <Icon name="pin" size={18} />
                  <span><b>全国单位地图</b><small>全国可信单位点位</small></span>
                </button>
                <button className={unitMapView === "heat" ? "selected" : ""} type="button" role="tab" aria-selected={unitMapView === "heat"} onClick={() => selectUnitMapView("heat")}>
                  <Icon name="focus" size={18} />
                  <span><b>全国成交热力地图</b><small>成交金额与采购意向</small></span>
                </button>
                <button className={unitMapView === "groups" ? "selected" : ""} type="button" role="tab" aria-selected={unitMapView === "groups"} onClick={() => selectUnitMapView("groups")}>
                  <Icon name="link" size={18} />
                  <span><b>客户关系网络</b><small>总部与集团分支关系</small></span>
                </button>
                {showCompetitorMarketMapEntry ? (
                  <button className={unitMapView === "competitors" ? "selected" : ""} type="button" role="tab" aria-selected={unitMapView === "competitors"} onClick={() => selectUnitMapView("competitors")}>
                    <Icon name="focus" size={18} />
                    <span><b>同行市场版图</b><small>据点、成交与强势区域</small></span>
                  </button>
                ) : null}
                <button className={unitMapView === "salespeople" ? "selected" : ""} type="button" role="tab" aria-selected={unitMapView === "salespeople"} onClick={() => selectUnitMapView("salespeople")}>
                  <Icon name="people" size={18} />
                  <span><b>销售覆盖与人效</b><small>城市范围、活动与业绩</small></span>
                </button>
                <button className={unitMapView === "cases" ? "selected" : ""} type="button" role="tab" aria-selected={unitMapView === "cases"} onClick={() => selectUnitMapView("cases")}>
                  <Icon name="database" size={18} />
                  <span><b>典型案例地图</b><small>一省一案 · 标杆复盘</small></span>
                </button>
              </div>
            </aside>
          </div>
          <div className="map-footer">
            <span>
              <i className="legend-actual" />
              {unitMapView === "points" ? "已定位单位" : unitMapView === "heat" ? "单位数量热力" : unitMapView === "groups" ? "集团颜色区分" : unitMapView === "competitors" ? "同行名称分色" : unitMapView === "salespeople" ? "销售姓名分色" : "橙色省份已上线"}
            </span>
            <span>
              <i className="legend-forecast" />
              {unitMapView === "points" ? "缩放自动聚合" : unitMapView === "heat" ? "五档可多选" : unitMapView === "groups" ? "状态文字标识" : unitMapView === "competitors" ? "强、中、弱三级区域" : unitMapView === "salespeople" ? "1 / 3 / 6 / 12 月" : "灰色省份筹备中"}
            </span>
            <span>{unitMapView === "points" ? "未定位记录不会显示在地图中" : unitMapView === "heat" ? "点击省份查看类型与客户状态构成" : unitMapView === "groups" ? "点击总部展开关系；关闭、Esc 或返回全国集团可重置" : unitMapView === "competitors" ? "点击据点、成交单位或区域打开对应详情" : unitMapView === "salespeople" ? "点击销售 Pin 查看市、省、大区或全国覆盖，选择两人后可对比" : "点击省份或使用下拉框浏览案例复盘"}</span>
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
        {screen === "data" && <HomeDataInsights />}
      </section>
    </main>
  );
}
