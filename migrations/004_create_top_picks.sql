CREATE TABLE IF NOT EXISTS top_picks (
    pick_id SERIAL PRIMARY KEY,
    post_id VARCHAR(50) REFERENCES posts(post_id),
    user_id VARCHAR(50) REFERENCES users(user_id),
    tickers VARCHAR(5)[],
    score FLOAT,
    sentiment VARCHAR(10),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE
)