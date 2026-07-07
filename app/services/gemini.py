import time
from google import genai
from app.config import settings
from pydantic import BaseModel
from typing import List, Optional
from app.pipeline.prompts import RELEVANCE_PROMPT, HISTORICAL_RELEVANCE_PROMPT

GEMINI_API_KEY = settings.GOOGLE_GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)


class RelevanceResult(BaseModel):
    is_relevant: bool
    ticker: Optional[str] = None


class RelevanceResponse(BaseModel):
    results: List[RelevanceResult]


def classify_relevance_with_gemini(posts: List[str], historical: bool = False) -> RelevanceResponse:
    if historical:
        prompt = HISTORICAL_RELEVANCE_PROMPT
    else:
        prompt = RELEVANCE_PROMPT
    # Prepare the input for the Gemini model
    for i, post in enumerate(posts, start=1):
        prompt += f'\n{i}. "{post}"'
    response = client.interactions.create(
        model="gemini-2.5-flash-lite",
        input=prompt,
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": RelevanceResponse.model_json_schema(),
        },
    )

    output = response.output_text.strip()
    if output.startswith("```"):
        output = output.split("\n", 1)[1]
        output = output.rsplit("```", 1)[0]
    time.sleep(.1)  # Sleep for 0.1 seconds as a buffer to avoid rate limiting
    return RelevanceResponse.model_validate_json(output.strip())
