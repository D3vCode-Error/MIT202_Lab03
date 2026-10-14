
import csv
import json
import random
import statistics
import time
from pathlib import Path

import psycopg2
import redis

Path("results").mkdir(exist_ok=True)

db = psycopg2.connect(
    host="127.0.0.1",
    port=5432,
    dbname="ecommerce",
    user="labuser",
    password="lab_postgres_pw"
)
db.autocommit = True

cache = redis.Redis(
    host="127.0.0.1",
    port=16379,
    decode_responses=True
)

cache.ping()

QUERY = """
SELECT order_id, customer_id, order_date, status, total_amount
FROM ecommerce.orders
WHERE order_id = %s
"""

REQUESTS = 2000
SEED = 2026

# Reproducible workload: 80% of requests target
# 100 popular orders, while 20% target 900 others.
rng = random.Random(SEED)
popular = list(range(1, 101))
other = list(range(101, 1001))

workload = [
    rng.choice(popular if rng.random() < 0.8 else other)
    for _ in range(REQUESTS)
]


def percentile(values, p):
    ordered = sorted(values)
    position = (len(ordered) - 1) * p / 100
    low = int(position)
    high = min(low + 1, len(ordered) - 1)
    fraction = position - low
    return ordered[low] * (1 - fraction) + ordered[high] * fraction


def fetch_db(order_id):
    with db.cursor() as cursor:
        cursor.execute(QUERY, (order_id,))
        row = cursor.fetchone()

    if row is None:
        return None

    return {
        "order_id": row[0],
        "customer_id": row[1],
        "order_date": row[2].isoformat(),
        "status": row[3],
        "total_amount": str(row[4]),
    }


def benchmark(label, ttl):
    cache.flushdb()

    latencies = []
    hits = 0
    misses = 0
    db_queries = 0

    start = time.perf_counter()

    for order_id in workload:
        request_start = time.perf_counter()

        if ttl is None:
            result = fetch_db(order_id)
            db_queries += 1
        else:
            key = f"mit03:order:{order_id}"
            cached = cache.get(key)

            if cached is not None:
                result = json.loads(cached)
                hits += 1
            else:
                result = fetch_db(order_id)
                misses += 1
                db_queries += 1

                if result is not None:
                    cache.set(key, json.dumps(result), ex=ttl)

        if result is None:
            raise RuntimeError(f"Order {order_id} not found")

        latencies.append(
            (time.perf_counter() - request_start) * 1000
        )

    duration = time.perf_counter() - start
    memory = cache.info("memory")["used_memory"]

    return {
        "configuration": label,
        "ttl_seconds": "none" if ttl is None else ttl,
        "requests": REQUESTS,
        "p50_ms": round(percentile(latencies, 50), 4),
        "p95_ms": round(percentile(latencies, 95), 4),
        "mean_ms": round(statistics.mean(latencies), 4),
        "hit_count": hits,
        "miss_count": misses,
        "hit_ratio_pct": round(
            hits / REQUESTS * 100, 2
        ),
        "db_queries": db_queries,
        "db_qps": round(db_queries / duration, 2),
        "redis_memory_bytes": memory,
        "duration_seconds": round(duration, 4),
    }


try:
    results = [
        benchmark("No cache", None),
        benchmark("TTL 30", 30),
        benchmark("TTL 300", 300),
        benchmark("TTL 3600", 3600),
    ]

    output = "results/e4_cache_ttl_benchmark.csv"

    with open(output, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file, fieldnames=results[0].keys()
        )
        writer.writeheader()
        writer.writerows(results)

    print("\n=== EXERCISE 4: CACHE-ASIDE BENCHMARK ===")

    for row in results:
        print(json.dumps(row, indent=2))

    print("\nSaved:", output)

finally:
    db.close()
    cache.close()
