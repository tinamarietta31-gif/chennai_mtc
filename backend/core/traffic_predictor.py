"""
Traffic Prediction Model - Predict traffic conditions based on various factors
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
from collections import defaultdict

class TrafficPredictor:
    def __init__(self):
        # Traffic patterns for different areas of Chennai
        self.area_traffic_patterns = {
            'central': {  # T.Nagar, Anna Nagar, Adyar
                'morning_peak': (7, 10),
                'evening_peak': (17, 21),
                'peak_multiplier': 1.8,
                'base_multiplier': 1.0
            },
            'it_corridor': {  # OMR, Sholinganallur
                'morning_peak': (8, 11),
                'evening_peak': (17, 22),
                'peak_multiplier': 2.2,
                'base_multiplier': 0.8
            },
            'north': {  # Washermanpet, Royapuram
                'morning_peak': (6, 9),
                'evening_peak': (16, 19),
                'peak_multiplier': 1.5,
                'base_multiplier': 1.0
            },
            'south': {  # Tambaram, Chromepet
                'morning_peak': (7, 10),
                'evening_peak': (17, 20),
                'peak_multiplier': 1.7,
                'base_multiplier': 0.9
            }
        }
        
        # Day of week factors
        self.day_factors = {
            0: 1.1,  # Monday - high
            1: 1.0,  # Tuesday
            2: 1.0,  # Wednesday
            3: 1.0,  # Thursday
            4: 1.2,  # Friday - high
            5: 0.7,  # Saturday - low
            6: 0.6,  # Sunday - lowest
        }
        
        # Special events/holidays
        self.holiday_factor = 0.5
    
    def predict_traffic(self, hour: int, day_of_week: int = None, 
                       area: str = 'central', is_holiday: bool = False) -> Dict:
        """
        Predict traffic conditions
        
        Returns:
            - traffic_index: 0-1 scale (0=free flow, 1=heavily congested)
            - speed_factor: multiplier for average speed
            - delay_minutes: expected delay per 10km
        """
        if day_of_week is None:
            day_of_week = datetime.now().weekday()
        
        pattern = self.area_traffic_patterns.get(area, self.area_traffic_patterns['central'])
        
        # Calculate base traffic index
        morning_peak = pattern['morning_peak']
        evening_peak = pattern['evening_peak']
        
        if morning_peak[0] <= hour <= morning_peak[1]:
            base_index = 0.8  # Morning peak
            period = 'morning_peak'
        elif evening_peak[0] <= hour <= evening_peak[1]:
            base_index = 0.9  # Evening peak (usually worse)
            period = 'evening_peak'
        elif 11 <= hour <= 16:
            base_index = 0.5  # Midday
            period = 'midday'
        elif 21 <= hour or hour <= 5:
            base_index = 0.2  # Night
            period = 'night'
        else:
            base_index = 0.4  # Off-peak
            period = 'off_peak'
        
        # Apply day factor
        day_factor = self.day_factors.get(day_of_week, 1.0)
        
        # Apply holiday factor
        if is_holiday:
            day_factor *= self.holiday_factor
        
        # Calculate final traffic index
        traffic_index = min(1.0, base_index * day_factor)
        
        # Calculate speed factor (inverse of traffic)
        speed_factor = max(0.3, 1.0 - (traffic_index * 0.7))
        
        # Calculate expected delay per 10km
        delay_minutes = traffic_index * 15  # Max 15 min delay per 10km
        
        return {
            'traffic_index': round(traffic_index, 2),
            'speed_factor': round(speed_factor, 2),
            'delay_minutes_per_10km': round(delay_minutes, 1),
            'period': period,
            'congestion_level': self._get_congestion_level(traffic_index),
            'recommendation': self._get_recommendation(traffic_index, period)
        }
    
    def _get_congestion_level(self, index: float) -> str:
        """Convert traffic index to human-readable level"""
        if index < 0.3:
            return 'free_flow'
        elif index < 0.5:
            return 'light'
        elif index < 0.7:
            return 'moderate'
        elif index < 0.85:
            return 'heavy'
        else:
            return 'severe'
    
    def _get_recommendation(self, index: float, period: str) -> str:
        """Get travel recommendation"""
        if index < 0.3:
            return "Excellent time to travel. Roads are clear."
        elif index < 0.5:
            return "Good time to travel. Minor delays possible."
        elif index < 0.7:
            return "Moderate traffic. Plan extra 10-15 minutes."
        elif index < 0.85:
            return "Heavy traffic. Consider delaying travel or using alternative routes."
        else:
            return "Severe congestion. Significant delays expected. Consider postponing if possible."
    
    def get_best_travel_time(self, start_hour: int = 6, end_hour: int = 22) -> List[Dict]:
        """Find the best times to travel today"""
        results = []
        current_day = datetime.now().weekday()
        
        for hour in range(start_hour, end_hour + 1):
            prediction = self.predict_traffic(hour, current_day)
            results.append({
                'hour': hour,
                'time': f"{hour:02d}:00",
                **prediction
            })
        
        # Sort by traffic index (lowest first)
        results.sort(key=lambda x: x['traffic_index'])
        
        return results
    
    def get_weekly_pattern(self, hour: int = 9) -> List[Dict]:
        """Get traffic pattern for a specific hour across the week"""
        days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        results = []
        
        for i, day_name in enumerate(days):
            prediction = self.predict_traffic(hour, i)
            results.append({
                'day': day_name,
                'day_number': i,
                **prediction
            })
        
        return results


class DelayPredictor:
    """Predict delays for specific routes based on historical patterns"""
    
    def __init__(self):
        # Simulated historical delay data
        self.route_delay_history = defaultdict(list)
        self._generate_historical_data()
    
    def _generate_historical_data(self):
        """Generate simulated historical delay data"""
        np.random.seed(42)
        
        # Generate delays for 100 routes
        for route_num in range(1, 101):
            route_id = str(route_num)
            
            # Each route has different delay patterns
            base_delay = np.random.uniform(2, 8)
            variance = np.random.uniform(1, 4)
            
            # Generate 30 days of data
            for _ in range(30):
                delay = max(0, np.random.normal(base_delay, variance))
                self.route_delay_history[route_id].append(delay)
    
    def predict_delay(self, route_number: str, time_of_day: int) -> Dict:
        """Predict delay for a specific route"""
        history = self.route_delay_history.get(route_number, [])
        
        if not history:
            # Default prediction for unknown routes
            base_delay = 5.0
        else:
            base_delay = np.mean(history)
        
        # Adjust for time of day
        if 8 <= time_of_day <= 10 or 17 <= time_of_day <= 20:
            time_factor = 1.5  # Peak hours
        elif 11 <= time_of_day <= 16:
            time_factor = 1.1  # Midday
        else:
            time_factor = 0.8  # Off-peak
        
        predicted_delay = base_delay * time_factor
        
        # Calculate confidence based on historical data
        if history:
            std_dev = np.std(history)
            confidence = max(0.5, 1 - (std_dev / base_delay) if base_delay > 0 else 0.5)
        else:
            confidence = 0.5
        
        return {
            'route_number': route_number,
            'predicted_delay_minutes': round(predicted_delay, 1),
            'confidence': round(confidence, 2),
            'delay_range': {
                'min': round(max(0, predicted_delay - 3), 1),
                'max': round(predicted_delay + 5, 1)
            },
            'time_factor': time_factor
        }
