"use client";

/** 高德地图组件：按需加载 JSAPI，将已定位单位以 MarkerCluster 聚合，并在卸载时释放 WebGL。 */

import { useEffect, useRef, useState } from "react";

import type { MapPoint } from "@/lib/api";

declare global {
  interface Window {
    AMapLoader?: AMapLoaderRuntime;
    _AMapSecurityConfig?: { serviceHost: string };
  }
}

interface AMapLngLat {
  getLng(): number;
  getLat(): number;
}

interface AMapMarker {
  getPosition(): AMapLngLat | null;
  setContent(content: string): void;
  setAnchor(anchor: string): void;
  on(event: "click", handler: () => void): void;
}

interface AMapMap {
  addControl(control: unknown): void;
  destroy(): void;
  setCenter(center: [number, number]): void;
}

interface ClusterDatum {
  lnglat: [number, number];
  extData: MapPoint;
}

interface AMapMarkerCluster {
  setData(data: ClusterDatum[]): void;
}

interface AMapNamespace {
  getConfig(): { appname?: string };
  Map: new (container: HTMLElement, options: Record<string, unknown>) => AMapMap;
  Scale: new () => unknown;
  ToolBar: new (options: Record<string, unknown>) => unknown;
  MarkerCluster: new (
    map: AMapMap,
    data: ClusterDatum[],
    options: {
      gridSize: number;
      maxZoom: number;
      averageCenter: boolean;
      clusterByZoomChange: boolean;
      renderMarker: (context: { marker: AMapMarker; data?: ClusterDatum }) => void;
      renderClusterMarker: (context: { count: number; marker: AMapMarker }) => void;
    },
  ) => AMapMarkerCluster;
}

interface AMapLoaderRuntime {
  load(options: Record<string, unknown>): Promise<AMapNamespace>;
}

type AMapRuntime = { map: AMapMap; AMap: AMapNamespace; cluster: AMapMarkerCluster | null };
let amapLoaderPromise: Promise<NonNullable<Window["AMapLoader"]>> | null = null;

interface OrganizationMapProps {
  points: MapPoint[];
  selectedId: string | null;
  onSelectPoint: (point: MapPoint) => void;
}

/** 加载一次高德 Loader 脚本，保留现有项目的安全代理路径而不把安全密钥写入浏览器。 */
function loadAmapLoader(): Promise<NonNullable<Window["AMapLoader"]>> {
  if (window.AMapLoader) return Promise.resolve(window.AMapLoader);
  if (amapLoaderPromise) return amapLoaderPromise;
  const promise = new Promise<AMapLoaderRuntime>((resolve, reject) => {
    const resolveAvailableLoader = () => {
      if (window.AMapLoader) resolve(window.AMapLoader);
      else reject(new Error("高德地图加载器不可用"));
    };
    const existing = document.querySelector<HTMLScriptElement>('script[data-amap-loader="true"]');
    if (existing) {
      // React 严格模式会二次挂载组件；脚本已完成时不能再等待一个不会重放的 load 事件。
      if (existing.dataset.loaded === "true") {
        resolveAvailableLoader();
        return;
      }
      existing.addEventListener("load", resolveAvailableLoader, { once: true });
      existing.addEventListener("error", () => reject(new Error("高德地图加载器加载失败")), { once: true });
      return;
    }
    const script = document.createElement("script");
    script.src = "https://webapi.amap.com/loader.js";
    script.async = true;
    script.dataset.amapLoader = "true";
    // 记录终态，使后续 effect 可同步复用已完成的加载器。
    script.addEventListener("load", () => { script.dataset.loaded = "true"; }, { once: true });
    script.onload = resolveAvailableLoader;
    script.onerror = () => reject(new Error("高德地图加载器加载失败"));
    document.head.appendChild(script);
  }).catch((error: unknown) => {
    // 失败 Promise 不能永久缓存，否则网络恢复后所有后续挂载都会立即失败。
    amapLoaderPromise = null;
    throw error;
  });
  amapLoaderPromise = promise;
  return promise;
}

/** 为一次 SDK 加载设置终止时间，避免两个悬挂 Promise 让地图永久处于空白。 */
function loadRuntimeAttempt(loader: AMapLoaderRuntime, options: Record<string, unknown>): Promise<AMapNamespace> {
  return new Promise((resolve, reject) => {
    const timeoutId = window.setTimeout(() => reject(new Error("高德地图加载超时")), 8000);
    loader.load(options).then(resolve, reject).finally(() => window.clearTimeout(timeoutId));
  });
}

/** 加载 AMap 运行时；超时或失败时只重试一次，并最终返回明确错误。 */
async function loadAmapRuntime(loader: AMapLoaderRuntime, key: string): Promise<AMapNamespace> {
  const options = { key, version: "2.0", plugins: ["AMap.MarkerCluster", "AMap.ToolBar", "AMap.Scale"] };
  let lastError: unknown;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      return await loadRuntimeAttempt(loader, options);
    } catch (error: unknown) {
      lastError = error;
    }
  }
  throw lastError instanceof Error ? lastError : new Error("高德地图加载失败");
}

/** 为不同客户状态生成可辨认 pin，帮助在密集点位中优先识别成交和商机客户。 */
function pinColor(status: MapPoint["customer_status"]): string {
  return status === "已成交客户" ? "#0874c9" : status === "商机客户" ? "#df6f20" : "#536d5c";
}

/** 将坐标规整为稳定索引键，用于从高德 Marker 位置安全回查单位资料。 */
function pointKey(longitude: number, latitude: number): string {
  return `${longitude.toFixed(6)}:${latitude.toFixed(6)}`;
}

/** 对写入 Marker HTML 属性的单位名做最小转义，避免异常名称破坏 pin 标记。 */
function escapeHtmlAttribute(value: string): string {
  return value.replaceAll("&", "&amp;").replaceAll('"', "&quot;").replaceAll("<", "&lt;").replaceAll(">", "&gt;");
}

/** 管理端全国目标单位地图，聚合 20,000 条以内的可信坐标并与详情抽屉联动。 */
export function AdminOrganizationMap({ points, selectedId, onSelectPoint }: OrganizationMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const runtimeRef = useRef<AMapRuntime | null>(null);
  const selectRef = useRef(onSelectPoint);
  const pointsByCoordinateRef = useRef<Map<string, MapPoint[]>>(new Map());
  const [error, setError] = useState<string | null>(null);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => { selectRef.current = onSelectPoint; }, [onSelectPoint]);

  useEffect(() => {
    let disposed = false;
    const key = process.env.NEXT_PUBLIC_AMAP_JSAPI_KEY;
    if (!key || !containerRef.current) {
      setError("未配置高德 Web JS API Key，地图暂不可用。");
      return;
    }
    // 高德安全模式要求完整的同源代理地址；`/_AMapService` 必须是路径首段。
    window._AMapSecurityConfig = { serviceHost: `${window.location.origin}/_AMapService` };
    loadAmapLoader()
      .then((loader) => loadAmapRuntime(loader, key))
      .then((AMap) => {
        // 高德技能调用标识必须在创建 Map 实例前设置。
        AMap.getConfig().appname = "amap-jsapi-skill";
        // Strict Mode 的演练性 cleanup 不会卸载当前 DOM 容器，不能据此丢弃仍可用的 SDK 结果。
        if (disposed || !containerRef.current) return;
        const map = new AMap.Map(containerRef.current, { viewMode: "2D", zoom: 4.4, center: [104.1, 35.6], mapStyle: "amap://styles/light" });
        map.addControl(new AMap.Scale());
        map.addControl(new AMap.ToolBar({ position: "RT" }));
        runtimeRef.current = { map, AMap, cluster: null };
        setMapReady(true);
      })
      .catch((loadError: unknown) => {
        if (!disposed) setError(loadError instanceof Error ? loadError.message : "地图加载失败");
      });
    return () => {
      disposed = true;
      runtimeRef.current?.map.destroy();
      runtimeRef.current = null;
    };
  }, []);

  useEffect(() => {
    const runtime = runtimeRef.current;
    if (!runtime) return;
    const data: ClusterDatum[] = points.map((point) => ({ lnglat: [point.longitude, point.latitude], extData: point }));
    const pointsByCoordinate = new Map<string, MapPoint[]>();
    points.forEach((point) => {
      const key = pointKey(point.longitude, point.latitude);
      pointsByCoordinate.set(key, [...(pointsByCoordinate.get(key) ?? []), point]);
    });
    pointsByCoordinateRef.current = pointsByCoordinate;
    if (!runtime.cluster) {
      runtime.cluster = new runtime.AMap.MarkerCluster(runtime.map, data, {
        gridSize: 72,
        maxZoom: 16,
        averageCenter: true,
        clusterByZoomChange: true,
        renderMarker: ({ marker, data: markerData }) => {
          // 优先使用本轮数据；坐标索引 ref 作为不同 SDK 版本的兼容降级，始终指向最新筛选结果。
          const position = marker.getPosition();
          const point = markerData?.extData ?? (position ? pointsByCoordinateRef.current.get(pointKey(position.getLng(), position.getLat()))?.[0] : undefined);
          const title = escapeHtmlAttribute(point?.name ?? "目标单位");
          const color = point ? pinColor(point.customer_status) : "#536d5c";
          marker.setContent(`<span class="org-map-pin" style="--pin:${color}" title="${title}"></span>`);
          marker.setAnchor("center");
          if (point) marker.on("click", () => selectRef.current(point));
        },
        renderClusterMarker: ({ count, marker }) => {
          marker.setContent(`<span class="org-map-cluster">${count}</span>`);
          marker.setAnchor("center");
        },
      });
    } else {
      runtime.cluster.setData(data);
    }
  }, [mapReady, points]);

  useEffect(() => {
    const selected = points.find((point) => point.id === selectedId);
    if (selected && runtimeRef.current) runtimeRef.current.map.setCenter([selected.longitude, selected.latitude]);
  }, [mapReady, points, selectedId]);

  return (
    <div className="organization-map-shell">
      <div className="organization-map" ref={containerRef} aria-label="全国目标单位地图" />
      {error ? <div className="organization-map-message">{error}</div> : null}
      {!error && points.length === 0 ? <div className="organization-map-message">当前筛选没有已定位单位。待补地址记录仍保留在列表供核验。</div> : null}
      <div className="organization-map-legend"><span><i className="won" />已成交</span><span><i className="opportunity" />商机</span><span><i className="potential" />潜在</span><b>{points.length.toLocaleString("zh-CN")} 个可信点位</b></div>
    </div>
  );
}
