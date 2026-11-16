"""
Performance benchmark against a running API (default http://localhost:8000).
    python3 benchmark.py                # sequential latency + 20-way concurrent load
Reports median / p95 latency for the screening endpoint and throughput under concurrency.
"""
import os
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import requests

BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")
FORM = {"age_bracket": "30-35", "feeling_sad": "Sometimes", "irritable": "Yes", "trouble_sleeping": "Yes",
        "trouble_concentrating": "No", "appetite_changes": "Sometimes", "feeling_anxious": "Yes",
        "feeling_guilty": "No", "bonding_difficulty": "No", "self_harm_thoughts": "No"}


def pct(values, p):
    values = sorted(values)
    return values[min(len(values) - 1, int(round(p / 100 * (len(values) - 1))))]


def mother_headers():
    fac = requests.get(f"{BASE}/facilities").json()[0]["id"]
    email = f"bench-{uuid.uuid4().hex[:8]}@example.com"
    requests.post(f"{BASE}/auth/register", json={"name": "Bench", "email": email, "password": "secret123",
                  "role": "mother", "facility_id": fac, "date_of_birth": "1995-01-01", "delivery_date": "2026-06-01"})
    tok = requests.post(f"{BASE}/auth/login", data={"username": email, "password": "secret123"}).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def one_call(headers):
    t0 = time.perf_counter()
    r = requests.post(f"{BASE}/screening/submit", json=FORM, headers=headers)
    return (time.perf_counter() - t0) * 1000, r.status_code


def main():
    h = mother_headers()
    one_call(h)  # warm-up (model already loaded at first call)
    seq = [one_call(h)[0] for _ in range(100)]
    print(f"Sequential x100  median {statistics.median(seq):.1f} ms | p95 {pct(seq, 95):.1f} ms | max {max(seq):.1f} ms")

    n, workers = 200, 20
    t0 = time.perf_counter()
    with ThreadPoolExecutor(workers) as ex:
        results = list(ex.map(lambda _: one_call(h), range(n)))
    wall = time.perf_counter() - t0
    lat = [r[0] for r in results]
    ok = sum(1 for r in results if r[1] == 200)
    print(f"Concurrent {n} req / {workers} workers  success {ok}/{n} | {n / wall:.1f} req/s | "
          f"median {statistics.median(lat):.1f} ms | p95 {pct(lat, 95):.1f} ms")


if __name__ == "__main__":
    main()
