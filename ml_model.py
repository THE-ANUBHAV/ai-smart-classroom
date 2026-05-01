"""
═══════════════════════════════════════════════════════════════
  ML ENGINE — Engagement Prediction for Smart Classroom
  Team-8 | GLA University | B.Tech CSE (AI-ML)
  
  Uses Random Forest + weighted formula hybrid approach.
  Auto-trains on collected data, falls back to formula when
  insufficient training data is available.
═══════════════════════════════════════════════════════════════
"""

import numpy as np
import os
import json
from datetime import datetime

try:
    from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    import joblib
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    print("[ML] scikit-learn not installed. Using formula-only mode.")

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ml_models')
SCORE_MODEL_PATH = os.path.join(MODEL_DIR, 'engagement_score_model.pkl')
LEVEL_MODEL_PATH = os.path.join(MODEL_DIR, 'engagement_level_model.pkl')
SCALER_PATH = os.path.join(MODEL_DIR, 'scaler.pkl')

# ═══ WEIGHTED FORMULA (FALLBACK) ═══

def compute_engagement_formula(data, session_minutes=0):
    """
    Compute engagement score using weighted sensor formula.
    This is the primary method and also serves as fallback when ML model
    has insufficient training data.
    
    Weights: motion=0.40, sound=0.25, temperature=0.20, time=0.15
    """
    # Motion score: average of 3 PIR sensors × 100
    pir1 = 1 if data.get('pir1') else 0
    pir2 = 1 if data.get('pir2') else 0
    pir3 = 1 if data.get('pir3') else 0
    motion_avg = ((pir1 + pir2 + pir3) / 3) * 100

    # Sound score: optimal at 55-65 dB (conversation level)
    sound = data.get('sound_level', 55) or 55
    sound_score = max(0, min(100, 100 - abs(sound - 60) * 2))

    # Temperature score: optimal at 22-24°C
    temp = data.get('temperature', 23) or 23
    temp_score = max(0, min(100, 100 - abs(temp - 23) * 8))

    # Humidity penalty: optimal 40-60%, penalize outside range
    humidity = data.get('humidity', 50) or 50
    if 40 <= humidity <= 60:
        humidity_bonus = 5
    elif humidity > 70 or humidity < 30:
        humidity_bonus = -10
    else:
        humidity_bonus = 0

    # Time decay: engagement naturally drops after 20 minutes
    if session_minutes > 20:
        time_factor = max(40, 100 - (session_minutes - 20) * 1.5)
    else:
        time_factor = 100

    # Weighted engagement score
    score = (
        0.40 * motion_avg +
        0.25 * sound_score +
        0.20 * temp_score +
        0.15 * time_factor +
        humidity_bonus
    )

    return max(0, min(100, round(score, 1)))


def classify_engagement(score):
    """Classify engagement level from score."""
    if score >= 80:
        return 'HIGH'
    elif score >= 50:
        return 'MEDIUM'
    else:
        return 'LOW'


# ═══ FEATURE EXTRACTION ═══

def extract_features(data):
    """Extract ML feature vector from sensor data."""
    pir1 = 1 if data.get('pir1') else 0
    pir2 = 1 if data.get('pir2') else 0
    pir3 = 1 if data.get('pir3') else 0

    temp = data.get('temperature', 23) or 23
    humidity = data.get('humidity', 50) or 50
    sound = data.get('sound_level', 55) or 55
    air_quality = data.get('air_quality', 80) or 80
    ldr = data.get('ldr_value', 500) or 500

    motion_avg = (pir1 + pir2 + pir3) / 3
    sound_deviation = abs(sound - 60)
    temp_deviation = abs(temp - 23)
    humidity_deviation = abs(humidity - 50)

    return np.array([
        motion_avg,           # 0: average motion (0-1)
        pir1,                 # 1: left zone
        pir2,                 # 2: center zone
        pir3,                 # 3: right zone
        temp,                 # 4: temperature
        temp_deviation,       # 5: temp deviation from optimal
        humidity,             # 6: humidity
        humidity_deviation,   # 7: humidity deviation from optimal
        sound,                # 8: sound level
        sound_deviation,      # 9: sound deviation from optimal
        air_quality,          # 10: air quality
        ldr,                  # 11: light level
    ]).reshape(1, -1)


# ═══ MODEL TRAINING ═══

def generate_training_data(n_samples=2000):
    """
    Generate synthetic training data based on realistic classroom scenarios.
    Used to bootstrap the model before real data is collected.
    """
    np.random.seed(42)
    X = []
    y_score = []
    y_level = []

    for _ in range(n_samples):
        scenario = np.random.choice(['high', 'medium', 'low'], p=[0.3, 0.4, 0.3])

        if scenario == 'high':
            pir1, pir2, pir3 = (np.random.random() < 0.85 for _ in range(3))
            temp = np.random.normal(23, 1)
            humidity = np.random.normal(50, 8)
            sound = np.random.normal(60, 8)
            air_q = np.random.normal(75, 15)
            ldr = np.random.normal(600, 100)
        elif scenario == 'medium':
            pir1, pir2, pir3 = (np.random.random() < 0.5 for _ in range(3))
            temp = np.random.normal(25, 2)
            humidity = np.random.normal(55, 12)
            sound = np.random.normal(55, 15)
            air_q = np.random.normal(90, 20)
            ldr = np.random.normal(500, 150)
        else:
            pir1, pir2, pir3 = (np.random.random() < 0.2 for _ in range(3))
            temp = np.random.normal(28, 3)
            humidity = np.random.normal(65, 15)
            sound = np.random.choice([np.random.normal(35, 5), np.random.normal(85, 8)])
            air_q = np.random.normal(110, 25)
            ldr = np.random.normal(400, 200)

        pir1, pir2, pir3 = int(pir1), int(pir2), int(pir3)
        temp = np.clip(temp, 15, 40)
        humidity = np.clip(humidity, 20, 95)
        sound = np.clip(sound, 25, 100)
        air_q = np.clip(air_q, 30, 200)
        ldr = np.clip(ldr, 50, 1000)

        motion_avg = (pir1 + pir2 + pir3) / 3
        features = [
            motion_avg, pir1, pir2, pir3,
            temp, abs(temp - 23),
            humidity, abs(humidity - 50),
            sound, abs(sound - 60),
            air_q, ldr,
        ]
        X.append(features)

        # Compute engagement using formula
        data = {
            'pir1': pir1, 'pir2': pir2, 'pir3': pir3,
            'temperature': temp, 'humidity': humidity,
            'sound_level': sound, 'air_quality': air_q,
            'ldr_value': ldr,
        }
        score = compute_engagement_formula(data)
        # Add noise to make it more realistic
        score = np.clip(score + np.random.normal(0, 5), 0, 100)
        y_score.append(round(score, 1))
        y_level.append(classify_engagement(score))

    return np.array(X), np.array(y_score), np.array(y_level)


def train_model():
    """Train ML models on synthetic + available real data."""
    if not ML_AVAILABLE:
        print("[ML] scikit-learn not available, skipping model training")
        return False

    os.makedirs(MODEL_DIR, exist_ok=True)

    print("[ML] Generating training data...")
    X, y_score, y_level = generate_training_data(2000)

    # Try to augment with real data from database
    try:
        from database import get_readings
        for room in ['Room A101', 'Room B205', 'Room C310']:
            readings = get_readings(room, limit=500)
            for r in readings:
                if r.get('engagement_score') is not None:
                    features = extract_features(r).flatten()
                    X = np.vstack([X, features])
                    y_score = np.append(y_score, r['engagement_score'])
                    y_level = np.append(y_level, r.get('engagement_level', classify_engagement(r['engagement_score'])))
    except Exception as e:
        print(f"[ML] Could not load real data: {e}")

    print(f"[ML] Training on {len(X)} samples...")

    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Train score regression model
    X_train, X_test, y_train, y_test = train_test_split(
        X_scaled, y_score, test_size=0.2, random_state=42
    )
    score_model = GradientBoostingRegressor(
        n_estimators=100, max_depth=5, random_state=42
    )
    score_model.fit(X_train, y_train)
    train_r2 = score_model.score(X_test, y_test)
    print(f"[ML] Score model R²: {train_r2:.3f}")

    # Train level classifier
    X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
        X_scaled, y_level, test_size=0.2, random_state=42
    )
    level_model = RandomForestClassifier(
        n_estimators=100, max_depth=8, random_state=42
    )
    level_model.fit(X_train_c, y_train_c)
    train_acc = level_model.score(X_test_c, y_test_c)
    print(f"[ML] Level classifier accuracy: {train_acc:.3f}")

    # Save models
    joblib.dump(score_model, SCORE_MODEL_PATH)
    joblib.dump(level_model, LEVEL_MODEL_PATH)
    joblib.dump(scaler, SCALER_PATH)
    print("[ML] Models saved successfully")

    return True


# ═══ PREDICTION ═══

_loaded_models = {}

def load_models():
    """Load trained models into memory."""
    if not ML_AVAILABLE:
        return False
    if not all(os.path.exists(p) for p in [SCORE_MODEL_PATH, LEVEL_MODEL_PATH, SCALER_PATH]):
        print("[ML] Models not found, training now...")
        train_model()

    try:
        _loaded_models['score'] = joblib.load(SCORE_MODEL_PATH)
        _loaded_models['level'] = joblib.load(LEVEL_MODEL_PATH)
        _loaded_models['scaler'] = joblib.load(SCALER_PATH)
        print("[ML] Models loaded successfully")
        return True
    except Exception as e:
        print(f"[ML] Error loading models: {e}")
        return False


def predict_engagement(data, session_minutes=0):
    """
    Predict engagement score and level.
    Uses ML model if available, falls back to weighted formula.
    Returns: {'score': float, 'level': str, 'method': str}
    """
    # Always compute formula score as baseline/fallback
    formula_score = compute_engagement_formula(data, session_minutes)

    # Try ML prediction
    if ML_AVAILABLE and 'score' in _loaded_models:
        try:
            features = extract_features(data)
            features_scaled = _loaded_models['scaler'].transform(features)

            ml_score = float(_loaded_models['score'].predict(features_scaled)[0])
            ml_score = max(0, min(100, round(ml_score, 1)))
            ml_level = _loaded_models['level'].predict(features_scaled)[0]

            # Blend ML and formula (70% ML, 30% formula) for robustness
            blended_score = round(0.7 * ml_score + 0.3 * formula_score, 1)
            blended_level = classify_engagement(blended_score)

            return {
                'score': blended_score,
                'level': blended_level,
                'ml_score': ml_score,
                'formula_score': formula_score,
                'method': 'ml_hybrid'
            }
        except Exception as e:
            print(f"[ML] Prediction error, using formula: {e}")

    return {
        'score': formula_score,
        'level': classify_engagement(formula_score),
        'method': 'formula'
    }


# ═══ ANALYTICS ═══

def get_engagement_insights(readings):
    """Generate AI insights from a list of readings."""
    if not readings:
        return ["No data available for analysis."]

    insights = []
    scores = [r.get('engagement_score', 50) for r in readings if r.get('engagement_score') is not None]
    temps = [r.get('temperature', 23) for r in readings if r.get('temperature') is not None]
    sounds = [r.get('sound_level', 55) for r in readings if r.get('sound_level') is not None]

    if not scores:
        return ["Insufficient data for analysis."]

    avg_score = np.mean(scores)
    avg_temp = np.mean(temps) if temps else 23
    avg_sound = np.mean(sounds) if sounds else 55

    if avg_temp > 26:
        insights.append(f"⚠️ High temperature detected (avg {avg_temp:.1f}°C) — consider HVAC optimization for better comfort")
    elif avg_temp < 20:
        insights.append(f"❄️ Low temperature detected (avg {avg_temp:.1f}°C) — room may be too cold for comfort")

    if len(scores) > 5:
        max_score = max(scores)
        min_score = min(scores)
        max_idx = scores.index(max_score)
        min_idx = scores.index(min_score)
        if max_score - min_score > 40:
            insights.append(f"📉 Large engagement swing detected ({min_score:.0f} → {max_score:.0f}) — consider structured activities")
        if min_idx > len(scores) * 0.6:
            insights.append("📉 Engagement dropped in the latter half — suggest activity break after 20 minutes")

    if sounds and (max(sounds) - min(sounds) > 30):
        insights.append("🔊 High noise variance detected — may indicate alternating discussion and distraction periods")

    if avg_score >= 75:
        insights.append(f"✅ Strong session performance (avg {avg_score:.0f}%) — current teaching method is effective")
    elif avg_score < 45:
        insights.append(f"📉 Low overall engagement (avg {avg_score:.0f}%) — consider interactive teaching strategies")

    if not insights:
        insights.append("✅ Session parameters within normal range")

    return insights


if __name__ == '__main__':
    print("Training engagement prediction model...")
    train_model()
    print("\nTesting prediction:")
    test_data = {
        'pir1': True, 'pir2': True, 'pir3': False,
        'temperature': 24.5, 'humidity': 55,
        'sound_level': 58, 'air_quality': 85, 'ldr_value': 600
    }
    result = predict_engagement(test_data)
    print(f"  Score: {result['score']}, Level: {result['level']}, Method: {result['method']}")
