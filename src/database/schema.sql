-- Etsy BI Analyzer — SQLite schema
-- This file is the canonical definition of the database.
-- All repository code must match this schema.

PRAGMA foreign_keys = ON;

-- =============================================================
-- imports
-- Tracks every file the user has imported.
-- =============================================================

CREATE TABLE IF NOT EXISTS imports (
    import_id        INTEGER PRIMARY KEY AUTOINCREMENT,
    filename         TEXT    NOT NULL,
    file_type        TEXT    NOT NULL,
    file_hash        TEXT    NOT NULL UNIQUE,
    import_date      TEXT    NOT NULL,
    rows_total       INTEGER NOT NULL DEFAULT 0,
    rows_valid       INTEGER NOT NULL DEFAULT 0,
    rows_invalid     INTEGER NOT NULL DEFAULT 0,
    status           TEXT    NOT NULL DEFAULT 'PENDING'
);

CREATE INDEX IF NOT EXISTS idx_imports_type ON imports(file_type);
CREATE INDEX IF NOT EXISTS idx_imports_date ON imports(import_date);

-- =============================================================
-- orders
-- One row per order. Source: EtsySoldOrders*.csv
-- =============================================================

CREATE TABLE IF NOT EXISTS orders (
    order_id                TEXT PRIMARY KEY,
    sale_date               TEXT NOT NULL,
    buyer_user_id           TEXT,
    full_name               TEXT,
    first_name              TEXT,
    last_name               TEXT,
    number_of_items         INTEGER,
    payment_method          TEXT,
    date_shipped            TEXT,
    street_1                TEXT,
    street_2                TEXT,
    ship_city               TEXT,
    ship_state              TEXT,
    ship_zipcode            TEXT,
    ship_country            TEXT,
    currency                TEXT NOT NULL,
    order_value             REAL NOT NULL,
    coupon_code             TEXT,
    coupon_details          TEXT,
    discount_amount         REAL NOT NULL DEFAULT 0,
    shipping_discount       REAL NOT NULL DEFAULT 0,
    shipping                REAL NOT NULL DEFAULT 0,
    sales_tax               REAL NOT NULL DEFAULT 0,
    order_total             REAL NOT NULL,
    status                  TEXT,
    card_processing_fees    REAL NOT NULL DEFAULT 0,
    order_net               REAL NOT NULL,
    import_id               INTEGER NOT NULL,
    FOREIGN KEY (import_id) REFERENCES imports(import_id)
);

CREATE INDEX IF NOT EXISTS idx_orders_date    ON orders(sale_date);
CREATE INDEX IF NOT EXISTS idx_orders_country ON orders(ship_country);
CREATE INDEX IF NOT EXISTS idx_orders_buyer   ON orders(buyer_user_id);

-- =============================================================
-- order_items
-- One row per line item. Source: EtsySoldOrderItems*.csv
-- =============================================================

CREATE TABLE IF NOT EXISTS order_items (
    transaction_id      TEXT PRIMARY KEY,
    order_id            TEXT NOT NULL,
    sale_date           TEXT NOT NULL,
    listing_id          TEXT NOT NULL,
    item_name           TEXT,
    quantity            INTEGER NOT NULL,
    price               REAL NOT NULL,
    currency            TEXT NOT NULL,
    coupon_code         TEXT,
    coupon_details      TEXT,
    discount_amount     REAL NOT NULL DEFAULT 0,
    shipping_discount   REAL NOT NULL DEFAULT 0,
    order_shipping      REAL NOT NULL DEFAULT 0,
    order_sales_tax     REAL NOT NULL DEFAULT 0,
    item_total          REAL NOT NULL,
    vat_paid_by_buyer   REAL NOT NULL DEFAULT 0,
    sku                 TEXT,
    import_id           INTEGER NOT NULL,
    FOREIGN KEY (order_id)  REFERENCES orders(order_id),
    FOREIGN KEY (import_id) REFERENCES imports(import_id)
);

CREATE INDEX IF NOT EXISTS idx_order_items_order   ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_order_items_listing ON order_items(listing_id);
CREATE INDEX IF NOT EXISTS idx_order_items_date    ON order_items(sale_date);

-- =============================================================
-- payments
-- One row per payment. Source: EtsyDirectCheckoutPayments*.csv
-- =============================================================

CREATE TABLE IF NOT EXISTS payments (
    payment_id          TEXT PRIMARY KEY,
    order_id            TEXT NOT NULL,
    buyer_username      TEXT,
    buyer_name          TEXT,
    gross_amount        REAL NOT NULL,
    fees                REAL NOT NULL DEFAULT 0,
    net_amount          REAL NOT NULL,
    refund_amount       REAL NOT NULL DEFAULT 0,
    currency            TEXT NOT NULL,
    listing_amount      REAL,
    listing_currency    TEXT,
    exchange_rate       REAL,
    vat_amount          REAL NOT NULL DEFAULT 0,
    status              TEXT,
    funds_available     TEXT,
    order_date          TEXT NOT NULL,
    import_id           INTEGER NOT NULL,
    FOREIGN KEY (order_id)  REFERENCES orders(order_id),
    FOREIGN KEY (import_id) REFERENCES imports(import_id)
);

CREATE INDEX IF NOT EXISTS idx_payments_order   ON payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_date    ON payments(order_date);
CREATE INDEX IF NOT EXISTS idx_payments_funds   ON payments(funds_available);

-- =============================================================
-- deposits
-- One row per bank payout. Source: EtsyDeposits*.csv
-- =============================================================

CREATE TABLE IF NOT EXISTS deposits (
    deposit_id              INTEGER PRIMARY KEY AUTOINCREMENT,
    deposit_date            TEXT NOT NULL,
    amount                  REAL NOT NULL,
    currency                TEXT NOT NULL,
    status                  TEXT,
    bank_account_ending     TEXT,
    import_id               INTEGER NOT NULL,
    FOREIGN KEY (import_id) REFERENCES imports(import_id)
);

CREATE INDEX IF NOT EXISTS idx_deposits_date ON deposits(deposit_date);

-- =============================================================
-- listings_catalog
-- One row per listing. Source: EtsyListingsDownload*.csv
-- Note: no listing_id in the source file.
-- =============================================================

CREATE TABLE IF NOT EXISTS listings_catalog (
    catalog_row_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    title            TEXT NOT NULL,
    description      TEXT,
    price            REAL NOT NULL,
    currency         TEXT NOT NULL,
    quantity         INTEGER NOT NULL,
    tags             TEXT,
    materials        TEXT,
    sku              TEXT,
    import_id        INTEGER NOT NULL,
    FOREIGN KEY (import_id) REFERENCES imports(import_id)
);

CREATE INDEX IF NOT EXISTS idx_listings_sku   ON listings_catalog(sku);
CREATE INDEX IF NOT EXISTS idx_listings_title ON listings_catalog(title);

-- =============================================================
-- data_quality_issues
-- Findings produced by validation and reconciliation.
-- =============================================================

CREATE TABLE IF NOT EXISTS data_quality_issues (
    issue_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    import_id     INTEGER,
    check_name    TEXT NOT NULL,
    severity      TEXT NOT NULL CHECK (severity IN ('INFO','WARNING','ERROR')),
    table_name    TEXT,
    row_ref       TEXT,
    field_name    TEXT,
    message       TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    FOREIGN KEY (import_id) REFERENCES imports(import_id)
);

CREATE INDEX IF NOT EXISTS idx_issues_severity ON data_quality_issues(severity);
CREATE INDEX IF NOT EXISTS idx_issues_import   ON data_quality_issues(import_id);
CREATE INDEX IF NOT EXISTS idx_issues_check    ON data_quality_issues(check_name);