/** 客户关系网络浏览器验收：覆盖真实数据库交互及加载、空数据、错误和移动布局状态。 */

import { expect, test } from "@playwright/test";

import { installFakeAmap } from "./fake-amap";

const pageUrl = process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3100";

test.use({ launchOptions: { executablePath: "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe" } });

/** 等待 React 完成 hydration 后切换地图入口，避免开发容器冷编译时吞掉首次点击。 */
async function openGroupNetwork(page: import("@playwright/test").Page): Promise<void> {
  await installFakeAmap(page);
  await page.goto(pageUrl, { waitUntil: "networkidle" });
  await page.getByRole("tab", { name: /客户关系网络/ }).click();
}

test("真实数据库集团可展开、查看单位并通过 Esc 重置", async ({ page }) => {
  await openGroupNetwork(page);
  const groupSelector = page.getByLabel("选择客户集团");
  await expect(groupSelector.locator("option")).toHaveCount(4);
  await expect(groupSelector).toHaveValue("");
  await groupSelector.selectOption({ label: "集团1" });
  await expect(page.getByRole("heading", { name: "集团1" })).toBeVisible();
  await expect.poll(() => page.evaluate(() => {
    const calls = (window as Window & { __fakeAmapFitCalls?: Array<{ overlayKinds: string[]; immediately: boolean; avoid: number[]; maxZoom: number }> }).__fakeAmapFitCalls ?? [];
    return calls.at(-1);
  })).toEqual({ overlayKinds: ["marker", "marker", "marker", "marker"], immediately: false, avoid: [150, 150, 280, 450], maxZoom: 10 });
  await expect(page.getByText(/共 3 家分支，已成交 1 家，活跃商机 3 家/)).toBeVisible();
  await expect(page.getByText("¥1,880,000")).toBeVisible();
  const treeRows = page.locator(".group-tree button");
  await expect(treeRows).toHaveCount(4);
  await expect(treeRows.first()).toContainText("集团1总部");
  await expect(treeRows.first()).toContainText("总部 · 浙江省 · 杭州市");
  await expect(treeRows.nth(1)).toContainText("1 级分支 · 上海市 · 上海市");
  const treeLayout = await treeRows.evaluateAll((rows) => rows.map((row) => {
    const name = row.querySelector<HTMLElement>("b");
    const dot = row.querySelector<HTMLElement>("i");
    return {
      top: row.getBoundingClientRect().top,
      nameFits: Boolean(name && name.scrollWidth <= name.clientWidth && name.scrollHeight <= name.clientHeight),
      dotColor: dot ? getComputedStyle(dot).backgroundColor : "",
    };
  }));
  expect(treeLayout.every((row, index) => row.nameFits && row.dotColor !== "rgba(0, 0, 0, 0)" && (index === 0 || row.top > treeLayout[index - 1].top))).toBe(true);
  await page.locator(".group-network-panel").getByRole("button", { name: /集团1一级分支1/ }).click();
  await expect(page.getByRole("button", { name: /返回集团概览/ })).toBeVisible();
  await expect(page.getByText("实际成交金额")).toBeVisible();
  await page.keyboard.press("Escape");
  await expect(groupSelector).toHaveValue("");
  await expect(page.getByRole("heading", { name: "集团1" })).toHaveCount(0);
});

test("集团选择器位于标题下方且地图缩放按钮横向排列", async ({ page }) => {
  await page.route("**/api/v1/public/customer-groups", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify([
      { id: "group-1", name: "集团1", color: "#2f8f72", headquarters: { id: "unit-1", name: "集团1总部", longitude: 116.4, latitude: 39.9 } },
      { id: "group-2", name: "集团2", color: "#f59e0b", headquarters: { id: "unit-2", name: "集团2总部", longitude: 121.47, latitude: 31.23 } },
      { id: "group-3", name: "集团3", color: "#3f7f5f", headquarters: { id: "unit-3", name: "集团3总部", longitude: 113.26, latitude: 23.13 } },
    ]),
  }));
  await openGroupNetwork(page);
  const selector = page.getByLabel("选择客户集团");
  const zoom = page.getByRole("group", { name: "地图缩放" });
  const zoomIn = zoom.getByRole("button", { name: "放大地图" });
  const zoomOut = zoom.getByRole("button", { name: "缩小地图" });
  await expect(selector).toBeVisible();
  await expect(zoom).toBeVisible();
  const headquartersPins = page.locator(".group-map-marker.is-headquarters");
  await expect(headquartersPins).toHaveCount(3);
  const pinLayout = await headquartersPins.first().evaluate((marker) => {
    const label = marker.querySelector<HTMLElement>("b");
    const pin = marker.querySelector<HTMLElement>("span");
    const glyph = marker.querySelector<HTMLElement>("em");
    const labelRect = label?.getBoundingClientRect();
    const pinRect = pin?.getBoundingClientRect();
    const glyphRect = glyph?.getBoundingClientRect();
    const bodyStyle = pin ? getComputedStyle(pin, "::before") : null;
    const tipStyle = pin ? getComputedStyle(pin, "::after") : null;
    return {
      width: pinRect?.width,
      height: pinRect?.height,
      labelAbovePin: Boolean(labelRect && pinRect && labelRect.bottom <= pinRect.top),
      circularBody: bodyStyle?.borderRadius,
      hasPoint: tipStyle?.content !== "none" && tipStyle?.backgroundColor !== "rgba(0, 0, 0, 0)",
      glyphOffset: pinRect && glyphRect ? [Math.round(glyphRect.left - pinRect.left), Math.round(glyphRect.top - pinRect.top)] : null,
      glyphSize: glyphRect ? [glyphRect.width, glyphRect.height] : null,
    };
  });
  expect(pinLayout).toEqual({ width: 32, height: 38, labelAbovePin: true, circularBody: "50%", hasPoint: true, glyphOffset: [1, 0], glyphSize: [30, 30] });

  const layout = await page.evaluate(() => {
    const cardElement = document.querySelector<HTMLElement>(".group-map-title-card");
    const card = cardElement?.getBoundingClientRect();
    const title = cardElement?.querySelector<HTMLElement>("h1")?.getBoundingClientRect();
    const selectorElement = document.querySelector<HTMLElement>(".group-map-selector")?.getBoundingClientRect();
    const map = document.querySelector<HTMLElement>(".home-group-network-map")?.getBoundingClientRect();
    const zoomElement = document.querySelector<HTMLElement>(".group-map-zoom")?.getBoundingClientRect();
    const buttons = Array.from(document.querySelectorAll<HTMLElement>(".group-map-zoom button")).map((button) => button.getBoundingClientRect());
    return {
      cardContainsSelector: Boolean(cardElement?.querySelector(".group-map-selector")),
      cardHasSurface: cardElement ? getComputedStyle(cardElement).backgroundColor !== "rgba(0, 0, 0, 0)" : false,
      cardFitsMap: Boolean(card && map && card.left >= map.left && card.right <= map.right),
      selectorBelowTitle: Boolean(title && selectorElement && selectorElement.top >= title.bottom),
      zoomAtBottomRight: Boolean(map && zoomElement && map.right - zoomElement.right <= 24 && map.bottom - zoomElement.bottom <= 24),
      zoomIsHorizontal: buttons.length === 2 && Math.abs(buttons[0].top - buttons[1].top) < 2 && buttons[1].left > buttons[0].left,
    };
  });
  expect(layout).toEqual({ cardContainsSelector: true, cardHasSurface: true, cardFitsMap: true, selectorBelowTitle: true, zoomAtBottomRight: true, zoomIsHorizontal: true });

  await zoomIn.click();
  await zoomOut.click();
  await expect.poll(() => page.evaluate(() => (window as Window & { __fakeAmapZoomCalls?: string[] }).__fakeAmapZoomCalls)).toEqual(["in", "out"]);

  await page.setViewportSize({ width: 390, height: 844 });
  await expect.poll(() => page.evaluate(() => {
    const card = document.querySelector<HTMLElement>(".group-map-title-card")?.getBoundingClientRect();
    const map = document.querySelector<HTMLElement>(".home-group-network-map")?.getBoundingClientRect();
    return Boolean(card && map && card.left >= map.left && card.right <= map.right);
  })).toBe(true);
});

test("总部接口加载、空数据和错误状态均有明确反馈", async ({ page }) => {
  await page.route("**/api/v1/public/customer-groups", async (route) => {
    await new Promise((resolve) => setTimeout(resolve, 700));
    await route.fulfill({ status: 200, contentType: "application/json", body: "[]" });
  });
  await openGroupNetwork(page);
  await expect(page.getByText("正在读取集团总部")).toBeVisible();
  await expect(page.getByText("暂无客户集团数据")).toBeVisible();

  await page.unroute("**/api/v1/public/customer-groups");
  await page.route("**/api/v1/public/customer-groups", (route) => route.fulfill({ status: 500, contentType: "application/json", body: JSON.stringify({ detail: "演示错误" }) }));
  await page.reload();
  await page.getByRole("tab", { name: /客户关系网络/ }).click();
  await expect(page.getByText("客户关系网络暂不可用")).toBeVisible();
  await expect(page.getByRole("button", { name: "重新加载" })).toBeVisible();
});

test("移动端关系面板保持在视口内且页面无横向溢出", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await openGroupNetwork(page);
  await page.getByLabel("选择客户集团").selectOption({ label: "集团1" });
  const panel = page.locator(".group-network-panel");
  await expect(panel).toBeVisible();
  await panel.scrollIntoViewIfNeeded();
  const metrics = await page.evaluate(() => {
    const panelElement = document.querySelector<HTMLElement>(".group-network-panel");
    const mapElement = document.querySelector<HTMLElement>(".home-group-network-map");
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
  });
  expect(metrics).toEqual({ documentFits: true, panelFitsMap: true, panelHeightFitsViewport: true });
});
