"""
ML Engine - Travel Time Prediction and Delay Probability
Trained on actual route data from CSV files
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import pickle
import os
from typing import Dict, Tuple

class MLEngine:
    def __init__(self):
        # Dynamically determine the base path (project root)
        current_file = os.path.abspath(__file__)
        core_dir = os.path.dirname(current_file)
        backend_dir = os.path.dirname(core_dir)
        self.base_path = os.getenv("DATA_BASE_PATH", os.path.dirname(backend_dir))
        
        self.model_path = os.path.join(self.base_path, "backend/models")
        self.travel_time_model = None
        self.delay_model = None
        self.scaler = StandardScaler()
        self._ready = False
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize or load ML models"""
        try:
            # Try to load existing models
            if self._load_models():
                print("✅ ML models loaded successfully!")
            else:
                # Train new models with actual CSV data
                print("⏳ Training new ML models from CSV data...")
                self._train_models()
                print("✅ ML models trained successfully!")
            
            self._ready = True
        except Exception as e:
            print(f"❌ Error initializing ML models: {e}")
            self._ready = False
    
    def _load_models(self) -> bool:
        """Load pre-trained models from disk"""
        try:
            travel_model_path = os.path.join(self.model_path, "travel_time_model.pkl")
            delay_model_path = os.path.join(self.model_path, "delay_model.pkl")
            scaler_path = os.path.join(self.model_path, "scaler.pkl")
            
            if all(os.path.exists(p) for p in [travel_model_path, delay_model_path, scaler_path]):
                with open(travel_model_path, 'rb') as f:
                    self.travel_time_model = pickle.load(f)
                with open(delay_model_path, 'rb') as f:
                    self.delay_model = pickle.load(f)
                with open(scaler_path, 'rb') as f:
                    self.scaler = pickle.load(f)
                return True
        except:
            pass
        return False
    
    def _save_models(self):
        """Save trained models to disk"""
        os.makedirs(self.model_path, exist_ok=True)
        
        with open(os.path.join(self.model_path, "travel_time_model.pkl"), 'wb') as f:
            pickle.dump(self.travel_time_model, f)
        with open(os.path.join(self.model_path, "delay_model.pkl"), 'wb') as f:
            pickle.dump(self.delay_model, f)
        with open(os.path.join(self.model_path, "scaler.pkl"), 'wb') as f:
            pickle.dump(self.scaler, f)
    
    def _load_csv_data(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load the actual CSV files"""
        route_stops_path = os.path.join(self.base_path, "route_stop_ordered.csv")
        route_edges_path = os.path.join(self.base_path, "route_edges.csv")
        
        route_stops_df = pd.read_csv(route_stops_path)
        route_edges_df = pd.read_csv(route_edges_path)
        
        print(f"   - Loaded route_stop_ordered.csv: {len(route_stops_df)} rows")
        print(f"   - Loaded route_edges.csv: {len(route_edges_df)} rows")
        
        return route_stops_df, route_edges_df
    
    def _generate_training_data_from_csv(self) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """
        Generate training data from actual CSV files
        
        Uses route_stop_ordered.csv and route_edges.csv to create realistic
        training samples based on actual route patterns
        """
        route_stops_df, route_edges_df = self._load_csv_data()
        
        # Group stops by route
        route_groups = route_stops_df.groupby('route_number')
        
        training_samples = []
        
        for route_number, group in route_groups:
            group = group.sort_values('stop_sequence')
            stops_list = group.to_dict('records')
            num_stops_in_route = len(stops_list)
            
            if num_stops_in_route < 2:
                continue
            
            # Get edges for this route
            route_edges = route_edges_df[
                route_edges_df['route_number'].astype(str) == str(route_number)
            ]
            
            # Calculate total route distance
            total_route_distance = route_edges['distance_km'].sum() if len(route_edges) > 0 else 0
            
            # Generate samples for different source-destination pairs within this route
            for i in range(num_stops_in_route):
                for j in range(i + 1, min(i + 5, num_stops_in_route)):  # Reduced for faster training
                    source_stop = stops_list[i]
                    dest_stop = stops_list[j]
                    
                    # Calculate segment metrics
                    num_stops = j - i
                    
                    # Calculate segment distance from edges
                    segment_distance = self._calculate_segment_distance(
                        route_edges, stops_list, i, j
                    )
                    
                    if segment_distance == 0:
                        # Estimate using coordinates
                        segment_distance = self._estimate_distance_from_coords(
                            stops_list[i:j+1]
                        )
                    
                    # Generate samples for different times of day (reduced for speed)
                    for hour in [8, 12, 17, 22]:
                        peak_hour_flag = 1 if (8 <= hour <= 10) or (17 <= hour <= 20) else 0
                        
                        # Calculate average stop density
                        avg_stop_density = num_stops / (segment_distance + 0.1)
                        
                        training_samples.append({
                            'route_number': route_number,
                            'number_of_stops': num_stops,
                            'total_distance_km': round(segment_distance, 2),
                            'time_of_day': hour,
                            'peak_hour_flag': peak_hour_flag,
                            'route_length': round(total_route_distance, 2),
                            'average_stop_density': round(avg_stop_density, 3),
                            'source_lat': source_stop['latitude'],
                            'source_lng': source_stop['longitude'],
                            'dest_lat': dest_stop['latitude'],
                            'dest_lng': dest_stop['longitude']
                        })
        
        df = pd.DataFrame(training_samples)
        print(f"   - Generated {len(df)} training samples from CSV data")
        
        # Calculate target: travel_time based on realistic formula
        # Base speed varies by time of day
        df['traffic_multiplier'] = df['time_of_day'].apply(self._get_traffic_factor)
        
        # Travel time = (distance / speed) * 60 + stop_delay
        base_speed_kmh = 18  # Average bus speed in Chennai
        stop_delay_minutes = 1.2  # Average delay per stop
        
        # Add some realistic variation based on route characteristics
        np.random.seed(42)
        noise = np.random.normal(0, 2, len(df))
        
        df['travel_time'] = (
            (df['total_distance_km'] / base_speed_kmh) * 60 * df['traffic_multiplier'] +
            df['number_of_stops'] * stop_delay_minutes +
            noise
        ).clip(lower=3)  # Minimum 3 minutes
        
        # Generate delay labels
        # Higher probability during peak hours and for longer distances
        delay_prob = (
            0.35 * df['peak_hour_flag'] +
            0.25 * (df['total_distance_km'] / df['total_distance_km'].max()) +
            0.15 * (df['number_of_stops'] / df['number_of_stops'].max()) +
            np.random.uniform(0, 0.25, len(df))
        )
        df['has_delay'] = (delay_prob > 0.5).astype(int)
        
        return df, df['travel_time'], df['has_delay']
    
    def _calculate_segment_distance(self, route_edges: pd.DataFrame, 
                                    stops_list: list, start_idx: int, end_idx: int) -> float:
        """Calculate distance for a segment using route edges"""
        if len(route_edges) == 0:
            return 0.0
        
        total_distance = 0.0
        
        # Create a mapping of stop names to their indices
        stop_names = [s['stop_name'].lower() for s in stops_list]
        
        for _, edge in route_edges.iterrows():
            from_stop = str(edge['from_stop']).lower()
            to_stop = str(edge['to_stop']).lower()
            
            # Check if this edge is within our segment
            try:
                from_idx = stop_names.index(from_stop) if from_stop in stop_names else -1
                to_idx = stop_names.index(to_stop) if to_stop in stop_names else -1
                
                if from_idx >= start_idx and to_idx <= end_idx and from_idx < to_idx:
                    total_distance += edge['distance_km']
            except:
                continue
        
        return total_distance
    
    def _estimate_distance_from_coords(self, stops: list) -> float:
        """Estimate distance using haversine formula between consecutive stops"""
        from math import radians, cos, sin, sqrt, atan2
        
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371  # Earth's radius in km
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            return R * c
        
        total_distance = 0.0
        for i in range(len(stops) - 1):
            dist = haversine(
                stops[i]['latitude'], stops[i]['longitude'],
                stops[i+1]['latitude'], stops[i+1]['longitude']
            )
            total_distance += dist
        
        # Multiply by road factor (roads are not straight lines)
        return total_distance * 1.3
    
    def _get_traffic_factor(self, hour: int) -> float:
        """Get traffic multiplier based on hour"""
        if 8 <= hour <= 10:
            return 1.6  # Morning peak
        elif 17 <= hour <= 20:
            return 1.8  # Evening peak (worst)
        elif 11 <= hour <= 16:
            return 1.2  # Midday
        elif 21 <= hour <= 23 or 0 <= hour <= 6:
            return 0.85  # Night
        return 1.0
    
    def _train_models(self):
        """Train ML models on actual CSV data"""
        # Generate training data from CSV files
        print("   [1/5] Generating training data...")
        df, y_time, y_delay = self._generate_training_data_from_csv()
        
        # Feature columns for training
        feature_cols = ['number_of_stops', 'total_distance_km', 'time_of_day', 
                       'peak_hour_flag', 'route_length', 'average_stop_density']
        
        X_features = df[feature_cols]
        
        # Scale features
        print("   [2/5] Scaling features...")
        X_scaled = self.scaler.fit_transform(X_features)
        
        # Split data
        X_train, X_test, y_train_time, y_test_time = train_test_split(
            X_scaled, y_time, test_size=0.2, random_state=42
        )
        _, _, y_train_delay, y_test_delay = train_test_split(
            X_scaled, y_delay, test_size=0.2, random_state=42
        )
        
        # Train travel time model (RandomForestRegressor)
        print("   [3/5] Training travel time model...")
        self.travel_time_model = RandomForestRegressor(
            n_estimators=50,
            max_depth=10,
            min_samples_split=5,
            random_state=42,
            n_jobs=-1
        )
        self.travel_time_model.fit(X_train, y_train_time)
        
        # Train delay prediction model
        print("   [4/5] Training delay prediction model...")
        self.delay_model = GradientBoostingClassifier(
            n_estimators=30,
            max_depth=5,
            random_state=42
        )
        self.delay_model.fit(X_train, y_train_delay)
        
        # Evaluate models
        time_score = self.travel_time_model.score(X_test, y_test_time)
        delay_score = self.delay_model.score(X_test, y_test_delay)
        
        print(f"   - Travel Time Model R² Score: {time_score:.3f}")
        print(f"   - Delay Model Accuracy: {delay_score:.3f}")
        
        # Save models
        self._save_models()
    
    def predict_travel_time(self, number_of_stops: int, total_distance_km: float,
                           time_of_day: int, route_length: float) -> Dict:
        """
        Predict travel time and delay probability
        """
        if not self._ready:
            return self._fallback_prediction(number_of_stops, total_distance_km, time_of_day)
        
        try:
            # Prepare features
            peak_hour_flag = 1 if (8 <= time_of_day <= 10) or (17 <= time_of_day <= 20) else 0
            average_stop_density = number_of_stops / (total_distance_km + 0.1)
            
            features = np.array([[
                number_of_stops,
                total_distance_km,
                time_of_day,
                peak_hour_flag,
                route_length,
                average_stop_density
            ]])
            
            # Scale features using DataFrame to preserve feature names
            feature_names = ['number_of_stops', 'total_distance_km', 'time_of_day',
                           'peak_hour_flag', 'route_length', 'average_stop_density']
            import pandas as pd
            features_df = pd.DataFrame(features, columns=feature_names)
            
            # Scale features
            features_scaled = self.scaler.transform(features_df)
            
            # Predict travel time
            predicted_time = self.travel_time_model.predict(features_scaled)[0]
            
            # Predict delay probability
            delay_proba = self.delay_model.predict_proba(features_scaled)[0]
            delay_probability = delay_proba[1] if len(delay_proba) > 1 else 0.0
            
            # Get confidence from model
            tree_predictions = [tree.predict(features_scaled)[0] 
                              for tree in self.travel_time_model.estimators_]
            confidence = 1 - (np.std(tree_predictions) / (np.mean(tree_predictions) + 0.1))
            
            return {
                'predicted_time': round(max(3, predicted_time), 1),
                'delay_probability': round(delay_probability, 2),
                'confidence': round(max(0, min(1, confidence)), 2),
                'peak_hour': bool(peak_hour_flag),
                'traffic_factor': self._get_traffic_factor(time_of_day)
            }
            
        except Exception as e:
            print(f"Prediction error: {e}")
            return self._fallback_prediction(number_of_stops, total_distance_km, time_of_day)
    
    def _fallback_prediction(self, number_of_stops: int, total_distance_km: float, 
                            time_of_day: int) -> Dict:
        """Fallback prediction using simple formula"""
        base_speed = 18  # km/h
        stop_delay = 1.2  # minutes
        
        traffic_factor = self._get_traffic_factor(time_of_day)
        
        travel_time = (total_distance_km / base_speed) * 60 * traffic_factor
        travel_time += number_of_stops * stop_delay
        
        peak_hour = (8 <= time_of_day <= 10) or (17 <= time_of_day <= 20)
        delay_prob = 0.6 if peak_hour else 0.25
        
        return {
            'predicted_time': round(max(3, travel_time), 1),
            'delay_probability': delay_prob,
            'confidence': 0.6,
            'peak_hour': peak_hour,
            'traffic_factor': traffic_factor
        }
    
    def is_ready(self) -> bool:
        """Check if ML engine is ready"""
        return self._ready
    
    def get_feature_importance(self) -> Dict:
        """Get feature importance from the model"""
        if not self._ready or self.travel_time_model is None:
            return {}
        
        feature_names = ['number_of_stops', 'total_distance_km', 'time_of_day',
                        'peak_hour_flag', 'route_length', 'average_stop_density']
        
        importance = dict(zip(feature_names, 
                            self.travel_time_model.feature_importances_))
        
        return {k: round(v, 4) for k, v in sorted(importance.items(), 
                                                   key=lambda x: x[1], 
                                                   reverse=True)}
    
    def retrain(self):
        """Force retrain models with current CSV data"""
        # Delete existing models
        for filename in ['travel_time_model.pkl', 'delay_model.pkl', 'scaler.pkl']:
            filepath = os.path.join(self.model_path, filename)
            if os.path.exists(filepath):
                os.remove(filepath)
        
        # Retrain
        print("⏳ Retraining ML models from CSV data...")
        self._train_models()
        print("✅ ML models retrained successfully!")
