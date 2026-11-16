// k6 load test of ONE operation: POST /api/stock/remove/ (WF-B), quantity 1 per request, user `manager`.
// Targets (declared BEFORE measuring, docs/PERF_TARGETS.md): p95 <= 500 ms, unexpected failures < 1 %.
// Protocol: N simulated users start together; a 10 s warm-up phase (tag phase=warmup) is followed by a 60 s MEASURED phase (phase=hold) at the same N.
// Only valid requests are sent (large stock), so any status other than 201 is an UNEXPECTED failure.
import http from 'k6/http';
import { check } from 'k6';

const BASE = __ENV.BASE_URL || 'http://127.0.0.1:8000';
const VUS = parseInt(__ENV.VUS || '1');
const basic = (u, p) => 'Basic ' + encoding_b64(`${u}:${p}`);
import encoding from 'k6/encoding';
function encoding_b64(s) { return encoding.b64encode(s); }

http.setResponseCallback(http.expectedStatuses(201));

export const options = {
  scenarios: {
    warmup: { executor: 'constant-vus', vus: VUS, duration: '10s', tags: { phase: 'warmup' }, exec: 'adjust' },
    hold: { executor: 'constant-vus', vus: VUS, duration: '60s', startTime: '10s', tags: { phase: 'hold' }, exec: 'adjust' },
  },
  thresholds: {
    'http_req_duration{phase:hold}': ['p(95)<500'],
    'http_req_failed{phase:hold}': ['rate<0.01'],
    'http_reqs{phase:hold}': ['count>0'],
  },
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

export function setup() {
  // Same starting data for every run: a fresh item with a large quantity (the server DB itself is reset by scripts/perf_run.sh)
  const r = http.post(`${BASE}/api/stock/`, JSON.stringify({ part: 1, location: 1, quantity: '5000000', delete_on_deplete: false }),
    { headers: { 'Content-Type': 'application/json', Authorization: basic('admin', 'admin12345') }, responseCallback: http.expectedStatuses(201) });
  const body = r.json();
  return { pk: (Array.isArray(body) ? body[0] : body).pk };
}

export function adjust(data) {
  const res = http.post(`${BASE}/api/stock/remove/`, JSON.stringify({ items: [{ pk: data.pk, quantity: '1' }] }),
    { headers: { 'Content-Type': 'application/json', Authorization: basic('manager', 'manager12345') } });
  check(res, { 'status is 201': (r) => r.status === 201 });
}
