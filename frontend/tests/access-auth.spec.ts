/** 真实 localhost 访问控制验收：确认匿名只能看登录页，超级管理员可进入主站与账号管理。 */

import { expect, test } from "@playwright/test";

/** 登录后锁定两个主入口、五个地图入口及其业务顺序。 */

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
  const screenTabs = page.getByRole("tablist", { name: "主界面切换" }).getByRole("tab");
  await expect(screenTabs).toHaveText(["全国单位地图", "数据洞察"]);
  await expect(page.getByRole("tab", { name: "单位数据库", exact: true })).toHaveCount(0);
  const mapTabs = page.getByRole("tablist", { name: "单位地图切换" }).getByRole("tab");
  await expect(mapTabs).toHaveCount(5);
  await expect(mapTabs.locator("b")).toHaveText(["全国单位地图", "全国成交热力地图", "典型案例地图", "销售覆盖与人效", "客户关系网络"]);
  await expect(mapTabs.first()).toHaveAttribute("aria-selected", "true");
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
  const zhejiangRow = page.locator(".account-row").filter({ hasText: "sales_zhejiang" });
  await expect(zhejiangRow).toContainText("宁波市");
  await zhejiangRow.getByRole("button", { name: "修改" }).click();
  const scopeDialog = page.getByRole("dialog", { name: "修改 sales_zhejiang" });
  await expect(scopeDialog.getByLabel("省份").first()).toHaveValue("浙江");
  await expect(scopeDialog.getByLabel("城市").first()).toHaveValue("宁波市");
  await scopeDialog.getByRole("button", { name: "取消" }).click();
});

test("退出接口失败时保留当前页面并显示可重试错误", async ({ page }) => {
  let logoutRequests = 0;
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.route("**/api/v1/**", async (route) => {
    const path = new URL(route.request().url()).pathname.replace("/api/v1", "");
    if (path === "/auth/me") return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        username: "logout_test", role: "超级管理员", salesperson_id: null,
        can_manage_users: true, can_manage_salespeople: true, coverage_scopes: [],
      }),
    });
    if (path === "/auth/logout") {
      logoutRequests += 1;
      await new Promise((resolve) => setTimeout(resolve, 80));
      return route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "演示退出失败" }),
      });
    }
    if (path === "/public/organizations/filters") return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ organization_types: [], customer_statuses: [], review_statuses: [], provinces: [], cities: [], districts: [] }),
    });
    if (path === "/public/organizations/map-points") return route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
    return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "测试未配置" }) });
  });

  await page.goto(baseUrl, { waitUntil: "domcontentloaded" });
  const logoutResponse = page.waitForResponse((response) => response.url().endsWith("/api/v1/auth/logout"));
  const logoutButton = page.getByRole("button", { name: "退出", exact: true });
  await logoutButton.click();
  expect((await logoutResponse).status()).toBe(500);
  await expect.poll(() => logoutRequests).toBe(1);
  expect(pageErrors).toEqual([]);
  const bodyText = await page.locator("body").innerText();
  expect(bodyText).toContain("logout_test");
  await expect(page.locator(".site-session-error")).toContainText("演示退出失败");
  await expect(page.locator(".topbar")).toBeVisible();
  await expect(page.getByRole("button", { name: "退出", exact: true })).toBeEnabled();
});
