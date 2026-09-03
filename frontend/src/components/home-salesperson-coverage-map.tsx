"use client";

/** 第五地图：绘制销售位置 Pin，并承载单人详情、双人对比及月份/年份切换。 */

import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties, type ReactNode } from "react";

import { apiFetch, type SalespersonCoverage, type SalespersonCoverageScope, type SalespersonPeriodMonths } from "@/lib/api";
import { destroyAmapMap, loadAmapNamespace } from "@/lib/amap";
import { escapeHtml } from "@/lib/html";

interface AmapOverlay {
  on(event: "click", handler: () => void): void;
}

interface AmapMap {
  add(overlays: unknown | unknown[]): void;
  addControl(control: unknown): void;
  destroy(): void;
  remove(overlays: unknown | unknown[]): void;
  setFitView(overlays?: unknown[], immediately?: boolean, avoid?: number[], maxZoom?: number): void;
  setZoomAndCenter(zoom: number, center: [number, number]): void;
  zoomIn(): void;
  zoomOut(): void;
}

interface SalesAmapNamespace {
  getConfig(): { appname?: string };
  Map: new (container: HTMLElement, options: Record<string, unknown>) => AmapMap;
  Marker: new (options: Record<string, unknown>) => AmapOverlay;
  Scale: new () => unknown;
}

type Runtime = { AMap: SalesAmapNamespace; map: AmapMap; overlays: unknown[] };
type LoadStatus = "loading" | "ready" | "error";

const periods: SalespersonPeriodMonths[] = [1, 3, 6, 12];
const defaultPeriod: SalespersonPeriodMonths = 3;
const currencyFormatter = new Intl.NumberFormat("zh-CN", { style: "currency", currency: "CNY", maximumFractionDigits: 0 });

/** 年份菜单始终提供当前年及前两年，避免跨年后继续显示过期的固定年份。 */
function recentActivityYears(): number[] {
  const currentYear = new Date().getFullYear();
  return [currentYear, currentYear - 1, currentYear - 2];
}

/** 格式化数据库 Decimal 字符串，金额缺失时仍稳定显示人民币零元。 */
function formatCurrency(value: string): string {
  return currencyFormatter.format(Number(value) || 0);
}

/** 为四级销售覆盖生成紧凑标签，避免大区或全国被误读为城市数量。 */
function formatCoverageScope(scope: SalespersonCoverageScope): string {
  return scope.scope_level === "全国" ? "全国" : `${scope.scope_name}（${scope.scope_level}）`;
}

/** 合并一名销售的覆盖标签，并为空档案提供明确占位。 */
function formatCoverageScopes(person: SalespersonCoverage): string {
  return person.coverage_scopes.map(formatCoverageScope).join("、") || "未配置覆盖范围";
}

/** 按浮层实测尺寸为聚焦区域留出安全区；并为并发渲染尚未落位的面板提供同尺寸兜底。 */
function fitViewAvoidance(container: HTMLElement, panelMode: "single" | "compare"): number[] {
  const rootRect = container.getBoundingClientRect();
  const titleRect = container.querySelector<HTMLElement>(".salesperson-map-title-card")?.getBoundingClientRect();
  const panelRect = container.querySelector<HTMLElement>(".salesperson-detail-panel")?.getBoundingClientRect();
  if (window.innerWidth <= 900) {
    const top = Math.ceil((titleRect?.bottom ?? rootRect.top) - rootRect.top + 24);
    const fallbackPanelHeight = rootRect.height * (window.innerWidth <= 620 ? 0.58 : 0.54);
    const bottom = panelRect ? Math.ceil(rootRect.bottom - panelRect.top + 24) : Math.ceil(fallbackPanelHeight + 24);
    return [top, bottom, 48, 48];
  }
  if (panelMode === "compare") {
    const top = titleRect ? Math.ceil(titleRect.bottom - rootRect.top + 24) : 388;
    const right = panelRect ? Math.ceil(rootRect.right - panelRect.left + 24) : 608;
    return [top, 48, 48, right];
  }
  const right = panelRect ? Math.ceil(rootRect.right - panelRect.left + 32) : 426;
  const left = titleRect ? Math.ceil(titleRect.right - rootRect.left + 32) : 340;
  return [96, 88, left, right];
}

/** 用统一线宽的内联图标保持标题卡、选择器和详情面板视觉一致。 */
function SalesIcon({ name, size = 17 }: { name: "people" | "close" | "compare" | "reset" | "down"; size?: number }) {
  const paths: Record<string, ReactNode> = {
    people: <><circle cx="9" cy="8" r="3" /><path d="M3.5 19c.4-4 2.1-6 5.5-6s5.1 2 5.5 6M16 5.5a2.5 2.5 0 0 1 0 5M16 13c2.7.2 4.1 2.1 4.5 5" /></>,
    close: <path d="m6 6 12 12M18 6 6 18" />,
    compare: <><path d="M8 5h11M5 5l2-2m-2 2 2 2M16 19H5m14 0-2-2m2 2-2 2" /><path d="M8 9v6m8-6v6" /></>,
    reset: <><path d="M4 12a8 8 0 1 0 2.3-5.7L4 8" /><path d="M4 3v5h5" /></>,
    down: <path d="m7 10 5 5 5-5" />,
  };
  return <svg aria-hidden="true" viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

/** 详情内统一切换滚动月份或自然年；成交与储备继续使用当前累计值。 */
function SalespersonPeriodBar({ period, year, loading, onMonthChange, onYearChange }: { period: SalespersonPeriodMonths; year: number | null; loading: boolean; onMonthChange: (months: SalespersonPeriodMonths) => void; onYearChange: (year: number) => void }) {
  return (
    <div className="salesperson-detail-period" role="group" aria-label="活动统计时间范围" aria-busy={loading}>
      <span>活动时间范围</span>
      <div className="salesperson-period-months" role="radiogroup" aria-label="滚动月份">
        {periods.map((months) => <button key={months} type="button" role="radio" aria-checked={year === null && period === months} className={year === null && period === months ? "selected" : ""} disabled={loading} onClick={() => onMonthChange(months)}>{months} 月</button>)}
      </div>
      <select className={year === null ? "" : "selected"} aria-label="活动年份" value={year ?? ""} disabled={loading} onChange={(event) => onYearChange(Number(event.target.value))}>
        <option value="" disabled>年份</option>
        {recentActivityYears().map((optionYear) => <option key={optionYear} value={optionYear}>{optionYear} 年</option>)}
      </select>
    </div>
  );
}

/** 单人详情按需求 6.2 展示负责区域、活动明细、成交和储备金额。 */
function SalespersonDetail({ person, period, year, loading, onPeriodChange, onYearChange, onClose }: { person: SalespersonCoverage; period: SalespersonPeriodMonths; year: number | null; loading: boolean; onPeriodChange: (months: SalespersonPeriodMonths) => void; onYearChange: (year: number) => void; onClose: () => void }) {
  const metrics = person.performance;
  const periodLabel = metrics.period_year === null ? `最近 ${metrics.period_months} 个月` : `${metrics.period_year} 年`;
  return (
    <aside className="salesperson-detail-panel" aria-label={`${person.display_name}销售详情`} style={{ "--sales-color": person.color } as CSSProperties}>
      <header>
        <div><i /><h2>{person.display_name}</h2><p>{periodLabel}人效详情</p></div>
        <button type="button" aria-label="关闭销售详情" onClick={onClose}><SalesIcon name="close" /></button>
      </header>
      <section className="salesperson-coverage-copy"><h3>负责区域</h3><p>{formatCoverageScopes(person)}</p></section>
      <section className="salesperson-money-strip">
        <div><span>成交金额 · {metrics.project_count} 个项目</span><strong>{formatCurrency(metrics.actual_sales_amount)}</strong></div>
        <div><span>储备金额 · {metrics.active_opportunity_count} 个项目</span><strong>{formatCurrency(metrics.pipeline_amount)}</strong></div>
      </section>
      <SalespersonPeriodBar period={period} year={year} loading={loading} onMonthChange={onPeriodChange} onYearChange={onYearChange} />
      <section className="salesperson-activity-block">
        <div><h3>活动强度</h3><strong>{metrics.activities.total}<small> 次</small></strong></div>
        <dl>
          <div><dt>客户拜访</dt><dd>{metrics.activities.visits}</dd></div>
          <div><dt>方案演示</dt><dd>{metrics.activities.demonstrations}</dd></div>
          <div><dt>市场活动</dt><dd>{metrics.activities.marketing_events}</dd></div>
        </dl>
      </section>
    </aside>
  );
}

/** 双人对比复用单人指标结构，以左右两列保留直接可扫读的同口径差异。 */
function SalespersonComparison({ people, period, year, loading, onPeriodChange, onYearChange, onClose }: { people: [SalespersonCoverage, SalespersonCoverage]; period: SalespersonPeriodMonths; year: number | null; loading: boolean; onPeriodChange: (months: SalespersonPeriodMonths) => void; onYearChange: (year: number) => void; onClose: () => void }) {
  return (
    <aside className="salesperson-detail-panel salesperson-compare-panel" aria-label={`${people[0].display_name}与${people[1].display_name}人效对比`}>
      <header><div><h2>销售人效对比</h2><p>活动按所选月份 · 金额按当前累计/储备口径</p></div><button type="button" aria-label="关闭销售对比" onClick={onClose}><SalesIcon name="close" /></button></header>
      <SalespersonPeriodBar period={period} year={year} loading={loading} onMonthChange={onPeriodChange} onYearChange={onYearChange} />
      <div className="salesperson-compare-grid">
        {people.map((person) => (
          <article key={person.id} style={{ "--sales-color": person.color } as CSSProperties}>
            <div className="salesperson-compare-name"><i /><h3>{person.display_name}</h3><span>{person.coverage_scopes.length} 项范围</span></div>
            <p className="salesperson-compare-cities">{formatCoverageScopes(person)}</p>
            <dl>
              <div><dt>活动总数</dt><dd>{person.performance.activities.total} 次</dd></div>
              <div><dt>拜访 / 演示 / 市场</dt><dd>{person.performance.activities.visits} / {person.performance.activities.demonstrations} / {person.performance.activities.marketing_events}</dd></div>
              <div><dt>成交金额</dt><dd>{formatCurrency(person.performance.actual_sales_amount)}</dd></div>
              <div><dt>储备项目金额</dt><dd>{formatCurrency(person.performance.pipeline_amount)}</dd></div>
            </dl>
          </article>
        ))}
      </div>
    </aside>
  );
}

/** 首页销售覆盖地图负责数据请求、人员 Pin 绘制、选择聚焦和对比状态闭环。 */
export function HomeSalespersonCoverageMap() {
  const containerRef = useRef<HTMLDivElement>(null);
  const runtimeRef = useRef<Runtime | null>(null);
  const [mapReady, setMapReady] = useState(false);
  const [period, setPeriod] = useState<SalespersonPeriodMonths>(defaultPeriod);
  const [periodYear, setPeriodYear] = useState<number | null>(null);
  const [people, setPeople] = useState<SalespersonCoverage[]>([]);
  const [dataStatus, setDataStatus] = useState<LoadStatus>("loading");
  const [mapStatus, setMapStatus] = useState<LoadStatus>("loading");
  const [dataMessage, setDataMessage] = useState<string | null>(null);
  const [mapMessage, setMapMessage] = useState<string | null>(null);
  const [dataAttempt, setDataAttempt] = useState(0);
  const [mapAttempt, setMapAttempt] = useState(0);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [activeSalespersonId, setActiveSalespersonId] = useState<string | null>(null);
  const [comparisonActive, setComparisonActive] = useState(false);

  const visibleIds = useMemo(
    () => comparisonActive ? selectedIds : activeSalespersonId ? [activeSalespersonId] : [],
    [activeSalespersonId, comparisonActive, selectedIds],
  );
  const selectedPeople = selectedIds.flatMap((id) => people.find((person) => person.id === id) ?? []);
  const activePerson = people.find((person) => person.id === activeSalespersonId) ?? null;
  const comparedPeople = comparisonActive && selectedPeople.length === 2 ? selectedPeople as [SalespersonCoverage, SalespersonCoverage] : null;
  const stateStatus: LoadStatus | "empty" = mapStatus === "error" || dataStatus === "error"
    ? "error"
    : mapStatus === "loading" || dataStatus === "loading"
      ? "loading"
      : people.length === 0 ? "empty" : "ready";
  const stateMessage = mapStatus === "error" ? mapMessage : dataStatus === "error" ? dataMessage : null;

  /** 每次开始新的单人或对比查看都恢复三个月口径，避免上一次临时筛选泄漏到下一次查看。 */
  const resetPeriodToDefault = useCallback(() => {
    if (period === defaultPeriod && periodYear === null) return;
    setDataStatus("loading");
    setDataMessage(null);
    setPeriod(defaultPeriod);
    setPeriodYear(null);
  }, [period, periodYear]);

  /** 关闭详情和对比，恢复全国销售覆盖视图和默认三个月口径。 */
  const resetView = useCallback(() => {
    resetPeriodToDefault();
    setSelectedIds([]);
    setActiveSalespersonId(null);
    setComparisonActive(false);
    setDropdownOpen(false);
  }, [resetPeriodToDefault]);

  /** 区域点击进入单人详情，同时把对比选择收敛为该销售。 */
  const openSalesperson = useCallback((id: string) => {
    resetPeriodToDefault();
    setSelectedIds([id]);
    setActiveSalespersonId(id);
    setComparisonActive(false);
    setDropdownOpen(false);
  }, [resetPeriodToDefault]);

  /** 下拉选择最多保留两名销售；每次选择都会先聚焦新加入的人。 */
  function addSalesperson(id: string) {
    if (selectedIds.includes(id)) return;
    resetPeriodToDefault();
    const nextIds = selectedIds.length >= 2 ? [selectedIds[1], id] : [...selectedIds, id];
    setSelectedIds(nextIds);
    setActiveSalespersonId(id);
    setComparisonActive(false);
    if (nextIds.length === 2) setDropdownOpen(false);
  }

  /** 删除标题白框顶部的已选姓名，并同步退出失效的对比状态。 */
  function removeSalesperson(id: string) {
    resetPeriodToDefault();
    const nextIds = selectedIds.filter((selectedId) => selectedId !== id);
    setSelectedIds(nextIds);
    setComparisonActive(false);
    setActiveSalespersonId(nextIds.at(-1) ?? null);
  }

  /** 在用户动作内进入加载态，effect 仅负责同步后端请求。 */
  function changePeriod(months: SalespersonPeriodMonths) {
    if (months === period && periodYear === null) return;
    setDataStatus("loading");
    setDataMessage(null);
    setPeriod(months);
    setPeriodYear(null);
  }

  /** 选择自然年后关闭滚动月份选中态，并立即请求该完整年份的活动。 */
  function changeYear(year: number) {
    if (year === periodYear) return;
    setDataStatus("loading");
    setDataMessage(null);
    setPeriodYear(year);
  }

  /** 只有选满两人才能进入对比，并从三个月活动数据开始展示。 */
  function startComparison() {
    if (selectedIds.length !== 2) return;
    resetPeriodToDefault();
    setActiveSalespersonId(null);
    setComparisonActive(true);
    setDropdownOpen(false);
  }

  /** 失败后只重试对应资源，地图与数据的错误不会相互覆盖。 */
  function retryLoad() {
    if (dataStatus === "error") {
      setDataStatus("loading");
      setDataMessage(null);
      setDataAttempt((value) => value + 1);
    }
    if (mapStatus === "error") {
      setMapStatus("loading");
      setMapMessage(null);
      setMapAttempt((value) => value + 1);
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    const query = periodYear === null ? `months=${period}` : `year=${periodYear}`;
    apiFetch<SalespersonCoverage[]>(`/public/salespeople/coverage?${query}`, { signal: controller.signal, cache: "no-store" })
      .then((data) => {
        setPeople(data);
        setDataStatus("ready");
        setSelectedIds((current) => current.filter((id) => data.some((person) => person.id === id)));
      })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setDataStatus("error");
        setDataMessage(error instanceof Error ? error.message : "销售覆盖数据加载失败");
      });
    return () => controller.abort();
  }, [dataAttempt, period, periodYear]);

  useEffect(() => {
    let disposed = false;
    if (!containerRef.current) return;
    loadAmapNamespace<SalesAmapNamespace>(["AMap.Scale"])
      .then((AMap) => {
        if (disposed || !containerRef.current) return;
        const map = new AMap.Map(containerRef.current, { viewMode: "2D", zoom: 4.35, center: [104.1, 35.6], mapStyle: "amap://styles/light", showLabel: true });
        map.addControl(new AMap.Scale());
        runtimeRef.current = { AMap, map, overlays: [] };
        setMapReady(true);
        setMapStatus("ready");
      })
      .catch((error: unknown) => { if (!disposed) { setMapStatus("error"); setMapMessage(error instanceof Error ? error.message : "地图加载失败"); } });
    return () => {
      disposed = true;
      destroyAmapMap(runtimeRef.current?.map ?? null);
      runtimeRef.current = null;
    };
  }, [mapAttempt]);

  useEffect(() => {
    const runtime = runtimeRef.current;
    if (!runtime || !mapReady || dataStatus !== "ready" || mapStatus !== "ready") return;
    const activeRuntime = runtime;
    let cancelled = false;
    let focusTimer: number | null = null;

    if (activeRuntime.overlays.length > 0) activeRuntime.map.remove(activeRuntime.overlays);
    activeRuntime.overlays = [];
    const displayedPeople = visibleIds.length > 0 ? people.filter((person) => visibleIds.includes(person.id)) : people;
    const focusMarkers: unknown[] = [];

    /** 每人绘制一个可点击位置 Pin；姓名绝对定位在上方，不扩大或遮挡相邻 Pin 的点击区。 */
    displayedPeople.forEach((person) => {
      const active = visibleIds.includes(person.id);
      const center: [number, number] = [person.coverage_center_longitude, person.coverage_center_latitude];
      const marker = new activeRuntime.AMap.Marker({
        position: center,
        anchor: "bottom-center",
        zIndex: active ? 130 : 120,
        content: `<div class="salesperson-marker ${active ? "is-active" : ""}" style="--sales-color:${person.color}" title="${escapeHtml(person.display_name)}"><b>${escapeHtml(person.display_name)}</b><span></span></div>`,
      });
      marker.on("click", () => openSalesperson(person.id));
      activeRuntime.map.add(marker);
      activeRuntime.overlays.push(marker);
      if (active) focusMarkers.push(marker);
    });

    if (visibleIds.length === 0) {
      activeRuntime.map.setZoomAndCenter(4.35, [104.1, 35.6]);
    } else if (focusMarkers.length > 0) {
      focusTimer = window.setTimeout(() => {
        focusTimer = null;
        if (cancelled) return;
        const mapRoot = containerRef.current?.parentElement ?? document.documentElement;
        activeRuntime.map.setFitView(focusMarkers, false, fitViewAvoidance(mapRoot, comparisonActive ? "compare" : "single"), 8.2);
      }, 120);
    }
    return () => {
      cancelled = true;
      if (focusTimer !== null) window.clearTimeout(focusTimer);
    };
  }, [comparisonActive, dataStatus, mapReady, mapStatus, openSalesperson, people, visibleIds]);

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      if (dropdownOpen) setDropdownOpen(false);
      else resetView();
    };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [dropdownOpen, resetView]);

  return (
    <div className="home-salesperson-coverage-map">
      <div ref={containerRef} className="salesperson-map-canvas" aria-label="全国销售人员位置地图" />
      <section className="salesperson-map-title-card" aria-labelledby="salesperson-map-title">
        <div className="salesperson-title-row"><h1 id="salesperson-map-title">销售覆盖与人效</h1>{visibleIds.length > 0 ? <button type="button" className="salesperson-title-reset" onClick={resetView}><SalesIcon name="reset" />全国视图</button> : null}</div>
        <div className="salesperson-compare-builder">
          <div className="salesperson-selected-chips" aria-label="已选择销售">
            {selectedPeople.length === 0 ? <span>最多选择两名销售进行比较</span> : selectedPeople.map((person) => (
              <span key={person.id} style={{ "--sales-color": person.color } as CSSProperties}><i />{person.display_name}<button type="button" aria-label={`移除${person.display_name}`} onClick={() => removeSalesperson(person.id)}><SalesIcon name="close" size={13} /></button></span>
            ))}
          </div>
          <div className="salesperson-selector-wrap">
            <button type="button" className="salesperson-selector-trigger" aria-expanded={dropdownOpen} onClick={() => setDropdownOpen((open) => !open)}><SalesIcon name="people" /><span>选择销售人员</span><SalesIcon name="down" size={15} /></button>
            {dropdownOpen ? <div className="salesperson-selector-menu" role="listbox" aria-label="全部销售人员">{people.map((person) => <button key={person.id} type="button" role="option" aria-selected={selectedIds.includes(person.id)} disabled={selectedIds.includes(person.id)} onClick={() => addSalesperson(person.id)}><i style={{ background: person.color }} /><span>{person.display_name}<small>{person.coverage_scopes.length} 项覆盖范围</small></span>{selectedIds.includes(person.id) ? <b>已选</b> : null}</button>)}</div> : null}
          </div>
          <button type="button" className="salesperson-compare-action" disabled={selectedIds.length !== 2} onClick={startComparison}><SalesIcon name="compare" />对比</button>
        </div>
      </section>
      {mapReady ? <div className={`salesperson-map-zoom ${activePerson || comparedPeople ? "has-panel" : ""}`} role="group" aria-label="地图缩放"><button type="button" aria-label="放大地图" onClick={() => runtimeRef.current?.map.zoomIn()}>＋</button><button type="button" aria-label="缩小地图" onClick={() => runtimeRef.current?.map.zoomOut()}>−</button></div> : null}
      {stateStatus !== "ready" ? <div className="salesperson-map-state" aria-live="polite"><SalesIcon name="people" size={22} /><strong>{stateStatus === "loading" ? "正在读取销售覆盖" : stateStatus === "error" ? "销售覆盖地图暂不可用" : "暂无销售覆盖数据"}</strong><span>{stateStatus === "loading" ? "正在汇总活动、成交与储备项目" : stateMessage ?? "请先维护销售人员及负责范围"}</span>{stateStatus === "error" ? <button type="button" onClick={retryLoad}>重新加载</button> : null}</div> : null}
      {activePerson ? <SalespersonDetail person={activePerson} period={period} year={periodYear} loading={dataStatus === "loading"} onPeriodChange={changePeriod} onYearChange={changeYear} onClose={resetView} /> : null}
      {comparedPeople ? <SalespersonComparison people={comparedPeople} period={period} year={periodYear} loading={dataStatus === "loading"} onPeriodChange={changePeriod} onYearChange={changeYear} onClose={resetView} /> : null}
    </div>
  );
}
