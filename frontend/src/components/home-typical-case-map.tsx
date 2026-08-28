"use client";

/** 首页第六地图：用可键盘操作的全国 SVG 地图浏览数据库驱动的一省一案内容。 */
import Image from "next/image";
import { useEffect, useMemo, useState, type CSSProperties, type KeyboardEvent } from "react";
import chinaMap from "@svg-maps/china";

import { apiFetch, type TypicalCaseMapResponse, type TypicalCasePublicDetail } from "@/lib/api";

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

const currencyFormatter = new Intl.NumberFormat("zh-CN", {
  style: "currency",
  currency: "CNY",
  maximumFractionDigits: 0,
});

/** 把案例接口中的 ISO 日期转成中文年月日，空值保持不展示。 */
function formatDate(value: string | null): string | null {
  if (!value) return null;
  return new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "long", day: "numeric" }).format(new Date(value));
}

/** 统一处理省份路径的 Enter/Space 选择，避免鼠标交互成为唯一入口。 */
function selectProvinceFromKeyboard(event: KeyboardEvent<SVGPathElement>, onSelect: () => void): void {
  if (event.key !== "Enter" && event.key !== " ") return;
  event.preventDefault();
  onSelect();
}

/** 展示已发布案例的完整复盘内容，并为图片失败提供稳定的文字降级。 */
function TypicalCaseStory({ detail, loading, error, onRetry }: { detail: TypicalCasePublicDetail | null; loading: boolean; error: string | null; onRetry: () => void }) {
  const [failedImage, setFailedImage] = useState<string | null>(null);
  const cover = detail?.images.find((image) => image.is_cover) ?? detail?.images[0] ?? null;

  if (loading) return <div className="typical-case-state" role="status"><i /><strong>正在展开案例复盘</strong><span>读取项目挑战、实施方案与成果指标…</span></div>;
  if (error) return <div className="typical-case-state is-error" role="alert"><strong>案例详情暂时无法读取</strong><span>{error}</span><button type="button" onClick={onRetry}>重新读取</button></div>;
  if (!detail) return null;

  const signedAt = formatDate(detail.signed_at);
  return (
    <article className="typical-case-story" aria-live="polite">
      <div className="typical-case-cover">
        {cover && failedImage !== cover.path ? (
          <Image src={cover.path} alt={cover.alt_text} fill sizes="(max-width: 900px) 100vw, 38vw" onError={() => setFailedImage(cover.path)} />
        ) : (
          <div className="typical-case-image-fallback"><span>CASE STUDY</span><b>{detail.province}</b><small>案例影像待补充</small></div>
        )}
        <span className="typical-case-cover-location">{detail.province} · {detail.city}</span>
      </div>
      <div className="typical-case-story-body">
        <div className="typical-case-meta"><span>{detail.industry_label}</span><span>{detail.customer_display_name}</span></div>
        <h2>{detail.title}</h2>
        {detail.subtitle ? <p className="typical-case-subtitle">{detail.subtitle}</p> : null}
        <p className="typical-case-summary">{detail.summary}</p>
        {detail.metrics.length > 0 ? (
          <dl className="typical-case-metrics">
            {detail.metrics.map((metric) => <div key={metric.label}><dt>{metric.label}</dt><dd>{metric.value}<small>{metric.unit}</small></dd>{metric.note ? <span>{metric.note}</span> : null}</div>)}
          </dl>
        ) : null}
        <div className="typical-case-narrative">
          <section><h3>现场挑战</h3><p>{detail.challenge}</p></section>
          <section><h3>实施方案</h3><p>{detail.solution}</p></section>
          <section><h3>交付成果</h3><p>{detail.outcome}</p></section>
          <section><h3>产品与服务</h3><p>{detail.product_scope}</p></section>
        </div>
        {detail.customer_quote ? <blockquote><p>“{detail.customer_quote}”</p>{detail.quote_attribution ? <cite>— {detail.quote_attribution}</cite> : null}</blockquote> : null}
        {detail.contract_amount || signedAt ? <footer>{detail.contract_amount ? <span>公开合同额 <b>{currencyFormatter.format(Number(detail.contract_amount))}</b></span> : null}{signedAt ? <span>签约日期 <b>{signedAt}</b></span> : null}</footer> : null}
      </div>
    </article>
  );
}

/** 组合全国案例地图、后端统计与省级详情，并隔离地图列表和详情两级请求状态。 */
export function HomeTypicalCaseMap() {
  const [mapData, setMapData] = useState<TypicalCaseMapResponse | null>(null);
  const [mapLoading, setMapLoading] = useState(true);
  const [mapError, setMapError] = useState<string | null>(null);
  const [retryKey, setRetryKey] = useState(0);
  const [selectedProvince, setSelectedProvince] = useState<string | null>(null);
  const [detail, setDetail] = useState<TypicalCasePublicDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailRetryKey, setDetailRetryKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    apiFetch<TypicalCaseMapResponse>("/public/typical-cases", { signal: controller.signal })
      .then((response) => {
        if (controller.signal.aborted) return;
        setMapData(response);
        const initial = response.regions.find((region) => region.case?.is_featured)
          ?? response.regions.find((region) => region.status === "已上线")
          ?? response.regions[0];
        setDetail(null);
        setDetailLoading(Boolean(initial?.case));
        setSelectedProvince(initial?.province ?? null);
      })
      .catch((requestError: Error) => { if (!controller.signal.aborted) setMapError(requestError.message); })
      .finally(() => { if (!controller.signal.aborted) setMapLoading(false); });
    return () => controller.abort();
  }, [retryKey]);

  const regionsByProvince = useMemo(() => new Map(mapData?.regions.map((region) => [region.province, region]) ?? []), [mapData]);
  const selectedRegion = selectedProvince ? regionsByProvince.get(selectedProvince) ?? null : null;
  const selectedCaseId = selectedRegion?.case?.id ?? null;
  // SVG 后绘制的路径位于上层；把当前省份移到末尾，避免焦点框被邻省覆盖。
  const orderedLocations = useMemo(() => [...chinaMap.locations].sort((left, right) => (
    Number((provinceNames[left.id] ?? left.name) === selectedProvince)
    - Number((provinceNames[right.id] ?? right.name) === selectedProvince)
  )), [selectedProvince]);

  useEffect(() => {
    if (!selectedCaseId) return;
    const controller = new AbortController();
    apiFetch<TypicalCasePublicDetail>(`/public/typical-cases/${selectedCaseId}`, { signal: controller.signal })
      .then((response) => { if (!controller.signal.aborted) setDetail(response); })
      .catch((requestError: Error) => { if (!controller.signal.aborted) setDetailError(requestError.message); })
      .finally(() => { if (!controller.signal.aborted) setDetailLoading(false); });
    return () => controller.abort();
  }, [selectedCaseId, detailRetryKey]);

  /** 仅重试当前已发布案例的详情请求，保留用户已经选择的省份。 */
  function retryDetail(): void {
    setDetailLoading(true);
    setDetailError(null);
    setDetailRetryKey((value) => value + 1);
  }

  /** 切换省份时立即清理旧详情，避免新省份标题下短暂显示上一次内容。 */
  function selectProvince(province: string): void {
    const nextRegion = regionsByProvince.get(province);
    setSelectedProvince(province);
    setDetail(null);
    setDetailLoading(Boolean(nextRegion?.case));
    setDetailError(null);
  }

  /** 由用户操作重置地图请求边界，确保 effect 只负责同步网络资源。 */
  function retryMap(): void {
    setMapData(null);
    setMapLoading(true);
    setMapError(null);
    setRetryKey((value) => value + 1);
  }

  if (mapLoading) return <div className="home-typical-case-map"><div className="typical-case-map-state" role="status"><i /><strong>正在绘制全国案例地图</strong><span>同步 31 个省级区域的案例状态…</span></div></div>;
  if (mapError) return <div className="home-typical-case-map"><div className="typical-case-map-state is-error" role="alert"><strong>典型案例地图暂不可用</strong><span>{mapError}</span><button type="button" onClick={retryMap}>重新加载</button></div></div>;
  if (!mapData || mapData.regions.length === 0) return <div className="home-typical-case-map"><div className="typical-case-map-state"><strong>尚未配置省级案例</strong><span>请先在管理端录入案例展示内容。</span></div></div>;

  return (
    <div className="home-typical-case-map">
      <section className="typical-case-atlas" aria-label="全国典型案例地图">
        <header>
          <div><h1>一省一案</h1><p>从全国标杆项目中，沉淀可复用的行业实践。</p></div>
          <dl><div><dt>已上线</dt><dd>{mapData.published_count}</dd></div><div><dt>筹备中</dt><dd>{mapData.pending_count}</dd></div></dl>
        </header>
        <label className="typical-case-province-select"><span>选择省份案例</span><select value={selectedProvince ?? ""} onChange={(event) => selectProvince(event.target.value)}>{mapData.regions.map((region) => <option value={region.province} key={region.province}>{region.province} · {region.status}</option>)}</select></label>
        <div className="typical-case-map-stage">
          <svg viewBox={chinaMap.viewBox} role="group" aria-label="大陆 31 个省级典型案例状态图">
            {orderedLocations.map((location: { id: string; name: string; path: string }) => {
              const province = provinceNames[location.id] ?? location.name;
              const region = regionsByProvince.get(province);
              const selected = province === selectedProvince;
              const statusClass = !region ? "is-out-of-scope" : region.status === "已上线" ? "is-published" : "is-pending";
              return <path key={location.id} d={location.path} data-province={province} className={`typical-case-province ${statusClass} ${selected ? "is-selected" : ""}`} style={{ "--case-fill": region?.status === "已上线" ? "#e95c2f" : "#d8d5cf" } as CSSProperties} tabIndex={region ? 0 : -1} role={region ? "button" : undefined} aria-pressed={region ? selected : undefined} aria-label={region ? `${province}${region.status === "已上线" ? "典型案例已上线" : "案例筹备中"}` : undefined} onClick={() => { if (region) selectProvince(province); }} onKeyDown={(event) => { if (region) selectProvinceFromKeyboard(event, () => selectProvince(province)); }}><title>{region ? `${province} · ${region.status}` : province}</title></path>;
            })}
          </svg>
          <div className="typical-case-legend"><span><i className="is-live" />已上线</span><span><i />筹备中</span><small>港澳台暂不在首期范围</small></div>
        </div>
      </section>
      <section className="typical-case-detail" aria-label="省级案例详情">
        {selectedRegion?.status === "筹备中" ? <div className="typical-case-pending"><span>{selectedRegion.province}</span><strong>{selectedRegion.province}案例筹备中</strong><p>团队正在筛选可公开、可复用的代表项目。案例通过去敏与发布审核后，将在此展示完整复盘。</p><div><i />资料归档<i />内容审核<i />正式上线</div></div> : <TypicalCaseStory detail={detail} loading={detailLoading} error={detailError} onRetry={retryDetail} />}
      </section>
    </div>
  );
}
