import paho.mqtt.client as mqtt
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Update these variables to connect to your local MQTT broker
MQTT_BROKER = "10.185.1.8"  # Replace with the IP address of your Mosquitto broker
MQTT_PORT = 1883

# Define topics to subscribe to
HEARTBEAT_TOPIC = "agents/heartbeat"
DEVICE_STATUS_TOPIC = "device/status"
COMMAND_RESPONSE_TOPIC_PREFIX = "agents/"

def on_connect(client, userdata, flags, reason_code, properties):
    logging.info(f"Connected with result code {reason_code}")
    try:
        client.subscribe(HEARTBEAT_TOPIC)
        client.subscribe(DEVICE_STATUS_TOPIC + "/#")
        client.subscribe(COMMAND_RESPONSE_TOPIC_PREFIX + "+/response")
        logging.info("Subscribed to topics:")
        logging.info(f"- {HEARTBEAT_TOPIC}")
        logging.info(f"- {DEVICE_STATUS_TOPIC}/#")
        logging.info(f"- {COMMAND_RESPONSE_TOPIC_PREFIX}+/response")
    except Exception as e:
        logging.error(f"Failed to subscribe: {e}")

def on_message(client, userdata, msg):
    try:
        message = json.loads(msg.payload.decode('utf-8'))
        topic_parts = msg.topic.split("/")
        
        if msg.topic == HEARTBEAT_TOPIC:
            logging.info(f"Heartbeat received from agent: {message['agent_id']}")
        elif topic_parts[0] == "device" and topic_parts[1] == "status":
            logging.info(f"Device status update received from agent: {message['agent_id']}")
            # Print the device status
            logging.info(f"Received device status: {message.get('status', 'Status not found')}")
            # Process device status update
            process_device_status(message)
        elif len(topic_parts) >= 3 and topic_parts[0] == "agents" and topic_parts[2] == "response":
            logging.info(f"Command response received from agent: {topic_parts[1]}")
            # Process command response
            process_command_response(message, topic_parts[1])
    except Exception as e:
        logging.error(f"Error processing message: {e}")

def on_subscribe(client, userdata, mid, reason_codes, properties):
    if len(reason_codes) > 0 and reason_codes[0].is_failure:
        logging.error(f"Broker rejected your subscription: {reason_codes[0]}")
    else:
        logging.info(f"Broker granted the following QoS: {[code.value for code in reason_codes]}")

def on_unsubscribe(client, userdata, mid, reason_codes, properties):
    if len(reason_codes) == 0 or not reason_codes[0].is_failure:
        logging.info("Unsubscribe succeeded (if SUBACK is received in MQTTv3 it success)")
    else:
        logging.error(f"Broker replied with failure: {reason_codes[0]}")
    client.disconnect()

def process_device_status(message):
    # Update main server about device status
    response = requests.post(
        "http://10.185.1.8:7000/update_device_status/",
        json={"device_id": message['agent_id'], "status": message.get('status', 'unknown')}
    )
    logging.info(f"Main server updated with data from {message['agent_id']}: {response.status_code}")

def process_command_response(message, agent_id):
    # Process command response
    if 'error' in message:
        logging.error(f"Error executing command on agent {agent_id}: {message['error']}")
    else:
        logging.info(f"Command executed successfully on agent {agent_id}: {message}")

# Create an MQTT client instance using MQTTv5
client = mqtt.Client(protocol=mqtt.MQTTv5, transport='tcp')
# Set the callback functions
client.on_connect = on_connect
client.on_message = on_message
client.on_subscribe = on_subscribe
client.on_unsubscribe = on_unsubscribe

try:
    client.connect(MQTT_BROKER, MQTT_PORT, 60)
    client.loop_forever()
except Exception as e:
    logging.error(f"Failed to connect to MQTT broker: {e}")