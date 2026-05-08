FROM node:22-alpine AS builder

WORKDIR /app

RUN apk add --no-cache curl

COPY package.json package-lock.json* ./

RUN npm ci --legacy-peer-deps --prefer-offline --no-audit

COPY . ./

ARG NODE_ENV="production"

RUN if [ "$NODE_ENV" = "production" ]; then \
    npm run build; \
    else \
    mkdir -p /app/dist; \
    echo '<h1>Development Mode - Nginx Proxy Active</h1>' > /app/dist/index.html; \
    fi

FROM node:22-alpine

LABEL maintainer="VoiceAgent Team" \
    version="1.0" \
    description="React Client - Vite Dev Server (dev) or Static Files (prod)"

WORKDIR /app

ARG NODE_ENV="production"
ENV NODE_ENV="${NODE_ENV}"

RUN apk add --no-cache curl

COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/dist ./dist
COPY . ./

EXPOSE 3000 5173

CMD ["sh", "-c", "if [ \"$NODE_ENV\" = \"production\" ]; then echo 'Production build complete'; sleep infinity; else npm run dev; fi"]
