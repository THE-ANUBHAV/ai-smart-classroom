"""
═══════════════════════════════════════════════════════════════
  DATABASE MANAGER — SQLite for Smart Classroom IoT System
  Team-8 | GLA University | B.Tech CSE (AI-ML)
═══════════════════════════════════════════════════════════════
"""

import sqlite3
import os
import json
from datetime import datetime, timedelta
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smartclassroom.db')


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize database tables."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS classrooms (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                room_number TEXT,
                capacity INTEGER DEFAULT 60,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sensor_readings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                room TEXT NOT NULL,
                esp_id TEXT DEFAULT 'ESP32-01',
                temperature REAL,
                humidity REAL,
                pir1 INTEGER DEFAULT 0,
                pir2 INTEGER DEFAULT 0,
                pir3 INTEGER DEFAULT 0,
                sound_level REAL,
                sound_raw INTEGER,
                air_quality REAL,
                ldr_value REAL,
                motion_pct REAL,
                engagement_score REAL,
                engagement_level TEXT,
                source TEXT DEFAULT 'hardware'
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                room TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT NOT NULL,
                sensor TEXT,
                action TEXT,
                resolved INTEGER DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room TEXT NOT NULL,
                start_time TIMESTAMP NOT NULL,
                end_time TIMESTAMP,
                avg_engagement REAL,
                total_readings INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active'
            );

            CREATE TABLE IF NOT EXISTS thresholds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                room TEXT NOT NULL,
                temp_warning REAL DEFAULT 28.0,
                temp_critical REAL DEFAULT 32.0,
                humidity_warning REAL DEFAULT 70.0,
                humidity_critical REAL DEFAULT 85.0,
                sound_warning REAL DEFAULT 85.0,
                sound_critical REAL DEFAULT 95.0,
                engagement_low REAL DEFAULT 40.0,
                engagement_critical REAL DEFAULT 25.0,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_readings_room_time
                ON sensor_readings(room, timestamp);
            CREATE INDEX IF NOT EXISTS idx_alerts_room_time
                ON alerts(room, timestamp);
            CREATE INDEX IF NOT EXISTS idx_sessions_room
                ON sessions(room, status);
        """)

        # Seed default classrooms
        default_rooms = [
            ('Room A101', 'A101', 60),
            ('Room B205', 'B205', 80),
            ('Room C310', 'C310', 40),
        ]
        for name, number, cap in default_rooms:
            conn.execute(
                "INSERT OR IGNORE INTO classrooms (name, room_number, capacity) VALUES (?, ?, ?)",
                (name, number, cap)
            )
            conn.execute(
                "INSERT OR IGNORE INTO thresholds (room) VALUES (?)",
                (name,)
            )
    print("[DB] Database initialized successfully")


# ═══ SENSOR READINGS ═══

def insert_reading(data):
    """Insert a new sensor reading."""
    with get_db() as conn:
        conn.execute("""
            INSERT INTO sensor_readings
            (timestamp, room, esp_id, temperature, humidity, pir1, pir2, pir3,
             sound_level, sound_raw, air_quality, ldr_value, motion_pct,
             engagement_score, engagement_level, source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            data.get('timestamp', datetime.now().isoformat()),
            data.get('room', 'Room A101'),
            data.get('esp_id', 'ESP32-01'),
            data.get('temperature'),
            data.get('humidity'),
            data.get('pir1', 0),
            data.get('pir2', 0),
            data.get('pir3', 0),
            data.get('sound_level'),
            data.get('sound_raw'),
            data.get('air_quality'),
            data.get('ldr_value'),
            data.get('motion_pct'),
            data.get('engagement_score'),
            data.get('engagement_level'),
            data.get('source', 'hardware'),
        ))


def get_readings(room, limit=100):
    """Get recent readings for a room."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM sensor_readings WHERE room = ? ORDER BY timestamp DESC LIMIT ?",
            (room, limit)
        ).fetchall()
        return [dict(r) for r in rows]


def get_readings_range(room, start_time, end_time):
    """Get readings within a time range."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM sensor_readings WHERE room = ? AND timestamp BETWEEN ? AND ? ORDER BY timestamp ASC",
            (room, start_time, end_time)
        ).fetchall()
        return [dict(r) for r in rows]


def get_daily_averages(room, days=7):
    """Get daily average engagement for a room."""
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    with get_db() as conn:
        rows = conn.execute("""
            SELECT DATE(timestamp) as date,
                   AVG(engagement_score) as avg_engagement,
                   AVG(temperature) as avg_temp,
                   AVG(humidity) as avg_humidity,
                   AVG(sound_level) as avg_sound,
                   COUNT(*) as reading_count
            FROM sensor_readings
            WHERE room = ? AND timestamp > ?
            GROUP BY DATE(timestamp)
            ORDER BY date ASC
        """, (room, cutoff)).fetchall()
        return [dict(r) for r in rows]


# ═══ ALERTS ═══

def insert_alert(room, severity, message, sensor=None, action=None):
    """Insert a new alert."""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO alerts (room, severity, message, sensor, action) VALUES (?, ?, ?, ?, ?)",
            (room, severity, message, sensor, action)
        )


def get_alerts(room=None, limit=50):
    """Get recent alerts."""
    with get_db() as conn:
        if room:
            rows = conn.execute(
                "SELECT * FROM alerts WHERE room = ? ORDER BY timestamp DESC LIMIT ?",
                (room, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM alerts ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


def get_alert_stats(room=None):
    """Get alert statistics for today."""
    today = datetime.now().strftime('%Y-%m-%d')
    with get_db() as conn:
        query_base = "FROM alerts WHERE DATE(timestamp) = ?"
        params = [today]
        if room:
            query_base += " AND room = ?"
            params.append(room)

        total = conn.execute(f"SELECT COUNT(*) {query_base}", params).fetchone()[0]
        critical = conn.execute(
            f"SELECT COUNT(*) {query_base} AND severity = 'CRITICAL'", params
        ).fetchone()[0]

        most_freq = conn.execute(f"""
            SELECT sensor, COUNT(*) as cnt {query_base}
            GROUP BY sensor ORDER BY cnt DESC LIMIT 1
        """, params).fetchone()

        return {
            'total_today': total,
            'critical_count': critical,
            'most_frequent': most_freq['sensor'] if most_freq else '--',
        }


# ═══ SESSIONS ═══

def start_session(room):
    """Start a new session."""
    with get_db() as conn:
        # Close any existing active sessions for this room
        conn.execute(
            "UPDATE sessions SET status = 'ended', end_time = CURRENT_TIMESTAMP WHERE room = ? AND status = 'active'",
            (room,)
        )
        cursor = conn.execute(
            "INSERT INTO sessions (room, start_time) VALUES (?, ?)",
            (room, datetime.now().isoformat())
        )
        return cursor.lastrowid


def end_session(session_id):
    """End a session and compute averages."""
    with get_db() as conn:
        session = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if not session:
            return

        readings = conn.execute("""
            SELECT AVG(engagement_score) as avg_eng, COUNT(*) as total
            FROM sensor_readings
            WHERE room = ? AND timestamp BETWEEN ? AND CURRENT_TIMESTAMP
        """, (session['room'], session['start_time'])).fetchone()

        conn.execute("""
            UPDATE sessions SET end_time = CURRENT_TIMESTAMP, status = 'ended',
            avg_engagement = ?, total_readings = ?
            WHERE id = ?
        """, (readings['avg_eng'], readings['total'], session_id))


def get_sessions(room=None, limit=20):
    """Get session history."""
    with get_db() as conn:
        if room:
            rows = conn.execute(
                "SELECT * FROM sessions WHERE room = ? ORDER BY start_time DESC LIMIT ?",
                (room, limit)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM sessions ORDER BY start_time DESC LIMIT ?",
                (limit,)
            ).fetchall()
        return [dict(r) for r in rows]


# ═══ THRESHOLDS ═══

def get_thresholds(room):
    """Get thresholds for a room."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM thresholds WHERE room = ?", (room,)).fetchone()
        return dict(row) if row else None


def update_thresholds(room, data):
    """Update thresholds for a room."""
    with get_db() as conn:
        conn.execute("""
            UPDATE thresholds SET
            temp_warning = ?, humidity_warning = ?,
            sound_warning = ?, engagement_low = ?,
            updated_at = CURRENT_TIMESTAMP
            WHERE room = ?
        """, (
            data.get('temp_warning', 28),
            data.get('humidity_warning', 70),
            data.get('sound_warning', 85),
            data.get('engagement_low', 40),
            room,
        ))


if __name__ == '__main__':
    init_db()
    print("[DB] Database setup complete. File:", DB_PATH)
