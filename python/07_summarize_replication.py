
import csv
import os
import statistics

CLIENT_LEVELS = [5, 20, 50]
STANDBYS = ["standby_1", "standby_2"]

summary = []

for clients in CLIENT_LEVELS:
    filename = f"results/e2_pg_lag_{clients}_clients.csv"

    if not os.path.exists(filename):
        print(f"Missing: {filename}")
        continue

    with open(filename, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    for standby in STANDBYS:
        samples = [
            row for row in rows
            if row["standby"] == standby
        ]

        lag_ms = [
            float(row["replay_lag_ms"])
            for row in samples
            if row["replay_lag_ms"].strip()
        ]

        lag_bytes = [
            float(row["replay_lag_bytes"])
            for row in samples
            if row["replay_lag_bytes"].strip()
        ]

        record = {
            "clients": clients,
            "standby": standby,
            "samples": len(samples),
            "valid_lag_ms_samples": len(lag_ms),
            "mean_replay_lag_ms": (
                round(statistics.mean(lag_ms), 3)
                if lag_ms else ""
            ),
            "max_replay_lag_ms": (
                round(max(lag_ms), 3)
                if lag_ms else ""
            ),
            "mean_replay_lag_bytes": (
                round(statistics.mean(lag_bytes), 2)
                if lag_bytes else ""
            ),
            "max_replay_lag_bytes": (
                int(max(lag_bytes))
                if lag_bytes else ""
            ),
        }

        summary.append(record)

        print(
            f"{clients:2d} clients | {standby:9s} | "
            f"samples={record['samples']:3d} | "
            f"valid_ms={record['valid_lag_ms_samples']:3d} | "
            f"mean_ms={record['mean_replay_lag_ms']} | "
            f"max_ms={record['max_replay_lag_ms']} | "
            f"mean_bytes={record['mean_replay_lag_bytes']} | "
            f"max_bytes={record['max_replay_lag_bytes']}"
        )

os.makedirs("results", exist_ok=True)

output = "results/e2_pg_lag_summary.csv"

with open(output, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(
        f,
        fieldnames=[
            "clients",
            "standby",
            "samples",
            "valid_lag_ms_samples",
            "mean_replay_lag_ms",
            "max_replay_lag_ms",
            "mean_replay_lag_bytes",
            "max_replay_lag_bytes",
        ],
    )
    writer.writeheader()
    writer.writerows(summary)

print(f"\nSummary saved: {output}")
