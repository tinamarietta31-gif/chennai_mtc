"""
Real-Time Bus ETA Prediction Engine
Uses ticket machine timestamps to track bus locations and predict arrival times
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from datetime import datetime, timedelta
import pickle
import os
from typing import Dict, List, Optional
from collections import defaultdict
import random
import requests

class BusETAPredictor:
    def __init__(self):
        self.base_path = "/Users/jerimothimmanuel/chennai_mtc_project"
        self.model_path = os.path.join(self.base_path, "backend/models")
        self.eta_model = None
        self.scaler = StandardScaler()
        
        # Live bus tracking data (in production, this comes from ticket machines)
        self.live_bus_positions = {}  # bus_id -> {route, current_stop, timestamp, direction}
        self.ticket_history = []  # Historical ticket timestamps
        
        # Route timing patterns learned from data
        self.route_timing_patterns = defaultdict(dict)
        
        # Weather and traffic factors
        self.current_weather = "clear"  # clear, rain, heavy_rain
        self.current_traffic = "normal"  # light, normal, heavy, very_heavy
        
        self._ready = False
        self._initialize()
    
    def _initialize(self):
        """Initialize the ETA prediction system"""
        try:
            if not self._load_model():
                print("⏳ Training ETA prediction model...")
                self._train_eta_model()
            
            # Load historical patterns
            self._load_route_patterns()
            
            # Initialize simulated live buses
            self._initialize_live_buses()
            
            self._ready = True
            print("✅ Bus ETA Predictor initialized!")
        except Exception as e:
            print(f"❌ Error initializing ETA Predictor: {e}")
            import traceback
            traceback.print_exc()
    
    def _load_model(self) -> bool:
        """Load pre-trained ETA model"""
        try:
            model_file = os.path.join(self.model_path, "eta_model.pkl")
            scaler_file = os.path.join(self.model_path, "eta_scaler.pkl")
            
            if os.path.exists(model_file) and os.path.exists(scaler_file):
                with open(model_file, 'rb') as f:
                    self.eta_model = pickle.load(f)
                with open(scaler_file, 'rb') as f:
                    self.scaler = pickle.load(f)
                return True
        except:
            pass
        return False
    
    def _save_model(self):
        """Save trained model"""
        os.makedirs(self.model_path, exist_ok=True)
        with open(os.path.join(self.model_path, "eta_model.pkl"), 'wb') as f:
            pickle.dump(self.eta_model, f)
        with open(os.path.join(self.model_path, "eta_scaler.pkl"), 'wb') as f:
            pickle.dump(self.scaler, f)
    
    def _load_route_patterns(self):
        """Load route timing patterns from CSV data"""
        try:
            route_stops_path = os.path.join(self.base_path, "route_stop_ordered.csv")
            route_edges_path = os.path.join(self.base_path, "route_edges.csv")
            
            route_stops_df = pd.read_csv(route_stops_path)
            route_edges_df = pd.read_csv(route_edges_path)
            
            # Calculate average time between stops for each route
            for route in route_stops_df['route_number'].unique():
                route_data = route_stops_df[route_stops_df['route_number'] == route]
                edges = route_edges_df[route_edges_df['route_number'] == route]
                
                total_distance = edges['distance_km'].sum()
                num_stops = len(route_data)
                
                # Estimate timing patterns
                self.route_timing_patterns[str(route)] = {
                    'total_distance': total_distance,
                    'num_stops': num_stops,
                    'avg_speed_peak': 12,  # km/h during peak
                    'avg_speed_normal': 18,  # km/h normal
                    'avg_speed_night': 25,  # km/h night
                    'stop_delay': 1.5,  # minutes per stop
                    'frequency_peak': 10,  # minutes between buses
                    'frequency_normal': 15,
                    'frequency_night': 30
                }
            
            print(f"   - Loaded patterns for {len(self.route_timing_patterns)} routes")
        except Exception as e:
            print(f"   - Error loading patterns: {e}")
    
    def _train_eta_model(self):
        """Train ETA prediction model on simulated ticket timestamp data"""
        # Generate training data simulating 10 days of ticket machine data
        training_data = self._generate_ticket_training_data(days=10)
        
        features = [
            'distance_to_stop',      # km from current position to target stop
            'num_stops_remaining',   # stops between current and target
            'hour_of_day',           # 0-23
            'day_of_week',           # 0-6
            'is_peak_hour',          # 1 or 0
            'is_weekend',            # 1 or 0
            'weather_factor',        # 1.0 (clear) to 2.0 (heavy rain)
            'traffic_factor',        # 1.0 (light) to 2.0 (very heavy)
            'historical_avg_time',   # historical average for this segment
            'recent_delay',          # delay in last segment (minutes)
        ]
        
        X = training_data[features]
        y = training_data['actual_eta']  # in minutes
        
        # Scale features
        X_scaled = self.scaler.fit_transform(X)
        
        # Train Gradient Boosting model
        self.eta_model = GradientBoostingRegressor(
            n_estimators=150,
            max_depth=8,
            min_samples_split=5,
            learning_rate=0.1,
            random_state=42
        )
        self.eta_model.fit(X_scaled, y)
        
        # Save model
        self._save_model()
        
        print(f"   - Trained on {len(training_data)} ticket records")
        print(f"   - Model R² Score: {self.eta_model.score(X_scaled, y):.3f}")
    
    def _generate_ticket_training_data(self, days: int = 10) -> pd.DataFrame:
        """
        Generate simulated ticket machine timestamp data
        In production, this would come from real ticket machines
        """
        records = []
        
        # Load route data
        route_stops_path = os.path.join(self.base_path, "route_stop_ordered.csv")
        route_edges_path = os.path.join(self.base_path, "route_edges.csv")
        
        route_stops_df = pd.read_csv(route_stops_path)
        route_edges_df = pd.read_csv(route_edges_path)
        
        routes = route_stops_df['route_number'].unique()
        
        for day in range(days):
            for route in routes:
                route_data = route_stops_df[route_stops_df['route_number'] == route].sort_values('stop_sequence')
                stops = route_data.to_dict('records')
                
                if len(stops) < 3:
                    continue
                
                # Simulate multiple bus trips per day
                trips_per_day = random.randint(15, 25)
                
                for trip in range(trips_per_day):
                    # Random start hour (5 AM to 11 PM)
                    start_hour = random.randint(5, 22)
                    start_minute = random.randint(0, 59)
                    
                    # Determine conditions
                    is_peak = (7 <= start_hour <= 10) or (17 <= start_hour <= 20)
                    is_weekend = day % 7 >= 5
                    
                    # Weather (random, with some patterns)
                    weather_choices = ['clear'] * 7 + ['rain'] * 2 + ['heavy_rain'] * 1
                    weather = random.choice(weather_choices)
                    weather_factor = {'clear': 1.0, 'rain': 1.3, 'heavy_rain': 1.8}[weather]
                    
                    # Traffic based on time
                    if is_peak:
                        traffic_factor = random.uniform(1.4, 1.8)
                    elif is_weekend:
                        traffic_factor = random.uniform(0.9, 1.2)
                    else:
                        traffic_factor = random.uniform(1.0, 1.3)
                    
                    # Simulate bus movement through stops
                    current_time = datetime.now().replace(
                        hour=start_hour, minute=start_minute, second=0
                    ) - timedelta(days=days-day)
                    
                    cumulative_delay = 0
                    
                    for i, stop in enumerate(stops[:-1]):
                        # Get distance to next stop
                        edges = route_edges_df[
                            (route_edges_df['route_number'] == route) &
                            (route_edges_df['from_stop'].astype(str) == str(stop['stop_id']))
                        ]
                        
                        distance = edges['distance_km'].sum() if len(edges) > 0 else random.uniform(0.5, 2.0)
                        
                        # Calculate time to reach each future stop
                        for j in range(i + 1, min(i + 10, len(stops))):
                            target_stop = stops[j]
                            stops_between = j - i
                            
                            # Calculate distance to target
                            dist_to_target = distance * stops_between * random.uniform(0.8, 1.2)
                            
                            # Base speed
                            if is_peak:
                                base_speed = 12
                            elif 22 <= start_hour or start_hour <= 5:
                                base_speed = 25
                            else:
                                base_speed = 18
                            
                            # Calculate ETA
                            travel_time = (dist_to_target / base_speed) * 60  # minutes
                            stop_time = stops_between * 1.5  # 1.5 min per stop
                            
                            # Apply factors
                            actual_eta = (travel_time + stop_time) * weather_factor * traffic_factor
                            
                            # Add some randomness
                            actual_eta += random.gauss(0, 2)
                            actual_eta = max(2, actual_eta)  # minimum 2 minutes
                            
                            # Historical average (simulated)
                            historical_avg = (travel_time + stop_time) * 1.1
                            
                            records.append({
                                'route_number': route,
                                'current_stop_seq': i,
                                'target_stop_seq': j,
                                'distance_to_stop': dist_to_target,
                                'num_stops_remaining': stops_between,
                                'hour_of_day': start_hour,
                                'day_of_week': day % 7,
                                'is_peak_hour': 1 if is_peak else 0,
                                'is_weekend': 1 if is_weekend else 0,
                                'weather_factor': weather_factor,
                                'traffic_factor': traffic_factor,
                                'historical_avg_time': historical_avg,
                                'recent_delay': cumulative_delay,
                                'actual_eta': actual_eta
                            })
                        
                        # Update cumulative delay
                        cumulative_delay = random.gauss(cumulative_delay, 1)
                        cumulative_delay = max(0, cumulative_delay)
        
        return pd.DataFrame(records)
    
    def _initialize_live_buses(self):
        """Initialize simulated live bus positions"""
        # In production, this data comes from ticket machine API
        route_stops_path = os.path.join(self.base_path, "route_stop_ordered.csv")
        route_stops_df = pd.read_csv(route_stops_path)
        
        routes = route_stops_df['route_number'].unique()
        
        for route in routes:
            route_data = route_stops_df[route_stops_df['route_number'] == route].sort_values('stop_sequence')
            stops = route_data.to_dict('records')
            
            if len(stops) < 3:
                continue
            
            destination_stop = stops[-1]['stop_name']
            
            # Create 2-3 buses per route
            for bus_num in range(random.randint(2, 3)):
                bus_id = f"{route}_BUS_{bus_num}"
                current_stop_idx = random.randint(0, len(stops) - 2)
                
                self.live_bus_positions[bus_id] = {
                    'route': str(route),
                    'current_stop_idx': current_stop_idx,
                    'current_stop': stops[current_stop_idx],
                    'destination': destination_stop,
                    'last_ticket_time': datetime.now() - timedelta(minutes=random.randint(1, 5)),
                    'direction': 'forward',
                    'delay_minutes': random.uniform(-2, 5),
                    'passengers': random.randint(10, 50),
                    'progress_to_next': 0.0,
                    'current_lat': float(stops[current_stop_idx].get('latitude', 0)),
                    'current_lng': float(stops[current_stop_idx].get('longitude', 0)),
                }
        
        print(f"   - Initialized {len(self.live_bus_positions)} live buses on {len(routes)} routes")
    
    def update_bus_position(self, bus_id: str, stop_id: str, timestamp: datetime, 
                           ticket_count: int = 0):
        """
        Update bus position from ticket machine data
        Called when conductor generates a ticket
        """
        if bus_id in self.live_bus_positions:
            bus = self.live_bus_positions[bus_id]
            
            # Calculate delay based on expected vs actual time
            expected_time = bus['last_ticket_time'] + timedelta(minutes=3)
            actual_delay = (timestamp - expected_time).total_seconds() / 60
            
            bus['last_ticket_time'] = timestamp
            bus['delay_minutes'] = (bus['delay_minutes'] + actual_delay) / 2  # Running average
            bus['passengers'] += ticket_count
            
            # Store in history for model retraining
            self.ticket_history.append({
                'bus_id': bus_id,
                'stop_id': stop_id,
                'timestamp': timestamp,
                'delay': actual_delay
            })
    
    def predict_eta(self, route_number: str, target_stop_name: str, 
                   user_stop_name: str, data_loader) -> Dict:
        """
        Predict ETA for buses arriving at user's stop
        
        Args:
            route_number: Bus route number
            target_stop_name: Where user wants to go (for filtering buses going that direction)
            user_stop_name: User's current stop (where they're waiting)
            data_loader: DataLoader instance for stop info
        
        Returns:
            List of incoming buses with ETA predictions
        """
        if not self._ready:
            return {'error': 'ETA Predictor not ready'}
        
        incoming_buses = []
        current_time = datetime.now()
        hour = current_time.hour
        day_of_week = current_time.weekday()
        
        # Determine current conditions
        is_peak = (7 <= hour <= 10) or (17 <= hour <= 20)
        is_weekend = day_of_week >= 5
        weather_factor = self._get_weather_factor()
        traffic_factor = self._get_traffic_factor(hour, is_weekend)
        
        # Get user's stop sequence in this route
        user_stop_seq = data_loader.get_stop_sequence_in_route(route_number, user_stop_name)
        target_stop_seq = data_loader.get_stop_sequence_in_route(route_number, target_stop_name)
        
        if user_stop_seq is None:
            return {'error': f'Stop {user_stop_name} not found on route {route_number}'}
        
        # Find buses on this route that haven't passed user's stop
        for bus_id, bus_info in self.live_bus_positions.items():
            if bus_info['route'] != str(route_number):
                continue
            
            bus_stop_seq = bus_info['current_stop_idx']
            
            # Check if bus is before user's stop (coming towards them)
            if bus_stop_seq < user_stop_seq:
                stops_away = user_stop_seq - bus_stop_seq
                
                # Estimate distance
                distance = stops_away * 1.2  # Rough estimate: 1.2 km per stop
                
                # Get historical average for this segment
                pattern = self.route_timing_patterns.get(str(route_number), {})
                historical_avg = stops_away * 3  # 3 min per stop average
                
                # Prepare features for prediction
                features = np.array([[
                    distance,
                    stops_away,
                    hour,
                    day_of_week,
                    1 if is_peak else 0,
                    1 if is_weekend else 0,
                    weather_factor,
                    traffic_factor,
                    historical_avg,
                    bus_info['delay_minutes']
                ]])
                
                # Predict ETA
                features_scaled = self.scaler.transform(features)
                predicted_eta = self.eta_model.predict(features_scaled)[0]
                
                # Apply current delay
                predicted_eta += bus_info['delay_minutes']
                predicted_eta = max(1, predicted_eta)  # Minimum 1 minute
                
                # Calculate arrival time
                arrival_time = current_time + timedelta(minutes=predicted_eta)
                
                incoming_buses.append({
                    'bus_id': bus_id,
                    'route_number': route_number,
                    'current_location': bus_info['current_stop'].get('stop_name', f"Stop {bus_stop_seq}"),
                    'stops_away': stops_away,
                    'eta_minutes': round(predicted_eta, 1),
                    'arrival_time': arrival_time.strftime('%H:%M'),
                    'delay_status': self._get_delay_status(bus_info['delay_minutes']),
                    'passengers': bus_info['passengers'],
                    'confidence': self._calculate_confidence(stops_away, bus_info['delay_minutes'])
                })
        
        # Sort by ETA
        incoming_buses.sort(key=lambda x: x['eta_minutes'])
        
        return {
            'user_stop': user_stop_name,
            'destination': target_stop_name,
            'route_number': route_number,
            'current_time': current_time.strftime('%H:%M:%S'),
            'weather': self.current_weather,
            'traffic': self.current_traffic,
            'incoming_buses': incoming_buses[:5],  # Top 5 nearest buses
            'next_bus_eta': incoming_buses[0]['eta_minutes'] if incoming_buses else None
        }
    
    def get_all_incoming_buses(self, user_stop_name: str, data_loader) -> Dict:
        """Get all incoming buses to a stop across all routes"""
        all_buses = []
        
        # Get all routes passing through this stop
        routes = data_loader.get_routes_for_stop(user_stop_name)
        
        for route in routes:
            result = self.predict_eta(route, user_stop_name, user_stop_name, data_loader)
            if 'incoming_buses' in result:
                all_buses.extend(result['incoming_buses'])
        
        # Sort all by ETA
        all_buses.sort(key=lambda x: x['eta_minutes'])
        
        return {
            'stop_name': user_stop_name,
            'current_time': datetime.now().strftime('%H:%M:%S'),
            'total_incoming': len(all_buses),
            'buses': all_buses[:10]  # Top 10
        }
    
    def _get_weather_factor(self) -> float:
        """Get current weather impact factor"""
        factors = {
            'clear': 1.0,
            'cloudy': 1.05,
            'rain': 1.3,
            'heavy_rain': 1.8
        }
        return factors.get(self.current_weather, 1.0)
    
    def _get_traffic_factor(self, hour: int, is_weekend: bool) -> float:
        """Get traffic factor based on time"""
        if is_weekend:
            return 1.1
        
        if 7 <= hour <= 10:
            return 1.6  # Morning rush
        elif 17 <= hour <= 20:
            return 1.8  # Evening rush (worst)
        elif 11 <= hour <= 16:
            return 1.2  # Midday
        elif 21 <= hour or hour <= 6:
            return 0.9  # Night
        return 1.0
    
    def _get_delay_status(self, delay_minutes: float) -> str:
        """Get human-readable delay status"""
        if delay_minutes < -1:
            return "Early"
        elif delay_minutes < 2:
            return "On Time"
        elif delay_minutes < 5:
            return "Slightly Delayed"
        elif delay_minutes < 10:
            return "Delayed"
        else:
            return "Heavily Delayed"
    
    def _calculate_confidence(self, stops_away: int, current_delay: float) -> float:
        """Calculate prediction confidence"""
        # Less confident when bus is far away or has high delay variance
        base_confidence = 0.95
        distance_penalty = stops_away * 0.03
        delay_penalty = abs(current_delay) * 0.02
        
        confidence = base_confidence - distance_penalty - delay_penalty
        return round(max(0.5, min(0.98, confidence)), 2)
    
    def set_weather(self, weather: str):
        """Update current weather condition"""
        if weather in ['clear', 'cloudy', 'rain', 'heavy_rain']:
            self.current_weather = weather
    
    def set_traffic(self, traffic: str):
        """Update current traffic condition"""
        if traffic in ['light', 'normal', 'heavy', 'very_heavy']:
            self.current_traffic = traffic
    
    def simulate_bus_movement(self):
        """Simulate smooth bus movement between stops for realistic demo tracking"""
        if not hasattr(self, '_cached_route_stops'):
            route_stops_path = os.path.join(self.base_path, "route_stop_ordered.csv")
            self._cached_route_stops = pd.read_csv(route_stops_path)
            
        for bus_id, bus_info in self.live_bus_positions.items():
            route_data = self._cached_route_stops[
                self._cached_route_stops['route_number'] == bus_info['route']
            ].sort_values('stop_sequence')
            stops = route_data.to_dict('records')
            
            idx = bus_info['current_stop_idx']
            if idx < len(stops) - 1:
                curr_stop = stops[idx]
                next_stop = stops[idx + 1]
                
                # Advance progress by ~2% per 3-second tick, creating a smooth ~2.5 minute journey between stops
                bus_info['progress_to_next'] = bus_info.get('progress_to_next', 0.0) + 0.02
                
                if bus_info['progress_to_next'] >= 1.0:
                    # Reached next stop
                    bus_info['current_stop_idx'] += 1
                    bus_info['progress_to_next'] = 0.0
                    bus_info['current_stop'] = next_stop
                    bus_info['last_ticket_time'] = datetime.now()
                    bus_info['current_lat'] = float(next_stop.get('latitude', 0))
                    bus_info['current_lng'] = float(next_stop.get('longitude', 0))
                    
                    bus_info['delay_minutes'] += random.gauss(0, 1)
                    bus_info['passengers'] += random.randint(-5, 10)
                    bus_info['passengers'] = max(0, bus_info['passengers'])
                else:
                    # Get OSRM polyline for smooth map movement strictly on roads
                    lat1, lon1 = float(curr_stop.get('latitude', 0)), float(curr_stop.get('longitude', 0))
                    lat2, lon2 = float(next_stop.get('latitude', 0)), float(next_stop.get('longitude', 0))
                    p = bus_info['progress_to_next']
                    
                    path = self._get_osrm_path(lat1, lon1, lat2, lon2)
                    if len(path) > 1:
                        # Find precise sub-segment along detailed polyline
                        idx_float = p * (len(path) - 1)
                        idx_lower = int(idx_float)
                        idx_upper = min(idx_lower + 1, len(path) - 1)
                        remainder = idx_float - idx_lower
                        
                        plat1, plng1 = path[idx_lower]
                        plat2, plng2 = path[idx_upper]
                        
                        bus_info['current_lat'] = plat1 + (plat2 - plat1) * remainder
                        bus_info['current_lng'] = plng1 + (plng2 - plng1) * remainder
                    else:
                        bus_info['current_lat'] = lat1 + (lat2 - lat1) * p
                        bus_info['current_lng'] = lon1 + (lon2 - lon1) * p
                        
    def _get_osrm_path(self, lat1: float, lon1: float, lat2: float, lon2: float) -> List[List[float]]:
        """Fetch and cache precise road geometry between two points using OSRM"""
        if not hasattr(self, '_osrm_cache'):
            self._osrm_cache = {}
            
        key = f"{lat1:.4f},{lon1:.4f}-{lat2:.4f},{lon2:.4f}"
        if key in self._osrm_cache:
            return self._osrm_cache[key]
            
        try:
            url = f"https://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=geojson&continue_straight=true&approaches=unrestricted;unrestricted"
            res = requests.get(url, timeout=2) # Short timeout so demo doesn't hang
            data = res.json()
            if data.get('code') == 'Ok' and data.get('routes'):
                coords = data['routes'][0]['geometry']['coordinates']
                path = [[c[1], c[0]] for c in coords] # GeoJSON is lon,lat -> Leaflet wants lat,lon
                self._osrm_cache[key] = path
                return path
        except Exception:
            pass
            
        # Fallback to straight line
        path = [[lat1, lon1], [lat2, lon2]]
        self._osrm_cache[key] = path
        return path
    def retrain_model(self):
        """Retrain model with accumulated ticket history"""
        if len(self.ticket_history) < 100:
            return {'status': 'Not enough data', 'records': len(self.ticket_history)}
        
        # In production, combine historical + new data
        print("⏳ Retraining ETA model with new data...")
        self._train_eta_model()
        return {'status': 'Model retrained', 'records': len(self.ticket_history)}
    
    def is_ready(self) -> bool:
        return self._ready
