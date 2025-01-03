from fastapi import FastAPI, Request, Body
import sqlite3
import time
import threading
from datetime import datetime, timedelta
import logging
from typing import Dict

# Create a new FastAPI app
app = FastAPI()

# Configuration
DATABASE_NAME = "agent_data.db"
HEARTBEAT_TIMEOUT = 300.0  # Agents are considered offline if no heartbeat in the last 5 minutes

class DeviceManager:
    def __init__(self):
        self.device_statuses = {}  # {(agent_id, device_id): {'status': status, 'last_update': last_update}}
    
    def update_device_status(self, agent_id: str, device_id: str, device_name: str, status: str, current_time: float):
        self.device_statuses[(agent_id, device_id)] = {
            'device_name': device_name,
            'status': status,
            'last_update': current_time
        }
        
    def print_current_device_statuses(self):
        print("Current Device Statuses:")
        for (agent_id, device_id), update in self.device_statuses.items():
            print(f"Device Name: {update['device_name']}, Agent ID: {agent_id}, Status: {update['status']}")

# Create an instance of the DeviceManager class
device_manager = DeviceManager()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# In-memory storage for agent heartbeats and device statuses
agent_heartbeats: Dict[str, float] = {}

# Create or connect to the SQLite database
def init_database():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    # Create a table for storing agent heartbeats if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_heartbeats (
            agent_id TEXT PRIMARY KEY,
            last_heartbeat REAL
        )
    ''')
    # Create a table for storing device statuses if it doesn't exist
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS device_statuses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT,
            device_id TEXT,
            status TEXT,
            last_activity REAL
        )
    ''')
    conn.commit()
    conn.close()

init_database()

# Define the endpoint for receiving heartbeats from agents
@app.post("/agents/heartbeat/")
def receive_heartbeat(heartbeat: Dict[str, str]):
    agent_id = heartbeat.get('agent_id')
    if not agent_id:
        return {"status": "error", "message": "Agent ID is required"}, 400
    current_time = time.time()
    agent_heartbeats[agent_id] = current_time
    # Store heartbeat in the database
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO agent_heartbeats (agent_id, last_heartbeat)
        VALUES (?, ?)
    ''', (agent_id, current_time))
    conn.commit()
    conn.close()
    logging.info(f"Heartbeat received from agent {agent_id}")
    return {"status": "success"}

# Define the endpoint for receiving device statuses
@app.post("/update_device_status/")
def receive_device_status(data: Dict[str, str]):
    try:
        agent_id = data.get('agent_id')
        device_id = data.get('device_id')
        device_name = data.get('device_name')  # assuming you have a 'device_name' key in your data
        status = data.get('status', 'unknown')  # Get the status with a default value
        
        logging.info(f"Received device status update: agent_id={agent_id}, device_id={device_id}, device_name={device_name}, status={status}")
        
        if not agent_id or not device_id:
            return {"status": "error", "message": "Agent ID and Device ID are required"}, 400
        
        current_time = time.time()
        
        # Store device status in the database
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO device_statuses (agent_id, device_id, status, last_activity)
            VALUES (?, ?, ?, ?)
        ''', (agent_id, device_id, status, current_time))
        conn.commit()
        conn.close()
        
        logging.info(f"Device status stored in database: agent_id={agent_id}, device_id={device_id}, status={status}")
        
        # Update the DeviceManager instance
        device_manager.update_device_status(agent_id, device_id, device_name, status, current_time)
        
        logging.info("Updated device manager with new device status")
        
        # Print the updated list of devices with their current statuses
        print("Current Device Statuses:")
        for (agent_id, device_id), update in device_manager.device_statuses.items():
            print(f"Device Name: {update['device_name']}, Agent ID: {agent_id}, Status: {update['status']}")
        
        return {"status": "success"}
    except Exception as e:
        logging.error(f"Error processing device status update: {e}")
        return {"status": "error", "message": str(e)}, 500

# Define the endpoint for sending commands to agents
@app.post("/agents/{agent_id}/command/")
def send_command(agent_id: str, command: Dict[str, str]):
    # Publish the command to the MQTT broker
    import paho.mqtt.client as mqtt
    client = mqtt.Client()
    client.connect("MQTT_BROKER_ADDRESS", 1883, 60)
    client.publish(f"agents/{agent_id}/command", str(command))
    logging.info(f"Command sent to agent {agent_id}: {command}")
    return {"status": "success"}

# Start a background task for aggregating and monitoring agents
def monitor_agents():
    while True:
        current_time = time.time()
        # Check heartbeats
        for agent_id, last_heartbeat in agent_heartbeats.items():
            if current_time - last_heartbeat > HEARTBEAT_TIMEOUT:
                logging.warning(f"Agent {agent_id} is offline")
        # Check device statuses
        for (agent_id, device_id), status in device_manager.device_statuses.items():
            if current_time - float(status['last_update']) > HEARTBEAT_TIMEOUT:
                logging.warning(f"Device {device_id} of agent {agent_id} is inactive")
        time.sleep(60)  # Monitor every minute

# Run the background task
monitor_thread = threading.Thread(target=monitor_agents)
monitor_thread.daemon = True
monitor_thread.start()

# Run the FastAPI app
if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)