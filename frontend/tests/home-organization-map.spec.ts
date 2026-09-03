/** 首页单位地图响应式验收：保证默认入口在窄屏内收缩，并把地图标签滚动限制在自身轨道。 */
import { expect, test } from "@playwright/test";

import { createAdminSession, type AuthCookies } from "./auth-session";
import { installFakeAmap } from "./fake-amap";

const pageUrl = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3100";
const adminUsername = process.env.ADMIN_USERNAME;
const adminPassword = process.env.ADMIN_PASSWORD;

test.use({ launchOptions: { executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" } });

let sessionCookies: AuthCookies = [];

test.beforeAll(async ({ browser }) => {
  test.skip(!adminUsername || !adminPassword, "需要管理员凭据验收受保护的单位地图");
  sessionCookies = await createAdminSession(browser, pageUrl, adminUsername!, adminPassword!);
});

test.beforeEach(async ({ context }) => {
  await context.addCookies(sessionCookies);
});

/** 用稳定的单位点位和筛选项打开默认地图，避免验收依赖数据库中的演示记录数量。 */
async function openOrganizationMap(page: import("@playwright/test").Page): Promise<void> {
  await installFakeAmap(page);
  await page.route("**/api/v1/public/organizations/map-points**", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([{
      id: "00000000-0000-4000-8000-000000000001",
      name: "移动端布局演示单位",
      organization_type: "高校",
      customer_status: "潜在客户",
      review_status: "已核验",
      longitude: 116.397,
      latitude: 39.909,
      province: "北京市",
      city: "北京市",
      district: "东城区",
      address: "北京市东城区演示地址 1 号",
      active_opportunity_count: 2,
      opportunity_stage: "方案/报价",
      estimated_opportunity_amount: "320000.00",
    }]),
  }));
  await page.route("**/api/v1/public/organizations/filters**", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({
      organization_types: ["高校"],
      customer_statuses: ["潜在客户"],
      review_statuses: ["已核验"],
      provinces: ["北京市"],
      cities: [],
      districts: [],
    }),
  }));
  await page.goto(pageUrl, { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("tab", { name: "全国单位地图", exact: true })).toHaveAttribute("aria-selected", "true");
  await expect(page.locator(".organization-map-shell")).toBeVisible();
}

test("移动端默认单位地图、筛选和切换轨道不撑宽工作区", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openOrganizationMap(page);

  const layout = await page.evaluate(() => {
    const content = document.querySelector<HTMLElement>(".unit-map-content")?.getBoundingClientRect();
    const card = document.querySelector<HTMLElement>(".map-card")?.getBoundingClientRect();
    const rail = document.querySelector<HTMLElement>(".map-view-rail");
    const map = document.querySelector<HTMLElement>(".organization-map-shell")?.getBoundingClientRect();
    return {
      documentFits: document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      contentFits: Boolean(content && card && content.left >= card.left - 1 && content.right <= card.right + 1),
      railScrollsInternally: Boolean(rail && rail.scrollWidth <= rail.clientWidth),
      mapFits: Boolean(map && card && map.left >= card.left - 1 && map.right <= card.right + 1),
    };
  });

  expect(layout).toEqual({ documentFits: true, contentFits: true, railScrollsInternally: true, mapFits: true });
});

test("点击单个单位 Pin 展示可关闭的地理与商机信息卡", async ({ page }) => {
  await page.setViewportSize({ width: 1536, height: 1000 });
  await openOrganizationMap(page);

  await page.locator(".org-map-pin").click();
  const popup = page.getByRole("dialog", { name: "移动端布局演示单位单位信息" });
  await expect(popup).toBeVisible();
  await expect(popup).toContainText("北京市 · 北京市 · 东城区");
  await expect(popup).toContainText("2 个推进中 · 方案/报价");
  await expect(popup).toContainText("¥320,000");
  await popup.getByRole("button", { name: "关闭单位信息" }).click();
  await expect(popup).toHaveCount(0);
});

test("桌面地区筛选按点位边界自动缩放并保留左右空隙", async ({ page }) => {
  await page.setViewportSize({ width: 1536, height: 1000 });
  await installFakeAmap(page);
  const points = [
    { id: "00000000-0000-4000-8000-000000000011", name: "杭州西湖演示单位", organization_type: "高校", customer_status: "潜在客户", review_status: "已核验", longitude: 120.15, latitude: 30.27, province: "浙江省", city: "杭州市", district: "西湖区", address: "西湖区演示地址", active_opportunity_count: 0, opportunity_stage: null, estimated_opportunity_amount: "0.00" },
    { id: "00000000-0000-4000-8000-000000000012", name: "杭州滨江演示单位", organization_type: "高校", customer_status: "商机客户", review_status: "已核验", longitude: 120.21, latitude: 30.17, province: "浙江省", city: "杭州市", district: "滨江区", address: "滨江区演示地址", active_opportunity_count: 1, opportunity_stage: "资格确认", estimated_opportunity_amount: "120000.00" },
    { id: "00000000-0000-4000-8000-000000000013", name: "宁波演示单位", organization_type: "高校", customer_status: "潜在客户", review_status: "已核验", longitude: 121.55, latitude: 29.87, province: "浙江省", city: "宁波市", district: "鄞州区", address: "鄞州区演示地址", active_opportunity_count: 0, opportunity_stage: null, estimated_opportunity_amount: "0.00" },
  ];
  await page.route("**/api/v1/public/organizations/map-points**", (route) => {
    const url = new URL(route.request().url());
    const city = url.searchParams.get("city");
    const district = url.searchParams.get("district");
    const filtered = district ? points.filter((point) => point.district === district) : city ? points.filter((point) => point.city === city) : points;
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(filtered) });
  });
  await page.route("**/api/v1/public/organizations/filters**", (route) => {
    const url = new URL(route.request().url());
    const province = url.searchParams.get("province");
    const city = url.searchParams.get("city");
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ organization_types: ["高校"], customer_statuses: ["潜在客户", "商机客户"], review_statuses: ["已核验"], provinces: ["浙江省"], cities: province ? ["杭州市", "宁波市"] : [], districts: city === "杭州市" ? ["西湖区", "滨江区"] : [] }) });
  });
  await page.goto(pageUrl, { waitUntil: "domcontentloaded" });

  await page.getByRole("combobox", { name: "省份", exact: true }).selectOption("浙江省");
  await expect(page.locator(".organization-map-legend b")).toHaveText("3 个可信点位");
  await expect.poll(() => page.evaluate(() => (window as Window & { __fakeAmapBoundsFitCalls?: unknown[] }).__fakeAmapBoundsFitCalls?.length ?? 0)).toBe(1);
  let fitCall = await page.evaluate(() => (window as Window & { __fakeAmapBoundsFitCalls?: Array<{ southWest: number[]; northEast: number[]; avoid: number[]; maxZoom: number }> }).__fakeAmapBoundsFitCalls?.at(-1));
  expect(fitCall).toEqual({ southWest: [120.15, 29.87], northEast: [121.55, 30.27], avoid: [72, 112, 96, 96], maxZoom: 12 });

  await page.getByRole("combobox", { name: "市", exact: true }).selectOption("杭州市");
  await expect(page.locator(".organization-map-legend b")).toHaveText("2 个可信点位");
  await expect.poll(() => page.evaluate(() => (window as Window & { __fakeAmapBoundsFitCalls?: unknown[] }).__fakeAmapBoundsFitCalls?.length ?? 0)).toBe(2);
  fitCall = await page.evaluate(() => (window as Window & { __fakeAmapBoundsFitCalls?: Array<{ southWest: number[]; northEast: number[]; avoid: number[]; maxZoom: number }> }).__fakeAmapBoundsFitCalls?.at(-1));
  expect(fitCall).toEqual({ southWest: [120.15, 30.17], northEast: [120.21, 30.27], avoid: [72, 112, 96, 96], maxZoom: 12 });

  await page.getByRole("combobox", { name: "区", exact: true }).selectOption("西湖区");
  await expect(page.locator(".organization-map-legend b")).toHaveText("1 个可信点位");
  await expect.poll(() => page.evaluate(() => (window as Window & { __fakeAmapViewportCalls?: unknown[] }).__fakeAmapViewportCalls?.length ?? 0)).toBe(3);
  const viewport = await page.evaluate(() => (window as Window & { __fakeAmapViewportCalls?: Array<{ zoom: number; center: number[] }> }).__fakeAmapViewportCalls?.at(-1));
  expect(viewport).toEqual({ zoom: 12, center: [120.15, 30.27] });
});
