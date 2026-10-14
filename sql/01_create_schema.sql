
-- Laboratory Activity 03
-- Section 3.2: Relational Database Schema

CREATE SCHEMA IF NOT EXISTS ecommerce;

SET search_path TO ecommerce, public;

CREATE TABLE customers (
    customer_id BIGSERIAL PRIMARY KEY,
    full_name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    country_code CHAR(2) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE orders (
    order_id BIGSERIAL,
    customer_id BIGINT NOT NULL,
    order_date DATE NOT NULL,
    status TEXT NOT NULL,
    total_amount NUMERIC(12,2) NOT NULL,
    PRIMARY KEY (order_id, order_date)
);

CREATE TABLE order_items (
    order_id BIGINT NOT NULL,
    line_no INT NOT NULL,
    sku TEXT NOT NULL,
    quantity INT NOT NULL,
    unit_price NUMERIC(12,2) NOT NULL,
    PRIMARY KEY (order_id, line_no)
);
