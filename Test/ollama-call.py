import aiohttp
from starlette.responses import StreamingResponse
import json


m= 'llama3.3'

current_chat = []

system_prompt = f"You are a personal assistant named Sara. You are witty, occasionally sarcastic and helpful. The following are memories from past conversations that may add valuable context. If they do not, ignore them. "

async def send_to_completions_api(prompt: str):
            current_chat.append({'role': 'system', 'content': system_prompt})
            current_chat.append({'role': 'user', 'content': prompt})
            async with aiohttp.ClientSession() as session:
                data = {'model': m, 'messages': current_chat}  # Use the client-provided model name
                if m == "llama3.3":
                    url = 'http://100.82.117.46:11434/api/chat'
                else:
                    url = 'http://localhost:11434/api/chat'
                try:
                    async with session.post(url, json=data) as response:
                        # Check if the request was successful
                        response.raise_for_status()
                        print("YAY")
                        
                        # Yield each chunk of the response as it becomes available
                        while True:
                            
                            chunk = await response.content.read(1024)
                            if not chunk:
                                break
                            yield chunk.decode('utf-8')
                            print(chunk.decode('utf-8'))
                            
                except aiohttp.ClientResponseError as e:
                    print(f"Request failed: {e.status} - {e.message}")
                except Exception as e:
                    print(f"An error occurred: {e}")
async def stream_response():
        chunk_response = []
        chunk_full_response = ''
        async for chunk in send_to_completions_api(msg_content):
            chunk_response.append(chunk)
            yield chunk
        chunk_full_response = ''.join(chunk_response)
        data_list = [json.loads(line) for line in chunk_full_response.splitlines()]
        chunk_full_response = ''.join([item['response'] for item in data_list])
        #print('\n'.join(map(str, chat_history)))
if __name__ == "__main__":
     prompt = input("text: ")
     res = send_to_completions_api(prompt)
     print(res)
