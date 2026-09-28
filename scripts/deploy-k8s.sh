#!/bin/sh
# Deploy one commit's images to the k3d cluster and smoke-test it (T-M8-010, ADR-0003, AD-065).
#   scripts/deploy-k8s.sh deploy <sha>   import <registry>/civic-station-*:<sha>, apply overlays/prod at <sha>
#   scripts/deploy-k8s.sh smoke  <sha>   through the Ingress: version == <sha>, POST 201, GET it back
# Env: REGISTRY (default ghcr.io/nu-abdulrehman), CLUSTER (default civic-station),
#      EXPECT_PROVIDER (fail if the live provider differs; with "llm", a rules:fallback triage
#      also fails, because a retired model otherwise looks healthy behind the 201 fallback).
set -eu

CMD=$1
SHA=$2
REGISTRY=${REGISTRY:-ghcr.io/nu-abdulrehman}
PROD_REGISTRY=ghcr.io/nu-abdulrehman # the newName committed in k8s/overlays/prod
CLUSTER=${CLUSTER:-civic-station}
NS=civic-station
BASE=http://127.0.0.1:8081
HOST="Host: civic-station.localhost"

deploy() {
    for svc in backend frontend; do
        img=$REGISTRY/civic-station-$svc:$SHA
        docker image inspect "$img" >/dev/null 2>&1 || docker pull "$img"
        k3d image import -c "$CLUSTER" "$img"
    done
    # A throwaway overlay over prod pins both images and APP_VERSION to the SHA; never :latest.
    # `name` must match the image as prod already rewrote it, not the base name.
    dir=k8s/overlays/.deploy-$SHA
    mkdir -p "$dir"
    cat > "$dir/kustomization.yaml" <<YAML
resources: [../prod]
images:
  - { name: $PROD_REGISTRY/civic-station-backend, newName: $REGISTRY/civic-station-backend, newTag: "$SHA" }
  - { name: $PROD_REGISTRY/civic-station-frontend, newName: $REGISTRY/civic-station-frontend, newTag: "$SHA" }
configMapGenerator:
  - { name: app-config, behavior: merge, literals: [APP_VERSION=$SHA] }
YAML
    if kubectl kustomize "$dir" | grep -q PLACEHOLDER_COMMIT_SHA; then
        echo "deploy: rendered manifests still contain PLACEHOLDER_COMMIT_SHA"; rm -rf "$dir"; exit 1
    fi
    kubectl apply -k "$dir"
    rm -rf "$dir"
    kubectl rollout status statefulset/postgres -n "$NS" --timeout=180s
    kubectl rollout status deployment/redis -n "$NS" --timeout=180s
    kubectl rollout status deployment/backend -n "$NS" --timeout=300s
    kubectl rollout status deployment/frontend -n "$NS" --timeout=180s
}

smoke() {
    # Old pods serve through their 5 s preStop after rollout status returns; poll, never sleep blind.
    i=0
    until [ "$(curl -s -H "$HOST" "$BASE/api/version" | python3 -c 'import json,sys; print(json.load(sys.stdin)["version"])' 2>/dev/null)" = "$SHA" ]; do
        i=$((i + 1)); [ "$i" -le 60 ] || { echo "smoke: /api/version never reported $SHA"; return 1; }
        sleep 1
    done
    code=$(curl -s -o /dev/null -w '%{http_code}' -H "$HOST" "$BASE/")
    [ "$code" = 200 ] || { echo "smoke: frontend / returned $code"; return 1; }
    # The SHA makes the text unique, so the triage cache cannot answer for the provider.
    created=$(curl -fsS -H "$HOST" -H 'Content-Type: application/json' -X POST "$BASE/api/complaints" \
        -d "{\"text\":\"CD smoke test $SHA: streetlight out on Main Street for three nights\",\"location\":\"Main Street\"}") \
        || { echo "smoke: POST /api/complaints failed"; return 1; }
    # Exact identity per provider: with llm, "rules:fallback" means the hosted model is not
    # answering, which a 201 would otherwise hide (handoff section 9).
    echo "$created" | python3 -c '
import json, os, sys
body = json.load(sys.stdin)
got = body["triaged_by"]
print("smoke: created", body["id"], "category=" + body["category"], "triaged_by=" + got)
want = {"llm": "llm:groq", "rules": "rules", "simulated": "simulated"}.get(os.environ.get("EXPECT_PROVIDER", ""))
if want and got != want:
    sys.exit("smoke: expected triaged_by=" + want + ", got " + got)
' || return 1
    id=$(echo "$created" | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
    curl -fsS -o /dev/null -H "$HOST" "$BASE/api/complaints/$id" || { echo "smoke: GET $id failed"; return 1; }
    if [ "${FORCE_SMOKE_FAILURE:-false}" = true ]; then
        echo "smoke: failing on purpose (force_smoke_failure)"; return 1
    fi
    echo "smoke: $SHA ok"
}

case $CMD in
    deploy) deploy ;;
    smoke) smoke ;;
    *) echo "usage: $0 deploy|smoke <sha>" >&2; exit 2 ;;
esac
