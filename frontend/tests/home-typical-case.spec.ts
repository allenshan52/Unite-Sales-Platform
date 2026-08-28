/** 第六地图浏览器验收：验证真实 API、发布/筹备交互、失败恢复和移动端边界。 */
import { expect, test } from "@playwright/test";

import { installFakeAmap } from "./fake-amap";

const pageUrl = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3100";

test.use({ launchOptions: { executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" } });

/** 打开主页第六入口并等待案例地图完成真实数据加载。 */
async function openTypicalCases(page: import("@playwright/test").Page): Promise<void> {
  await installFakeAmap(page);
  await page.goto(pageUrl, { waitUntil: "domcontentloaded" });
  const caseTab = page.getByRole("tab", { name: /典型案例地图/ });
  await expect(caseTab).toBeVisible();
  await caseTab.click();
  await expect(page.getByRole("heading", { name: "一省一案" })).toBeVisible();
}

test("默认打开推荐案例并展示后端统计、封面和完整复盘", async ({ page }) => {
  await openTypicalCases(page);
  await expect(page.getByText("已上线").first()).toBeVisible();
  await expect(page.getByText("筹备中").first()).toBeVisible();
  await expect(page.locator(".typical-case-province.is-published")).toHaveCount(6);
  await expect(page.locator(".typical-case-story h2")).toBeVisible();
  const coverImage = page.locator(".typical-case-cover img");
  await expect(coverImage).toBeVisible();
  await expect.poll(() => coverImage.evaluate((image) => (image as HTMLImageElement).complete && (image as HTMLImageElement).naturalWidth > 0)).toBe(true);
  await expect(page.getByRole("heading", { name: "现场挑战" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "实施方案" })).toBeVisible();
  await expect(page.getByRole("heading", { name: "交付成果" })).toBeVisible();
  if (process.env.CAPTURE_UI === "1") await page.screenshot({ path: "ui-check/typical-case-desktop.png", fullPage: true });
});

test("省份下拉和键盘地图路径都可切换发布与筹备状态", async ({ page }) => {
  await openTypicalCases(page);
  await page.getByLabel("选择省份案例").selectOption({ label: "江苏省 · 已上线" });
  await expect(page.locator(".typical-case-cover-location")).toContainText("江苏省");
  await expect(page.locator(".typical-case-map-stage svg path").last()).toHaveAttribute("data-province", "江苏省");
  const pendingProvince = page.getByRole("button", { name: "北京市案例筹备中" });
  await pendingProvince.focus();
  await pendingProvince.press("Enter");
  await expect(page.locator(".typical-case-map-stage svg path").last()).toHaveAttribute("data-province", "北京市");
  await expect(page.getByText("北京市案例筹备中", { exact: true })).toBeVisible();
  await expect(page.getByText("资料归档")).toBeVisible();
});

test("地图请求失败时提供明确错误和重新加载入口", async ({ page }) => {
  await installFakeAmap(page);
  await page.route("**/api/v1/public/typical-cases", (route) => route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "案例服务维护中" }) }));
  await page.goto(pageUrl, { waitUntil: "domcontentloaded" });
  await page.getByRole("tab", { name: /典型案例地图/ }).click();
  await expect(page.getByText("典型案例地图暂不可用")).toBeVisible();
  await expect(page.getByText("案例服务维护中")).toBeVisible();
  await expect(page.getByRole("button", { name: "重新加载" })).toBeVisible();
});

test("移动端地图与案例内容按单列排列且页面无横向溢出", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openTypicalCases(page);
  await expect(page.getByLabel("选择省份案例")).toBeVisible();
  const layout = await page.evaluate(() => {
    const shell = document.querySelector<HTMLElement>(".map-card")?.getBoundingClientRect();
    const content = document.querySelector<HTMLElement>(".home-typical-case-map")?.getBoundingClientRect();
    const rail = document.querySelector<HTMLElement>(".map-view-rail")?.getBoundingClientRect();
    const selectedTab = document.querySelector<HTMLElement>(".map-switch button.selected")?.getBoundingClientRect();
    const map = document.querySelector<HTMLElement>(".typical-case-atlas")?.getBoundingClientRect();
    const story = document.querySelector<HTMLElement>(".typical-case-detail")?.getBoundingClientRect();
    return {
      fits: document.documentElement.scrollWidth <= document.documentElement.clientWidth,
      contained: Boolean(shell && content && content.left >= shell.left - 1 && content.right <= shell.right + 1),
      selectedTabInRail: Boolean(rail && selectedTab && selectedTab.left >= rail.left && selectedTab.right <= rail.right),
      stacked: Boolean(map && story && story.top >= map.bottom - 2),
    };
  });
  expect(layout).toEqual({ fits: true, contained: true, selectedTabInRail: true, stacked: true });
  if (process.env.CAPTURE_UI === "1") {
    await page.screenshot({ path: "ui-check/typical-case-mobile.png" });
    await page.locator(".typical-case-story h2").scrollIntoViewIfNeeded();
    await page.screenshot({ path: "ui-check/typical-case-mobile-story.png" });
  }
});
