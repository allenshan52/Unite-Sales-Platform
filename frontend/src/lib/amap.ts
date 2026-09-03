/** 高德 JSAPI 公共加载器：统一安全代理、超时重试、调用标识与地图销毁。 */

interface AMapLoaderRuntime {
  load(options: Record<string, unknown>): Promise<unknown>;
}

export interface DestroyableAmapMap {
  destroy(): void;
}

export interface AmapNamespaceBase {
  getConfig(): { appname?: string };
}

declare global {
  interface Window {
    AMapLoader?: AMapLoaderRuntime;
    _AMapSecurityConfig?: { serviceHost: string };
  }
}

let loaderPromise: Promise<AMapLoaderRuntime> | null = null;

/** 动态加载一次官方 Loader，并兼容 React 严格模式下的重复挂载。 */
function loadAmapLoader(): Promise<AMapLoaderRuntime> {
  if (window.AMapLoader) return Promise.resolve(window.AMapLoader);
  if (loaderPromise) return loaderPromise;
  loaderPromise = new Promise<AMapLoaderRuntime>((resolve, reject) => {
    let script = document.querySelector<HTMLScriptElement>('script[data-amap-loader="true"]');
    if (script?.dataset.failed === "true") {
      script.remove();
      script = null;
    }
    if (!script) {
      script = document.createElement("script");
      script.src = "https://webapi.amap.com/loader.js";
      script.async = true;
      script.dataset.amapLoader = "true";
      document.head.appendChild(script);
    }

    const activeScript = script;
    const timeoutId = window.setTimeout(() => {
      activeScript.dataset.failed = "true";
      activeScript.remove();
      reject(new Error("高德地图加载器加载超时"));
    }, 20_000);
    const resolveLoader = () => {
      window.clearTimeout(timeoutId);
      if (!window.AMapLoader) {
        activeScript.dataset.failed = "true";
        activeScript.remove();
        reject(new Error("高德地图加载器不可用"));
        return;
      }
      activeScript.dataset.loaded = "true";
      resolve(window.AMapLoader);
    };
    const rejectLoader = () => {
      window.clearTimeout(timeoutId);
      activeScript.dataset.failed = "true";
      activeScript.remove();
      reject(new Error("高德地图加载器加载失败"));
    };
    activeScript.addEventListener("load", resolveLoader, { once: true });
    activeScript.addEventListener("error", rejectLoader, { once: true });
  }).catch((error: unknown) => {
    loaderPromise = null;
    throw error;
  });
  return loaderPromise;
}

/** 为一次 SDK 请求设置终止时间，避免外部脚本异常时地图永久停留在加载态。 */
function loadAttempt(loader: AMapLoaderRuntime, options: Record<string, unknown>): Promise<unknown> {
  return new Promise((resolve, reject) => {
    const timeoutId = window.setTimeout(() => reject(new Error("高德地图加载超时")), 20_000);
    loader.load(options).then(resolve, reject).finally(() => window.clearTimeout(timeoutId));
  });
}

/** 通过同源安全代理加载 AMap；失败只重试一次，并在创建地图前写入技能调用标识。 */
export async function loadAmapNamespace<T extends AmapNamespaceBase>(plugins: string[]): Promise<T> {
  const key = process.env.NEXT_PUBLIC_AMAP_JSAPI_KEY;
  if (!key) throw new Error("未配置高德 Web JS API Key，地图暂不可用。");
  window._AMapSecurityConfig = { serviceHost: `${window.location.origin}/_AMapService` };
  const loader = await loadAmapLoader();
  let lastError: unknown;
  for (let attempt = 0; attempt < 2; attempt += 1) {
    try {
      const AMap = await loadAttempt(loader, { key, version: "2.0", plugins }) as T;
      AMap.getConfig().appname = "amap-jsapi-skill";
      return AMap;
    } catch (error: unknown) {
      lastError = error;
    }
  }
  throw lastError instanceof Error ? lastError : new Error("高德地图加载失败");
}

/** 安全销毁可能尚未完成初始化的地图实例，供所有地图组件统一清理资源。 */
export function destroyAmapMap(map: DestroyableAmapMap | null): void {
  map?.destroy();
}
