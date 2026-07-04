import anthropic
from app.config import settings
from pydantic import BaseModel
from typing import List
from app.pipeline.prompts import SENTIMENT_PROMPT
import time

client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


class PostSentiment(BaseModel):
    sentiment: str
    sentiment_score: float
    is_valid: bool


class SentimentResponse(BaseModel):
    results: List[PostSentiment]


def classify_sentiment_with_haiku(posts: list[str]) -> SentimentResponse:
    prompt = SENTIMENT_PROMPT
    for i, post in enumerate(posts, start=1):
        prompt += f'\n{i}. "{post}"'

    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    output = message.content[0].text.strip()
    if output.startswith("```"):
        output = output.split("\n", 1)[1]
        output = output.rsplit("```", 1)[0]
    time.sleep(0.1)  # Sleep for 0.1 seconds as a buffer to avoid rate limiting
    return SentimentResponse.model_validate_json(output.strip())
