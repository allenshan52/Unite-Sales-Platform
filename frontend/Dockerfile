# Next.js 生产镜像：在容器内安装锁定依赖，并把公开高德 Web Key 编译进浏览器包。
FROM node:22-slim AS dependencies
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

FROM node:22-slim AS builder
WORKDIR /app
ARG NEXT_PUBLIC_AMAP_JSAPI_KEY
ENV NEXT_PUBLIC_AMAP_JSAPI_KEY=$NEXT_PUBLIC_AMAP_JSAPI_KEY
COPY --from=dependencies /app/node_modules ./node_modules
COPY . ./
RUN npm run build

FROM node:22-slim AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
