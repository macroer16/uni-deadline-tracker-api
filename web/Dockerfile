# ---- Build the static site ----
FROM node:22-alpine AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

# ---- Serve it with nginx as a non-root user ----
FROM nginxinc/nginx-unprivileged:1.29-alpine
ENV API_UPSTREAM=http://api:8000
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY --from=build /web/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD wget -q -O /dev/null http://127.0.0.1:8080/healthz || exit 1
