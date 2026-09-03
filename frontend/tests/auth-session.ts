/** Playwright 真实会话助手：每个测试文件只登录一次，再向隔离上下文分发同一组 Cookie。 */

import { expect, type Browser, type BrowserContext } from "@playwright/test";

export type AuthCookies = Awaited<ReturnType<BrowserContext["cookies"]>>;

let cachedSession: AuthCookies | null = null;

/** 通过真实登录页创建一组授权 Cookie，避免同文件用例重复触发网关登录限流。 */
export async function createAdminSession(
  browser: Browser,
  baseUrl: string,
  username: string,
  password: string,
): Promise<AuthCookies> {
  if (cachedSession) return cachedSession;
  const context = await browser.newContext();
  const page = await context.newPage();
  try {
    for (let attempt = 0; attempt < 5; attempt += 1) {
      await page.goto(baseUrl, { waitUntil: "networkidle" });
      await page.getByLabel("账号").fill(username);
      await page.getByLabel("密码").fill(password);
      const loginResponse = page.waitForResponse((response) => response.url().endsWith("/api/v1/auth/login"));
      await page.getByRole("button", { name: "进入网站" }).click();
      const response = await loginResponse;
      if (response.ok()) {
        await expect(page.locator(".topbar")).toBeVisible();
        cachedSession = await context.cookies();
        return cachedSession;
      }
      if (response.status() !== 429) throw new Error(`测试登录失败，HTTP ${response.status()}`);
      await page.waitForTimeout(13_000);
    }
    throw new Error("测试登录持续触发网关限流，请稍后重试");
  } finally {
    await context.close();
  }
}
