-- ==============================================================================
-- E-Commerce Competitor Price Monitor - Advanced Analytics
-- ==============================================================================

-- 1. LAG() - Day-over-Day Price Changes
-- Detect price drops or increases by comparing the current row's price to the previous row for the same product & competitor.
SELECT 
    product_id,
    competitor_id,
    scraped_at,
    price,
    LAG(price) OVER (PARTITION BY product_id, competitor_id ORDER BY scraped_at) AS previous_price,
    price - LAG(price) OVER (PARTITION BY product_id, competitor_id ORDER BY scraped_at) AS price_diff
FROM price_history;

-- 2. LEAD() - Forward-Looking Price Movement
-- Peek into the next recorded price to see what happened next.
SELECT 
    product_id,
    competitor_id,
    scraped_at,
    price,
    LEAD(price) OVER (PARTITION BY product_id, competitor_id ORDER BY scraped_at) AS next_price
FROM price_history;

-- 3. DENSE_RANK() - Competitor Price Ranking
-- Rank competitors from cheapest to most expensive for a specific product on a given day.
WITH latest_prices AS (
    SELECT 
        product_id, 
        competitor_id, 
        price,
        ROW_NUMBER() OVER(PARTITION BY product_id, competitor_id ORDER BY scraped_at DESC) as rn
    FROM price_history
)
SELECT 
    product_id,
    competitor_id,
    price,
    DENSE_RANK() OVER (PARTITION BY product_id ORDER BY price ASC) as price_rank
FROM latest_prices
WHERE rn = 1;

-- 4. ROW_NUMBER() - Top N Products by Price Drop
-- Identify the biggest single-day price drops across all products.
WITH price_changes AS (
    SELECT 
        product_id,
        price - LAG(price) OVER (PARTITION BY product_id, competitor_id ORDER BY scraped_at) AS drop_amount
    FROM price_history
)
SELECT 
    product_id,
    drop_amount,
    ROW_NUMBER() OVER (ORDER BY drop_amount ASC) as drop_rank
FROM price_changes
WHERE drop_amount < 0
LIMIT 10;

-- 5. NTILE() - Price Quartile Bucketing
-- Group prices for a category into 4 quartiles to understand price distribution.
SELECT 
    p.id,
    p.name,
    ph.price,
    NTILE(4) OVER (PARTITION BY p.category_id ORDER BY ph.price) as price_quartile
FROM products p
JOIN price_history ph ON ph.product_id = p.id;

-- 6. Window Frames - 7-day Rolling Average Price
-- Calculate a moving average of the price over the last 7 rows (assuming daily data).
SELECT 
    product_id,
    scraped_at,
    price,
    AVG(price) OVER (
        PARTITION BY product_id, competitor_id 
        ORDER BY scraped_at 
        ROWS BETWEEN 6 PRECEDING AND CURRENT ROW
    ) AS rolling_7d_avg
FROM price_history;

-- 7. Window Frames - 30-day Rolling Average Price
SELECT 
    product_id,
    scraped_at,
    price,
    AVG(price) OVER (
        PARTITION BY product_id, competitor_id 
        ORDER BY scraped_at 
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    ) AS rolling_30d_avg
FROM price_history;

-- 8. Multi-Level Aggregation CTE (Daily -> Weekly -> Monthly)
-- Compute averages sequentially across different time granularities.
WITH daily_avg AS (
    SELECT product_id, DATE(scraped_at) as scrape_date, AVG(price) as avg_price
    FROM price_history GROUP BY product_id, DATE(scraped_at)
),
weekly_avg AS (
    SELECT product_id, YEARWEEK(scrape_date) as scrape_week, AVG(avg_price) as avg_weekly_price
    FROM daily_avg GROUP BY product_id, YEARWEEK(scrape_date)
)
SELECT * FROM weekly_avg;

-- 9. Recursive CTE - Hierarchy/Timeline Generation
-- Generate a sequence of dates for the last 30 days to ensure we have a continuous timeline,
-- even if scrapes didn't run every day.
WITH RECURSIVE date_series AS (
    SELECT CURRENT_DATE() - INTERVAL 30 DAY AS calendar_date
    UNION ALL
    SELECT calendar_date + INTERVAL 1 DAY
    FROM date_series
    WHERE calendar_date < CURRENT_DATE()
)
SELECT * FROM date_series;

-- 10. Cross-Competitor Price Gap Analysis
-- Find the absolute and percentage gap between the lowest and highest price for a product.
WITH max_min_prices AS (
    SELECT 
        product_id,
        MIN(price) as lowest_price,
        MAX(price) as highest_price
    FROM price_history
    GROUP BY product_id
)
SELECT 
    product_id,
    lowest_price,
    highest_price,
    (highest_price - lowest_price) AS absolute_gap,
    ((highest_price - lowest_price) / lowest_price) * 100 AS percentage_gap
FROM max_min_prices;

-- 11. Most Volatile Products
-- Find products with the highest standard deviation in price (most frequent/drastic price changes).
SELECT 
    product_id,
    STDDEV(price) AS price_volatility,
    COUNT(*) as observation_count
FROM price_history
GROUP BY product_id
HAVING observation_count > 10
ORDER BY price_volatility DESC
LIMIT 10;

-- 12. Out-of-Stock Duration Analysis
-- Identify how many consecutive rows a product was out of stock.
WITH stock_status_groups AS (
    SELECT 
        product_id,
        competitor_id,
        scraped_at,
        in_stock,
        ROW_NUMBER() OVER (PARTITION BY product_id, competitor_id ORDER BY scraped_at) 
        - ROW_NUMBER() OVER (PARTITION BY product_id, competitor_id, in_stock ORDER BY scraped_at) AS grp
    FROM price_history
)
SELECT 
    product_id,
    competitor_id,
    in_stock,
    COUNT(*) as consecutive_events,
    MIN(scraped_at) as status_started_at,
    MAX(scraped_at) as status_ended_at
FROM stock_status_groups
WHERE in_stock = FALSE
GROUP BY product_id, competitor_id, in_stock, grp;
