"""
Data Layer - Load and manage CSV datasets
"""

import pandas as pd
import os
from typing import List, Dict, Optional
from collections import defaultdict
from urllib.parse import unquote

class DataLoader:
    def __init__(self):
        # Dynamically determine the base path (project root)
        # Structure: root/backend/core/data_loader.py
        # We need to go up 3 levels to reach root
        current_file = os.path.abspath(__file__)
        core_dir = os.path.dirname(current_file)
        backend_dir = os.path.dirname(core_dir)
        root_dir = os.path.dirname(backend_dir)
        
        self.base_path = os.getenv("DATA_BASE_PATH", root_dir)
            
        print(f"📂 Initializing DataLoader with base path: {self.base_path}")
        self.stops_df = None
        self.route_stops_df = None
        self.route_edges_df = None
        self.bus_stops_df = None  # Real stop names
        self.graph = defaultdict(list)
        self.route_graph = defaultdict(dict)
        self._loaded = False
        self._load_data()
    
    def _load_data(self):
        """Load all CSV datasets into memory"""
        try:
            # Load stops dataset
            stops_path = os.path.join(self.base_path, "cleaned_all_stops.csv")
            self.stops_df = pd.read_csv(stops_path)
            self.stops_df['stop_name_lower'] = self.stops_df['stop_name'].str.lower()
            
            # Load chennai_bus_stops.csv with REAL stop names
            bus_stops_path = os.path.join(self.base_path, "chennai_bus_stops.csv")
            if os.path.exists(bus_stops_path):
                self.bus_stops_df = pd.read_csv(bus_stops_path, header=None, 
                                                 names=['stop_id', 'stop_name', 'latitude', 'longitude'])
                # Decode URL-encoded names and clean them
                self.bus_stops_df['stop_name'] = self.bus_stops_df['stop_name'].apply(
                    lambda x: self._decode_stop_name(x) if pd.notna(x) else ''
                )
                # Filter out empty names
                self.bus_stops_df = self.bus_stops_df[self.bus_stops_df['stop_name'].str.len() > 0]
                print(f"   - Loaded real stop names: {len(self.bus_stops_df)}")
            
            # Load route ordered stops dataset
            route_stops_path = os.path.join(self.base_path, "route_stop_ordered.csv")
            self.route_stops_df = pd.read_csv(route_stops_path)
            
            # Load route edges dataset
            edges_path = os.path.join(self.base_path, "route_edges.csv")
            self.route_edges_df = pd.read_csv(edges_path)
            
            # Build graph structures
            self._build_stop_name_mapping()
            self._build_graph()
            self._build_route_index()
            
            self._loaded = True
            print(f"✅ Data loaded successfully!")
            print(f"   - Stops: {len(self.stops_df)}")
            print(f"   - Route Stops: {len(self.route_stops_df)}")
            print(f"   - Route Edges: {len(self.route_edges_df)}")
            
        except Exception as e:
            print(f"❌ Error loading data: {e}")
            import traceback
            traceback.print_exc()
            self._loaded = False
    
    def _decode_stop_name(self, name: str) -> str:
        """Decode URL-encoded stop names"""
        if not name or pd.isna(name):
            return ''
        # Replace %20% with space (custom encoding in your data)
        name = str(name).replace('%20%', ' ')
        # Standard URL decode
        name = unquote(name)
        # Clean up extra spaces
        name = ' '.join(name.split())
        return name.strip()
    
    def _build_stop_name_mapping(self):
        """Build mapping between stop IDs and real names from chennai_bus_stops.csv"""
        self.stop_id_to_name = {}
        self.stop_name_to_id = {}
        self.stop_id_to_coords = {}
        
        # First, use chennai_bus_stops.csv for real names
        if self.bus_stops_df is not None:
            for _, row in self.bus_stops_df.iterrows():
                stop_id = str(row['stop_id'])
                stop_name = str(row['stop_name']).strip()
                if stop_name and stop_name != 'nan':
                    self.stop_id_to_name[stop_id] = stop_name
                    self.stop_name_to_id[stop_name.lower()] = stop_id
                    if pd.notna(row['latitude']) and pd.notna(row['longitude']):
                        self.stop_id_to_coords[stop_id] = {
                            'lat': row['latitude'],
                            'lng': row['longitude']
                        }
        
        print(f"   - Built stop name mapping: {len(self.stop_id_to_name)} real names")
    
    def _build_graph(self):
        """Build adjacency graph from route edges"""
        for _, row in self.route_edges_df.iterrows():
            route = str(row['route_number'])
            from_stop = row['from_stop']
            to_stop = row['to_stop']
            distance = row['distance_km']
            
            # Add edge to graph
            self.graph[from_stop].append({
                'to_stop': to_stop,
                'route': route,
                'distance': distance
            })
            
            # Build route-specific graph
            if route not in self.route_graph:
                self.route_graph[route] = defaultdict(list)
            self.route_graph[route][from_stop].append({
                'to_stop': to_stop,
                'distance': distance
            })
    
    def _build_route_index(self):
        """Build index for quick route lookups"""
        self.stop_to_routes = defaultdict(set)
        self.route_stops_index = defaultdict(list)
        
        for _, row in self.route_stops_df.iterrows():
            route = str(row['route_number'])
            
            # Get the stop_id and stop_name directly from route_stop_ordered.csv
            stop_id = str(row['stop_id']).strip()
            
            # Use stop_name from the CSV (which has been cleaned by clean_data.py)
            stop_name = str(row.get('stop_name', '')).strip()
            if not stop_name or stop_name == 'nan':
                stop_name = self.stop_id_to_name.get(stop_id, f"Stop_{stop_id}")
            
            sequence = row['stop_sequence']
            
            # Index by stop name (lowercase) for route lookups
            self.stop_to_routes[stop_name.lower()].add(route)
            self.stop_to_routes[stop_id].add(route)
            
            self.route_stops_index[route].append({
                'stop_id': stop_id,
                'stop_name': stop_name,
                'sequence': sequence,
                'latitude': row['latitude'],
                'longitude': row['longitude']
            })
        
        # Sort by sequence
        for route in self.route_stops_index:
            self.route_stops_index[route].sort(key=lambda x: x['sequence'])
        
        # Debug: Print sample of stop names
        all_names = list(set(
            stop['stop_name'] for stops in self.route_stops_index.values() for stop in stops
        ))
        print(f"   - Total routes indexed: {len(self.route_stops_index)}")
        print(f"   - Sample stop names: {all_names[:5]}")
    
    def is_loaded(self) -> bool:
        """Check if data is loaded"""
        return self._loaded
    
    def get_stops(self, query: str = None) -> List[Dict]:
        """Get all stops or filter by query"""
        if query:
            query_lower = query.lower()
            filtered = self.stops_df[
                self.stops_df['stop_name_lower'].str.contains(query_lower, na=False)
            ]
        else:
            filtered = self.stops_df
        
        return filtered[['stop_id', 'stop_name', 'latitude', 'longitude']].to_dict('records')
    
    def get_stop_suggestions(self, query: str, limit: int = 10) -> List[Dict]:
        """Get autocomplete suggestions for stop names with routes"""
        query_lower = query.lower().strip()
        suggestions = []
        seen_names = set()
        
        # Primary source: search in route_stops_index (cleaned names)
        for route_num, route_stops in self.route_stops_index.items():
            for stop in route_stops:
                stop_name = stop['stop_name']
                stop_name_lower = stop_name.lower()
                
                if query_lower in stop_name_lower and stop_name_lower not in seen_names:
                    # Collect all routes for this stop
                    routes = list(self.stop_to_routes.get(stop_name_lower, set()))
                    
                    seen_names.add(stop_name_lower)
                    suggestions.append({
                        'stop_id': stop['stop_id'],
                        'stop_name': stop_name,
                        'latitude': stop['latitude'],
                        'longitude': stop['longitude'],
                        'routes': routes[:5]
                    })
                    
                    if len(suggestions) >= limit:
                        break
            if len(suggestions) >= limit:
                break
        
        # Fallback: also search in stops_df if not enough
        if len(suggestions) < limit and self.stops_df is not None:
            filtered = self.stops_df[
                self.stops_df['stop_name_lower'].str.contains(query_lower, na=False)
            ]
            
            for _, row in filtered.iterrows():
                stop_id = str(row['stop_id'])
                stop_name = self.stop_id_to_name.get(stop_id, row['stop_name'])
                stop_name_lower = stop_name.lower()
                
                if stop_name_lower not in seen_names:
                    routes = list(self.stop_to_routes.get(stop_name_lower, set()))
                    if not routes:
                        routes = list(self.stop_to_routes.get(stop_id, set()))
                    
                    seen_names.add(stop_name_lower)
                    suggestions.append({
                        'stop_id': stop_id,
                        'stop_name': stop_name,
                        'latitude': row['latitude'],
                        'longitude': row['longitude'],
                        'routes': routes[:5]
                    })
                    
                    if len(suggestions) >= limit:
                        break
        
        # Sort by number of routes (more routes = more important stop)
        suggestions.sort(key=lambda x: -len(x.get('routes', [])))
        
        return suggestions[:limit]
    
    def get_routes_for_stop(self, stop_name: str) -> set:
        """Get all routes passing through a stop"""
        import re
        stop_lower = stop_name.lower().strip()
        
        # Try exact match first
        if stop_lower in self.stop_to_routes:
            return self.stop_to_routes[stop_lower]
        
        # Try partial match - search in all keys
        for key, routes in self.stop_to_routes.items():
            if stop_lower in key or key in stop_lower:
                return routes
        
        # Try normalized match (strip coordinate suffixes)
        def normalize(name):
            name = name.lower().strip()
            name = re.sub(r'\s*\([\d.]+n\)', '', name)
            name = re.sub(r'\s*\(route\s+\w+\)', '', name)
            name = re.sub(r'\s*#\d+', '', name)
            return name.strip()
        
        stop_norm = normalize(stop_lower)
        all_routes = set()
        for key, routes in self.stop_to_routes.items():
            key_norm = normalize(key)
            if stop_norm == key_norm or stop_norm in key_norm or key_norm in stop_norm:
                all_routes.update(routes)
        
        if all_routes:
            return all_routes
        
        # Try road name match (first part before comma)
        stop_road = stop_norm.split(',')[0].strip()
        if len(stop_road) > 5:
            for key, routes in self.stop_to_routes.items():
                key_road = normalize(key).split(',')[0].strip()
                if stop_road == key_road:
                    all_routes.update(routes)
        
        return all_routes
    
    def get_route_stops(self, route_number: str) -> List[Dict]:
        """Get all stops for a route in order"""
        return self.route_stops_index.get(str(route_number), [])
    
    def get_route_coordinates(self, route_number: str) -> Dict:
        """Get all coordinates for a route for map visualization"""
        stops = self.get_route_stops(route_number)
        if not stops:
            return None
        
        coordinates = [
            {"lat": stop['latitude'], "lng": stop['longitude']}
            for stop in stops
        ]
        
        markers = [
            {
                "position": {"lat": stop['latitude'], "lng": stop['longitude']},
                "title": stop['stop_name'],
                "sequence": stop['sequence']
            }
            for stop in stops
        ]
        
        return {
            "route_number": route_number,
            "path": coordinates,
            "markers": markers,
            "total_stops": len(stops)
        }
    
    def get_stop_sequence_in_route(self, route_number: str, stop_name: str) -> Optional[int]:
        """Get the sequence number of a stop in a route"""
        stops = self.get_route_stops(str(route_number))
        stop_name_lower = stop_name.lower().strip()
        
        for stop in stops:
            sn = stop['stop_name'].lower()
            if sn == stop_name_lower or stop_name_lower in sn or sn in stop_name_lower:
                return stop['sequence']
        
        return None
    
    def get_distance_between_stops(self, route_number: str, from_stop: str, to_stop: str) -> float:
        """Calculate total distance between two stops on a route"""
        stops = self.route_stops_index.get(str(route_number), [])
        from_seq = None
        to_seq = None
        
        from_stop_lower = from_stop.lower()
        to_stop_lower = to_stop.lower()
        
        for stop in stops:
            if stop['stop_name'].lower() == from_stop_lower:
                from_seq = stop['sequence']
            if stop['stop_name'].lower() == to_stop_lower:
                to_seq = stop['sequence']
        
        if from_seq is None or to_seq is None:
            return 0.0
        
        # Get edges for this route
        route_edges = self.route_edges_df[
            self.route_edges_df['route_number'].astype(str) == str(route_number)
        ]
        
        total_distance = 0.0
        stops_in_route = {s['stop_name'].lower(): s['sequence'] for s in stops}
        
        for _, edge in route_edges.iterrows():
            edge_from = edge['from_stop'].lower() if isinstance(edge['from_stop'], str) else str(edge['from_stop'])
            edge_to = edge['to_stop'].lower() if isinstance(edge['to_stop'], str) else str(edge['to_stop'])
            
            from_edge_seq = stops_in_route.get(edge_from)
            to_edge_seq = stops_in_route.get(edge_to)
            
            if from_edge_seq and to_edge_seq:
                if from_seq <= from_edge_seq < to_seq:
                    total_distance += edge['distance_km']
        
        return round(total_distance, 2)
    
    def get_total_stops(self) -> int:
        """Get total number of unique stops"""
        return len(self.stops_df) if self.stops_df is not None else 0
    
    def get_total_routes(self) -> int:
        """Get total number of routes"""
        return len(self.route_stops_index)
    
    def get_total_edges(self) -> int:
        """Get total number of route edges"""
        return len(self.route_edges_df) if self.route_edges_df is not None else 0
    
    def find_nearest_stop(self, lat: float, lon: float) -> Dict:
        """Find nearest stop to given coordinates"""
        from math import radians, cos, sin, sqrt, atan2
        
        def haversine(lat1, lon1, lat2, lon2):
            R = 6371  # Earth's radius in km
            lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
            dlat = lat2 - lat1
            dlon = lon2 - lon1
            a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
            c = 2 * atan2(sqrt(a), sqrt(1-a))
            return R * c
        
        min_dist = float('inf')
        nearest_stop = None
        
        for _, row in self.stops_df.iterrows():
            dist = haversine(lat, lon, row['latitude'], row['longitude'])
            if dist < min_dist:
                min_dist = dist
                nearest_stop = {
                    'stop_id': row['stop_id'],
                    'stop_name': row['stop_name'],
                    'latitude': row['latitude'],
                    'longitude': row['longitude'],
                    'distance_km': round(dist, 3)
                }
        
        return nearest_stop
    
    def find_stop_by_name(self, name: str) -> Optional[Dict]:
        """Find a stop by name with fuzzy matching"""
        name_lower = name.lower().strip()
        
        # Search in stops_df
        if self.stops_df is not None:
            # Exact match first
            exact = self.stops_df[self.stops_df['stop_name_lower'] == name_lower]
            if not exact.empty:
                row = exact.iloc[0]
                return {
                    'stop_id': str(row['stop_id']),
                    'stop_name': row['stop_name'],
                    'latitude': row['latitude'],
                    'longitude': row['longitude']
                }
            
            # Partial match
            partial = self.stops_df[self.stops_df['stop_name_lower'].str.contains(name_lower, na=False)]
            if not partial.empty:
                row = partial.iloc[0]
                return {
                    'stop_id': str(row['stop_id']),
                    'stop_name': row['stop_name'],
                    'latitude': row['latitude'],
                    'longitude': row['longitude']
                }
        
        # Also search in route_stops_index
        for route, stops in self.route_stops_index.items():
            for stop in stops:
                stop_name_lower = stop['stop_name'].lower()
                if name_lower == stop_name_lower or name_lower in stop_name_lower or stop_name_lower in name_lower:
                    return {
                        'stop_id': str(stop['stop_id']),
                        'stop_name': stop['stop_name'],
                        'latitude': stop['latitude'],
                        'longitude': stop['longitude']
                    }
        
        return None

    def get_stop_id_by_name(self, name: str) -> Optional[str]:
        """Get stop_id from stop name"""
        stop = self.find_stop_by_name(name)
        return stop.get('stop_id') if stop else None
    
    def find_routes_between_stops(self, from_stop_name: str, to_stop_name: str) -> List[Dict]:
        """Find all routes connecting two stops"""
        routes = []
        
        from_stop_lower = from_stop_name.lower().strip()
        to_stop_lower = to_stop_name.lower().strip()
        
        print(f"🔍 Finding routes from '{from_stop_name}' to '{to_stop_name}'")
        
        # Search through all routes
        for route_num, route_stops in self.route_stops_index.items():
            from_idx = None
            to_idx = None
            from_stop_data = None
            to_stop_data = None
            
            # Find both stops in this route
            for idx, stop in enumerate(route_stops):
                stop_name_lower = stop['stop_name'].lower()
                
                # Check for from_stop (fuzzy match)
                if from_idx is None:
                    if (from_stop_lower == stop_name_lower or 
                        from_stop_lower in stop_name_lower or 
                        stop_name_lower in from_stop_lower):
                        from_idx = idx
                        from_stop_data = stop
                
                # Check for to_stop (fuzzy match)
                if to_idx is None:
                    if (to_stop_lower == stop_name_lower or 
                        to_stop_lower in stop_name_lower or 
                        stop_name_lower in to_stop_lower):
                        to_idx = idx
                        to_stop_data = stop
            
            # If both stops found and destination is after source
            if from_idx is not None and to_idx is not None and to_idx > from_idx:
                # Calculate distance
                distance = self._calculate_route_distance(route_num, from_idx, to_idx)
                
                routes.append({
                    'route_number': route_num,
                    'from_stop': from_stop_data,
                    'to_stop': to_stop_data,
                    'from_sequence': from_idx + 1,
                    'to_sequence': to_idx + 1,
                    'stops_count': to_idx - from_idx,
                    'distance_km': distance,
                    'stops': route_stops[from_idx:to_idx+1]
                })
        
        print(f"   Found {len(routes)} direct routes")
        
        # Sort by number of stops (fewer is better)
        routes.sort(key=lambda x: x['stops_count'])
        
        return routes
    
    def _calculate_route_distance(self, route_number: str, from_idx: int, to_idx: int) -> float:
        """Calculate distance between two stops on a route"""
        route_stops = self.route_stops_index.get(str(route_number), [])
        
        if not route_stops or from_idx >= len(route_stops) or to_idx >= len(route_stops):
            return 0.0
        
        # Get stop IDs for the segment
        stop_ids = [str(route_stops[i]['stop_id']) for i in range(from_idx, to_idx + 1)]
        
        # Sum up distances from route_edges
        total_distance = 0.0
        route_edges = self.route_edges_df[
            self.route_edges_df['route_number'].astype(str) == str(route_number)
        ]
        
        for i in range(len(stop_ids) - 1):
            from_id = stop_ids[i]
            to_id = stop_ids[i + 1]
            
            # Find edge
            edge = route_edges[
                (route_edges['from_stop'].astype(str) == from_id) &
                (route_edges['to_stop'].astype(str) == to_id)
            ]
            
            if not edge.empty:
                total_distance += edge['distance_km'].iloc[0]
            else:
                # Estimate ~1km per stop if edge not found
                total_distance += 1.0
        
        return round(total_distance, 2)
