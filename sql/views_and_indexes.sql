-- ==============================================================================
-- E-Commerce Competitor Price Monitor - Views and Indexes
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- VIEWS
-- ------------------------------------------------------------------------------

-- 1. latest_prices View
-- Purpose: Quickly fetch the most recent price for every product across every competitor.
-- This is critical for dashboard performance, avoiding complex subqueries repeatedly.
CREATE OR REPLACE VIEW v_latest_prices AS
SELECT 
    ph.product_id,
    ph.competitor_id,
    ph.price,
    ph.currency,
    ph.in_stock,
    ph.scraped_at
FROM price_history ph
INNER JOIN (
    SELECT product_id, competitor_id, MAX(scraped_at) AS max_scraped_at
    FROM price_history
    GROUP BY product_id, competitor_id
) latest 
ON ph.product_id = latest.product_id 
AND ph.competitor_id = latest.competitor_id 
AND ph.scraped_at = latest.max_scraped_at;

-- 2. price_changes View
-- Purpose: Pre-calculates the day-over-day (or scrape-over-scrape) price changes.
-- Useful for feeding data to the price_alerts system or trend dashboards.
CREATE OR REPLACE VIEW v_price_changes AS
SELECT 
    product_id,
    competitor_id,
    scraped_at,
    price,
    LAG(price) OVER (PARTITION BY product_id, competitor_id ORDER BY scraped_at) AS previous_price,
    price - LAG(price) OVER (PARTITION BY product_id, competitor_id ORDER BY scraped_at) AS price_diff
FROM price_history;

-- 3. product_summary View
-- Purpose: Consolidates core product data, category names, and the most recent known price 
-- into a single denormalized view for easy consumption by downstream BI tools.
CREATE OR REPLACE VIEW v_product_summary AS
SELECT 
    p.id AS product_id,
    p.sku,
    p.name AS product_name,
    c.name AS category_name,
    lp.price AS current_best_price,
    lp.in_stock,
    lp.scraped_at AS last_updated
FROM products p
LEFT JOIN categories c ON p.category_id = c.id
LEFT JOIN v_latest_prices lp ON p.id = lp.product_id;

-- ------------------------------------------------------------------------------
-- INDEXES & GENERATED COLUMNS
-- ------------------------------------------------------------------------------

-- 1. Generated Column & Index on JSON
-- Purpose: To efficiently query products by brand without doing a full table scan 
-- evaluating the JSON document on every row.
ALTER TABLE products 
ADD COLUMN brand VARCHAR(100) GENERATED ALWAYS AS (attributes->>'$.brand') VIRTUAL;

CREATE INDEX idx_products_brand ON products(brand);

-- 2. Composite Index for Latest Price Subquery
-- Purpose: The v_latest_prices view (and many analytics queries) group by product and competitor 
-- and find the max scraped_at. This composite index makes that specific aggregation extremely fast.
CREATE INDEX idx_price_history_latest 
ON price_history(product_id, competitor_id, scraped_at DESC);

-- 3. Covering Index for Dashboard Queries
-- Purpose: If a dashboard routinely requests the product's SKU, name, and category,
-- a covering index allows MySQL to satisfy the query entirely from the index tree 
-- without hitting the main table data blocks.
CREATE INDEX idx_products_covering 
ON products(category_id, sku, name);

-- 4. Index for Price Alerts 
-- Purpose: When resolving or reviewing price alerts, users will frequently filter by product_id 
-- and order by created_at.
CREATE INDEX idx_price_alerts_lookup 
ON price_alerts(product_id, created_at DESC);

-- 5. Foreign Key supporting Indexes
-- Note: MySQL automatically indexes foreign keys, but creating explicit composite indexes 
-- that include FKs is often necessary for specific join+filter patterns.
CREATE INDEX idx_products_cat_brand 
ON products(category_id, brand);
