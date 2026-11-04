FROM node:24.22.2-bookworm-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY services/api/package.json services/api/package.json
COPY services/scanner/package.json services/scanner/package.json
COPY packages/runtime/package.json packages/runtime/package.json
RUN npm ci
COPY apps/web apps/web
RUN npm run build --workspace @ai-security/web

FROM nginx:1.30.6-alpine
COPY docker/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/apps/web/dist /usr/share/nginx/html
USER nginx
EXPOSE 8080
ENTRYPOINT ["nginx", "-g", "daemon off;"]
