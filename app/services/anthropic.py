from anthropic import Anthropic
from app.config import settings


client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)




def classify_sentiment_with_haiku(posts: list[str]) -> SentimentResponse: