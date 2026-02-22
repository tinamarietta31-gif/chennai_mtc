"""
Test suite for Chennai MTC Smart Transport API
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from app import app

client = TestClient(app)


class TestHealthEndpoints:
    """Test health and status endpoints"""
    
    def test_root_endpoint(self):
        """Test root endpoint returns API info"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "version" in data
    
    def test_health_check(self):
        """Test health check endpoint"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "healthy"
    
    def test_stats_endpoint(self):
        """Test stats endpoint returns data counts"""
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_stops" in data
        assert "total_routes" in data
        assert "total_edges" in data


class TestStopsEndpoints:
    """Test stops-related endpoints"""
    
    def test_get_all_stops(self):
        """Test getting all stops"""
        response = client.get("/get-stops")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_search_stops(self):
        """Test searching stops by name"""
        response = client.get("/get-stops?query=central")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_stop_suggestions(self):
        """Test autocomplete suggestions"""
        response = client.get("/get-stop-suggestions?query=anna")
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert isinstance(data["suggestions"], list)
    
    def test_stop_suggestions_min_length(self):
        """Test that suggestions require minimum query length"""
        response = client.get("/get-stop-suggestions?query=a")
        assert response.status_code == 422  # Validation error


class TestRouteEndpoints:
    """Test route-related endpoints"""
    
    def test_search_route_success(self):
        """Test route search with valid stops"""
        response = client.post("/search-route", json={
            "source": "Broadway",
            "destination": "T.Nagar",
            "time_of_day": 9
        })
        # May return 404 if no route exists, which is valid
        assert response.status_code in [200, 404]
    
    def test_search_route_missing_params(self):
        """Test route search with missing parameters"""
        response = client.post("/search-route", json={
            "source": "Broadway"
        })
        assert response.status_code == 422  # Validation error
    
    def test_get_route_map(self):
        """Test getting route map data"""
        response = client.get("/get-route-map/1")
        # Route may or may not exist
        assert response.status_code in [200, 404]


class TestPredictionEndpoints:
    """Test ML prediction endpoints"""
    
    def test_predict_time(self):
        """Test travel time prediction"""
        response = client.post("/predict-time", json={
            "number_of_stops": 10,
            "total_distance_km": 5.5,
            "time_of_day": 9,
            "route_length": 5.5
        })
        assert response.status_code == 200
        data = response.json()
        assert "predicted_time" in data
        assert "delay_probability" in data
        assert "confidence" in data
    
    def test_predict_time_peak_hours(self):
        """Test prediction during peak hours"""
        # Morning peak
        response = client.post("/predict-time", json={
            "number_of_stops": 15,
            "total_distance_km": 8.0,
            "time_of_day": 9,
            "route_length": 8.0
        })
        morning_data = response.json()
        
        # Evening peak
        response = client.post("/predict-time", json={
            "number_of_stops": 15,
            "total_distance_km": 8.0,
            "time_of_day": 18,
            "route_length": 8.0
        })
        evening_data = response.json()
        
        # Off-peak
        response = client.post("/predict-time", json={
            "number_of_stops": 15,
            "total_distance_km": 8.0,
            "time_of_day": 14,
            "route_length": 8.0
        })
        offpeak_data = response.json()
        
        # Peak hours should have higher delay probability
        assert morning_data["peak_hour"] == True
        assert evening_data["peak_hour"] == True
        assert offpeak_data["peak_hour"] == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
