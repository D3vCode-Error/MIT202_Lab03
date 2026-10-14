
# MIT Laboratory Activity 03
# Exercise 1 - W1: Order Detail Retrieval


import csv
import os
import statistics
import time
from pathlib import Path

import psycopg
from pymongo import MongoClient


ORDER_ID = 42
RUNS = 5

PG_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "dbname": "ecommerce",
    "user": "labuser",
    "password": os.getenv(
        "PGPASSWORD", "lab_postgres_pw"
    ),
}

MONGO_URI = (
    "mongodb://labadmin:"
    + os.getenv("MONGO_PASSWORD", "lab_mongo_pw")
    + "@127.0.0.1:27017/?authSource=admin"
)

SQL_W1 = """
SELECT
    o.order_id,
    c.full_name,
    o.order_date,
    o.status,
    o.total_amount,
    i.line_no,
    i.sku,
    i.quantity,
    i.unit_price
FROM ecommerce.orders o
JOIN ecommerce.customers c
    ON o.customer_id = c.customer_id
JOIN ecommerce.order_items i
    ON o.order_id = i.order_id
WHERE o.order_id = %s
ORDER BY i.line_no
"""


def postgresql_w1(conn):
    with conn.cursor() as cur:
        cur.execute(SQL_W1, (ORDER_ID,))
        rows = cur.fetchall()

    return {
        "order_id": rows[0][0] if rows else None,
        "customer_name": rows[0][1] if rows else None,
        "items": [
            {
                "line_no": row[5],
                "sku": row[6],
                "quantity": row[7],
                "unit_price": str(row[8]),
            }
            for row in rows
        ],
    }


def embedded_w1(db):
    doc = db.orders.find_one(
        {"order_id": ORDER_ID},
        {"_id": 0}
    )

    if doc is None:
        return None

    return {
        "order_id": doc["order_id"],
        "customer_name": doc["customer_name"],
        "items": [
            {
                "line_no": item["line_no"],
                "sku": item["sku"],
                "quantity": item["quantity"],
                "unit_price": str(item["unit_price"].to_decimal()),
            }
            for item in doc["items"]
        ],
    }


def referenced_w1(db):
    order = db.orders.find_one(
        {"order_id": ORDER_ID},
        {"_id": 0}
    )

    if order is None:
        return None

    customer = db.customers.find_one(
        {"customer_id": order["customer_id"]},
        {"_id": 0}
    )

    items = list(
        db.order_items.find(
            {"order_id": ORDER_ID},
            {"_id": 0}
        ).sort("line_no", 1)
    )

    return {
        "order_id": order["order_id"],
        "customer_name": customer["full_name"],
        "items": [
            {
                "line_no": item["line_no"],
                "sku": item["sku"],
                "quantity": item["quantity"],
                "unit_price": str(item["unit_price"].to_decimal()),
            }
            for item in items
        ],
    }


def benchmark(name, function):
    times = []

    print(f"\n{name}")

    for run in range(1, RUNS + 1):
        start = time.perf_counter()

        result = function()

        elapsed_ms = (
            time.perf_counter() - start
        ) * 1000

        if result is None:
            raise RuntimeError(
                f"{name}: order was not found"
            )

        if len(result["items"]) != 3:
            raise RuntimeError(
                f"{name}: expected 3 order items"
            )

        times.append(elapsed_ms)

        print(
            f"Run {run}: {elapsed_ms:.4f} ms"
            + (" (discard)" if run == 1 else "")
        )

    retained = times[1:]

    mean = statistics.mean(retained)
    stdev = statistics.stdev(retained)

    print(f"Mean runs 2-5: {mean:.4f} ms")
    print(f"Std. deviation: {stdev:.4f} ms")

    return result, times, mean, stdev


def main():
    output_dir = Path("results")
    output_dir.mkdir(exist_ok=True)

    pg = psycopg.connect(**PG_CONFIG)
    mongo = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=10000
    )

    try:
        mongo.admin.command("ping")

        embedded = mongo["ecommerce_embedded"]
        referenced = mongo["ecommerce_referenced"]

        tests = [
            ("PostgreSQL", lambda: postgresql_w1(pg)),
            ("MongoDB Embedded",
             lambda: embedded_w1(embedded)),
            ("MongoDB Referenced",
             lambda: referenced_w1(referenced)),
        ]

        results = []
        baseline = None

        for name, function in tests:
            data, runs, mean, stdev = benchmark(
                name, function
            )

            # Verify identical business results.
            if baseline is None:
                baseline = data
            elif data != baseline:
                raise RuntimeError(
                    f"Data mismatch in {name}: {data}"
                )

            results.append({
                "database": name,
                "order_id": ORDER_ID,
                "run1_discarded_ms": runs[0],
                "run2_ms": runs[1],
                "run3_ms": runs[2],
                "run4_ms": runs[3],
                "run5_ms": runs[4],
                "mean_ms": mean,
                "stdev_ms": stdev,
            })

        path = output_dir / "w1_results.csv"

        with path.open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(
                file, fieldnames=results[0].keys()
            )
            writer.writeheader()
            writer.writerows(results)

        print("\nAll three stores returned")
        print("the same order ID, name and items.")
        print(f"Results saved to: {path}")

    finally:
        pg.close()
        mongo.close()


if __name__ == "__main__":
    main()
