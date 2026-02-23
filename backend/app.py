"""
AI-Powered Smart Public Transport Optimization System for Chennai
Main FastAPI Application
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
import uvicorn
import pandas as pd
import os
import sys

# Add current and parent directory to sys.path to ensure local modules are found
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
sys.path.append(os.path.dirname(current_dir))

from core.data_loader import DataLoader
from core.route_engine import RouteEngine
from core.ml_engine import MLEngine
from core.eta_predictor import BusETAPredictor

app = FastAPI(
    title="Chennai MTC Smart Transport API",
    description="AI-powered bus route optimization system",
    version="1.0.0"
)

# CORS middleware for frontend
ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
data_loader = DataLoader()
route_engine = RouteEngine(data_loader)
ml_engine = MLEngine()
eta_predictor = BusETAPredictor()

# Pydantic models
class RouteRequest(BaseModel):
    source: str
    destination: str
    time_of_day: Optional[int] = 12  # 24-hour format

class RouteResponse(BaseModel):
    route_number: str
    source_stop: str
    destination_stop: str
    stops_between: int
    total_distance_km: float
    estimated_time_minutes: float
    predicted_time_minutes: float
    delay_probability: float
    route_type: str
    stops_list: List[dict]

class StopResponse(BaseModel):
    stop_id: str
    stop_name: str
    latitude: float
    longitude: float

class PredictionRequest(BaseModel):
    number_of_stops: int
    total_distance_km: float
    time_of_day: int
    route_length: float

# API Endpoints

@app.get("/")
async def root():
    return {
        "message": "Chennai MTC Smart Transport API",
        "version": "1.0.0",
        "endpoints": ["/search-route", "/predict-time", "/get-stops", "/get-route-map"]
    }

@app.get("/get-stops", response_model=List[StopResponse])
async def get_stops(query: str = Query(None, description="Search query for stop name")):
    """Get all stops or search stops by name"""
    try:
        stops = data_loader.get_stops(query)
        return stops
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-stop-suggestions")
async def get_stop_suggestions(query: str = Query(..., min_length=1), limit: int = 10):
    """Get autocomplete suggestions for stops"""
    suggestions = data_loader.get_stop_suggestions(query, limit)
    return {"suggestions": suggestions}

@app.get("/get-reachable-stops")
async def get_reachable_stops(from_stop: str, limit: int = 50):
    """
    Get all stops reachable from a given stop
    Only returns stops that have direct bus routes from the source
    """
    reachable = []
    seen_stops = set()
    
    # Get all routes passing through this stop
    routes = data_loader.get_routes_for_stop(from_stop)
    
    for route in routes:
        stops = data_loader.get_route_stops(route)
        
        # Find the source stop's sequence (fuzzy match)
        source_seq = None
        from_lower = from_stop.lower().strip()
        for stop in stops:
            sn = stop['stop_name'].lower()
            if sn == from_lower or from_lower in sn or sn in from_lower:
                source_seq = stop['sequence']
                break
        
        if source_seq is None:
            continue
        
        # Get stops AFTER source (destinations)
        for stop in stops:
            if stop['sequence'] > source_seq:
                stop_key = stop['stop_name'].lower()
                if stop_key not in seen_stops:
                    seen_stops.add(stop_key)
                    reachable.append({
                        'stop_id': stop['stop_id'],
                        'stop_name': stop['stop_name'],
                        'latitude': stop['latitude'],
                        'longitude': stop['longitude'],
                        'routes': [route],
                        'stops_away': stop['sequence'] - source_seq
                    })
                else:
                    # Add route to existing stop
                    for r in reachable:
                        if r['stop_name'].lower() == stop_key:
                            if route not in r['routes']:
                                r['routes'].append(route)
                            break
    
    # Sort by number of routes (more routes = more popular destination)
    reachable.sort(key=lambda x: (-len(x['routes']), x['stops_away']))
    
    return {
        "from_stop": from_stop,
        "total_reachable": len(reachable),
        "routes_from_stop": list(routes),
        "reachable_stops": reachable[:limit]
    }

@app.post("/search-route")
async def search_route(request: RouteRequest):
    """Search for routes between source and destination"""
    try:
        routes = route_engine.find_routes(
            source=request.source,
            destination=request.destination,
            time_of_day=request.time_of_day
        )
        
        if not routes:
            raise HTTPException(
                status_code=404, 
                detail="No routes found between the specified stops"
            )
        
        # Add ML predictions to routes
        enriched_routes = []
        for route in routes:
            prediction = ml_engine.predict_travel_time(
                number_of_stops=route['stops_between'],
                total_distance_km=route['total_distance_km'],
                time_of_day=request.time_of_day,
                route_length=route['total_distance_km']
            )
            route['predicted_time_minutes'] = prediction['predicted_time']
            route['delay_probability'] = prediction['delay_probability']
            enriched_routes.append(route)
        
        # Rank routes
        ranked_routes = route_engine.rank_routes(enriched_routes)
        return ranked_routes
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/predict-time")
async def predict_time(request: PredictionRequest):
    """Predict travel time using ML model"""
    try:
        prediction = ml_engine.predict_travel_time(
            number_of_stops=request.number_of_stops,
            total_distance_km=request.total_distance_km,
            time_of_day=request.time_of_day,
            route_length=request.route_length
        )
        return prediction
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-route-map/{route_number}")
async def get_route_map(route_number: str):
    """Get route coordinates for map visualization"""
    try:
        route_data = data_loader.get_route_coordinates(route_number)
        if not route_data:
            raise HTTPException(
                status_code=404, 
                detail=f"Route {route_number} not found"
            )
        return route_data
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-route-between-stops/{route_number}")
async def get_route_between_stops(
    route_number: str,
    source: str = Query(...),
    destination: str = Query(...)
):
    """Get route segment between two stops for map visualization"""
    try:
        route_segment = route_engine.get_route_segment(
            route_number=route_number,
            source=source,
            destination=destination
        )
        return route_segment
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "data_loaded": data_loader.is_loaded(),
        "ml_model_ready": ml_engine.is_ready()
    }

@app.get("/stats")
async def get_stats():
    """Get system statistics"""
    return {
        "total_stops": data_loader.get_total_stops(),
        "total_routes": data_loader.get_total_routes(),
        "total_edges": data_loader.get_total_edges()
    }

@app.get("/list-all-stops")
async def list_all_stops():
    """List all unique stop names in the system"""
    stops = list(data_loader.stop_to_routes.keys())
    return {
        "total": len(stops),
        "stops": sorted(stops)
    }

@app.get("/list-all-routes")
async def list_all_routes():
    """List all route numbers in the system"""
    routes = list(data_loader.route_stops_index.keys())
    return {
        "total": len(routes),
        "routes": sorted(routes)
    }

# ============== REAL-TIME BUS ETA ENDPOINTS ==============

class ETARequest(BaseModel):
    from_stop: str
    to_stop: str
    route_number: Optional[str] = None

@app.post("/get-bus-eta")
async def get_bus_eta(request: ETARequest):
    """
    Get real-time ETA for buses arriving at user's stop
    Uses ticket machine timestamps to predict arrival
    """
    if request.route_number:
        # Get ETA for specific route
        result = eta_predictor.predict_eta(
            request.route_number,
            request.to_stop,
            request.from_stop,
            data_loader
        )
    else:
        # Find routes and get ETA for all
        routes = route_engine.find_routes(request.from_stop, request.to_stop)
        if not routes:
            return {"error": "No routes found", "incoming_buses": []}
        
        all_buses = []
        for route in routes:
            result = eta_predictor.predict_eta(
                route['route_number'],
                request.to_stop,
                request.from_stop,
                data_loader
            )
            if 'incoming_buses' in result:
                all_buses.extend(result['incoming_buses'])
        
        all_buses.sort(key=lambda x: x['eta_minutes'])
        result = {
            'from_stop': request.from_stop,
            'to_stop': request.to_stop,
            'current_time': datetime.now().strftime('%H:%M:%S'),
            'incoming_buses': all_buses[:10]
        }
    
    return result

@app.get("/get-incoming-buses/{stop_name}")
async def get_incoming_buses(stop_name: str):
    """Get all incoming buses to a specific stop"""
    result = eta_predictor.get_all_incoming_buses(stop_name, data_loader)
    return result

@app.get("/live-bus-positions")
async def get_live_bus_positions():
    """Get current positions of all tracked buses"""
    buses = []
    for bus_id, info in eta_predictor.live_bus_positions.items():
        buses.append({
            'bus_id': bus_id,
            'route': info['route'],
            'current_stop': info['current_stop'].get('stop_name', 'Unknown'),
            'destination': info.get('destination', 'Terminus'),
            'direction': info.get('direction', 'forward'),
            'latitude': info.get('current_lat', info['current_stop'].get('latitude')),
            'longitude': info.get('current_lng', info['current_stop'].get('longitude')),
            'last_update': info['last_ticket_time'].strftime('%H:%M:%S'),
            'delay_status': eta_predictor._get_delay_status(info['delay_minutes']),
            'passengers': info['passengers']
        })
    return {
        'total_buses': len(buses),
        'timestamp': datetime.now().strftime('%H:%M:%S'),
        'buses': buses
    }

@app.post("/update-bus-position")
async def update_bus_position(bus_id: str, stop_id: str, ticket_count: int = 1):
    """
    Update bus position from ticket machine
    Called when conductor generates a ticket
    """
    eta_predictor.update_bus_position(
        bus_id, stop_id, datetime.now(), ticket_count
    )
    return {"status": "updated", "bus_id": bus_id}

@app.post("/set-weather")
async def set_weather(weather: str):
    """Set current weather condition (clear, rain, heavy_rain)"""
    eta_predictor.set_weather(weather)
    return {"status": "updated", "weather": weather}

@app.post("/set-traffic")
async def set_traffic(traffic: str):
    """Set current traffic condition (light, normal, heavy, very_heavy)"""
    eta_predictor.set_traffic(traffic)
    return {"status": "updated", "traffic": traffic}

@app.post("/simulate-bus-movement")
async def simulate_movement():
    """Simulate bus movement for demo purposes"""
    eta_predictor.simulate_bus_movement()
    return {"status": "buses moved"}

@app.post("/retrain-eta-model")
async def retrain_eta():
    """Retrain ETA model with accumulated data"""
    result = eta_predictor.retrain_model()
    return result

@app.get("/get-all-stops-with-routes")
async def get_all_stops_with_routes():
    """
    Get ALL stops with their routes for client-side filtering
    This loads once and filters on frontend for instant autocomplete
    """
    stops = []
    seen = set()
    
    # Primary source: route_stops_index (cleaned stop names from route_stop_ordered.csv)
    for route_num, route_stops in data_loader.route_stops_index.items():
        for stop in route_stops:
            stop_name = stop['stop_name']
            stop_key = stop_name.lower()
            
            if stop_key in seen:
                # Add route to existing stop
                for s in stops:
                    if s['stop_name'].lower() == stop_key:
                        if route_num not in s['routes']:
                            s['routes'].append(route_num)
                        break
                continue
            
            seen.add(stop_key)
            stops.append({
                'stop_id': stop['stop_id'],
                'stop_name': stop_name,
                'latitude': float(stop['latitude']),
                'longitude': float(stop['longitude']),
                'routes': [route_num]
            })
    
    # Sort by number of routes (important stops first)
    stops.sort(key=lambda x: -len(x['routes']))
    
    return {
        "total": len(stops),
        "stops": stops
    }

@app.get("/get-destination-stops")
async def get_destination_stops(from_stop: str):
    """
    Get all stops reachable from the source stop
    Only returns stops that come AFTER the source on the SAME routes
    """
    destinations = []
    seen = set()
    from_stop_lower = from_stop.lower().strip()
    
    print(f"\n📍 Finding destinations from: '{from_stop}'")
    
    # Get routes passing through source stop
    source_routes = data_loader.get_routes_for_stop(from_stop)
    
    # If not found, try partial match
    if not source_routes:
        for stop_name, routes in data_loader.stop_to_routes.items():
            if from_stop_lower in stop_name or stop_name in from_stop_lower:
                source_routes = routes
                print(f"   Found via partial match: {stop_name} -> routes: {routes}")
                break
    
    print(f"   Source routes: {source_routes}")
    
    if not source_routes:
        return {
            "from_stop": from_stop,
            "source_routes": [],
            "total_destinations": 0,
            "destination_stops": [],
            "error": "No routes found for this stop"
        }
    
    for route in source_routes:
        stops = data_loader.get_route_stops(route)
        print(f"   Route {route}: {len(stops)} stops")
        
        # Find source stop sequence in this route
        source_seq = None
        for stop in stops:
            stop_name_lower = stop['stop_name'].lower()
            # Match by exact name or partial match
            if stop_name_lower == from_stop_lower or from_stop_lower in stop_name_lower or stop_name_lower in from_stop_lower:
                source_seq = stop['sequence']
                print(f"      Found source at seq {source_seq}: {stop['stop_name']}")
                break
        
        if source_seq is None:
            print(f"      Source not found in route {route}")
            continue
        
        # Get all stops AFTER source (these are valid destinations)
        for stop in stops:
            if stop['sequence'] > source_seq:
                stop_key = stop['stop_name'].lower()
                stops_away = stop['sequence'] - source_seq
                
                if stop_key not in seen:
                    seen.add(stop_key)
                    destinations.append({
                        'stop_id': stop['stop_id'],
                        'stop_name': stop['stop_name'],
                        'latitude': stop.get('latitude', 0),
                        'longitude': stop.get('longitude', 0),
                        'routes': [str(route)],
                        'stops_away': stops_away
                    })
                else:
                    # Add route to existing destination
                    for d in destinations:
                        if d['stop_name'].lower() == stop_key:
                            if str(route) not in d['routes']:
                                d['routes'].append(str(route))
                            # Keep minimum stops_away
                            d['stops_away'] = min(d['stops_away'], stops_away)
                            break
    
    # Sort by stops_away (nearest first)
    destinations.sort(key=lambda x: x['stops_away'])
    
    print(f"   Total destinations found: {len(destinations)}")
    
    return {
        "from_stop": from_stop,
        "source_routes": list(source_routes),
        "total_destinations": len(destinations),
        "destination_stops": destinations
    }

# Add these routes if not already present:

@app.get("/api/routes")
async def get_all_routes():
    """Get list of all available routes"""
    routes = list(data_loader.route_stops_index.keys())
    return {
        "total": len(routes),
        "routes": sorted(routes)
    }

@app.get("/api/route/{route_number}/stops")
async def get_route_stops(route_number: str):
    """Get all stops for a specific route"""
    stops = data_loader.get_route_stops(route_number)
    if not stops:
        raise HTTPException(status_code=404, detail=f"Route {route_number} not found")
    return {
        "route_number": route_number,
        "total_stops": len(stops),
        "stops": stops
    }

@app.get("/api/route/{route_number}/coordinates")
async def get_route_coordinates(route_number: str):
    """Get coordinates for map visualization"""
    coords = data_loader.get_route_coordinates(route_number)
    if not coords:
        raise HTTPException(status_code=404, detail=f"Route {route_number} not found")
    return coords

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
