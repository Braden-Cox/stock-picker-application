CREATE TABLE IF NOT EXISTS tickers (
    ticker VARCHAR(10) PRIMARY KEY,
    company_name VARCHAR(255),
    exchange VARCHAR(100) NOT NULL,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    flag_reason VARCHAR(255),
    needs_prefix BOOLEAN NOT NULL DEFAULT FALSE,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_posts_scraped INT DEFAULT 0,
    relevant_posts INT DEFAULT 0,
    relevance_rate FLOAT DEFAULT NULL
)