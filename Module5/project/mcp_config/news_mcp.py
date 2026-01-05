# import os
# import requests
# from dotenv import load_dotenv

# load_dotenv()

# API_KEY = os.getenv("NEWS_API_KEY")
# BASE_URL = "https://newsapi.org/v2/top-headlines"

# TOPIC_MAP = {
#     "sport": "sports",
#     "tech": "technology",
#     "business": "business",
#     "politic": "policy",
#     "science": "sci",
#     "health": "health",
#     "entertainment": "fun"
# }

# def get_news(query: str = "") -> str:
#     """
#     Fetch up to 5 news articles.
#     """
#     if not API_KEY:
#         return "⚠️ News API key is missing. Set NEWS_API_KEY in .env."

#     query = query.strip().lower()
#     query = TOPIC_MAP.get(query, query)

#     params = {
#         "apiKey": API_KEY,
#         "language": "en",
#         "pageSize": 5
#     }
#     if query:
#         params["q"] = query

#     try:
#         response = requests.get(BASE_URL, params=params, timeout=10)
#         response.raise_for_status()
#         data = response.json()
#     except requests.exceptions.RequestException as e:
#         return f"⚠️ Failed to fetch news: {str(e)}"

#     articles = data.get("articles", [])
#     if not articles:
#         if query:
#             return get_news("")
#         return "⚠️ No news available at the moment."

#     output = []
#     for art in articles:
#         output.append(
#             f"📰 **Title:** {art.get('title', 'No title')}\n"
#             f"{art.get('description', 'No summary available.')}\n"
#             f"Source: {art.get('source', {}).get('name', 'Unknown')}\n"
#             f"🔗 **URL:** {art.get('url','')}\n"
#         )

#     return "\n\n".join(output)



import os
import requests
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

API_KEY = os.getenv("NEWS_API_KEY")
BASE_URL = "https://newsapi.org/v2/top-headlines"

# Сопоставление пользовательских тем с категориями NewsAPI
TOPIC_MAP = {
    "sport": "sports",
    "sports": "sports",
    "tech": "technology",
    "technology": "technology",
    "business": "business",
    "politics": "general",
    "science": "science",
    "health": "health",
    "entertainment": "entertainment",
    "general": "general"
}

def get_news(query: str = "") -> str:
    """
    Fetch up to 5 news articles from NewsAPI.
    - Determine category if a keyword is found in query
    - If no category, search by keyword
    """
    if not API_KEY:
        return "⚠️ News API key is missing. Set NEWS_API_KEY in your .env file."

    query_lower = query.strip().lower()
    category = None

    # Проверяем, есть ли слово категории в запросе
    for k, v in TOPIC_MAP.items():
        if k in query_lower:
            category = v
            break

    params = {
        "apiKey": API_KEY,
        "pageSize": 5,
        "language": "en",
        "country": "us"  # required for category
    }

    if category:
        params["category"] = category
    elif query.strip():
        params["q"] = query.strip()

    try:
        response = requests.get(BASE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException as e:
        return f"⚠️ Failed to fetch news: {str(e)}"

    articles = data.get("articles", [])
    if not articles:
        if query:
            return get_news("")  # fallback to top headlines
        return "⚠️ No news available at the moment."

    # Форматируем статьи
    output = []
    for art in articles:
        published = art.get("publishedAt")
        if published:
            try:
                published = datetime.fromisoformat(published.replace("Z", "+00:00"))
                published = published.strftime("%Y-%m-%d %H:%M")
            except Exception:
                pass

        output.append(
            f"📰 **Title:** {art.get('title', 'No title')}\n"
            f"{art.get('description', 'No summary available.')}\n"
            f"Source: {art.get('source', {}).get('name', 'Unknown')} | Published: {published}\n"
            f"🔗 [Read full article]({art.get('url','')})\n"
        )

    return "\n\n".join(output)


