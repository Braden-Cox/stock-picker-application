from app.config import settings
import requests

getXAPI_key = settings.GETXAPI_KEY


def getXAPI_scrape_posts(query, cursor=None):
    params = {"q": query, "product": "Latest"}
    if cursor:
        params["cursor"] = cursor
    response = requests.get(
        "https://api.getxapi.com/twitter/tweet/advanced_search",
        params=params,
        headers={"Authorization": "Bearer " + getXAPI_key},
    )
    return response.json()
