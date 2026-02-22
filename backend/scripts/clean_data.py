#!/usr/bin/env python3
"""
Comprehensive Data Cleaner for Chennai MTC Bus Data
- Removes duplicates
- Validates coordinates
- Generates unique stop names using reverse geocoding
- Cleans route data
"""

import pandas as pd
import numpy as np
import os
import json
import requests
import time
from collections import defaultdict

class MTCDataCleaner:
    def __init__(self):
        self.base_path = "/Users/jerimothimmanuel/chennai_mtc_project"
        self.route_stops_file = os.path.join(self.base_path, "route_stop_ordered.csv")
        self.route_edges_file = os.path.join(self.base_path, "route_edges.csv")
        self.output_dir = os.path.join(self.base_path, "backend/data")
        self.cache_file = os.path.join(self.output_dir, "geocode_cache.json")
        
        os.makedirs(self.output_dir, exist_ok=True)
        self.geocode_cache = self._load_cache()
    
    def _load_cache(self):
        """Load geocoding cache"""
        if os.path.exists(self.cache_file):
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        return {}
    
    def _save_cache(self):
        """Save geocoding cache"""
        with open(self.cache_file, 'w') as f:
            json.dump(self.geocode_cache, f, indent=2)
    
    def clean_all(self):
        """Run all cleaning operations"""
        print("🧹 Chennai MTC Data Cleaner")
        print("=" * 60)
        
        # Load data
        print("\n📂 Loading datasets...")
        route_stops_df = pd.read_csv(self.route_stops_file)
        print(f"   Loaded {len(route_stops_df)} route-stop records")
        
        if os.path.exists(self.route_edges_file):
            route_edges_df = pd.read_csv(self.route_edges_file)
            print(f"   Loaded {len(route_edges_df)} route edge records")
        else:
            route_edges_df = None
        
        # Step 1: Analyze current data
        print("\n📊 Analyzing data quality...")
        self._analyze_data(route_stops_df)
        
        # Step 2: Clean stop data
        print("\n🔧 Cleaning stop data...")
        route_stops_df = self._clean_stops(route_stops_df)
        
        # Step 3: Remove duplicates
        print("\n🗑️  Removing duplicates...")
        route_stops_df = self._remove_duplicates(route_stops_df)
        
        # Step 4: Generate unique stop names
        print("\n🏷️  Generating unique stop names...")
        route_stops_df = self._generate_unique_names(route_stops_df)
        
        # Step 5: Validate and fix sequences
        print("\n🔢 Validating stop sequences...")
        route_stops_df = self._fix_sequences(route_stops_df)
        
        # Step 6: Create clean bus_stops.csv
        print("\n📝 Creating clean bus_stops.csv...")
        bus_stops_df = self._create_bus_stops(route_stops_df)
        
        # Step 7: Save cleaned data
        print("\n💾 Saving cleaned data...")
        self._save_cleaned_data(route_stops_df, bus_stops_df, route_edges_df)
        
        # Final summary
        self._print_summary(route_stops_df, bus_stops_df)
    
    def _analyze_data(self, df):
        """Analyze current data quality"""
        total_records = len(df)
        unique_stops = df['stop_id'].nunique()
        unique_routes = df['route_number'].nunique()
        
        # Check for missing values
        missing_names = df['stop_name'].isna().sum() if 'stop_name' in df.columns else total_records
        
        # Check for Stop_xxx names
        if 'stop_name' in df.columns:
            stop_id_names = df['stop_name'].apply(
                lambda x: str(x).startswith('Stop_') or str(x).startswith('stop_')
            ).sum()
        else:
            stop_id_names = total_records
        
        # Check for duplicates
        duplicates = total_records - df.drop_duplicates(['route_number', 'stop_id', 'stop_sequence']).shape[0]
        
        # Check coordinate validity
        valid_coords = df[
            (df['latitude'].between(12.5, 13.5)) & 
            (df['longitude'].between(79.5, 80.5))
        ].shape[0]
        
        print(f"   Total records: {total_records}")
        print(f"   Unique stops: {unique_stops}")
        print(f"   Unique routes: {unique_routes}")
        print(f"   Stops with ID-based names: {stop_id_names}")
        print(f"   Duplicate records: {duplicates}")
        print(f"   Valid Chennai coordinates: {valid_coords}/{total_records}")
    
    def _clean_stops(self, df):
        """Clean stop data - fix basic issues"""
        # Ensure required columns exist
        if 'stop_name' not in df.columns:
            df['stop_name'] = df['stop_id'].apply(lambda x: f"Stop_{x}")
        
        # Clean string columns
        df['stop_name'] = df['stop_name'].fillna('').astype(str).str.strip()
        df['stop_id'] = df['stop_id'].astype(str).str.strip()
        df['route_number'] = df['route_number'].astype(str).str.strip()
        
        # Fix invalid coordinates (set to NaN if outside Chennai)
        invalid_lat = ~df['latitude'].between(12.5, 13.5)
        invalid_lon = ~df['longitude'].between(79.5, 80.5)
        
        if invalid_lat.any() or invalid_lon.any():
            print(f"   Fixed {(invalid_lat | invalid_lon).sum()} invalid coordinates")
            df.loc[invalid_lat, 'latitude'] = np.nan
            df.loc[invalid_lon, 'longitude'] = np.nan
        
        # Remove rows with no valid coordinates
        before = len(df)
        df = df.dropna(subset=['latitude', 'longitude'])
        print(f"   Removed {before - len(df)} rows with missing coordinates")
        
        return df
    
    def _remove_duplicates(self, df):
        """Remove duplicate records"""
        before = len(df)
        
        # Remove exact duplicates
        df = df.drop_duplicates()
        
        # Remove duplicate stop_id within same route (keep first by sequence)
        df = df.sort_values(['route_number', 'stop_sequence'])
        df = df.drop_duplicates(subset=['route_number', 'stop_id'], keep='first')
        
        # Remove duplicate sequences within same route
        df = df.drop_duplicates(subset=['route_number', 'stop_sequence'], keep='first')
        
        print(f"   Removed {before - len(df)} duplicate records")
        print(f"   Remaining records: {len(df)}")
        
        return df
    
    def _generate_unique_names(self, df):
        """Generate unique, meaningful stop names using reverse geocoding"""
        # Get unique stops by stop_id
        unique_stops = df.drop_duplicates('stop_id')[['stop_id', 'latitude', 'longitude']].copy()
        
        print(f"   Found {len(unique_stops)} unique stops to name")
        
        stop_names = {}
        
        for idx, row in unique_stops.iterrows():
            stop_id = str(row['stop_id'])
            lat = row['latitude']
            lon = row['longitude']
            
            # Try to get name from geocoding
            name = self._reverse_geocode(lat, lon, stop_id)
            stop_names[stop_id] = name
            
            # Progress indicator
            current = len(stop_names)
            if current % 20 == 0:
                print(f"   Progress: {current}/{len(unique_stops)} stops named")
        
        # Apply names to dataframe
        df['stop_name'] = df['stop_id'].astype(str).map(stop_names)
        
        # Make names unique by adding suffixes where needed
        df = self._make_names_unique(df)
        
        # Save cache after all geocoding
        self._save_cache()
        
        return df
    
    def _reverse_geocode(self, lat, lon, stop_id):
        """Get place name from coordinates using OpenStreetMap Nominatim"""
        cache_key = f"{lat:.6f},{lon:.6f}"
        
        # Check cache first
        if cache_key in self.geocode_cache:
            return self.geocode_cache[cache_key]
        
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': lat,
                'lon': lon,
                'format': 'json',
                'zoom': 18,
                'addressdetails': 1
            }
            headers = {
                'User-Agent': 'ChennaiMTCProject/1.0 (educational)'
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                address = data.get('address', {})
                
                # Build unique name from address components
                name = self._build_stop_name(address, lat, lon)
                
                self.geocode_cache[cache_key] = name
                
                # Rate limit: 1 request per second for Nominatim
                time.sleep(1.1)
                
                return name
            
        except Exception as e:
            print(f"   ⚠️ Geocoding error for {stop_id}: {e}")
        
        # Fallback: generate name from coordinates
        return self._generate_fallback_name(lat, lon, stop_id)
    
    def _build_stop_name(self, address, lat, lon):
        """Build a descriptive stop name from address components"""
        # Extract address parts
        road = address.get('road') or address.get('street') or address.get('highway')
        
        # Landmarks/POIs
        landmark = (
            address.get('amenity') or
            address.get('building') or
            address.get('shop') or
            address.get('tourism') or
            address.get('office') or
            address.get('leisure')
        )
        
        # Area names
        neighbourhood = address.get('neighbourhood') or address.get('quarter')
        suburb = address.get('suburb') or address.get('locality')
        city_district = address.get('city_district')
        
        # Build the name
        parts = []
        
        # Primary identifier
        if road:
            parts.append(road)
        elif landmark:
            parts.append(landmark)
        elif neighbourhood:
            parts.append(neighbourhood)
        
        # Add area context
        if suburb and suburb not in parts:
            parts.append(suburb)
        elif neighbourhood and neighbourhood not in parts:
            parts.append(neighbourhood)
        elif city_district and city_district not in parts:
            parts.append(city_district)
        
        # If we have a good name
        if len(parts) >= 1:
            if len(parts) == 1:
                # Add coordinate hint for uniqueness
                return f"{parts[0]} ({lat:.4f})"
            else:
                return f"{parts[0]}, {parts[1]}"
        
        # Fallback
        return self._generate_fallback_name(lat, lon, "")
    
    def _generate_fallback_name(self, lat, lon, stop_id):
        """Generate name when geocoding fails"""
        # Chennai area detection based on coordinates
        areas = [
            ((13.05, 13.15), (80.20, 80.30), "North Chennai"),
            ((13.00, 13.05), (80.20, 80.28), "Central Chennai"),
            ((12.95, 13.00), (80.20, 80.28), "South Chennai"),
            ((12.90, 12.95), (80.15, 80.25), "Tambaram Area"),
            ((12.95, 13.00), (80.15, 80.22), "Guindy Area"),
            ((13.00, 13.08), (80.15, 80.22), "West Chennai"),
            ((12.97, 13.03), (80.22, 80.28), "Adyar Area"),
        ]
        
        for (lat_min, lat_max), (lon_min, lon_max), area_name in areas:
            if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
                return f"{area_name} Stop ({lat:.4f})"
        
        return f"Chennai Bus Stop ({lat:.4f}, {lon:.4f})"
    
    def _make_names_unique(self, df):
        """Ensure all stop names are unique across the entire dataset"""
        # First, get unique stop_id to name mapping
        stop_id_to_name = df.drop_duplicates('stop_id').set_index('stop_id')['stop_name'].to_dict()
        
        # Check for duplicate names (different stop_ids with same name)
        name_to_stop_ids = defaultdict(list)
        for stop_id, name in stop_id_to_name.items():
            name_to_stop_ids[name].append(stop_id)
        
        duplicates = {name: ids for name, ids in name_to_stop_ids.items() if len(ids) > 1}
        
        if not duplicates:
            print(f"   ✅ All {len(stop_id_to_name)} stop names are already unique!")
            return df
        
        print(f"   Found {len(duplicates)} duplicate names to fix...")
        
        # Fix duplicates by adding distinguishing info
        for dup_name, stop_ids in duplicates.items():
            for idx, stop_id in enumerate(stop_ids):
                if idx == 0:
                    continue  # Keep first one as-is
                
                # Get coordinates for this stop
                stop_data = df[df['stop_id'] == stop_id].iloc[0]
                lat = stop_data['latitude']
                lon = stop_data['longitude']
                
                # Get routes this stop serves
                routes = df[df['stop_id'] == stop_id]['route_number'].unique()
                
                # Create unique suffix
                if len(routes) == 1:
                    new_name = f"{dup_name} (Route {routes[0]})"
                else:
                    new_name = f"{dup_name} ({lat:.4f}N)"
                
                # Ensure it's unique
                all_names = set(df['stop_name'].unique())
                counter = 2
                base_name = new_name
                while new_name in all_names:
                    new_name = f"{base_name} #{counter}"
                    counter += 1
                
                # Update in dataframe
                df.loc[df['stop_id'] == stop_id, 'stop_name'] = new_name
                stop_id_to_name[stop_id] = new_name
        
        print(f"   ✅ Fixed all duplicate names")
        return df
    
    def _fix_sequences(self, df):
        """Fix stop sequences within each route"""
        fixed_routes = 0
        
        for route in df['route_number'].unique():
            route_mask = df['route_number'] == route
            route_data = df[route_mask].sort_values('stop_sequence')
            
            # Check if sequences are continuous
            sequences = route_data['stop_sequence'].tolist()
            expected = list(range(1, len(sequences) + 1))
            
            if sequences != expected:
                # Resequence
                df.loc[route_mask, 'stop_sequence'] = range(1, sum(route_mask) + 1)
                fixed_routes += 1
        
        if fixed_routes > 0:
            print(f"   Fixed sequences for {fixed_routes} routes")
        
        return df
    
    def _create_bus_stops(self, route_stops_df):
        """Create a clean bus_stops.csv with unique stops"""
        # Get unique stops
        stops = route_stops_df.groupby('stop_id').agg({
            'stop_name': 'first',
            'latitude': 'mean',
            'longitude': 'mean',
            'route_number': lambda x: ','.join(sorted(set(x.astype(str))))
        }).reset_index()
        
        stops.columns = ['stop_id', 'stop_name', 'latitude', 'longitude', 'routes']
        
        print(f"   Created {len(stops)} unique bus stops")
        
        return stops
    
    def _save_cleaned_data(self, route_stops_df, bus_stops_df, route_edges_df):
        """Save all cleaned data"""
        # Backup original
        backup_path = self.route_stops_file.replace('.csv', '_original_backup.csv')
        if not os.path.exists(backup_path):
            original_df = pd.read_csv(self.route_stops_file)
            original_df.to_csv(backup_path, index=False)
            print(f"   Original backup: {backup_path}")
        
        # Save cleaned route_stop_ordered.csv
        route_stops_df.to_csv(self.route_stops_file, index=False)
        print(f"   Saved: {self.route_stops_file}")
        
        # Save bus_stops.csv
        bus_stops_path = os.path.join(self.base_path, "bus_stops.csv")
        bus_stops_df.to_csv(bus_stops_path, index=False)
        print(f"   Saved: {bus_stops_path}")
        
        # Also save to backend/data
        bus_stops_df.to_csv(os.path.join(self.output_dir, "bus_stops.csv"), index=False)
        
        # Create stop name mapping JSON
        name_mapping = dict(zip(bus_stops_df['stop_id'], bus_stops_df['stop_name']))
        mapping_path = os.path.join(self.output_dir, "stop_name_mapping.json")
        with open(mapping_path, 'w') as f:
            json.dump(name_mapping, f, indent=2)
        print(f"   Saved: {mapping_path}")
    
    def _print_summary(self, route_stops_df, bus_stops_df):
        """Print final summary"""
        print("\n" + "=" * 60)
        print("✅ Data Cleaning Complete!")
        print("=" * 60)
        print(f"\n📊 Final Statistics:")
        print(f"   Total route-stop records: {len(route_stops_df)}")
        print(f"   Unique bus stops: {len(bus_stops_df)}")
        print(f"   Unique routes: {route_stops_df['route_number'].nunique()}")
        print(f"   Unique stop names: {bus_stops_df['stop_name'].nunique()}")
        
        # Check for any remaining issues
        id_names = bus_stops_df['stop_name'].apply(
            lambda x: str(x).startswith('Stop_')
        ).sum()
        
        if id_names > 0:
            print(f"   ⚠️  Stops still with ID-based names: {id_names}")
        else:
            print(f"   ✅ All stops have proper names!")
        
        print(f"\n📁 Output files:")
        print(f"   - {self.route_stops_file}")
        print(f"   - {self.base_path}/bus_stops.csv")
        print(f"   - {self.output_dir}/stop_name_mapping.json")


if __name__ == "__main__":
    cleaner = MTCDataCleaner()
    cleaner.clean_all()