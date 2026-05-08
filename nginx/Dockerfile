FROM node:22-alpine AS client-builder

WORKDIR /app

ARG NODE_ENV=production

RUN apk add --no-cache curl

COPY client/package.json client/package-lock.json* ./

RUN npm ci --legacy-peer-deps \
    && npm install --force @rollup/rollup-linux-x64-gnu @rollup/rollup-linux-arm64-gnu \
    && npm rebuild \
    && npm cache clean --force

COPY client/ ./

RUN if [ "$NODE_ENV" = "production" ]; then \
    npm run build; \
    else \
    mkdir -p /app/dist; \
    echo '<h1>Development Mode - Nginx Proxy Active</h1>' > /app/dist/index.html; \
    fi

FROM nginx:1.27-alpine

LABEL maintainer="VoiceAgent Team" \
    version="1.0" \
    description="Nginx Reverse Proxy with Vite HMR Support"

ARG NODE_ENV=production
ENV NODE_ENV=${NODE_ENV}

WORKDIR /etc/nginx

RUN mkdir -p /usr/share/nginx/html \
    && chown -R nginx:nginx /etc/nginx /var/cache/nginx /var/log/nginx /usr/share/nginx/html \
    && chmod -R 755 /etc/nginx \
    && touch /var/run/nginx.pid \
    && chown nginx:nginx /var/run/nginx.pid

USER nginx

COPY --chown=nginx:nginx nginx/config/proxy.conf ./
COPY --chown=nginx:nginx nginx/config/nginx.conf ./nginx.conf.prod
COPY --chown=nginx:nginx nginx/config/nginx-dev.conf ./nginx-dev.conf

RUN if [ "$NODE_ENV" = "production" ]; then \
    cp nginx.conf.prod nginx.conf; \
    else \
    cp nginx-dev.conf nginx.conf; \
    fi && rm nginx.conf.prod nginx-dev.conf

COPY --from=client-builder --chown=nginx:nginx /app/dist/ /usr/share/nginx/html/

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
