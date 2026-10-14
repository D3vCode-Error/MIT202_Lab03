
-- Exercise 3: Load the quarterly partitions
-- Source: ecommerce.orders
-- Destination: ecommerce.orders_part

BEGIN;

INSERT INTO ecommerce.orders_part (
    order_id,
    customer_id,
    order_date,
    status,
    total_amount
)
SELECT
    order_id,
    customer_id,
    order_date,
    status,
    total_amount
FROM ecommerce.orders
ON CONFLICT (order_id, order_date) DO NOTHING;

COMMIT;

ANALYZE ecommerce.orders_part;
ANALYZE ecommerce.orders;
