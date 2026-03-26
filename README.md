# AI‑Powered Smart Classroom Engagement Learning Analytics System

An IoT + AI system that monitors classroom environment and activity using low‑cost sensors, then applies machine learning to estimate **engagement levels (High / Medium / Low)** and visualize them on an interactive dashboard for teachers and coordinators.

---

## 🚀 Features

- Real‑time collection of temperature, humidity, motion, and noise data using ESP32 and classroom sensors.
- Engagement analytics using machine learning models (e.g., Random Forest, XGBoost) on aggregated sensor data.  
- Web-based dashboard for teachers with live charts, historical trends, and engagement summaries per lecture and classroom.
- Role-based access (teacher, admin) with secure login and controlled views. 
- Privacy-friendly design: no individual student identification or video recording; only aggregated classroom-level metrics.

---

## 🧩 System Architecture

The system is organized into five layers:

1. **IoT Data Collection Layer** – ESP32 board with PIR motion, sound, and DHT11/DHT22 sensors deployed in the classroom.  
2. **Data Transmission Layer** – Wi‑Fi connectivity using HTTP or MQTT to send timestamped readings to the server. 
3. **Data Storage Layer** – Database (PostgreSQL / MongoDB) storing raw sensor readings, sessions, and derived metrics.
4. **AI Analytics Layer** – Python services for feature extraction, model training, engagement classification, and clustering.
5. **Presentation Layer** – Web dashboard (e.g., React / Streamlit / Flask templates) for visualization and reporting.

---

## 🛠️ Hardware & Software Stack

**Hardware**
- ESP32 development board (x1–2)  
- DHT11/DHT22 temperature & humidity sensors  
- PIR motion sensors (HC‑SR501)  
- Sound sensor modules (KY‑037/KY‑038)  
- Breadboard, jumper wires, resistors, 5V power source / power bank  

**Software** 
- Firmware: Arduino IDE / ESP-IDF (C/C++) for ESP32  
- Backend: Python (Flask / FastAPI), REST or MQTT ingestion APIs  
- Database: PostgreSQL or MongoDB  
- ML: Python, NumPy, Pandas, Scikit‑learn, possibly XGBoost  
- Dashboard: React / Streamlit / HTML+CSS+JS with Chart.js / Plotly  

---

## 📂 Project Structure (Example)

```bash
ai-smart-classroom/
├─ firmware/
│  └─ esp32_sensors.ino
├─ backend/
│  ├─ app.py
│  ├─ models/
│  ├─ routes/
│  └─ requirements.txt
├─ ml/
│  ├─ feature_engineering.py
│  ├─ train_model.ipynb
│  └─ models/
├─ dashboard/
│  ├─ src/
│  └─ package.json
├─ data/
│  ├─ raw/
│  └─ processed/
├─ docs/
│  ├─ synopsis.pdf
│  └─ architecture.png
└─ README.md
```

---

## ⚙️ Setup & Installation

1. **Clone the repository**

```bash
git clone https://github.com/<your-username>/ai-smart-classroom.git
cd ai-smart-classroom
```

2. **Backend & ML environment**

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. **Configure environment**

Create a `.env` file in `backend/` with values like:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/classroom_db
SECRET_KEY=your-secret-key
MQTT_BROKER_URL=...
```

4. **Run backend server**

```bash
uvicorn app:app --reload  # if using FastAPI
# or
python app.py             # if using Flask
```

5. **Run dashboard (if React)**

```bash
cd ../dashboard
npm install
npm start
```

6. **Flash ESP32 firmware**

- Open `firmware/esp32_sensors.ino` in Arduino IDE.  
- Set Wi‑Fi SSID, password, and backend/MQTT URL.  
- Upload to ESP32 and open Serial Monitor to confirm sensor data transmission.[web:55][web:58]

---

## 📊 How It Works

1. ESP32 reads sensor values every 5–10 seconds and sends them to the backend with timestamps and classroom ID. 
2. Backend stores readings, aggregates them into time windows, and computes features (mean, variance, deltas, etc.). 
3. Trained ML models classify engagement levels (High/Medium/Low) for each window and save the results in the database.  
4. Dashboard fetches metrics via APIs and displays live gauges, time‑series charts, and daily/weekly summaries for teachers and admins.

---

## ✅ Use Cases

- Teachers monitor engagement during a lecture and quickly see when attention drops.  
- Coordinators compare engagement across classrooms or periods and correlate with temperature/noise conditions.  
- Departments gather evidence for pedagogical changes and infrastructure improvements based on real data.

---

## 🔒 Privacy & Ethical Considerations

- No storage of personally identifiable student data, faces, or raw audio—only aggregated sensor readings.
- Engagement analytics are at classroom level, not per individual.  
- Pilot deployments should be conducted with informed consent from faculty and students and approval from the department.

---

## 📖 Documentation

- `docs/synopsis.pdf` – Project synopsis and detailed design document.  
- `docs/report.pdf` – Full project report (architecture, implementation, results).  
- `docs/user-manual.pdf` – Instructions for teachers and admins to use the dashboard.

---

## 👨‍💻 Team

- **Anubhav Singh** – Team Leader / Tech Lead & AI‑ML Engineer (overall architecture, IoT–backend–ML integration, model design, and final delivery).
- **Bhartendu Ji** – IoT & Backend Developer (ESP32 hardware, sensor integration, firmware, ingestion APIs, and database pipeline).
- **Stuti Mittal** – Frontend, QA & Documentation Lead (dashboard UI/UX, testing, documentation, and presentation material).
