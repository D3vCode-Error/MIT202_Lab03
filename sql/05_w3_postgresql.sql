
-- MIT Laboratory Activity 03
-- Exercise 1, W3: PostgreSQL schema evolution
-- Run against the original pre-W3 schema.
-- Safe repeatable trials: each trial rolls back.

SET search_path TO ecommerce, public;

DO $$
DECLARE
    i INTEGER;
    t_start TIMESTAMPTZ;
    elapsed_ms NUMERIC;
    changed_orders INTEGER;
BEGIN
    FOR i IN 1..5 LOOP
        t_start := clock_timestamp();

        -- Do not include permanent changes between trials.
        -- PostgreSQL PL/pgSQL exception blocks use
        -- subtransactions to roll back their work.
        BEGIN
            ALTER TABLE ecommerce.customers
                ADD COLUMN loyalty_tier TEXT;

            ALTER TABLE ecommerce.orders
                ADD COLUMN discount_code TEXT;

            UPDATE ecommerce.orders
            SET discount_code = 'PROMO5'
            WHERE order_id % 20 = 0;

            GET DIAGNOSTICS changed_orders = ROW_COUNT;

            elapsed_ms :=
                EXTRACT(
                    EPOCH FROM
                    (clock_timestamp() - t_start)
                ) * 1000;

            RAISE NOTICE
                'Trial %, rows=%, time_ms=%',
                i, changed_orders, elapsed_ms;

            -- Force the subtransaction to roll back.
            RAISE EXCEPTION 'ROLLBACK_TRIAL'
                USING ERRCODE = 'P0001';

        EXCEPTION
            WHEN SQLSTATE 'P0001' THEN
                NULL;
        END;
    END LOOP;
END
$$;
