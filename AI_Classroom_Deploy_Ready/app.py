"""
================================================================
  FLASK BACKEND SERVER - Smart Classroom IoT Analytics System
  Team-8 | GLA University | B.Tech CSE (AI-ML)
  
  Receives real sensor data from ESP32 via HTTP POST,
  processes through ML engine, stores in SQLite,
  pushes real-time updates to dashboard via WebSocket.
================================================================
"""

from flask import Flask, request, jsonify, send_from_directory, render_template_string
from flask_socketio import SocketIO, emit
from flask_cors import CORS
from datetime import datetime, timedelta
import os
import json
import threading
import time

from database import (
    init_db, insert_reading, get_readings, get_readings_range,
    get_daily_averages, insert_alert, get_alerts, get_alert_stats,
    start_session, end_session, get_sessions, get_thresholds,
    update_thresholds
)
from ml_model import predict_engagement, load_models, get_engagement_insights, classify_engagement
# import thingworx_api

# ═══ APP INITIALIZATION ═══

app = Flask(__name__, static_folder='.', static_url_path='')
app.config['SECRET_KEY'] = 'smartclassroom-team8-gla-2026'
CORS(app, origins="*")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# Track connected ESP32 devices and active sessions
connected_devices = {}
active_sessions = {}
alert_streaks = {}  # Track consecutive alert conditions
room_state = {}     # Cache aggregated sensor values per room for distributed ESP32s


# ═══ GUNICORN-SAFE INITIALIZATION ═══
# This block runs once when app.py is imported (by Gunicorn or locally).
# The _initialized flag prevents double-init if Flask debug reloader triggers a reload.

_initialized = False

def initialize():
    """Initialize database and ML models on startup."""
    global _initialized
    if _initialized:
        return
    _initialized = True
    print("\n" + "=" * 60)
    print("  AI-Powered Smart Classroom Analytics System")
    print("  Team-8 | GLA University | B.Tech CSE (AI-ML)")
    print("=" * 60)
    init_db()
    load_models()
    # Start default sessions for all rooms
    for room in ['Room A101', 'Room B205', 'Room C310']:
        sid = start_session(room)
        active_sessions[room] = sid
        alert_streaks[room] = {'low_eng': 0, 'low_motion': 0}
    print("[SERVER] Ready! Waiting for ESP32 connections...")
    print("[SERVER] Dashboard: http://localhost:5000")
    print("[SERVER] Health check: /api/health")
    print("=" * 60 + "\n")

# Run initialization immediately when imported by Gunicorn
initialize()


# ═══ SERVE FRONTEND ═══

@app.route('/')
def index():
    """Serve the main dashboard."""
    return send_from_directory('.', 'index.html')


# ═══ ESP32 DATA INGESTION ENDPOINT ═══

@app.route('/api/sensor-data', methods=['POST'])
def receive_sensor_data():
    """
    Receive sensor data from ESP32 via HTTP POST.
    Expected JSON payload:
    {
        "esp_id": "ESP32-01",
        "room": "Room A101",
        "temperature": 24.5,
        "humidity": 55.2,
        "pir1": 1,
        "pir2": 1,
        "pir3": 0,
        "sound_level": 58.3,
        "sound_raw": 2048,
        "air_quality": 85,
        "ldr_value": 600
    }
    """
    try:
        data = request.get_json(force=True)
        if not data:
            return jsonify({'error': 'No JSON data received'}), 400

        room = data.get('room', 'Room A101')
        esp_id = data.get('esp_id', 'ESP32-01')

        # Track device connection
        connected_devices[esp_id] = {
            'room': room,
            'last_seen': datetime.now().isoformat(),
            'ip': request.remote_addr
        }

        # Initialize room state if not exists
        if room not in room_state:
            room_state[room] = {
                'temperature': 24.0,
                'humidity': 50.0,
                'pir1': 0,
                'pir2': 0,
                'pir3': 0,
                'sound_level': 45.0,
                'sound_raw': 2048,
                'air_quality': 50,
                'ldr_value': 0
            }

        # Update room state with ONLY the keys provided in this payload
        for key in ['temperature', 'humidity', 'pir1', 'pir2', 'pir3', 'sound_level', 'sound_raw', 'air_quality', 'ldr_value']:
            if key in data:
                room_state[room][key] = data[key]

        # Use the merged room state for all calculations
        merged = room_state[room]

        # Calculate motion percentage from merged state
        pir1 = int(merged['pir1'])
        pir2 = int(merged['pir2'])
        pir3 = int(merged['pir3'])
        motion_pct = round(((pir1 + pir2 + pir3) / 3) * 100, 1)
        merged['motion_pct'] = motion_pct

        # Compute session duration for time decay
        session_minutes = 0
        if room in active_sessions:
            sessions = get_sessions(room, limit=1)
            if sessions and sessions[0].get('start_time'):
                try:
                    start = datetime.fromisoformat(sessions[0]['start_time'])
                    session_minutes = (datetime.now() - start).total_seconds() / 60
                except:
                    pass

        # ML engagement prediction using merged state
        result = predict_engagement(merged, session_minutes)
        merged['engagement_score'] = result['score']
        merged['engagement_level'] = result['level']
        merged['timestamp'] = datetime.now().isoformat()
        merged['source'] = 'hardware_merged'
        merged['esp_id'] = esp_id
        merged['room'] = room

        # Store merged state in local SQLite database
        insert_reading(merged)

        # ---------------------------------------------------------
        # PUSH TO THINGWORX CLOUD DATABASE
        # ---------------------------------------------------------
        # Execute push to ThingWorx in a separate thread using merged data
        # threading.Thread(target=thingworx_api.push_reading_to_thingworx, args=(merged,), daemon=True).start()

        # Check alert conditions
        check_and_emit_alerts(merged, room)

        # Emit to all connected dashboard clients via WebSocket
        emit_data = {
            'timestamp': merged['timestamp'],
            'room': room,
            'esp_id': esp_id,
            'temperature': merged.get('temperature'),
            'humidity': merged.get('humidity'),
            'pir1': pir1,
            'pir2': pir2,
            'pir3': pir3,
            'sound_level': merged.get('sound_level'),
            'air_quality': merged.get('air_quality'),
            'ldr_value': merged.get('ldr_value'),
            'motion': motion_pct,
            'engagement': result['score'],
            'level': result['level'],
            'method': result.get('method', 'formula'),
            'source': 'hardware_merged'
        }
        socketio.emit('new_reading', emit_data)

        return jsonify({
            'status': 'ok',
            'engagement_score': result['score'],
            'engagement_level': result['level'],
            'prediction_method': result.get('method', 'formula')
        }), 200

    except Exception as e:
        print(f"[ERROR] Sensor data processing failed: {e}")
        return jsonify({'error': str(e)}), 500


# ═══ ALERT ENGINE ═══

def check_and_emit_alerts(data, room):
    """Check sensor data against thresholds and emit alerts."""
    thresholds = get_thresholds(room)
    if not thresholds:
        return

    alerts_generated = []
    streaks = alert_streaks.get(room, {'low_eng': 0, 'low_motion': 0})

    temp = data.get('temperature', 23)
    humidity = data.get('humidity', 50)
    sound = data.get('sound_level', 55)
    engagement = data.get('engagement_score', 50)
    motion = data.get('motion_pct', 50)

    # Temperature check
    if temp and temp > thresholds['temp_warning']:
        severity = 'CRITICAL' if temp > thresholds.get('temp_critical', 32) else 'WARNING'
        alert = {
            'severity': severity,
            'message': f'🌡️ Temperature {temp}°C exceeds {thresholds["temp_warning"]}°C threshold',
            'sensor': 'Temperature',
            'action': 'Adjust HVAC or open windows to cool the room'
        }
        alerts_generated.append(alert)
        insert_alert(room, **alert)

    # Humidity check
    if humidity and humidity > thresholds['humidity_warning']:
        alert = {
            'severity': 'WARNING',
            'message': f'💧 Humidity {humidity}% exceeds {thresholds["humidity_warning"]}% threshold',
            'sensor': 'Humidity',
            'action': 'Activate dehumidifier or improve ventilation'
        }
        alerts_generated.append(alert)
        insert_alert(room, **alert)

    # Sound check
    if sound and sound > thresholds['sound_warning']:
        alert = {
            'severity': 'WARNING',
            'message': f'🔊 Sound level {sound} dB exceeds {thresholds["sound_warning"]} dB threshold',
            'sensor': 'Sound',
            'action': 'Request noise reduction or switch to quieter activity'
        }
        alerts_generated.append(alert)
        insert_alert(room, **alert)

    # Sustained low engagement
    if engagement and engagement < thresholds['engagement_low']:
        streaks['low_eng'] += 1
        if streaks['low_eng'] >= 3:
            alert = {
                'severity': 'CRITICAL',
                'message': f'📉 Sustained low engagement ({engagement}) for {streaks["low_eng"]} consecutive readings',
                'sensor': 'Engagement',
                'action': 'Consider interactive activity, quiz, group discussion, or short break'
            }
            alerts_generated.append(alert)
            insert_alert(room, **alert)
    else:
        streaks['low_eng'] = 0

    # Low motion
    if motion is not None and motion < 20:
        streaks['low_motion'] += 1
        if streaks['low_motion'] >= 5:
            alert = {
                'severity': 'INFO',
                'message': f'🚶 Low student activity for {streaks["low_motion"]} consecutive readings',
                'sensor': 'Motion',
                'action': 'Students may need a movement break or change of activity'
            }
            alerts_generated.append(alert)
            insert_alert(room, **alert)
    else:
        streaks['low_motion'] = 0

    alert_streaks[room] = streaks

    # Emit alerts to dashboard and push to ThingWorx
    for alert in alerts_generated:
        alert['room'] = room
        alert['time'] = datetime.now().strftime('%H:%M:%S')
        socketio.emit('new_alert', alert)
        
        # Push alert to ThingWorx Service
        # threading.Thread(target=thingworx_api.push_alert_to_thingworx, args=(alert,), daemon=True).start()


# ═══ REST API ENDPOINTS ═══

@app.route('/api/live', methods=['GET'])
def api_live():
    """Get the absolute latest real-time reading for HTTP Polling REST API."""
    room = request.args.get('room', 'Room A101')
    readings = get_readings(room, limit=1)
    if readings:
        return jsonify({'status': 'ok', 'reading': readings[0]})
    return jsonify({'status': 'error', 'message': 'No data available'})

@app.route('/api/readings', methods=['GET'])
def api_readings():
    """Get sensor readings for a room."""
    room = request.args.get('room', 'Room A101')
    limit = int(request.args.get('limit', 100))
    readings = get_readings(room, limit)
    return jsonify(readings)


@app.route('/api/readings/range', methods=['GET'])
def api_readings_range():
    """Get readings within a date range."""
    room = request.args.get('room', 'Room A101')
    start = request.args.get('start')
    end = request.args.get('end', datetime.now().isoformat())
    if not start:
        start = (datetime.now() - timedelta(days=7)).isoformat()
    readings = get_readings_range(room, start, end)
    return jsonify(readings)


@app.route('/api/daily-averages', methods=['GET'])
def api_daily_averages():
    """Get daily average metrics."""
    room = request.args.get('room', 'Room A101')
    days = int(request.args.get('days', 7))
    averages = get_daily_averages(room, days)
    return jsonify(averages)


@app.route('/api/alerts', methods=['GET'])
def api_alerts():
    """Get alert history."""
    room = request.args.get('room')
    limit = int(request.args.get('limit', 50))
    alerts = get_alerts(room, limit)
    return jsonify(alerts)


@app.route('/api/alert-stats', methods=['GET'])
def api_alert_stats():
    """Get alert statistics."""
    room = request.args.get('room')
    stats = get_alert_stats(room)
    return jsonify(stats)


@app.route('/api/sessions', methods=['GET'])
def api_sessions():
    """Get session history."""
    room = request.args.get('room')
    limit = int(request.args.get('limit', 20))
    sessions = get_sessions(room, limit)
    return jsonify(sessions)


@app.route('/api/insights', methods=['GET'])
def api_insights():
    """Get AI-generated engagement insights."""
    room = request.args.get('room', 'Room A101')
    limit = int(request.args.get('limit', 50))
    readings = get_readings(room, limit)
    insights = get_engagement_insights(readings)
    return jsonify({'insights': insights})


@app.route('/api/devices', methods=['GET'])
def api_devices():
    """Get connected ESP32 devices."""
    return jsonify(connected_devices)


@app.route('/api/thresholds', methods=['GET'])
def api_get_thresholds():
    """Get thresholds for a room."""
    room = request.args.get('room', 'Room A101')
    thresholds = get_thresholds(room)
    return jsonify(thresholds or {})


@app.route('/api/thresholds', methods=['POST'])
def api_set_thresholds():
    """Update thresholds for a room."""
    data = request.get_json()
    room = data.get('room', 'Room A101')
    update_thresholds(room, data)
    return jsonify({'status': 'ok'})


@app.route('/api/export', methods=['GET'])
def api_export():
    """Export all data as JSON."""
    room = request.args.get('room', 'Room A101')
    export_data = {
        'export_date': datetime.now().isoformat(),
        'room': room,
        'readings': get_readings(room, 1000),
        'alerts': get_alerts(room, 200),
        'sessions': get_sessions(room, 50),
    }
    return jsonify(export_data)


@app.route('/api/seed-demo', methods=['POST'])
def api_seed_demo():
    """
    Inject 7 days of realistic demo data into the database.
    Call once before a presentation: POST /api/seed-demo
    Simulates a full week of classroom activity with natural patterns.
    """
    import random as rnd
    room = request.args.get('room', 'Room A101')
    now = datetime.now()

    # Realistic classroom scenarios that cycle through the day
    scenarios = [
        # (name, temp, humidity, motion_pct, sound_db, air_q, engagement, pir1,pir2,pir3)
        ("morning_warmup",   24.5, 52, 60,  55, 120, 62,  1, 1, 0),
        ("active_lecture",   25.8, 55, 85,  68, 180, 82,  1, 1, 1),
        ("peak_engagement",  26.0, 57, 92,  72, 200, 91,  1, 1, 1),
        ("group_discussion", 26.5, 58, 78,  76, 210, 75,  1, 1, 1),
        ("post_lunch_dip",   27.1, 60, 45,  50, 150, 48,  1, 0, 1),
        ("recovery",         26.8, 59, 65,  60, 170, 66,  1, 1, 0),
        ("quiet_study",      25.5, 54, 35,  42, 100, 55,  0, 1, 0),
        ("end_of_class",     26.2, 56, 80,  70, 190, 73,  1, 1, 1),
    ]

    count = 0
    for day_offset in range(7, 0, -1):
        base_time = now - timedelta(days=day_offset)
        # Generate readings every 3 minutes across an 8-hour class day
        for minute in range(0, 480, 3):
            ts = base_time + timedelta(minutes=minute)
            sc = scenarios[minute % len(scenarios)]
            # Add realistic noise
            reading = {
                'room': room,
                'esp_id': 'ESP32-DEMO',
                'timestamp': ts.isoformat(),
                'temperature': round(sc[1] + rnd.uniform(-0.8, 0.8), 1),
                'humidity': round(sc[2] + rnd.uniform(-3, 3), 1),
                'motion_pct': round(sc[3] + rnd.uniform(-10, 10), 1),
                'sound_level': round(sc[4] + rnd.uniform(-5, 5), 1),
                'air_quality': round(sc[5] + rnd.uniform(-15, 15)),
                'engagement_score': round(max(10, min(99, sc[7*1] + rnd.uniform(-8, 8))), 1),
                'engagement_level': sc[8] if sc[7] > 70 else ('MEDIUM' if sc[7] > 45 else 'LOW'),
                'pir1': sc[7], 'pir2': sc[8], 'pir3': sc[7],
                'ldr_value': rnd.randint(400, 800),
                'sound_raw': rnd.randint(1800, 2800),
                'source': 'demo'
            }
            # Fix engagement_level using score
            score = reading['engagement_score']
            reading['engagement_level'] = 'HIGH' if score >= 80 else ('MEDIUM' if score >= 50 else 'LOW')
            try:
                insert_reading(reading)
                count += 1
            except:
                pass

    print(f"[DEMO] Seeded {count} demo readings for {room}")
    return jsonify({
        'status': 'ok',
        'message': f'Seeded {count} demo readings for {room} across 7 days',
        'room': room
    })


@app.route('/api/health', methods=['GET'])
def api_health():
    """Health check endpoint for ESP32 to verify server is running."""
    return jsonify({
        'status': 'ok',
        'server': 'SmartClassroom-API',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat(),
        'connected_devices': len(connected_devices)
    })


# ═══ WEBSOCKET EVENTS ═══


@socketio.on('start_demo_stream')
def handle_demo_stream(data):
    """
    When dashboard emits 'start_demo_stream', begin auto-firing
    realistic sensor readings every 4 seconds — no hardware needed.
    Perfect for live presentations.
    """
    import random as rnd
    room = data.get('room', 'Room A101')

    scenarios = [
        dict(temperature=24.5, humidity=52, pir1=1, pir2=1, pir3=0, sound_level=55, air_quality=120, engagement=62, level='MEDIUM', motion=66),
        dict(temperature=25.8, humidity=55, pir1=1, pir2=1, pir3=1, sound_level=68, air_quality=180, engagement=82, level='HIGH',   motion=99),
        dict(temperature=26.0, humidity=57, pir1=1, pir2=1, pir3=1, sound_level=72, air_quality=200, engagement=91, level='HIGH',   motion=99),
        dict(temperature=26.5, humidity=58, pir1=1, pir2=1, pir3=1, sound_level=76, air_quality=210, engagement=75, level='HIGH',   motion=99),
        dict(temperature=27.1, humidity=60, pir1=1, pir2=0, pir3=1, sound_level=50, air_quality=150, engagement=48, level='LOW',    motion=66),
        dict(temperature=26.8, humidity=59, pir1=1, pir2=1, pir3=0, sound_level=60, air_quality=170, engagement=66, level='MEDIUM', motion=66),
        dict(temperature=25.5, humidity=54, pir1=0, pir2=1, pir3=0, sound_level=42, air_quality=100, engagement=55, level='MEDIUM', motion=33),
        dict(temperature=26.2, humidity=56, pir1=1, pir2=1, pir3=1, sound_level=70, air_quality=190, engagement=73, level='HIGH',   motion=99),
    ]

    def stream_loop():
        step = 0
        while True:
            sc = scenarios[step % len(scenarios)]
            payload = {
                'timestamp': datetime.now().isoformat(),
                'room': room,
                'esp_id': 'ESP32-DEMO',
                'temperature': round(sc['temperature'] + rnd.uniform(-0.5, 0.5), 1),
                'humidity':    round(sc['humidity']    + rnd.uniform(-2, 2), 1),
                'pir1': sc['pir1'], 'pir2': sc['pir2'], 'pir3': sc['pir3'],
                'sound_level': round(sc['sound_level'] + rnd.uniform(-4, 4), 1),
                'air_quality': round(sc['air_quality'] + rnd.uniform(-10, 10)),
                'motion':      sc['motion'],
                'engagement':  round(max(10, min(99, sc['engagement'] + rnd.uniform(-6, 6))), 1),
                'level':       sc['level'],
                'ldr_value':   rnd.randint(400, 800),
                'method':      'demo',
                'source':      'demo_stream'
            }
            try:
                insert_reading({
                    **payload,
                    'engagement_score': payload['engagement'],
                    'engagement_level': payload['level'],
                    'motion_pct':       payload['motion'],
                })
            except:
                pass
            socketio.emit('new_reading', payload)
            step += 1
            time.sleep(4)

    threading.Thread(target=stream_loop, daemon=True).start()
    emit('demo_stream_started', {'status': 'ok', 'room': room, 'interval': 4})
    print(f"[DEMO STREAM] Live demo started for {room}")


@socketio.on('connect')
def handle_connect():
    """Handle WebSocket client connection."""
    print(f"[WS] Dashboard client connected: {request.sid}")
    emit('connection_status', {
        'status': 'connected',
        'server_time': datetime.now().isoformat(),
        'connected_devices': connected_devices
    })


@socketio.on('disconnect')
def handle_disconnect():
    print(f"[WS] Dashboard client disconnected: {request.sid}")


@socketio.on('request_readings')
def handle_request_readings(data):
    """Handle frontend request for historical readings."""
    room = data.get('room', 'Room A101')
    limit = data.get('limit', 20)
    readings = get_readings(room, limit)
    emit('readings_response', {'room': room, 'readings': readings})


# ═══ RUN SERVER ═══

if __name__ == '__main__':
    print("\n[SERVER] Starting locally on http://0.0.0.0:5000")
    print("[SERVER] Press Ctrl+C to stop\n")
    socketio.run(
        app,
        host='0.0.0.0',
        port=5000,
        debug=False,
        allow_unsafe_werkzeug=True
    )
