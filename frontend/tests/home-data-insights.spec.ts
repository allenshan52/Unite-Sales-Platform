/** 数据洞察浏览器验收：覆盖真实会话、账号范围、大区热力、省市下钻与 Excel 导出。 */
import { expect, test, type Page } from "@playwright/test";

const pageUrl = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3100";
const adminUsername = process.env.ADMIN_USERNAME;
const adminPassword = process.env.ADMIN_PASSWORD;

test.use({ launchOptions: { executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" } });

type ApiRegion = {
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
};

/** 构造一条后端区域聚合响应，数值单位保持为元。 */
function region(name: string, province: string, amountWan: number, rank: number, contribution: number, coordinates?: [number, number]): ApiRegion {
  return {
    id: name,
    name,
    province,
    city: name === province ? null : name,
    longitude: coordinates?.[0] ?? null,
    latitude: coordinates?.[1] ?? null,
    sales_amount: String(amountWan * 10_000),
    project_count: Math.max(1, Math.round(amountWan / 60)),
    pipeline_amount: String(Math.round(amountWan * 0.72) * 10_000),
    pipeline_count: 2,
    average_deal_amount: "600000.00",
    metric_value: String(amountWan * 10_000),
    contribution_percent: contribution.toFixed(1),
    rank,
    yoy_percent: "12.5",
    qoq_percent: "4.2",
  };
}

/** 根据查询范围返回稳定但季度排名不同的聚合响应。 */
function overviewFor(url: URL) {
  const year = Number(url.searchParams.get("year") ?? "2026");
  const period = url.searchParams.get("period") ?? "year";
  const province = url.searchParams.get("province");
  const city = url.searchParams.get("city");
  const scopeMode = url.searchParams.get("scope_mode") ?? "assigned";
  let regions: ApiRegion[];
  if (city && province) {
    regions = [];
  } else if (province === "江苏省") {
    regions = period === "q1"
      ? [region("南京市", province, 260, 1, 61, [118.7969, 32.0603]), region("苏州市", province, 166, 2, 39, [120.5853, 31.2989])]
      : [region("苏州市", province, 337, 1, 57, [120.5853, 31.2989]), region("南京市", province, 254, 2, 43, [118.7969, 32.0603])];
  } else if (province === "湖北省") {
    regions = [region("武汉市", province, 280, 1, 55, [114.3055, 30.5928]), region("宜昌市", province, 229, 2, 45, [111.2865, 30.6919])];
  } else if (province === "广西壮族自治区") {
    regions = [region("南宁市", province, 280, 1, 55, [108.3669, 22.817]), region("桂林市", province, 229, 2, 45, [110.2902, 25.2736])];
  } else if (province === "新疆维吾尔自治区") {
    regions = [region("乌鲁木齐市", province, 280, 1, 55, [87.6168, 43.8256]), region("昌吉回族自治州", province, 229, 2, 45, [87.3082, 44.0112])];
  } else if (period === "q1") {
    regions = [region("江苏省", "江苏省", 620, 1, 44), region("浙江省", "浙江省", 480, 2, 34), region("广东省", "广东省", 310, 3, 22)];
  } else if (period === "q3") {
    regions = [region("广东省", "广东省", 710, 1, 50), region("浙江省", "浙江省", 420, 2, 30), region("江苏省", "江苏省", 280, 3, 20)];
  } else {
    regions = [region("浙江省", "浙江省", 680, 1, 42), region("江苏省", "江苏省", 591, 2, 36), region("广东省", "广东省", 350, 3, 22)];
  }
  if (!province && !city) {
    const additional = [
      ["四川省", 250], ["新疆维吾尔自治区", 220], ["广西壮族自治区", 200], ["湖北省", 180],
      ["河南省", 160], ["福建省", 140], ["山东省", 120], ["吉林省", 90], ["辽宁省", 80],
    ] as const;
    regions = [...regions, ...additional.map(([name, amount], index) => region(name, name, amount, index + 4, 1))];
  }
  const totalWan = city ? 337 : regions.reduce((sum, item) => sum + Number(item.sales_amount) / 10_000, 0);
  return {
    year,
    period,
    metric: url.searchParams.get("metric") ?? "sales",
    available_years: [2026, 2025, 2024],
    scope: {
      level: city ? "city" : province ? "province" : "national",
      name: city ?? province ?? "全国",
      province,
      city,
      mode: scopeMode,
      visible_provinces: regions.map((item) => item.province),
      visible_regions: ["浙江区", "东区", "北区", "南区"],
    },
    aggregated_at: "2026-08-25T08:30:00Z",
    kpis: {
      sales_amount: String(totalWan * 10_000), sales_yoy_percent: "12.5", sales_qoq_percent: "4.2",
      project_count: 12, projects_yoy_percent: "9.1", projects_qoq_percent: "3.0",
      average_deal_amount: "630000.00", pipeline_amount: "8800000.00", pipeline_count: 7,
      active_region_count: city ? 1 : regions.length,
    },
    regions,
    macro_regions: [
      { id: "浙江区", name: "浙江区", provinces: ["浙江省", "江西省"], sales_amount: "6800000", project_count: 8, pipeline_amount: "3600000", pipeline_count: 4, metric_value: "6800000", contribution_percent: "32.0" },
      { id: "东区", name: "东区", provinces: ["江苏省", "安徽省", "上海市", "山东省", "河南省"], sales_amount: "8710000", project_count: 11, pipeline_amount: "4600000", pipeline_count: 5, metric_value: "8710000", contribution_percent: "41.0" },
      { id: "北区", name: "北区", provinces: ["吉林省", "辽宁省"], sales_amount: "1700000", project_count: 3, pipeline_amount: "900000", pipeline_count: 2, metric_value: "1700000", contribution_percent: "8.0" },
      { id: "南区", name: "南区", provinces: ["广东省", "福建省", "广西壮族自治区"], sales_amount: "6900000", project_count: 9, pipeline_amount: "3500000", pipeline_count: 4, metric_value: "6900000", contribution_percent: "19.0" },
    ],
    trend: Array.from({ length: 12 }, (_, index) => ({ month: index + 1, current_amount: String((index + 3) * 100_000), previous_amount: String((index + 2) * 90_000) })),
    signals: [
      { tone: "positive", title: "成交贡献居首", description: "实际销售额来自数据库聚合。" },
      { tone: "warning", title: "商机储备充足", description: "建议关注推进节奏。" },
    ],
    top_customers: Array.from({ length: city ? 3 : 10 }, (_, index) => ({
      rank: index + 1, name: `优纳特演示成交单位${index + 1}`, province: province ?? "浙江省", city: city ?? "杭州市",
      sales_amount: String((220 - index * 10) * 10_000), project_count: index % 2 + 1, latest_signed_at: `2026-0${(index % 8) + 1}-15`,
    })),
    stages: [
      { stage: "已识别", opportunity_count: 1, amount: "1000000.00", percent: "20.0" },
      { stage: "资格确认", opportunity_count: 1, amount: "1500000.00", percent: "30.0" },
      { stage: "商务谈判", opportunity_count: 1, amount: "2500000.00", percent: "50.0" },
    ],
  };
}

/** 为聚合读取和 Excel 导出安装确定性响应，登录与授权仍走真实服务。 */
async function mockInsightsApi(page: Page): Promise<void> {
  await page.route("**/api/v1/public/insights/**", (route) => {
    const url = new URL(route.request().url());
    if (url.pathname.endsWith("/export")) {
      return route.fulfill({ status: 200, contentType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", body: "xlsx" });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(overviewFor(url)) });
  });
}

/** 用完全虚构的管理员会话打开洞察页，让竞态用例不依赖真实数据库或登录限流。 */
async function openMockedInsights(page: Page): Promise<void> {
  await page.route("**/api/v1/auth/me", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      username: "insights_test", role: "超级管理员", salesperson_id: null,
      can_manage_users: true, can_manage_salespeople: true, coverage_scopes: [],
    }),
  }));
  await page.route("**/api/v1/public/organizations/**", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: route.request().url().includes("filters")
      ? JSON.stringify({ organization_types: [], customer_statuses: [], review_statuses: [], provinces: [], cities: [], districts: [] })
      : "[]",
  }));
  await page.goto(pageUrl, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: "数据洞察", exact: true }).click();
  await expect(page.getByRole("heading", { name: "专属区域经营洞察" })).toBeVisible();
}

/** 使用真实服务端会话进入数据洞察页。 */
async function loginAndOpenInsights(page: Page): Promise<void> {
  test.setTimeout(90_000);
  test.skip(!adminUsername || !adminPassword, "需要 ADMIN_USERNAME 与 ADMIN_PASSWORD 验收真实主站");
  await page.context().clearCookies();
  await page.goto(pageUrl, { waitUntil: "networkidle" });
  await page.getByLabel("账号").fill(adminUsername!);
  await page.getByLabel("密码").fill(adminPassword!);
  for (let attempt = 0; attempt < 4; attempt += 1) {
    await page.getByRole("button", { name: "进入网站" }).click();
    try {
      await page.locator(".topbar").waitFor({ state: "visible", timeout: 3_000 });
      break;
    } catch {
      if (!await page.getByText("登录请求过于频繁，请稍后重试", { exact: true }).isVisible() || attempt === 3) break;
      // 本文件保留真实登录边界；网关每 12 秒补充一个令牌，限流时按补充周期有限重试。
      await page.waitForTimeout(13_000);
    }
  }
  await expect(page.locator(".topbar")).toBeVisible();
  await page.getByRole("tab", { name: "数据洞察", exact: true }).click();
  await expect(page.getByRole("heading", { name: "专属区域经营洞察" })).toBeVisible();
  await expect(page.getByText("数据洞察 · 数据库实时聚合", { exact: true })).toBeVisible();
}

test("年份筛选、省市下钻和城市详情使用对应数据库聚合请求", async ({ page }) => {
  await mockInsightsApi(page);
  await loginAndOpenInsights(page);
  await page.getByRole("combobox", { name: "年份" }).selectOption("2025");
  await page.getByRole("combobox", { name: "统计期间" }).selectOption("q2");
  await page.locator('[data-insight-province="jiangsu"]').click();
  await expect(page.getByRole("heading", { name: "江苏省城市数据" })).toBeVisible();
  await page.getByRole("button", { name: "查看苏州市经营详情" }).click();
  await expect(page.getByRole("dialog", { name: "苏州市年度统计" })).toContainText("数据库聚合");
  await expect(page.getByRole("dialog")).toContainText("优纳特演示成交单位1");
});

test("页面只保留成交单位 Top 10 并下载真实 Excel", async ({ page }) => {
  await mockInsightsApi(page);
  await loginAndOpenInsights(page);
  await expect(page.getByRole("heading", { name: "Top 10 成交单位" })).toBeVisible();
  await expect(page.getByText("Top 10 成交项目")).toHaveCount(0);
  await expect(page.locator(".insight-customer-card tbody tr")).toHaveCount(10);
  const download = page.waitForEvent("download");
  await page.getByRole("button", { name: "导出报表" }).click();
  await expect((await download).suggestedFilename()).toContain("区域经营报表.xlsx");
});

test("顶部地图与全部省份清单等高且清单可滚动查看", async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 950 });
  await mockInsightsApi(page);
  await loginAndOpenInsights(page);
  const layout = await page.evaluate(() => {
    const mapCard = document.querySelector<HTMLElement>(".insight-map-card")!.getBoundingClientRect();
    const mapStage = document.querySelector<HTMLElement>(".insight-map-stage")!.getBoundingClientRect();
    const mapSvg = document.querySelector<SVGSVGElement>(".insight-map")!;
    const rankingCard = document.querySelector<HTMLElement>(".insight-ranking-card")!.getBoundingClientRect();
    const list = document.querySelector<HTMLElement>(".insight-ranking-list")!;
    const mapContent = mapSvg.querySelector<SVGGElement>("g")!;
    const box = mapContent.getBBox();
    const matrix = mapContent.getScreenCTM()!;
    const bottom = new DOMPoint(box.x + box.width, box.y + box.height).matrixTransform(matrix).y;
    return {
      mapHeight: mapCard.height,
      rankingHeight: rankingCard.height,
      listScrolls: list.scrollHeight > list.clientHeight,
      mapBottomGap: mapStage.bottom - bottom,
      svgContained: mapSvg.getBoundingClientRect().bottom <= mapStage.bottom,
    };
  });
  expect(layout.mapHeight).toBeCloseTo(layout.rankingHeight, 0);
  expect(layout.mapHeight).toBeCloseTo(585, 0);
  expect(layout.listScrolls).toBe(true);
  expect(layout.svgContained).toBe(true);
  expect(layout.mapBottomGap).toBeGreaterThanOrEqual(28);
});

test("季度切换同步改变省份金额和热度且不再展示区域排名", async ({ page }) => {
  await mockInsightsApi(page);
  await loginAndOpenInsights(page);
  const periodSelect = page.getByRole("combobox", { name: "统计期间" });
  const firstRegion = page.locator(".insight-ranking-list li:first-child button > span > b");
  await expect(page.getByText("区域排名", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("heading", { name: "全部省份数据" })).toBeVisible();
  await expect(page.locator(".insight-ranking-list li")).toHaveCount(12);
  await periodSelect.selectOption("q1");
  await expect(firstRegion).toHaveText("江苏省");
  const q1Width = await page.getByRole("button", { name: "查看浙江省详情" }).locator("em").getAttribute("style");
  await periodSelect.selectOption("q3");
  await expect(firstRegion).toHaveText("广东省");
  await expect(page.getByRole("button", { name: "查看浙江省详情" }).locator("em")).not.toHaveAttribute("style", q1Width ?? "");
  await periodSelect.selectOption("q2");
  await page.locator('[data-insight-province="jiangsu"]').click();
  await expect(firstRegion).toHaveText("苏州市");
  await periodSelect.selectOption("q1");
  await expect(firstRegion).toHaveText("南京市");
});

test("省内城市 Pin 固定清晰尺寸并支持直接切换省份", async ({ page }) => {
  await mockInsightsApi(page);
  await loginAndOpenInsights(page);
  const diameters: number[] = [];
  for (const provinceId of ["hubei", "guangxi-zhuang", "xinjiang-uygur"]) {
    await page.locator(`[data-insight-province="${provinceId}"]`).click();
    await expect(page.locator(".insight-city-dot")).toHaveCount(2);
    await page.waitForTimeout(500);
    const box = await page.locator(".insight-city-dot").first().boundingBox();
    expect(box).not.toBeNull();
    diameters.push(box!.width);
    if (provinceId === "xinjiang-uygur") {
      await expect(page.locator('[data-label-placement="above"]')).toHaveCount(1);
      await expect(page.locator('[data-label-placement="below"]')).toHaveCount(1);
    }
    await page.locator(".insight-map-back").click();
  }
  expect(Math.min(...diameters)).toBeGreaterThanOrEqual(23);
  expect(Math.max(...diameters) - Math.min(...diameters)).toBeLessThanOrEqual(1);
  await page.locator('[data-insight-province="hubei"]').click();
  await expect(page.getByRole("combobox", { name: "直接切换省份" })).toHaveValue("湖北省");
  await page.locator('[data-insight-province="henan"]').click();
  await expect(page.getByRole("heading", { name: "河南省城市数据" })).toBeVisible();
  await page.getByRole("combobox", { name: "直接切换省份" }).selectOption("新疆维吾尔自治区");
  await expect(page.getByRole("heading", { name: "新疆维吾尔自治区城市数据" })).toBeVisible();
});

test("大区视角显示完整大区数据并把范围参数传给接口", async ({ page }) => {
  const requestedModes: string[] = [];
  await page.route("**/api/v1/public/insights/**", (route) => {
    const url = new URL(route.request().url());
    requestedModes.push(url.searchParams.get("scope_mode") ?? "assigned");
    if (url.pathname.endsWith("/export")) return route.fulfill({ status: 200, body: "xlsx" });
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(overviewFor(url)) });
  });
  await loginAndOpenInsights(page);
  await page.getByRole("combobox", { name: "数据范围" }).selectOption("region");
  await expect(page.getByRole("heading", { name: "大区金额热力" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "全部大区数据" })).toBeVisible();
  await expect(page.locator(".insight-region-row")).toHaveCount(4);
  expect(requestedModes).toContain("region");
});

test("快速切换城市时只保留最后一次详情请求", async ({ page }) => {
  await page.route("**/api/v1/public/insights/**", async (route) => {
    const url = new URL(route.request().url());
    const city = url.searchParams.get("city");
    if (city === "苏州市") await new Promise((resolve) => setTimeout(resolve, 350));
    if (city === "南京市") await new Promise((resolve) => setTimeout(resolve, 20));
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(overviewFor(url)) });
  });
  await openMockedInsights(page);
  await page.locator('[data-insight-province="jiangsu"]').click();
  await page.getByRole("button", { name: "查看苏州市经营详情" }).click();
  await page.getByRole("button", { name: "查看南京市经营详情" }).click();

  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("heading", { name: "南京市" })).toBeVisible();
  await expect(dialog.getByRole("heading", { name: "苏州市" })).toHaveCount(0);
});
