# Next.js 生产镜像：默认使用官方 Node；NODE_IMAGE 允许受控离线环境复用已审计的本地基础镜像。
ARG NODE_IMAGE=node:22-slim
FROM ${NODE_IMAGE} AS dependencies
USER root
WORKDIR /app
ENV NODE_ENV=development
COPY package.json package-lock.json ./
RUN npm ci --legacy-peer-deps

FROM ${NODE_IMAGE} AS builder
USER root
WORKDIR /app
ENV NODE_ENV=development
ARG NEXT_PUBLIC_AMAP_JSAPI_KEY
ENV NEXT_PUBLIC_AMAP_JSAPI_KEY=$NEXT_PUBLIC_AMAP_JSAPI_KEY
COPY --from=dependencies /app/node_modules ./node_modules
COPY . ./
RUN npm run build

FROM ${NODE_IMAGE} AS runner
USER root
WORKDIR /app
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV HOSTNAME=0.0.0.0
COPY --from=builder --chown=node:node /app/.next/standalone ./
COPY --from=builder --chown=node:node /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
