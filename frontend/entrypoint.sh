#!/bin/sh
# Renders the nginx config from the environment, then becomes nginx (ADR-0002, FR-FE-014).
set -eu

if [ -z "${BACKEND_ORIGIN:-}" ]; then
    echo "entrypoint: BACKEND_ORIGIN is not set (expected e.g. http://backend:8000)" >&2
    exit 1
fi
case "$BACKEND_ORIGIN" in
    http://*/ | https://*/ | *" "*)
        echo "entrypoint: BACKEND_ORIGIN must have no trailing slash or spaces: '$BACKEND_ORIGIN'" >&2
        exit 1 ;;
    http://?* | https://?*) ;;
    *)
        echo "entrypoint: BACKEND_ORIGIN must be http(s)://<host>:<port>, got '$BACKEND_ORIGIN'" >&2
        exit 1 ;;
esac

# THE build-once-deploy-many line (engineering-notes Q3): the backend address enters here, at
# container start, never at build time. The argument restricts substitution to one variable.
envsubst '${BACKEND_ORIGIN}' < /etc/nginx/templates/nginx.conf.template > /etc/nginx/conf.d/default.conf

exec nginx -g 'daemon off;'
