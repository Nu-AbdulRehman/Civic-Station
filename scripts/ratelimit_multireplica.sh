#!/bin/sh
# Distributed rate-limiter proof (T-M9-008, T-M4-010, FR-CACHE-007, BR-CACHE-004).
#   scripts/ratelimit_multireplica.sh > docs/evidence/ratelimit-multireplica.txt
# With 4 backend replicas, 30 POSTs from one client inside one 60 s window must give exactly
# 10 x 201 and 20 x 429, each 429 with Retry-After. A per-process limiter would allow 40.
set -eu

NS=civic-station
BASE=http://127.0.0.1:8081
HOST="Host: civic-station.localhost"

# The HPA owns replicas, so pin its floor at 4 for the test rather than fighting it with scale.
kubectl patch hpa backend -n "$NS" -p '{"spec":{"minReplicas":4}}' >/dev/null
trap 'kubectl patch hpa backend -n "$NS" -p "{\"spec\":{\"minReplicas\":2}}" >/dev/null' EXIT
until [ "$(kubectl get deploy backend -n "$NS" -o jsonpath='{.status.readyReplicas}')" -ge 4 ] 2>/dev/null; do
    sleep 2
done

echo "# Distributed rate limiter, 4 replicas (T-M9-008, FR-CACHE-007). $(date -u +%FT%TZ)"
echo "# RATE_LIMIT_REQUESTS=10 per RATE_LIMIT_WINDOW_SECONDS=60, one client, through the Ingress."
echo '$ kubectl get pods -l app=backend'
kubectl get pods -n "$NS" -l app=backend
since=$(date -u +%FT%TZ)

# Start just after a window boundary so all 30 land in one fixed window.
while [ $(( $(date +%s) % 60 )) -gt 5 ]; do sleep 1; done
echo
echo "## 30 x POST /api/complaints"
i=1
while [ "$i" -le 30 ]; do
    out=$(curl -s -o /dev/null -D - -H "$HOST" -H 'Content-Type: application/json' -X POST \
        "$BASE/api/complaints" \
        -d "{\"text\":\"Rate limit probe $i: water leak outside house $i\",\"location\":\"Block $i\"}" \
        | tr -d '\r')
    code=$(echo "$out" | awk 'NR==1{print $2}')
    retry=$(echo "$out" | awk -F': ' 'tolower($1)=="retry-after"{print $2}')
    echo "request $i: $code${retry:+ Retry-After=$retry}"
    echo "$code" >> /tmp/ratelimit-codes.$$
    i=$((i + 1))
done

echo
echo "## Totals"
sort /tmp/ratelimit-codes.$$ | uniq -c
rm -f /tmp/ratelimit-codes.$$

# Which pod answered: the requests were spread across replicas, so one process could not have
# counted them all. Each pod logs one request.completed line per POST.
echo
echo "## POSTs answered per pod"
for pod in $(kubectl get pods -n "$NS" -l app=backend -o name); do
    n=$(kubectl logs "$pod" -n "$NS" -c backend --since-time="$since" | python3 -c '
import json, sys
n = 0
for line in sys.stdin:
    try:
        e = json.loads(line)
    except ValueError:
        continue
    n += e.get("msg") == "request.completed" and e.get("method") == "POST" and e.get("path") == "/api/complaints"
print(n)')
    echo "$pod: $n"
done
