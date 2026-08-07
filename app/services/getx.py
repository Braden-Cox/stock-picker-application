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
        timeout=(10,30), #10 second connection timeout, 30 second read timeout
    )
    return response.json()


def getXAPI_get_username_by_id(user_id):
    response = requests.get(
        "https://api.getxapi.com/twitter/user/info_by_id",
        params={"userId": user_id},
        headers={"Authorization": "Bearer " + getXAPI_key},
        timeout=(10,30), #10 second connection timeout, 30 second read timeout
    )
    data = response.json()
    if "data" not in data or "userName" not in data["data"]:
        raise ValueError(f"Could not resolve username for user_id {user_id}: {data}")
    return data["data"]["userName"]
