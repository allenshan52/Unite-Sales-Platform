/** 真实 localhost 访问控制验收：确认匿名只能看登录页，超级管理员可进入主站与账号管理。 */

import { expect, test } from "@playwright/test";

/** 登录后同时锁定当前五个地图入口，同行市场版图保持隐藏。 */

const baseUrl = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3100";
const adminUsername = process.env.ADMIN_USERNAME;
const adminPassword = process.env.ADMIN_PASSWORD;

test.use({ launchOptions: { executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" } });

test("未登录时只显示公司内部访问弹窗且业务 API 返回 401", async ({ page }) => {
  await page.context().clearCookies();
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await expect(page.getByText("公司内部访问", { exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "全国销售网络作战地图" })).toBeVisible();
  await expect(page.locator(".topbar")).toHaveCount(0);
  const response = await page.request.get(`${baseUrl}/api/v1/public/organizations/filters`);
  expect(response.status()).toBe(401);
});

test("超级管理员可登录主站并看到带覆盖范围的授权账号后台", async ({ page }) => {
  test.skip(!adminUsername || !adminPassword, "需要 ADMIN_USERNAME 与 ADMIN_PASSWORD 验收真实登录");
  await page.context().clearCookies();
  await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.getByLabel("账号").fill(adminUsername!);
  await page.getByLabel("密码").fill(adminPassword!);
  await page.getByRole("button", { name: "进入网站" }).click();
  await expect(page.locator(".topbar")).toBeVisible();
  const mapTabs = page.getByRole("tablist", { name: "单位地图切换" }).getByRole("tab");
  await expect(mapTabs).toHaveCount(5);
  await expect(page.getByRole("tab", { name: /同行市场版图/ })).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(await page.locator(".map-switch").evaluate((element) => element.getBoundingClientRect().right <= window.innerWidth)).toBe(true);
  await page.setViewportSize({ width: 1280, height: 720 });
  await expect(page.getByRole("link", { name: /数据后台/ })).toBeVisible();
  await page.getByRole("link", { name: /数据后台/ }).click();
  await expect(page.getByRole("heading", { name: "数据后台" })).toBeVisible();
  await page.getByRole("tab", { name: "授权账号", exact: true }).click();
  await expect(page.getByRole("heading", { name: /个授权账号/ })).toBeVisible();
  await expect(page.getByText(adminUsername!, { exact: true })).toBeVisible();
  const superAdminRow = page.locator(".account-row").filter({ hasText: adminUsername! });
  await expect(superAdminRow.getByText("全国", { exact: true })).toBeVisible();
  const jilinRow = page.locator(".account-row").filter({ hasText: "jilin_sales" });
  await expect(jilinRow).toContainText("吉林");
  await jilinRow.getByRole("button", { name: "修改" }).click();
  const scopeDialog = page.getByRole("dialog", { name: "修改 jilin_sales" });
  await expect(scopeDialog.getByLabel("省份")).toHaveValue("吉林");
  await scopeDialog.getByRole("button", { name: "取消" }).click();
});
