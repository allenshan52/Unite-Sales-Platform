/** 业务热力图浏览器验收：覆盖卖方成交、互斥采购意向热力模式和省份逐笔详情。 */

import { expect, test, type Page } from "@playwright/test";

import { installFakeAmap } from "./fake-amap";

const pageUrl = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3100";
const adminUsername = process.env.ADMIN_USERNAME;
const adminPassword = process.env.ADMIN_PASSWORD;

test.use({ launchOptions: { executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" } });

/** 使用真实服务端会话进入主站，业务数据则由用例路由精确控制。 */
async function loginAndOpenHeatmap(page: Page): Promise<void> {
  test.skip(!adminUsername || !adminPassword, "需要 ADMIN_USERNAME 与 ADMIN_PASSWORD 验收真实主站");
  await installFakeAmap(page);
  await page.context().clearCookies();
  await page.goto(pageUrl, { waitUntil: "networkidle" });
  await page.getByLabel("账号").fill(adminUsername!);
  await page.getByLabel("密码").fill(adminPassword!);
  await page.getByRole("button", { name: "进入网站" }).click();
  await expect(page.locator(".topbar")).toBeVisible();
  await page.getByRole("tab", { name: /全国成交热力地图/ }).click();
}

/** 为成交热力三个读取端点安装稳定模拟响应，保留登录与会话的真实链路。 */
async function mockHeatmapApi(page: Page): Promise<void> {
  await page.route("**/api/v1/public/deal-heatmap/sellers", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([
      { id: "unite", name: "优纳特", kind: "unite", website_url: null },
      { id: "competitor-1", name: "同行演示公司", kind: "competitor", website_url: "https://example.com" },
    ]),
  }));
  await page.route("**/api/v1/public/deal-heatmap/provinces**", (route) => {
    const url = new URL(route.request().url());
    const sellerId = url.searchParams.get("seller_id") ?? "unite";
    const year = url.searchParams.get("year");
    const province = decodeURIComponent(url.pathname.split("/").at(-1) ?? "");
    const isDetail = province !== "provinces";
    if (!isDetail) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          seller: sellerId === "unite" ? { id: "unite", name: "优纳特", kind: "unite", website_url: null } : { id: "competitor-1", name: "同行演示公司", kind: "competitor", website_url: "https://example.com" },
          available_years: [2026, 2025, 2024],
          provinces: sellerId === "unite"
            ? [
                { province: "江苏省", signed_amount: year === "2026" ? "1650000.00" : "4250000.00", signed_order_count: year === "2026" ? 1 : 2, intention_amount: "0.00", intention_count: 0 },
                { province: "四川省", signed_amount: "0.00", signed_order_count: 0, intention_amount: "760000.00", intention_count: 1 },
                { province: "浙江省", signed_amount: "0.00", signed_order_count: 0, intention_amount: "380000.00", intention_count: 1 },
              ]
            : [{ province: "江苏省", signed_amount: "680000.00", signed_order_count: 1, intention_amount: "0.00", intention_count: 0 }],
        }),
      });
    }
    const competitor = sellerId !== "unite";
    const uniteAmount = year === "2026" ? "1650000.00" : "4250000.00";
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        seller: competitor ? { id: "competitor-1", name: "同行演示公司", kind: "competitor", website_url: "https://example.com" } : { id: "unite", name: "优纳特", kind: "unite", website_url: null },
        province,
        signed_amount: competitor ? "680000.00" : province === "江苏省" ? uniteAmount : "0.00",
        signed_order_count: competitor || province === "江苏省" ? 1 : 0,
        orders: competitor || province === "江苏省" ? [{
          id: "00000000-0000-0000-0000-000000000001",
          customer_name: "华东检测中心（演示）",
          customer_province: competitor ? "江苏省" : null,
          customer_city: competitor ? "苏州市" : null,
          project_name: competitor ? "同行分析系统项目" : "优纳特实验室项目",
          amount: competitor ? "680000.00" : uniteAmount,
          signed_at: "2026-05-18",
          deal_type: "设备采购",
          product_name: competitor ? "分析工作站" : null,
          specification_model: competitor ? "AX-2026" : null,
          product_image_url: null,
          unit_price: competitor ? "340000.00" : null,
          source_type: competitor ? "公开信息" : null,
          source_reference: competitor ? "演示中标公告" : null,
          source_url: null,
          confidence: competitor ? "高" : null,
          notes: competitor ? "来源已由公开中标公告复核" : null,
        }] : [],
        intention_amount: province === "四川省" ? "760000.00" : "0.00",
        intention_count: province === "四川省" ? 1 : 0,
        intentions: province === "四川省" ? [{
          id: "00000000-0000-0000-0000-000000000002",
          customer_name: "西南科研院（演示）",
          title: "色谱平台采购意向",
          stage: "方案/报价",
          estimated_amount: "760000.00",
          next_action_at: "2026-09-12",
        }] : [],
      }),
    });
  });
}

test("成交金额与采购意向以互斥热力模式展示各自明细", async ({ page }) => {
  await mockHeatmapApi(page);
  await loginAndOpenHeatmap(page);

  const seller = page.getByLabel("选择成交公司");
  await expect(seller).toHaveValue("unite");
  await expect(seller.locator("option")).toHaveCount(2);
  await expect(page.getByRole("button", { name: "成交金额", exact: true })).toHaveAttribute("aria-pressed", "true");
  const year = page.getByLabel("成交年份");
  await expect(year).toHaveValue("");
  await expect(year.locator("option")).toHaveText(["全部年份", "2026 年", "2025 年", "2024 年"]);
  await expect(page.locator(".heatmap-color-legend").getByText("400万元+", { exact: true })).toBeVisible();
  await expect(page.locator(".heatmap-color-legend").getByText("1–150万元", { exact: true })).toBeVisible();
  const toolLayout = await page.evaluate(() => {
    const map = document.querySelector<HTMLElement>(".organization-heatmap-stage")?.getBoundingClientRect();
    const legend = document.querySelector<HTMLElement>(".heatmap-color-legend")?.getBoundingClientRect();
    const year = document.querySelector<HTMLElement>(".heatmap-year-filter")?.getBoundingClientRect();
    const zoom = document.querySelector<HTMLElement>(".heatmap-zoom")?.getBoundingClientRect();
    return {
      legendAtTopLeft: Boolean(map && legend && legend.left - map.left <= 24 && legend.top - map.top <= 24),
      yearAtBottomLeft: Boolean(map && year && year.left - map.left <= 24 && map.bottom - year.bottom <= 24),
      zoomAfterYear: Boolean(year && zoom && zoom.left > year.right && zoom.left - year.right <= 12),
      zoomAtBottomLeft: Boolean(map && zoom && zoom.left - map.left <= 24 && map.bottom - zoom.bottom <= 24),
    };
  });
  expect(toolLayout).toEqual({ legendAtTopLeft: true, yearAtBottomLeft: true, zoomAfterYear: true, zoomAtBottomLeft: false });

  const jiangsu = page.locator('.organization-heat-province[data-province="江苏省"]');
  await expect(jiangsu).toHaveCSS("fill", "rgb(169, 52, 32)");
  await jiangsu.click();
  const jiangsuDialog = page.getByRole("dialog", { name: "江苏省订单明细" });
  await expect(jiangsuDialog).toContainText("优纳特实验室项目");
  await expect(page.getByText("合同总金额", { exact: true })).toBeVisible();
  await expect(jiangsuDialog.getByText("¥4,250,000").first()).toBeVisible();
  await page.getByRole("button", { name: "关闭省份明细" }).click();

  await year.selectOption("2026");
  await expect(jiangsu).toHaveCSS("fill", "rgb(244, 176, 145)");
  await jiangsu.click();
  await expect(page.getByRole("dialog", { name: "江苏省订单明细" }).getByText("¥1,650,000").first()).toBeVisible();
  await page.getByRole("button", { name: "关闭省份明细" }).click();

  const intentionMode = page.getByRole("button", { name: "采购意向", exact: true });
  await intentionMode.click();
  await expect(intentionMode).toHaveAttribute("aria-pressed", "true");
  await expect(page.locator(".organization-intention-province")).toHaveCount(0);
  await expect(page.getByLabel("成交年份")).toHaveCount(0);
  await expect(page.getByText("当前有效意向", { exact: true })).toBeVisible();
  const intentionLegend = page.getByLabel("采购意向金额热力颜色图例");
  await expect(intentionLegend.getByText("0–15.2万元", { exact: true })).toBeVisible();
  await expect(intentionLegend.getByText("60.8–76万元", { exact: true })).toBeVisible();
  const sichuan = page.locator('.organization-heat-province[data-province="四川省"]');
  const zhejiang = page.locator('.organization-heat-province[data-province="浙江省"]');
  await expect(sichuan).toHaveCSS("fill", "rgb(20, 115, 95)");
  await expect(zhejiang).toHaveCSS("fill", "rgb(127, 197, 179)");
  await sichuan.click();
  const intentionDialog = page.getByRole("dialog", { name: "四川省采购意向明细" });
  await expect(intentionDialog).not.toContainText("成交订单");
  await expect(intentionDialog).toContainText("色谱平台采购意向");
  await expect(intentionDialog).toContainText("¥760,000");
});

test("切换同行后展示客户省市、官网、产品、来源和备注", async ({ page }) => {
  await mockHeatmapApi(page);
  await loginAndOpenHeatmap(page);

  await page.getByLabel("选择成交公司").selectOption("competitor-1");
  const jiangsu = page.locator('.organization-heat-province[data-province="江苏省"]');
  await expect(jiangsu).toHaveCSS("fill", "rgb(249, 217, 200)");
  await jiangsu.click();
  const dialog = page.getByRole("dialog", { name: "江苏省订单明细" });
  await expect(dialog).toContainText("同行分析系统项目");
  await expect(dialog).toContainText("分析工作站");
  await expect(dialog).toContainText("AX-2026");
  await expect(dialog).toContainText("¥340,000");
  await expect(dialog).toContainText("公开信息 · 置信度高");
  await expect(dialog).toContainText("江苏省 · 苏州市");
  await expect(dialog.getByRole("link", { name: "访问官网" })).toHaveAttribute("href", "https://example.com");
  await expect(dialog).toContainText("来源已由公开中标公告复核");
  await expect(dialog.getByRole("img", { name: "暂无产品图片" })).toBeVisible();
});

test("汇总接口错误可重试，并明确展示加载与空数据状态", async ({ page }) => {
  let summaryAttempt = 0;
  await page.route("**/api/v1/public/deal-heatmap/sellers", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([{ id: "unite", name: "优纳特", kind: "unite" }]),
  }));
  await page.route("**/api/v1/public/deal-heatmap/provinces**", async (route) => {
    summaryAttempt += 1;
    if (summaryAttempt === 1) {
      return route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "演示成交热力加载失败" }) });
    }
    await new Promise((resolve) => setTimeout(resolve, 400));
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ seller: { id: "unite", name: "优纳特", kind: "unite" }, available_years: [2026, 2025, 2024], provinces: [] }),
    });
  });

  await loginAndOpenHeatmap(page);
  const alert = page.getByRole("alert").filter({ hasText: "演示成交热力加载失败" });
  await expect(alert).toBeVisible();
  await alert.getByRole("button", { name: "重新加载" }).click();
  await expect(page.getByRole("status").filter({ hasText: "正在汇总省级成交金额" })).toBeVisible();
  await expect(page.getByText("所选公司暂无成交或采购意向数据。")).toBeVisible();
  await expect(page.getByLabel("成交年份")).toBeVisible();
  expect(summaryAttempt).toBe(2);
});
