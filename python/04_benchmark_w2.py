
# MIT Laboratory Activity 03
# Exercise 1 - W2 Analytical Aggregation

import csv
import os
import statistics
import time
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import psycopg
from pymongo import MongoClient


RUNS = 5
START_DATE = datetime(2026, 1, 1, tzinfo=timezone.utc)
END_DATE = datetime(2027, 1, 1, tzinfo=timezone.utc)

PG_CONFIG = {
    "host": "127.0.0.1",
    "port": 5432,
    "dbname": "ecommerce",
    "user": "labuser",
    "password": os.getenv("PGPASSWORD", "lab_postgres_pw"),
}

MONGO_URI = (
    "mongodb://labadmin:"
    + os.getenv("MONGO_PASSWORD", "lab_mongo_pw")
    + "@127.0.0.1:27017/?authSource=admin"
)

SQL_W2 = """
SELECT
    TRIM(c.country_code) AS country_code,
    TO_CHAR(o.order_date, 'YYYY-MM') AS order_month,
    COUNT(*) AS total_orders,
    SUM(o.total_amount) AS total_revenue
FROM ecommerce.orders o
JOIN ecommerce.customers c
    ON o.customer_id = c.customer_id
WHERE o.order_date >= DATE '2026-01-01'
  AND o.order_date < DATE '2027-01-01'
GROUP BY
    TRIM(c.country_code),
    TO_CHAR(o.order_date, 'YYYY-MM')
ORDER BY country_code, order_month
"""


def postgresql_w2(conn):
    with conn.cursor() as cur:
        cur.execute(SQL_W2)
        return cur.fetchall()


def embedded_w2(db):
    pipeline = [
        {
            "$match": {
                "order_date": {
                    "$gte": START_DATE,
                    "$lt": END_DATE
                }
            }
        },
        {
            "$group": {
                "_id": {
                    "country": "$country_code",
                    "month": {
                        "$dateToString": {
                            "format": "%Y-%m",
                            "date": "$order_date",
                            "timezone": "UTC"
                        }
                    }
                },
                "total_orders": {"$sum": 1},
                "total_revenue": {"$sum": "$total_amount"}
            }
        },
        {"$sort": {"_id.country": 1, "_id.month": 1}}
    ]

    return list(db.orders.aggregate(pipeline))


def referenced_w2(db):
    pipeline = [
        {
            "$match": {
                "order_date": {
                    "$gte": START_DATE,
                    "$lt": END_DATE
                }
            }
        },
        {
            "$lookup": {
                "from": "customers",
                "localField": "customer_id",
                "foreignField": "customer_id",
                "as": "customer"
            }
        },
        {"$unwind": "$customer"},
        {
            "$group": {
                "_id": {
                    "country": "$customer.country_code",
                    "month": {
                        "$dateToString": {
                            "format": "%Y-%m",
                            "date": "$order_date",
                            "timezone": "UTC"
                        }
                    }
                },
                "total_orders": {"$sum": 1},
                "total_revenue": {"$sum": "$total_amount"}
            }
        },
        {"$sort": {"_id.country": 1, "_id.month": 1}}
    ]

    return list(
        db.orders.aggregate(
            pipeline,
            allowDiskUse=True
        )
    )


def normalize(rows, source):
    normalized = {}

    for row in rows:
        if source == "PostgreSQL":
            country, month, count, revenue = row
        else:
            country = row["_id"]["country"]
            month = row["_id"]["month"]
            count = row["total_orders"]
            revenue = row["total_revenue"]

            if hasattr(revenue, "to_decimal"):
                revenue = revenue.to_decimal()

        key = (str(country).strip(), str(month))
        normalized[key] = (
            int(count),
            Decimal(str(revenue)).quantize(Decimal("0.01"))
        )

    return normalized


def benchmark(name, function):
    times = []
    last_result = None

    print(f"\n{name}", flush=True)

    for run in range(1, RUNS + 1):
        start = time.perf_counter()
        last_result = function()
        duration = (time.perf_counter() - start) * 1000

        times.append(duration)

        print(
            f"Run {run}: {duration:.3f} ms"
            + (" [DISCARDED]" if run == 1 else ""),
            flush=True
        )

    retained = times[1:]
    mean_ms = statistics.mean(retained)
    stdev_ms = statistics.stdev(retained)

    print(f"Mean latency: {mean_ms:.3f} ms")
    print(f"Standard deviation: {stdev_ms:.3f} ms")

    return last_result, times, mean_ms, stdev_ms


def main():
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    pg = psycopg.connect(**PG_CONFIG)
    mongo = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=10000
    )

    try:
        mongo.admin.command("ping")

        tests = [
            ("PostgreSQL", lambda: postgresql_w2(pg)),
            (
                "MongoDB Embedded",
                lambda: embedded_w2(
                    mongo["ecommerce_embedded"]
                )
            ),
            (
                "MongoDB Referenced",
                lambda: referenced_w2(
                    mongo["ecommerce_referenced"]
                )
            )
        ]

        results = []
        baseline = None

        for name, function in tests:
            data, runs, mean, std = benchmark(name, function)
            normalized = normalize(data, name)

            if not normalized:
                raise RuntimeError(f"No results from {name}")

            if baseline is None:
                baseline = normalized
            elif normalized != baseline:
                raise RuntimeError(
                    f"Aggregation mismatch for {name}."
                    " Verify dates, grouping and data."
                )

            results.append({
                "database": name,
                "run1_discarded_ms": runs[0],
                "run2_ms": runs[1],
                "run3_ms": runs[2],
                "run4_ms": runs[3],
                "run5_ms": runs[4],
                "mean_ms": mean,
                "stdev_ms": std,
                "groups": len(normalized)
            })

        output = results_dir / "w2_results.csv"

        with output.open(
            "w", newline="", encoding="utf-8"
        ) as file:
            writer = csv.DictWriter(
                file, fieldnames=results[0].keys()
            )
            writer.writeheader()
            writer.writerows(results)

        print("\nAll three aggregations match.")
        print(f"Country-month groups: {len(baseline)}")
        print(f"Results saved: {output}")

    finally:
        pg.close()
        mongo.close()


if __name__ == "__main__":
    main()
