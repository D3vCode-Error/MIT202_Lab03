
import csv
import time
from pathlib import Path

import redis

Path("results").mkdir(exist_ok=True)

r = redis.Redis(host="127.0.0.1", port=16380)
VALUE = b"x" * 8192
results = []

def run_test(policy):
    r.flushdb()
    r.config_set("maxmemory-policy", policy)
    r.config_resetstat()

    # Insert 120 initial 8 KB keys.
    for i in range(120):
        r.set(f"e4:item:{i}", VALUE)

    # Establish frequently accessed keys.
    for _ in range(100):
        for i in range(10):
            r.get(f"e4:item:{i}")

    # Make some other keys recently accessed.
    for i in range(110, 120):
        r.get(f"e4:item:{i}")

    # Insert additional keys until eviction pressure occurs.
    i = 120
    while r.info("stats")["evicted_keys"] < 50 and i < 1200:
        r.set(f"e4:item:{i}", VALUE)
        i += 1

    stats = r.info("stats")
    memory = r.info("memory")

    hot_survived = sum(
        r.exists(f"e4:item:{j}") for j in range(10)
    )
    recent_survived = sum(
        r.exists(f"e4:item:{j}") for j in range(110, 120)
    )
    cold_survived = sum(
        r.exists(f"e4:item:{j}") for j in range(10, 110)
    )

    row = {
        "policy": policy,
        "keys_inserted": i,
        "evicted_keys": stats["evicted_keys"],
        "remaining_keys": r.dbsize(),
        "hot_survived_of_10": hot_survived,
        "recent_survived_of_10": recent_survived,
        "cold_survived_of_100": cold_survived,
        "used_memory_bytes": memory["used_memory"],
        "maxmemory_bytes": memory["maxmemory"],
    }

    results.append(row)

    print(f"\n=== {policy.upper()} ===")
    for key, value in row.items():
        print(f"{key}: {value}")


try:
    run_test("allkeys-lru")
    run_test("allkeys-lfu")

    with open(
        "results/e4_lru_lfu_comparison.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as file:
        writer = csv.DictWriter(
            file, fieldnames=results[0].keys()
        )
        writer.writeheader()
        writer.writerows(results)

    print("\n=== EVICTION COMPARISON COMPLETE ===")
    print("Saved: results/e4_lru_lfu_comparison.csv")

finally:
    r.close()
