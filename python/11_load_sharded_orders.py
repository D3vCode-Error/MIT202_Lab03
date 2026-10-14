
import csv
import os
from datetime import datetime, timezone
from pymongo import MongoClient

os.makedirs("results", exist_ok=True)

SOURCE_URI = (
    "mongodb://labadmin:lab_mongo_pw@127.0.0.1:27017/"
    "?authSource=admin&directConnection=true"
)
TARGET_URI = "mongodb://127.0.0.1:27217/?directConnection=true"

source = MongoClient(SOURCE_URI)
target = MongoClient(TARGET_URI)

source_orders = source["ecommerce_embedded"]["orders"]
database = target["sharding_lab"]

hashed = database["orders_hashed"]
ranged = database["orders_ranged"]

# Only load into empty experiment collections.
if hashed.estimated_document_count() != 0:
    raise RuntimeError("orders_hashed is not empty. Stop to avoid duplicates.")
if ranged.estimated_document_count() != 0:
    raise RuntimeError("orders_ranged is not empty. Stop to avoid duplicates.")

batch_hashed = []
batch_ranged = []
batch_size = 1000
total = 0

start = datetime.now(timezone.utc)
print("Starting migration:", start.isoformat(), flush=True)

cursor = source_orders.find(
    {},
    {
        "_id": 0,
        "order_id": 1,
        "customer_id": 1,
        "order_date": 1
    },
    no_cursor_timeout=True
).batch_size(batch_size)

try:
    for order in cursor:
        date = order["order_date"]

        if isinstance(date, str):
            date = datetime.fromisoformat(date.replace("Z", "+00:00"))

        if not isinstance(date, datetime):
            raise TypeError(f"Unexpected order_date type: {type(date)}")

        doc = {
            "order_id": order["order_id"],
            "customer_id": order["customer_id"],
            "order_date": date
        }

        batch_hashed.append(doc.copy())
        batch_ranged.append(doc.copy())

        if len(batch_hashed) == batch_size:
            hashed.insert_many(batch_hashed, ordered=False)
            ranged.insert_many(batch_ranged, ordered=False)
            total += len(batch_hashed)
            batch_hashed.clear()
            batch_ranged.clear()

            if total % 100000 == 0:
                print(f"Loaded {total:,} orders into each collection",
                      flush=True)

    if batch_hashed:
        hashed.insert_many(batch_hashed, ordered=False)
        ranged.insert_many(batch_ranged, ordered=False)
        total += len(batch_hashed)

finally:
    cursor.close()
    source.close()

end = datetime.now(timezone.utc)

print("Source orders copied:", total)
print("Hashed documents:", hashed.count_documents({}))
print("Ranged documents:", ranged.count_documents({}))
print("Duration seconds:", (end - start).total_seconds())

target.close()
