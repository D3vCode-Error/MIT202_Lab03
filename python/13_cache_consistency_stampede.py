
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import psycopg2
import redis

Path("results").mkdir(exist_ok=True)

PG = dict(
    host="127.0.0.1",
    port=5432,
    dbname="ecommerce",
    user="labuser",
    password="lab_postgres_pw"
)

CACHE_HOST = "127.0.0.1"
CACHE_PORT = 16379
CACHE_DB = 15

r = redis.Redis(
    host=CACHE_HOST,
    port=CACHE_PORT,
    db=CACHE_DB,
    decode_responses=True
)

r.ping()

def connect_db():
    return psycopg2.connect(**PG)


def setup_demo():
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS
                ecommerce.e4_cache_demo (
                    id INTEGER PRIMARY KEY,
                    description TEXT NOT NULL
                )
            """)
            cur.execute("""
                INSERT INTO ecommerce.e4_cache_demo
                (id, description)
                VALUES (1, 'Initial value')
                ON CONFLICT (id)
                DO UPDATE SET
                    description = EXCLUDED.description
            """)
    r.delete("e4:write_through:1")


def read_demo_db():
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT description
                FROM ecommerce.e4_cache_demo
                WHERE id = 1
            """)
            return cur.fetchone()[0]


def test_write_through():
    print("=== WRITE-THROUGH TEST ===")

    key = "e4:write_through:1"
    new_value = "Updated through write-through"

    # Commit to PostgreSQL first.
    with connect_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE ecommerce.e4_cache_demo
                SET description = %s
                WHERE id = 1
            """, (new_value,))

    # Then update Redis.
    # These operations are sequential, not atomic
    # across the two independent systems.
    r.set(key, new_value, ex=300)

    db_value = read_demo_db()
    cache_value = r.get(key)

    print("PostgreSQL value:", db_value)
    print("Redis value:", cache_value)
    print("Values match:", db_value == cache_value)

    return db_value == cache_value


def test_stampede(use_lock):
    key = "e4:stampede:locked" if use_lock else "e4:stampede:unlocked"
    lock_key = key + ":lock"
    r.delete(key, lock_key)

    workers = 50
    barrier = threading.Barrier(workers)
    counter_lock = threading.Lock()
    db_queries = [0]

    def slow_db_read():
        with counter_lock:
            db_queries[0] += 1

        # Deliberate simulated 50 ms database delay
        # to expose simultaneous cache misses.
        time.sleep(0.05)
        return "order-42-demo"

    def worker(_):
        client = redis.Redis(
            host=CACHE_HOST,
            port=CACHE_PORT,
            db=CACHE_DB,
            decode_responses=True
        )

        barrier.wait()
        cached = client.get(key)
        if cached is not None:
            return cached

        if not use_lock:
            value = slow_db_read()
            client.set(key, value, ex=300)
            return value

        # Only one worker should load the missing value.
        deadline = time.monotonic() + 10

        while time.monotonic() < deadline:
            cached = client.get(key)
            if cached is not None:
                return cached

            lock = client.lock(
                lock_key,
                timeout=5,
                blocking_timeout=0.1
            )

            if lock.acquire(blocking=False):
                try:
                    cached = client.get(key)
                    if cached is not None:
                        return cached

                    value = slow_db_read()
                    client.set(key, value, ex=300)
                    return value
                finally:
                    lock.release()

            time.sleep(0.005)

        raise TimeoutError("Cache stampede worker timed out")

    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        values = list(pool.map(worker, range(workers)))

    duration_ms = (time.perf_counter() - start) * 1000

    label = "WITH REDIS LOCK" if use_lock else "WITHOUT LOCK"

    print(f"\n=== STAMPEDE {label} ===")
    print("Concurrent clients:", workers)
    print("Successful responses:", len(values))
    print("Database-load simulations:", db_queries[0])
    print("Elapsed time (ms):", round(duration_ms, 3))
    print("All responses correct:",
          all(v == "order-42-demo" for v in values))

    return {
        "clients": workers,
        "db_load_simulations": db_queries[0],
        "elapsed_ms": round(duration_ms, 3),
        "successful_responses": len(values)
    }


try:
    setup_demo()

    consistent = test_write_through()

    unlocked = test_stampede(False)
    locked = test_stampede(True)

    summary = {
        "write_through_values_match": consistent,
        "without_lock": unlocked,
        "with_lock": locked,
        "note": (
            "Stampede database reads are simulated "
            "using a 50 ms delayed function."
        )
    }

    with open(
        "results/e4_write_through_stampede.json",
        "w",
        encoding="utf-8"
    ) as f:
        json.dump(summary, f, indent=2)

    print("\n=== EXPERIMENT COMPLETE ===")
    print(json.dumps(summary, indent=2))

finally:
    r.close()
