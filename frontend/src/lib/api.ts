/** 单位 API 客户端：区分公开目录 DTO 与管理员详情，并统一处理同源请求。 */

export type OrganizationType = "高校" | "研究院" | "疾控" | "食药" | "环保" | "公安";
export type CustomerStatus = "潜在客户" | "商机客户" | "已成交客户";
export type ReviewStatus = "待核验" | "已核验" | "不纳入";
export type GeocodeStatus = "待编码" | "已定位" | "低置信度" | "待补地址";
export type CooperationLevel = "一级" | "二级" | "三级";
export type OpportunityStage = "已识别" | "资格确认" | "方案/报价" | "商务谈判" | "已关闭失单";
export type EvidenceKind = "官方名录" | "院系/专业目录" | "研究方向/实验室" | "体育例外依据" | "官方地址" | "其他";

export interface OrganizationSite {
  id: string;
  site_name: string | null;
  raw_address: string | null;
  address: string | null;
  province: string | null;
  city: string | null;
  district: string | null;
  amap_adcode: string | null;
  geocode_status: GeocodeStatus;
  geocode_confidence: number | null;
  longitude: number | null;
  latitude: number | null;
  is_primary: boolean;
}

export interface OrganizationEvidence {
  id: string;
  evidence_kind: string;
  title: string;
  source_url: string;
  retrieved_at: string;
  excerpt: string | null;
}

export interface OrganizationContact {
  id: string;
  name: string;
  department: string | null;
  title: string | null;
  mobile: string | null;
  email: string | null;
  is_primary: boolean;
  is_active: boolean;
  notes: string | null;
}

export interface OrganizationOpportunity {
  id: string;
  title: string;
  stage: OpportunityStage;
  estimated_amount: string | null;
  ai_summary: string | null;
  next_action: string | null;
  next_action_at: string | null;
}

export interface OrganizationSalesProject {
  id: string;
  opportunity_id: string | null;
  name: string;
  contract_amount: string;
  signed_at: string | null;
  project_detail: string | null;
}

export interface Organization {
  id: string;
  name: string;
  organization_type: OrganizationType;
  industry: string | null;
  customer_status: CustomerStatus;
  review_status: ReviewStatus;
  inclusion_reason: string | null;
  is_sports_exception: boolean;
  parent_group: string | null;
  website: string | null;
  unified_social_credit_code: string | null;
  recent_follow_up_at: string | null;
  recent_follow_up_content: string | null;
  follow_up_owner: string | null;
  cooperation_intent: string | null;
  cooperation_level: CooperationLevel | null;
  notes: string | null;
  sites: OrganizationSite[];
  evidences: OrganizationEvidence[];
  contacts: OrganizationContact[];
  sales_projects: OrganizationSalesProject[];
  opportunities: OrganizationOpportunity[];
  created_at: string;
  updated_at: string;
}

export interface OrganizationSiteUpdateInput {
  site_name: string | null;
  raw_address: string | null;
  address: string | null;
  province: string | null;
  city: string | null;
  district: string | null;
  amap_adcode: string | null;
  geocode_status: GeocodeStatus;
  geocode_confidence: number | null;
  longitude: number | null;
  latitude: number | null;
}

export interface OrganizationUpdateInput {
  name: string;
  organization_type: OrganizationType;
  industry: string | null;
  customer_status: CustomerStatus;
  review_status: ReviewStatus;
  inclusion_reason: string | null;
  is_sports_exception: boolean;
  parent_group: string | null;
  website: string | null;
  unified_social_credit_code: string | null;
  recent_follow_up_at: string | null;
  recent_follow_up_content: string | null;
  follow_up_owner: string | null;
  cooperation_intent: string | null;
  cooperation_level: CooperationLevel | null;
  notes: string | null;
  contacts: Array<Omit<OrganizationContact, "id"> & { id: string | null }>;
  sales_projects: Array<Omit<OrganizationSalesProject, "id" | "contract_amount"> & { id: string | null; contract_amount: number }>;
  opportunities: Array<Omit<OrganizationOpportunity, "id" | "estimated_amount"> & { id: string | null; estimated_amount: number | null }>;
  primary_site: OrganizationSiteUpdateInput;
}

export interface OrganizationEvidenceCreateInput {
  evidence_kind: EvidenceKind;
  title: string;
  source_url: string;
  published_at: string | null;
  excerpt: string | null;
}

/** 管理员新增单位时一次提交主档、主地点及全部可选关联记录。 */
export interface OrganizationCreateInput extends OrganizationUpdateInput {
  evidences: OrganizationEvidenceCreateInput[];
}

export interface OrganizationPage {
  items: Organization[];
  total: number;
  page: number;
  page_size: number;
}

export interface PublicOrganizationSite {
  province: string | null;
  city: string | null;
  district: string | null;
  is_primary: boolean;
}

export interface PublicOrganization {
  id: string;
  name: string;
  organization_type: OrganizationType;
  industry: string | null;
  customer_status: CustomerStatus;
  review_status: ReviewStatus;
  inclusion_reason: string | null;
  is_sports_exception: boolean;
  parent_group: string | null;
  website: string | null;
  recent_follow_up_at: string | null;
  recent_follow_up_content: string | null;
  cooperation_intent: string | null;
  cooperation_level: CooperationLevel | null;
  evidence_count: number;
  sites: PublicOrganizationSite[];
}

export interface PublicOrganizationPage {
  items: PublicOrganization[];
  total: number;
  page: number;
  page_size: number;
}

export interface ProvinceOrganizationSummary {
  province: string;
  total: number;
  organization_types: Record<string, number>;
  customer_statuses: Record<string, number>;
}

export interface SalesOfficeLocation {
  id: string;
  name: string;
  city: string;
  address: string | null;
  longitude: number;
  latitude: number;
  coverage_radius_km: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export type ChannelPartnerType = "经销商" | "代理商" | "合作伙伴";

export interface ChannelPartnerMapPoint {
  id: string;
  name: string;
  partner_type: ChannelPartnerType;
  address: string;
  map_longitude: number;
  map_latitude: number;
  coverage_radius_km: number;
  cooperation_level: CooperationLevel;
}

export interface MapPoint {
  id: string;
  name: string;
  organization_type: OrganizationType;
  customer_status: CustomerStatus;
  review_status: ReviewStatus;
  longitude: number;
  latitude: number;
  province: string | null;
  city: string | null;
  district: string | null;
}

export interface FilterOptions {
  organization_types: OrganizationType[];
  customer_statuses: CustomerStatus[];
  review_statuses: ReviewStatus[];
  provinces: string[];
  cities: string[];
  districts: string[];
}

/** 把 FastAPI 的字符串或 Pydantic 422 错误数组整理为可读消息，避免页面出现 [object Object]。 */
function apiErrorMessage(detail: unknown, fallback: string): string {
  if (typeof detail === "string" && detail.trim()) return detail;
  if (Array.isArray(detail)) {
    const messages = detail.flatMap((item) => {
      if (!item || typeof item !== "object") return [];
      const message = "msg" in item && typeof item.msg === "string" ? item.msg : null;
      const location = "loc" in item && Array.isArray(item.loc) ? item.loc.filter((part: unknown) => part !== "body").join(".") : "";
      return message ? [`${location ? `${location}：` : ""}${message}`] : [];
    });
    if (messages.length > 0) return messages.join("；");
  }
  return fallback;
}

/** 执行同源 API 请求，并统一保留会话、请求头、取消信号与错误呈现。 */
export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    credentials: "include",
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(apiErrorMessage(body?.detail, "请求失败，请稍后重试"));
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

/** 下载受管理员会话保护的文件响应，并交给浏览器保存为本地文件。 */
export async function apiDownload(path: string, filename: string): Promise<void> {
  const response = await fetch(`/api/v1${path}`, { credentials: "include" });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(apiErrorMessage(body?.detail, "导出失败，请稍后重试"));
  }
  const objectUrl = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = filename;
  link.click();
  // 延后释放，避免部分浏览器尚未开始保存文件就失去 Blob 引用。
  window.setTimeout(() => URL.revokeObjectURL(objectUrl), 0);
}

/** 以 URLSearchParams 传递筛选条件，避免组件自行拼接或遗漏编码。 */
export function queryString(filters: Record<string, string | boolean | string[] | undefined>): string {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([key, value]) => {
    if (Array.isArray(value)) value.forEach((item) => params.append(key, item));
    else if (value !== undefined && value !== "" && value !== false) params.set(key, String(value));
  });
  const result = params.toString();
  return result ? `?${result}` : "";
}
