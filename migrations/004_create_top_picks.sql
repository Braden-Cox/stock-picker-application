CREATE TABLE IF NOT EXISTS top_picks (
    pick_id SERIAL PRIMARY KEY,
    post_id VARCHAR(50) REFERENCES posts(post_id),
    ticker VARCHAR(5),
    score FLOAT,
    sentiment VARCHAR(10),
    predicted_timeframe VARCHAR(20),
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE
)