import requests
import json
import os
from datetime import datetime

# ==========================================
# THINGWORX CONFIGURATION
# ==========================================
# Use environment variables for Render, fallback to the provided credentials
THINGWORX_URL = os.environ.get('THINGWORX_URL', 'http://172.16.78.20:7080/Thingworx')
APP_KEY = os.environ.get('THINGWORX_APP_KEY', 'ab608e23-00b8-433c-8a2c-a5adb4593de6')
THING_NAME = os.environ.get('THINGWORX_THING_NAME', 'SmartClassroom_Thing')

HEADERS = {
    'appKey': APP_KEY,
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

def push_reading_to_thingworx(data):
    """
    Pushes sensor data to a ThingWorx Thing's properties.
    In a real ThingWorx setup, you would typically use a Stream or ValueStream
    for historical data. Here we update the properties of the Thing.
    """
    url = f"{THINGWORX_URL}/Things/{THING_NAME}/Properties/*"
    
    # Format the payload for ThingWorx
    payload = {
        "temperature": data.get("temperature", 0),
        "humidity": data.get("humidity", 0),
        "motion_pct": data.get("motion_pct", 0),
        "sound_level": data.get("sound_level", 0),
        "air_quality": data.get("air_quality", 0),
        "engagement_score": data.get("engagement_score", 0),
        "engagement_level": data.get("engagement_level", "UNKNOWN"),
        "room": data.get("room", "Room A101"),
        "esp_id": data.get("esp_id", "ESP32-01"),
        "last_update": datetime.now().isoformat()
    }

    try:
        # Use PUT to update properties in ThingWorx
        response = requests.put(url, headers=HEADERS, json=payload, timeout=5)
        if response.status_code == 200:
            print(f"[THINGWORX] Successfully updated {THING_NAME} properties.")
            return True
        else:
            print(f"[THINGWORX ERROR] Status {response.status_code}: {response.text}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"[THINGWORX ERROR] Failed to connect to ThingWorx: {e}")
        return False

def push_alert_to_thingworx(alert_data):
    """
    Optionally push alerts to a ThingWorx Service.
    Assumes a service named 'LogAlert' exists on the Thing.
    """
    url = f"{THINGWORX_URL}/Things/{THING_NAME}/Services/LogAlert"
    
    try:
        response = requests.post(url, headers=HEADERS, json=alert_data, timeout=5)
        return response.status_code == 200
    except:
        return False
