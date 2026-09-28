# syntax=docker/dockerfile:1
# Frontend image (T-M6-003, FR-CTR-002, NFR-PORT-002). Build with Node, serve with nginx; the
# final stage holds only dist/, the template and the entrypoint. No backend URL is baked in:
# BACKEND_ORIGIN is read at container start (ADR-0002, FR-FE-014).

FROM node:22.23.3-alpine3.24 AS build
WORKDIR /src
COPY package.json package-lock.json ./
RUN npm ci
# tests/ stays in the context: `npm run build` type-checks it (tsconfig include).
COPY . .
RUN npm run build

# -slim: no njs/acme modules, ~15 MB unpacked against the 60 MB gate (NFR-PERF-007, AD-063).
FROM nginx:1.30.5-alpine3.24-slim AS runtime
# Non-root nginx (07-M6 §2.2): drop the `user` directive, move the pid file and every temp path
# into /tmp, and let uid 101 write the one file the entrypoint renders.
RUN sed -i \
        -e '/^user /d' \
        -e 's|^pid .*|pid /tmp/nginx.pid;|' \
        -e 's|^http {|http {\n    client_body_temp_path /tmp/client_temp;\n    proxy_temp_path /tmp/proxy_temp;\n    fastcgi_temp_path /tmp/fastcgi_temp;\n    uwsgi_temp_path /tmp/uwsgi_temp;\n    scgi_temp_path /tmp/scgi_temp;|' \
        /etc/nginx/nginx.conf \
    && rm -f /etc/nginx/conf.d/default.conf \
    && chown 101:101 /etc/nginx/conf.d
COPY nginx.conf.template /etc/nginx/templates/nginx.conf.template
COPY --chmod=755 entrypoint.sh /entrypoint.sh
# ponytail: dist/ stays root-owned (read-only to uid 101), stricter than the chown in 07-M6 §2.2.
COPY --from=build /src/dist /usr/share/nginx/html
USER 101
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
    CMD ["wget", "-q", "-O", "/dev/null", "http://127.0.0.1:8080/"]
ENTRYPOINT ["/entrypoint.sh"]
