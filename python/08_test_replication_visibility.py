
import csv
import os
import time
import uuid
from datetime import datetime, timezone

import psycopg

TRIALS = 20
OUTPUT = "results/e2_pg_visibility_20_trials.csv"

os.makedirs("results", exist_ok=True)

CONNECTIONS = {
    "primary": 5433,
    "standby_1": 5434,
    "standby_2": 5435,
}

def connect(port):
    return psycopg.connect(
        host="127.0.0.1",
        port=port,
        dbname="ecommerce",
        user="labuser",
        password="lab_repl_pw",
        autocommit=True,
        connect_timeout=10,
    )

connections = {
    name: connect(port)
    for name, port in CONNECTIONS.items()
}

primary = connections["primary"]
standbys = ["standby_1", "standby_2"]

summary = {
    name: {"visible": 0, "stale": 0, "errors": 0}
    for name in standbys
}

print("PostgreSQL Read-Your-Own-Writes Test")
print("20 trials | Primary + Async + Sync standbys")
print("A missing marker on immediate read counts as stale.")
print()

try:
    with open(OUTPUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "trial",
            "timestamp_utc",
            "standby",
            "marker",
            "visible",
            "stale",
            "read_latency_ms",
            "time_since_commit_ms",
            "error",
        ])

        for trial in range(1, TRIALS + 1):
            marker = f"e2_{trial}_{uuid.uuid4().hex}"

            # With autocommit=True, the INSERT completes
            # and commits before we query the replicas.
            with primary.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO public.replication_visibility_test
                        (marker)
                    VALUES (%s)
                    """,
                    (marker,),
                )

            commit_time = time.perf_counter()

            # Alternate the query order to reduce
            # systematic first-reader advantage.
            order = (
                standbys
                if trial % 2 == 1
                else list(reversed(standbys))
            )

            for standby in order:
                read_start = time.perf_counter()
                error = ""

                try:
                    with connections[standby].cursor() as cur:
                        cur.execute(
                            """
                            SELECT EXISTS (
                                SELECT 1
                                FROM public.replication_visibility_test
                                WHERE marker = %s
                            )
                            """,
                            (marker,),
                        )
                        visible = bool(cur.fetchone()[0])

                    status = "VISIBLE" if visible else "STALE"

                    if visible:
                        summary[standby]["visible"] += 1
                    else:
                        summary[standby]["stale"] += 1

                except Exception as exc:
                    visible = None
                    status = "ERROR"
                    error = str(exc)
                    summary[standby]["errors"] += 1

                read_end = time.perf_counter()

                writer.writerow([
                    trial,
                    datetime.now(timezone.utc).isoformat(),
                    standby,
                    marker,
                    "" if visible is None else int(visible),
                    "" if visible is None else int(not visible),
                    round((read_end - read_start) * 1000, 3),
                    round((read_start - commit_time) * 1000, 3),
                    error,
                ])

                print(
                    f"Trial {trial:02d} | "
                    f"{standby:9s} | {status}"
                )

            f.flush()

    print("\nFINAL SUMMARY")
    for standby in standbys:
        s = summary[standby]
        print(
            f"{standby}: "
            f"visible={s['visible']}, "
            f"stale={s['stale']}, "
            f"errors={s['errors']}, "
            f"trials={TRIALS}"
        )

    print(f"\nResults saved: {OUTPUT}")

finally:
    for connection in connections.values():
        connection.close()
