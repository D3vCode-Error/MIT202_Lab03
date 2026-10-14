
\set ON_ERROR_STOP on
\timing on

\echo === EXERCISE 3: DETACH VS DELETE ===

-- Separate partitioned test table.
CREATE TABLE ecommerce.orders_detach_test (
    LIKE ecommerce.orders INCLUDING DEFAULTS
) PARTITION BY RANGE (order_date);

CREATE TABLE ecommerce.orders_detach_q1
PARTITION OF ecommerce.orders_detach_test
FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

-- Ordinary comparison table with the same source rows.
CREATE TABLE ecommerce.orders_delete_test
AS
SELECT *
FROM ecommerce.orders
WHERE order_date >= DATE '2024-01-01'
  AND order_date < DATE '2024-04-01';

-- Populate the detachable partition with identical records.
INSERT INTO ecommerce.orders_detach_test
SELECT *
FROM ecommerce.orders
WHERE order_date >= DATE '2024-01-01'
  AND order_date < DATE '2024-04-01';

ANALYZE ecommerce.orders_detach_test;
ANALYZE ecommerce.orders_delete_test;

\echo === VERIFY EQUAL STARTING COUNTS ===

SELECT
    (SELECT COUNT(*) FROM ecommerce.orders_detach_test)
        AS detach_test_rows,
    (SELECT COUNT(*) FROM ecommerce.orders_delete_test)
        AS delete_test_rows;

\echo === METHOD A: DETACH PARTITION ===

ALTER TABLE ecommerce.orders_detach_test
DETACH PARTITION ecommerce.orders_detach_q1;

\echo === VERIFY DETACH RESULTS ===

SELECT
    (SELECT COUNT(*) FROM ecommerce.orders_detach_test)
        AS remaining_parent_rows,
    (SELECT COUNT(*) FROM ecommerce.orders_detach_q1)
        AS preserved_detached_rows;

\echo === METHOD B: DELETE ===

DELETE FROM ecommerce.orders_delete_test;

\echo === VERIFY DELETE RESULTS ===

SELECT COUNT(*) AS remaining_delete_test_rows
FROM ecommerce.orders_delete_test;

\echo === VACUUM ===

VACUUM (VERBOSE, ANALYZE)
ecommerce.orders_delete_test;

\echo === FINAL STORAGE MEASUREMENTS ===

SELECT
    pg_size_pretty(
        pg_total_relation_size(
            'ecommerce.orders_detach_q1'
        )
    ) AS detached_partition_size,
    pg_size_pretty(
        pg_total_relation_size(
            'ecommerce.orders_delete_test'
        )
    ) AS vacuumed_table_size;

\echo === EXPERIMENT COMPLETE ===
