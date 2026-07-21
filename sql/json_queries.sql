-- ==============================================================================
-- E-Commerce Competitor Price Monitor - JSON Queries Showcase
-- ==============================================================================

-- 1. Extracting string values using ->> (unquoted) and -> (quoted) operators
-- This retrieves the brand of the product without JSON quotes.
SELECT 
    id, 
    name, 
    attributes->>'$.brand' AS brand 
FROM products 
WHERE attributes->>'$.brand' IS NOT NULL;

-- 2. Extracting nested arrays or objects
-- Useful when a product has multiple colors or variations in an array.
SELECT 
    id, 
    name, 
    attributes->'$.colors' AS colors_array 
FROM products 
WHERE JSON_TYPE(attributes->'$.colors') = 'ARRAY';

-- 3. JSON_CONTAINS
-- Finding products that have a specific attribute value.
-- E.g., Find all products where "Red" is one of the colors in the JSON array.
SELECT 
    id, 
    name 
FROM products 
WHERE JSON_CONTAINS(attributes, '"Red"', '$.colors');

-- 4. JSON_TABLE
-- Flattening a JSON array of technical specifications into relational rows.
-- Assume attributes contains: {"specs": [{"name": "Weight", "value": "1kg"}, {"name": "Screen", "value": "15 inch"}]}
SELECT 
    p.id AS product_id, 
    p.name AS product_name, 
    specs.spec_name, 
    specs.spec_value
FROM products p,
JSON_TABLE(
    p.attributes, 
    '$.specs[*]' COLUMNS (
        spec_name VARCHAR(50) PATH '$.name',
        spec_value VARCHAR(100) PATH '$.value'
    )
) AS specs;

-- 5. JSON_ARRAYAGG
-- Aggregate multiple scalar values into a JSON array per category.
-- Creates a single JSON array of product names per category.
SELECT 
    c.name AS category_name, 
    JSON_ARRAYAGG(p.name) AS all_products_in_category
FROM categories c
JOIN products p ON p.category_id = c.id
GROUP BY c.id;

-- 6. JSON_MERGE_PATCH
-- Update a product's JSON attribute to add or update a specific field without overwriting the whole document.
-- E.g., Adding or updating the "warranty" field.
UPDATE products 
SET attributes = JSON_MERGE_PATCH(attributes, '{"warranty": "2 years"}')
WHERE id = 1;

-- 7. Generated Columns with JSON
-- In a real scenario, you can alter the table to add a virtual column based on JSON and index it.
ALTER TABLE products 
ADD COLUMN brand VARCHAR(100) GENERATED ALWAYS AS (attributes->>'$.brand') VIRTUAL;

CREATE INDEX idx_products_brand ON products(brand);

-- 8. JSON_KEYS
-- Discovering the schema of the JSON documents. Useful for exploratory data analysis.
SELECT 
    id, 
    JSON_KEYS(attributes) AS available_attribute_keys
FROM products
WHERE JSON_LENGTH(attributes) > 0;

-- 9. JSON_LENGTH
-- Finding products with more than 3 specifications/attributes.
SELECT 
    id, 
    name, 
    JSON_LENGTH(attributes) AS attribute_count
FROM products
WHERE JSON_LENGTH(attributes) > 3;

-- 10. JSON_SEARCH
-- Search for a specific string value across the entire JSON document, returning the path.
SELECT 
    id, 
    name, 
    JSON_SEARCH(attributes, 'one', 'Apple') AS path_to_apple
FROM products
WHERE JSON_SEARCH(attributes, 'one', 'Apple') IS NOT NULL;
