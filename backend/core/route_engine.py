"""
Core Logic Engine - Route Finding and Ranking
"""

from typing import List, Dict, Optional
from collections import defaultdict
import heapq

class RouteEngine:
    def __init__(self, data_loader):
        self.data_loader = data_loader
        self.AVERAGE_SPEED_KMH = 20  # Average bus speed in Chennai traffic
        self.STOP_DELAY_MINUTES = 1  # Average delay per stop
    
    def _normalize_stop_name(self, name: str) -> str:
        """Strip coordinate suffixes and route tags for better matching"""
        import re
        name = name.lower().strip()
        # Remove patterns like (12.9910N), (Route M1), #2, etc.
        name = re.sub(r'\s*\([\d.]+n\)', '', name)
        name = re.sub(r'\s*\(route\s+\w+\)', '', name)
        name = re.sub(r'\s*#\d+', '', name)
        return name.strip()
    
    def _stops_match(self, query: str, stop_name: str) -> bool:
        """Check if query matches a stop name using normalized comparison"""
        q = query.lower().strip()
        s = stop_name.lower().strip()
        
        # Exact match
        if q == s:
            return True
        
        # Direct contains
        if q in s or s in q:
            return True
        
        # Normalized match (strip coordinates/route tags)
        q_norm = self._normalize_stop_name(q)
        s_norm = self._normalize_stop_name(s)
        
        if q_norm == s_norm:
            return True
        if q_norm in s_norm or s_norm in q_norm:
            return True
        
        # Match on road name (first part before comma or zone)
        q_road = q_norm.split(',')[0].strip()
        s_road = s_norm.split(',')[0].strip()
        
        if len(q_road) > 5 and len(s_road) > 5:
            if q_road == s_road or q_road in s_road or s_road in q_road:
                return True
        
        return False
    
    def _find_matching_stop(self, query: str) -> str:
        """Find the best matching stop name from the data"""
        query_lower = query.lower().strip()
        
        # First try exact match
        for stop_name in self.data_loader.stop_to_routes.keys():
            if stop_name == query_lower:
                return stop_name
        
        # Then try contains match
        for stop_name in self.data_loader.stop_to_routes.keys():
            if query_lower in stop_name or stop_name in query_lower:
                return stop_name
        
        # Try partial word match
        query_words = query_lower.split()
        for stop_name in self.data_loader.stop_to_routes.keys():
            if all(word in stop_name for word in query_words):
                return stop_name
        
        return query_lower
    
    def find_routes(self, source: str, destination: str, time_of_day: int = 12) -> List[Dict]:
        """Find all routes connecting source to destination"""
        results = []
        
        source_lower = source.lower().strip()
        dest_lower = destination.lower().strip()
        
        print(f"\n🔍 Searching routes: '{source}' -> '{destination}'")
        
        # Search through ALL routes for matching stops
        for route_num, route_stops in self.data_loader.route_stops_index.items():
            source_idx = None
            dest_idx = None
            source_stop_data = None
            dest_stop_data = None
            
            for idx, stop in enumerate(route_stops):
                # Match source (fuzzy)
                if source_idx is None:
                    if self._stops_match(source, stop['stop_name']):
                        source_idx = idx
                        source_stop_data = stop
                
                # Match destination (fuzzy) — keep searching for last match after source
                if self._stops_match(destination, stop['stop_name']):
                    if source_idx is not None and idx > source_idx:
                        dest_idx = idx
                        dest_stop_data = stop
            
            # Only valid if source comes before destination
            if source_idx is not None and dest_idx is not None and dest_idx > source_idx:
                stops_between = dest_idx - source_idx
                stops_list = route_stops[source_idx:dest_idx + 1]
                
                # Calculate distance
                distance = self.data_loader._calculate_route_distance(route_num, source_idx, dest_idx)
                if distance == 0:
                    distance = self._estimate_distance(stops_list)
                
                # Calculate estimated time
                estimated_time = self._calculate_travel_time(distance, stops_between, time_of_day)
                
                results.append({
                    'route_number': str(route_num),
                    'source_stop': source_stop_data['stop_name'],
                    'destination_stop': dest_stop_data['stop_name'],
                    'stops_between': stops_between,
                    'total_distance_km': round(distance, 2),
                    'estimated_time_minutes': round(estimated_time, 1),
                    'predicted_time_minutes': round(estimated_time, 1),
                    'delay_probability': 0.3,
                    'route_type': 'Direct',
                    'stops_list': [
                        {
                            'stop_name': s['stop_name'],
                            'latitude': s['latitude'],
                            'longitude': s['longitude'],
                            'sequence': s['sequence']
                        }
                        for s in stops_list
                    ]
                })
                print(f"   ✅ Route {route_num}: {stops_between} stops, {round(distance, 2)} km")
        
        if not results:
            print(f"   ❌ No direct routes found")
        
        # Sort by stops (fewer = better)
        results.sort(key=lambda x: x['stops_between'])
        
        return results
    
    def _validate_route(self, route_number: str, source: str, destination: str, time_of_day: int) -> Optional[Dict]:
        """
        Validate that a route goes from source to destination in correct direction
        """
        source_seq = self.data_loader.get_stop_sequence_in_route(route_number, source)
        dest_seq = self.data_loader.get_stop_sequence_in_route(route_number, destination)
        
        # Check if both stops exist and direction is correct
        if source_seq is None or dest_seq is None:
            return None
        
        if dest_seq <= source_seq:
            # Destination comes before source - wrong direction
            return None
        
        # Get stops between source and destination
        stops_list = self._get_stops_between(route_number, source, destination)
        stops_between = len(stops_list) - 1  # Exclude source
        
        # Calculate distance
        total_distance = self.data_loader.get_distance_between_stops(
            route_number, source, destination
        )
        
        # If distance not available from edges, estimate
        if total_distance == 0:
            total_distance = self._estimate_distance(stops_list)
        
        # Calculate estimated travel time
        estimated_time = self._calculate_travel_time(
            total_distance, stops_between, time_of_day
        )
        
        return {
            'route_number': route_number,
            'source_stop': source,
            'destination_stop': destination,
            'source_sequence': source_seq,
            'destination_sequence': dest_seq,
            'stops_between': stops_between,
            'total_distance_km': round(total_distance, 2),
            'estimated_time_minutes': round(estimated_time, 1),
            'stops_list': stops_list
        }
    
    def _get_stops_between(self, route_number: str, source: str, destination: str) -> List[Dict]:
        """Get all stops between source and destination inclusive"""
        all_stops = self.data_loader.get_route_stops(route_number)
        
        source_idx = None
        dest_idx = None
        
        for i, stop in enumerate(all_stops):
            if source_idx is None and self._stops_match(source, stop['stop_name']):
                source_idx = i
            if self._stops_match(destination, stop['stop_name']):
                if source_idx is not None and i > source_idx:
                    dest_idx = i
        
        if source_idx is not None and dest_idx is not None:
            return all_stops[source_idx:dest_idx + 1]
        
        return []
    
    def _estimate_distance(self, stops_list: List[Dict]) -> float:
        """Estimate distance using haversine formula between consecutive stops"""
        from math import radians, cos, sin, sqrt, atan2
        
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            return R * c
        
        total_distance = 0.0
        for i in range(len(stops_list) - 1):
            dist = haversine(
                stops_list[i]['latitude'], stops_list[i]['longitude'],
                stops_list[i+1]['latitude'], stops_list[i+1]['longitude']
            )
            total_distance += dist
        
        return total_distance
    
    def _calculate_travel_time(self, distance_km: float, num_stops: int, time_of_day: int) -> float:
        """
        Calculate estimated travel time considering:
        - Distance
        - Number of stops
        - Time of day (peak hours)
        """
        # Base travel time
        base_time = (distance_km / self.AVERAGE_SPEED_KMH) * 60  # minutes
        
        # Stop delays
        stop_delay = num_stops * self.STOP_DELAY_MINUTES
        
        # Traffic multiplier based on time of day
        traffic_multiplier = self._get_traffic_multiplier(time_of_day)
        
        total_time = (base_time * traffic_multiplier) + stop_delay
        
        return total_time
    
    def _get_traffic_multiplier(self, hour: int) -> float:
        """Get traffic multiplier based on time of day"""
        # Peak hours: 8-10 AM and 5-8 PM
        if 8 <= hour <= 10:
            return 1.5  # Morning peak
        elif 17 <= hour <= 20:
            return 1.7  # Evening peak
        elif 11 <= hour <= 16:
            return 1.2  # Moderate traffic
        elif 21 <= hour <= 23 or 0 <= hour <= 6:
            return 0.9  # Low traffic
        else:
            return 1.0  # Normal
    
    def rank_routes(self, routes: List[Dict]) -> List[Dict]:
        """
        Rank routes by priority:
        1. Direct routes first
        2. Fastest routes
        3. Least stops
        """
        def route_score(route):
            # Lower score = better
            score = 0
            
            # Route type priority
            if route.get('route_type') == 'Direct':
                score -= 100
            
            # Predicted time weight (most important)
            score += route.get('predicted_time_minutes', route.get('estimated_time_minutes', 0)) * 2
            
            # Number of stops weight
            score += route.get('stops_between', 0) * 0.5
            
            # Distance weight
            score += route.get('total_distance_km', 0) * 0.3
            
            return score
        
        ranked = sorted(routes, key=route_score)
        
        # Add ranking labels
        for i, route in enumerate(ranked):
            if i == 0:
                route['rank'] = 'Best Route'
                route['route_type'] = f"{route.get('route_type', '')} - Recommended"
            elif route.get('stops_between', 0) == min(r.get('stops_between', float('inf')) for r in ranked):
                route['route_type'] = f"{route.get('route_type', '')} - Least Stops"
            elif route.get('total_distance_km', 0) == min(r.get('total_distance_km', float('inf')) for r in ranked):
                route['route_type'] = f"{route.get('route_type', '')} - Shortest Distance"
        
        return ranked
    
    def get_route_segment(self, route_number: str, source: str, destination: str) -> Dict:
        """Get route segment between two stops for map visualization"""
        stops = self._get_stops_between(route_number, source, destination)
        
        if not stops:
            return {"error": "No stops found for this route segment"}
        
        path = [
            {"lat": stop['latitude'], "lng": stop['longitude']}
            for stop in stops
        ]
        
        markers = [
            {
                "position": {"lat": stop['latitude'], "lng": stop['longitude']},
                "title": stop['stop_name'],
                "sequence": stop['sequence'],
                "isSource": self._stops_match(source, stop['stop_name']),
                "isDestination": self._stops_match(destination, stop['stop_name'])
            }
            for stop in stops
        ]
        
        return {
            "route_number": route_number,
            "source": source,
            "destination": destination,
            "path": path,
            "markers": markers,
            "total_stops": len(stops)
        }
    
    def find_indirect_routes(self, source: str, destination: str, max_transfers: int = 1) -> List[Dict]:
        """
        Find routes with transfers (for future implementation)
        Uses BFS to find routes with minimum transfers
        """
        # This is a placeholder for future implementation
        # Would use graph search algorithms to find transfer points
        pass
    
    def filter_passed_buses(self, route_number: str, current_stop: str, direction: str = 'forward') -> bool:
        """
        Filter out buses that have already passed a stop
        Returns True if bus is still valid (hasn't passed)
        """
        # This would integrate with real-time bus tracking API
        # For now, returns True (bus is valid)
        return True
