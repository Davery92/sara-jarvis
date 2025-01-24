import ollama
from typing import Optional
import requests



def chat_response(query: str) -> str:
    """
    Respond to general chat messages

    Args:
    query: The user message

    Returns:
    str: A chat response.
    """
    response = ollama.chat('llama3.1', messages=[{'role': 'user', 'content': query}])


    return response["message"]["content"]

query_url = "http://10.185.1.9:8080/"
count = 5

def search_searxng(
    query: str,
    filter_list: Optional[list[str]] = None,
    **kwargs,
) -> list[dict]:
    """
    Search a SearXNG instance if user asks a question and return the results as a list of dictionaries.
    
    Args:
        query (str): The search term or question to find in the SearXNG database.
        
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

available_functions = {
  'chat_response': chat_response,
  'search_searxng': search_searxng,
}

def test_chat(prompt):

    response = ollama.chat(
    'llama3.1',
    messages=prompt,
    tools=[chat_response, search_searxng], # Actual function reference
    )


    if response.message.tool_calls:
        for tool in response.message.tool_calls or []:
            function_to_call = available_functions.get(tool.function.name)
            
            if function_to_call:
                print(function_to_call(**tool.function.arguments))
                
            else:
                print('Function not found:', tool.function.name)

    else:
        print(response["message"]["content"])

if __name__ == "__main__":
    while True:
        prompt = []
        query = input("Text: ")
        prompt.append({'role': 'system', 'content': "You have tools you can use to help answer the user query. Do not use them if they aren't necessary"})
        prompt.append({'role': 'user', 'content': query})
        res = test_chat(prompt)
