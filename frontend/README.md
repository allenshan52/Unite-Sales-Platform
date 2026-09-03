# 优纳特销售地图前端

基于 Next.js App Router、React、TypeScript 和 Tailwind CSS 的内部销售数据界面。业务 API 统一通过根目录网关访问；高德 Web JSAPI 请求由站内代理补充安全配置。

## 本地命令

请先在项目根目录完成 `.env` 配置和后端启动，再进入前端目录：

```powershell
Set-Location -LiteralPath 'D:\桌面\优纳特销售网站\frontend'
npm install
npm run dev
```

默认完整站点入口由根目录 `APP_PORT` 决定。生产构建和静态检查：

```powershell
npm run lint -- src tests
npx tsc --noEmit
npm run build
```

浏览器验收位于 `tests/`，默认读取 `PLAYWRIGHT_BASE_URL`；需要真实数据的用例还读取 `ADMIN_USERNAME` 和 `ADMIN_PASSWORD`。不要把 `.env.local`、密钥、`.next/`、`node_modules/` 或测试产物提交到 Git。
