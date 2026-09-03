"use client";

/** 管理端最新请求协调器：取消同类旧请求，防止迟到响应覆盖用户最后一次选择。 */

import { useCallback, useEffect, useRef } from "react";

/** 执行 latest-request-wins 请求，并在组件卸载时释放仍在进行的网络任务。 */
export function useLatestRequest() {
  const controllerRef = useRef<AbortController | null>(null);

  const cancel = useCallback(() => {
    controllerRef.current?.abort();
    controllerRef.current = null;
  }, []);

  useEffect(() => cancel, [cancel]);

  const run = useCallback(async <T>(request: (signal: AbortSignal) => Promise<T>): Promise<T | undefined> => {
    cancel();
    const controller = new AbortController();
    controllerRef.current = controller;
    try {
      const value = await request(controller.signal);
      return controller.signal.aborted ? undefined : value;
    } catch (error) {
      if (controller.signal.aborted) return undefined;
      throw error;
    } finally {
      if (controllerRef.current === controller) controllerRef.current = null;
    }
  }, [cancel]);

  return { cancel, run } as const;
}
