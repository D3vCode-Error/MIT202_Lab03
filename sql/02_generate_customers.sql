
-- Generate 100,000 synthetic customers

SET search_path TO ecommerce, public;

INSERT INTO customers (
    customer_id,
    full_name,
    email,
    country_code,
    created_at
)
SELECT
    id,
    'Customer ' || id,
    'customer' || id || '@example.test',
    (ARRAY['PH','US','JP','SG','AU','CA'])
        [1 + ((id - 1) % 6)],
    TIMESTAMPTZ '2024-01-01 00:00:00+00'
        + ((id - 1) % 1096) * INTERVAL '1 day'
FROM generate_series(1,100000) AS id;

-- Synchronize the BIGSERIAL sequence
SELECT setval(
    pg_get_serial_sequence('ecommerce.customers', 'customer_id'),
    100000,
    true
);

ANALYZE customers;
