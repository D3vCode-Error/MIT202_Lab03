
import csv
import os
import sys
import time
from datetime import datetime, timezone

import psycopg

CLIENTS = int(sys.argv[1])
DURATION = 180
INTERVAL = 2

OUTPUT = f"results/e2_pg_lag_{CLIENTS}_clients.csv"

os.makedirs("results", exist_ok=True)

conn = psycopg.connect(
    host="127.0.0.1",
    port=5433,
    dbname="ecommerce",
    user="labuser",
    password="lab_repl_pw",
    autocommit=True,
)

query = """
SELECT
    application_name,
    state,
    sync_state,
    pg_wal_lsn_diff(pg_current_wal_lsn(), replay_lsn)
        AS replay_lag_bytes,
    EXTRACT(EPOCH FROM replay_lag) * 1000
        AS replay_lag_ms
FROM pg_stat_replication
WHERE application_name IN ('standby_1', 'standby_2')
ORDER BY application_name;
"""

print(f"Monitoring {CLIENTS} clients for {DURATION} seconds")
print(f"Saving results to {OUTPUT}")

start = time.monotonic()

with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "timestamp_utc",
        "elapsed_seconds",
        "clients",
        "standby",
        "state",
        "sync_state",
        "replay_lag_bytes",
        "replay_lag_ms",
    ])

    try:
        while True:
            elapsed = time.monotonic() - start
            if elapsed >= DURATION:
                break

            timestamp = datetime.now(
                timezone.utc
            ).isoformat()

            with conn.cursor() as cur:
                cur.execute(query)
                rows = cur.fetchall()

            for row in rows:
                standby, state, sync_state, lag_bytes, lag_ms = row

                writer.writerow([
                    timestamp,
                    round(elapsed, 2),
                    CLIENTS,
                    standby,
                    state,
                    sync_state,
                    float(lag_bytes) if lag_bytes is not None else "",
                    float(lag_ms) if lag_ms is not None else "",
                ])

                print(
                    f"{elapsed:6.1f}s | {standby:10s} | "
                    f"{sync_state:5s} | "
                    f"lag_bytes={lag_bytes} | "
                    f"lag_ms={lag_ms}"
                )

            f.flush()
            time.sleep(max(0, start + (int(elapsed / INTERVAL) + 1)
                           * INTERVAL - time.monotonic()))

    except KeyboardInterrupt:
        print("Monitoring interrupted.")

conn.close()
print(f"Results saved: {OUTPUT}")
