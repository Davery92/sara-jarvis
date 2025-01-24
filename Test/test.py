import asyncio
from fastapi import FastAPI
import datetime

app = FastAPI()

ml_models = {
    "current_model": None
}

async def check_service_periodically():
    while True:
        print(f"Checking service status at {datetime.datetime.now()}", flush=True)
        
        try:
            # Replace with actual HTTP request logic
            response_status = 200  # Simulated successful response
            
            if response_status == 200:
                ml_models["current_model"] = "latest_model"
                print("Service is available. Using latest model.", flush=True)
            else:
                ml_models["current_model"] = "fallback_model"
                print("Service is unavailable or returned non-200 status. Using fallback model.", flush=True)
                
        except Exception as e:
            ml_models["current_model"] = "fallback_model"
            print(f"An error occurred: {str(e)}. Using fallback model.", flush=True)
            
        await asyncio.sleep(60)
        print("Periodic check completed. Next check in 60 seconds.", flush=True)

@app.on_event("startup")
async def startup_event():
    print("Starting up the application and background tasks...", flush=True)
    asyncio.create_task(check_service_periodically())

@app.get("/")
async def root():
    return {"message": "Service is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)