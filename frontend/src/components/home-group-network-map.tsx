"use client";

/** 首页客户关系网络：以高德 Marker/Polyline 展示集团树，并平滑聚焦全部单位点位。 */

import { useCallback, useEffect, useRef, useState, type CSSProperties } from "react";

import { apiFetch, type CustomerGroupDetail, type CustomerGroupHeadquarters, type CustomerGroupUnit } from "@/lib/api";
import { destroyAmapMap, loadAmapNamespace } from "@/lib/amap";
import { escapeHtml } from "@/lib/html";

interface AmapMarker {
  on(event: "click", handler: () => void): void;
}

interface AmapMap {
  add(overlays: unknown | unknown[]): void;
  addControl(control: unknown): void;
  destroy(): void;
  remove(overlays: unknown | unknown[]): void;
  setFitView(overlays?: unknown[], immediately?: boolean, avoid?: number[], maxZoom?: number): void;
  setZoomAndCenter(zoom: number, center: [number, number]): void;
  zoomIn(): void;
  zoomOut(): void;
}

interface GroupAmapNamespace {
  getConfig(): { appname?: string };
  Map: new (container: HTMLElement, options: Record<string, unknown>) => AmapMap;
  Marker: new (options: Record<string, unknown>) => AmapMarker;
  Polyline: new (options: Record<string, unknown>) => unknown;
  Scale: new () => unknown;
}

type Runtime = { AMap: GroupAmapNamespace; map: AmapMap; overlays: unknown[] };

const currencyFormatter = new Intl.NumberFormat("zh-CN", {
  style: "currency",
  currency: "CNY",
  maximumFractionDigits: 0,
});

/** 将数据库 Decimal 字符串按中国地区人民币格式展示。 */
function formatCurrency(value: string | null): string {
  return value === null ? "—" : currencyFormatter.format(Number(value));
}

/** 把商机阶段转换为短标签；成交状态始终单独呈现，不占用集团识别色。 */
function unitStatus(unit: CustomerGroupUnit): string {
  if (unit.is_won) return "已成交";
  return unit.opportunity_stage ?? "暂无商机";
}

/** 提供全组件一致的线性图标，不引入新的图标资源请求。 */
function PanelIcon({ name }: { name: "close" | "back" | "reset" | "building" }) {
  const paths = {
    close: <><path d="m5 5 14 14M19 5 5 19" /></>,
    back: <><path d="m14 6-6 6 6 6" /><path d="M8 12h11" /></>,
    reset: <><path d="M4 12a8 8 0 1 0 2.3-5.7L4 8" /><path d="M4 3v5h5" /></>,
    building: <><path d="M5 21V5l7-3 7 3v16" /><path d="M3 21h18M9 9h1m4 0h1m-6 4h1m4 0h1m-6 4h1m4 0h1" /></>,
  };
  return <svg aria-hidden="true" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

/** 以集团色纵向列出单位，完整呈现名称、层级和省市并与地图选择保持同步。 */
function GroupTree({ units, groupColor, selectedId, onSelect }: { units: CustomerGroupUnit[]; groupColor: string; selectedId: string | null; onSelect: (unit: CustomerGroupUnit) => void }) {
  return (
    <div className="group-tree" aria-label="集团层级树" style={{ "--group-color": groupColor } as CSSProperties}>
      {units.map((unit) => (
        <button
          key={unit.id}
          type="button"
          className={selectedId === unit.id ? "selected" : ""}
          onClick={() => onSelect(unit)}
        >
          <i />
          <span><b>{unit.name}</b><small>{unit.is_headquarters ? "总部" : `${unit.level} 级分支`} · {unit.province} · {unit.city}</small></span>
        </button>
      ))}
    </div>
  );
}

/** 集团详情面板在概览和单位详情间切换，并保留明确返回与关闭操作。 */
function GroupPanel({ detail, selectedUnit, onSelectUnit, onBack, onClose }: {
  detail: CustomerGroupDetail;
  selectedUnit: CustomerGroupUnit | null;
  onSelectUnit: (unit: CustomerGroupUnit) => void;
  onBack: () => void;
  onClose: () => void;
}) {
  if (selectedUnit) {
    return (
      <aside className="group-network-panel" aria-label={`${selectedUnit.name}单位详情`}>
        <header>
          <button className="group-panel-back" type="button" onClick={onBack}><PanelIcon name="back" />返回集团概览</button>
          <button className="group-panel-close" type="button" aria-label="关闭客户关系网络详情" onClick={onClose}><PanelIcon name="close" /></button>
        </header>
        <div className="group-panel-title">
          <h2>{selectedUnit.name}</h2>
          <p>{selectedUnit.is_headquarters ? "集团总部" : `${selectedUnit.level} 级分支`} · {selectedUnit.province} · {selectedUnit.city}</p>
        </div>
        <div className="group-status-row">
          <b className={selectedUnit.is_won ? "is-won" : ""}>{unitStatus(selectedUnit)}</b>
          {selectedUnit.opportunity_stage ? <b>{selectedUnit.opportunity_stage}</b> : null}
        </div>
        <dl className="group-unit-detail">
          <div><dt>详细地址</dt><dd>{selectedUnit.address}</dd></div>
          <div><dt>地理位置</dt><dd>{selectedUnit.longitude.toFixed(4)}, {selectedUnit.latitude.toFixed(4)}</dd></div>
          <div><dt>组织层级</dt><dd>{selectedUnit.is_headquarters ? "总部节点" : `${selectedUnit.level} 级分支`}</dd></div>
          <div><dt>实际成交金额</dt><dd>{formatCurrency(selectedUnit.actual_sales_amount)}</dd></div>
          <div><dt>预计商机金额</dt><dd>{formatCurrency(selectedUnit.estimated_opportunity_amount)}</dd></div>
        </dl>
      </aside>
    );
  }

  return (
    <aside className="group-network-panel" aria-label={`${detail.name}集团概览`}>
      <header className="group-panel-actions">
        <button className="group-panel-close" type="button" aria-label="关闭客户关系网络详情" onClick={onClose}><PanelIcon name="close" /></button>
      </header>
      <div className="group-panel-title">
        <h2>{detail.name}</h2>
        <p>共 {detail.summary.branch_count} 家分支，已成交 {detail.summary.won_branch_count} 家，活跃商机 {detail.summary.active_opportunity_count} 家</p>
      </div>
      <div className="group-summary-grid">
        <div><span>实际成交总额</span><strong>{formatCurrency(detail.summary.actual_sales_amount)}</strong></div>
        <div><span>覆盖省市</span><strong>{detail.summary.provinces.length} 省 · {detail.summary.cities.length} 市</strong></div>
      </div>
      <section className="group-coverage"><h3>覆盖区域</h3><p>{detail.summary.cities.join("、") || "仅总部所在城市"}</p></section>
      <section className="group-tree-section">
        <div className="group-tree-heading"><h3>层级关系</h3><span>点击单位查看详情</span></div>
        {detail.summary.branch_count === 0 ? <p className="group-empty-branches">该集团暂无分支，当前只显示总部。</p> : null}
        <GroupTree units={detail.units} groupColor={detail.color} selectedId={null} onSelect={onSelectUnit} />
      </section>
      <button className="group-reset-button" type="button" onClick={onClose}><PanelIcon name="reset" />返回全国集团</button>
    </aside>
  );
}

/** 首页关系地图负责锚点式总部 Pin、集团懒加载、关系线和单位详情的完整交互闭环。 */
export function HomeGroupNetworkMap() {
  const containerRef = useRef<HTMLDivElement>(null);
  const runtimeRef = useRef<Runtime | null>(null);
  const detailRequestRef = useRef(0);
  const [mapReady, setMapReady] = useState(false);
  const [groups, setGroups] = useState<CustomerGroupHeadquarters[]>([]);
  const [selectedGroupId, setSelectedGroupId] = useState("");
  const [selectedGroup, setSelectedGroup] = useState<CustomerGroupDetail | null>(null);
  const [selectedUnitId, setSelectedUnitId] = useState<string | null>(null);
  const [listStatus, setListStatus] = useState<"loading" | "ready" | "error">("loading");
  const [detailStatus, setDetailStatus] = useState<"idle" | "loading" | "error">("idle");
  const [message, setMessage] = useState<string | null>(null);
  const [listAttempt, setListAttempt] = useState(0);

  /** 清除展开态和关系覆盖物，恢复全国总部视图。 */
  const resetGroup = useCallback(() => {
    detailRequestRef.current += 1;
    setSelectedGroupId("");
    setSelectedGroup(null);
    setSelectedUnitId(null);
    setDetailStatus("idle");
    setMessage(null);
  }, []);

  /** 点击总部后按需读取单集团节点，避免首屏一次传输全国关系树。 */
  const openGroup = useCallback(async (groupId: string) => {
    const previousGroupId = selectedGroup?.id ?? "";
    const requestId = detailRequestRef.current + 1;
    detailRequestRef.current = requestId;
    setSelectedGroupId(groupId);
    setSelectedUnitId(null);
    setDetailStatus("loading");
    setMessage(null);
    try {
      const detail = await apiFetch<CustomerGroupDetail>(`/public/customer-groups/${groupId}`);
      if (detailRequestRef.current !== requestId) return;
      setSelectedGroup(detail);
      setDetailStatus("idle");
    } catch (error: unknown) {
      if (detailRequestRef.current !== requestId) return;
      setSelectedGroupId(previousGroupId);
      setDetailStatus("error");
      setMessage(error instanceof Error ? error.message : "集团详情加载失败");
    }
  }, [selectedGroup?.id]);

  useEffect(() => {
    const controller = new AbortController();
    apiFetch<CustomerGroupHeadquarters[]>("/public/customer-groups", { signal: controller.signal })
      .then((data) => { setGroups(data); setListStatus("ready"); })
      .catch((error: unknown) => {
        if (controller.signal.aborted) return;
        setListStatus("error");
        setMessage(error instanceof Error ? error.message : "集团总部加载失败");
      });
    return () => controller.abort();
  }, [listAttempt]);

  useEffect(() => {
    let disposed = false;
    if (!containerRef.current) return;
    loadAmapNamespace<GroupAmapNamespace>(["AMap.Scale"])
      .then((AMap) => {
        if (disposed || !containerRef.current) return;
        const map = new AMap.Map(containerRef.current, {
          viewMode: "2D", zoom: 4.35, center: [104.1, 35.6], mapStyle: "amap://styles/light", showLabel: true,
        });
        map.addControl(new AMap.Scale());
        runtimeRef.current = { AMap, map, overlays: [] };
        setMapReady(true);
      })
      .catch((error: unknown) => { if (!disposed) { setListStatus("error"); setMessage(error instanceof Error ? error.message : "地图加载失败"); } });
    return () => {
      disposed = true;
      destroyAmapMap(runtimeRef.current?.map ?? null);
      runtimeRef.current = null;
    };
  }, []);

  useEffect(() => {
    const runtime = runtimeRef.current;
    if (!runtime || !mapReady || listStatus !== "ready") return;
    if (runtime.overlays.length) runtime.map.remove(runtime.overlays);
    const overlays: unknown[] = [];
    if (!selectedGroup) {
      groups.forEach((group) => {
        const marker = new runtime.AMap.Marker({
          position: [group.headquarters.longitude, group.headquarters.latitude],
          anchor: "bottom-center",
          zIndex: 120,
          content: `<div class="group-map-marker is-headquarters" style="--group-color:${group.color}"><span><em>总</em></span><b>${escapeHtml(group.name)}</b></div>`,
        });
        marker.on("click", () => { void openGroup(group.id); });
        overlays.push(marker);
      });
      runtime.map.add(overlays);
      runtime.map.setZoomAndCenter(4.35, [104.1, 35.6]);
    } else {
      const unitsById = new Map(selectedGroup.units.map((unit) => [unit.id, unit]));
      const unitMarkers: unknown[] = [];
      selectedGroup.units.forEach((unit) => {
        if (!unit.parent_id) return;
        const parent = unitsById.get(unit.parent_id);
        if (!parent) return;
        overlays.push(new runtime.AMap.Polyline({
          path: [[parent.longitude, parent.latitude], [unit.longitude, unit.latitude]],
          strokeColor: selectedGroup.color, strokeOpacity: 0.72, strokeWeight: unit.level === 1 ? 3 : 2,
          strokeStyle: unit.level > 1 ? "dashed" : "solid", zIndex: 60,
        }));
      });
      selectedGroup.units.forEach((unit) => {
        const marker = new runtime.AMap.Marker({
          position: [unit.longitude, unit.latitude], anchor: "bottom-center", zIndex: unit.is_headquarters ? 130 : 110,
          content: `<div class="group-map-marker ${unit.is_headquarters ? "is-headquarters" : "is-branch"}" style="--group-color:${selectedGroup.color}"><span><em>${unit.is_headquarters ? "总" : `L${unit.level}`}</em></span><b>${escapeHtml(unit.name)}</b><small>${escapeHtml(unitStatus(unit))}</small></div>`,
        });
        marker.on("click", () => setSelectedUnitId(unit.id));
        overlays.push(marker);
        unitMarkers.push(marker);
      });
      runtime.map.add(overlays);
      // 四向留出 Pin/标签安全区；桌面端左避标题卡、右避详情面板，确保边缘单位不被浮层遮挡。
      const avoid = window.innerWidth <= 900 ? [96, 350, 72, 72] : [150, 150, 280, 450];
      runtime.map.setFitView(unitMarkers, false, avoid, 10);
    }
    runtime.overlays = overlays;
  }, [groups, listStatus, mapReady, openGroup, selectedGroup]);

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => { if (event.key === "Escape" && selectedGroup) resetGroup(); };
    window.addEventListener("keydown", handleEscape);
    return () => window.removeEventListener("keydown", handleEscape);
  }, [resetGroup, selectedGroup]);

  const selectedUnit = selectedGroup?.units.find((unit) => unit.id === selectedUnitId) ?? null;

  return (
    <div className="home-group-network-map">
      <div ref={containerRef} className="group-network-canvas" aria-label="全国客户集团关系地图" />
      <section className="group-map-title-card" aria-labelledby="group-map-title">
        <div className="group-map-heading">
          <span>2026 / 客户集团</span>
          <h1 id="group-map-title">客户关系网络</h1>
        </div>
        {listStatus === "ready" && groups.length > 0 ? (
          <label className="group-map-selector">
            <span><PanelIcon name="building" />选择客户集团</span>
            <select
              aria-label="选择客户集团"
              value={selectedGroupId}
              onChange={(event) => {
                const groupId = event.target.value;
                if (!groupId) resetGroup();
                else void openGroup(groupId);
              }}
            >
              <option value="">全部集团总部（{groups.length}）</option>
              {groups.map((group) => <option key={group.id} value={group.id}>{group.name}</option>)}
            </select>
          </label>
        ) : null}
      </section>
      {mapReady ? (
        <div className={`group-map-zoom ${selectedGroup ? "has-panel" : ""}`} role="group" aria-label="地图缩放">
          <button type="button" aria-label="放大地图" onClick={() => runtimeRef.current?.map.zoomIn()}>＋</button>
          <button type="button" aria-label="缩小地图" onClick={() => runtimeRef.current?.map.zoomOut()}>−</button>
        </div>
      ) : null}
      {detailStatus === "loading" ? <div className="group-map-loading" role="status"><i />正在展开集团关系…</div> : null}
      {detailStatus === "error" ? (
        <div className="group-map-loading is-error" role="alert"><b>{message}</b><button type="button" onClick={() => setDetailStatus("idle")}>关闭</button></div>
      ) : null}
      {listStatus !== "ready" || groups.length === 0 ? (
        <div className="group-map-state" aria-live="polite">
          <PanelIcon name="building" />
          <strong>{listStatus === "loading" ? "正在读取集团总部" : listStatus === "error" ? "客户关系网络暂不可用" : "暂无客户集团数据"}</strong>
          <span>{listStatus === "loading" ? "地图和数据库正在建立连接" : message ?? "请先在数据库中维护集团和总部"}</span>
          {listStatus === "error" ? <button type="button" onClick={() => { setListStatus("loading"); setMessage(null); setListAttempt((value) => value + 1); }}>重新加载</button> : null}
        </div>
      ) : null}
      {selectedGroup ? (
        <GroupPanel
          detail={selectedGroup}
          selectedUnit={selectedUnit}
          onSelectUnit={(unit) => setSelectedUnitId(unit.id)}
          onBack={() => setSelectedUnitId(null)}
          onClose={resetGroup}
        />
      ) : null}
    </div>
  );
}
