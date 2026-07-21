-- ==============================================================================
-- E-Commerce Competitor Price Monitor - Database Schema
-- ==============================================================================

-- Create the tables in logical dependency order (parents before children)

-- ------------------------------------------------------------------------------
-- 1. competitors
-- Represents the competitors whose websites are being monitored.
-- ------------------------------------------------------------------------------
CREATE TABLE competitors (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL COMMENT 'Name of the competitor (e.g., Amazon, Walmart)',
    base_url VARCHAR(255) COMMENT 'Base URL of the competitor',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Record creation timestamp'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 2. categories
-- Represents the product categories (e.g., Electronics, Clothing).
-- ------------------------------------------------------------------------------
CREATE TABLE categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL COMMENT 'Name of the category'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 3. products
-- Represents the core product catalog.
-- Uses a JSON column to store variable attributes like specs, brand, colors.
-- ------------------------------------------------------------------------------
CREATE TABLE products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sku VARCHAR(100) UNIQUE NOT NULL COMMENT 'Stock Keeping Unit or unique identifier',
    name VARCHAR(255) NOT NULL COMMENT 'Product Name',
    category_id INT COMMENT 'Foreign key to categories table',
    attributes JSON COMMENT 'Flexible JSON store for variable product specs (brand, color, sizes, etc.)',
    source_competitor_id INT COMMENT 'Which competitor we first discovered this product from',
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When we first saw this product',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT 'When this record was last modified',
    CONSTRAINT fk_products_category FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL,
    CONSTRAINT fk_products_competitor FOREIGN KEY (source_competitor_id) REFERENCES competitors(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 4. price_history
-- Time-series data tracking prices over time for each product on each competitor.
-- ------------------------------------------------------------------------------
CREATE TABLE price_history (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL COMMENT 'Reference to the product',
    competitor_id INT NOT NULL COMMENT 'Reference to the competitor pricing the product',
    price DECIMAL(10,2) NOT NULL COMMENT 'Scraped price amount',
    currency VARCHAR(3) DEFAULT 'USD' COMMENT 'ISO currency code',
    in_stock BOOLEAN DEFAULT TRUE COMMENT 'Whether the item was in stock during scrape',
    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'Timestamp of the scrape event',
    CONSTRAINT fk_price_history_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    CONSTRAINT fk_price_history_competitor FOREIGN KEY (competitor_id) REFERENCES competitors(id) ON DELETE CASCADE,
    -- Unique constraint ensures we don't store multiple identical scrapes at the exact same second
    UNIQUE KEY uk_product_competitor_scraped (product_id, competitor_id, scraped_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 5. price_alerts
-- Triggered events when a significant price change or availability change happens.
-- ------------------------------------------------------------------------------
CREATE TABLE price_alerts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL COMMENT 'Product associated with the alert',
    alert_type ENUM('price_drop', 'price_increase', 'back_in_stock', 'out_of_stock') NOT NULL COMMENT 'Type of event',
    old_price DECIMAL(10,2) COMMENT 'Previous price before the change',
    new_price DECIMAL(10,2) COMMENT 'New price triggering the alert',
    pct_change DECIMAL(5,2) COMMENT 'Percentage change between old and new price',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT 'When the alert was generated',
    CONSTRAINT fk_price_alerts_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ------------------------------------------------------------------------------
-- 6. scrape_runs
-- Logging table to track execution of scraper jobs.
-- ------------------------------------------------------------------------------
CREATE TABLE scrape_runs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    competitor_id INT COMMENT 'Which competitor was scraped (NULL if global)',
    started_at TIMESTAMP COMMENT 'When the run started',
    completed_at TIMESTAMP COMMENT 'When the run finished',
    products_scraped INT DEFAULT 0 COMMENT 'Number of products processed in this run',
    status ENUM('running', 'completed', 'failed') NOT NULL COMMENT 'Current status of the run',
    error_message TEXT COMMENT 'Any error logs if the run failed',
    CONSTRAINT fk_scrape_runs_competitor FOREIGN KEY (competitor_id) REFERENCES competitors(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
