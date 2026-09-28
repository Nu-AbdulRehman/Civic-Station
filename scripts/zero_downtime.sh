#!/bin/sh
# Zero-downtime rolling update under load (T-M9-009, FR-LOAD-004, NFR-REL-003).
#   scripts/zero_downtime.sh <new-image> > docs/evidence/zero-downtime-rollout.txt
# Runs k6 at 40 VUs for 150 s, swaps the backend image 30 s in, and reports k6's failed-request
# count next to the number of requests attempted: zero failures means nothing without the total.
set -eu

IMAGE=$1
NS=civic-station
SUMMARY=${TMPDIR:-/tmp}/zero-downtime-summary.json

echo "# Zero-downtime rollout under load (T-M9-009, FR-LOAD-004). $(date -u +%FT%TZ)"
echo "# k6 PROFILE=plateau, 40 VUs for 150 s through the Ingress; 'kubectl set image' at t=30 s."
echo "# maxSurge 1 / maxUnavailable 0, preStop sleep 5, terminationGracePeriodSeconds 30."
echo '$ kubectl get deploy backend -o image (before)'
kubectl get deploy backend -n "$NS" -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'

PROFILE=plateau PLATEAU_SECONDS=150 k6 run -q load/k6-script.js --summary-export "$SUMMARY" \
    > "${SUMMARY%.json}.log" 2>&1 &
K6=$!
sleep 30
echo
echo "\$ kubectl set image deployment/backend backend=$IMAGE"
kubectl set image deployment/backend -n "$NS" "backend=$IMAGE"
kubectl rollout status deployment/backend -n "$NS" --timeout=300s
echo '$ kubectl get deploy backend -o image (after)'
kubectl get deploy backend -n "$NS" -o jsonpath='{.spec.template.spec.containers[0].image}{"\n"}'
wait $K6 || true

echo
echo "## k6 result"
python3 - "$SUMMARY" <<'PY'
import json, sys
m = json.load(open(sys.argv[1]))["metrics"]
reqs = int(m["http_reqs"]["count"])
failed = int(m["http_req_failed"]["passes"])  # Rate metric: passes = requests that failed
d = m["http_req_duration"]
print(f"requests attempted: {reqs}")
print(f"requests failed:    {failed}")
print(f"latency p95: {d['p(95)']:.0f} ms, max: {d['max']:.0f} ms")
PY
