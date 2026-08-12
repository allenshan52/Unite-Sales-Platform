/** Next.js 配置：将浏览器的高德安全代理前缀重写到同应用内的 Route Handler。 */
import type { NextConfig } from "next";

const backendApiOrigin = process.env.BACKEND_API_ORIGIN ?? "http://localhost:8000";

const nextConfig: NextConfig = {
  // 生产容器只复制 Next.js 追踪到的运行文件，避免携带完整开发依赖。
  output: "standalone",
  /** 保持公开代理地址稳定，同时不暴露后端路由实现细节。 */
  async rewrites() {
    return [
      // 本地开发保持 API 同源，管理员会话 cookie 无需跨域配置。
      {
        source: "/api/v1/:path*",
        destination: `${backendApiOrigin}/api/v1/:path*`,
      },
      {
        source: "/_AMapService/:path*",
        destination: "/amap-service/:path*",
      },
    ];
  },
};

export default nextConfig;
