
import csv
import json
from pathlib import Path

import psycopg2

Path("results").mkdir(exist_ok=True)

PG = {
    "host": "127.0.0.1",
    "port": 5432,
    "dbname": "ecommerce",
    "user": "labuser",
    "password": "lab_postgres_pw",
}

LEVELS = [
    "READ UNCOMMITTED",
    "READ COMMITTED",
    "REPEATABLE READ",
    "SERIALIZABLE",
]

def connect():
    return psycopg2.connect(**PG)

def setup():
    with connect() as con:
        with con.cursor() as cur:
            cur.execute("""
                CREATE SCHEMA IF NOT EXISTS acid_lab
            """)
            cur.execute("""
                CREATE TABLE IF NOT EXISTS
                acid_lab.isolation_demo (
                    id INTEGER PRIMARY KEY,
                    amount INTEGER NOT NULL
                )
            """)

def reset():
    with connect() as con:
        with con.cursor() as cur:
            cur.execute("""
                TRUNCATE acid_lab.isolation_demo
            """)
            cur.execute("""
                INSERT INTO acid_lab.isolation_demo
                (id, amount)
                VALUES (1, 100)
            """)

def run_test(level):
    reset()

    reader = connect()
    writer = connect()

    reader.autocommit = False
    writer.autocommit = False

    try:
        with reader.cursor() as rc, writer.cursor() as wc:

            rc.execute(
                "SET TRANSACTION ISOLATION LEVEL " + level
            )

            # First reader snapshot.
            rc.execute("""
                SELECT amount
                FROM acid_lab.isolation_demo
                WHERE id = 1
            """)
            first_value = rc.fetchone()[0]

            rc.execute("""
                SELECT COUNT(*)
                FROM acid_lab.isolation_demo
                WHERE amount >= 100
            """)
            first_count = rc.fetchone()[0]

            # Concurrent transaction updates a row
            # and inserts another matching row.
            wc.execute("""
                UPDATE acid_lab.isolation_demo
                SET amount = 200
                WHERE id = 1
            """)
            wc.execute("""
                INSERT INTO acid_lab.isolation_demo
                (id, amount)
                VALUES (2, 150)
            """)
            writer.commit()

            # Reader repeats the same queries.
            rc.execute("""
                SELECT amount
                FROM acid_lab.isolation_demo
                WHERE id = 1
            """)
            second_value = rc.fetchone()[0]

            rc.execute("""
                SELECT COUNT(*)
                FROM acid_lab.isolation_demo
                WHERE amount >= 100
            """)
            second_count = rc.fetchone()[0]

            reader.commit()

            return {
                "isolation_level": level,
                "first_amount": first_value,
                "second_amount": second_value,
                "non_repeatable_read": (
                    first_value != second_value
                ),
                "first_count": first_count,
                "second_count": second_count,
                "phantom_read": (
                    first_count != second_count
                ),
            }

    except Exception:
        reader.rollback()
        writer.rollback()
        raise

    finally:
        reader.close()
        writer.close()

def main():
    setup()
    results = []

    for level in LEVELS:
        result = run_test(level)
        results.append(result)

        print("\n=== " + level + " ===")
        print(json.dumps(result, indent=2))

    with open(
        "results/e5_pg_isolation_matrix.csv",
        "w",
        newline="",
        encoding="utf-8",
    ) as f:
        writer = csv.DictWriter(
            f,
            fieldnames=results[0].keys()
        )
        writer.writeheader()
        writer.writerows(results)

    print("\n=== ISOLATION MATRIX ===")
    for row in results:
        print(
            row["isolation_level"],
            "| Non-repeatable:",
            row["non_repeatable_read"],
            "| Phantom:",
            row["phantom_read"],
        )

    print("\n=== ISOLATION EXPERIMENT COMPLETE ===")
    print("Saved: results/e5_pg_isolation_matrix.csv")

if __name__ == "__main__":
    main()
