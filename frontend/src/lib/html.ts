/** 地图 HTML 安全工具：统一转义写入高德自定义覆盖物的数据库文本。 */

/** 转义 HTML 文本及双引号属性边界，防止异常名称破坏覆盖物结构。 */
export function escapeHtml(value: string): string {
  return value
    .replaceAll("&", "&amp;")
    .replaceAll('"', "&quot;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}
