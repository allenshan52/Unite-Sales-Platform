/** 单位 API 客户端：区分公开目录 DTO 与管理员详情，并统一处理同源请求。 */

export type OrganizationType = "高校" | "研究院" | "疾控" | "食药" | "环保" | "公安" | "企业";
export type CustomerStatus = "潜在客户" | "商机客户" | "已成交客户";
export type ReviewStatus = "待核验" | "已核验" | "不纳入";
export type GeocodeStatus = "待编码" | "已定位" | "低置信度" | "待补地址";
export type CooperationLevel = "一级" | "二级" | "三级";
export type OpportunityStage = "已识别" | "资格确认" | "方案/报价" | "商务谈判" | "已关闭失单";
export type EvidenceKind = "官方名录" | "院系/专业目录" | "研究方向/实验室" | "体育例外依据" | "官方地址" | "其他";
export type UserRole = "普通用户" | "超级管理员";
export type SalesCoverageLevel = "市" | "省" | "大区" | "全国";
export type InsightsPeriod = "year" | "q1" | "q2" | "q3" | "q4";
export type InsightsMetric = "sales" | "projects" | "pipeline";
export type InsightsScopeMode = "assigned" | "region";

export interface InsightsRegion {
  id: string;
  name: string;
  province: string;
  city: string | null;
  longitude: number | null;
  latitude: number | null;
  sales_amount: string;
  project_count: number;
  pipeline_amount: string;
  pipeline_count: number;
  average_deal_amount: string;
  metric_value: string;
  contribution_percent: string;
  rank: number;
  yoy_percent: string | null;
  qoq_percent: string | null;
}

export interface InsightsMacroRegion {
  id: string;
  name: string;
  provinces: string[];
  sales_amount: string;
  project_count: number;
  pipeline_amount: string;
  pipeline_count: number;
  metric_value: string;
  contribution_percent: string;
}

export interface InsightsOverview {
  year: number;
  period: InsightsPeriod;
  metric: InsightsMetric;
  available_years: number[];
  scope: {
    level: "national" | "province" | "city";
    name: string;
    province: string | null;
    city: string | null;
    mode: InsightsScopeMode;
    visible_provinces: string[];
    visible_regions: string[];
  };
  aggregated_at: string;
  kpis: {
    sales_amount: string;
    sales_yoy_percent: string | null;
    sales_qoq_percent: string | null;
    project_count: number;
    projects_yoy_percent: string | null;
    projects_qoq_percent: string | null;
    average_deal_amount: string;
    pipeline_amount: string;
    pipeline_count: number;
    active_region_count: number;
  };
  regions: InsightsRegion[];
  macro_regions: InsightsMacroRegion[];
  trend: Array<{ month: number; current_amount: string; previous_amount: string }>;
  signals: Array<{ tone: "positive" | "warning" | "neutral"; title: string; description: string }>;
  top_customers: Array<{ rank: number; name: string; province: string; city: string; sales_amount: string; project_count: number; latest_signed_at: string | null }>;
  stages: Array<{ stage: string; opportunity_count: number; amount: string; percent: string }>;
}

export interface CurrentUser {
  username: string;
  role: UserRole;
  coverage_scopes: AccountCoverageScope[];
  salesperson_id: string | null;
  can_manage_users: boolean;
  can_manage_salespeople: boolean;
}

export interface AccountCoverageScope {
  id: string;
  scope_level: SalesCoverageLevel;
  scope_name: string;
  province: string | null;
  city: string | null;
  amap_adcode: string | null;
  included_provinces: string[];
}

export interface AuthorizedUser extends CurrentUser {
  id: string;
  is_active: boolean;
  last_login_at: string | null;
  created_at: string;
  is_current: boolean;
  is_protected: boolean;
  coverage_scopes: AccountCoverageScope[];
  salesperson_name: string | null;
  salesperson_employee_code: string | null;
}

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

export interface OrderProductItem {
  id: string;
  product_name: string;
  brand?: string | null;
  specification_model: string | null;
  product_image_url?: string | null;
  unit_price: string | null;
  quantity: string | null;
  line_total: string;
}

export interface OrganizationSalesProject {
  id: string;
  opportunity_id: string | null;
  salesperson_id: string | null;
  name: string;
  contract_amount: string;
  unit_price?: string | null;
  quantity?: string | null;
  supplier_name: string | null;
  specification_model?: string | null;
  province: string | null;
  city: string | null;
  signed_at: string | null;
  project_detail: string | null;
  products: OrderProductItem[];
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
  archived_at: string | null;
  version: number;
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
  version?: number;
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
  sales_projects: Array<Omit<OrganizationSalesProject, "id" | "contract_amount" | "unit_price" | "quantity" | "products"> & { id: string | null; contract_amount: number; unit_price?: number | null; quantity?: number | null; products: Array<Omit<OrderProductItem, "id" | "unit_price" | "quantity" | "line_total"> & { id: string | null; unit_price: number | null; quantity: number | null; line_total: number }> }>;
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

export type OrganizationBatchAction =
  | { ids: string[]; action: "review"; review_status: ReviewStatus; note?: string }
  | { ids: string[]; action: "archive" | "restore" }
  | { ids: string[]; action: "assign_owner"; follow_up_owner: string };

export interface OrganizationBatchResult {
  updated: number;
}

export interface PublicOrganizationSite {
  province: string | null;
  city: string | null;
  district: string | null;
  is_primary: boolean;
}

export type IntelligenceSourceType = "公开信息" | "一线反馈" | "推测";
export type IntelligenceConfidence = "高" | "中" | "低";
export type CompetitorCustomerLevel = "一级" | "二级" | "三级";
export type CompetitorSiteType = "总部" | "分部" | "服务点";
export type CompetitorStrengthLevel = "强" | "中" | "弱";
export type CompetitorRegionLevel = "省" | "市";

export interface PublicOrganizationCompetitorLink {
  competitor_id: string;
  competitor_name: string;
  competitor_color: string;
  competitor_customer_id: string;
  customer_level: CompetitorCustomerLevel;
  deal_count: number;
  total_amount: string;
  source_type: IntelligenceSourceType;
  confidence: IntelligenceConfidence;
  match_confidence: IntelligenceConfidence;
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
  competitor_contracts: PublicOrganizationCompetitorLink[];
}

export interface PublicOrganizationPage {
  items: PublicOrganization[];
  total: number;
  page: number;
  page_size: number;
}

export interface DealHeatmapSeller {
  id: string;
  name: string;
  kind: "unite" | "competitor";
  website_url: string | null;
}

export interface DealHeatmapProvinceSummary {
  province: string;
  signed_amount: string;
  signed_order_count: number;
  intention_amount: string;
  intention_count: number;
}

export interface DealHeatmapSummary {
  seller: DealHeatmapSeller;
  available_years: number[];
  provinces: DealHeatmapProvinceSummary[];
}

export interface DealHeatmapOrder {
  id: string;
  customer_name: string;
  customer_province: string | null;
  customer_city: string | null;
  project_name: string;
  amount: string;
  signed_at: string | null;
  deal_type: string | null;
  products: OrderProductItem[];
  product_name?: string | null;
  specification_model?: string | null;
  product_image_url?: string | null;
  unit_price?: string | null;
  quantity?: string | null;
  supplier_name: string | null;
  source_type: IntelligenceSourceType | null;
  source_reference: string | null;
  source_url: string | null;
  confidence: IntelligenceConfidence | null;
  notes: string | null;
}

export interface DealHeatmapIntention {
  id: string;
  customer_name: string;
  title: string;
  stage: OpportunityStage;
  estimated_amount: string;
  next_action_at: string | null;
}

export interface DealHeatmapProvinceDetail {
  seller: DealHeatmapSeller;
  province: string;
  signed_amount: string;
  signed_order_count: number;
  orders: DealHeatmapOrder[];
  intention_amount: string;
  intention_count: number;
  intentions: DealHeatmapIntention[];
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
  address: string | null;
  active_opportunity_count: number;
  opportunity_stage: OpportunityStage | null;
  estimated_opportunity_amount: string;
}

export interface PublicWonCustomerDeal {
  id: string;
  name: string;
  contract_amount: string;
  signed_at: string | null;
  project_detail: string | null;
}

export interface PublicWonCustomerMapPoint {
  id: string;
  name: string;
  organization_type: OrganizationType;
  industry: string | null;
  customer_status: CustomerStatus;
  review_status: ReviewStatus;
  address: string | null;
  province: string | null;
  city: string | null;
  district: string | null;
  longitude: number;
  latitude: number;
  deal_count: number;
  actual_sales_amount: string;
  deals: PublicWonCustomerDeal[];
}

export interface FilterOptions {
  organization_types: OrganizationType[];
  customer_statuses: CustomerStatus[];
  review_statuses: ReviewStatus[];
  provinces: string[];
  cities: string[];
  districts: string[];
  salespeople: Array<{ id: string; employee_code: string; display_name: string; is_active: boolean }>;
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

export interface CustomerGroupUnit {
  id: string;
  parent_id: string | null;
  name: string;
  level: number;
  is_headquarters: boolean;
  address: string;
  province: string;
  city: string;
  longitude: number;
  latitude: number;
  is_won: boolean;
  actual_sales_amount: string;
  opportunity_stage: OpportunityStage | null;
  estimated_opportunity_amount: string | null;
}

export interface CustomerGroupHeadquarters {
  id: string;
  name: string;
  color: string;
  headquarters: CustomerGroupUnit;
}

export interface CustomerGroupSummary {
  branch_count: number;
  won_branch_count: number;
  active_opportunity_count: number;
  actual_sales_amount: string;
  provinces: string[];
  cities: string[];
}

export interface CustomerGroupDetail {
  id: string;
  name: string;
  color: string;
  headquarters_id: string;
  summary: CustomerGroupSummary;
  units: CustomerGroupUnit[];
}

/** 管理员客户集团页的一条完整可编辑单位记录。 */
export interface CustomerGroupProfileUnit {
  id: string;
  draft_key: string;
  parent_draft_key: string | null;
  name: string;
  is_headquarters: boolean;
  address: string;
  province: string;
  city: string;
  longitude: number;
  latitude: number;
  is_won: boolean;
  actual_sales_amount: string;
  opportunity_stage: OpportunityStage | null;
  estimated_opportunity_amount: string | null;
  created_at: string;
  updated_at: string;
}

/** 管理员客户集团页按需读取的集团主档和完整单位树。 */
export interface CustomerGroupProfile {
  id: string;
  name: string;
  color: string;
  units: CustomerGroupProfileUnit[];
  created_at: string;
  updated_at: string;
}

export interface CompetitorSite {
  id: string;
  name: string;
  site_type: CompetitorSiteType;
  address: string;
  province: string;
  city: string;
  longitude: number;
  latitude: number;
  source_type: IntelligenceSourceType;
  source_reference: string;
  source_url: string | null;
  confidence: IntelligenceConfidence;
  notes: string | null;
  is_primary: boolean;
}

export interface CompetitorDeal {
  id: string;
  project_name: string;
  deal_type: string;
  products: OrderProductItem[];
  product_name?: string | null;
  specification_model?: string | null;
  product_image_url?: string | null;
  unit_price?: string | null;
  quantity?: string | null;
  supplier_name: string | null;
  amount: string;
  signed_at: string | null;
  source_type: IntelligenceSourceType;
  source_reference: string;
  source_url: string | null;
  confidence: IntelligenceConfidence;
  notes: string | null;
}

export type AdminDealSeller = "all" | "unite" | "competitor";

export interface AdminDealItem {
  id: string;
  seller_type: Exclude<AdminDealSeller, "all">;
  seller_id: string | null;
  customer_id: string;
  seller_name: string;
  customer_name: string;
  project_name: string;
  total_amount: string;
  supplier_name: string | null;
  opportunity_id: string | null;
  salesperson_id: string | null;
  salesperson_name: string | null;
  signed_at: string | null;
  province: string | null;
  city: string | null;
  deal_type: string | null;
  source_type: IntelligenceSourceType | null;
  source_reference: string | null;
  source_url: string | null;
  confidence: IntelligenceConfidence | null;
  notes: string | null;
  products: OrderProductItem[];
}

export interface AdminDealPage {
  items: AdminDealItem[];
  total: number;
  page: number;
  page_size: number;
}

export interface AdminDealFilterOptions {
  competitors: Array<{ value: string; label: string }>;
  suppliers: string[];
  years: number[];
}

export interface CompetitorCustomer {
  id: string;
  name: string;
  customer_level: CompetitorCustomerLevel;
  address: string;
  province: string;
  city: string;
  longitude: number;
  latitude: number;
  source_type: IntelligenceSourceType;
  source_reference: string;
  source_url: string | null;
  confidence: IntelligenceConfidence;
  first_observed_at: string | null;
  last_verified_at: string | null;
  notes: string | null;
  linked_organization_id: string | null;
  linked_organization_name: string | null;
  match_status: "待确认" | "已确认" | "已拒绝" | null;
  match_confidence: IntelligenceConfidence | null;
  deals: CompetitorDeal[];
}

export interface CompetitorStrengthRegion {
  id: string;
  region_level: CompetitorRegionLevel;
  province: string;
  city: string | null;
  strength_level: CompetitorStrengthLevel;
  source_type: IntelligenceSourceType;
  source_reference: string;
  source_url: string | null;
  confidence: IntelligenceConfidence;
  basis: string;
  score: string;
  site_count: number;
  customer_count: number;
  total_amount: string;
}

export interface CompetitorMapItem {
  id: string;
  name: string;
  website_url: string | null;
  color: string;
  description: string | null;
  primary_site: CompetitorSite;
}

export interface CompetitorDetail {
  id: string;
  name: string;
  website_url: string | null;
  color: string;
  description: string | null;
  summary: {
    site_count: number;
    customer_count: number;
    linked_customer_count: number;
    deal_count: number;
    total_amount: string;
    strong_region_count: number;
  };
  sites: CompetitorSite[];
  customers: CompetitorCustomer[];
  strength_regions: CompetitorStrengthRegion[];
}

export type SalespersonPeriodMonths = 1 | 3 | 6 | 12;
export interface SalespersonCoverageScope {
  scope_level: SalesCoverageLevel;
  scope_name: string;
  province: string | null;
  city: string | null;
  amap_adcode: string | null;
  included_provinces: string[];
}

export interface SalespersonActivitySummary {
  visits: number;
  demonstrations: number;
  marketing_events: number;
  total: number;
}

export interface SalespersonPerformance {
  period_months: SalespersonPeriodMonths;
  activities: SalespersonActivitySummary;
  actual_sales_amount: string;
  pipeline_amount: string;
  project_count: number;
  active_opportunity_count: number;
}

/** 第五地图只读 DTO：销售 Pin、分级覆盖范围与同一月份口径的人效汇总。 */
export interface SalespersonCoverage {
  id: string;
  employee_code: string;
  display_name: string;
  color: string;
  coverage_center_longitude: number;
  coverage_center_latitude: number;
  coverage_scopes: SalespersonCoverageScope[];
  performance: SalespersonPerformance;
}

export type SalesActivityType = "拜访" | "演示" | "市场活动";

export interface SalespersonProfileCoverageScope {
  id: string;
  scope_level: SalesCoverageLevel;
  scope_name: string;
  province: string | null;
  city: string | null;
  amap_adcode: string | null;
}

export interface SalespersonProfileActivity {
  id: string;
  organization_id: string | null;
  organization_name: string | null;
  activity_type: SalesActivityType;
  occurred_at: string;
  province: string;
  city: string;
  amap_adcode: string;
  notes: string | null;
}

/** 管理员销售页的完整档案 DTO，同时承载主档、覆盖范围和活动子集合。 */
export interface SalespersonProfile {
  id: string;
  employee_code: string;
  display_name: string;
  color: string;
  coverage_center_longitude: number;
  coverage_center_latitude: number;
  is_active: boolean;
  coverage_scopes: SalespersonProfileCoverageScope[];
  activities: SalespersonProfileActivity[];
  created_at: string;
  updated_at: string;
}

/** 第六地图图片、指标和一省一案公开 DTO；只包含后端批准发布的去敏字段。 */
export interface TypicalCaseImage {
  path: string;
  alt_text: string;
  caption: string | null;
  is_cover: boolean;
}

export interface TypicalCaseMetric {
  label: string;
  value: string;
  unit: string | null;
  note: string | null;
}

export type TypicalCaseAdminStatus = "未配置" | "草稿" | "已上线";

/** 管理列表只承载省份状态和识别信息，完整故事由详情接口按需返回。 */
export interface TypicalCaseAdminListItem {
  id: string | null;
  province: string;
  province_adcode: string;
  status: TypicalCaseAdminStatus;
  city: string | null;
  title: string | null;
  customer_display_name: string | null;
  industry_label: string | null;
  cover_image: TypicalCaseImage | null;
  is_featured: boolean;
  updated_at: string | null;
}

export interface TypicalCaseAdminOverview {
  total_regions: number;
  configured_count: number;
  draft_count: number;
  published_count: number;
  items: TypicalCaseAdminListItem[];
}

export interface TypicalCaseInput {
  sales_project_id: string | null;
  province: string;
  province_adcode: string;
  city: string;
  title: string;
  subtitle: string | null;
  customer_display_name: string;
  industry_label: string;
  summary: string;
  challenge: string;
  solution: string;
  outcome: string;
  product_scope: string;
  customer_quote: string | null;
  quote_attribution: string | null;
  show_contract_amount: boolean;
  is_published: boolean;
  is_featured: boolean;
  images: TypicalCaseImage[];
  metrics: TypicalCaseMetric[];
}

export interface TypicalCaseAdminDetail extends TypicalCaseInput {
  id: string;
  project_name: string | null;
  organization_name: string | null;
  contract_amount: string | null;
  signed_at: string | null;
  published_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface TypicalCaseProjectOption {
  id: string;
  project_name: string;
  organization_name: string;
  province: string;
  city: string;
  contract_amount: string;
  signed_at: string | null;
}

export interface TypicalCaseImageUploadRead {
  path: string;
  width: number;
  height: number;
  size_bytes: number;
}

export interface TypicalCasePublicSummary {
  id: string;
  province: string;
  province_adcode: string;
  city: string;
  title: string;
  subtitle: string | null;
  customer_display_name: string;
  industry_label: string;
  summary: string;
  cover_image: TypicalCaseImage | null;
  is_featured: boolean;
}

export interface TypicalCaseMapRegion {
  province: string;
  province_adcode: string;
  status: "已上线" | "筹备中";
  case: TypicalCasePublicSummary | null;
}

export interface TypicalCaseMapResponse {
  total_regions: number;
  published_count: number;
  pending_count: number;
  regions: TypicalCaseMapRegion[];
}

export interface TypicalCasePublicDetail extends Omit<TypicalCasePublicSummary, "cover_image" | "is_featured"> {
  challenge: string;
  solution: string;
  outcome: string;
  product_scope: string;
  customer_quote: string | null;
  quote_attribution: string | null;
  images: TypicalCaseImage[];
  metrics: TypicalCaseMetric[];
  project_name: string | null;
  signed_at: string | null;
  contract_amount: string | null;
  published_at: string | null;
}

/** 从非 HttpOnly Cookie 读取服务端绑定的 CSRF token，仅用于同源写请求头。 */
function csrfToken(): string | null {
  if (typeof document === "undefined") return null;
  const prefix = "unite_csrf_token=";
  const cookie = document.cookie.split("; ").find((item) => item.startsWith(prefix));
  return cookie ? decodeURIComponent(cookie.slice(prefix.length)) : null;
}

/** 为登录后的非只读请求附加 CSRF 头；登录本身由服务端 Origin 校验保护。 */
function addCsrfHeader(headers: Headers, method = "GET"): void {
  if (["GET", "HEAD", "OPTIONS"].includes(method.toUpperCase())) return;
  const token = csrfToken();
  if (token) headers.set("X-CSRF-Token", token);
}

/** 执行同源 API 请求，并统一保留会话、CSRF、取消信号与错误呈现。 */
export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  addCsrfHeader(headers, options.method);
  const response = await fetch(`/api/v1${path}`, {
    ...options,
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(apiErrorMessage(body?.detail, "请求失败，请稍后重试"));
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

/** 上传表单文件时保留浏览器生成的 multipart 边界，并复用统一错误解析。 */
export async function apiUpload<T>(path: string, formData: FormData): Promise<T> {
  const headers = new Headers();
  addCsrfHeader(headers, "POST");
  const response = await fetch(`/api/v1${path}`, {
    method: "POST",
    body: formData,
    credentials: "include",
    headers,
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(apiErrorMessage(body?.detail, "上传失败，请检查文件后重试"));
  }
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
