
-- Generate 1,000,000 synthetic orders
-- Dates span January 2024 to December 2026

SET search_path TO ecommerce, public;

INSERT INTO orders (
    order_id,
    customer_id,
    order_date,
    status,
    total_amount
)
SELECT
    id,
    1 + ((id - 1) % 100000),
    DATE '2024-01-01' + ((id - 1) % 1096),
    (ARRAY[
        'NEW',
        'PROCESSING',
        'SHIPPED',
        'COMPLETED'
    ])[1 + ((id - 1) % 4)],
    (
        30
        + ((id + 1) % 90)
        + ((id + 2) % 90)
        + ((id + 3) % 90)
    )::NUMERIC(12,2)
FROM generate_series(1,1000000) AS id;

-- Synchronize order ID sequence
SELECT setval(
    pg_get_serial_sequence('ecommerce.orders', 'order_id'),
    1000000,
    true
);

ANALYZE orders;
