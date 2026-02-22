#!/usr/bin/env python3
"""
Stop Name Resolver
Finds real names for stops that only have stop_id as their name
Uses reverse geocoding with OpenStreetMap Nominatim API
"""

import pandas as pd
import requests
import time
import os
import json
from typing import Optional

class StopNameResolver:
    def __init__(self):
        self.base_path = "/Users/jerimothimmanuel/chennai_mtc_project"
        self.cache_file = os.path.join(self.base_path, "backend/data/geocode_cache.json")
        self.cache = self._load_cache()
        
    def _load_cache(self) -> dict:
        """Load geocoding cache to avoid repeated API calls"""
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_cache(self):
        """Save geocoding cache"""
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        with open(self.cache_file, 'w') as f:
            json.dump(self.cache, f, indent=2)
    
    def reverse_geocode(self, lat: float, lon: float) -> Optional[str]:
        """Get unique place name from coordinates using Nominatim"""
        cache_key = f"{lat:.6f},{lon:.6f}"
        
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        try:
            url = f"https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'zoom': 18,  # Street level
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'ChennaiMTCProject/1.0 (educational project)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                address = data.get('address', {})
                
                # Build a unique name with multiple components
                name = self._build_unique_stop_name(address, lat, lon)
                
                if name:
                    self.cache[cache_key] = name
                    self._save_cache()
                    return name
            
            # Rate limiting - Nominatim requires 1 second between requests
            time.sleep(1)
            
        except Exception as e:
            print(f"   Geocoding error for {lat}, {lon}: {e}")
        
        return None
    
    def _build_unique_stop_name(self, address: dict, lat: float, lon: float) -> str:
        """
        Build a unique stop name using multiple address components
        Format: [Road/Street] - [Landmark/Area/Neighbourhood], [Suburb/City]
        """
        components = []
        
        # Primary: Road or street name
        road = address.get('road') or address.get('street')
        
        # Secondary: Landmark, amenity, or building
        landmark = (
            address.get('amenity') or 
            address.get('building') or 
            address.get('shop') or
            address.get('tourism') or
            address.get('leisure')
        )
        
        # Area: neighbourhood, suburb, or locality
        area = (
            address.get('neighbourhood') or 
            address.get('suburb') or 
            address.get('locality') or
            address.get('village')
        )
        
        # City or town
        city = (
            address.get('city') or 
            address.get('town') or 
            address.get('city_district') or
            address.get('state_district')
        )
        
        # Build the name
        if road:
            components.append(road)
        
        if landmark and landmark != road:
            components.append(f"nr {landmark}")  # "nr" = near
        elif area and area != road:
            components.append(area)
        
        # Add city/suburb for uniqueness if we have few components
        if len(components) < 2 and city:
            components.append(city)
        elif len(components) == 1 and area and area not in components:
            components.append(area)
        
        # If still not unique enough, add partial coordinates
        if len(components) < 2:
            # Use last 3 digits of coordinates for micro-location
            coord_suffix = f"({lat:.3f},{lon:.3f})"[-12:]
            if components:
                components.append(coord_suffix)
            else:
                components.append(f"Stop {coord_suffix}")
        
        # Join components
        if len(components) >= 2:
            name = f"{components[0]} - {', '.join(components[1:])}"
        else:
            name = components[0] if components else None
        
        return name
    
    def is_stop_id_name(self, name: str) -> bool:
        """Check if the stop name is just a stop_id"""
        if not name:
            return True
        name = str(name).strip()
        # Check if it starts with "Stop_" or is purely numeric
        return name.startswith('Stop_') or name.isdigit() or name.startswith('stop_')
    
    def _make_names_unique(self, df, csv_path):
        """Ensure all stop names are unique by adding area/route suffixes"""
        print("\n🔧 Making stop names unique...")
        
        # Find duplicate names
        name_counts = df['stop_name'].value_counts()
        duplicates = name_counts[name_counts > 1].index.tolist()
        
        if not duplicates:
            print("   ✅ All names are already unique!")
            return
        
        print(f"   Found {len(duplicates)} duplicate names to fix")
        
        changes = 0
        for dup_name in duplicates:
            # Skip Stop_xxx names - they'll be geocoded
            if self.is_stop_id_name(dup_name):
                continue
                
            # Get all rows with this name
            mask = df['stop_name'] == dup_name
            dup_rows = df[mask]
            
            for idx, (row_idx, row) in enumerate(dup_rows.iterrows()):
                if idx == 0:
                    continue  # Keep first one as-is
                
                # Create unique suffix based on route and coordinates
                route = str(row.get('route_number', ''))
                lat = row.get('latitude', 0)
                lon = row.get('longitude', 0)
                
                # Try different uniqueness strategies
                if route:
                    new_name = f"{dup_name} (Route {route})"
                else:
                    # Use coordinate-based suffix
                    new_name = f"{dup_name} ({lat:.4f})"
                
                # If still not unique, add sequence
                existing_names = df['stop_name'].tolist()
                counter = 2
                base_name = new_name
                while new_name in existing_names:
                    new_name = f"{base_name} #{counter}"
                    counter += 1
                
                df.at[row_idx, 'stop_name'] = new_name
                changes += 1
        
        # Save updated file
        df.to_csv(csv_path, index=False)
        print(f"   ✅ Fixed {changes} duplicate names")

    def resolve_stop_names(self, max_stops: int = 500):
        """
        Resolve real names for stops that only have IDs as names
        """
        print("🔍 Stop Name Resolver")
        print("=" * 50)
        
        # Load datasets
        route_stops_path = os.path.join(self.base_path, "route_stop_ordered.csv")
        bus_stops_path = os.path.join(self.base_path, "bus_stops.csv")
        
        route_stops_df = pd.read_csv(route_stops_path)
        
        # Also load bus_stops.csv for reference
        bus_stops_df = None
        if os.path.exists(bus_stops_path):
            bus_stops_df = pd.read_csv(bus_stops_path)
            print(f"✅ Loaded {len(bus_stops_df)} stops from bus_stops.csv")
        
        # Create a mapping from stop_id to known names from bus_stops.csv
        known_names = {}
        if bus_stops_df is not None:
            for _, row in bus_stops_df.iterrows():
                stop_id = str(row['stop_id'])
                stop_name = str(row['stop_name'])
                if not self.is_stop_id_name(stop_name):
                    known_names[stop_id] = stop_name
        
        print(f"📚 Found {len(known_names)} stops with known names")
        
        # Find stops that need name resolution
        stops_to_resolve = []
        for _, row in route_stops_df.iterrows():
            stop_id = str(row['stop_id'])
            stop_name = str(row.get('stop_name', ''))
            
            if self.is_stop_id_name(stop_name):
                # Check if we already know the name from bus_stops.csv
                if stop_id in known_names:
                    stops_to_resolve.append({
                        'stop_id': stop_id,
                        'current_name': stop_name,
                        'new_name': known_names[stop_id],
                        'source': 'bus_stops.csv'
                    })
                else:
                    # Need to geocode
                    lat = row.get('latitude', row.get('lat', 0))
                    lon = row.get('longitude', row.get('lon', 0))
                    if lat and lon and lat != 0 and lon != 0:
                        stops_to_resolve.append({
                            'stop_id': stop_id,
                            'current_name': stop_name,
                            'lat': lat,
                            'lon': lon,
                            'source': 'geocode'
                        })
        
        print(f"\n🔄 Found {len(stops_to_resolve)} stops needing name resolution")
        
        # Process stops
        resolved_count = 0
        geocode_count = 0
        name_mapping = {}
        
        for i, stop in enumerate(stops_to_resolve[:max_stops]):
            stop_id = stop['stop_id']
            
            if stop['source'] == 'bus_stops.csv':
                name_mapping[stop_id] = stop['new_name']
                resolved_count += 1
            else:
                # Geocode
                if geocode_count < 100:  # Limit geocoding calls
                    print(f"   [{i+1}/{len(stops_to_resolve)}] Geocoding stop {stop_id}...", end=" ")
                    new_name = self.reverse_geocode(stop['lat'], stop['lon'])
                    if new_name:
                        name_mapping[stop_id] = new_name
                        print(f"✅ {new_name}")
                        resolved_count += 1
                    else:
                        print("❌ No name found")
                    geocode_count += 1
                    time.sleep(1.1)  # Rate limiting
        
        print(f"\n✅ Resolved {resolved_count} stop names")
        
        # Update the route_stops_ordered.csv
        if name_mapping:
            print("\n📝 Updating route_stop_ordered.csv...")
            
            # Check if 'stop_name' column exists, if not create it
            if 'stop_name' not in route_stops_df.columns:
                route_stops_df['stop_name'] = route_stops_df['stop_id'].apply(lambda x: f"Stop_{x}")
            
            # Update names
            updated_count = 0
            for idx, row in route_stops_df.iterrows():
                stop_id = str(row['stop_id'])
                if stop_id in name_mapping:
                    route_stops_df.at[idx, 'stop_name'] = name_mapping[stop_id]
                    updated_count += 1
            
            # Save updated file
            backup_path = route_stops_path.replace('.csv', '_backup.csv')
            route_stops_df.to_csv(backup_path, index=False)
            route_stops_df.to_csv(route_stops_path, index=False)
            
            print(f"✅ Updated {updated_count} stop names")
            print(f"💾 Backup saved to: {backup_path}")
            print(f"💾 Updated file: {route_stops_path}")
        
        # Also save the name mapping for reference
        mapping_path = os.path.join(self.base_path, "backend/data/stop_name_mapping.json")
        os.makedirs(os.path.dirname(mapping_path), exist_ok=True)
        with open(mapping_path, 'w') as f:
            json.dump(name_mapping, f, indent=2)
        print(f"💾 Name mapping saved to: {mapping_path}")
        
        # After geocoding, make names unique
        route_stops_df = pd.read_csv(route_stops_path)
        self._make_names_unique(route_stops_df, route_stops_path)
        
        return name_mapping
    
    def update_from_bus_stops(self):
        """
        Quick update: Just use bus_stops.csv to fill in names
        No geocoding required
        """
        print("🔍 Quick Stop Name Update (from bus_stops.csv)")
        print("=" * 50)
        
        route_stops_path = os.path.join(self.base_path, "route_stop_ordered.csv")
        
        # Try multiple possible locations for bus_stops.csv
        possible_paths = [
            os.path.join(self.base_path, "bus_stops.csv"),
            os.path.join(self.base_path, "data", "bus_stops.csv"),
            os.path.join(self.base_path, "backend", "data", "bus_stops.csv"),
        ]
        
        bus_stops_path = None
        for path in possible_paths:
            if os.path.exists(path):
                bus_stops_path = path
                break
        
        route_stops_df = pd.read_csv(route_stops_path)
        
        if bus_stops_path is None:
            print("❌ bus_stops.csv not found! Trying to use route_stop_ordered.csv itself...")
            # Use the stop names that are already good in route_stop_ordered.csv
            self._update_from_existing_good_names(route_stops_df)
            return
        
        bus_stops_df = pd.read_csv(bus_stops_path)
        
        # Create stop_id -> name mapping from bus_stops
        id_to_name = {}
        for _, row in bus_stops_df.iterrows():
            stop_id = str(row['stop_id'])
            stop_name = str(row['stop_name']).strip()
            if stop_name and stop_name != 'nan' and not self.is_stop_id_name(stop_name):
                id_to_name[stop_id] = stop_name
        
        print(f"📚 Found {len(id_to_name)} named stops in bus_stops.csv")
        
        # Check current state
        if 'stop_name' not in route_stops_df.columns:
            route_stops_df['stop_name'] = ''
        
        # Count stops needing update
        needs_update = 0
        for _, row in route_stops_df.iterrows():
            if self.is_stop_id_name(str(row.get('stop_name', ''))):
                needs_update += 1
        
        print(f"🔄 {needs_update} stops need name updates")
        
        # Update names
        updated = 0
        still_missing = []
        for idx, row in route_stops_df.iterrows():
            stop_id = str(row['stop_id'])
            current_name = str(row.get('stop_name', ''))
            
            if self.is_stop_id_name(current_name):
                if stop_id in id_to_name:
                    route_stops_df.at[idx, 'stop_name'] = id_to_name[stop_id]
                    updated += 1
                else:
                    still_missing.append({
                        'stop_id': stop_id,
                        'lat': row.get('latitude', 0),
                        'lon': row.get('longitude', 0)
                    })
        
        # Save
        backup_path = route_stops_path.replace('.csv', '_backup.csv')
        route_stops_df.to_csv(backup_path, index=False)
        route_stops_df.to_csv(route_stops_path, index=False)
        
        print(f"\n✅ Updated {updated} stop names")
        print(f"⚠️  {len(still_missing)} stops still have no name (need geocoding)")
        print(f"💾 Backup: {backup_path}")
        
        # Save list of stops still needing names
        if still_missing:
            missing_path = os.path.join(self.base_path, "backend/data/stops_needing_names.json")
            os.makedirs(os.path.dirname(missing_path), exist_ok=True)
            with open(missing_path, 'w') as f:
                json.dump(still_missing[:100], f, indent=2)  # First 100
            print(f"📝 Stops needing names saved to: {missing_path}")
        
        return updated

    def _update_from_existing_good_names(self, route_stops_df):
        """Use already good names in the dataset to fill in missing ones by stop_id"""
        print("📝 Building name mapping from existing good names...")
        
        # Find all good names (not Stop_xxx)
        id_to_name = {}
        for _, row in route_stops_df.iterrows():
            stop_id = str(row['stop_id'])
            stop_name = str(row.get('stop_name', ''))
            if stop_name and stop_name != 'nan' and not self.is_stop_id_name(stop_name):
                if stop_id not in id_to_name:
                    id_to_name[stop_id] = stop_name
        
        print(f"📚 Found {len(id_to_name)} unique named stops")
        
        # Update stops that need names
        updated = 0
        for idx, row in route_stops_df.iterrows():
            stop_id = str(row['stop_id'])
            current_name = str(row.get('stop_name', ''))
            
            if self.is_stop_id_name(current_name):
                if stop_id in id_to_name:
                    route_stops_df.at[idx, 'stop_name'] = id_to_name[stop_id]
                    updated += 1
        
        # Save
        route_stops_path = os.path.join(self.base_path, "route_stop_ordered.csv")
        backup_path = route_stops_path.replace('.csv', '_backup.csv')
        route_stops_df.to_csv(backup_path, index=False)
        route_stops_df.to_csv(route_stops_path, index=False)
        
        print(f"✅ Updated {updated} stop names from existing data")
        print(f"💾 Backup: {backup_path}")
        
        # Count remaining stops without names
        still_missing = sum(1 for _, row in route_stops_df.iterrows() 
                          if self.is_stop_id_name(str(row.get('stop_name', ''))))
        print(f"⚠️  {still_missing} stops still have no proper name")
        
        return updated


if __name__ == "__main__":
    resolver = StopNameResolver()
    
    # First, quick update from bus_stops.csv (no API calls)
    resolver.update_from_bus_stops()
    
    # Then, geocode remaining stops (will make API calls)
    print("\n" + "=" * 50)
    print("🌍 Starting geocoding for stops without names...")
    print("   This will take some time due to API rate limits")
    print("=" * 50)
    resolver.resolve_stop_names(max_stops=200)  # Geocode up to 200 stops