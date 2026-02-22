# 🚌 AI-Powered Smart Public Transport Optimization System for Chennai

An intelligent transport routing application that uses machine learning to provide optimal bus route recommendations for Chennai Metropolitan Transport Corporation (MTC).

## 🎯 Features

- **Smart Route Finding**: Find direct routes between any two stops
- **ML-Powered Predictions**: AI-based travel time and delay predictions
- **Real-time Traffic Consideration**: Adjusts estimates based on time of day
- **Interactive Maps**: Google Maps integration for route visualization
- **Multiple Route Options**: Direct, shortest, and fastest route suggestions
- **Scalable Architecture**: Designed to expand across Tamil Nadu

## 📁 Project Structure

```
chennai_mtc_project/
├── backend/
│   ├── app.py                 # FastAPI application
│   ├── requirements.txt       # Python dependencies
│   ├── core/
│   │   ├── __init__.py
│   │   ├── data_loader.py     # CSV data loading & graph building
│   │   ├── route_engine.py    # Route finding algorithms
│   │   └── ml_engine.py       # ML prediction models
│   └── models/                # Saved ML models
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.js             # Main application
│   │   ├── index.js           # Entry point
│   │   ├── index.css          # Tailwind CSS
│   │   ├── components/
│   │   │   ├── Header.js
│   │   │   ├── SearchPanel.js
│   │   │   ├── RouteResults.js
│   │   │   ├── MapView.js
│   │   │   └── StatsPanel.js
│   │   └── services/
│   │       └── api.js         # API service
│   ├── package.json
│   ├── tailwind.config.js
│   └── postcss.config.js
├── route_stop_ordered.csv     # Route-stops mapping
├── route_edges.csv            # Route edges/distances
└── README.md
```

## 🚀 Getting Started

### Prerequisites

- Python 3.9+
- Node.js 18+

### Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

The API will be available at `http://localhost:8000`

### Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create .env file (optional - no API key required!)
cp .env.example .env

# Start development server
npm start
```

The app will be available at `http://localhost:3000`

> **Note:** This app uses OpenStreetMap + Leaflet for maps, which is completely free and requires no API key!

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/search-route` | POST | Search routes between source and destination |
| `/predict-time` | POST | Predict travel time using ML model |
| `/get-stops` | GET | Get all stops or search by name |
| `/get-stop-suggestions` | GET | Autocomplete suggestions for stops |
| `/get-route-map/{route_number}` | GET | Get route coordinates for map |
| `/get-route-between-stops/{route_number}` | GET | Get segment between two stops |
| `/stats` | GET | Get system statistics |
| `/health` | GET | Health check endpoint |

## 🤖 ML Model

The system uses a **RandomForestRegressor** trained on simulated traffic data with features:

- Number of stops
- Total distance (km)
- Time of day
- Peak hour flag
- Route length
- Average stop density

**Output:**
- Predicted travel time (minutes)
- Delay probability (0-1)

## 🗺️ Data Sources

1. **route_stop_ordered.csv**: Ordered stops for each route
2. **route_edges.csv**: Distance between consecutive stops

## 🔧 Configuration

### Environment Variables

**Backend (.env):**
```
HOST=0.0.0.0
PORT=8000
DATA_PATH=/path/to/data
```

**Frontend (.env):**
```
REACT_APP_API_URL=http://localhost:8000
# No API key required for maps - using OpenStreetMap!
```

## 📈 Route Ranking Logic

Routes are ranked by:
1. **Direct routes** (highest priority)
2. **Fastest routes** (ML-predicted time)
3. **Least stops** (fewer intermediate stops)
4. **Shortest distance**

## 🚧 Future Enhancements

- [ ] Live GPS bus tracking
- [ ] Real MTC API integration
- [ ] Multi-transfer route suggestions
- [ ] Passenger load prediction
- [ ] Tamil Nadu state-wide expansion
- [ ] Mobile app (React Native)
- [ ] Voice-based route search
- [ ] Emergency routing (hospitals)
- [ ] Accessibility mode

## 📊 Tech Stack

**Backend:**
- FastAPI
- Pandas
- Scikit-learn
- XGBoost

**Frontend:**
- React.js
- Tailwind CSS
- OpenStreetMap + Leaflet (free, no API key!)
- Axios

## 📝 License

This project is developed for Chennai MTC Smart Transport initiative.

## 👥 Contributors

Built with ❤️ for Chennai

## 🗺️ Map Provider

This project uses **OpenStreetMap** with **Leaflet** for map visualization:
- ✅ Completely free - no API key required
- ✅ Open source
- ✅ High-quality map data
- ✅ Multiple tile layer options available

Available tile layers (can be changed in MapView.js):
- OpenStreetMap (default)
- CartoDB Positron (light theme)
- CartoDB Dark Matter (dark theme)

---
