import paho.mqtt.client as mqtt
from pynput import mouse, keyboard
import requests
import time
import threading
import json
import socket
import logging

# Configuration
MQTT_BROKER_ADDRESS = "10.185.1.8"
MQTT_PORT = 1883
MQTT_USERNAME = "your_username"  # Replace with your MQTT username
MQTT_PASSWORD = "your_password"  # Replace with your MQTT password
HEARTBEAT_INTERVAL = 60  # seconds
AGENT_ID = f"agent_{socket.gethostname()}"
CENTRAL_SERVER_URL = "http://10.185.1.8:7000"

# MQTT Topics
HEARTBEAT_TOPIC = "agents/heartbeat"
DEVICE_STATUS_TOPIC = "device/status"
COMMAND_TOPIC = f"agents/{AGENT_ID}/command"

# Global variables to store sensor data and command responses
last_heartbeat_time = time.time()
keyboard_event_counter = 0
mouse_click_counter = 0

device_status = {
    "agent_id": AGENT_ID,
    "status": "inactive",  # Default status is inactive
    "keyboard_events": 0,
    "mouse_clicks": 0
}

# Function to send heartbeat
def send_heartbeat():
    global last_heartbeat_time  # Declare as global
    while True:
        current_time = time.time()
        if current_time - last_heartbeat_time > HEARTBEAT_INTERVAL:
            client.publish(HEARTBEAT_TOPIC, json.dumps({"agent_id": AGENT_ID}))
            logging.info(f"Heartbeat sent: {AGENT_ID}")
            last_heartbeat_time = current_time
        time.sleep(10)

# Function to send device status
def send_device_status():
    while True:
        global keyboard_event_counter, mouse_click_counter  # Declare as global
        
        # Update device_status dictionary with current counters
        device_status["keyboard_events"] = keyboard_event_counter
        device_status["mouse_clicks"] = mouse_click_counter
        
        logging.info(f"Keyboard events: {device_status['keyboard_events']}")
        logging.info(f"Mouse clicks: {device_status['mouse_clicks']}")
        
        # Set device status based on activity
        if keyboard_event_counter > 0 or mouse_click_counter > 0:
            device_status["status"] = "active"
        else:
            device_status["status"] = "inactive"
        
        client.publish(DEVICE_STATUS_TOPIC, json.dumps(device_status))
        logging.info(f"Device status sent: {device_status}")
        
        # Reset keyboard and mouse click counters
        keyboard_event_counter = 0
        mouse_click_counter = 0
        
        time.sleep(60)  # Send status every minute

# Callback for when the client receives a CONNACK response from the server
def on_connect(client, userdata, flags, reason_code, properties):
    print(f"Connected with result code {reason_code}")
    client.subscribe(COMMAND_TOPIC)

# Callback for when a PUBLISH message is received from the server
def on_message(client, userdata, msg):
    try:
        command = json.loads(msg.payload.decode('utf-8'))
        logging.info(f"Received command: {command}")
        response = execute_command(command)
        client.publish(COMMAND_TOPIC + "/response", json.dumps(response))
    except Exception as e:
        logging.error(f"Failed to process command: {str(e)}")

# Function to execute commands
def execute_command(command):
    # Implement logic to execute specific commands
    action = command.get("action")
    if action == "get_status":
        return {"status": device_status}
    elif action == "shutdown":
        logging.info("Shutting down agent...")
        client.loop_stop()
        client.disconnect()
        import os
        os._exit(0)
    else:
        return {"error": f"Unknown command: {action}"}

# Function to handle keyboard events
# Function to handle keyboard events
def on_press(key):
    try:
        global keyboard_event_counter  # Declare as global
        keyboard_event_counter += 1
        logging.info(f"Keyboard event counter: {keyboard_event_counter}")
    except Exception as e:
        logging.error(f"Failed to log keyboard event: {str(e)}")

# Function to handle mouse click events
def on_click(x, y, button, pressed):
    global mouse_click_counter  # Declare as global
    if pressed:
        mouse_click_counter += 1
        logging.info(f"Mouse click counter: {mouse_click_counter}")

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
# Set callbacks for MQTTv5
client.on_connect = on_connect
client.on_message = on_message
# Connect to the MQTT broker with username and password
client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)
client.connect(MQTT_BROKER_ADDRESS, MQTT_PORT, 60)

# Start the MQTT client loop in a separate thread
mqtt_thread = threading.Thread(target=client.loop_forever)
mqtt_thread.daemon = True
mqtt_thread.start()

# Set up keyboard and mouse listeners
keyboard_listener = keyboard.Listener(on_press=on_press)
mouse_listener = mouse.Listener(on_click=on_click)
# Start the keyboard and mouse listeners in separate threads
keyboard_listener.start()
mouse_listener.start()

# Start sending heartbeats and device status
heartbeat_thread = threading.Thread(target=send_heartbeat)
status_thread = threading.Thread(target=send_device_status)
heartbeat_thread.daemon = True
status_thread.daemon = True
heartbeat_thread.start()
status_thread.start()

logging.info(f"Agent {AGENT_ID} started")

# Keep the main thread alive
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    logging.info("Agent shutting down")
    client.loop_stop()
    client.disconnect()
    keyboard_listener.stop()
    mouse_listener.stop()