"use client";

/** 高德地图组件：按需加载 JSAPI，将已定位单位以 MarkerCluster 聚合，并在卸载时释放 WebGL。 */

import { useEffect, useRef, useState } from "react";

import type { MapPoint } from "@/lib/api";
import { destroyAmapMap, loadAmapNamespace } from "@/lib/amap";
import { escapeHtml } from "@/lib/html";

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

interface AMapInfoWindow {
  setContent(content: HTMLElement): void;
  open(map: AMapMap, position: [number, number]): void;
  close(): void;
}

interface AMapMap {
  addControl(control: unknown): void;
  destroy(): void;
  getFitZoomAndCenterByBounds(bounds: object, avoid: number[], maxZoom: number): [number, AMapLngLat];
  setCenter(center: [number, number]): void;
  setZoomAndCenter(zoom: number, center: [number, number] | AMapLngLat): void;
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
  Bounds: new (southWest: [number, number], northEast: [number, number]) => object;
  Pixel: new (x: number, y: number) => object;
  Map: new (container: HTMLElement, options: Record<string, unknown>) => AMapMap;
  InfoWindow: new (options: Record<string, unknown>) => AMapInfoWindow;
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

type AMapRuntime = { map: AMapMap; AMap: AMapNamespace; cluster: AMapMarkerCluster | null; infoWindow: AMapInfoWindow | null };

interface OrganizationMapProps {
  points: MapPoint[];
  selectedId: string | null;
  onSelectPoint: (point: MapPoint) => void;
  focusRegion?: boolean;
  showPointPopup?: boolean;
}

const REGION_FIT_AVOIDANCE: [number, number, number, number] = [72, 112, 96, 96];
const REGION_FIT_MAX_ZOOM = 12;

/** 为不同客户状态生成可辨认 pin，帮助在密集点位中优先识别成交和商机客户。 */
function pinColor(status: MapPoint["customer_status"]): string {
  return status === "已成交客户" ? "#0874c9" : status === "商机客户" ? "#df6f20" : "#536d5c";
}

/** 将坐标规整为稳定索引键，用于从高德 Marker 位置安全回查单位资料。 */
function pointKey(longitude: number, latitude: number): string {
  return `${longitude.toFixed(6)}:${latitude.toFixed(6)}`;
}

/** 把地图点位的安全字段组装为可关闭的信息卡，所有数据库文本先完成 HTML 转义。 */
function pointPopupContent(point: MapPoint, onClose: () => void): HTMLElement {
  const content = document.createElement("article");
  const location = [point.province, point.city, point.district].filter(Boolean).join(" · ") || "行政区待补充";
  const opportunity = point.active_opportunity_count > 0
    ? `${point.active_opportunity_count} 个推进中 · ${point.opportunity_stage ?? "阶段待补充"}`
    : "暂无推进中商机";
  const amount = Number(point.estimated_opportunity_amount);
  const amountLabel = point.active_opportunity_count > 0 && Number.isFinite(amount)
    ? `¥${new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 }).format(amount)}`
    : "—";
  content.className = "organization-map-popup";
  content.setAttribute("role", "dialog");
  content.setAttribute("aria-label", `${point.name}单位信息`);
  content.innerHTML = `
    <button class="organization-map-popup-close" type="button" aria-label="关闭单位信息">×</button>
    <header><span>单位信息</span><strong>${escapeHtml(point.name)}</strong></header>
    <div class="organization-map-popup-tags"><span>${escapeHtml(point.organization_type)}</span><span>${escapeHtml(point.customer_status)}</span></div>
    <dl>
      <div><dt>地理位置</dt><dd>${escapeHtml(location)}<small>${escapeHtml(point.address ?? "详细地址待补充")}</small><small>${point.longitude.toFixed(6)}, ${point.latitude.toFixed(6)}</small></dd></div>
      <div><dt>商机概况</dt><dd>${escapeHtml(opportunity)}</dd></div>
      <div><dt>预计金额</dt><dd class="organization-map-popup-amount">${amountLabel}</dd></div>
    </dl>
    <i class="organization-map-popup-arrow" aria-hidden="true"></i>`;
  content.querySelector<HTMLButtonElement>(".organization-map-popup-close")?.addEventListener("click", onClose, { once: true });
  return content;
}

/** 在点位上方打开唯一 InfoWindow，并让高德自动避让底部图例。 */
function openPointPopup(runtime: AMapRuntime, point: MapPoint): void {
  if (!runtime.infoWindow) return;
  runtime.infoWindow.setContent(pointPopupContent(point, () => runtime.infoWindow?.close()));
  runtime.infoWindow.open(runtime.map, [point.longitude, point.latitude]);
}

/** 按当前地区点位计算视野，并限制最大层级，避免边缘 Pin 贴住竖边界或单点过度放大。 */
function fitRegionPoints(runtime: AMapRuntime, points: MapPoint[]): void {
  if (points.length === 0) return;
  let minLongitude = points[0].longitude;
  let maxLongitude = minLongitude;
  let minLatitude = points[0].latitude;
  let maxLatitude = minLatitude;
  for (const point of points.slice(1)) {
    minLongitude = Math.min(minLongitude, point.longitude);
    maxLongitude = Math.max(maxLongitude, point.longitude);
    minLatitude = Math.min(minLatitude, point.latitude);
    maxLatitude = Math.max(maxLatitude, point.latitude);
  }
  if (minLongitude === maxLongitude && minLatitude === maxLatitude) {
    runtime.map.setZoomAndCenter(REGION_FIT_MAX_ZOOM, [minLongitude, minLatitude]);
    return;
  }
  const bounds = new runtime.AMap.Bounds([minLongitude, minLatitude], [maxLongitude, maxLatitude]);
  const [zoom, center] = runtime.map.getFitZoomAndCenterByBounds(bounds, REGION_FIT_AVOIDANCE, REGION_FIT_MAX_ZOOM);
  runtime.map.setZoomAndCenter(zoom, center);
}

/** 管理端全国目标单位地图，聚合 20,000 条以内的可信坐标并与详情抽屉联动。 */
export function AdminOrganizationMap({ points, selectedId, onSelectPoint, focusRegion = false, showPointPopup = false }: OrganizationMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const runtimeRef = useRef<AMapRuntime | null>(null);
  const selectRef = useRef(onSelectPoint);
  const pointsByCoordinateRef = useRef<Map<string, MapPoint[]>>(new Map());
  const [error, setError] = useState<string | null>(null);
  const [mapReady, setMapReady] = useState(false);

  useEffect(() => { selectRef.current = onSelectPoint; }, [onSelectPoint]);

  useEffect(() => {
    let disposed = false;
    if (!containerRef.current) return;
    loadAmapNamespace<AMapNamespace>(["AMap.MarkerCluster", "AMap.ToolBar", "AMap.Scale"])
      .then((AMap) => {
        // Strict Mode 的演练性 cleanup 不会卸载当前 DOM 容器，不能据此丢弃仍可用的 SDK 结果。
        if (disposed || !containerRef.current) return;
        const map = new AMap.Map(containerRef.current, { viewMode: "2D", zoom: 4.4, center: [104.1, 35.6], mapStyle: "amap://styles/light" });
        map.addControl(new AMap.Scale());
        map.addControl(new AMap.ToolBar({ position: "RT" }));
        const infoWindow = showPointPopup ? new AMap.InfoWindow({
          isCustom: true,
          autoMove: true,
          avoid: [24, 24, 90, 24],
          closeWhenClickMap: true,
          anchor: "bottom-center",
          offset: new AMap.Pixel(0, -16),
        }) : null;
        runtimeRef.current = { map, AMap, cluster: null, infoWindow };
        setMapReady(true);
      })
      .catch((loadError: unknown) => {
        if (!disposed) setError(loadError instanceof Error ? loadError.message : "地图加载失败");
      });
    return () => {
      disposed = true;
      runtimeRef.current?.infoWindow?.close();
      destroyAmapMap(runtimeRef.current?.map ?? null);
      runtimeRef.current = null;
    };
  }, [showPointPopup]);

  useEffect(() => {
    const runtime = runtimeRef.current;
    if (!runtime) return;
    const data: ClusterDatum[] = points.map((point) => ({ lnglat: [point.longitude, point.latitude], extData: point }));
    const pointsByCoordinate = new Map<string, MapPoint[]>();
    points.forEach((point) => {
      const key = pointKey(point.longitude, point.latitude);
      const bucket = pointsByCoordinate.get(key);
      if (bucket) bucket.push(point);
      else pointsByCoordinate.set(key, [point]);
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
          const title = escapeHtml(point?.name ?? "目标单位");
          const color = point ? pinColor(point.customer_status) : "#536d5c";
          marker.setContent(`<span class="org-map-pin" style="--pin:${color}" title="${title}"></span>`);
          marker.setAnchor("center");
          if (point) marker.on("click", () => {
            if (showPointPopup) openPointPopup(runtime, point);
            selectRef.current(point);
          });
        },
        renderClusterMarker: ({ count, marker }) => {
          marker.setContent(`<span class="org-map-cluster">${count}</span>`);
          marker.setAnchor("center");
        },
      });
    } else {
      runtime.cluster.setData(data);
    }
    if (focusRegion) fitRegionPoints(runtime, points);
  }, [focusRegion, mapReady, points, showPointPopup]);

  useEffect(() => {
    const selected = points.find((point) => point.id === selectedId);
    const runtime = runtimeRef.current;
    if (!runtime) return;
    if (!selected) {
      runtime.infoWindow?.close();
      return;
    }
    runtime.map.setCenter([selected.longitude, selected.latitude]);
    if (showPointPopup) openPointPopup(runtime, selected);
  }, [mapReady, points, selectedId, showPointPopup]);

  return (
    <div className="organization-map-shell">
      <div className="organization-map" ref={containerRef} aria-label="全国目标单位地图" />
      {error ? <div className="organization-map-message">{error}</div> : null}
      {!error && points.length === 0 ? <div className="organization-map-message">当前筛选没有已定位单位。待补地址记录仍保留在列表供核验。</div> : null}
      <div className="organization-map-legend"><span><i className="won" />已成交</span><span><i className="opportunity" />商机</span><span><i className="potential" />潜在</span><b>{points.length.toLocaleString("zh-CN")} 个可信点位</b></div>
    </div>
  );
}
