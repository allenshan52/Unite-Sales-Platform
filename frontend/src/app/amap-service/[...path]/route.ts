/**
 * 高德服务端代理路由：将浏览器请求转发至 restapi.amap.com，并仅在服务端注入安全密钥。
 * 使用 NextRequest/NextResponse，避免将安全密钥暴露给客户端代码。
 */
import { NextRequest, NextResponse } from "next/server";

const AMAP_SERVICE_ORIGIN = "https://restapi.amap.com";

type RouteContext = {
  params: Promise<{ path: string[] }>;
};

/** 转发 GET 请求、过滤客户端传入的 jscode，并透传上游响应状态。 */
export async function GET(request: NextRequest, { params }: RouteContext) {
  const securityJsCode = process.env.AMAP_SECURITY_JS_CODE;

  if (!securityJsCode) {
    return NextResponse.json(
      { message: "AMap proxy is not configured." },
      { status: 503 },
    );
  }

  const { path } = await params;
  const targetUrl = new URL(`/${path.map(encodeURIComponent).join("/")}`, AMAP_SERVICE_ORIGIN);

  request.nextUrl.searchParams.forEach((value, key) => {
    if (key !== "jscode") {
      targetUrl.searchParams.append(key, value);
    }
  });
  targetUrl.searchParams.set("jscode", securityJsCode);

  let upstream: Response;

  try {
    upstream = await fetch(targetUrl, {
      headers: { accept: request.headers.get("accept") ?? "application/json" },
      cache: "no-store",
      // 开发环境回退代理也必须终止失联上游，避免占满 Next.js 请求槽位。
      signal: AbortSignal.timeout(10_000),
    });
  } catch {
    return NextResponse.json(
      { message: "AMap proxy upstream is unavailable." },
      { status: 502 },
    );
  }

  return new NextResponse(upstream.body, {
    status: upstream.status,
    headers: {
      "cache-control": "no-store",
      "content-type": upstream.headers.get("content-type") ?? "application/json; charset=utf-8",
    },
  });
}
