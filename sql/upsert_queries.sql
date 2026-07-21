-- ==============================================================================
-- E-Commerce Competitor Price Monitor - UPSERT Queries
-- ==============================================================================

-- 1. Upsert Competitors
-- Insert a new competitor. If the name already exists, update the base_url.
INSERT INTO competitors (name, base_url)
VALUES ('Amazon', 'https://www.amazon.com')
ON DUPLICATE KEY UPDATE 
    base_url = VALUES(base_url);

-- 2. Upsert Categories
-- Insert a new category, or do nothing if it already exists (updating name to name is effectively a no-op).
INSERT INTO categories (name)
VALUES ('Electronics')
ON DUPLICATE KEY UPDATE 
    name = VALUES(name);

-- 3. Product Upsert with JSON_MERGE_PATCH
-- When a product is scraped again, we might find new attributes. 
-- We want to merge the new attributes with existing ones rather than overwrite.
INSERT INTO products (sku, name, category_id, attributes, source_competitor_id)
VALUES ('SKU12345', 'iPhone 15', 1, '{"brand": "Apple", "storage": "128GB"}', 1)
ON DUPLICATE KEY UPDATE 
    name = VALUES(name),
    -- Merge new JSON properties into the existing document
    attributes = JSON_MERGE_PATCH(COALESCE(attributes, '{}'), VALUES(attributes)),
    updated_at = CURRENT_TIMESTAMP;

-- 4. Price History Insert with Duplicate Detection
-- Since price_history has a UNIQUE KEY on (product_id, competitor_id, scraped_at),
-- we use ON DUPLICATE KEY UPDATE to handle the rare collision (e.g., duplicate scrape events).
INSERT INTO price_history (product_id, competitor_id, price, currency, in_stock, scraped_at)
VALUES (1, 1, 799.99, 'USD', TRUE, '2023-10-01 12:00:00')
ON DUPLICATE KEY UPDATE 
    price = VALUES(price),
    in_stock = VALUES(in_stock);

-- 5. Bulk Upsert Pattern
-- Ideal for processing batches of items efficiently.
INSERT INTO products (sku, name, category_id, attributes)
VALUES 
    ('SKU-A', 'Product A', 1, '{"brand": "X"}'),
    ('SKU-B', 'Product B', 2, '{"brand": "Y"}'),
    ('SKU-C', 'Product C', 1, '{"brand": "Z"}')
ON DUPLICATE KEY UPDATE 
    name = VALUES(name),
    attributes = JSON_MERGE_PATCH(COALESCE(attributes, '{}'), VALUES(attributes)),
    updated_at = CURRENT_TIMESTAMP;
