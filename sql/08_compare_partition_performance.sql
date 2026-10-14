
-- Exercise 3: Partitioning performance comparison
-- PostgreSQL 16
-- Preserve the original and partitioned tables.

\timing on

-- Avoid parallel-worker differences obscuring the
-- comparison between sequential and partitioned scans.
SET max_parallel_workers_per_gather = 0;

-- Refresh planner statistics.
ANALYZE ecommerce.orders;
ANALYZE ecommerce.orders_part;

\echo
\echo ===== Q1: UNPARTITIONED - DATE RESTRICTED =====

EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*) AS total_orders
FROM ecommerce.orders
WHERE order_date >= DATE '2026-04-01'
  AND order_date < DATE '2026-07-01';

\echo
\echo ===== Q2: PARTITIONED - DATE RESTRICTED =====

EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*) AS total_orders
FROM ecommerce.orders_part
WHERE order_date >= DATE '2026-04-01'
  AND order_date < DATE '2026-07-01';

\echo
\echo ===== Q3: UNPARTITIONED - NO DATE FILTER =====

EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*) AS total_orders
FROM ecommerce.orders;

\echo
\echo ===== Q4: PARTITIONED - NO DATE FILTER =====

EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*) AS total_orders
FROM ecommerce.orders_part;

\echo
\echo ===== COMPARISON COMPLETE =====
