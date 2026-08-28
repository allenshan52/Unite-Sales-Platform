/** 数据后台浏览器验收：覆盖八页导航、分类分页、完整字段 CRUD 和响应式布局。 */

import { expect, test, type Page, type Route } from "@playwright/test";

const baseUrl = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3100";
const adminUrl = `${baseUrl}/admin/organizations`;

test.use({ launchOptions: { executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" } });

type RecordItem = Record<string, unknown> & { id: string };

/** 按真实接口语义切片模拟数据，确保大数据分页回归不会被全量假响应掩盖。 */
function paginate<T>(items: T[], url: URL) {
  const page = Number(url.searchParams.get("page") ?? 1);
  const pageSize = Number(url.searchParams.get("page_size") ?? 10);
  const start = (page - 1) * pageSize;
  return { items: items.slice(start, start + pageSize), total: items.length, page, page_size: pageSize };
}

const resourceItems: Record<string, RecordItem[]> = {
  channel_partners: [
    { id: "channel-1", name: "演示经销商", partner_type: "经销商", cooperation_level: "一级", is_active: true },
    { id: "channel-2", name: "演示代理商", partner_type: "代理商", cooperation_level: "二级", is_active: true },
    { id: "channel-3", name: "演示合作伙伴", partner_type: "合作伙伴", cooperation_level: "三级", is_active: true },
  ],
  salespeople: [{ id: "sales-1", employee_code: "XS001", display_name: "演示销售", color: "#2878B5", coverage_center_longitude: 120.15, coverage_center_latitude: 30.28, is_active: true }],
  competitors: [{ id: "competitor-1", name: "演示同行", website_url: "https://example.com", color: "#25846F", description: "仅用于浏览器测试的虚构同行", is_active: true, created_at: "2026-08-18T00:00:00+08:00", updated_at: "2026-08-18T00:00:00+08:00" }],
  competitor_sites: [{ id: "site-1", competitor_id: "competitor-1", name: "演示同行总部", site_type: "总部", address: "北京市演示路 8 号", province: "北京市", city: "北京市", longitude: 116.4, latitude: 39.9, source_type: "公开信息", source_reference: "虚构公开资料", source_url: null, confidence: "高", notes: null, is_primary: true }],
  competitor_customers: [{ id: "customer-1", competitor_id: "competitor-1", name: "演示成交单位", customer_level: "一级", address: "苏州市演示路 9 号", province: "江苏省", city: "苏州市", longitude: 120.58, latitude: 31.3, source_type: "一线反馈", source_reference: "虚构一线反馈", source_url: null, confidence: "中", first_observed_at: "2026-06-01", last_verified_at: "2026-08-01", notes: "虚构单位" }],
  competitor_deals: [{ id: "deal-1", competitor_customer_id: "customer-1", project_name: "演示成交项目", deal_type: "设备", product_name: "台式气相色谱仪", specification_model: "GC-DEMO-01", product_image_url: "/cases/jiangsu-lab.webp", unit_price: "130000.25", quantity: "2.000", supplier_name: "虚构仪器供应商", amount: "260000.50", signed_at: "2026-07-15", source_type: "公开信息", source_reference: "虚构合同公告", source_url: null, confidence: "高", notes: null }],
  competitor_links: [{ id: "link-1", competitor_customer_id: "customer-1", organization_id: "org-1", organization_id_label: "演示目标单位", match_status: "已确认", match_method: "名称和地址", match_confidence: "高", matched_by: "admin", matched_at: "2026-08-01T09:00:00+08:00", notes: null }],
  competitor_strength_regions: [{ id: "region-1", competitor_id: "competitor-1", region_level: "省", province: "北京市", city: null, strength_level: "强", source_type: "公开信息", source_reference: "虚构区域资料", source_url: null, confidence: "高", basis: "虚构测试依据" }],
};

// 新订单契约把旧单产品字段迁移为 products 数组，保留两条明细覆盖增删编辑与列表摘要。
resourceItems.competitor_deals[0].products = [
  { id: "deal-product-1", product_name: "台式气相色谱仪", brand: "虚构品牌甲", specification_model: "GC-DEMO-01", product_image_url: "/cases/jiangsu-lab.webp", unit_price: "130000.25", quantity: "2.000", line_total: "260000.50" },
];

const salespersonProfiles: Record<string, Record<string, unknown>> = {
  "sales-1": {
    ...resourceItems.salespeople[0],
    coverage_scopes: [{ id: "coverage-1", scope_level: "市", scope_name: "杭州市", province: "浙江省", city: "杭州市", amap_adcode: "330100" }],
    activities: [{ id: "activity-1", organization_id: null, organization_name: null, activity_type: "拜访", occurred_at: "2026-08-17T09:00:00+08:00", province: "浙江省", city: "杭州市", amap_adcode: "330100", notes: "虚构活动" }],
    created_at: "2026-08-17T00:00:00+08:00",
    updated_at: "2026-08-17T00:00:00+08:00",
  },
};

const customerGroupProfiles: Record<string, Record<string, unknown>> = {
  "group-1": {
    id: "group-1", name: "演示客户集团", color: "#2F8F72",
    units: [
      { id: "group-unit-1", draft_key: "group-unit-1", parent_draft_key: null, name: "演示集团总部", is_headquarters: true, address: "北京市演示路 1 号", province: "北京市", city: "北京市", longitude: 116.4074, latitude: 39.9042, is_won: false, actual_sales_amount: "0.00", opportunity_stage: null, estimated_opportunity_amount: null, created_at: "2026-08-18T00:00:00+08:00", updated_at: "2026-08-18T00:00:00+08:00" },
      { id: "group-unit-2", draft_key: "group-unit-2", parent_draft_key: "group-unit-1", name: "演示集团分支", is_headquarters: false, address: "天津市演示路 2 号", province: "天津市", city: "天津市", longitude: 117.2, latitude: 39.12, is_won: true, actual_sales_amount: "88000.00", opportunity_stage: "商务谈判", estimated_opportunity_amount: "120000.00", created_at: "2026-08-18T00:00:00+08:00", updated_at: "2026-08-18T00:00:00+08:00" },
    ],
    created_at: "2026-08-18T00:00:00+08:00", updated_at: "2026-08-18T00:00:00+08:00",
  },
};

let typicalCaseDetail: Record<string, unknown> = {
  id: "case-zhejiang", sales_project_id: null, province: "浙江省", province_adcode: "330000", city: "金华市",
  title: "研发中心分析平台一期", subtitle: "虚构演示案例", customer_display_name: "浙江某研发中心（演示）",
  industry_label: "医药研发分析", summary: "虚构案例摘要", challenge: "虚构业务挑战", solution: "虚构解决方案",
  outcome: "虚构实施成果", product_scope: "虚构产品与服务范围", customer_quote: null, quote_attribution: null,
  show_contract_amount: false, is_published: false, is_featured: false, images: [], metrics: [], project_name: null,
  organization_name: null, contract_amount: null, signed_at: null, published_at: null,
  created_at: "2026-08-18T00:00:00+08:00", updated_at: "2026-08-18T00:00:00+08:00",
};

/** 为案例列表生成一个已配置省份和一个空槽位，验证单列表进入详情的交互。 */
function typicalCaseOverview() {
  return {
    total_regions: 31, configured_count: 1, draft_count: 1, published_count: 0,
    items: [
      { id: "case-zhejiang", province: "浙江省", province_adcode: "330000", status: "草稿", city: typicalCaseDetail.city, title: typicalCaseDetail.title, customer_display_name: typicalCaseDetail.customer_display_name, industry_label: typicalCaseDetail.industry_label, cover_image: null, is_featured: false, updated_at: typicalCaseDetail.updated_at },
      { id: null, province: "北京市", province_adcode: "110000", status: "未配置", city: null, title: null, customer_display_name: null, industry_label: null, cover_image: null, is_featured: false, updated_at: null },
    ],
  };
}

/** 为页面安装最小受控 API，避免浏览器验收依赖本机 PostgreSQL。 */
async function installAdminApi(page: Page, currentUser: Record<string, unknown> = { username: "admin", role: "超级管理员", coverage_scopes: [{ id: "account-scope-1", scope_level: "全国", scope_name: "全国", province: null, city: null, amap_adcode: null, included_provinces: [] }], salesperson_id: null, can_manage_users: true, can_manage_salespeople: true }): Promise<void> {
  await page.route("**/api/v1/**", async (route: Route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace("/api/v1", "");
    const json = (body: unknown, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });

    if (path === "/auth/me") return json(currentUser);
    if (path === "/auth/logout" && request.method() === "POST") return route.fulfill({ status: 204, body: "" });
    if (path === "/organizations/filters") return json({ organization_types: [], customer_statuses: [], review_statuses: [], provinces: [], cities: [], districts: [], salespeople: [{ id: "sales-1", employee_code: "XS001", display_name: "演示销售", is_active: true }] });
    if (path === "/organizations") return json({ items: [], total: 0, page: 1, page_size: 10 });
    if (path === "/organizations/org-1") return json({ id: "org-1", name: "演示目标单位", opportunities: [{ id: "opportunity-1", title: "演示商机", stage: "方案交流", estimated_amount: "300000.00", ai_summary: null, next_action: null, next_action_at: null }] });
    if (path === "/admin-data/organizations/options") return json([{ value: "org-1", label: "演示目标单位" }]);
    if (path === "/admin-data/competitor_customers/options") return json([{ value: "customer-1", label: "演示成交单位" }]);
    if (path === "/admin-data/salespeople/options") return json([{ value: "sales-1", label: "演示销售" }]);
    if (path === "/admin-deals/options") return json({ competitors: [{ value: "competitor-1", label: "演示同行" }], suppliers: ["虚构仪器供应商"], years: [2026] });
    if (path === "/admin-deals") {
      const deal = resourceItems.competitor_deals[0];
      if (!deal) return json({ items: [], total: 0, page: 1, page_size: 20 });
      return json({ items: [{ id: deal.id, seller_type: "competitor", seller_id: "competitor-1", customer_id: deal.competitor_customer_id, seller_name: "演示同行", customer_name: "演示成交单位", project_name: deal.project_name, total_amount: deal.amount, supplier_name: deal.supplier_name, opportunity_id: null, salesperson_id: null, salesperson_name: null, signed_at: deal.signed_at, province: "江苏省", city: "苏州市", deal_type: deal.deal_type, source_type: deal.source_type, source_reference: deal.source_reference, source_url: deal.source_url, confidence: deal.confidence, notes: deal.notes, products: deal.products }], total: 1, page: 1, page_size: 20 });
    }
    if (path === "/admin-deals/unite" && request.method() === "POST") return json({ id: "unite-deal-created" }, 201);

    if (path === "/admin-typical-cases/project-options") return json([]);
    if (path === "/admin-typical-cases" && request.method() === "GET") return json(typicalCaseOverview());
    if (path === "/admin-typical-cases/case-zhejiang" && request.method() === "GET") return json(typicalCaseDetail);
    if (path === "/admin-typical-cases/case-zhejiang" && request.method() === "PATCH") {
      typicalCaseDetail = { ...typicalCaseDetail, ...request.postDataJSON(), updated_at: "2026-08-19T10:00:00+08:00" };
      return json(typicalCaseDetail);
    }
    if (path === "/admin-typical-cases/case-zhejiang" && request.method() === "DELETE") return route.fulfill({ status: 204, body: "" });
    if (path === "/admin-typical-cases" && request.method() === "POST") {
      typicalCaseDetail = { ...typicalCaseDetail, ...request.postDataJSON(), id: "case-created", created_at: "2026-08-19T10:00:00+08:00", updated_at: "2026-08-19T10:00:00+08:00", project_name: null, organization_name: null, contract_amount: null, signed_at: null, published_at: null };
      return json(typicalCaseDetail, 201);
    }

    if (path === "/admin-competitors" && request.method() === "GET") {
      const items = resourceItems.competitors.map((competitor) => {
        const sites = resourceItems.competitor_sites.filter((item) => item.competitor_id === competitor.id);
        const customers = resourceItems.competitor_customers.filter((item) => item.competitor_id === competitor.id);
        const customerIds = new Set(customers.map((item) => item.id));
        const deals = resourceItems.competitor_deals.filter((item) => customerIds.has(String(item.competitor_customer_id)));
        const links = resourceItems.competitor_links.filter((item) => customerIds.has(String(item.competitor_customer_id)));
        const regions = resourceItems.competitor_strength_regions.filter((item) => item.competitor_id === competitor.id);
        const primarySite = sites.find((item) => item.is_primary);
        return { ...competitor, primary_site_name: primarySite?.name ?? null, primary_site_city: primarySite?.city ?? null, site_count: sites.length, customer_count: customers.length, linked_customer_count: links.filter((item) => item.match_status === "已确认").length, pending_link_count: links.filter((item) => item.match_status === "待确认").length, deal_count: deals.length, total_amount: deals.reduce((total, item) => total + Number(item.amount ?? 0), 0).toFixed(2), strength_region_count: regions.length, strength_regions: regions.map((item) => item.city ? `${item.province}·${item.city}` : String(item.province)).slice(0, 3) };
      });
      return json(paginate(items, url));
    }

    if (path === "/public/competitors/competitor-1") return json({ id: "competitor-1", name: "演示同行", website_url: "https://example.com", color: "#25846F", description: "虚构同行", summary: { site_count: 1, customer_count: 1, linked_customer_count: 1, deal_count: 1, total_amount: "260000.50", strong_region_count: 1 }, sites: [], customers: [], strength_regions: [{ id: "computed-region-1", region_level: "省", province: "江苏省", city: null, strength_level: "强", source_type: "公开信息", source_reference: "自动聚合", source_url: null, confidence: "高", basis: "计算结果", score: "88.50", site_count: 1, customer_count: 1, total_amount: "260000.50" }] });

    const customerGroupMatch = path.match(/^\/admin-customer-groups(?:\/([^/]+))?$/);
    if (customerGroupMatch) {
      const itemId = customerGroupMatch[1];
      if (request.method() === "GET" && !itemId) {
        const items = Object.values(customerGroupProfiles).map((profile) => {
          const units = profile.units as Array<Record<string, unknown>>;
          const headquarters = units.find((unit) => unit.is_headquarters);
          const branches = units.filter((unit) => !unit.is_headquarters);
          return {
            id: profile.id, name: profile.name, color: profile.color,
            headquarters_name: headquarters?.name ?? null, headquarters_city: headquarters?.city ?? null,
            branch_count: branches.length, won_unit_count: units.filter((unit) => unit.is_won).length,
            active_opportunity_count: units.filter((unit) => unit.opportunity_stage && unit.opportunity_stage !== "已关闭失单").length,
            actual_sales_amount: units.reduce((total, unit) => total + Number(unit.actual_sales_amount ?? 0), 0).toFixed(2),
            estimated_opportunity_amount: units.reduce((total, unit) => total + Number(unit.estimated_opportunity_amount ?? 0), 0).toFixed(2),
          };
        });
        return json(paginate(items, url));
      }
      if (request.method() === "GET" && itemId) return json(customerGroupProfiles[itemId] ?? { detail: "记录不存在" }, customerGroupProfiles[itemId] ? 200 : 404);
      if (request.method() === "POST") {
        const payload = request.postDataJSON() as Record<string, unknown>;
        const id = `group-${Object.keys(customerGroupProfiles).length + 1}`;
        const units = (payload.units as Array<Record<string, unknown>>).map((unit, index) => ({ ...unit, id: `${id}-unit-${index + 1}`, created_at: "2026-08-18T00:00:00+08:00", updated_at: "2026-08-18T00:00:00+08:00" }));
        const created = { id, ...payload, units, created_at: "2026-08-18T00:00:00+08:00", updated_at: "2026-08-18T00:00:00+08:00" };
        customerGroupProfiles[id] = created;
        return json(created, 201);
      }
      if (request.method() === "PATCH" && itemId && customerGroupProfiles[itemId]) {
        const payload = request.postDataJSON() as Record<string, unknown>;
        customerGroupProfiles[itemId] = { ...customerGroupProfiles[itemId], ...payload };
        return json(customerGroupProfiles[itemId]);
      }
      if (request.method() === "DELETE" && itemId) {
        delete customerGroupProfiles[itemId];
        return route.fulfill({ status: 204, body: "" });
      }
    }

    const salespersonMatch = path.match(/^\/admin-salespeople(?:\/([^/]+))?$/);
    if (salespersonMatch) {
      const itemId = salespersonMatch[1];
      if (request.method() === "GET" && !itemId) {
        const items = resourceItems.salespeople.map((item) => {
          const profile = salespersonProfiles[item.id];
          const coverageScopes = (profile?.coverage_scopes as Array<{ scope_level: string; scope_name: string }> | undefined) ?? [];
          return { ...item, coverage_scopes: coverageScopes.map((scope) => scope.scope_level === "全国" ? "全国" : `${scope.scope_name}（${scope.scope_level}）`).slice(0, 10), coverage_scope_total: coverageScopes.length, actual_sales_amount: "88000.00", visit_count: 3, demonstration_count: 2, marketing_event_count: 1 };
        });
        return json(paginate(items, url));
      }
      if (request.method() === "GET" && itemId) return json(salespersonProfiles[itemId] ?? { detail: "记录不存在" }, salespersonProfiles[itemId] ? 200 : 404);
      if (request.method() === "POST") {
        const payload = request.postDataJSON() as Record<string, unknown>;
        const id = `sales-${resourceItems.salespeople.length + 1}`;
        const created = { id, ...payload, created_at: "2026-08-17T00:00:00+08:00", updated_at: "2026-08-17T00:00:00+08:00" };
        salespersonProfiles[id] = created;
        resourceItems.salespeople.push({ id, ...payload } as RecordItem);
        return json(created, 201);
      }
      if (request.method() === "PATCH" && itemId && salespersonProfiles[itemId]) {
        const payload = request.postDataJSON() as Record<string, unknown>;
        salespersonProfiles[itemId] = { ...salespersonProfiles[itemId], ...payload };
        const index = resourceItems.salespeople.findIndex((item) => item.id === itemId);
        resourceItems.salespeople[index] = { ...resourceItems.salespeople[index], ...payload };
        return json(salespersonProfiles[itemId]);
      }
      if (request.method() === "DELETE" && itemId) {
        delete salespersonProfiles[itemId];
        const index = resourceItems.salespeople.findIndex((item) => item.id === itemId);
        if (index >= 0) resourceItems.salespeople.splice(index, 1);
        return route.fulfill({ status: 204, body: "" });
      }
    }

    const match = path.match(/^\/admin-data\/([^/]+)(?:\/([^/]+))?$/);
    if (!match) return json({ detail: "未模拟的接口" }, 404);
    const [, resource, itemId] = match;
    const items = resourceItems[resource] ?? (resourceItems[resource] = []);
    if (request.method() === "GET") {
      const partnerType = url.searchParams.get("partner_type");
      const parentId = url.searchParams.get("parent_id");
      const ownerField = resource === "competitor_deals" || resource === "competitor_links" ? "competitor_customer_id" : "competitor_id";
      const partnerItems = partnerType ? items.filter((item) => item.partner_type === partnerType) : items;
      const visibleItems = parentId ? partnerItems.filter((item) => item[ownerField] === parentId) : partnerItems;
      return json(paginate(visibleItems, url));
    }

    if (request.method() === "POST") {
      const payload = (request.postDataJSON() as { data: Record<string, unknown> }).data;
      const created = { id: `${resource}-${items.length + 1}`, ...payload };
      items.push(created);
      return json(created, 201);
    }
    const index = items.findIndex((item) => item.id === itemId);
    if (request.method() === "PUT" && index >= 0) {
      const payload = (request.postDataJSON() as { data: Record<string, unknown> }).data;
      items[index] = { ...items[index], ...payload };
      return json(items[index]);
    }
    if (request.method() === "DELETE" && index >= 0) {
      items.splice(index, 1);
      return route.fulfill({ status: 204, body: "" });
    }
    return json({ detail: "记录不存在" }, 404);
  });
}

/** 打开已登录后台并等待默认全国目标单位页完成加载。 */
async function openAdmin(page: Page): Promise<void> {
  await installAdminApi(page);
  await page.goto(adminUrl, { waitUntil: "networkidle" });
  await expect(page.getByRole("heading", { name: "数据后台" })).toBeVisible();
}

test("普通用户可进入数据后台但看不到授权账号页面", async ({ page }) => {
  await installAdminApi(page, {
    username: "jl_ln_sales",
    role: "普通用户",
    coverage_scopes: [
      { id: "scope-jilin", scope_level: "省", scope_name: "吉林", province: "吉林", city: null, amap_adcode: null, included_provinces: ["吉林"] },
      { id: "scope-liaoning", scope_level: "省", scope_name: "辽宁", province: "辽宁", city: null, amap_adcode: null, included_provinces: ["辽宁"] },
    ],
    salesperson_id: "sales-1",
    can_manage_users: false,
    can_manage_salespeople: false,
  });

  await page.goto(adminUrl, { waitUntil: "networkidle" });

  await expect(page.getByRole("heading", { name: "数据后台" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "全国目标单位", exact: true })).toBeVisible();
  await expect(page.getByRole("tab", { name: "授权账号", exact: true })).toHaveCount(0);
  await expect(page.getByRole("tab", { name: "销售", exact: true })).toHaveCount(0);
  await expect(page.getByText("jl_ln_sales", { exact: true })).toBeVisible();
});

test("全国普通用户可管理销售但看不到授权账号页面", async ({ page }) => {
  await installAdminApi(page, {
    username: "national_manager",
    role: "普通用户",
    coverage_scopes: [{ id: "scope-national", scope_level: "全国", scope_name: "全国", province: null, city: null, amap_adcode: null, included_provinces: [] }],
    salesperson_id: null,
    can_manage_users: false,
    can_manage_salespeople: true,
  });

  await page.goto(adminUrl, { waitUntil: "networkidle" });

  await expect(page.getByRole("tab", { name: "销售", exact: true })).toBeVisible();
  await expect(page.getByRole("tab", { name: "授权账号", exact: true })).toHaveCount(0);
});

test("返回主页面保留当前登录会话", async ({ page }) => {
  let logoutRequests = 0;
  page.on("request", (request) => {
    if (request.url().endsWith("/api/v1/auth/logout")) logoutRequests += 1;
  });
  await openAdmin(page);
  await page.getByRole("link", { name: "返回主页面", exact: true }).click();
  await expect(page).toHaveURL(baseUrl + "/");
  await expect(page.getByRole("button", { name: "退出", exact: true })).toBeVisible();
  expect(logoutRequests).toBe(0);
});

test("用户名位于退出按钮下方且不与后台标签重叠", async ({ page }) => {
  await openAdmin(page);
  const tabs = page.getByRole("tablist", { name: "后台数据页面" });
  const exitButton = page.getByRole("button", { name: "退出", exact: true });
  const username = page.locator(".admin-username");
  const [tabsBox, exitBox, usernameBox] = await Promise.all([tabs.boundingBox(), exitButton.boundingBox(), username.boundingBox()]);
  expect(tabsBox).not.toBeNull();
  expect(exitBox).not.toBeNull();
  expect(usernameBox).not.toBeNull();
  expect(usernameBox!.y).toBeGreaterThanOrEqual(exitBox!.y + exitBox!.height);
  const overlapsTabs = usernameBox!.x < tabsBox!.x + tabsBox!.width && usernameBox!.x + usernameBox!.width > tabsBox!.x && usernameBox!.y < tabsBox!.y + tabsBox!.height && usernameBox!.y + usernameBox!.height > tabsBox!.y;
  expect(overlapsTabs).toBe(false);

  await page.setViewportSize({ width: 2048, height: 900 });
  const desktopHeader = await page.locator(".admin-data-header").evaluate((header) => {
    const heading = header.querySelector<HTMLElement>(".admin-data-heading")?.getBoundingClientRect();
    const navigation = header.querySelector<HTMLElement>(".admin-dataset-tabs")?.getBoundingClientRect();
    const actions = header.querySelector<HTMLElement>(".admin-user")?.getBoundingClientRect();
    const overlaps = (left?: DOMRect, right?: DOMRect) => Boolean(left && right && left.left < right.right && left.right > right.left && left.top < right.bottom && left.bottom > right.top);
    return {
      headingNavigationOverlap: overlaps(heading, navigation),
      navigationActionsOverlap: overlaps(navigation, actions),
      documentFits: document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    };
  });
  expect(desktopHeader).toEqual({ headingNavigationOverlap: false, navigationActionsOverlap: false, documentFits: true });

  await page.setViewportSize({ width: 1440, height: 900 });
  const compactHeaderRows = await page.locator(".admin-data-header").evaluate((header) => {
    const top = (selector: string) => Math.round(header.querySelector<HTMLElement>(selector)?.getBoundingClientRect().top ?? -1);
    return [top(".admin-data-heading"), top(".admin-dataset-tabs"), top(".admin-user")];
  });
  expect(Math.max(...compactHeaderRows) - Math.min(...compactHeaderRows)).toBeLessThanOrEqual(16);
});

test("退出登录后返回网站主页面", async ({ page }) => {
  await openAdmin(page);
  await page.getByRole("button", { name: "退出", exact: true }).click();
  await expect(page).toHaveURL(baseUrl + "/");
});

test("单位后台移除保存视图和最近访问并保留原子批量归档", async ({ page }) => {
  const item = {
    id: "org-batch", name: "批量操作演示单位", organization_type: "企业", industry: "演示行业",
    customer_status: "潜在客户", review_status: "待核验", inclusion_reason: "虚构测试数据",
    is_sports_exception: false, parent_group: null, website: null, unified_social_credit_code: null,
    recent_follow_up_at: null, recent_follow_up_content: null, follow_up_owner: null,
    cooperation_intent: null, cooperation_level: null, notes: null, archived_at: null, version: 1,
    sites: [], evidences: [], contacts: [], opportunities: [], sales_projects: [],
    created_at: "2026-08-20T00:00:00+08:00", updated_at: "2026-08-20T00:00:00+08:00",
  };
  let batchPayload: Record<string, unknown> | null = null;

  await installAdminApi(page);
  await page.route("**/api/v1/organizations**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname.endsWith("/filters")) return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ organization_types: ["企业"], customer_statuses: ["潜在客户"], review_statuses: ["待核验"], provinces: [], cities: [], districts: [] }) });
    if (url.pathname.endsWith("/batch") && request.method() === "POST") {
      batchPayload = request.postDataJSON() as Record<string, unknown>;
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ updated: 1 }) });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [item], total: 1, page: 1, page_size: Number(url.searchParams.get("page_size") ?? 10) }) });
  });
  await page.goto(adminUrl, { waitUntil: "networkidle" });

  await expect(page.locator(".organization-preference-bar")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "保存当前" })).toHaveCount(0);

  await page.getByLabel("选择批量操作演示单位").check();
  await expect(page.getByLabel("单位批量操作")).toContainText("已选择 1 条");
  await page.getByRole("button", { name: "批量归档" }).click();
  await page.getByRole("dialog", { name: "批量归档单位？" }).getByRole("button", { name: "确认归档" }).click();
  await expect(page.getByRole("status")).toContainText("已更新 1 条记录");
  expect(batchPayload).toEqual({ ids: ["org-batch"], action: "archive" });
});

test("优纳特成交项目明细可在单位后台完整修改", async ({ page }) => {
  const captured: { patchPayload?: Record<string, unknown> } = {};
  const timestamp = "2026-08-27T08:00:00+08:00";
  const organization = {
    id: "org-order", name: "成交编辑演示单位", organization_type: "企业", industry: "演示行业",
    customer_status: "已成交客户", review_status: "已核验", inclusion_reason: null, is_sports_exception: false,
    parent_group: null, website: null, unified_social_credit_code: null, recent_follow_up_at: null,
    recent_follow_up_content: null, follow_up_owner: null, cooperation_intent: null, cooperation_level: null,
    notes: null, archived_at: null, version: 1, evidences: [], contacts: [], opportunities: [],
    sites: [{ id: "site-order", site_name: "主地点", raw_address: null, address: "演示路 1 号", province: "江苏省", city: "苏州市", district: null, amap_adcode: null, geocode_status: "已定位", geocode_confidence: 90, longitude: 120.58, latitude: 31.3, is_primary: true }],
    sales_projects: [{ id: "project-order", opportunity_id: null, salesperson_id: null, name: "演示成交项目", contract_amount: "2500.00", unit_price: "1250.00", quantity: "2.000", supplier_name: "原供应商", specification_model: "SPEC-A", province: "江苏省", city: "苏州市", signed_at: "2026-08-20", project_detail: "仅用于浏览器测试", products: [{ id: "project-product-1", product_name: "演示检测产品", brand: "原品牌", specification_model: "SPEC-A", unit_price: "1250.00", quantity: "2.000", line_total: "2500.00" }] }],
    created_at: timestamp, updated_at: timestamp,
  };

  await installAdminApi(page);
  await page.route("**/api/v1/organizations**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.pathname.endsWith("/filters")) return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ organization_types: ["企业"], customer_statuses: ["已成交客户"], review_statuses: ["已核验"], provinces: ["江苏省"], cities: [], districts: [], salespeople: [{ id: "sales-1", employee_code: "XS001", display_name: "演示销售", is_active: true }] }) });
    if (url.pathname.endsWith("/org-order") && request.method() === "PATCH") {
      captured.patchPayload = request.postDataJSON() as Record<string, unknown>;
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(organization) });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [organization], total: 1, page: 1, page_size: 10 }) });
  });
  await page.goto(adminUrl, { waitUntil: "networkidle" });

  await page.getByRole("listitem").filter({ hasText: "成交编辑演示单位" }).getByRole("button", { name: "修改" }).click();
  const dialog = page.getByRole("dialog", { name: "修改单位档案" });
  const order = dialog.locator(".organization-edit-record").filter({ hasText: "成交项目 1" });
  await expect(order.getByLabel("品牌")).toHaveValue("原品牌");
  await expect(order.getByLabel("产品规格")).toHaveValue("SPEC-A");
  await expect(order.getByLabel("单价（元）")).toHaveValue("1250.00");
  await expect(order.getByLabel("数量")).toHaveValue("2.000");
  await expect(order.getByLabel("供应商")).toHaveValue("原供应商");
  await expect(order.getByLabel("省份")).toHaveValue("江苏省");
  await expect(order.getByLabel("城市")).toHaveValue("苏州市");

  await order.getByLabel("品牌").fill("更新品牌");
  await order.getByLabel("产品规格").fill("SPEC-B");
  await order.getByLabel("单价（元）").fill("1300.50");
  await order.getByLabel("数量").fill("3.5");
  await order.getByLabel("供应商").fill("更新供应商");
  await order.getByLabel("省份").fill("浙江省");
  await order.getByLabel("城市").fill("杭州市");
  await order.getByLabel("负责销售").selectOption("sales-1");
  await dialog.getByRole("button", { name: "保存修改" }).click();

  await expect.poll(() => captured.patchPayload).toBeDefined();
  const salesProjects = captured.patchPayload?.sales_projects as Array<Record<string, unknown>>;
  expect(salesProjects[0]).toMatchObject({
    unit_price: 1300.5, quantity: 3.5, supplier_name: "更新供应商", specification_model: "SPEC-B",
    province: "浙江省", city: "杭州市", salesperson_id: "sales-1",
  });
  expect((salesProjects[0].products as Array<Record<string, unknown>>)[0]).toMatchObject({ brand: "更新品牌", specification_model: "SPEC-B" });
});

test("八个数据页统一显示分类、数量和分页布局", async ({ page }) => {
  await openAdmin(page);
  const tabs = page.getByRole("tablist", { name: "后台数据页面" }).getByRole("tab");
  await expect(tabs).toHaveCount(8);
  await expect(tabs.first()).toHaveAttribute("aria-selected", "true");
  const tabFrame = await page.locator(".admin-dataset-tabs").evaluate((element) => {
    const frame = element.getBoundingClientRect();
    const header = element.closest(".admin-data-header")?.getBoundingClientRect();
    return {
      frameWidth: frame.width,
      buttonWidth: Array.from(element.querySelectorAll("button")).reduce((total, button) => total + button.getBoundingClientRect().width, 0),
      centerOffset: header ? Math.abs(frame.left + frame.width / 2 - (header.left + header.width / 2)) : Number.POSITIVE_INFINITY,
    };
  });
  expect(tabFrame.frameWidth - tabFrame.buttonWidth).toBeLessThanOrEqual(12);
  expect(tabFrame.centerOffset).toBeLessThanOrEqual(1);
  await expect(page.getByRole("navigation", { name: "单位列表分页" })).toContainText("上一页");

  const expectedCategories = new Map([
    ["销售与渠道", 4],
  ]);
  for (const [tab, count] of expectedCategories) {
    await page.getByRole("tab", { name: tab, exact: true }).click();
    const selector = page.getByLabel("选择数据分类");
    await expect(selector.locator("option")).toHaveCount(count);
    await expect(page.getByRole("navigation", { name: /分页/ })).toContainText(/第 1 \/ 1 页/);
    await expect(page.getByLabel("每页显示记录数")).toHaveValue("10");
    if (tab === "销售与渠道") {
      await expect(selector.locator("option")).toHaveText(["销售常驻点", "经销商", "代理商", "合作伙伴"]);
      await selector.selectOption({ label: "代理商" });
      await expect(page.getByText("演示代理商", { exact: true })).toBeVisible();
      await expect(page.getByText("演示经销商", { exact: true })).toHaveCount(0);
    }
  }
  await page.getByRole("tab", { name: "同行", exact: true }).click();
  await expect(page.getByLabel("选择数据分类")).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "同行列表分页" })).toContainText(/第 1 \/ 1 页/);
  await expect(page.getByLabel("每页显示同行数")).toHaveValue("10");
  await expect(page.getByRole("row").filter({ hasText: "演示同行" })).toContainText("¥260,000.5");
  const competitorTableFits = await page.locator(".competitor-admin-table").evaluate((element) => element.scrollWidth <= element.clientWidth);
  expect(competitorTableFits).toBe(true);
  if (process.env.ADMIN_COMPETITOR_LIST_SCREENSHOT) await page.screenshot({ path: process.env.ADMIN_COMPETITOR_LIST_SCREENSHOT, fullPage: true });
  await page.getByRole("tab", { name: "客户集团", exact: true }).click();
  await expect(page.getByLabel("选择数据分类")).toHaveCount(0);
  await expect(page.getByRole("navigation", { name: "客户集团列表分页" })).toContainText(/第 1 \/ 1 页/);
  await expect(page.getByLabel("每页显示客户集团数")).toHaveValue("10");
  const customerGroupTableFits = await page.locator(".customer-group-admin-table").evaluate((element) => element.scrollWidth <= element.clientWidth);
  expect(customerGroupTableFits).toBe(true);
  await page.getByRole("tab", { name: "销售", exact: true }).click();
  await expect(page.getByLabel("选择数据分类")).toHaveCount(0);
  const salesTabCenterOffset = await page.locator(".admin-dataset-tabs").evaluate((element) => {
    const frame = element.getBoundingClientRect();
    const header = element.closest(".admin-data-header")?.getBoundingClientRect();
    return header ? Math.abs(frame.left + frame.width / 2 - (header.left + header.width / 2)) : Number.POSITIVE_INFINITY;
  });
  expect(salesTabCenterOffset).toBeLessThanOrEqual(1);
  await expect(page.getByRole("navigation", { name: "销售人员列表分页" })).toContainText(/第 1 \/ 1 页/);
  await expect(page.getByLabel("每页显示销售人员数")).toHaveValue("10");
  const salespersonHeaders = page.locator(".salesperson-admin-table").getByRole("columnheader");
  await expect(salespersonHeaders.last()).toHaveText("操作");
  await expect(page.locator(".salesperson-admin-table").getByRole("columnheader", { name: "状态" })).toHaveCount(0);
  const salespersonTableFits = await page.locator(".salesperson-admin-table").evaluate((element) => element.scrollWidth <= element.clientWidth);
  expect(salespersonTableFits).toBe(true);
  if (process.env.ADMIN_UI_DESKTOP_SCREENSHOT) await page.screenshot({ path: process.env.ADMIN_UI_DESKTOP_SCREENSHOT, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  const mobileSalespersonListFits = await page.locator(".salesperson-admin-table").evaluate((element) => ({
    documentFits: document.documentElement.scrollWidth <= document.documentElement.clientWidth,
    tableFits: element.scrollWidth <= element.clientWidth,
  }));
  expect(mobileSalespersonListFits).toEqual({ documentFits: true, tableFits: true });
});

test("典型案例保持单一省份列表并按需打开完整详情", async ({ page }) => {
  await openAdmin(page);
  await page.getByRole("tab", { name: "典型案例", exact: true }).click();
  await expect(page.getByRole("heading", { name: "31 个省份" })).toBeVisible();
  await expect(page.getByLabel("案例配置统计")).toHaveText("0已上线1草稿30未配置");
  await expect(page.getByText("列表仅展示状态摘要；点击任一省份后维护全部案例细节。")).toHaveCount(0);
  await expect(page.locator(".case-admin-table .admin-data-row")).toHaveCount(3);
  await expect(page.getByText("等待创建案例")).toBeVisible();
  if (process.env.ADMIN_CASE_LIST_SCREENSHOT) await page.screenshot({ path: process.env.ADMIN_CASE_LIST_SCREENSHOT, fullPage: true });

  const zhejiangRow = page.locator(".case-admin-table .admin-data-row").filter({ hasText: "浙江省" });
  await zhejiangRow.getByRole("button", { name: "打开详情" }).click();
  await expect(page.getByRole("heading", { name: "浙江省典型案例" })).toBeVisible();
  await expect(page.getByLabel("省份")).toBeDisabled();
  await expect(page.getByLabel(/案例标题/)).toHaveValue("研发中心分析平台一期");
  await page.getByLabel("案例摘要").fill("更新后的虚构案例摘要");
  await page.getByRole("button", { name: "保存草稿" }).click();
  await expect(page.getByRole("status")).toContainText("已保存浙江省案例草稿");
  if (process.env.ADMIN_CASE_DETAIL_SCREENSHOT) await page.screenshot({ path: process.env.ADMIN_CASE_DETAIL_SCREENSHOT, fullPage: true });
  await page.getByRole("button", { name: "返回省份列表" }).click();
  await expect(page.getByText("北京市")).toBeVisible();
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
});

test("销售人员主档集成分级覆盖范围、销售活动和二次确认删除", async ({ page }) => {
  await openAdmin(page);
  await page.getByRole("tab", { name: "销售", exact: true }).click();
  const initialRow = page.getByRole("row").filter({ hasText: "演示销售" });
  await expect(initialRow).toContainText("杭州市（市）");
  await expect(initialRow).toContainText("¥88,000");
  await expect(initialRow).toContainText("拜访 3");
  await expect(initialRow).not.toContainText("在职启用");
  await initialRow.getByRole("button", { name: "修改" }).click();
  const legacyDialog = page.getByRole("dialog", { name: "管理 演示销售" });
  const legacyScope = legacyDialog.locator(".organization-edit-record").filter({ hasText: "覆盖范围 1" });
  await expect(legacyScope.getByLabel(/省份/)).toHaveValue("浙江");
  await legacyDialog.getByRole("button", { name: "关闭销售人员档案" }).click();

  await page.getByRole("button", { name: "添加销售人员" }).click();
  const addDialog = page.getByRole("dialog", { name: "添加销售人员" });
  await expect(addDialog.getByRole("heading", { name: "覆盖范围" })).toBeVisible();
  await expect(addDialog.getByRole("heading", { name: "销售活动" })).toBeVisible();
  await addDialog.getByLabel(/员工编号/).fill("XS002");
  await addDialog.getByLabel(/姓名/).fill("新增销售");
  await addDialog.getByLabel(/Pin 经度/).fill("121.47");
  await addDialog.getByLabel(/Pin 纬度/).fill("31.23");
  await addDialog.getByRole("button", { name: "新增覆盖范围" }).click();
  const coverageRecord = addDialog.locator(".organization-edit-record").filter({ hasText: "覆盖范围 1" });
  await coverageRecord.getByLabel("覆盖层级 1").selectOption("大区");
  await coverageRecord.getByLabel(/大区/).selectOption("东区");
  await expect(coverageRecord).toContainText("江苏、安徽、上海、山东、河南");
  await addDialog.getByRole("button", { name: "新增销售活动" }).click();
  const activityRecord = addDialog.locator(".organization-edit-record").filter({ hasText: "销售活动 1" });
  await activityRecord.getByLabel(/发生时间/).fill("2026-08-17T10:30");
  await activityRecord.getByLabel(/^省份/).fill("上海市");
  await activityRecord.getByLabel(/^城市/).fill("上海市");
  await activityRecord.getByLabel(/高德行政区编码/).fill("310100");
  await addDialog.getByRole("button", { name: "添加销售人员" }).click();
  await expect(page.getByRole("row").filter({ hasText: "新增销售" })).toBeVisible();

  const newRow = page.getByRole("row").filter({ hasText: "新增销售" });
  await newRow.getByRole("button", { name: "修改" }).click();
  const editDialog = page.getByRole("dialog", { name: "管理 新增销售" });
  await expect(editDialog.getByText("覆盖范围 1", { exact: true })).toBeVisible();
  await expect(editDialog.getByText("销售活动 1", { exact: true })).toBeVisible();
  await editDialog.getByLabel(/姓名/).fill("更新销售");
  await editDialog.getByRole("button", { name: "保存完整档案" }).click();
  await expect(page.getByRole("row").filter({ hasText: "更新销售" })).toBeVisible();

  const updatedRow = page.getByRole("row").filter({ hasText: "更新销售" });
  await updatedRow.getByRole("button", { name: "删除" }).click();
  const deleteDialog = page.getByRole("dialog", { name: "确认删除销售人员？" });
  await expect(deleteDialog).toContainText("永久删除");
  await deleteDialog.getByRole("button", { name: "确认删除" }).click();
  await expect(page.getByRole("row").filter({ hasText: "更新销售" })).toHaveCount(0);
});

test("客户集团主档集成总部、分支和二次确认删除", async ({ page }) => {
  await openAdmin(page);
  await page.getByRole("tab", { name: "客户集团", exact: true }).click();
  const initialRow = page.getByRole("row").filter({ hasText: "演示客户集团" });
  await expect(initialRow).toContainText("演示集团总部");
  await expect(initialRow).toContainText("分支 1");
  await expect(initialRow).toContainText("¥88,000");
  if (process.env.ADMIN_GROUP_UI_SCREENSHOT) await page.screenshot({ path: process.env.ADMIN_GROUP_UI_SCREENSHOT, fullPage: true });

  await page.getByRole("button", { name: "添加客户集团" }).click();
  const addDialog = page.getByRole("dialog", { name: "添加客户集团" });
  await expect(addDialog.getByRole("heading", { name: "总部与分支" })).toBeVisible();
  await addDialog.getByLabel(/集团名称/).fill("新增客户集团");
  const headquartersRecord = addDialog.locator(".customer-group-unit-record").filter({ hasText: "集团总部" });
  await headquartersRecord.getByLabel(/单位名称/).fill("新增集团总部");
  await headquartersRecord.getByLabel(/详细地址/).fill("上海市演示路 1 号");
  await headquartersRecord.getByLabel(/省份/).fill("上海市");
  await headquartersRecord.getByLabel(/城市/).fill("上海市");
  await addDialog.getByRole("button", { name: "新增分支单位" }).click();
  const branchRecord = addDialog.locator(".customer-group-unit-record").filter({ hasText: "分支单位 1" });
  await branchRecord.getByLabel(/单位名称/).fill("新增集团分支");
  await branchRecord.getByLabel(/详细地址/).fill("江苏省演示路 2 号");
  await branchRecord.getByLabel(/省份/).fill("江苏省");
  await branchRecord.getByLabel(/城市/).fill("南京市");
  await addDialog.getByRole("button", { name: "添加客户集团" }).click();
  await expect(page.getByRole("row").filter({ hasText: "新增客户集团" })).toBeVisible();

  const newRow = page.getByRole("row").filter({ hasText: "新增客户集团" });
  await newRow.getByRole("button", { name: "修改" }).click();
  const editDialog = page.getByRole("dialog", { name: "管理 新增客户集团" });
  await expect(editDialog.locator(".customer-group-unit-record").nth(0).getByLabel(/单位名称/)).toHaveValue("新增集团总部");
  await expect(editDialog.locator(".customer-group-unit-record").nth(1).getByLabel(/单位名称/)).toHaveValue("新增集团分支");
  await editDialog.getByLabel(/集团名称/).fill("更新客户集团");
  await editDialog.getByRole("button", { name: "保存完整档案" }).click();
  await expect(page.getByRole("row").filter({ hasText: "更新客户集团" })).toBeVisible();

  const updatedRow = page.getByRole("row").filter({ hasText: "更新客户集团" });
  await updatedRow.getByRole("button", { name: "删除" }).click();
  const deleteDialog = page.getByRole("dialog", { name: "确认删除客户集团？" });
  await expect(deleteDialog).toContainText("总部、1 个分支单位");
  await deleteDialog.getByRole("button", { name: "确认删除" }).click();
  await expect(page.getByRole("row").filter({ hasText: "更新客户集团" })).toHaveCount(0);
});

test("同行主列表按需进入据点、交易关联和强势区域详情", async ({ page }) => {
  await openAdmin(page);
  await page.getByRole("tab", { name: "同行", exact: true }).click();
  const competitorRow = page.getByRole("row").filter({ hasText: "演示同行" });
  await competitorRow.getByRole("button", { name: "修改", exact: true }).click();
  await expect(page.getByRole("heading", { name: "演示同行", exact: true })).toBeVisible();
  const detailHeader = page.locator(".competitor-detail-header");
  const summary = detailHeader.getByLabel("同行档案摘要");
  await expect(summary).toContainText("1 个据点");
  const headerLayout = await detailHeader.evaluate((element) => {
    const main = element.querySelector(".competitor-detail-main");
    const actions = element.querySelector(".organization-row-actions");
    const identityRect = element.querySelector(".competitor-detail-identity")?.getBoundingClientRect();
    const summaryRect = element.querySelector(".competitor-summary-strip")?.getBoundingClientRect();
    const mainRect = main?.getBoundingClientRect();
    const actionsRect = actions?.getBoundingClientRect();
    const headerRect = element.getBoundingClientRect();
    const editRect = Array.from(element.querySelectorAll("button")).find((button) => button.textContent?.includes("修改主档"))?.getBoundingClientRect();
    return {
      summaryInsideMain: element.querySelector(".competitor-summary-strip")?.parentElement === main,
      summaryBesideIdentity: Boolean(identityRect && summaryRect && summaryRect.left >= identityRect.right && Math.abs(summaryRect.top - identityRect.top) < 16),
      actionsStayRight: Boolean(mainRect && actionsRect && editRect && mainRect.right <= actionsRect.left && editRect.left >= actionsRect.left),
      summaryStartsLeft: Boolean(summaryRect && summaryRect.left < headerRect.left + headerRect.width / 2),
    };
  });
  expect(headerLayout).toEqual({ summaryInsideMain: true, summaryBesideIdentity: true, actionsStayRight: true, summaryStartsLeft: true });
  await expect(page.getByText("演示同行总部", { exact: true })).toBeVisible();

  await page.getByRole("tab", { name: "成交单位与交易" }).click();
  const customerRow = page.getByRole("row").filter({ hasText: "演示成交单位" });
  await expect(customerRow).toBeVisible();
  await customerRow.getByRole("button", { name: "交易与关联" }).click();
  await expect(page.getByText("演示成交项目", { exact: true })).toBeVisible();
  await expect(page.getByText("台式气相色谱仪", { exact: true })).toBeVisible();
  await page.getByRole("row").filter({ hasText: "演示成交项目" }).getByRole("button", { name: "修改" }).click();
  const dealDialog = page.getByRole("dialog", { name: "编辑同行成交记录" });
  await expect(dealDialog.getByLabel(/产品名称/)).toHaveValue("台式气相色谱仪");
  await expect(dealDialog.getByLabel(/^品牌$/)).toHaveValue("虚构品牌甲");
  await expect(dealDialog.getByLabel(/产品规格/)).toHaveValue("GC-DEMO-01");
  await expect(dealDialog.getByLabel(/产品图片路径或 URL/)).toHaveValue("/cases/jiangsu-lab.webp");
  await expect(dealDialog.getByLabel(/单价（元）/)).toHaveValue("130000.25");
  await expect(dealDialog.getByLabel(/数量/)).toHaveValue("2.000");
  await expect(dealDialog.getByLabel(/供应商名称/)).toHaveValue("虚构仪器供应商");
  await dealDialog.getByRole("button", { name: "取消" }).click();
  await expect(page.getByText("演示目标单位", { exact: true })).toBeVisible();

  await page.getByRole("tab", { name: "强势区域" }).click();
  await expect(page.getByText("虚构测试依据", { exact: true })).toHaveCount(0);
  await expect(page.getByText("公开地图计算结果", { exact: true })).toBeVisible();
  await expect(page.getByText(/得分 88.50/)).toBeVisible();
  if (process.env.ADMIN_COMPETITOR_DETAIL_SCREENSHOT) await page.screenshot({ path: process.env.ADMIN_COMPETITOR_DETAIL_SCREENSHOT, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  const mobileHeaderFits = await detailHeader.evaluate((element) => ({
    summaryInsideMain: element.querySelector(".competitor-summary-strip")?.parentElement?.classList.contains("competitor-detail-main"),
    documentFits: document.documentElement.scrollWidth <= document.documentElement.clientWidth,
  }));
  expect(mobileHeaderFits).toEqual({ summaryInsideMain: true, documentFits: true });
  await page.getByRole("button", { name: "返回同行列表" }).click();
  await expect(page.getByRole("navigation", { name: "同行列表分页" })).toBeVisible();
});

test("空数据、接口错误和移动端横向导航均有安全边界", async ({ page }) => {
  await openAdmin(page);
  await page.route("**/api/v1/admin-customer-groups**", (route) => route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [], total: 0, page: 1, page_size: 10 }) }));
  await page.getByRole("tab", { name: "客户集团", exact: true }).click();
  await expect(page.getByText(/暂无匹配客户集团/)).toBeVisible();

  await page.route("**/api/v1/admin-competitors**", (route) => route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "同行数据暂不可用" }) }));
  await page.getByRole("tab", { name: "同行", exact: true }).click();
  await expect(page.locator(".admin-page-error")).toContainText("同行数据暂不可用");

  await page.setViewportSize({ width: 390, height: 844 });
  const metrics = await page.evaluate(() => {
    const tabs = document.querySelector<HTMLElement>(".admin-dataset-tabs");
    const list = document.querySelector<HTMLElement>(".admin-data-list-card");
    const tabsRect = tabs?.getBoundingClientRect();
    const listRect = list?.getBoundingClientRect();
    return {
      documentFits: document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      tabsFitViewport: Boolean(tabsRect && tabsRect.left >= 0 && tabsRect.right <= window.innerWidth),
      listFitsViewport: Boolean(listRect && listRect.left >= 0 && listRect.right <= window.innerWidth),
    };
  });
  expect(metrics).toEqual({ documentFits: true, tabsFitViewport: true, listFitsViewport: true });

  if (process.env.ADMIN_UI_SCREENSHOT) await page.screenshot({ path: process.env.ADMIN_UI_SCREENSHOT, fullPage: true });
});

test("地图与列表切换按首条偏移换算页码，2 万条数据不会跳批次或越界", async ({ page }) => {
  await openAdmin(page);
  await page.route("**/api/v1/organizations**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/map-points")) return route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    if (url.pathname.endsWith("/filters")) return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ organization_types: [], customer_statuses: [], review_statuses: [], provinces: [], cities: [], districts: [] }) });
    const requestedPage = Number(url.searchParams.get("page") ?? 1);
    const requestedPageSize = Number(url.searchParams.get("page_size") ?? 10);
    const item = { id: `org-${requestedPage}`, name: `分页单位 ${requestedPage}`, organization_type: "企业", customer_status: "潜在客户", review_status: "待核验", is_sports_exception: false, sites: [] };
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [item], total: 20000, page: requestedPage, page_size: requestedPageSize }) });
  });

  await page.getByLabel("每页显示单位数").selectOption("100");
  await page.getByRole("navigation", { name: "单位列表分页" }).getByRole("button", { name: "下一页" }).click();
  await expect(page.getByRole("navigation", { name: "单位列表分页" })).toContainText("第 2 / 200 页");
  await page.getByRole("button", { name: "显示地图" }).click();
  await expect(page.getByRole("navigation", { name: "单位列表分页" })).toContainText("第 11 / 2000 页");
  await page.getByRole("button", { name: "关闭地图" }).click();
  await expect(page.getByRole("navigation", { name: "单位列表分页" })).toContainText("第 2 / 200 页");
});

test("销售详情只采用最后一次点击，且活动单位候选在聚焦前不批量请求", async ({ page }) => {
  await openAdmin(page);
  let optionRequests = 0;
  await page.route("**/api/v1/admin-data/organizations/options**", async (route) => {
    optionRequests += 1;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify([{ value: "org-1", label: "演示目标单位" }]) });
  });
  await page.route("**/api/v1/admin-salespeople**", async (route) => {
    const url = new URL(route.request().url());
    const id = url.pathname.split("/").at(-1);
    const listItems = [
      { ...resourceItems.salespeople[0], id: "sales-slow", employee_code: "XS101", display_name: "慢速销售", coverage_scopes: [], coverage_scope_total: 0, actual_sales_amount: "0.00", visit_count: 0, demonstration_count: 0, marketing_event_count: 0 },
      { ...resourceItems.salespeople[0], id: "sales-fast", employee_code: "XS102", display_name: "快速销售", coverage_scopes: [], coverage_scope_total: 0, actual_sales_amount: "0.00", visit_count: 0, demonstration_count: 0, marketing_event_count: 0 },
    ];
    if (id === "admin-salespeople") return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: listItems, total: 2, page: 1, page_size: 10 }) });
    const item = listItems.find((candidate) => candidate.id === id)!;
    if (id === "sales-slow") await new Promise((resolve) => setTimeout(resolve, 280));
    const profile = { ...item, coverage_center_longitude: 116.4, coverage_center_latitude: 39.9, is_active: true, coverage_scopes: [], activities: [{ id: `${id}-activity`, organization_id: null, organization_name: null, activity_type: "拜访", occurred_at: "2026-08-17T09:00:00+08:00", province: "北京市", city: "北京市", amap_adcode: "110100", notes: null }] };
    try { await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(profile) }); } catch { /* 被新请求取消即为预期。 */ }
  });

  await page.getByRole("tab", { name: "销售", exact: true }).click();
  await page.getByRole("row").filter({ hasText: "慢速销售" }).getByRole("button", { name: "修改" }).click();
  await page.getByRole("row").filter({ hasText: "快速销售" }).getByRole("button", { name: "修改" }).click();
  const dialog = page.getByRole("dialog", { name: "管理 快速销售" });
  await expect(dialog).toBeVisible();
  await page.waitForTimeout(350);
  await expect(page.getByRole("dialog", { name: "管理 慢速销售" })).toHaveCount(0);
  expect(optionRequests).toBe(0);
  await dialog.getByLabel("搜索关联目标单位").focus();
  await expect.poll(() => optionRequests).toBe(1);
});

test("同行子资源修改后重新计算公开强势区域", async ({ page }) => {
  await openAdmin(page);
  let computedRequests = 0;
  await page.route("**/api/v1/public/competitors/competitor-1", async (route) => {
    computedRequests += 1;
    const score = computedRequests === 1 ? "88.50" : "77.00";
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ id: "competitor-1", name: "演示同行", color: "#25846F", description: "虚构同行", summary: { site_count: 1, customer_count: 1, linked_customer_count: 1, deal_count: 1, total_amount: "260000.50", strong_region_count: 1 }, sites: [], customers: [], strength_regions: [{ id: `computed-${computedRequests}`, region_level: "省", province: "江苏省", city: null, strength_level: "强", source_type: "公开信息", source_reference: "自动聚合", source_url: null, confidence: "高", basis: "计算结果", score, site_count: 1, customer_count: 1, total_amount: "260000.50" }] }) });
  });

  await page.getByRole("tab", { name: "同行", exact: true }).click();
  await page.getByRole("row").filter({ hasText: "演示同行" }).getByRole("button", { name: "修改", exact: true }).click();
  await page.getByRole("tab", { name: "强势区域" }).click();
  await expect(page.getByText(/得分 88.50/)).toBeVisible();
  await page.getByRole("tab", { name: "基本资料与据点" }).click();
  await page.getByRole("row").filter({ hasText: "演示同行总部" }).getByRole("button", { name: "修改" }).click();
  await page.getByRole("dialog").getByRole("button", { name: "保存修改" }).click();
  await page.getByRole("tab", { name: "强势区域" }).click();
  await expect(page.getByText(/得分 77.00/)).toBeVisible();
  expect(computedRequests).toBe(2);
});

test("单位筛选和详情抽屉具备完整键盘语义", async ({ page }) => {
  await openAdmin(page);
  const listItem = { id: "org-a11y", name: "无障碍演示单位", organization_type: "企业", customer_status: "潜在客户", review_status: "待核验", is_sports_exception: false, sites: [{ id: "site-a11y", is_primary: true, province: "浙江省", city: "杭州市", district: "西湖区", address: "演示路 1 号", geocode_status: "已定位", longitude: 120.1, latitude: 30.2 }] };
  const detail = { ...listItem, industry: "演示行业", inclusion_reason: "仅用于无障碍测试", parent_group: null, evidences: [], contacts: [], opportunities: [], sales_projects: [], notes: null };
  await page.route("**/api/v1/organizations**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/filters")) return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ organization_types: ["企业"], customer_statuses: ["潜在客户"], review_statuses: ["待核验"], provinces: ["浙江省"], cities: [], districts: [] }) });
    if (url.pathname.endsWith("/org-a11y")) return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(detail) });
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [listItem], total: 1, page: 1, page_size: Number(url.searchParams.get("page_size") ?? 10) }) });
  });

  const search = page.getByLabel("搜索单位名称");
  await search.focus();
  const focusStyle = await search.locator("..").evaluate((element) => getComputedStyle(element).outlineStyle);
  expect(focusStyle).not.toBe("none");
  await page.getByLabel("每页显示单位数").selectOption("25");
  await expect(page.getByRole("list", { name: "单位记录" })).toBeVisible();
  await expect(page.locator(".organization-table").getByRole("table")).toHaveCount(0);

  const detailButton = page.getByRole("button", { name: /查看无障碍演示单位详情/ });
  await detailButton.click();
  const dialog = page.getByRole("dialog", { name: "单位详情" });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByRole("button", { name: "关闭详情" })).toBeFocused();
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(detailButton).toBeFocused();
});

test("成交订单页可按同行和产品筛选并展开多产品详情", async ({ page }) => {
  /** 锁定统一订单页的成功、筛选和产品明细展示状态。 */
  await openAdmin(page);
  await page.getByRole("tab", { name: "成交订单", exact: true }).click();
  await expect(page.getByRole("heading", { name: "成交订单", exact: true })).toBeVisible();
  await expect(page.getByText("订单数据库", { exact: true })).toHaveCount(0);
  await expect(page.getByText(/统一查看优纳特和同行订单/)).toHaveCount(0);
  await expect(page.getByText("笔符合条件", { exact: true })).toHaveCount(0);
  await expect(page.locator(".admin-deal-count")).toHaveText("1");
  await page.getByLabel("订单归属").selectOption("competitor");
  await page.getByLabel("同行公司").selectOption("competitor-1");
  await page.getByPlaceholder("搜索产品名称").fill("色谱仪");
  await expect(page.getByText("演示成交项目", { exact: true })).toBeVisible();
  await page.getByText("查看产品与订单详情", { exact: true }).click();
  await expect(page.getByText(/台式气相色谱仪/)).toBeVisible();
  await expect(page.locator(".admin-deal-products").getByText("品牌：虚构品牌甲", { exact: true })).toBeVisible();
  await expect(page.locator(".admin-deal-detail-grid")).toContainText("成交单位");
  await expect(page.locator(".admin-deal-detail-grid")).toContainText("项目总价");
  await expect(page.getByText(/产品总价/)).toBeVisible();
});

test("成交订单页可直接新增优纳特订单并修改删除同行订单", async ({ page }) => {
  /** 验证统一页面复用公共数据库写入，且编辑合同保留完整多产品结构。 */
  let updatePayload: Record<string, unknown> | null = null;
  let uniteCreatePayload: Record<string, unknown> | null = null;
  let deleteRequests = 0;
  page.on("request", (request) => {
    const pathname = new URL(request.url()).pathname;
    if (pathname.endsWith("/admin-data/competitor_deals/deal-1") && request.method() === "PUT") updatePayload = request.postDataJSON() as Record<string, unknown>;
    if (pathname.endsWith("/admin-data/competitor_deals/deal-1") && request.method() === "DELETE") deleteRequests += 1;
    if (pathname.endsWith("/admin-deals/unite") && request.method() === "POST") uniteCreatePayload = request.postDataJSON() as Record<string, unknown>;
  });

  await openAdmin(page);
  await page.getByRole("tab", { name: "成交订单", exact: true }).click();
  const orderCard = page.locator(".admin-deal-list article").filter({ hasText: "演示成交项目" });
  const [titleBox, createBox, amountBox, actionsBox] = await Promise.all([
    page.getByRole("heading", { name: "成交订单", exact: true }).boundingBox(),
    page.getByRole("button", { name: "添加订单" }).boundingBox(),
    orderCard.locator(".admin-deal-amount>strong").boundingBox(),
    orderCard.locator(".admin-deal-row-actions").boundingBox(),
  ]);
  expect(createBox!.x).toBeGreaterThan(titleBox!.x + titleBox!.width);
  expect(actionsBox!.y).toBeGreaterThan(amountBox!.y);
  await orderCard.getByRole("button", { name: "修改" }).click();
  const editDialog = page.getByRole("dialog", { name: /修改演示成交项目/ });
  await editDialog.getByLabel(/项目名称/).fill("更新演示成交项目");
  await editDialog.getByRole("button", { name: "添加产品" }).click();
  const secondProduct = editDialog.locator(".admin-product-editor article").nth(1);
  await secondProduct.getByLabel(/产品名称/).fill("演示维护服务");
  await secondProduct.getByLabel(/^品牌$/).fill("虚构服务品牌");
  await secondProduct.getByLabel(/产品总价/).fill("5000");
  await editDialog.getByRole("button", { name: "保存修改" }).click();
  await expect(page.getByText("订单修改已保存", { exact: true })).toBeVisible();
  expect(updatePayload).not.toBeNull();
  const capturedUpdate = updatePayload as unknown as { data: { products: unknown[] } } | null;
  expect(capturedUpdate?.data.products).toHaveLength(2);

  const updatedCard = page.locator(".admin-deal-list article").filter({ hasText: "更新演示成交项目" });
  await updatedCard.getByRole("button", { name: "删除" }).click();
  const deleteDialog = page.getByRole("dialog", { name: "确认删除成交订单？" });
  await expect(deleteDialog).toContainText("2 条产品明细");
  await deleteDialog.getByRole("button", { name: "确认删除" }).click();
  await expect(page.getByText("成交订单已删除", { exact: true })).toBeVisible();
  expect(deleteRequests).toBe(1);

  await page.getByRole("button", { name: "添加订单" }).click();
  const createDialog = page.getByRole("dialog", { name: "添加成交订单" });
  await expect(createDialog.getByLabel("订单归属")).toHaveValue("unite");
  await createDialog.getByLabel("成交单位", { exact: true }).selectOption("org-1");
  await createDialog.getByLabel(/项目名称/).fill("新建优纳特订单");
  await createDialog.getByLabel(/项目总价/).fill("88000");
  await createDialog.getByLabel("负责销售", { exact: true }).selectOption("sales-1");
  const firstProduct = createDialog.locator(".admin-product-editor article").first();
  await firstProduct.getByLabel(/产品名称/).fill("优纳特演示产品");
  await firstProduct.getByLabel(/^品牌$/).fill("优纳特");
  await firstProduct.getByLabel(/产品总价/).fill("88000");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth)).toBe(true);
  const mobileDialogBox = await createDialog.boundingBox();
  expect(mobileDialogBox!.x).toBeGreaterThanOrEqual(0);
  expect(mobileDialogBox!.x + mobileDialogBox!.width).toBeLessThanOrEqual(390);
  await createDialog.getByRole("button", { name: "添加订单" }).click();
  await expect(page.getByText("成交订单已添加", { exact: true })).toBeVisible();
  expect(uniteCreatePayload).toMatchObject({ organization_id: "org-1", salesperson_id: "sales-1", project_name: "新建优纳特订单" });
  const capturedCreate = uniteCreatePayload as unknown as { products: unknown[] } | null;
  expect(capturedCreate?.products).toHaveLength(1);
});
