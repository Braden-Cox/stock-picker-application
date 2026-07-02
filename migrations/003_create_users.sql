CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(50) PRIMARY KEY,
    username VARCHAR(50) NOT NULL,
    list_status VARCHAR(20) DEFAULT 'unknown',
    hit_rate FLOAT DEFAULT NULL,
    total_picks INT DEFAULT 0,
    correct_picks INT DEFAULT 0,
    pending_picks INT DEFAULT 0,
    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_scraped TIMESTAMP DEFAULT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)