
# MIT Laboratory Activity 03
# Exercise 1 - W3 MongoDB Schema Evolution

import csv
import os
import statistics
import time
from pathlib import Path

from pymongo import MongoClient

MONGO_URI = (
    "mongodb://labadmin:"
    + os.getenv("MONGO_PASSWORD", "lab_mongo_pw")
    + "@127.0.0.1:27017/?authSource=admin"
)

DATABASES = [
    "ecommerce_embedded",
    "ecommerce_referenced"
]

RUNS = 5
OUTPUT = Path("results/w3_mongodb.csv")


def check_baseline(db):
    """Ensure no W3 fields exist before a trial."""

    customer_count = db.customers.count_documents(
        {"loyalty_tier": {"$exists": True}}
    )

    order_count = db.orders.count_documents(
        {"discount_code": {"$exists": True}}
    )

    if customer_count != 0 or order_count != 0:
        raise RuntimeError(
            f"{db.name}: Existing W3 fields detected. "
            "Inspect the data before retrying."
        )


def apply_changes(db):
    """Add W3 fields and measure execution time."""

    start = time.perf_counter()

    customers = db.customers.update_many(
        {},
        {"$set": {"loyalty_tier": None}}
    )

    orders = db.orders.update_many(
        {"order_id": {"$mod": [20, 0]}},
        {"$set": {"discount_code": "PROMO5"}}
    )

    elapsed = time.perf_counter() - start

    if customers.matched_count != 100000:
        raise RuntimeError(
            "Unexpected customer update count"
        )

    if orders.matched_count != 50000:
        raise RuntimeError(
            "Unexpected discounted order count"
        )

    return elapsed, customers, orders


def restore_baseline(db):
    """Remove trial fields without deleting documents."""

    db.customers.update_many(
        {"loyalty_tier": {"$exists": True}},
        {"$unset": {"loyalty_tier": ""}}
    )

    db.orders.update_many(
        {"discount_code": {"$exists": True}},
        {"$unset": {"discount_code": ""}}
    )

    check_baseline(db)


def benchmark_database(db):
    print(f"\nTesting: {db.name}", flush=True)

    check_baseline(db)
    durations = []

    for trial in range(1, RUNS + 1):
        elapsed, customers, orders = apply_changes(db)

        durations.append(elapsed)

        print(
            f"Trial {trial}: {elapsed:.4f} seconds "
            f"| customers: {customers.modified_count} "
            f"| orders: {orders.modified_count}"
            + (" [DISCARD]" if trial == 1 else ""),
            flush=True
        )

        restore_baseline(db)

    mean = statistics.mean(durations[1:])
    std = statistics.stdev(durations[1:])

    print(f"Mean trials 2-5: {mean:.4f} seconds")
    print(f"Standard deviation: {std:.4f} seconds")

    return {
        "database": db.name,
        "run1_discarded_s": durations[0],
        "run2_s": durations[1],
        "run3_s": durations[2],
        "run4_s": durations[3],
        "run5_s": durations[4],
        "mean_s": mean,
        "stdev_s": std
    }


def main():
    OUTPUT.parent.mkdir(exist_ok=True)

    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=10000
    )

    try:
        client.admin.command("ping")
        results = []

        for name in DATABASES:
            results.append(
                benchmark_database(client[name])
            )

        with OUTPUT.open(
            "w",
            newline="",
            encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=results[0].keys()
            )
            writer.writeheader()
            writer.writerows(results)

        print("\nMongoDB W3 benchmark completed.")
        print(f"Results saved: {OUTPUT}")
        print("Temporary W3 fields have been removed.")

    finally:
        client.close()


if __name__ == "__main__":
    main()
