"use client";

/** 高德地点搜索控件：把 POI 选择统一转换为后台表单按需保存的名称、行政区、地址和坐标。 */

import { useEffect, useId, useRef, useState } from "react";
import { CheckCircle2, CircleAlert, LoaderCircle, MapPin, Search } from "lucide-react";

import { apiFetch } from "@/lib/api";

export interface AmapLocationSelection {
  name: string;
  address: string;
  province: string;
  city: string;
  district: string;
  amapAdcode: string;
  longitude: string;
  latitude: string;
}

interface AmapLocationValue {
  name?: string;
  address?: string;
  longitude?: string | number;
  latitude?: string | number;
}

interface AmapLocationSearchProps {
  label?: string;
  description?: string;
  queryHint?: string;
  value?: AmapLocationValue;
  required?: boolean;
  disabled?: boolean;
  onSelect: (location: AmapLocationSelection) => void;
}

/** 提供明确搜索、候选选择、空结果和故障反馈，不在输入时持续调用外部服务。 */
export function AmapLocationSearch({
  label = "高德地点搜索",
  description = "选择结果后自动填写地址、行政区和经纬度",
  queryHint = "",
  value,
  required = false,
  disabled = false,
  onSelect,
}: AmapLocationSearchProps) {
  const resultsId = useId();
  const requestIdRef = useRef(0);
  const mountedRef = useRef(true);
  const [query, setQuery] = useState(value?.name ?? "");
  const [results, setResults] = useState<AmapLocationSelection[]>([]);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      requestIdRef.current += 1;
    };
  }, []);

  /** 按显式关键词调用一次 PlaceSearch，过期回调不会覆盖较新的结果。 */
  async function searchLocation(): Promise<void> {
    const keyword = query.trim() || queryHint.trim();
    if (keyword.length < 2) {
      setMessage("请输入至少 2 个字的单位名称或详细地址");
      setResults([]);
      return;
    }
    const requestId = requestIdRef.current + 1;
    requestIdRef.current = requestId;
    setLoading(true);
    setMessage(null);
    setResults([]);
    try {
      const payload = await apiFetch<Array<{
        name: string; address: string; province: string; city: string; district: string;
        amap_adcode: string; longitude: string; latitude: string;
      }>>(`/admin-location-search?keyword=${encodeURIComponent(keyword)}`);
      if (!mountedRef.current || requestId !== requestIdRef.current) return;
      const locations = payload.map((item) => ({ ...item, amapAdcode: item.amap_adcode }));
      setResults(locations);
      setMessage(locations.length ? null : "没有找到匹配地点，请补充城市或详细地址");
      setLoading(false);
    } catch (error) {
      if (!mountedRef.current || requestId !== requestIdRef.current) return;
      setMessage(error instanceof Error ? error.message : "高德地点搜索失败，请重试");
      setLoading(false);
    }
  }

  /** 选择候选后立即回填父表单，并收起结果避免误选第二次。 */
  function selectLocation(location: AmapLocationSelection): void {
    onSelect(location);
    setQuery(location.name);
    setResults([]);
    setMessage(null);
  }

  const hasCoordinates = value?.longitude !== "" && value?.longitude !== undefined
    && value?.latitude !== "" && value?.latitude !== undefined;
  const selectedName = value?.name?.trim();

  return (
    <div className="amap-location-search field-wide">
      <div className="amap-location-search-heading">
        <span><MapPin size={14} />{label}{required ? <b aria-hidden="true">*</b> : null}</span>
        <small>{description}</small>
      </div>
      <div className="amap-location-search-row">
        <input
          aria-label={label}
          role="combobox"
          aria-autocomplete="list"
          aria-controls={resultsId}
          aria-expanded={results.length > 0}
          aria-required={required}
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key !== "Enter") return;
            event.preventDefault();
            void searchLocation();
          }}
          placeholder={queryHint ? `默认搜索：${queryHint}` : "输入单位名称或详细地址"}
          disabled={disabled || loading}
        />
        <button type="button" onClick={() => void searchLocation()} disabled={disabled || loading || (!query.trim() && !queryHint.trim())}>
          {loading ? <LoaderCircle className="amap-location-spinner" size={15} /> : <Search size={15} />}
          {loading ? "正在搜索" : "搜索位置"}
        </button>
      </div>
      {selectedName ? <p className="amap-location-current"><CheckCircle2 size={13} />已选择：{selectedName}</p> : hasCoordinates ? <p className="amap-location-current"><CheckCircle2 size={13} />已定位：{value?.address || "地址待确认"} · {value?.longitude}, {value?.latitude}</p> : null}
      {message ? <p className="amap-location-message" role="alert"><CircleAlert size={13} />{message}</p> : null}
      <div className="amap-location-results" id={resultsId} hidden={results.length === 0}>
        {results.map((location) => (
          <button type="button" key={`${location.longitude}-${location.latitude}-${location.name}`} onClick={() => selectLocation(location)}>
            <MapPin size={15} />
            <span><strong>{location.name}</strong><small>{location.address || [location.province, location.city, location.district].filter(Boolean).join(" · ")}</small></span>
          </button>
        ))}
      </div>
    </div>
  );
}
