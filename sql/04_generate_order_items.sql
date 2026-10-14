
-- Generate three items for every order

SET search_path TO ecommerce, public;

INSERT INTO order_items (
    order_id,
    line_no,
    sku,
    quantity,
    unit_price
)
SELECT
    o.order_id,
    item_no,
    'SKU-' || LPAD(
        (1 + ((o.order_id + item_no) % 500))::TEXT,
        4,
        '0'
    ),
    1,
    (10 + ((o.order_id + item_no) % 90))::NUMERIC(12,2)
FROM orders AS o
CROSS JOIN generate_series(1,3) AS item_no;

ANALYZE order_items;
