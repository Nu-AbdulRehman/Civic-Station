// Load profile for the HPA, VPA and zero-downtime evidence (T-M9-001, FR-LOAD-001, AD-017, AD-050).
// GETs only, so the POST rate limiter stays fully armed during the demonstration.
//   k6 run load/k6-script.js --out json=<raw.json>
// Env: BASE_URL (default http://127.0.0.1:8081), HOST_HEADER (default civic-station.localhost),
//      PROFILE=scaling (default, the AD-050 stages) | plateau (40 VUs for PLATEAU_SECONDS, default 120).
import http from "k6/http";
import { check } from "k6";

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8081";
const PARAMS = { headers: { Host: __ENV.HOST_HEADER || "civic-station.localhost" } };

const STAGES = {
  scaling: [
    { duration: "60s", target: 40 }, // ramp: makes the lag visible
    { duration: "180s", target: 40 }, // plateau above the 60 % CPU target
    { duration: "30s", target: 0 }, // ramp down
    { duration: "330s", target: 0 }, // idle > the 300 s scale-down window
  ],
  plateau: [{ duration: `${__ENV.PLATEAU_SECONDS || 120}s`, target: 40 }],
};

export const options = {
  stages: STAGES[__ENV.PROFILE || "scaling"],
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<2000"],
  },
};

// Filter values come from the server's own stats keys (every enum key is always present,
// AD-025), so the script never carries a hand-written copy of the vocabulary.
export function setup() {
  const stats = http.get(`${BASE}/api/stats`, PARAMS).json();
  return {
    category: Object.keys(stats.by_category),
    priority: Object.keys(stats.by_priority),
    status: Object.keys(stats.by_status),
  };
}

const pick = (values) => values[Math.floor(Math.random() * values.length)];

// Varied filters and pages, so PostgreSQL executes real queries instead of repeating one.
function listQuery(vocab) {
  const q = [`page=${1 + Math.floor(Math.random() * 3)}`, `page_size=${pick([10, 20, 50, 100])}`];
  for (const field of ["category", "priority", "status"]) {
    if (Math.random() < 0.5) q.push(`${field}=${pick(vocab[field])}`);
  }
  return q.join("&");
}

export default function (vocab) {
  // 8 list calls and 1 stats call per iteration (10-M9 §2); stats is cached, so it stays a minority.
  for (let i = 0; i < 8; i++) {
    const r = http.get(`${BASE}/api/complaints?${listQuery(vocab)}`, { ...PARAMS, tags: { name: "list" } });
    check(r, { "list 200": (res) => res.status === 200 });
  }
  const s = http.get(`${BASE}/api/stats`, { ...PARAMS, tags: { name: "stats" } });
  check(s, { "stats 200": (res) => res.status === 200 });
}
