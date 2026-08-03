# Load-test baseline

The repository includes a small standard-library HTTP load tool at
`backend/load_tests/http_load.py`. It is intended to catch obvious regressions
in liveness, readiness and authenticated API latency before a deployment.

Run it against a locally running API:

```powershell
cd backend
.\.venv\Scripts\python.exe -m load_tests.http_load `
  --base-url http://localhost:8000 `
  --endpoint /health/ready `
  --requests 500 `
  --concurrency 25
```

The output reports successful/failed requests, error rate, throughput and
p50/p95/p99 latency. An authenticated endpoint can be tested with
`--bearer-token`, but do not put a real token in a committed script or log.

This is not a 100,000-user capacity test. It has no realistic arrival-rate
model, browser/device behavior, multi-endpoint journey, queue-depth assertion,
database saturation report, or production monitoring correlation. Before a
public launch, run a tool such as k6, Locust or Gatling in an isolated staging
environment against PostgreSQL, Redis, the worker pool and object storage.

Suggested release evidence:

- a 15-minute steady-state test and a ramp test;
- p95/p99 for login, analysis enqueue, polling and assignment submission;
- queue age/depth, worker failure/retry rate and provider latency/cost;
- PostgreSQL connection-pool usage, slow queries and lock waits;
- API error rate, CPU, memory and storage/network saturation;
- a documented threshold and the exact commit/configuration tested.
