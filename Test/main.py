# main.py
from fastapi import FastAPI, Body
import numpy as np
from pydantic import BaseModel
import chromadb
import json
import ollama
import aiohttp
from starlette.responses import StreamingResponse
import asyncio
from uuid import uuid4
from datetime import date, datetime


app = FastAPI()


stm_chroma_client = chromadb.PersistentClient(path="/home/david/sara-jarvis/Sara/stm_index.chromadb")
ltm_chroma_client = chromadb.PersistentClient(path="/home/david/sara-jarvis/Sara/ltm_index.chromadb")
stm_collection = stm_chroma_client.get_or_create_collection(name="stm")
ltm_collection = ltm_chroma_client.get_or_create_collection(name="ltm")



def write_to_file(role, content, dates):
    try:
        with open(f"/home/david/sara-jarvis/Sara/{dates}.txt",'x+') as f:
            pass  # Create the file but don't write anything yet
    except FileExistsError:
        pass  # The file already exists
    with open(f"/home/david/sara-jarvis/Sara/{dates}.txt", 'a+') as f:
        f.write(f"{role}:\n")
        f.write(content + "\n")

current_chat = []

class ChatMessage(BaseModel):
    """Chat message model"""
    user_id: str
    message: str

def text_to_embedding_ollama(text):
    model_name = "bge-m3"
    response = ollama.embed(model=model_name, input=text)
    return response

def clear_chromadb_database():
    """Clears the entire ChromaDB database"""
    stm_collection.clear()

def stm_query_chromadb_index(query_vectors):

    results = stm_collection.query(
        query_embeddings=query_vectors,
        n_results=3,
    )
    metadata_content = [meta['content'] for meta in results['metadatas'][0]]
    print(metadata_content)
    return metadata_content

def ltm_query_chromadb_index(query_vectors):

    results = ltm_collection.query(
        query_embeddings=query_vectors,
        n_results=3,
    )
    metadata_content = [meta['content'] for meta in results['metadatas'][0]]
    print(metadata_content)
    return metadata_content


def embed_and_save(content, id):
    today = date.today()
    formatted_date = today.strftime("%m-%d-%Y")
    embeddings = text_to_embedding_ollama(content)
    embedding = embeddings['embeddings']
    embeddings = np.array(embedding, dtype=np.float32)
    stm_collection.upsert(
        embeddings=embedding,
        metadatas={'role': 'assistant', 'content': content},
        ids=[id]
    )
    current_chat.append({'role': 'assistant', 'content': content})
    write_to_file('Assistant', content, formatted_date)
    return embeddings

async def async_embed_and_save(content, id):
    await asyncio.to_thread(embed_and_save, content, id)

@app.post("/api/chat")
async def receive_chat_message(data: dict = Body(...)):    
    try:
        date_time = datetime.now().strftime('%A, %B %d, %Y %H:%M:%S')
        id = str(uuid4())
        today = date.today()
        formatted_date = today.strftime("%m-%d-%Y")
        message = data["message"]
        
        msg_content = message["content"]
        if "/think" in msg_content:
            m = "deepseek-r1:70b"
            msg_content = msg_content.replace("/think", "")
        else:
            m = data["model"]
        embeddings = text_to_embedding_ollama(msg_content)
        embedding = embeddings['embeddings']
        embeddings = np.array(embedding, dtype=np.float32)
        stm_messages = stm_query_chromadb_index(embedding)
        system_prompt = f"You are a personal assistant named Sara. You are witty, occasionally sarcastic and helpful. The current date and time is: {date_time} You have access to working memory akin to that of a human with short term, long term and deep storage memories. Each interaction causes a recollection of closely related memories. If these memories do not pertain to the conversation and do not help you, simply ignore them. Short Term Memories: {stm_messages} "
        current_chat.append({'role': 'system', 'content': system_prompt})
        current_chat.append({'role': 'user', 'content': msg_content})
        if len(current_chat) >= 10:
            current_chat.pop(0)
        write_to_file('User', msg_content, formatted_date)
        stm_collection.upsert(
            embeddings=embedding,
            metadatas={'role': 'user', 'content': msg_content},
            ids=[id]
            )
        
        

        async def send_to_completions_api(prompt: str):
            async with aiohttp.ClientSession() as session:
                
                    

                    pass
                    data = {'model': m, 'messages': current_chat}  # Use the client-provided model name
                    if m in ("llama3.3", "deepseek-r1:70b"):
                        url = 'http://100.82.117.46:11434/api/chat'
                    else:
                        url = 'http://localhost:11434/api/chat'
                    try:
                        async with session.post(url, json=data) as response:
                            # Check if the request was successful
                            response.raise_for_status()
                            
                            # Yield each chunk of the response as it becomes available
                            while True:
                                
                                chunk = await response.content.read(1024)
                                if not chunk:
                                    break
                                yield chunk.decode('utf-8')
                                
                    except aiohttp.ClientResponseError as e:
                        print(f"Request failed: {e.status} - {e.message}")
                    except Exception as e:
                        print(f"An error occurred: {e}")
        # Send the request asynchronously and yield each chunk of the response
        async def stream_response():
            chunk_response = []
            chunk_full_response = ''
            async for chunk in send_to_completions_api(msg_content):
                chunk_response.append(chunk)
                yield chunk
            chunk_full_response = ''.join(chunk_response)
            data_list = [json.loads(line) for line in chunk_full_response.splitlines()]
            chunk_full_response = ''.join([item['message']['content'] for item in data_list])
            await async_embed_and_save(chunk_full_response, id)
        return StreamingResponse(stream_response(), media_type="text/event-stream")
    
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7004)