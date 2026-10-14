
import csv
import os
import time
from statistics import mean
from pymongo import MongoClient, ReadPreference

os.makedirs("results", exist_ok=True)

# Run inside the Docker replica-set network.
URI = "mongodb://mongo1:27017,mongo2:27017,mongo3:27017/?replicaSet=rs0"

preferences = {
    "primary": ReadPreference.PRIMARY,
    "primaryPreferred": ReadPreference.PRIMARY_PREFERRED,
    "secondary": ReadPreference.SECONDARY,
}

results = []

client = MongoClient(URI, serverSelectionTimeoutMS=10000)

for name, preference in preferences.items():
    collection = client["replication_lab"].get_collection(
        "write_test_w3",
        read_preference=preference
    )

    times = []
    failures = 0

    for i in range(100):
        started = time.perf_counter()

        try:
            document = collection.find_one({"sequence": i + 1})
            if document is None:
                failures += 1
        except Exception as error:
            failures += 1
            print(f"{name}, trial {i + 1}: {error}")

        times.append((time.perf_counter() - started) * 1000)

    result = {
        "read_preference": name,
        "trials": 100,
        "failures": failures,
        "average_ms": round(mean(times), 3),
        "minimum_ms": round(min(times), 3),
        "maximum_ms": round(max(times), 3),
    }

    results.append(result)
    print(result)

output = "results/e2_mongo_read_preferences.csv"

with open(output, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

client.close()
print(f"Saved: {output}")
