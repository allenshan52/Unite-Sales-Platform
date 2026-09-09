/** Playwright 高德替身：离线模拟 Marker、Circle、文本与矢量覆盖物，让地图交互测试不依赖外部 SDK。 */

import type { Page } from "@playwright/test";

interface FakeAmapOptions {
  districtDelayByAdcode?: Record<string, number>;
  districtFailuresByAdcode?: Record<string, { times: number; info: string; infocode?: string }>;
}

/** 注入最小 AMap 接口，覆盖点位和行政区矢量图形测试。 */
export async function installFakeAmap(page: Page, options: FakeAmapOptions = {}): Promise<void> {
  await page.addInitScript((fakeOptions) => {
    type Overlay = { element?: HTMLButtonElement; kind: "circle" | "marker" | "polyline" | "polygon" | "text"; on(event: string, handler: () => void): void };
    type FitCall = { overlayKinds: Overlay["kind"][]; immediately: boolean; avoid: number[]; maxZoom: number };
    type BoundsFitCall = { southWest: [number, number]; northEast: [number, number]; avoid: number[]; maxZoom: number };
    type ViewportCall = { zoom: number; center: [number, number] };
    const testWindow = window as Window & { __fakeAmapDistrictCalls?: Record<string, number>; __fakeAmapDistrictConcurrency?: { active: number; max: number }; __fakeAmapFitCalls?: FitCall[]; __fakeAmapBoundsFitCalls?: BoundsFitCall[]; __fakeAmapZoomCalls?: Array<"in" | "out">; __fakeAmapViewportCalls?: ViewportCall[] };
    testWindow.__fakeAmapDistrictCalls = {};
    testWindow.__fakeAmapDistrictConcurrency = { active: 0, max: 0 };
    testWindow.__fakeAmapFitCalls = [];
    testWindow.__fakeAmapBoundsFitCalls = [];
    testWindow.__fakeAmapZoomCalls = [];
    testWindow.__fakeAmapViewportCalls = [];
    const config: { appname?: string } = {};

    class FakeMarker implements Overlay {
      element: HTMLButtonElement;
      kind = "marker" as const;
      position: [number, number];

      constructor(options: Record<string, unknown>) {
        const [longitude, latitude] = options.position as [number, number];
        this.position = [longitude, latitude];
        this.element = document.createElement("button");
        this.element.type = "button";
        this.element.className = "fake-amap-overlay";
        this.element.dataset.longitude = String(longitude);
        this.element.dataset.latitude = String(latitude);
        this.element.style.cssText = `position:absolute;left:${Math.max(5, Math.min(88, ((longitude - 73) / 62) * 100))}%;top:${Math.max(8, Math.min(86, ((54 - latitude) / 36) * 100))}%;z-index:${String(options.zIndex ?? 100)};border:0;background:transparent;padding:0`;
        this.element.innerHTML = String(options.content ?? "");
      }

      on(event: string, handler: () => void): void {
        this.element.addEventListener(event, handler);
      }

      getPosition(): { getLng(): number; getLat(): number } {
        return { getLng: () => this.position[0], getLat: () => this.position[1] };
      }

      setContent(content: string): void { this.element.innerHTML = content; }
      setAnchor(): void {}

      setOptions(options: Record<string, unknown>): void {
        if (options.fillOpacity !== undefined) this.element.style.opacity = String(options.fillOpacity);
        if (options.strokeWeight !== undefined) this.element.style.borderWidth = `${String(options.strokeWeight)}px`;
      }
    }

    class FakePolyline implements Overlay {
      kind = "polyline" as const;

      on(): void {}
    }

    class FakePolygon implements Overlay {
      element: HTMLButtonElement;
      kind = "polygon" as const;

      constructor(options: Record<string, unknown>) {
        const path = options.path as Array<Array<[number, number]>>;
        const [longitude, latitude] = path[0]?.[0] ?? [104, 35];
        this.element = document.createElement("button");
        this.element.type = "button";
        this.element.className = "fake-amap-polygon";
        this.element.style.cssText = `position:absolute;left:${Math.max(5, Math.min(88, ((longitude - 73) / 62) * 100))}%;top:${Math.max(8, Math.min(86, ((54 - latitude) / 36) * 100))}%;width:48px;height:36px;transform:translate(-50%,-50%);border:${String(options.strokeWeight ?? 1)}px solid ${String(options.strokeColor)};background:${String(options.fillColor)};opacity:${String(options.fillOpacity ?? 0.24)};z-index:${String(options.zIndex ?? 50)}`;
      }

      on(event: string, handler: () => void): void { this.element.addEventListener(event, handler); }
      setOptions(options: Record<string, unknown>): void {
        if (options.fillOpacity !== undefined) this.element.style.opacity = String(options.fillOpacity);
        if (options.strokeWeight !== undefined) this.element.style.borderWidth = `${String(options.strokeWeight)}px`;
      }
    }

    class FakeText implements Overlay {
      element: HTMLButtonElement;
      kind = "text" as const;

      constructor(options: Record<string, unknown>) {
        const [longitude, latitude] = options.position as [number, number];
        this.element = document.createElement("button");
        this.element.type = "button";
        this.element.className = "fake-amap-text";
        this.element.style.cssText = `position:absolute;left:${Math.max(5, Math.min(88, ((longitude - 73) / 62) * 100))}%;top:${Math.max(8, Math.min(86, ((54 - latitude) / 36) * 100))}%;z-index:${String(options.zIndex ?? 120)};border:0;background:transparent;padding:0`;
        this.element.innerHTML = String(options.text ?? "");
      }

      on(event: string, handler: () => void): void { this.element.addEventListener(event, handler); }
    }

    class FakeDistrictSearch {
      /** 由 adcode 生成稳定矩形与中心，足以验证市级边界渲染和视口聚焦。 */
      search(keyword: string, callback: (status: string, result: unknown) => void): void {
        const calls = testWindow.__fakeAmapDistrictCalls ?? {};
        calls[keyword] = (calls[keyword] ?? 0) + 1;
        testWindow.__fakeAmapDistrictCalls = calls;
        const concurrency = testWindow.__fakeAmapDistrictConcurrency ?? { active: 0, max: 0 };
        concurrency.active += 1;
        concurrency.max = Math.max(concurrency.max, concurrency.active);
        testWindow.__fakeAmapDistrictConcurrency = concurrency;
        const respond = () => {
          concurrency.active -= 1;
          const configuredFailure = fakeOptions.districtFailuresByAdcode?.[keyword];
          if (configuredFailure && calls[keyword] <= configuredFailure.times) {
            callback("error", { info: configuredFailure.info, infocode: configuredFailure.infocode });
            return;
          }
          const seed = Number(keyword);
          const longitude = 82 + (seed % 41);
          const latitude = 20 + (Math.floor(seed / 41) % 25);
          callback("complete", { districtList: [{ center: { lng: longitude, lat: latitude }, boundaries: [[[longitude - 0.5, latitude - 0.4], [longitude + 0.5, latitude - 0.4], [longitude + 0.5, latitude + 0.4], [longitude - 0.5, latitude + 0.4]]] }] });
        };
        const delay = fakeOptions.districtDelayByAdcode?.[keyword] ?? 0;
        if (delay > 0) window.setTimeout(respond, delay);
        else respond();
      }
    }

    class FakeBounds {
      constructor(public southWest: [number, number], public northEast: [number, number]) {}
    }

    class FakeMap {
      container: HTMLElement;

      constructor(container: HTMLElement) {
        this.container = container;
        const base = document.createElement("div");
        base.className = "fake-amap-base";
        base.style.cssText = "position:absolute;inset:0;background:linear-gradient(135deg,#e8f0eb,#dfeae5 58%,#edf2ee);";
        this.container.appendChild(base);
      }

      add(overlays: Overlay | Overlay[]): void {
        const items = Array.isArray(overlays) ? overlays : [overlays];
        items.forEach((overlay) => { if (overlay.element) this.container.appendChild(overlay.element); });
      }

      remove(overlays: Overlay | Overlay[]): void {
        const items = Array.isArray(overlays) ? overlays : [overlays];
        items.forEach((overlay) => overlay.element?.remove());
      }

      addControl(): void {}
      setFitView(overlays: Overlay[], immediately: boolean, avoid: number[], maxZoom: number): void {
        testWindow.__fakeAmapFitCalls?.push({ overlayKinds: overlays.map((overlay) => overlay.kind), immediately, avoid, maxZoom });
      }
      /** 按经纬度边界返回稳定中心，记录四向留白与最大层级供地区视野测试断言。 */
      getFitZoomAndCenterByBounds(bounds: FakeBounds, avoid: number[], maxZoom: number): [number, { getLng(): number; getLat(): number }] {
        testWindow.__fakeAmapBoundsFitCalls?.push({ southWest: bounds.southWest, northEast: bounds.northEast, avoid, maxZoom });
        const longitude = (bounds.southWest[0] + bounds.northEast[0]) / 2;
        const latitude = (bounds.southWest[1] + bounds.northEast[1]) / 2;
        return [maxZoom, { getLng: () => longitude, getLat: () => latitude }];
      }
      /** 记录全国总览视野，验证区域叠加不会触发局部 fitView。 */
      setZoomAndCenter(zoom: number, center: [number, number] | { getLng(): number; getLat(): number }): void {
        const coordinates: [number, number] = Array.isArray(center) ? center : [center.getLng(), center.getLat()];
        testWindow.__fakeAmapViewportCalls?.push({ zoom, center: coordinates });
      }
      /** 模拟真实地图的选中点居中能力，避免单位弹窗测试因接口缺失中断。 */
      setCenter(): void {}
      /** 记录放大操作，验证自定义控件确实委托给地图实例。 */
      zoomIn(): void { testWindow.__fakeAmapZoomCalls?.push("in"); }
      /** 记录缩小操作，验证横排控件的两个方向均可用。 */
      zoomOut(): void { testWindow.__fakeAmapZoomCalls?.push("out"); }
      destroy(): void { this.container.replaceChildren(); }
    }

    class FakeInfoWindow {
      content: HTMLElement | null = null;
      element: HTMLDivElement | null = null;

      /** 在替身地图的相同坐标位置挂载自定义内容，供 Popup 交互测试使用。 */
      setContent(content: HTMLElement): void { this.content = content; }

      open(map: FakeMap, position: [number, number]): void {
        this.close();
        if (!this.content) return;
        const [longitude, latitude] = position;
        this.element = document.createElement("div");
        this.element.className = "fake-amap-info-window";
        this.element.style.cssText = `position:absolute;left:${Math.max(12, Math.min(82, ((longitude - 73) / 62) * 100))}%;top:${Math.max(14, Math.min(78, ((54 - latitude) / 36) * 100))}%;transform:translate(-50%,-100%);z-index:500`;
        this.element.appendChild(this.content);
        map.container.appendChild(this.element);
      }

      close(): void {
        this.element?.remove();
        this.element = null;
      }
    }

    class FakeMarkerCluster {
      markers: FakeMarker[] = [];

      constructor(private map: FakeMap, data: Array<{ lnglat: [number, number] }>, private options: { renderMarker: (context: { marker: FakeMarker; data: { lnglat: [number, number] } }) => void }) {
        this.setData(data);
      }

      /** 把聚合输入逐个绘制成可点击 Pin；聚合算法本身不属于离线验收范围。 */
      setData(data: Array<{ lnglat: [number, number] }>): void {
        this.map.remove(this.markers);
        this.markers = data.map((item) => {
          const marker = new FakeMarker({ position: item.lnglat });
          this.options.renderMarker({ marker, data: item });
          return marker;
        });
        this.map.add(this.markers);
      }
    }

    (window as Window & { AMapLoader?: unknown }).AMapLoader = {
      load: async () => ({
        getConfig: () => config,
        Bounds: FakeBounds,
        InfoWindow: FakeInfoWindow,
        Map: FakeMap,
        Marker: FakeMarker,
        Polyline: FakePolyline,
        Polygon: FakePolygon,
        Text: FakeText,
        Pixel: class { constructor(public x: number, public y: number) {} },
        DistrictSearch: FakeDistrictSearch,
        MarkerCluster: FakeMarkerCluster,
        Scale: class {},
        ToolBar: class {},
      }),
    };
  }, options);
}
