"""Measurements behind docs/TRIAGE.md (T-M5-013, AD-052, NFR-PERF-004). Run from backend/:

uv run python ../scripts/measure_triage.py provider --out ../docs/evidence/triage-<name>.json
    Runs the 30 seeded complaints through the pipeline for TRIAGE_PROVIDER (with the usual
    timeout, retry and fallback, and an empty cache so every row costs a real call).
    Prints median/p95 latency, the fallback rate, and agreement with the seed's hand labels.

uv run python ../scripts/measure_triage.py compare a.json b.json
    Category and priority agreement between two provider runs (Groq vs Ollama).

uv run python ../scripts/measure_triage.py cache --base-url http://<host>:<port>
    The NFR-PERF-004 population against a running stack: the 30 seeded complaints
    resubmitted once each, then 20 manual submissions of which 10 are deliberate
    duplicates. Hit rate = triage_cache_hits_total / (hits + misses), from /metrics.
    Needs RATE_LIMIT_REQUESTS >= 50 on that stack for the run.
"""

import argparse
import asyncio
import json
import statistics
import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.config import load_settings  # noqa: E402
from app.observability.logging import configure_logging  # noqa: E402
from app.providers.triage.factory import build_triage_provider  # noqa: E402
from app.providers.triage.pipeline import TriagePipeline  # noqa: E402
from seeds.complaints import SEED  # noqa: E402


class _NoCache:
    async def get(self, key: str) -> None:
        return None

    async def set(self, *args: object) -> None:
        return None


class _NoOutcomes:
    async def record(self, outcome: object) -> None:
        return None

    async def recent(self) -> list[object]:
        return []


def _percentile(values: list[float], p: float) -> float:
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, round(p * (len(ordered) - 1)))]


async def _run_provider(interval: float) -> list[dict[str, Any]]:
    settings = load_settings()
    provider = build_triage_provider(settings)
    pipeline = TriagePipeline(
        provider,
        _NoCache(),  # type: ignore[arg-type]
        _NoOutcomes(),  # type: ignore[arg-type]
        timeout_seconds=settings.triage_timeout_seconds,
        prompt_version=settings.prompt_version,
    )
    rows = []
    for i, (text, location, category, priority, _status, _contact) in enumerate(SEED):
        if i and interval:
            # Pace under the provider's quota: a 429 here would measure the quota, not the model.
            await asyncio.sleep(interval)
        outcome = await pipeline.run(text, location)
        rows.append(
            {
                "text": text,
                "label_category": category,
                "label_priority": priority,
                "category": outcome.result.category.value,
                "priority": outcome.result.priority.value,
                "triaged_by": outcome.triaged_by.value,
                "fallback": outcome.fallback,
                "error_class": outcome.error_class.value if outcome.error_class else None,
                "latency_ms": outcome.latency_ms,
            }
        )
    return rows


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    latencies = [float(r["latency_ms"]) for r in rows]
    n = len(rows)
    return {
        "n": n,
        "provider": rows[0]["triaged_by"] if rows else None,
        "latency_ms_p50": statistics.median(latencies),
        "latency_ms_p95": _percentile(latencies, 0.95),
        "fallback_rate": sum(r["fallback"] for r in rows) / n,
        "fallback_error_classes": sorted({r["error_class"] for r in rows if r["error_class"]}),
        "agreement_with_labels_category": sum(r["category"] == r["label_category"] for r in rows)
        / n,
        "agreement_with_labels_priority": sum(r["priority"] == r["label_priority"] for r in rows)
        / n,
    }


def cmd_provider(out: Path, interval: float) -> None:
    rows = asyncio.run(_run_provider(interval))
    summary = _summary(rows)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        json.dumps({"summary": summary, "rows": rows}, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


def cmd_compare(a: Path, b: Path) -> None:
    rows_a = json.loads(a.read_text(encoding="utf-8"))["rows"]
    rows_b = json.loads(b.read_text(encoding="utf-8"))["rows"]
    pairs = list(zip(rows_a, rows_b, strict=True))
    print(json.dumps({
        "n": len(pairs),
        "category_agreement": sum(x["category"] == y["category"] for x, y in pairs) / len(pairs),
        "priority_agreement": sum(x["priority"] == y["priority"] for x, y in pairs) / len(pairs),
    }, indent=2))  # fmt: skip


MANUAL_UNIQUE = [
    (
        "Transformer sparking near Numaish chowrangi, whole block without light since night",
        "Numaish",
    ),
    ("Main road caved in near the underpass, cars cannot pass, huge hole", "Shahrah-e-Faisal"),
    ("Water tanker charging double rate, line water not coming for a week", "Malir Cantt"),
    ("Garbage truck has not come to our lane for two weeks, stray dogs everywhere", "Gulbahar"),
    ("Streetlights on the bridge not working, accidents at night", "Lyari Expressway"),
    ("Sewerage line choked, dirty water coming back into houses", "Korangi No. 5"),
    ("Illegal wall built on the footpath by a shop, people walking on the road", "Tariq Road"),
    ("Electric pole leaning dangerously after the rain, wires very low", "Orangi Sector 5"),
    ("Park lights broken and benches stolen, children cannot play in evening", "Gulshan Block 2"),
    ("No water pressure on upper floors since the new pipeline work started", "Clifton Block 9"),
]


def cmd_cache(base_url: str) -> None:
    import httpx

    def counters(client: httpx.Client) -> tuple[float, float]:
        text = client.get("/metrics").text
        values = {}
        for line in text.splitlines():
            for name in ("triage_cache_hits_total", "triage_cache_misses_total"):
                if line.startswith(name + " "):
                    values[name] = float(line.split()[1])
        return values.get("triage_cache_hits_total", 0.0), values.get(
            "triage_cache_misses_total", 0.0
        )

    population = [(text, location) for text, location, *_ in SEED]
    population += MANUAL_UNIQUE
    # Ten deliberate duplicates: five manual repeats and five seed texts with new casing and
    # spacing, which normalisation must fold onto the same key (AD-019).
    population += MANUAL_UNIQUE[:5]
    population += [(f"  {t.upper()}  ", loc) for t, loc, *_ in SEED[:5]]

    with httpx.Client(base_url=base_url, timeout=40) as client:
        hits0, misses0 = counters(client)
        statuses = [
            client.post("/api/complaints", json={"text": t, "location": loc}).status_code
            for t, loc in population
        ]
        hits1, misses1 = counters(client)
    hits, misses = hits1 - hits0, misses1 - misses0
    print(json.dumps({
        "submissions": len(population),
        "created": statuses.count(201),
        "other_statuses": sorted(set(statuses) - {201}),
        "hits": hits,
        "misses": misses,
        "hit_rate": hits / (hits + misses) if hits + misses else None,
    }, indent=2))  # fmt: skip


def main() -> None:
    configure_logging("WARNING", stream=sys.stderr)  # the measurement goes to stdout alone
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("provider")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--interval", type=float, default=0.0, help="seconds between calls")
    c = sub.add_parser("compare")
    c.add_argument("a", type=Path)
    c.add_argument("b", type=Path)
    k = sub.add_parser("cache")
    k.add_argument("--base-url", required=True)
    args = parser.parse_args()
    if args.command == "provider":
        cmd_provider(args.out, args.interval)
    elif args.command == "compare":
        cmd_compare(args.a, args.b)
    else:
        cmd_cache(args.base_url)


if __name__ == "__main__":
    main()
