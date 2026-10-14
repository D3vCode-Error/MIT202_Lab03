
\set ON_ERROR_STOP on
\timing on

\echo === EXERCISE 5: POSTGRESQL ACID ===

CREATE SCHEMA IF NOT EXISTS acid_lab;

DROP TABLE IF EXISTS acid_lab.transfers;
DROP TABLE IF EXISTS acid_lab.accounts;

CREATE TABLE acid_lab.accounts (
    account_id INTEGER PRIMARY KEY,
    owner_name TEXT NOT NULL,
    balance NUMERIC(12,2) NOT NULL
        CHECK (balance >= 0)
);

CREATE TABLE acid_lab.transfers (
    transfer_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_account INTEGER NOT NULL
        REFERENCES acid_lab.accounts(account_id),
    destination_account INTEGER NOT NULL
        REFERENCES acid_lab.accounts(account_id),
    amount NUMERIC(12,2) NOT NULL CHECK (amount > 0)
);

INSERT INTO acid_lab.accounts VALUES
(1, 'Account A', 1000.00),
(2, 'Account B', 1000.00);

\echo === INITIAL CONSISTENCY ===

SELECT * FROM acid_lab.accounts ORDER BY account_id;

\echo === ATOMICITY: FORCED CONSTRAINT FAILURE ===

BEGIN;

UPDATE acid_lab.accounts
SET balance = balance - 200
WHERE account_id = 1;

-- This operation violates CHECK (balance >= 0).
-- The surrounding transaction should become aborted.
SAVEPOINT before_invalid_update;

-- Capture the expected failure without stopping psql.
\set ON_ERROR_STOP off

UPDATE acid_lab.accounts
SET balance = -100
WHERE account_id = 2;

\set ON_ERROR_STOP on

ROLLBACK;

\echo === VERIFY ATOMICITY ===

SELECT * FROM acid_lab.accounts ORDER BY account_id;

\echo === CONSISTENCY: FOREIGN KEY CHECK ===

\set ON_ERROR_STOP off

INSERT INTO acid_lab.transfers
(source_account, destination_account, amount)
VALUES (1, 999, 100);

\set ON_ERROR_STOP on

\echo === VERIFY INVALID TRANSFER REJECTED ===

SELECT COUNT(*) AS invalid_transfer_records
FROM acid_lab.transfers;

\echo === VALID TRANSACTION ===

BEGIN;

UPDATE acid_lab.accounts
SET balance = balance - 100
WHERE account_id = 1;

UPDATE acid_lab.accounts
SET balance = balance + 100
WHERE account_id = 2;

INSERT INTO acid_lab.transfers
(source_account, destination_account, amount)
VALUES (1, 2, 100);

COMMIT;

\echo === FINAL ACCOUNT BALANCES ===

SELECT * FROM acid_lab.accounts ORDER BY account_id;

SELECT SUM(balance) AS total_balance
FROM acid_lab.accounts;

\echo === ACID ATOMICITY AND CONSISTENCY TEST COMPLETE ===
