/**
 * 同行市场版图浏览器验收：保留完整功能回归，入口重新开放后可直接恢复执行。
 */

import { expect, test } from "@playwright/test";

import { installFakeAmap } from "./fake-amap";

const pageUrl = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3100";
const browserExecutable = process.env.PLAYWRIGHT_BROWSER_PATH ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";

test.use({ launchOptions: { executablePath: browserExecutable } });
test.skip(true, "主页面暂时隐藏同行市场版图入口；恢复首页开关时删除此跳过。");

/** 等待客户端水合后切换到第四个地图入口，避免静态 HTML 吞掉过早点击。 */
async function openCompetitorMarket(page: import("@playwright/test").Page): Promise<void> {
  await installFakeAmap(page);
  await page.goto(pageUrl, { waitUntil: "networkidle" });
  await page.getByRole("tab", { name: /同行市场版图/ }).click();
  await expect(page.locator(".home-competitor-market-map")).toBeVisible();
}

test("成交单位下拉默认第一项并切换完整项目详情", async ({ page }) => {
  await openCompetitorMarket(page);
  const competitorFilter = page.getByLabel("按同行名称筛选");
  await expect(competitorFilter.locator("option").first()).toHaveText("全部同行据点（10）");
  await competitorFilter.selectOption({ label: "同行1" });
  await expect(page.getByRole("heading", { name: "同行1", exact: true })).toBeVisible();
  await expect(page.getByText("6 个成交单位")).toBeVisible();

  await page.getByRole("button", { name: /成交单位 6/ }).click();
  const customerSelect = page.getByLabel("选择同行成交单位");
  await expect(customerSelect.locator("option")).toHaveCount(6);
  await expect(customerSelect.locator("option:checked")).toHaveText(/^公司1 · .+ · ¥[\d,]+$/);
  await expect(page.locator(".competitor-intelligence-meta")).toHaveCount(0);
  await expect(page.getByText("已关联正式单位")).toBeVisible();
  await expect(page.getByText(/单位数据库：公司1/)).toBeVisible();
  await expect(page.getByText("产品名称", { exact: true })).toBeVisible();
  await expect(page.getByText("规格型号", { exact: true })).toBeVisible();
  await expect(page.getByText("产品单价", { exact: true })).toBeVisible();
  await expect(page.getByText("项目总价", { exact: true })).toBeVisible();
  await expect(page.getByText("中标时间", { exact: true })).toBeVisible();
  await expect(page.locator(".competitor-product-image:not(.is-empty)")).toBeVisible();
  const unitTwoOption = customerSelect.locator("option").filter({ hasText: "同行1签约单位2" });
  await expect(unitTwoOption).toHaveText(/^同行1签约单位2 · .+ · ¥[\d,]+$/);
  const unitTwoValue = await unitTwoOption.getAttribute("value");
  expect(unitTwoValue).not.toBeNull();
  await customerSelect.selectOption(unitTwoValue!);
  await expect(page.getByText("尚未关联正式单位")).toBeVisible();
  const unitThreeValue = await customerSelect.locator("option").filter({ hasText: "同行1签约单位3" }).getAttribute("value");
  expect(unitThreeValue).not.toBeNull();
  await customerSelect.selectOption(unitThreeValue!);
  await expect(page.getByRole("img", { name: "暂无产品图片" })).toBeVisible();

  await page.getByRole("button", { name: /竞争区域/ }).click();
  await expect(page.locator(".competitor-strength-tag")).toHaveText(/势区域/);
  await expect(page.getByText("综合评分", { exact: true })).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(competitorFilter).toHaveValue("");
  await expect(page.getByRole("heading", { name: "同行1", exact: true })).toHaveCount(0);
});

test("同行筛选与标题同框且地图缩放按钮位于右下角", async ({ page }) => {
  await page.route("**/api/v1/public/competitors", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([
      { id: "competitor-1", name: "同行1", color: "#25846f", primary_site: { id: "site-1", longitude: 116.4, latitude: 39.9 } },
      { id: "competitor-2", name: "同行2", color: "#d96a37", primary_site: { id: "site-2", longitude: 121.47, latitude: 31.23 } },
    ]),
  }));
  await openCompetitorMarket(page);

  const titleCard = page.locator(".competitor-map-title-card");
  const uniteCustomerButton = page.getByRole("button", { name: "显示优纳特客户" });
  const selector = page.getByLabel("按同行名称筛选");
  const zoom = page.getByRole("group", { name: "同行地图缩放" });
  await expect(titleCard).toBeVisible();
  await expect(page.getByRole("button", { name: /强势区域/ })).toHaveCount(0);
  await expect(uniteCustomerButton).toBeVisible();
  await expect(selector).toBeVisible();
  await expect(page.locator(".fake-amap-region")).toHaveCount(0);

  const headquartersPins = page.locator(".competitor-marker.is-primary");
  await expect(headquartersPins).toHaveCount(2);
  await expect(headquartersPins.first().locator("span")).toHaveText("");
  await expect(headquartersPins.first().locator("b")).toHaveText("同行1");
  const headquartersLayout = await headquartersPins.first().evaluate((marker) => {
    const labelRect = marker.querySelector<HTMLElement>("b")?.getBoundingClientRect();
    const pin = marker.querySelector<HTMLElement>("span");
    const pinRect = pin?.getBoundingClientRect();
    const bodyStyle = pin ? getComputedStyle(pin, "::before") : null;
    const tipStyle = pin ? getComputedStyle(pin, "::after") : null;
    return {
      width: pinRect?.width,
      height: pinRect?.height,
      labelAbovePin: Boolean(labelRect && pinRect && labelRect.bottom <= pinRect.top),
      emptyPin: pin?.textContent === "",
      circularBody: bodyStyle?.borderRadius,
      hasPoint: tipStyle?.content !== "none" && tipStyle?.backgroundColor !== "rgba(0, 0, 0, 0)",
    };
  });
  expect(headquartersLayout).toEqual({ width: 28, height: 34, labelAbovePin: true, emptyPin: true, circularBody: "50%", hasPoint: true });

  const layout = await page.evaluate(() => {
    const cardElement = document.querySelector<HTMLElement>(".competitor-map-title-card");
    const card = cardElement?.getBoundingClientRect();
    const title = cardElement?.querySelector<HTMLElement>("h1")?.getBoundingClientRect();
    const customerButton = cardElement?.querySelector<HTMLElement>(".competitor-customer-toggle")?.getBoundingClientRect();
    const selectorElement = cardElement?.querySelector<HTMLElement>(".competitor-map-selector")?.getBoundingClientRect();
    const map = document.querySelector<HTMLElement>(".home-competitor-market-map")?.getBoundingClientRect();
    const zoomElement = document.querySelector<HTMLElement>(".competitor-map-zoom")?.getBoundingClientRect();
    const buttons = Array.from(document.querySelectorAll<HTMLElement>(".competitor-map-zoom button")).map((button) => button.getBoundingClientRect());
    return {
      cardContainsSelector: Boolean(cardElement?.querySelector(".competitor-map-selector")),
      cardFitsMap: Boolean(card && map && card.left >= map.left && card.right <= map.right),
      selectorBelowTitle: Boolean(title && selectorElement && selectorElement.top > title.bottom),
      customerButtonAboveSelector: Boolean(customerButton && selectorElement && customerButton.bottom < selectorElement.top),
      zoomAtBottomRight: Boolean(map && zoomElement && map.right - zoomElement.right <= 24 && map.bottom - zoomElement.bottom <= 24),
      zoomIsHorizontal: buttons.length === 2 && Math.abs(buttons[0].top - buttons[1].top) < 2 && buttons[1].left > buttons[0].left,
    };
  });
  expect(layout).toEqual({ cardContainsSelector: true, cardFitsMap: true, selectorBelowTitle: true, customerButtonAboveSelector: true, zoomAtBottomRight: true, zoomIsHorizontal: true });

  await zoom.getByRole("button", { name: "放大同行地图" }).click();
  await zoom.getByRole("button", { name: "缩小同行地图" }).click();
  await expect.poll(() => page.evaluate(() => (window as Window & { __fakeAmapZoomCalls?: string[] }).__fakeAmapZoomCalls)).toEqual(["in", "out"]);

  await page.setViewportSize({ width: 390, height: 844 });
  await expect.poll(() => page.evaluate(() => {
    const card = document.querySelector<HTMLElement>(".competitor-map-title-card")?.getBoundingClientRect();
    const map = document.querySelector<HTMLElement>(".home-competitor-market-map")?.getBoundingClientRect();
    const zoomElement = document.querySelector<HTMLElement>(".competitor-map-zoom")?.getBoundingClientRect();
    return Boolean(card && map && zoomElement && card.left >= map.left && card.right <= map.right && zoomElement.right <= map.right && zoomElement.bottom <= map.bottom);
  })).toBe(true);
});

test("优纳特客户图层从正式单位接口读取六个已成交点位并展示实际成交详情", async ({ page }) => {
  await page.route("**/api/v1/public/organizations/won-customers", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify(Array.from({ length: 6 }, (_, index) => ({
      id: `won-${index + 1}`,
      name: `公司${index + 1}`,
      organization_type: "企业",
      industry: index < 2 ? "华北检测" : index < 4 ? "华东研发" : "华南新材料",
      customer_status: "已成交客户",
      review_status: "已核验",
      address: `公司${index + 1}演示地址`,
      province: index < 2 ? "北京市" : index < 4 ? "上海市" : "广东省",
      city: index < 2 ? "北京市" : index < 4 ? "上海市" : "深圳市",
      district: "演示区",
      longitude: 116.4 + index,
      latitude: 39.9 - index * 2,
      deal_count: 1,
      actual_sales_amount: "680000.00",
      deals: [{ id: `deal-${index + 1}`, name: `公司${index + 1}成交项目`, contract_amount: "680000.00", signed_at: "2026-01-12", project_detail: "纯虚构成交项目" }],
    }))),
  }));
  await openCompetitorMarket(page);

  const toggle = page.getByRole("button", { name: "显示优纳特客户" });
  await toggle.click();
  await expect(page.getByRole("button", { name: "隐藏优纳特客户" })).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".unite-customer-marker")).toHaveCount(6);
  await expect(page.locator(".unite-customer-marker").first().locator("span")).toHaveCSS("width", "20px");
  await expect(page.locator(".unite-customer-marker").first().locator("span")).toHaveCSS("height", "25px");
  await page.locator(".unite-customer-marker").first().click();
  const customerPanel = page.locator(".unite-customer-panel");
  await expect(customerPanel.getByRole("heading", { name: "公司1", exact: true }).first()).toBeVisible();
  await expect(customerPanel.getByText("优纳特已成交客户 · 数据来自正式单位库")).toBeVisible();
  await expect(customerPanel.getByText("¥680,000").first()).toBeVisible();
  await expect(customerPanel.getByText("公司1成交项目")).toBeVisible();

  await expect(page.locator(".unite-customer-marker")).toHaveCount(6);
  await expect(page.locator(".fake-amap-region")).toHaveCount(0);
});

test("优纳特客户图层对空数据与接口错误给出明确反馈", async ({ page }) => {
  await page.route("**/api/v1/public/organizations/won-customers", (route) => route.fulfill({ status: 200, contentType: "application/json", body: "[]" }));
  await openCompetitorMarket(page);
  await page.getByRole("button", { name: "显示优纳特客户" }).click();
  await expect(page.getByText(/暂无已成交客户点位/)).toBeVisible();

  await page.unroute("**/api/v1/public/organizations/won-customers");
  await page.route("**/api/v1/public/organizations/won-customers", (route) => route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "客户图层演示错误" }) }));
  await page.getByRole("alert").getByRole("button", { name: "关闭" }).click();
  await page.getByRole("button", { name: "显示优纳特客户" }).click();
  await expect(page.getByText("客户图层演示错误")).toBeVisible();
});

test("同行详情只绘制 Pin，快速切换会清理旧同行覆盖物", async ({ page }) => {
  await openCompetitorMarket(page);

  const competitorFilter = page.getByLabel("按同行名称筛选");
  await competitorFilter.selectOption({ label: "同行3" });
  await expect(page.locator(".fake-amap-region")).toHaveCount(0);
  await competitorFilter.selectOption({ label: "同行6" });

  await expect(page.getByRole("heading", { name: "同行6", exact: true })).toBeVisible();
  await expect(page.locator(".fake-amap-region")).toHaveCount(0);
  const latestFit = await expect.poll(() => page.evaluate(() => {
    const calls = (window as Window & { __fakeAmapFitCalls?: Array<{ overlayKinds: string[]; immediately: boolean; avoid: number[]; maxZoom: number }> }).__fakeAmapFitCalls ?? [];
    return calls.at(-1);
  })).not.toBeUndefined();
  void latestFit;
  const fitCall = await page.evaluate(() => (window as Window & { __fakeAmapFitCalls?: Array<{ overlayKinds: string[] }> }).__fakeAmapFitCalls?.at(-1));
  expect(fitCall?.overlayKinds).not.toContain("circle");
  expect(fitCall?.overlayKinds).toEqual(expect.arrayContaining(["marker"]));

  await page.keyboard.press("Escape");
  await expect(page.locator(".fake-amap-region")).toHaveCount(0);
});

test("同行 Pin 不请求高德行政区边界接口", async ({ page }) => {
  let districtRequestCount = 0;
  await page.route("**/_AMapService/v3/config/district**", (route) => {
    districtRequestCount += 1;
    return route.abort();
  });
  await openCompetitorMarket(page);
  await page.getByLabel("按同行名称筛选").selectOption({ label: "同行6" });
  await expect(page.locator(".fake-amap-region")).toHaveCount(0);
  expect(districtRequestCount).toBe(0);
});

test("同行列表加载、空数据和错误状态均有明确反馈", async ({ page }) => {
  await page.route("**/api/v1/public/competitors", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 700));
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await openCompetitorMarket(page);
  await expect(page.getByText("正在读取同行主要据点")).toBeVisible();
  await expect(page.getByText("暂无同行市场数据")).toBeVisible();

  await page.unroute("**/api/v1/public/competitors");
  await page.route("**/api/v1/public/competitors", (route) => route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "演示错误" }) }));
  await page.reload();
  await page.getByRole("tab", { name: /同行市场版图/ }).click();
  await expect(page.getByText("同行市场地图暂不可用")).toBeVisible();
  await expect(page.getByRole("button", { name: "重新加载" })).toBeVisible();
});

test("高德 SDK 加载失败时显示明确错误和重试入口", async ({ page }) => {
  await page.addInitScript(() => {
    (window as Window & { AMapLoader?: unknown }).AMapLoader = { load: () => Promise.reject(new Error("演示地图错误")) };
  });
  await page.goto(pageUrl, { waitUntil: "networkidle" });
  await page.getByRole("tab", { name: /同行市场版图/ }).click();
  await expect(page.getByText("同行市场地图暂不可用")).toBeVisible();
  await expect(page.getByText("演示地图错误")).toBeVisible();
  await expect(page.getByRole("button", { name: "重新加载" })).toBeVisible();
});

test("移动端同行面板保持在地图内且页面无横向溢出", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openCompetitorMarket(page);
  await page.getByLabel("按同行名称筛选").selectOption({ label: "同行1" });
  const panel = page.locator(".competitor-panel");
  await expect(panel).toBeVisible();
  await expect.poll(async () => page.evaluate(() => {
    const panelElement = document.querySelector<HTMLElement>(".competitor-panel");
    const mapElement = document.querySelector<HTMLElement>(".home-competitor-market-map");
    const panelRect = panelElement?.getBoundingClientRect();
    const mapRect = mapElement?.getBoundingClientRect();
    return {
      documentFits: document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      panelFitsMap: Boolean(
        panelRect &&
          mapRect &&
          panelRect.left >= mapRect.left &&
          panelRect.right <= mapRect.right &&
          panelRect.top >= mapRect.top &&
          panelRect.bottom <= mapRect.bottom,
      ),
      panelHeightFitsViewport: Boolean(panelRect && panelRect.height <= window.innerHeight),
    };
  })).toEqual({ documentFits: true, panelFitsMap: true, panelHeightFitsViewport: true });
});
