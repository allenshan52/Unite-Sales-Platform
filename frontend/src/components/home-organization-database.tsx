"use client";

/** 主页单位数据库：复用受保护的单位列表、筛选和点位 API，以橙蓝工作台展示安全的商务字段。 */

import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { useDebouncedValue } from "@/hooks/use-debounced-value";
import { apiFetch, queryString, type FilterOptions, type PublicOrganization, type PublicOrganizationPage } from "@/lib/api";

type DatabaseFilters = { search: string; type: string; customerStatus: string; reviewStatus: string; province: string; city: string; district: string };

const emptyFilters: DatabaseFilters = { search: "", type: "", customerStatus: "", reviewStatus: "", province: "", city: "", district: "" };
const pageSizeOptions = [8, 15, 25, 50, 100];

/** 将最近跟进时间按中国地区短日期展示，完整值保留在 time 元素中。 */
function formatFollowUpDate(value: string | null): string {
  return value ? new Intl.DateTimeFormat("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(value)) : "—";
}

/** 主页数据库面板：在固定高度的默认 8 条视图内展示单位，并允许更大页容量展开页面。 */
export function HomeOrganizationDatabase() {
  const [filters, setFilters] = useState<DatabaseFilters>(emptyFilters);
  const debouncedSearch = useDebouncedValue(filters.search.trim());
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(8);
  const [options, setOptions] = useState<FilterOptions | null>(null);
  const [page, setPage] = useState<PublicOrganizationPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const apiFilters = useMemo(() => ({ search: debouncedSearch || undefined, types: filters.type || undefined, customer_statuses: filters.customerStatus || undefined, review_statuses: filters.reviewStatus || undefined, province: filters.province || undefined, city: filters.city || undefined, district: filters.district || undefined }), [debouncedSearch, filters.city, filters.customerStatus, filters.district, filters.province, filters.reviewStatus, filters.type]);
  const filterOptionsQuery = useMemo(() => queryString({ province: filters.province || undefined, city: filters.city || undefined }), [filters.city, filters.province]);
  const cityOptions = options?.cities ?? [];
  const districtOptions = options?.districts ?? [];
  const totalPages = Math.max(1, Math.ceil((page?.total ?? 0) / pageSize));

  /** 单独加载公开列表；取消过期请求，避免旧筛选结果覆盖新筛选结果。 */
  useEffect(() => {
    const controller = new AbortController();
    const listQuery = queryString({ ...apiFilters, page: String(currentPage), page_size: String(pageSize) });
    void apiFetch<PublicOrganizationPage>(`/public/organizations${listQuery}`, { signal: controller.signal })
      .then((nextPage) => setPage(nextPage))
      .catch((requestError: unknown) => {
        if (!(requestError instanceof DOMException && requestError.name === "AbortError")) {
          setError(requestError instanceof Error ? requestError.message : "无法加载单位数据库");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [apiFilters, currentPage, pageSize]);

  /** 层级筛选选项拥有独立错误边界，菜单失败不会丢弃已经成功返回的列表。 */
  useEffect(() => {
    const controller = new AbortController();
    void apiFetch<FilterOptions>(`/public/organizations/filters${filterOptionsQuery}`, { signal: controller.signal })
      .then((nextOptions) => setOptions(nextOptions))
      .catch(() => {
        // 保留上一次有效选项；列表本身仍可继续浏览。
      });
    return () => controller.abort();
  }, [filterOptionsQuery]);

  /** 原子更新筛选并回到第一页，避免先请求旧页码再由 effect 二次请求。 */
  function updateFilters(changes: Partial<DatabaseFilters>) {
    setLoading(true);
    setError(null);
    setCurrentPage(1);
    setFilters((current) => ({ ...current, ...changes }));
  }

  /** 翻页和页容量变化在用户事件内标记加载状态，effect 只负责外部数据同步。 */
  function changePage(nextPage: number) {
    setLoading(true);
    setError(null);
    setCurrentPage(nextPage);
  }

  return (
    <section className={`unit-database ${pageSize > 8 ? "is-expanded" : ""}`} aria-label="单位数据库">
      <div className="database-toolbar">
        <div className="database-title"><h1>单位数据库</h1></div>
        <div className="database-filters">
          <label className="database-search"><Search size={17} /><input placeholder="搜索单位名称" value={filters.search} onChange={(event) => updateFilters({ search: event.target.value })} /></label>
          <select aria-label="单位类型" value={filters.type} onChange={(event) => updateFilters({ type: event.target.value })}><option value="">单位类型</option>{options?.organization_types.map((item) => <option key={item} value={item}>{item}</option>)}</select>
          <select aria-label="客户状态" value={filters.customerStatus} onChange={(event) => updateFilters({ customerStatus: event.target.value })}><option value="">客户状态</option>{options?.customer_statuses.map((item) => <option key={item} value={item}>{item}</option>)}</select>
          <select aria-label="审核状态" value={filters.reviewStatus} onChange={(event) => updateFilters({ reviewStatus: event.target.value })}><option value="">审核状态</option>{options?.review_statuses.map((item) => <option key={item} value={item}>{item}</option>)}</select>
          <select aria-label="省份" value={filters.province} onChange={(event) => updateFilters({ province: event.target.value, city: "", district: "" })}><option value="">全部省份</option>{options?.provinces.map((item) => <option key={item} value={item}>{item}</option>)}</select>
          <select aria-label="市" value={filters.city} disabled={!filters.province} onChange={(event) => updateFilters({ city: event.target.value, district: "" })}><option value="">全部市</option>{cityOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select>
          <select aria-label="区" value={filters.district} disabled={!filters.city} onChange={(event) => updateFilters({ district: event.target.value })}><option value="">全部区</option>{districtOptions.map((item) => <option key={item} value={item}>{item}</option>)}</select>
        </div>
      </div>

      <div className="database-list-card">
        {error ? <p className="database-error">{error}</p> : null}
        <div className="database-table" role="table" aria-label="单位数据库列表">
          <div className="database-row database-row-head" role="row"><span role="columnheader">单位</span><span role="columnheader">类型 / 行业</span><span role="columnheader">省市区</span><span role="columnheader">客户进展</span><span role="columnheader">最近跟进</span><span role="columnheader">商业关系</span><span role="columnheader">公开联系 / 证据</span></div>
          <div className="database-table-body">
            {loading ? <div className="database-empty">正在加载单位数据…</div> : null}
            {!loading && page?.items.map((organization: PublicOrganization) => {
              const primarySite = organization.sites.find((site) => site.is_primary) ?? organization.sites[0];
              const location = [primarySite?.province, primarySite?.city, primarySite?.district].filter(Boolean).join(" · ");

              return <div className="database-row" role="row" key={organization.id}>
                <span role="cell">
                  <strong>{organization.name}</strong>
                  {organization.is_sports_exception ? <small>体育例外</small> : null}
                  {organization.competitor_contracts.length > 0 ? <small className="competitor-linked-badge">同行已签约</small> : null}
                  {organization.competitor_contracts.length > 0 ? <em className="competitor-linked-detail" title={organization.competitor_contracts.map((link) => `${link.competitor_name} · ${link.customer_level} · ${Number(link.total_amount).toLocaleString("zh-CN")} 元 · 置信度 ${link.confidence}`).join("；")}>{organization.competitor_contracts.map((link) => `${link.competitor_name} · ${link.customer_level} · ${Number(link.total_amount).toLocaleString("zh-CN")} 元`).join("；")}</em> : null}
                </span>
                <span role="cell">{organization.organization_type}<em>{organization.industry || "未标注行业"}</em></span>
                <span role="cell">{location || "未补齐"}</span>
                <span role="cell"><b className={`database-status status-${organization.customer_status}`}>{organization.customer_status}</b><em>{organization.inclusion_reason || "等待补充推进说明"}</em></span>
                <span role="cell" className={organization.recent_follow_up_at || organization.recent_follow_up_content ? "" : "database-followup-empty"}><time dateTime={organization.recent_follow_up_at ?? undefined}>{formatFollowUpDate(organization.recent_follow_up_at)}</time><em>{organization.recent_follow_up_content || "暂无跟进内容"}</em></span>
                <span role="cell">{organization.cooperation_intent || organization.parent_group || "暂无合作意向"}<em>{organization.cooperation_level ? `${organization.cooperation_level}合作` : "未设置合作等级"}</em></span>
                <span role="cell">{organization.website ? <a href={organization.website} target="_blank" rel="noreferrer">官网与公开联系渠道</a> : "暂无公开联系渠道"}<em>{organization.evidence_count} 项公开证据</em></span>
              </div>;
            })}
            {!loading && page?.items.length === 0 ? <div className="database-empty">暂无匹配单位，请调整筛选条件。</div> : null}
          </div>
        </div>
        <nav className="database-pagination" aria-label="单位列表分页">
          <label>每页<select value={pageSize} onChange={(event) => { setLoading(true); setError(null); setCurrentPage(1); setPageSize(Number(event.target.value)); }}>{pageSizeOptions.map((size) => <option key={size} value={size}>{size} 条</option>)}</select></label>
          <span>第 {currentPage} / {totalPages} 页 · 共 {page?.total.toLocaleString("zh-CN") ?? "—"} 条</span>
          <div><button type="button" onClick={() => changePage(Math.max(1, currentPage - 1))} disabled={currentPage === 1}>上一页</button><button type="button" onClick={() => changePage(Math.min(totalPages, currentPage + 1))} disabled={currentPage === totalPages}>下一页</button></div>
        </nav>
      </div>
    </section>
  );
}
