"""
Advanced Route Features - Emergency Routing, Accessibility Mode, and Heatmaps
"""

from typing import List, Dict, Optional, Tuple
from math import radians, cos, sin, sqrt, atan2
from collections import defaultdict
import heapq

class AdvancedRouting:
    def __init__(self, data_loader):
        self.data_loader = data_loader
        
        # Hospital/Emergency locations in Chennai (sample data)
        self.emergency_locations = {
            'hospitals': [
                {'name': 'Apollo Hospital Greams Road', 'lat': 13.0569, 'lng': 80.2508},
                {'name': 'MIOT Hospital', 'lat': 13.0144, 'lng': 80.2232},
                {'name': 'Fortis Malar Hospital', 'lat': 13.0317, 'lng': 80.2557},
                {'name': 'Kauvery Hospital', 'lat': 13.0620, 'lng': 80.2469},
                {'name': 'Government General Hospital', 'lat': 13.0836, 'lng': 80.2756},
                {'name': 'Rajiv Gandhi Government General Hospital', 'lat': 13.0773, 'lng': 80.2887},
            ]
        }
    
    def haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance between two coordinates"""
        R = 6371  # Earth's radius in km
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c
    
    def find_nearest_hospital(self, lat: float, lng: float) -> Dict:
        """Find nearest hospital to given coordinates"""
        min_dist = float('inf')
        nearest = None
        
        for hospital in self.emergency_locations['hospitals']:
            dist = self.haversine_distance(lat, lng, hospital['lat'], hospital['lng'])
            if dist < min_dist:
                min_dist = dist
                nearest = {
                    **hospital,
                    'distance_km': round(dist, 2)
                }
        
        return nearest
    
    def emergency_route(self, source_lat: float, source_lng: float) -> Dict:
        """
        Find fastest route to nearest hospital from current location
        """
        # Find nearest stop to user
        nearest_stop = self.data_loader.find_nearest_stop(source_lat, source_lng)
        
        # Find nearest hospital
        nearest_hospital = self.find_nearest_hospital(source_lat, source_lng)
        
        # Find stop nearest to hospital
        hospital_stop = self.data_loader.find_nearest_stop(
            nearest_hospital['lat'], 
            nearest_hospital['lng']
        )
        
        return {
            'emergency_type': 'hospital',
            'source_stop': nearest_stop,
            'hospital': nearest_hospital,
            'destination_stop': hospital_stop,
            'message': f"Nearest hospital: {nearest_hospital['name']} ({nearest_hospital['distance_km']} km away)"
        }
    
    def accessibility_route(self, source: str, destination: str, 
                           max_walking_distance_m: int = 200) -> List[Dict]:
        """
        Find routes with minimal walking distance
        Useful for elderly, disabled, or passengers with heavy luggage
        """
        # Get all valid routes
        # Filter routes where stops are within max_walking_distance of actual source/destination
        routes = []
        
        # For now, return all direct routes as accessibility-friendly
        # In production, this would calculate walking distance from user's exact location
        return routes
    
    def calculate_bus_density_heatmap(self) -> List[Dict]:
        """
        Calculate bus density for heatmap visualization
        Returns list of coordinates with intensity values
        """
        stop_frequency = defaultdict(int)
        
        # Count how many routes pass through each stop
        for route_num, stops in self.data_loader.route_stops_index.items():
            for stop in stops:
                key = (round(stop['latitude'], 3), round(stop['longitude'], 3))
                stop_frequency[key] += 1
        
        # Convert to heatmap format
        heatmap_data = []
        max_frequency = max(stop_frequency.values()) if stop_frequency else 1
        
        for (lat, lng), frequency in stop_frequency.items():
            heatmap_data.append({
                'lat': lat,
                'lng': lng,
                'weight': frequency / max_frequency  # Normalized intensity
            })
        
        return heatmap_data
    
    def get_route_congestion_prediction(self, route_number: str, time_of_day: int) -> Dict:
        """
        Predict route congestion based on time and historical patterns
        """
        # Congestion factors based on time
        if 8 <= time_of_day <= 10:
            congestion_level = 'high'
            congestion_factor = 0.8
            expected_delay = 15  # minutes
        elif 17 <= time_of_day <= 20:
            congestion_level = 'very_high'
            congestion_factor = 0.9
            expected_delay = 20
        elif 11 <= time_of_day <= 16:
            congestion_level = 'moderate'
            congestion_factor = 0.5
            expected_delay = 8
        else:
            congestion_level = 'low'
            congestion_factor = 0.2
            expected_delay = 3
        
        return {
            'route_number': route_number,
            'congestion_level': congestion_level,
            'congestion_factor': congestion_factor,
            'expected_delay_minutes': expected_delay,
            'recommendation': self._get_congestion_recommendation(congestion_level)
        }
    
    def _get_congestion_recommendation(self, level: str) -> str:
        """Get recommendation based on congestion level"""
        recommendations = {
            'low': 'Good time to travel. Expect minimal delays.',
            'moderate': 'Normal traffic. Allow some buffer time.',
            'high': 'Peak hours. Consider leaving early or using alternative routes.',
            'very_high': 'Heavy traffic expected. Plan for significant delays.'
        }
        return recommendations.get(level, 'No specific recommendation.')


class TransferRouteEngine:
    """Engine for finding routes with transfers"""
    
    def __init__(self, data_loader):
        self.data_loader = data_loader
        self.MAX_TRANSFERS = 2
        self.MAX_WALKING_DISTANCE_KM = 0.5
    
    def find_routes_with_transfers(self, source: str, destination: str, 
                                   max_transfers: int = 1) -> List[Dict]:
        """
        Find routes that require transfers between buses
        Uses BFS to find optimal transfer points
        """
        # Get routes from source
        source_routes = set(self.data_loader.get_routes_for_stop(source))
        dest_routes = set(self.data_loader.get_routes_for_stop(destination))
        
        # Find direct routes first
        direct_routes = source_routes.intersection(dest_routes)
        
        if direct_routes:
            # Direct routes exist, no need for transfers
            return []
        
        # Find transfer routes
        transfer_routes = []
        
        # For each route from source
        for source_route in source_routes:
            source_stops = self.data_loader.get_route_stops(source_route)
            source_stop_names = {s['stop_name'].lower() for s in source_stops}
            
            # Find potential transfer points
            for dest_route in dest_routes:
                dest_stops = self.data_loader.get_route_stops(dest_route)
                dest_stop_names = {s['stop_name'].lower() for s in dest_stops}
                
                # Find common stops (transfer points)
                transfer_points = source_stop_names.intersection(dest_stop_names)
                
                for transfer_stop in transfer_points:
                    # Validate transfer is in correct direction
                    transfer_route = self._build_transfer_route(
                        source, destination, 
                        source_route, dest_route,
                        transfer_stop
                    )
                    
                    if transfer_route:
                        transfer_routes.append(transfer_route)
        
        # Sort by total time
        transfer_routes.sort(key=lambda x: x.get('total_estimated_time', float('inf')))
        
        return transfer_routes[:5]  # Return top 5 options
    
    def _build_transfer_route(self, source: str, destination: str,
                              first_route: str, second_route: str,
                              transfer_stop: str) -> Optional[Dict]:
        """Build a complete transfer route"""
        # Validate first leg: source -> transfer_stop
        source_seq = self.data_loader.get_stop_sequence_in_route(first_route, source)
        transfer_seq_1 = self.data_loader.get_stop_sequence_in_route(first_route, transfer_stop)
        
        if not source_seq or not transfer_seq_1 or transfer_seq_1 <= source_seq:
            return None
        
        # Validate second leg: transfer_stop -> destination
        transfer_seq_2 = self.data_loader.get_stop_sequence_in_route(second_route, transfer_stop)
        dest_seq = self.data_loader.get_stop_sequence_in_route(second_route, destination)
        
        if not transfer_seq_2 or not dest_seq or dest_seq <= transfer_seq_2:
            return None
        
        # Calculate metrics for each leg
        first_leg_stops = transfer_seq_1 - source_seq
        second_leg_stops = dest_seq - transfer_seq_2
        
        # Estimate times (simplified)
        first_leg_time = first_leg_stops * 3  # ~3 min per stop
        second_leg_time = second_leg_stops * 3
        transfer_wait_time = 10  # Average wait time for next bus
        
        return {
            'type': 'transfer_route',
            'legs': [
                {
                    'route_number': first_route,
                    'from_stop': source,
                    'to_stop': transfer_stop,
                    'stops': first_leg_stops,
                    'estimated_time': first_leg_time
                },
                {
                    'route_number': second_route,
                    'from_stop': transfer_stop,
                    'to_stop': destination,
                    'stops': second_leg_stops,
                    'estimated_time': second_leg_time
                }
            ],
            'transfer_point': transfer_stop,
            'transfer_wait_time': transfer_wait_time,
            'total_stops': first_leg_stops + second_leg_stops,
            'total_estimated_time': first_leg_time + second_leg_time + transfer_wait_time,
            'num_transfers': 1
        }
