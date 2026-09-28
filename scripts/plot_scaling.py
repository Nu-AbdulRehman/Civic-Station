# /// script
# requires-python = "==3.12.*"
# dependencies = ["matplotlib==3.11.2"]
# ///
"""Replicas against offered load, from committed inputs (T-M9-004, AD-044, AD-051).

    uv run scripts/plot_scaling.py <k6-raw.json> <scaling.csv> <out-prefix>

Reads k6's raw `--out json` stream and the 5 s samples from `scripts/watch_scaling.sh`, writes
`<out-prefix>k6-timeseries.csv` (one row per second: VUs, requests, failures, p95 latency) and
`<out-prefix>replicas-vs-load.png`, and prints the lag from load arriving to replicas rising and to
capacity (Ready pods) arriving. The raw k6 file is large and stays out of git; the per-second CSV
it reduces to is the committed input, so the chart regenerates with `--from-csv`:

    uv run scripts/plot_scaling.py --from-csv <k6-timeseries.csv> <scaling.csv> <out-prefix>
"""

import csv
import json
import sys
from collections import defaultdict
from datetime import datetime

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402


def ts(value: str) -> float:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def reduce_k6(raw_path: str) -> list[dict[str, float]]:
    """Per-second rows from k6's JSON lines: max VUs, request count, failures, p95 duration."""
    buckets: dict[int, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    with open(raw_path, encoding="utf-8") as f:
        for line in f:
            point = json.loads(line)
            if point.get("type") != "Point":
                continue
            metric, data = point["metric"], point["data"]
            if metric in ("vus", "http_reqs", "http_req_failed", "http_req_duration"):
                buckets[int(ts(data["time"]))][metric].append(float(data["value"]))
    rows = []
    for second in sorted(buckets):
        b = buckets[second]
        durations = sorted(b["http_req_duration"])
        p95 = durations[int(0.95 * (len(durations) - 1))] if durations else 0.0
        rows.append({
            "epoch": second,
            "vus": max(b["vus"], default=0.0),
            "requests": sum(b["http_reqs"]),
            "failed": sum(b["http_req_failed"]),
            "p95_ms": round(p95, 1),
        })
    return rows


def main(argv: list[str]) -> None:
    from_csv = argv[:1] == ["--from-csv"]
    if from_csv:
        argv = argv[1:]
    source, scaling_path, out = argv
    if from_csv:
        with open(source, encoding="utf-8") as f:
            load = [{k: float(v) for k, v in row.items()} for row in csv.DictReader(f)]
    else:
        load = reduce_k6(source)
        with open(f"{out}k6-timeseries.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["epoch", "vus", "requests", "failed", "p95_ms"])
            writer.writeheader()
            writer.writerows(load)

    with open(scaling_path, encoding="utf-8") as f:
        samples = [r for r in csv.DictReader(f) if r["desired_replicas"]]

    t0 = load[0]["epoch"]
    lt = [r["epoch"] - t0 for r in load]
    st = [ts(r["ts"]) - t0 for r in samples]
    desired = [int(r["desired_replicas"]) for r in samples]
    ready = [int(r["ready_replicas"] or 0) for r in samples]
    cpu = [float(r["cpu_percent"]) if r["cpu_percent"] else float("nan") for r in samples]

    fig, (top, bottom) = plt.subplots(2, 1, sharex=True, figsize=(11, 7))
    top.plot(lt, [r["requests"] for r in load], color="#3b6fb6", lw=0.8, label="requests/s")
    top.set_ylabel("requests / s")
    vus = top.twinx()
    vus.plot(lt, [r["vus"] for r in load], color="#999999", lw=1.5, label="virtual users")
    vus.set_ylabel("virtual users")
    top.set_title("Offered load (k6) against backend replicas (HPA)")
    top.legend(loc="upper left")
    vus.legend(loc="upper right")

    bottom.step(st, desired, where="post", color="#c0392b", lw=1.8, label="desired replicas (HPA)")
    bottom.step(st, ready, where="post", color="#27ae60", lw=1.8, ls="--", label="Ready replicas")
    bottom.set_ylabel("replicas")
    bottom.set_xlabel("seconds since the load test started")
    pct = bottom.twinx()
    pct.plot(st, cpu, color="#8e44ad", lw=0.9, alpha=0.7, label="CPU % of request")
    pct.axhline(60, color="#8e44ad", ls=":", lw=0.8)
    pct.set_ylabel("CPU utilisation, % of request")
    bottom.legend(loc="upper left")
    pct.legend(loc="upper right")
    fig.tight_layout()
    fig.savefig(f"{out}replicas-vs-load.png", dpi=120)

    start = next(t for t, r in zip(lt, load, strict=True) if r["vus"] > 0)
    base = desired[0]
    up = next((t for t, d in zip(st, desired, strict=True) if d > base), None)
    cap = next((t for t, r in zip(st, ready, strict=True) if r > base), None)
    print(f"load starts at t={start:.0f}s; replicas {base} -> max {max(desired)}")
    if up is not None and cap is not None:
        print(f"desired replicas rise at t={up:.0f}s (lag {up - start:.0f}s); "
              f"Ready capacity at t={cap:.0f}s (lag {cap - start:.0f}s)")


if __name__ == "__main__":
    main(sys.argv[1:])
