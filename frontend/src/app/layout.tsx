/**
 * Next.js App Router 根布局：导入全局样式并定义页面元数据与中文页面语言。
 * 使用 Next.js Metadata 类型，不承载业务状态或数据请求。
 */
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = { title: "Unite Sales · 销售态势中心", description: "优纳特销售数据可视化演示" };

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="zh-CN"><body>{children}</body></html>;
}
