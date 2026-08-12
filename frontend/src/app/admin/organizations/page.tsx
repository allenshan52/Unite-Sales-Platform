/** 单位管理路由：组合受认证保护的审核工作台，不在页面中复制 API 或地图实现。 */

import { AdminOrganizationWorkspace } from "@/components/admin-organization-workspace";

/** 展示全国目标单位的列表核验、详情、审核和地图聚合工作台。 */
export default function OrganizationAdminPage() {
  return <AdminOrganizationWorkspace />;
}
