FROM node:24.22.2-bookworm-slim
ENV NODE_ENV=production
WORKDIR /app
COPY package.json package-lock.json ./
COPY apps/web/package.json apps/web/package.json
COPY services/api/package.json services/api/package.json
COPY services/scanner/package.json services/scanner/package.json
COPY packages/runtime/package.json packages/runtime/package.json
COPY packages/contracts/package.json packages/contracts/package.json
RUN npm ci --omit=dev --ignore-scripts
COPY packages/runtime packages/runtime
COPY packages/contracts packages/contracts
COPY services/api services/api
COPY services/scanner services/scanner
USER node
CMD ["node", "services/api/src/index.js"]
