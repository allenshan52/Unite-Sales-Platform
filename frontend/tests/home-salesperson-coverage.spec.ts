/** 销售覆盖地图浏览器验收：验证每人一个 Pin、标题白框、月份/年份和双人对比闭环。 */

import { expect, test } from "@playwright/test";

import { createAdminSession, type AuthCookies } from "./auth-session";
import { installFakeAmap } from "./fake-amap";

const pageUrl = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3100";
const browserExecutable = process.env.PLAYWRIGHT_BROWSER_PATH ?? "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe";
const adminUsername = process.env.ADMIN_USERNAME;
const adminPassword = process.env.ADMIN_PASSWORD;

test.use({ launchOptions: { executablePath: browserExecutable } });

let sessionCookies: AuthCookies = [];

test.beforeAll(async ({ browser }) => {
  test.skip(!adminUsername || !adminPassword, "需要 ADMIN_USERNAME 与 ADMIN_PASSWORD 验收真实销售地图");
  sessionCookies = await createAdminSession(browser, pageUrl, adminUsername!, adminPassword!);
});

test.beforeEach(async ({ context }) => {
  /** 一次登录得到的 Cookie 分发给隔离上下文，避免测试套件触发登录限流。 */
  await context.addCookies(sessionCookies);
});

/** 必要时通过真实会话登录，再等待主页 hydration 后进入销售覆盖地图。 */
async function openSalespersonCoverage(page: import("@playwright/test").Page): Promise<void> {
  await installFakeAmap(page);
  await page.goto(pageUrl, { waitUntil: "networkidle" });
  await page.getByRole("tab", { name: /销售覆盖与人效/ }).click();
  await expect(page.getByRole("heading", { name: "销售覆盖与人效" })).toBeVisible();
}

test("默认三个月显示每人一个 Pin，点击姓名后展开单人详情并聚焦", async ({ page }) => {
  await openSalespersonCoverage(page);
  await expect(page.getByText("点击高亮城市查看销售详情", { exact: true })).toHaveCount(0);
  await expect(page.getByRole("radiogroup", { name: "活动统计时间范围" })).toHaveCount(0);
  await expect(page.locator(".fake-amap-region")).toHaveCount(0);
  await expect(page.locator(".salesperson-marker")).toHaveCount(6);
  const firstMarker = page.locator('.salesperson-marker[title="张1"]').first();
  await expect(firstMarker.locator("b")).toHaveText("张1");
  const nameLayout = await firstMarker.evaluate((marker) => {
    const pin = marker.querySelector<HTMLElement>("span")?.getBoundingClientRect();
    const labelElement = marker.querySelector<HTMLElement>("b");
    const label = labelElement?.getBoundingClientRect();
    const labelStyle = labelElement ? getComputedStyle(labelElement) : null;
    return {
      above: Boolean(pin && label && label.bottom <= pin.top),
      pointerEvents: labelStyle?.pointerEvents,
    };
  });
  expect(nameLayout).toEqual({ above: true, pointerEvents: "none" });
  await firstMarker.click();
  const detail = page.getByRole("complementary", { name: "张1销售详情" });
  await expect(detail).toBeVisible();
  await expect(detail.getByRole("radio", { name: "3 月" })).toHaveAttribute("aria-checked", "true");
  const yearSelect = detail.getByLabel("活动年份");
  const currentYear = new Date().getFullYear();
  await expect(yearSelect).toHaveValue("");
  await expect(yearSelect.locator("option")).toHaveText(["年份", `${currentYear} 年`, `${currentYear - 1} 年`, `${currentYear - 2} 年`]);
  await expect(detail.getByText("客户拜访")).toBeVisible();
  await expect(detail.locator(".salesperson-coverage-copy")).toContainText("全国");
  await expect(detail.getByText("成交金额", { exact: false })).toBeVisible();
  await expect(detail.getByText("储备金额", { exact: false })).toBeVisible();
  await expect.poll(() => page.evaluate(() => {
    const calls = (window as Window & { __fakeAmapFitCalls?: Array<{ overlayKinds: string[]; immediately: boolean; avoid: number[]; maxZoom: number }> }).__fakeAmapFitCalls ?? [];
    return calls.at(-1);
  })).toMatchObject({ overlayKinds: ["marker"], immediately: false, maxZoom: 8.2 });
  const focusPadding = await page.evaluate(() => {
    const calls = (window as Window & { __fakeAmapFitCalls?: Array<{ avoid: number[] }> }).__fakeAmapFitCalls ?? [];
    return calls.at(-1)?.avoid;
  });
  expect(focusPadding?.[1]).toBeLessThan(160);
  expect(focusPadding?.[2]).toBeGreaterThan(300);
  expect(focusPadding?.[3]).toBeGreaterThan(390);

  const selectedYear = currentYear - 1;
  const yearResponse = page.waitForResponse((response) => response.url().includes(`/salespeople/coverage?year=${selectedYear}`) && response.status() === 200);
  await yearSelect.selectOption(String(selectedYear));
  await yearResponse;
  await expect(detail.getByText(`${selectedYear} 年人效详情`)).toBeVisible();
  await expect(detail.getByRole("radio", { name: "3 月" })).toHaveAttribute("aria-checked", "false");

  const sixMonthResponse = page.waitForResponse((response) => response.url().includes("/salespeople/coverage?months=6") && response.status() === 200);
  await detail.getByRole("radio", { name: "6 月" }).click();
  const sixMonthPeople = await (await sixMonthResponse).json() as Array<{ display_name: string; performance: { activities: { total: number } } }>;
  const zhang = sixMonthPeople.find((person) => person.display_name === "张1");
  await expect(detail.getByText("最近 6 个月人效详情")).toBeVisible();
  await expect(detail.locator(".salesperson-activity-block")).toContainText(`${zhang?.performance.activities.total} 次`);
});

test("销售 Pin 不调用市界查询，重新进入地图仍保持每人一个 Pin", async ({ page }) => {
  await openSalespersonCoverage(page);
  const firstPassCalls = await page.evaluate(() => Object.values((window as Window & { __fakeAmapDistrictCalls?: Record<string, number> }).__fakeAmapDistrictCalls ?? {}).reduce((sum, count) => sum + count, 0));
  expect(firstPassCalls).toBe(0);

  await page.getByRole("tab", { name: "全国单位地图", exact: true }).click();
  await page.getByRole("tab", { name: /销售覆盖与人效/ }).click();
  await expect(page.locator(".fake-amap-region")).toHaveCount(0);
  await expect(page.locator(".salesperson-marker")).toHaveCount(6);
  const callsAfterRemount = await page.evaluate(() => Object.values((window as Window & { __fakeAmapDistrictCalls?: Record<string, number> }).__fakeAmapDistrictCalls ?? {}).reduce((sum, count) => sum + count, 0));
  expect(callsAfterRemount).toBe(0);
});

test("标题白框可选择和移除销售，并以左右两列比较两人", async ({ page }) => {
  await openSalespersonCoverage(page);
  const selector = page.getByRole("button", { name: /选择销售人员/ });
  await selector.click();
  await page.getByRole("option", { name: /张1/ }).click();
  await page.getByRole("option", { name: /王3/ }).click();
  await expect(page.getByLabel("已选择销售")).toContainText("张1");
  await expect(page.getByLabel("已选择销售")).toContainText("王3");
  const compare = page.getByRole("button", { name: "对比" });
  await expect(compare).toBeEnabled();
  await compare.click();
  const panel = page.getByRole("complementary", { name: "张1与王3人效对比" });
  await expect(panel).toBeVisible();
  await expect(panel.getByRole("heading", { name: "张1" })).toBeVisible();
  await expect(panel.getByRole("heading", { name: "王3" })).toBeVisible();
  await expect(panel.getByText("活动总数")).toHaveCount(2);
  await expect(page.locator(".fake-amap-region")).toHaveCount(0);
  await expect(page.locator(".salesperson-marker")).toHaveCount(2);
  await expect.poll(() => page.evaluate(() => {
    const calls = (window as Window & { __fakeAmapFitCalls?: Array<{ overlayKinds: string[]; avoid: number[] }> }).__fakeAmapFitCalls ?? [];
    return calls.at(-1);
  })).toMatchObject({ overlayKinds: ["marker", "marker"] });
  const comparisonPadding = await page.evaluate(() => {
    const calls = (window as Window & { __fakeAmapFitCalls?: Array<{ avoid: number[] }> }).__fakeAmapFitCalls ?? [];
    const root = document.querySelector<HTMLElement>(".home-salesperson-coverage-map")?.getBoundingClientRect();
    const title = document.querySelector<HTMLElement>(".salesperson-map-title-card")?.getBoundingClientRect();
    const panel = document.querySelector<HTMLElement>(".salesperson-compare-panel")?.getBoundingClientRect();
    return {
      actual: calls.at(-1)?.avoid,
      expectedTop: root && title ? Math.ceil(title.bottom - root.top + 24) : null,
      expectedRight: root && panel ? Math.ceil(root.right - panel.left + 24) : null,
    };
  });
  expect(Math.abs((comparisonPadding.actual?.[0] ?? 0) - (comparisonPadding.expectedTop ?? 0))).toBeLessThanOrEqual(1);
  expect(comparisonPadding.actual?.[1]).toBe(48);
  expect(comparisonPadding.actual?.[2]).toBe(48);
  expect(Math.abs((comparisonPadding.actual?.[3] ?? 0) - (comparisonPadding.expectedRight ?? 0))).toBeLessThanOrEqual(1);

  const sixMonthResponse = page.waitForResponse((response) => response.url().includes("/salespeople/coverage?months=6") && response.status() === 200);
  await panel.getByRole("radio", { name: "6 月" }).click();
  const sixMonthPeople = await (await sixMonthResponse).json() as Array<{ display_name: string; performance: { activities: { total: number } } }>;
  await expect(panel.getByRole("radio", { name: "6 月" })).toHaveAttribute("aria-checked", "true");
  for (const name of ["张1", "王3"]) {
    const person = sixMonthPeople.find((candidate) => candidate.display_name === name);
    await expect(panel.locator("article", { hasText: name })).toContainText(`${person?.performance.activities.total} 次`);
  }

  await panel.getByRole("button", { name: "关闭销售对比" }).click();
  await page.locator('.salesperson-marker[title="张1"]').click();
  await expect(page.getByRole("complementary", { name: "张1销售详情" }).getByRole("radio", { name: "3 月" })).toHaveAttribute("aria-checked", "true");
});

test("移动端标题、详情月份条和详情面板均保持在地图内", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openSalespersonCoverage(page);
  await page.locator('.salesperson-marker[title="冯7"]').first().click();
  await expect(page.getByRole("complementary", { name: "冯7销售详情" })).toBeVisible();
  const layout = await page.evaluate(() => {
    const map = document.querySelector<HTMLElement>(".home-salesperson-coverage-map")?.getBoundingClientRect();
    const title = document.querySelector<HTMLElement>(".salesperson-map-title-card")?.getBoundingClientRect();
    const panel = document.querySelector<HTMLElement>(".salesperson-detail-panel")?.getBoundingClientRect();
    const period = document.querySelector<HTMLElement>(".salesperson-detail-period")?.getBoundingClientRect();
    const within = (rect?: DOMRect) => Boolean(rect && map && rect.left >= map.left && rect.right <= map.right && rect.top >= map.top && rect.bottom <= map.bottom);
    return { documentFits: document.documentElement.scrollWidth <= document.documentElement.clientWidth, titleFits: within(title), periodFits: within(period), panelFits: within(panel) };
  });
  expect(layout).toEqual({ documentFits: true, titleFits: true, periodFits: true, panelFits: true });
});

test("地图 SDK 失败不会被后端数据成功状态覆盖", async ({ page }) => {
  /** 模拟地图加载失败但保留真实销售接口成功，锁定两个资源的独立错误边界。 */
  await page.addInitScript(() => {
    (window as Window & { AMapLoader?: unknown }).AMapLoader = { load: async () => { throw new Error("地图测试失败"); } };
  });
  await page.goto(pageUrl, { waitUntil: "networkidle" });
  await page.getByRole("tab", { name: /销售覆盖与人效/ }).click();
  await expect(page.getByText("销售覆盖地图暂不可用")).toBeVisible();
  await expect(page.getByText("地图测试失败")).toBeVisible();
  await expect(page.getByRole("button", { name: "重新加载" })).toBeVisible();
});
