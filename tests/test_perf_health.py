import time
from statistics import quantiles

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_p95_latency_under_100ms():
    # Warmup
    for _ in range(10):
        client.get("/health")

    latencies_ms = []
    iterations = 200

    start_suite = time.perf_counter()
    for _ in range(iterations):
        t0 = time.perf_counter()
        r = client.get("/health")
        t1 = time.perf_counter()
        assert r.status_code == 200
        latencies_ms.append((t1 - t0) * 1000.0)
    total_duration_ms = (time.perf_counter() - start_suite) * 1000.0

    # Compute p95 using inclusive method
    p95 = quantiles(latencies_ms, n=100, method="inclusive")[94]

    # Emit a CI-visible metric line
    print(
        f"perf_metric: health_p95_ms={p95:.2f} "
        f"total_ms={total_duration_ms:.2f} iters={iterations}"
    )

    # Generous threshold for local/CI variance
    assert p95 < 100.0
