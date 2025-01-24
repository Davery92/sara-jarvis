import logging
from typing import Optional
import requests

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

def search_searxng(
    query: str,
    filter_list: Optional[list[str]] = None,
    **kwargs,
) -> list[dict]:
    """
    Search a SearXNG instance for a given query and return the results as a list of dictionaries.
    
    Args:
        query_url (str): The base URL of the SearXNG server.
        query (str): The search term or question to find in the SearXNG database.
        count (int): The maximum number of results to retrieve from the search.
        
    Keyword Args:
        language (str): Language filter for the search results; e.g., "en-US". Defaults to an empty string.
        safesearch (int): Safe search filter for safer web results; 0 = off, 1 = moderate, 2 = strict. Defaults to 1 (moderate).
        time_range (str): Time range for filtering results by date; e.g., "2023-04-05..today" or "all-time". Defaults to ''.
        
    Returns:
        list[dict]: A list of dictionaries containing the search results.
        
    Raise:
        requests.exceptions.RequestException: If a request error occurs during the search process.
    """
    
    # Default values for optional parameters are provided as empty strings or None when not specified.
    language = kwargs.get("language", "en-US")
    
    params = {
        "q": query,
        "format": "json",
        "pageno": 1,
        "language": language,
        "theme": "simple",
        "image_proxy": 0,
    }
    
    log.debug(f"searching {query_url}")
    
    response = requests.get(
        query_url,
        headers={
            "User-Agent": "Open WebUI (https://github.com/open-webui/open-webui) RAG Bot",
            "Accept": "text/html",
            "Accept-Encoding": "gzip, deflate",
            "Accept-Language": "en-US,en;q=0.5",
            "Connection": "keep-alive",
        },
        params=params,
    )
    
    response.raise_for_status()  # Raise an exception for HTTP errors.
    
    json_response = response.json()
    
    results = json_response.get("results", [])
    
    return [
        {
            "url": result["url"],
            "title": result.get("title"),
            "content": result.get("content")
        }
        for result in results[:count]
    ]

# Example usage:
query_url = "http://10.185.1.9:8080/"
query = "python programming"
count = 5

results = search_searxng(query)

for result in results:
    print(f"Title: {result['title']}")
    print(f"URL: {result['url']}")
    print(f"Content: {result['content']}\n")