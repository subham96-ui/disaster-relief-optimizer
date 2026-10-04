# 🚨 AEGIS RELIEF — Disaster Relief Logistics Optimizer

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/Flask-2.x-000000?style=for-the-badge&logo=flask&logoColor=white"/>
  <img src="https://img.shields.io/badge/OpenStreetMap-GIS-7EBC6F?style=for-the-badge&logo=openstreetmap&logoColor=white"/>
  <img src="https://img.shields.io/badge/OR--Tools-Optimization-4285F4?style=for-the-badge&logo=google&logoColor=white"/>
</p>

> **AI-powered multi-modal disaster logistics optimizer** — routing relief supplies across road networks and drone flight paths with real-time GIS visualization.

---

## 🌍 Live Demo

[![Deploy on Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🗺️ **Interactive GIS Map** | Real-time Leaflet.js map with depot, zone, and route overlays |
| 🚛 **Truck Routing** | OSMnx road network routing with hazard-aware path planning |
| 🛸 **Drone Dispatch** | Great-circle air vector optimization for direct deliveries |
| ⚡ **AI Optimization** | Google OR-Tools VRP solver for optimal fleet allocation |
| 🌊 **Hazard Avoidance** | Flood zone detection and route re-scoring |
| 📊 **Live Dashboard** | Mission stats, ETA, and supply coverage analytics |

---

## 🚀 Run Locally

### Prerequisites
- Python 3.10+
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/subham96-ui/disaster-relief-optimizer.git
cd disaster-relief-optimizer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Start the server
python app.py

# 4. Open your browser
http://localhost:5000
```

---

## ☁️ Deploy on Render (Free — Live Public URL)

Get a shareable public URL in under 2 minutes:

1. Go to **[render.com](https://render.com)** → Sign up with GitHub
2. Click **"New +"** → **"Web Service"**
3. Connect your repo: `subham96-ui/disaster-relief-optimizer`
4. Set the following:
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python app.py`
5. Click **Deploy** ✅

Your site will be live at: `https://disaster-relief-optimizer-2im2.onrender.com/`

---

## 🗂️ Project Structure

```
disaster-relief-optimizer/
├── app.py                  # Flask application entry point
├── config.py               # Mission parameters & configuration
├── optimizer.py            # OR-Tools VRP optimization engine
├── routing_engine.py       # OSMnx road network + drone routing
├── requirements.txt        # Python dependencies
├── static/
│   ├── index.html          # Main GIS dashboard UI
│   ├── app.js              # Frontend logic & map interactions
│   └── style.css           # UI styles
└── templates/              # Flask HTML templates
```

---

## 🧠 How It Works

```
Mission Parameters → Routing Engine → OR-Tools Optimizer → GIS Dashboard
       ↓                   ↓                  ↓                 ↓
  Depots & Zones    Road + Air Graphs    VRP Solution      Live Map View
```

1. **Routing Engine** builds a road network graph (OSMnx) and computes drone air vectors
2. **Hazard scoring** penalizes routes passing through flood/danger zones
3. **OR-Tools VRP** finds the globally optimal dispatch plan across all vehicles
4. **GIS Dashboard** renders routes, ETAs, and supply coverage in real time

---

## 🛠️ Tech Stack

- **Backend:** Python, Flask, OSMnx, NetworkX, geopy
- **Optimization:** Google OR-Tools (Vehicle Routing Problem)
- **Frontend:** Leaflet.js, Vanilla JS, CSS3
- **GIS Data:** OpenStreetMap (via OSMnx)

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

<p align="center">Built with ❤️ for disaster relief communities worldwide</p>
