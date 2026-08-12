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


RELEVANCE_SCHEMA = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "is_relevant": {"type": "boolean"},
                    "ticker": {"type": "string", "nullable": True},
                },
                "required": ["is_relevant"],
            },
        }
    },
    "required": ["results"],
}


def classify_relevance_with_gemini(
    posts: List[str], historical: bool = False, max_retries: int = 6
) -> RelevanceResponse:
    if historical:
        prompt = HISTORICAL_RELEVANCE_PROMPT
    else:
        prompt = RELEVANCE_PROMPT
    for i, post in enumerate(posts, start=1):
        prompt += f'\n{i}. "{post}"'

    last_error = None
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
                config={
                    "response_mime_type": "application/json",
                    "response_schema": RELEVANCE_SCHEMA,
                },
            )
            output = response.text
            if output is None:
                feedback = response.prompt_feedback
                if feedback and feedback.block_reason:
                    # Deterministic content block — retrying identical input won't help.
                    if len(posts) == 1:
                        print(f"Post blocked by Gemini safety filter ({feedback.block_reason}), marking not relevant: {posts[0][:80]!r}")
                        return RelevanceResponse(results=[RelevanceResult(is_relevant=False)])
                    mid = len(posts) // 2
                    left = classify_relevance_with_gemini(posts[:mid], historical=historical, max_retries=max_retries)
                    right = classify_relevance_with_gemini(posts[mid:], historical=historical, max_retries=max_retries)
                    return RelevanceResponse(results=left.results + right.results)
                raise ValueError("Gemini response text is None")
            output = output.strip()
            if output.startswith("```"):
                output = output.split("\n", 1)[1]
                output = output.rsplit("```", 1)[0]
            time.sleep(0.1)
            return RelevanceResponse.model_validate_json(output.strip())
        except Exception as e:
            last_error = e
            print(f"Gemini response failed (attempt {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                wait = min(2 ** attempt, 60)  # exponential backoff, max 60 seconds
                print(f"Retrying in {wait} seconds...")
                time.sleep(wait)
    raise last_error
