
\set ON_ERROR_STOP on
\timing on

\echo === EXERCISE 3: CUSTOMER HASH PARTITIONING ===

-- Preserve the original customers table.
-- Do not copy its primary-key/unique indexes:
-- PostgreSQL requires a partitioned table's unique
-- constraints to include its partitioning key.

CREATE TABLE ecommerce.customers_hash_id (
    LIKE ecommerce.customers
) PARTITION BY HASH (customer_id);

CREATE TABLE ecommerce.customers_hash_country (
    LIKE ecommerce.customers
) PARTITION BY HASH (country_code);

-- Create eight partitions for each design.
DO $$
DECLARE
    i INTEGER;
BEGIN
    FOR i IN 0..7 LOOP
        EXECUTE format(
            'CREATE TABLE ecommerce.customers_id_p%s
             PARTITION OF ecommerce.customers_hash_id
             FOR VALUES WITH (MODULUS 8, REMAINDER %s)',
            i, i
        );

        EXECUTE format(
            'CREATE TABLE ecommerce.customers_country_p%s
             PARTITION OF ecommerce.customers_hash_country
             FOR VALUES WITH (MODULUS 8, REMAINDER %s)',
            i, i
        );
    END LOOP;
END;
$$;

\echo === LOAD THE SAME 100,000 CUSTOMERS ===

INSERT INTO ecommerce.customers_hash_id
SELECT * FROM ecommerce.customers;

INSERT INTO ecommerce.customers_hash_country
SELECT * FROM ecommerce.customers;

ANALYZE ecommerce.customers_hash_id;
ANALYZE ecommerce.customers_hash_country;

\echo === VERIFY ROW COUNTS ===

SELECT
    (SELECT COUNT(*) FROM ecommerce.customers)
        AS original_customers,
    (SELECT COUNT(*) FROM ecommerce.customers_hash_id)
        AS hash_id_customers,
    (SELECT COUNT(*) FROM ecommerce.customers_hash_country)
        AS hash_country_customers;

\echo === DISTRIBUTION BY CUSTOMER_ID ===

SELECT tableoid::regclass AS partition_name,
       COUNT(*) AS row_count
FROM ecommerce.customers_hash_id
GROUP BY tableoid
ORDER BY partition_name;

\echo === DISTRIBUTION BY COUNTRY_CODE ===

SELECT tableoid::regclass AS partition_name,
       COUNT(*) AS row_count
FROM ecommerce.customers_hash_country
GROUP BY tableoid
ORDER BY partition_name;

\echo === SKEW ANALYSIS INCLUDING EMPTY PARTITIONS ===

WITH partition_counts AS (
    SELECT
        'customer_id' AS partition_key,
        c.relname AS partition_name,
        (
            SELECT COUNT(*)
            FROM ecommerce.customers_hash_id t
            WHERE t.tableoid = c.oid
        ) AS row_count
    FROM pg_inherits i
    JOIN pg_class c ON c.oid = i.inhrelid
    WHERE i.inhparent =
        'ecommerce.customers_hash_id'::regclass

    UNION ALL

    SELECT
        'country_code' AS partition_key,
        c.relname AS partition_name,
        (
            SELECT COUNT(*)
            FROM ecommerce.customers_hash_country t
            WHERE t.tableoid = c.oid
        ) AS row_count
    FROM pg_inherits i
    JOIN pg_class c ON c.oid = i.inhrelid
    WHERE i.inhparent =
        'ecommerce.customers_hash_country'::regclass
)
SELECT
    partition_key,
    COUNT(*) AS partitions,
    SUM(row_count) AS total_rows,
    MIN(row_count) AS min_rows,
    MAX(row_count) AS max_rows,
    COUNT(*) FILTER (WHERE row_count = 0)
        AS empty_partitions,
    ROUND(
        MAX(row_count)::numeric /
        NULLIF(MIN(row_count), 0),
        3
    ) AS max_min_skew_ratio
FROM partition_counts
GROUP BY partition_key
ORDER BY partition_key;

\echo === HASH PARTITIONING COMPLETE ===
