#!/bin/sh
# Timestamped scaling capture for T-M9-003 (FR-LOAD-002, AD-051). Runs until killed or for $1 seconds.
#   scripts/watch_scaling.sh <seconds> <out-prefix>
# Writes <out-prefix>hpa-watch.txt   `kubectl get hpa -w`, each line prefixed with a UTC timestamp
#        <out-prefix>scaling.csv     every 5 s: ts, cpu %, desired, current and Ready replicas
# Ready is recorded apart from the replica count because a pod counts as a replica before it can
# serve: capacity arrives later than the number rises (10-M9 §3).
set -eu

DURATION=$1
OUT=$2
NS=civic-station

kubectl get hpa backend -n "$NS" -w --output-watch-events=false 2>&1 \
    | while IFS= read -r line; do printf '%s %s\n' "$(date -u +%FT%TZ)" "$line"; done > "${OUT}hpa-watch.txt" &
WATCH=$!
trap 'kill $WATCH 2>/dev/null || true' EXIT INT TERM

echo "ts,cpu_percent,desired_replicas,current_replicas,ready_replicas" > "${OUT}scaling.csv"
end=$(( $(date +%s) + DURATION ))
while [ "$(date +%s)" -lt "$end" ]; do
    hpa=$(kubectl get hpa backend -n "$NS" -o jsonpath='{.status.currentMetrics[0].resource.current.averageUtilization},{.status.desiredReplicas},{.status.currentReplicas}' 2>/dev/null || echo ",,")
    ready=$(kubectl get deploy backend -n "$NS" -o jsonpath='{.status.readyReplicas}' 2>/dev/null || true)
    echo "$(date -u +%FT%TZ),$hpa,${ready:-0}" >> "${OUT}scaling.csv"
    sleep 5
done
