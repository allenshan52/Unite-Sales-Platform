/** 数据后台资源配置：集中声明通用页面、子表、列表列和完整业务字段。 */

export type AdminSection = "organizations" | "deals" | "network" | "groups" | "competitors" | "sales" | "cases" | "accounts";
export type AdminFieldKind = "text" | "url" | "textarea" | "number" | "date" | "datetime" | "checkbox" | "color" | "select" | "string-list" | "foreign" | "product-list";

export interface AdminFieldConfig {
  name: string;
  label: string;
  kind: AdminFieldKind;
  required?: boolean;
  nullable?: boolean;
  wide?: boolean;
  options?: string[];
  foreignResource?: string;
  step?: string;
  min?: number;
  max?: number;
  maxLength?: number;
  defaultValue?: string | boolean;
  help?: string;
}

export interface AdminResourceConfig {
  key: string;
  resource?: string;
  filters?: Record<string, string>;
  label: string;
  singular: string;
  description: string;
  listFields: string[];
  fields: AdminFieldConfig[];
}

export interface AdminSectionConfig {
  label: string;
  resources: AdminResourceConfig[];
}

export const ADMIN_SECTION_TABS: Array<{ key: AdminSection; label: string }> = [
  { key: "organizations", label: "全国目标单位" },
  { key: "deals", label: "成交订单" },
  { key: "network", label: "销售与渠道" },
  { key: "groups", label: "客户集团" },
  { key: "sales", label: "销售" },
  { key: "cases", label: "典型案例" },
  { key: "accounts", label: "授权账号" },
];

const sourceTypes = ["公开信息", "一线反馈", "推测"];
const confidenceLevels = ["高", "中", "低"];
const channelPartnerFields: AdminFieldConfig[] = [
  { name: "name", label: "渠道名称", kind: "text", required: true, maxLength: 160 },
  { name: "partner_type", label: "主体类型", kind: "select", required: true, options: ["经销商", "代理商", "合作伙伴"] },
  { name: "address", label: "地址", kind: "text", required: true, wide: true, maxLength: 500 },
  { name: "longitude", label: "真实经度", kind: "number", nullable: true, step: "any", min: 72.004, max: 137.8347 },
  { name: "latitude", label: "真实纬度", kind: "number", nullable: true, step: "any", min: 0.8293, max: 55.8271 },
  { name: "display_longitude", label: "演示经度", kind: "number", required: true, step: "any", min: 72.004, max: 137.8347 },
  { name: "display_latitude", label: "演示纬度", kind: "number", required: true, step: "any", min: 0.8293, max: 55.8271 },
  { name: "authorized_coverage_area", label: "授权覆盖区域", kind: "text", nullable: true, wide: true, maxLength: 500 },
  { name: "coverage_radius_km", label: "覆盖半径（公里）", kind: "number", required: true, min: 1, max: 2000, defaultValue: "300" },
  { name: "authorized_product_lines", label: "授权产品线", kind: "string-list", nullable: true, wide: true, help: "每行填写一个产品线" },
  { name: "cooperation_level", label: "合作等级", kind: "select", required: true, options: ["一级", "二级", "三级"] },
  { name: "contract_info", label: "合同信息", kind: "textarea", nullable: true, wide: true, maxLength: 5000 },
  { name: "notes", label: "内部备注", kind: "textarea", nullable: true, wide: true, maxLength: 5000 },
  { name: "is_active", label: "启用渠道", kind: "checkbox", defaultValue: true },
];

export const ADMIN_SECTION_CONFIGS: Record<Exclude<AdminSection, "organizations" | "deals" | "groups" | "cases" | "accounts">, AdminSectionConfig> = {
  network: {
    label: "销售与渠道",
    resources: [
      {
        key: "sales_office_locations",
        label: "销售常驻点",
        singular: "销售常驻点",
        description: "维护销售办公地点、地图坐标、覆盖半径和启用状态。",
        listFields: ["name", "city", "coverage_radius_km", "is_active"],
        fields: [
          { name: "name", label: "常驻点名称", kind: "text", required: true, maxLength: 160 },
          { name: "city", label: "城市", kind: "text", required: true, maxLength: 60 },
          { name: "address", label: "详细地址", kind: "text", nullable: true, wide: true, maxLength: 500 },
          { name: "longitude", label: "经度", kind: "number", required: true, step: "any", min: 72.004, max: 137.8347 },
          { name: "latitude", label: "纬度", kind: "number", required: true, step: "any", min: 0.8293, max: 55.8271 },
          { name: "coverage_radius_km", label: "覆盖半径（公里）", kind: "number", required: true, min: 1, max: 2000, defaultValue: "300" },
          { name: "is_active", label: "启用常驻点", kind: "checkbox", defaultValue: true },
        ],
      },
      {
        key: "channel_partners_dealers",
        resource: "channel_partners",
        filters: { partner_type: "经销商" },
        label: "经销商",
        singular: "经销商",
        description: "维护经销商、授权范围、产品线、合同和内部备注。",
        listFields: ["name", "partner_type", "cooperation_level", "is_active"],
        fields: channelPartnerFields,
      },
      {
        key: "channel_partners_agents",
        resource: "channel_partners",
        filters: { partner_type: "代理商" },
        label: "代理商",
        singular: "代理商",
        description: "维护代理商、授权范围、产品线、合同和内部备注。",
        listFields: ["name", "partner_type", "cooperation_level", "is_active"],
        fields: channelPartnerFields,
      },
      {
        key: "channel_partners_partners",
        resource: "channel_partners",
        filters: { partner_type: "合作伙伴" },
        label: "合作伙伴",
        singular: "合作伙伴",
        description: "维护合作伙伴、授权范围、产品线、合同和内部备注。",
        listFields: ["name", "partner_type", "cooperation_level", "is_active"],
        fields: channelPartnerFields,
      },
    ],
  },
  competitors: {
    label: "同行",
    resources: [
      {
        key: "competitors",
        label: "同行主档",
        singular: "同行",
        description: "维护同行名称、公司官网、展示颜色、说明和启用状态。",
        listFields: ["name", "color", "is_active", "updated_at"],
        fields: [
          { name: "name", label: "同行名称", kind: "text", required: true, wide: true, maxLength: 255 },
          { name: "website_url", label: "同行公司官网 URL", kind: "url", nullable: true, wide: true, maxLength: 1000, help: "填写以 http:// 或 https:// 开头的完整网址" },
          { name: "color", label: "展示颜色", kind: "color", required: true, defaultValue: "#25846F" },
          { name: "description", label: "同行说明", kind: "textarea", nullable: true, wide: true, maxLength: 5000 },
          { name: "is_active", label: "启用同行", kind: "checkbox", defaultValue: true },
        ],
      },
      {
        key: "competitor_sites",
        label: "据点",
        singular: "同行据点",
        description: "维护总部、分部和服务点及其情报来源。",
        listFields: ["name", "competitor_id", "site_type", "city"],
        fields: [
          { name: "competitor_id", label: "所属同行", kind: "foreign", required: true, foreignResource: "competitors" },
          { name: "name", label: "据点名称", kind: "text", required: true, wide: true, maxLength: 255 },
          { name: "site_type", label: "据点类型", kind: "select", required: true, options: ["总部", "分部", "服务点"] },
          { name: "address", label: "地址", kind: "text", required: true, wide: true, maxLength: 500 },
          { name: "province", label: "省份", kind: "text", required: true, maxLength: 60 },
          { name: "city", label: "城市", kind: "text", required: true, maxLength: 60 },
          { name: "longitude", label: "经度", kind: "number", required: true, step: "any", min: 72.004, max: 137.8347 },
          { name: "latitude", label: "纬度", kind: "number", required: true, step: "any", min: 0.8293, max: 55.8271 },
          { name: "source_type", label: "来源类型", kind: "select", required: true, options: sourceTypes },
          { name: "source_reference", label: "来源说明", kind: "text", required: true, wide: true, maxLength: 500 },
          { name: "source_url", label: "来源网址", kind: "text", nullable: true, wide: true, maxLength: 1000 },
          { name: "confidence", label: "置信度", kind: "select", required: true, options: confidenceLevels },
          { name: "notes", label: "备注", kind: "textarea", nullable: true, wide: true, maxLength: 5000 },
          { name: "is_primary", label: "主要据点", kind: "checkbox" },
        ],
      },
      {
        key: "competitor_customers",
        label: "成交单位",
        singular: "同行成交单位",
        description: "维护同行成交单位、位置、等级和核验时间。",
        listFields: ["name", "competitor_id", "customer_level", "city"],
        fields: [
          { name: "competitor_id", label: "所属同行", kind: "foreign", required: true, foreignResource: "competitors" },
          { name: "name", label: "成交单位名称", kind: "text", required: true, wide: true, maxLength: 255 },
          { name: "customer_level", label: "客户等级", kind: "select", required: true, options: ["一级", "二级", "三级"] },
          { name: "address", label: "地址", kind: "text", required: true, wide: true, maxLength: 500 },
          { name: "province", label: "省份", kind: "text", required: true, maxLength: 60 },
          { name: "city", label: "城市", kind: "text", required: true, maxLength: 60 },
          { name: "longitude", label: "经度", kind: "number", required: true, step: "any", min: 72.004, max: 137.8347 },
          { name: "latitude", label: "纬度", kind: "number", required: true, step: "any", min: 0.8293, max: 55.8271 },
          { name: "source_type", label: "来源类型", kind: "select", required: true, options: sourceTypes },
          { name: "source_reference", label: "来源说明", kind: "text", required: true, wide: true, maxLength: 500 },
          { name: "source_url", label: "来源网址", kind: "text", nullable: true, wide: true, maxLength: 1000 },
          { name: "confidence", label: "置信度", kind: "select", required: true, options: confidenceLevels },
          { name: "first_observed_at", label: "首次发现日期", kind: "date", nullable: true },
          { name: "last_verified_at", label: "最后核验日期", kind: "date", nullable: true },
          { name: "notes", label: "备注", kind: "textarea", nullable: true, wide: true, maxLength: 5000 },
        ],
      },
      {
        key: "competitor_deals",
        label: "成交记录",
        singular: "同行成交记录",
        description: "维护成交单位下的逐笔项目、产品、数量、供应商、价格、日期和来源。",
        listFields: ["project_name", "competitor_customer_id", "amount", "signed_at"],
        fields: [
          { name: "competitor_customer_id", label: "同行成交单位", kind: "foreign", required: true, foreignResource: "competitor_customers" },
          { name: "project_name", label: "项目名称", kind: "text", required: true, wide: true, maxLength: 255 },
          { name: "deal_type", label: "成交类型", kind: "text", nullable: true, maxLength: 80 },
          { name: "products", label: "产品明细", kind: "product-list", wide: true },
          { name: "supplier_name", label: "供应商名称", kind: "text", nullable: true, maxLength: 255 },
          { name: "amount", label: "项目总价", kind: "number", required: true, step: "0.01", min: 0.01 },
          { name: "signed_at", label: "中标时间", kind: "date", nullable: true },
          { name: "source_type", label: "来源类型", kind: "select", nullable: true, options: sourceTypes },
          { name: "source_reference", label: "来源说明", kind: "text", nullable: true, wide: true, maxLength: 500 },
          { name: "source_url", label: "来源网址", kind: "text", nullable: true, wide: true, maxLength: 1000 },
          { name: "confidence", label: "置信度", kind: "select", nullable: true, options: confidenceLevels },
          { name: "notes", label: "备注", kind: "textarea", nullable: true, wide: true, maxLength: 5000 },
        ],
      },
      {
        key: "competitor_links",
        label: "正式单位关联",
        singular: "同行正式单位关联",
        description: "审核同行成交单位与全国目标单位之间的匹配关系。",
        listFields: ["competitor_customer_id", "organization_id", "match_status", "match_method"],
        fields: [
          { name: "competitor_customer_id", label: "同行成交单位", kind: "foreign", required: true, foreignResource: "competitor_customers" },
          { name: "organization_id", label: "全国目标单位", kind: "foreign", required: true, foreignResource: "organizations" },
          { name: "match_status", label: "匹配状态", kind: "select", required: true, options: ["待确认", "已确认", "已拒绝"] },
          { name: "match_method", label: "匹配方式", kind: "text", required: true, maxLength: 120 },
          { name: "match_confidence", label: "匹配置信度", kind: "select", required: true, options: confidenceLevels },
          { name: "matched_by", label: "匹配人员", kind: "text", nullable: true, maxLength: 120 },
          { name: "matched_at", label: "匹配时间", kind: "datetime", nullable: true },
          { name: "notes", label: "备注", kind: "textarea", nullable: true, wide: true, maxLength: 5000 },
        ],
      },
    ],
  },
  sales: {
    label: "销售",
    resources: [
      {
        key: "salespeople",
        label: "销售人员",
        singular: "销售人员",
        description: "销售人员主档；市、省、大区、全国覆盖范围和销售活动统一在人员档案内维护。",
        listFields: ["display_name", "employee_code", "is_active"],
        fields: [
          { name: "employee_code", label: "员工编号", kind: "text", required: true, maxLength: 40 },
          { name: "display_name", label: "姓名", kind: "text", required: true, maxLength: 120 },
          { name: "color", label: "展示颜色", kind: "color", required: true, defaultValue: "#2878B5" },
          { name: "coverage_center_longitude", label: "Pin 经度", kind: "number", required: true, step: "any", min: 72.004, max: 137.8347 },
          { name: "coverage_center_latitude", label: "Pin 纬度", kind: "number", required: true, step: "any", min: 0.8293, max: 55.8271 },
          { name: "is_active", label: "在职启用", kind: "checkbox", defaultValue: true },
        ],
      },
    ],
  },
};
