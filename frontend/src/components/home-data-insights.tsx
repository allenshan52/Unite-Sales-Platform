"use client";

/** 首页数据洞察：按账号覆盖范围展示省市下钻、大区热力、趋势和 Excel 导出。 */
import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from "react";
import chinaMap from "@svg-maps/china";
import {
  ArrowLeft,
  ArrowUpRight,
  BriefcaseBusiness,
  Building2,
  ChevronRight,
  CircleDollarSign,
  Download,
  MapPinned,
  RefreshCw,
  Target,
  TrendingUp,
  X,
} from "lucide-react";
import { projectMapCoordinates, provinceNames } from "@/components/home-organization-heatmap";
import { apiDownload, apiFetch, queryString, type InsightsMacroRegion, type InsightsMetric, type InsightsOverview, type InsightsPeriod, type InsightsRegion, type InsightsScopeMode } from "@/lib/api";

const periods: Array<{ value: InsightsPeriod; label: string }> = [
  { value: "year", label: "全年" },
  { value: "q1", label: "第一季度" },
  { value: "q2", label: "第二季度" },
  { value: "q3", label: "第三季度" },
  { value: "q4", label: "第四季度" },
];

const metricLabels: Record<InsightsMetric, string> = {
  sales: "实际销售额",
  projects: "成交项目数",
  pipeline: "商机储备",
};

const provinceIdByName = new Map(Object.entries(provinceNames).map(([id, name]) => [name, id]));

/** 把后端以元返回的固定精度金额转换为页面使用的万元数值。 */
function toWan(value: string | number): number {
  return Number(value) / 10_000;
}

/** 以中文管理报表习惯显示金额，整数不保留无意义小数。 */
function formatWan(value: string | number, digits = 0): string {
  return toWan(value).toLocaleString("zh-CN", { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/** 根据当前地图指标格式化金额或项目数。 */
function formatMetric(region: InsightsRegion, metric: InsightsMetric): string {
  return metric === "projects" ? `${region.project_count} 个` : `${formatWan(region.metric_value)} 万`;
}

/** 大区行与省市行共用同一金额/项目口径，避免界面自行重新聚合。 */
function formatMacroMetric(region: InsightsMacroRegion, metric: InsightsMetric): string {
  return metric === "projects" ? `${region.project_count} 个` : `${formatWan(region.metric_value)} 万`;
}

/** 变化率不存在时说明基期不足，避免用零增长误导。 */
function formatChange(label: string, value: string | null): string {
  if (value === null) return "暂无可比基期";
  const number = Number(value);
  return `${label} ${number >= 0 ? "+" : ""}${number.toFixed(1)}%`;
}

/** 将相对值映射到网站既有橙色体系的五档颜色。 */
function heatColor(value: number, max: number): string {
  const ratio = max ? value / max : 0;
  if (ratio >= 0.8) return "#d94a25";
  if (ratio >= 0.6) return "#e9683f";
  if (ratio >= 0.4) return "#ef8b67";
  if (ratio >= 0.2) return "#f5b69c";
  return value ? "#f9d9ca" : "#f0ebe7";
}

/** 为折线图生成不会溢出 SVG 画布的路径。 */
function linePath(values: number[], width: number, height: number, max: number): string {
  return values.map((value, index) => {
    const x = 34 + index * ((width - 68) / 11);
    const y = height - 30 - (value / max) * (height - 62);
    return `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
}

/** 根据等比适配后的 SVG 画布换算一个屏幕像素对应的地图坐标单位。 */
function mapUnitsPerPixel(viewBox: string, viewportWidth: number, viewportHeight: number): number {
  const values = viewBox.trim().split(/\s+/).map(Number);
  const viewBoxWidth = values[2];
  const viewBoxHeight = values[3];
  if (!Number.isFinite(viewBoxWidth) || !Number.isFinite(viewBoxHeight) || viewBoxWidth <= 0 || viewBoxHeight <= 0 || viewportWidth <= 0 || viewportHeight <= 0) return 1;
  const screenScale = Math.min(viewportWidth / viewBoxWidth, viewportHeight / viewBoxHeight);
  return screenScale > 0 ? 1 / screenScale : 1;
}

type CityPinLayout = {
  city: InsightsRegion;
  point: ReturnType<typeof projectMapCoordinates>;
  labelPlacement: "above" | "below";
};

/** 以屏幕距离识别重叠 Pin，并在上下两侧选择当前冲突更少的标签位置。 */
function layoutCityPins(regions: InsightsRegion[], unitsPerPixel: number): CityPinLayout[] {
  const overlapDistance = 30 * unitsPerPixel;
  const pins: CityPinLayout[] = [];
  regions.filter((city) => city.longitude !== null && city.latitude !== null).forEach((city) => {
    const point = projectMapCoordinates(city.longitude as number, city.latitude as number);
    const overlappingPins = pins.filter((pin) => Math.hypot(pin.point.x - point.x, pin.point.y - point.y) < overlapDistance);
    const aboveCount = overlappingPins.filter((pin) => pin.labelPlacement === "above").length;
    const belowCount = overlappingPins.length - aboveCount;
    pins.push({ city, point, labelPlacement: aboveCount <= belowCount ? "above" : "below" });
  });
  return pins;
}

/** 绘制数据库聚合的当前年度与上一年度月度实际销售趋势。 */
function SalesTrendChart({ overview, period }: { overview: InsightsOverview; period: InsightsPeriod }) {
  const width = 760;
  const height = 230;
  const current = overview.trend.map((item) => toWan(item.current_amount));
  const previous = overview.trend.map((item) => toWan(item.previous_amount));
  const max = Math.max(1, ...current, ...previous) * 1.12;
  const selectedQuarter = period === "year" ? null : Number(period.slice(1)) - 1;
  return (
    <div className="insight-trend-chart">
      <svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="月度实际销售额与上年同期趋势">
        <title>月度实际销售额与上年同期趋势，单位万元</title>
        {selectedQuarter !== null ? <rect className="insight-quarter-band" x={34 + selectedQuarter * 3 * ((width - 68) / 11) - 10} y="14" width={3 * ((width - 68) / 11)} height={height - 40} rx="10" /> : null}
        {[0.25, 0.5, 0.75, 1].map((tick) => <line key={tick} className="insight-grid-line" x1="34" x2={width - 34} y1={height - 30 - tick * (height - 62)} y2={height - 30 - tick * (height - 62)} />)}
        <path className="insight-line-previous" d={linePath(previous, width, height, max)} />
        <path className="insight-line-current" d={linePath(current, width, height, max)} />
        {current.map((value, index) => {
          const x = 34 + index * ((width - 68) / 11);
          const y = height - 30 - (value / max) * (height - 62);
          return <circle key={index} className="insight-line-dot" cx={x} cy={y} r="3.5"><title>{`${index + 1}月：${value.toLocaleString("zh-CN")} 万元`}</title></circle>;
        })}
        {current.map((_, index) => <text key={index} className="insight-axis-label" x={34 + index * ((width - 68) / 11)} y={height - 9}>{index + 1}月</text>)}
      </svg>
    </div>
  );
}

/** 读取一份可取消的洞察聚合，筛选变化时不会让旧响应覆盖新响应。 */
function useInsightsOverview(year: number, period: InsightsPeriod, metric: InsightsMetric, scopeMode: InsightsScopeMode, province?: string, enabled = true) {
  const [data, setData] = useState<InsightsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [version, setVersion] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const timeoutId = window.setTimeout(() => {
      setData(null);
      setLoading(enabled);
      setError(null);
      if (!enabled) return;
      void apiFetch<InsightsOverview>(`/public/insights/overview${queryString({ year: String(year), period, metric, scope_mode: scopeMode, province })}`, { signal: controller.signal })
        .then(setData)
        .catch((requestError: unknown) => {
          if (requestError instanceof DOMException && requestError.name === "AbortError") return;
          setError(requestError instanceof Error ? requestError.message : "数据洞察加载失败");
        })
        .finally(() => { if (!controller.signal.aborted) setLoading(false); });
    }, 0);
    return () => { window.clearTimeout(timeoutId); controller.abort(); };
  }, [enabled, metric, period, province, scopeMode, version, year]);

  return { data, loading, error, retry: () => setVersion((current) => current + 1) };
}

/** 组合账号专属筛选、地图、区域清单、单位清单和城市详情抽屉。 */
export function HomeDataInsights() {
  const rootRef = useRef<HTMLDivElement>(null);
  const mapSvgRef = useRef<SVGSVGElement>(null);
  const [year, setYear] = useState(new Date().getFullYear());
  const [period, setPeriod] = useState<InsightsPeriod>("year");
  const [metric, setMetric] = useState<InsightsMetric>("sales");
  const [scopeMode, setScopeMode] = useState<InsightsScopeMode>("assigned");
  const [selectedProvince, setSelectedProvince] = useState<string | null>(null);
  const [selectedCity, setSelectedCity] = useState<InsightsRegion | null>(null);
  const [cityOverview, setCityOverview] = useState<InsightsOverview | null>(null);
  const [cityLoading, setCityLoading] = useState(false);
  const [cityError, setCityError] = useState<string | null>(null);
  const [mapViewBox, setMapViewBox] = useState(chinaMap.viewBox);
  const [cityPinUnitsPerPixel, setCityPinUnitsPerPixel] = useState(1);
  const [toast, setToast] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const national = useInsightsOverview(year, period, metric, scopeMode);
  const province = useInsightsOverview(year, period, metric, scopeMode, selectedProvince ?? undefined, selectedProvince !== null);
  const overview = selectedProvince ? province.data ?? national.data : national.data;

  const nationalRegionByMapId = useMemo(() => {
    const result = new Map<string, InsightsRegion>();
    national.data?.regions.forEach((region) => {
      const mapId = provinceIdByName.get(region.name);
      if (mapId) result.set(mapId, region);
    });
    return result;
  }, [national.data]);
  const macroRegionByProvince = useMemo(() => {
    const result = new Map<string, InsightsMacroRegion>();
    national.data?.macro_regions.forEach((region) => region.provinces.forEach((provinceName) => result.set(provinceName, region)));
    return result;
  }, [national.data]);
  const mapMax = scopeMode === "region"
    ? Math.max(0, ...(national.data?.macro_regions.map((item) => Number(item.metric_value)) ?? []))
    : Math.max(0, ...[...nationalRegionByMapId.values()].map((item) => Number(item.metric_value)));

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      setSelectedCity(null);
      setCityOverview(null);
      setCityError(null);
    });
    return () => cancelAnimationFrame(frame);
  }, [metric, period, scopeMode, selectedProvince, year]);

  useEffect(() => {
    const frame = requestAnimationFrame(() => {
      if (!selectedProvince) {
        setMapViewBox(chinaMap.viewBox);
        return;
      }
      const mapId = provinceIdByName.get(selectedProvince);
      const path = mapId ? rootRef.current?.querySelector<SVGGraphicsElement>(`[data-insight-province="${mapId}"]`) : null;
      if (!path) return;
      const box = path.getBBox();
      const horizontalPadding = Math.max(12, box.width * 0.22);
      const verticalPadding = Math.max(12, box.height * 0.25);
      setMapViewBox(`${box.x - horizontalPadding} ${box.y - verticalPadding} ${box.width + horizontalPadding * 2} ${box.height + verticalPadding * 2}`);
    });
    return () => cancelAnimationFrame(frame);
  }, [selectedProvince]);

  useEffect(() => {
    const svg = mapSvgRef.current;
    if (!svg || !selectedProvince) return;
    /** 同步 SVG 画布变化，避免窗口尺寸调整后 Pin 再次失去统一比例。 */
    const updatePinScale = () => {
      setCityPinUnitsPerPixel(mapUnitsPerPixel(mapViewBox, svg.clientWidth, svg.clientHeight));
    };
    updatePinScale();
    const observer = new ResizeObserver(updatePinScale);
    observer.observe(svg);
    return () => observer.disconnect();
  }, [mapViewBox, selectedProvince]);

  useEffect(() => {
    if (!toast) return;
    const timer = window.setTimeout(() => setToast(null), 2600);
    return () => window.clearTimeout(timer);
  }, [toast]);

  /** 点击城市后按需读取城市统计，抽屉不复用省级数据冒充。 */
  const openCity = useCallback((city: InsightsRegion) => {
    if (!selectedProvince) return;
    const controller = new AbortController();
    setSelectedCity(city);
    setCityOverview(null);
    setCityError(null);
    setCityLoading(true);
    apiFetch<InsightsOverview>(`/public/insights/overview${queryString({ year: String(year), period, metric, scope_mode: scopeMode, province: selectedProvince, city: city.name })}`, { signal: controller.signal })
      .then(setCityOverview)
      .catch((requestError: unknown) => setCityError(requestError instanceof Error ? requestError.message : "城市统计加载失败"))
      .finally(() => setCityLoading(false));
  }, [metric, period, scopeMode, selectedProvince, year]);

  /** 返回全国层级并恢复完整地图视图。 */
  function resetProvince() {
    setSelectedProvince(null);
    setSelectedCity(null);
    setCityOverview(null);
    setMapViewBox(chinaMap.viewBox);
  }

  /** 下载与页面完全相同年份、期间、指标和区域范围的 Excel。 */
  async function exportReport(city?: string) {
    const scopeProvince = selectedProvince ?? undefined;
    setExporting(true);
    try {
      await apiDownload(
        `/public/insights/export${queryString({ year: String(year), period, metric, scope_mode: scopeMode, province: scopeProvince, city })}`,
        `${year}年-${city ?? selectedProvince ?? "全国"}-区域经营报表.xlsx`,
      );
      setToast("Excel 报表已按当前筛选导出");
    } catch (requestError) {
      setToast(requestError instanceof Error ? requestError.message : "导出失败，请稍后重试");
    } finally {
      setExporting(false);
    }
  }

  const currentLoading = selectedProvince ? province.loading : national.loading;
  const currentError = selectedProvince ? province.error : national.error;
  const currentRetry = selectedProvince ? province.retry : national.retry;
  const periodLabel = periods.find((item) => item.value === period)?.label ?? "全年";
  const years = national.data?.available_years.length ? national.data.available_years : [year];

  if (!national.data && national.loading) {
    return <div className="insight-shell"><div className="insight-page-state" role="status"><RefreshCw className="is-spinning" size={22} /><b>正在聚合数据库经营数据</b><span>成交、商机与区域指标会使用同一统计口径。</span></div></div>;
  }
  if (!national.data && national.error) {
    return <div className="insight-shell"><div className="insight-page-state is-error" role="alert"><b>数据洞察暂时无法加载</b><span>{national.error}</span><button type="button" onClick={national.retry}><RefreshCw size={14} />重新加载</button></div></div>;
  }
  if (!national.data || !overview) return null;

  const cityPins = selectedProvince ? layoutCityPins(overview.regions, cityPinUnitsPerPixel) : [];

  const kpis = [
    { label: "实际销售额", value: formatWan(overview.kpis.sales_amount), unit: "万元", change: formatChange("同比", overview.kpis.sales_yoy_percent), icon: CircleDollarSign, tone: "orange" },
    { label: "成交项目", value: overview.kpis.project_count.toLocaleString("zh-CN"), unit: "个", change: formatChange("同比", overview.kpis.projects_yoy_percent), icon: BriefcaseBusiness, tone: "blue" },
    { label: "平均成交额", value: formatWan(overview.kpis.average_deal_amount), unit: "万元", change: period === "year" ? "本年度合同均值" : formatChange("销售额环比", overview.kpis.sales_qoq_percent), icon: TrendingUp, tone: "green" },
    { label: "推进中商机", value: formatWan(overview.kpis.pipeline_amount), unit: "万元", change: `${overview.kpis.pipeline_count} 个当前有效商机`, icon: Target, tone: "purple" },
    { label: "有数据区域", value: overview.kpis.active_region_count.toLocaleString("zh-CN"), unit: selectedProvince ? "个城市" : "个省份", change: "成交或商机覆盖", icon: MapPinned, tone: "ink" },
  ];

  return (
    <div className="insight-shell" ref={rootRef} aria-busy={currentLoading}>
      <header className="insight-header panel-enter">
        <div>
          <span className="insight-eyebrow"><i />数据洞察 · 数据库实时聚合</span>
          <h1>专属区域经营洞察</h1>
          <p>仅汇总账号负责范围；大区视角会展开所覆盖省市所属的完整大区 · 更新于 {new Date(overview.aggregated_at).toLocaleString("zh-CN", { hour12: false })}</p>
        </div>
        <div className="insight-toolbar" aria-label="数据洞察筛选">
          <label><span>年份</span><select aria-label="年份" value={year} onChange={(event) => setYear(Number(event.target.value))}>{years.map((item) => <option key={item}>{item}</option>)}</select></label>
          <label><span>统计期间</span><select aria-label="统计期间" value={period} onChange={(event) => setPeriod(event.target.value as InsightsPeriod)}>{periods.map((item) => <option key={item.value} value={item.value}>{item.label}</option>)}</select></label>
          <label><span>地图指标</span><select aria-label="地图指标" value={metric} onChange={(event) => setMetric(event.target.value as InsightsMetric)}>{Object.entries(metricLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label>
          <label><span>数据范围</span><select aria-label="数据范围" value={scopeMode} onChange={(event) => { setScopeMode(event.target.value as InsightsScopeMode); resetProvince(); }}><option value="assigned">负责范围</option><option value="region">大区视角</option></select></label>
          <button className="insight-export" type="button" onClick={() => void exportReport()} disabled={exporting}>{exporting ? <RefreshCw className="is-spinning" size={16} /> : <Download size={16} />}{exporting ? "正在导出" : "导出报表"}</button>
        </div>
      </header>

      {currentError ? <div className="insight-inline-error" role="alert"><span>{currentError}</span><button type="button" onClick={currentRetry}>重试</button></div> : null}

      <section className="insight-kpis panel-enter" aria-label={`${overview.scope.name}核心经营指标`}>
        {kpis.map((kpi) => {
          const KpiIcon = kpi.icon;
          return <article className={`insight-kpi is-${kpi.tone}`} key={kpi.label}><div><span>{kpi.label}</span><KpiIcon size={17} /></div><strong>{kpi.value}<small>{kpi.unit}</small></strong><p><ArrowUpRight size={13} />{kpi.change}</p></article>;
        })}
      </section>

      <section className="insight-main-grid panel-enter">
        <article className="insight-card insight-map-card">
          <header className="insight-card-head">
            <div>
              <nav className="insight-breadcrumb" aria-label="区域层级">
                <button type="button" className={!selectedProvince ? "is-current" : ""} onClick={resetProvince}>全国</button>
                {selectedProvince ? <><ChevronRight size={13} /><span>{selectedProvince}</span></> : null}
              </nav>
              <h2>{selectedProvince ? `${selectedProvince}城市数据` : scopeMode === "region" ? "大区金额热力" : "负责区域数据"}</h2>
            </div>
            <span className="insight-scope-note">{selectedProvince ? "点击城市查看统计，点击相邻省份直接切换" : "点击省份下钻到城市"}</span>
          </header>
          <div className="insight-map-stage">
            <svg ref={mapSvgRef} className={`insight-map ${selectedProvince ? "is-drilled" : ""}`} viewBox={mapViewBox} preserveAspectRatio="xMidYMid meet" role="group" aria-label={`${overview.scope.name}${metricLabels[metric]}分布图`}>
              <g>
                {chinaMap.locations.map((location: { id: string; name: string; path: string }) => {
                  const datum = nationalRegionByMapId.get(location.id);
                  const macroRegion = datum ? macroRegionByProvince.get(datum.name) : undefined;
                  const heatValue = scopeMode === "region" && macroRegion ? Number(macroRegion.metric_value) : Number(datum?.metric_value ?? 0);
                  const isSelected = (provinceNames[location.id] ?? location.name) === selectedProvince;
                  return <path
                    key={location.id}
                    d={location.path}
                    data-insight-province={location.id}
                    className={`insight-province ${datum ? "has-data" : ""} ${isSelected ? "is-selected" : ""}`}
                    style={{ "--insight-fill": datum ? heatColor(heatValue, mapMax) : "#f0ebe7" } as CSSProperties}
                    tabIndex={datum ? 0 : -1}
                    role={datum ? "button" : undefined}
                    aria-label={datum ? `查看${datum.name}${metricLabels[metric]}，${scopeMode === "region" && macroRegion ? formatMacroMetric(macroRegion, metric) : formatMetric(datum, metric)}` : undefined}
                    onClick={() => datum && setSelectedProvince(datum.name)}
                    onKeyDown={(event) => { if (datum && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); setSelectedProvince(datum.name); } }}
                  ><title>{datum ? `${datum.name} · ${scopeMode === "region" && macroRegion ? `${macroRegion.name} ${formatMacroMetric(macroRegion, metric)}` : formatMetric(datum, metric)}` : provinceNames[location.id] ?? location.name}</title></path>;
                })}
              </g>
              {selectedProvince ? <g className="insight-city-layer">
                {cityPins.map(({ city, point, labelPlacement }) => {
                  const radius = 12 * cityPinUnitsPerPixel;
                  const hitRadius = 18 * cityPinUnitsPerPixel;
                  const haloRadius = 15 * cityPinUnitsPerPixel;
                  const labelBelow = labelPlacement === "below";
                  const labelY = (labelBelow ? 20 : -22) * cityPinUnitsPerPixel;
                  return <g key={city.id} className="insight-city-node" transform={`translate(${point.x} ${point.y})`} role="button" tabIndex={0} aria-label={`查看${city.name}经营详情`} onClick={() => openCity(city)} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); openCity(city); } }}>
                    <circle className="insight-city-hit" r={hitRadius} />
                    <circle className="insight-city-halo" r={haloRadius} vectorEffect="non-scaling-stroke" />
                    <circle className="insight-city-dot" r={radius} vectorEffect="non-scaling-stroke" />
                    <text y={labelY} dominantBaseline={labelBelow ? "hanging" : "auto"} data-label-placement={labelPlacement} style={{ fontSize: `${13 * cityPinUnitsPerPixel}px`, strokeWidth: `${3.5 * cityPinUnitsPerPixel}px` }}>{city.name.replace(/市$/, "")}</text>
                    <title>{`${city.name} · ${formatWan(city.sales_amount)} 万元`}</title>
                  </g>;
                })}
              </g> : null}
            </svg>
            {selectedProvince ? <div className="insight-map-controls">
              <button className="insight-map-back" type="button" onClick={resetProvince}><ArrowLeft size={15} />返回全国</button>
              <select className="insight-map-province-select" aria-label="直接切换省份" value={selectedProvince} onChange={(event) => setSelectedProvince(event.target.value)}>
                {national.data.regions.map((region) => <option key={region.id} value={region.name}>{region.name}</option>)}
              </select>
            </div> : null}
            <div className="insight-map-legend"><span>低</span>{["#f9d9ca", "#f5b69c", "#ef8b67", "#e9683f", "#d94a25"].map((color) => <i key={color} style={{ background: color }} />)}<span>高</span><b>{metricLabels[metric]}</b></div>
            {currentLoading ? <div className="insight-card-loading" role="status"><RefreshCw className="is-spinning" size={16} />正在更新区域数据</div> : null}
          </div>
        </article>

        <article className="insight-card insight-ranking-card">
          <header className="insight-card-head"><div><span className="insight-card-kicker">范围明细</span><h2>{selectedProvince ? "全部城市数据" : scopeMode === "region" ? "全部大区数据" : "全部省份数据"}</h2></div><b>{periodLabel}</b></header>
          {!selectedProvince && scopeMode === "region" && overview.macro_regions.length ? <ol className="insight-ranking-list">
            {overview.macro_regions.map((region) => {
              const maxValue = Math.max(0, ...overview.macro_regions.map((item) => Number(item.metric_value)));
              const barWidth = maxValue ? (Number(region.metric_value) / maxValue) * 100 : 0;
              return <li key={region.id}>
                <div className="insight-region-row">
                  <i>区</i>
                  <span><b>{region.name}</b><small aria-label={`${metricLabels[metric]}相对强度`}><em style={{ width: `${barWidth}%` }} /></small></span>
                  <strong>{formatMacroMetric(region, metric)}<small>覆盖 {region.provinces.join("、")}</small></strong>
                </div>
              </li>;
            })}
          </ol> : overview.regions.length ? <ol className="insight-ranking-list">
            {overview.regions.map((region) => {
              const maxValue = Math.max(0, ...overview.regions.map((item) => Number(item.metric_value)));
              const barWidth = maxValue ? (Number(region.metric_value) / maxValue) * 100 : 0;
              return <li key={region.id}>
                <button type="button" onClick={() => selectedProvince ? openCity(region) : setSelectedProvince(region.name)} aria-label={`查看${region.name}详情`}>
                  <i>{selectedProvince ? "市" : "省"}</i>
                  <span><b>{region.name}</b><small aria-label={`${metricLabels[metric]}相对强度`}><em style={{ width: `${barWidth}%` }} /></small></span>
                  <strong>{formatMetric(region, metric)}<small>贡献 {Number(region.contribution_percent).toFixed(1)}% · {metric === "pipeline" ? "当前快照" : formatChange("同比", region.yoy_percent)}</small></strong>
                </button>
              </li>;
            })}
          </ol> : <div className="insight-empty">当前负责范围暂无区域成交或有效商机</div>}
        </article>
      </section>

      <section className="insight-lower-grid panel-enter">
        <article className="insight-card insight-trend-card">
          <header className="insight-card-head"><div><span className="insight-card-kicker">增长趋势</span><h2>{overview.scope.name}月度实际销售</h2></div><div className="insight-chart-legend"><span><i className="is-current" />{year} 年</span><span><i />{year - 1} 年</span></div></header>
          <SalesTrendChart overview={overview} period={period} />
        </article>
        <aside className="insight-card insight-signals">
          <header className="insight-card-head"><div><span className="insight-card-kicker">经营提示</span><h2>值得关注</h2></div><TrendingUp size={18} /></header>
          {overview.signals.map((signal, index) => <div className={`insight-signal is-${signal.tone}`} key={`${signal.title}-${index}`}><span>{String(index + 1).padStart(2, "0")}</span><p><b>{signal.title}</b>{signal.description}</p></div>)}
        </aside>
      </section>

      <article className="insight-card insight-customer-card panel-enter">
        <header className="insight-card-head"><div><span className="insight-card-kicker">成交质量</span><h2>Top 10 成交单位</h2></div><span className="insight-scope-note">{overview.scope.name} · 当前显示 {overview.top_customers.length} 条</span></header>
        {overview.top_customers.length ? <div className="insight-table-wrap"><table><thead><tr><th>排名</th><th>成交单位</th><th>区域</th><th>成交金额</th><th>项目数</th><th>最近签约</th></tr></thead><tbody>{overview.top_customers.map((customer) => <tr key={`${customer.rank}-${customer.name}`}><td><i>{String(customer.rank).padStart(2, "0")}</i></td><td><Building2 size={15} />{customer.name}</td><td>{customer.city || customer.province}</td><td><strong>{formatWan(customer.sales_amount)} 万</strong></td><td>{customer.project_count} 个</td><td>{customer.latest_signed_at ?? "未填写"}</td></tr>)}</tbody></table></div> : <div className="insight-empty">当前期间暂无成交单位</div>}
      </article>

      {selectedCity ? <aside className="insight-detail-drawer" role="dialog" aria-modal="true" aria-label={`${selectedCity.name}年度统计`}>
        <header><div><span>城市经营统计 · 数据库聚合</span><h2>{selectedCity.name}</h2><p>{year} 年 · {periodLabel}</p></div><button type="button" onClick={() => setSelectedCity(null)} aria-label="关闭城市详情"><X size={19} /></button></header>
        {cityLoading ? <div className="insight-drawer-state" role="status"><RefreshCw className="is-spinning" size={18} />正在聚合城市数据</div> : cityError ? <div className="insight-drawer-state is-error" role="alert">{cityError}</div> : cityOverview ? <>
          <div className="insight-drawer-total"><span>实际销售额</span><strong>{formatWan(cityOverview.kpis.sales_amount)}<small>万元</small></strong><p><TrendingUp size={14} />{formatChange("同比", cityOverview.kpis.sales_yoy_percent)}{period === "year" ? "" : ` · ${formatChange("环比", cityOverview.kpis.sales_qoq_percent)}`}</p></div>
          <div className="insight-drawer-kpis"><article><span>成交项目</span><b>{cityOverview.kpis.project_count} 个</b></article><article><span>平均成交额</span><b>{formatWan(cityOverview.kpis.average_deal_amount)} 万</b></article><article><span>当前商机储备</span><b>{formatWan(cityOverview.kpis.pipeline_amount)} 万</b></article><article><span>省内贡献占比</span><b>{Number(selectedCity.contribution_percent).toFixed(1)}%</b></article></div>
          <section className="insight-stage-block">{cityOverview.stages.map((stage) => <div key={stage.stage}><span>{stage.stage}</span><b>{Number(stage.percent).toFixed(1)}%</b></div>)}<i>{cityOverview.stages.map((stage, index) => <em key={stage.stage} style={{ width: `${Number(stage.percent)}%`, background: ["#d9c9f2", "#b69be4", "#9577d5", "#7356bc"][index] }} />)}</i></section>
          <section className="insight-drawer-list"><h3>主要成交单位</h3>{cityOverview.top_customers.length ? cityOverview.top_customers.slice(0, 5).map((customer) => <div key={`${customer.rank}-${customer.name}`}><i>{customer.rank}</i><span>{customer.name}<small>{customer.latest_signed_at ?? "未填写"}</small></span><b>{formatWan(customer.sales_amount)} 万</b></div>) : <p className="insight-drawer-empty">当前期间暂无成交单位</p>}</section>
          <button className="insight-drawer-export" type="button" onClick={() => void exportReport(selectedCity.name)} disabled={exporting}><Download size={16} />导出该城市 Excel 报表</button>
        </> : null}
      </aside> : null}
      <div className={`insight-toast ${toast ? "is-visible" : ""}`} role="status" aria-live="polite">{toast}</div>
    </div>
  );
}
