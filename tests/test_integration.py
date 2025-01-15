import pytest
import requests
import time

# Configuration for integration tests
BASE_URL = "http://localhost:5000"

def test_fibonacci_integration():
    """Test the fibonacci endpoint with valid input"""
    response = requests.get(f"{BASE_URL}/fibonacci?n=5")
    assert response.status_code == 200
    assert response.json() == [0, 1, 1, 2, 3]

def test_fibonacci_invalid_input():
    """Test the fibonacci endpoint with invalid input"""
    response = requests.get(f"{BASE_URL}/fibonacci?n=abc")
    assert response.status_code == 400
    assert "Invalid integer" in response.json()["error"]

def test_health_check():
    """Test the health check endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_rate_limiting():
    """Test rate limiting by making multiple rapid requests"""
    responses = []
    for _ in range(12):  # More than our 10/minute limit
        response = requests.get(f"{BASE_URL}/fibonacci?n=5")
        responses.append(response.status_code)
        time.sleep(0.1)  # Small delay between requests
    
    assert 429 in responses  # At least one request should be rate limited

# Create a separate file for load testing 