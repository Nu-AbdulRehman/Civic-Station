#!/bin/sh
# Cluster bootstrap shared by local dev (scripts/k3d-up.sh) and CD (cd.yml deploy-k8s).
# Idempotent. Creates the k3d cluster, the VPA recommender, the namespace and the Secret.
# Env: CLUSTER (default civic-station), GROQ_API_KEY, POSTGRES_PASSWORD (both optional).
set -eu

CLUSTER=${CLUSTER:-civic-station}
NS=civic-station
VPA_REF=vertical-pod-autoscaler-1.8.0
VPA_RAW=https://raw.githubusercontent.com/kubernetes/autoscaler/$VPA_REF/vertical-pod-autoscaler/deploy

# Two agents so pod spreading, PDBs and node drains mean something. k3s bundles Traefik (the
# Ingress controller, AD-028) and metrics-server (the HPA's metric source).
if ! k3d cluster list "$CLUSTER" >/dev/null 2>&1; then
    k3d cluster create "$CLUSTER" --agents 2 -p "8081:80@loadbalancer" --wait
fi
kubectl config use-context "k3d-$CLUSTER" >/dev/null

# VPA in recommender mode needs only the CRDs, RBAC and the recommender (updateMode "Off").
kubectl apply -f "$VPA_RAW/vpa-v1-crd-gen.yaml" -f "$VPA_RAW/vpa-rbac.yaml" -f "$VPA_RAW/recommender-deployment.yaml"

kubectl create namespace "$NS" --dry-run=client -o yaml | kubectl apply -f -
# Real Secret, created once (AD-027, AD-064). Never re-created: the postgres PVC keeps the
# password it was initialised with. Hex, so it is safe inside DATABASE_URL.
if ! kubectl get secret app-secrets -n "$NS" >/dev/null 2>&1; then
    kubectl create secret generic app-secrets -n "$NS" \
        --from-literal=POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-$(od -An -tx1 -N16 /dev/urandom | tr -d ' \n')}" \
        --from-literal=GROQ_API_KEY="${GROQ_API_KEY:-}"
fi
