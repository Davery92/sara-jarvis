from ollama import ChatResponse, chat
import requests
import logging
from typing import Optional
import json

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

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

#results = search_searxng(query)


def ai_chat(query: str,):

  '''
  Chat with the ai and return a json message
  
  Args:
    query (str): The users message that the AI will reply too.
    
  Returns:
    json: a json reponse
    '''

  
  return query


def attempt(messages):


  #messages = [{'role': 'system', 'content': 'You are an advanced personal assistant. You respond to the user with wit and sarcasm, and you also have tools at your disposal. If you think the users message requires a tool, then use it. If not, just respond.'}]

  system_prompt = "You are an advanced personal assistant. You respond to the user with wit and sarcasm, and you also have tools at your disposal. If you think the users message requires a tool, then use it. If not, just respond."

  available_functions = {
    'search_searxng': search_searxng,
    'ai_chat': ai_chat,
  }
  response: ChatResponse = chat(
    'llama3.1',
    
    messages=messages,
    
    tools=[search_searxng, ai_chat], 
  )


  if response.message.tool_calls:
    # There may be multiple tool calls in the response
    skip_rest = False  # Initialize a flag to skip the rest of the function if needed
    for tool in response.message.tool_calls:
      # Ensure the function is available, and then call it
      if function_to_call := available_functions.get(tool.function.name):
        if function_to_call == available_functions.get(ai_chat):
          output = function_to_call(**tool.function.arguments)
          print(output)
          skip_rest = True  # Set the flag to skip the rest of the function
          break  # Break out of the loop since we don't need to process any more tool calls
        else:
          print('Calling function:', tool.function.name)
          print('Arguments:', tool.function.arguments)
          output = function_to_call(**tool.function.arguments)
          print('Function output:', output)
    if not skip_rest:  # Only continue with the rest of the function if the flag is False
      if response.message.tool_calls:
        # Add the function response to messages for the model to use
        messages.append(response.message)
        messages.append({'role': 'tool', 'content': str(output), 'name': tool.function.name})
        # Get final response from model with function outputs
        final_response = chat('llama3.1', messages=messages)
        print('Final response:', final_response.message.content)
  else:
    print('Function', tool.function.name, 'not found')

      

if __name__ == "__main__":
  while True:
    query = input("Enter text: ")
    query = [{'role': 'user', 'content': f"You are an advanced personal assistant. You respond to the user with wit and sarcasm, and you also have tools at your disposal. If you think the users message requires a tool, then use it. If not, just chat with them. The users message: {query}"}]
    attempt(query)
