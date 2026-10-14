
-- Exercise 3: PostgreSQL quarterly range partitioning
-- Preserves the original ecommerce.orders table.

CREATE TABLE IF NOT EXISTS ecommerce.orders_part (
    order_id BIGINT NOT NULL,
    customer_id BIGINT NOT NULL,
    order_date DATE NOT NULL,
    status VARCHAR(20),
    total_amount NUMERIC(12,2),
    PRIMARY KEY (order_id, order_date)
) PARTITION BY RANGE (order_date);

CREATE TABLE IF NOT EXISTS ecommerce.orders_2024_q1
PARTITION OF ecommerce.orders_part
FOR VALUES FROM ('2024-01-01') TO ('2024-04-01');

CREATE TABLE IF NOT EXISTS ecommerce.orders_2024_q2
PARTITION OF ecommerce.orders_part
FOR VALUES FROM ('2024-04-01') TO ('2024-07-01');

CREATE TABLE IF NOT EXISTS ecommerce.orders_2024_q3
PARTITION OF ecommerce.orders_part
FOR VALUES FROM ('2024-07-01') TO ('2024-10-01');

CREATE TABLE IF NOT EXISTS ecommerce.orders_2024_q4
PARTITION OF ecommerce.orders_part
FOR VALUES FROM ('2024-10-01') TO ('2025-01-01');

CREATE TABLE IF NOT EXISTS ecommerce.orders_2025_q1
PARTITION OF ecommerce.orders_part
FOR VALUES FROM ('2025-01-01') TO ('2025-04-01');

CREATE TABLE IF NOT EXISTS ecommerce.orders_2025_q2
PARTITION OF ecommerce.orders_part
FOR VALUES FROM ('2025-04-01') TO ('2025-07-01');

CREATE TABLE IF NOT EXISTS ecommerce.orders_2025_q3
PARTITION OF ecommerce.orders_part
FOR VALUES FROM ('2025-07-01') TO ('2025-10-01');

CREATE TABLE IF NOT EXISTS ecommerce.orders_2025_q4
PARTITION OF ecommerce.orders_part
FOR VALUES FROM ('2025-10-01') TO ('2026-01-01');

CREATE TABLE IF NOT EXISTS ecommerce.orders_2026_q1
PARTITION OF ecommerce.orders_part
FOR VALUES FROM ('2026-01-01') TO ('2026-04-01');

CREATE TABLE IF NOT EXISTS ecommerce.orders_2026_q2
PARTITION OF ecommerce.orders_part
FOR VALUES FROM ('2026-04-01') TO ('2026-07-01');

CREATE TABLE IF NOT EXISTS ecommerce.orders_2026_q3
PARTITION OF ecommerce.orders_part
FOR VALUES FROM ('2026-07-01') TO ('2026-10-01');

CREATE TABLE IF NOT EXISTS ecommerce.orders_2026_q4
PARTITION OF ecommerce.orders_part
FOR VALUES FROM ('2026-10-01') TO ('2027-01-01');

CREATE TABLE IF NOT EXISTS ecommerce.orders_default
PARTITION OF ecommerce.orders_part DEFAULT;
