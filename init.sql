-- Albion Profit Calculator Database Schema
CREATE SCHEMA IF NOT EXISTS albion;

SET search_path TO albion, public;

-- 1. Locations (Cities)
CREATE TABLE IF NOT EXISTS albion.locations (
    id INT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    region VARCHAR(100) DEFAULT '',
    tax_rate NUMERIC(5, 2) NOT NULL DEFAULT 6.5
);

-- Seed Royal Cities & Black Market
INSERT INTO albion.locations (id, name, region, tax_rate) VALUES
    (4, 'Thetford', 'Royal Continent', 6.5),
    (5, 'Fort Sterling', 'Royal Continent', 6.5),
    (6, 'Martlock', 'Royal Continent', 6.5),
    (7, 'Bridgewatch', 'Royal Continent', 6.5),
    (8, 'Lymhurst', 'Royal Continent', 6.5),
    (9, 'Caerleon', 'Royal Continent', 6.5),
    (10, 'Black Market', 'Caerleon', 6.5)
ON CONFLICT (id) DO UPDATE 
    SET name = EXCLUDED.name,
        region = EXCLUDED.region,
        tax_rate = EXCLUDED.tax_rate;

-- 2. Items
CREATE TABLE IF NOT EXISTS albion.items (
    item_id VARCHAR(255) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    tier INT NOT NULL DEFAULT 0,
    weight NUMERIC(10, 2) NOT NULL DEFAULT 1.0
);

ALTER TABLE IF EXISTS albion.items ALTER COLUMN item_id TYPE VARCHAR(255);
ALTER TABLE IF EXISTS albion.items ALTER COLUMN name TYPE VARCHAR(255);
ALTER TABLE IF EXISTS albion.market_orders ALTER COLUMN item_id TYPE VARCHAR(255);

-- 3. Market Orders
CREATE TABLE IF NOT EXISTS albion.market_orders (
    id BIGSERIAL PRIMARY KEY,
    item_id VARCHAR(255) NOT NULL REFERENCES albion.items(item_id) ON DELETE CASCADE,
    location_id INT NOT NULL REFERENCES albion.locations(id) ON DELETE CASCADE,
    order_type VARCHAR(10) NOT NULL,
    price BIGINT NOT NULL DEFAULT 0,
    quantity INT NOT NULL DEFAULT 0,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT uq_market_orders UNIQUE (item_id, location_id, order_type)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_orders_loc_type ON albion.market_orders (location_id, order_type);
CREATE INDEX IF NOT EXISTS idx_orders_item_loc ON albion.market_orders (item_id, location_id);
