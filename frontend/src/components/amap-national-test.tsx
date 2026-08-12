"use client";

/**
 * 高德 JS API 集成测试组件：加载全国省级地图、显示加载状态，并允许网络失败后重试。
 * 使用 React 生命周期及高德 AMap Loader；密钥仅由环境变量和本地代理提供。
 */
import { useEffect, useRef, useState } from "react";

const provinceLabels = [
  [116.4, 39.9, "北京"], [117.2, 39.1, "天津"], [114.5, 38.0, "河北"],
  [112.5, 37.8, "山西"], [111.8, 40.8, "内蒙古"], [123.4, 41.8, "辽宁"],
  [125.3, 43.9, "吉林"], [126.6, 45.8, "黑龙江"], [121.5, 31.2, "上海"],
  [118.8, 32.1, "江苏"], [120.2, 30.3, "浙江"], [117.3, 31.9, "安徽"],
  [119.3, 26.1, "福建"], [115.9, 28.7, "江西"], [117.0, 36.7, "山东"],
  [113.7, 34.8, "河南"], [114.3, 30.6, "湖北"], [112.9, 28.2, "湖南"],
  [113.3, 23.1, "广东"], [108.3, 22.8, "广西"], [110.3, 20.0, "海南"],
  [106.5, 29.6, "重庆"], [104.1, 30.7, "四川"], [106.7, 26.6, "贵州"],
  [102.7, 25.0, "云南"], [91.1, 29.6, "西藏"], [108.9, 34.3, "陕西"],
  [103.8, 36.1, "甘肃"], [101.8, 36.6, "青海"], [106.3, 38.5, "宁夏"],
  [87.6, 43.8, "新疆"], [121.0, 24.7, "台湾"], [114.2, 22.3, "香港"],
  [113.6, 22.2, "澳门"],
] as const;

type MapInstance = {
  add: (layer: unknown) => void;
  addControl: (control: unknown) => void;
  destroy: () => void;
  on: (event: string, handler: () => void) => void;
  setLimitBounds: (bounds: unknown) => void;
  setMask: (mask: unknown) => void;
};

type LabelsLayer = { add: (labels: unknown[]) => void };
type DistrictSearchResult = { districtList?: Array<{ boundaries?: unknown[] }> };
type TestAmapNamespace = {
  getConfig: () => { appname?: string };
  Map: new (container: HTMLElement, options: Record<string, unknown>) => MapInstance;
  DistrictLayer: { Province: new (options: Record<string, unknown>) => unknown };
  Scale: new (options?: Record<string, unknown>) => unknown;
  ToolBar: new (options: Record<string, unknown>) => unknown;
  LabelsLayer: new (options: Record<string, unknown>) => LabelsLayer;
  LabelMarker: new (options: Record<string, unknown>) => unknown;
  DistrictSearch: new (options: Record<string, unknown>) => { search: (query: string, callback: (status: string, result: unknown) => void) => void };
  Bounds: new (southWest: [number, number], northEast: [number, number]) => unknown;
};

/** 复用或动态注入高德 Loader 脚本，避免页面重复加载同一 SDK。 */
function loadAmapLoader() {
  if (window.AMapLoader) return Promise.resolve(window.AMapLoader);

  return new Promise<NonNullable<Window["AMapLoader"]>>((resolve, reject) => {
    const existing = document.querySelector<HTMLScriptElement>(
      'script[data-amap-loader="true"]',
    );
    if (existing) {
      if (window.AMapLoader) {
        resolve(window.AMapLoader);
        return;
      }
      existing.remove();
    }

    const script = document.createElement("script");
    script.src = "https://webapi.amap.com/loader.js";
    script.async = true;
    script.dataset.amapLoader = "true";
    script.onload = () => resolve(window.AMapLoader!);
    script.onerror = () => reject(new Error("AMap loader failed."));
    document.head.appendChild(script);
  });
}

/** 为外部地图加载增加超时保护，确保界面能从永久加载状态恢复为可重试状态。 */
function withTimeout<T>(promise: Promise<T>, timeoutMs: number) {
  return new Promise<T>((resolve, reject) => {
    const timeout = window.setTimeout(
      () => reject(new Error("AMap loader timed out.")),
      timeoutMs,
    );
    promise.then(
      (value) => {
        window.clearTimeout(timeout);
        resolve(value);
      },
      (error) => {
        window.clearTimeout(timeout);
        reject(error);
      },
    );
  });
}

/** 初始化、销毁并呈现高德全国地图的客户端 React 组件。 */
export function AmapNationalTest() {
  const container = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<"loading" | "ready" | "error">(
    process.env.NEXT_PUBLIC_AMAP_JSAPI_KEY ? "loading" : "error",
  );
  const [attempt, setAttempt] = useState(0);

  // 挂载时配置安全代理并创建地图；卸载时销毁实例，防止 WebGL 与事件监听泄漏。
  useEffect(() => {
    const key = process.env.NEXT_PUBLIC_AMAP_JSAPI_KEY;
    let disposed = false;
    let map: MapInstance | null = null;

    if (!key) {
      return;
    }

    window._AMapSecurityConfig = {
      serviceHost: `${window.location.origin}/_AMapService`,
    };

    void withTimeout(
      loadAmapLoader()
      .then((loader) =>
        loader.load({
          key,
          version: "2.0",
          plugins: ["AMap.Scale", "AMap.ToolBar", "AMap.DistrictSearch"],
        }),
      ),
      12_000,
    )
      .then((runtime) => {
        if (disposed || !container.current) return;
        const AMap = runtime as unknown as TestAmapNamespace;

        AMap.getConfig().appname = "amap-jsapi-skill";
        const instance: MapInstance = new AMap.Map(container.current, {
          viewMode: "2D",
          zoom: 3.95,
          zooms: [3, 8],
          center: [104.5, 35.5],
          mapStyle: "amap://styles/whitesmoke",
          showLabel: false,
          features: ["bg", "road", "building", "point"],
        });

        const provinces = new AMap.DistrictLayer.Province({
          zIndex: 12,
          adcode: ["100000"],
          depth: 1,
          styles: {
            fill: "rgba(79, 131, 237, 0.18)",
            "province-stroke": "rgba(35, 68, 118, 0.58)",
            "city-stroke": "rgba(35, 68, 118, 0.16)",
          },
        });
        map = instance;
        instance.add(provinces);
        instance.addControl(new AMap.Scale({ position: "LB" }));
        instance.addControl(new AMap.ToolBar({ position: { top: "24px", right: "20px" } }));

        const compact = window.innerWidth <= 720;
        const labels = new AMap.LabelsLayer({
          zIndex: 20,
          collision: compact,
          allowCollision: false,
        });
        labels.add(
          provinceLabels.map(([longitude, latitude, name]) =>
            new AMap.LabelMarker({
              position: [longitude, latitude],
              text: {
                content: name,
                direction: "center",
                style: {
                  color: "#243a5a",
                  fontSize: compact ? 9 : 11,
                  fontWeight: 700,
                },
              },
            }),
          ),
        );
        instance.add(labels);

        const districtSearch = new AMap.DistrictSearch({
          level: "country",
          subdistrict: 0,
          extensions: "all",
        });
        districtSearch.search("中国", (status: string, result: unknown) => {
          const boundaries = (result as DistrictSearchResult)?.districtList?.[0]?.boundaries;
          if (status !== "complete" || !boundaries?.length || disposed) return;

          instance.setMask(boundaries);
          instance.setLimitBounds(
            new AMap.Bounds([73.5, 17.4], [135.1, 53.8]),
          );
        });

        instance.on("complete", () => {
          if (!disposed) setStatus("ready");
        });
      })
      .catch(() => {
        if (!disposed) setStatus("error");
      });

    return () => {
      disposed = true;
      map?.destroy();
    };
  }, [attempt]);

  return (
    <div className="amap-test-card panel-enter">
      <div className="amap-test-heading">
        <div>
          <span>高德 JS API / 实验视图</span>
          <h1>全国省级地图</h1>
          <p>省界与名称由地图服务提供，仅用于集成验证。</p>
        </div>
        <div className={`amap-test-status ${status}`} role="status">
          <i />
          {status === "loading" ? "正在加载地图" : status === "ready" ? "地图已就绪" : "地图暂不可用"}
        </div>
      </div>
      <div className="amap-test-stage">
        <div ref={container} className="amap-test-map" aria-label="高德全国省级地图" />
        {status !== "ready" && (
          <div className="amap-test-overlay" aria-live="polite">
            <strong>{status === "loading" ? "正在连接高德地图" : "暂时无法加载地图"}</strong>
            <span>{status === "loading" ? "省级边界与标签准备中" : "请检查网络或稍后重试"}</span>
            {status === "error" && (
              <button
                type="button"
                onClick={() => {
                  setStatus("loading");
                  setAttempt((current) => current + 1);
                }}
              >
                重新加载
              </button>
            )}
          </div>
        )}
      </div>
      <div className="amap-test-footer">
        <span><i /> 省级行政区</span>
        <span>拖拽平移 · 滚轮缩放</span>
      </div>
    </div>
  );
}
