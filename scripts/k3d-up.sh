#!/bin/sh
# Local cluster for M7/M9 (T-M7-001, T-M9-002, AD-028). Idempotent: safe to re-run.
# Bootstraps the cluster, builds and imports the :dev images, applies the dev overlay.
# Needs: docker, k3d, kubectl. Browse http://civic-station.localhost:8081 afterwards.
set -eu

CLUSTER=${CLUSTER:-civic-station}
NS=civic-station

sh "$(dirname "$0")/k3d-cluster.sh"

docker build -t civic-station-backend:dev backend
docker build -t civic-station-frontend:dev frontend
k3d image import -c "$CLUSTER" civic-station-backend:dev civic-station-frontend:dev

kubectl apply -k k8s/overlays/dev
kubectl rollout status statefulset/postgres -n "$NS" --timeout=180s
kubectl rollout status deployment/redis -n "$NS" --timeout=180s
kubectl rollout status deployment/backend -n "$NS" --timeout=300s
kubectl rollout status deployment/frontend -n "$NS" --timeout=180s

kubectl wait --for=condition=Available apiservice/v1beta1.metrics.k8s.io --timeout=120s
kubectl top nodes
