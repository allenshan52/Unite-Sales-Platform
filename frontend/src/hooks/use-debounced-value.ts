"use client";

/**
 * 提供跨管理页面复用的值防抖能力，避免每个筛选组件重复维护定时器状态。
 * 基于 React effect，在组件卸载或输入变化时可靠清理计时器。
 */
import { useEffect, useState } from "react";

/** 延迟发布快速变化的值，减少搜索筛选触发的重复请求。 */
export function useDebouncedValue<T>(value: T, delayMs = 250): T {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const timeoutId = window.setTimeout(() => setDebouncedValue(value), delayMs);
    return () => window.clearTimeout(timeoutId);
  }, [delayMs, value]);

  return debouncedValue;
}
