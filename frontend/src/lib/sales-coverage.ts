/** 销售覆盖表单配置：复用后端固定的四级范围与七个大区业务口径。 */

import type { SalesCoverageLevel } from "@/lib/api";

export const salesCoverageLevels: SalesCoverageLevel[] = ["市", "省", "大区", "全国"];

export const salesRegionProvinces = {
  浙江区: ["浙江", "江西"],
  东区: ["江苏", "安徽", "上海", "山东", "河南"],
  北区: ["黑龙江", "辽宁", "吉林", "内蒙古", "河北", "山西", "天津", "北京"],
  西区: ["云南", "贵州", "湖南", "湖北", "四川", "重庆"],
  南区: ["广西", "广东", "福建", "海南"],
  西北: ["陕西", "甘肃", "宁夏", "青海"],
  其他: ["新疆", "西藏"],
} as const;

export const salesRegions = Object.keys(salesRegionProvinces);
export const salesProvinces = Array.from(new Set(Object.values(salesRegionProvinces).flat()));

const provinceAliases: Record<string, string> = {
  北京市: "北京", 天津市: "天津", 上海市: "上海", 重庆市: "重庆",
  内蒙古自治区: "内蒙古", 广西壮族自治区: "广西", 西藏自治区: "西藏",
  宁夏回族自治区: "宁夏", 新疆维吾尔自治区: "新疆",
};

/** 把历史省级全称转换为当前下拉使用的短名称。 */
export function canonicalSalesProvince(province: string | null): string {
  if (!province) return "";
  if (provinceAliases[province]) return provinceAliases[province];
  if (province.endsWith("省")) return province.slice(0, -1);
  return province;
}

/** 返回大区所含省份的可读说明，未选择时保持为空。 */
export function salesRegionDescription(region: string): string {
  return region in salesRegionProvinces
    ? salesRegionProvinces[region as keyof typeof salesRegionProvinces].join("、")
    : "";
}
