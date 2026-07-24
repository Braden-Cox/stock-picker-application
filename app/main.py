from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import picks, users, tickers, pipeline

app = FastAPI(
    title="Stock Picker Application API",
    description=(
    "API for a backend pipeline that scrapes stock-related X (formerly Twitter) posts, "
    "classifies them for relevance using Gemini LLM, and sentiment using Haiku LLM, verifies "
    "predictions agains real price movement, tracks X user credibility over time, and ranks "
    "the most promising current picks based on sentiment and user credibility."
    ),
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(picks.router)
app.include_router(users.router)
app.include_router(tickers.router)
app.include_router(pipeline.router)

@app.get("/")
def root():
    return {
        "status": "ok",
        "message": "Stock Picker Application API is running. Visit /docs for interactive API documentation."
    }
