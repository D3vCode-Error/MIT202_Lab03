
# MIT Laboratory Activity 03
# Exercise 1: PostgreSQL to MongoDB Migration

import os
from collections import defaultdict
from datetime import datetime, time, timezone

import psycopg
from pymongo import MongoClient, ASCENDING
from bson.decimal128 import Decimal128

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

BATCH_SIZE = 1000


def mongo_date(value):
    return datetime.combine(
        value, time.min, tzinfo=timezone.utc
    )


def customer_doc(row):
    return {
        "customer_id": row[0],
        "full_name": row[1],
        "email": row[2],
        "country_code": row[3].strip(),
        "created_at": row[4],
    }


def order_doc(row):
    return {
        "order_id": row[0],
        "customer_id": row[1],
        "order_date": mongo_date(row[2]),
        "status": row[3],
        "total_amount": Decimal128(str(row[4])),
    }


def migrate_customers(pg, embedded, referenced):
    print("Migrating customers...", flush=True)

    with pg.cursor(name="customer_stream") as cur:
        cur.execute("""
            SELECT customer_id, full_name, email,
                   country_code, created_at
            FROM ecommerce.customers
            ORDER BY customer_id
        """)

        total = 0

        while rows := cur.fetchmany(BATCH_SIZE):
            docs = [customer_doc(r) for r in rows]
            embedded.customers.insert_many(docs)
            referenced.customers.insert_many(docs)

            total += len(docs)
            print(f"Customers: {total:,}", flush=True)


def migrate_orders(pg, embedded, referenced):
    print("Migrating orders and items...", flush=True)

    with pg.cursor(name="order_stream") as cur:
        cur.execute("""
            SELECT o.order_id, o.customer_id,
                   o.order_date, o.status,
                   o.total_amount,
                   c.full_name, c.country_code
            FROM ecommerce.orders o
            JOIN ecommerce.customers c
              ON o.customer_id = c.customer_id
            ORDER BY o.order_id
        """)

        total_orders = 0
        total_items = 0

        while rows := cur.fetchmany(BATCH_SIZE):
            order_ids = [r[0] for r in rows]
            items_by_order = defaultdict(list)
            referenced_items = []

            with pg.cursor() as item_cur:
                item_cur.execute("""
                    SELECT order_id, line_no, sku,
                           quantity, unit_price
                    FROM ecommerce.order_items
                    WHERE order_id = ANY(%s)
                    ORDER BY order_id, line_no
                """, (order_ids,))

                for item in item_cur:
                    item_doc = {
                        "order_id": item[0],
                        "line_no": item[1],
                        "sku": item[2],
                        "quantity": item[3],
                        "unit_price": Decimal128(
                            str(item[4])
                        ),
                    }
                    referenced_items.append(item_doc)

                    items_by_order[item[0]].append({
                        "line_no": item[1],
                        "sku": item[2],
                        "quantity": item[3],
                        "unit_price": Decimal128(
                            str(item[4])
                        ),
                    })

            embedded_orders = []
            referenced_orders = []

            for row in rows:
                base = order_doc(row)

                ref_doc = dict(base)
                embedded_doc = dict(base)

                embedded_doc["customer_name"] = row[5]
                embedded_doc["country_code"] = row[6].strip()
                embedded_doc["items"] = items_by_order[
                    row[0]
                ]

                referenced_orders.append(ref_doc)
                embedded_orders.append(embedded_doc)

            embedded.orders.insert_many(embedded_orders)
            referenced.orders.insert_many(referenced_orders)

            if referenced_items:
                referenced.order_items.insert_many(
                    referenced_items
                )

            total_orders += len(rows)
            total_items += len(referenced_items)

            if total_orders % 10000 == 0:
                print(
                    f"Orders: {total_orders:,} | "
                    f"Items: {total_items:,}",
                    flush=True
                )


def create_indexes(embedded, referenced):
    print("Creating MongoDB indexes...", flush=True)

    for db in (embedded, referenced):
        db.customers.create_index(
            [("customer_id", ASCENDING)], unique=True
        )
        db.customers.create_index(
            [("email", ASCENDING)], unique=True
        )
        db.orders.create_index(
            [("order_id", ASCENDING)], unique=True
        )
        db.orders.create_index(
            [("order_date", ASCENDING)]
        )
        db.orders.create_index(
            [("customer_id", ASCENDING)]
        )

    embedded.orders.create_index(
        [("country_code", ASCENDING),
         ("order_date", ASCENDING)]
    )
    referenced.order_items.create_index(
        [("order_id", ASCENDING),
         ("line_no", ASCENDING)],
        unique=True
    )


def main():
    client = MongoClient(
        MONGO_URI,
        serverSelectionTimeoutMS=10000
    )
    embedded = client["ecommerce_embedded"]
    referenced = client["ecommerce_referenced"]

    try:
        client.admin.command("ping")

        expected = {
            "ecommerce_embedded": {
                "customers": 100000,
                "orders": 1000000,
            },
            "ecommerce_referenced": {
                "customers": 100000,
                "orders": 1000000,
                "order_items": 3000000,
            },
        }

        # Never silently overwrite existing data.
        for db in (embedded, referenced):
            existing = db.list_collection_names()
            if existing:
                raise RuntimeError(
                    f"{db.name} already contains collections: "
                    f"{existing}. Inspect before retrying."
                )

        with psycopg.connect(**PG_CONFIG) as pg:
            # Avoid exporting from a changing snapshot.
            pg.execute(
                "SET TRANSACTION ISOLATION LEVEL "
                "REPEATABLE READ, READ ONLY"
            )
            migrate_customers(pg, embedded, referenced)
            migrate_orders(pg, embedded, referenced)

        create_indexes(embedded, referenced)

        print("\nFinal MongoDB counts:")
        for db in (embedded, referenced):
            print(f"\n{db.name}")
            for collection, target in expected[db.name].items():
                actual = db[collection].count_documents({})
                print(
                    f"  {collection}: {actual:,} "
                    f"(expected {target:,})"
                )
                if actual != target:
                    raise RuntimeError(
                        f"Count mismatch for {db.name}.{collection}"
                    )

        print("\nMIGRATION COMPLETED SUCCESSFULLY")

    finally:
        client.close()


if __name__ == "__main__":
    main()
