import warnings
import os
import sys
import time
import redis

# Filter specific deprecation warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
warnings.filterwarnings("ignore", message=".*ast\\.Str.*")
warnings.filterwarnings("ignore", message=".*ast\\.Name.*")
warnings.filterwarnings("ignore", message=".*ast\\.Num.*")
warnings.filterwarnings("ignore", message=".*ast\\.Bytes.*")
warnings.filterwarnings("ignore", message=".*ast\\.NameConstant.*")
warnings.filterwarnings("ignore", message=".*the imp module.*")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from src.fibonacci import generate_fibonacci_sequence
from src.app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_generate_fibonacci_sequence():
    assert generate_fibonacci_sequence(1) == [0]
    assert generate_fibonacci_sequence(2) == [0, 1]
    assert generate_fibonacci_sequence(5) == [0, 1, 1, 2, 3]
    assert generate_fibonacci_sequence(0) == []
    assert generate_fibonacci_sequence(-5) == []

def test_fibonacci_endpoint_success(client):
    response = client.get('/fibonacci?n=5')
    assert response.status_code == 200
    assert response.json == [0, 1, 1, 2, 3]

def test_fibonacci_endpoint_negative(client):
    response = client.get('/fibonacci?n=-1')
    assert response.status_code == 422
    assert "Negative value is not allowed" in response.json["error"]

def test_fibonacci_endpoint_missing_param(client):
    response = client.get('/fibonacci')
    assert response.status_code == 400
    assert "Parameter 'n' is required" in response.json["error"]

def test_fibonacci_endpoint_invalid_param(client):
    response = client.get('/fibonacci?n=abc')
    assert response.status_code == 400
    assert "Invalid integer" in response.json["error"]

def test_redis_caching():
    """Test that Redis caching is working"""
    try:
        # Get Redis host from environment or default to localhost
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_client = redis.Redis(host=redis_host, port=6379, db=0)
        redis_client.ping()
        
        test_n = 7
        cache_key = f"fib_seq_{test_n}"
        
        # Clear any existing cache
        redis_client.delete(cache_key)
        
        # First call should calculate and cache
        start_time = time.time()
        result1 = generate_fibonacci_sequence(test_n)
        first_call_time = time.time() - start_time
        
        # Wait a moment to ensure cache is written
        time.sleep(0.1)
        
        # Verify the value is in Redis
        cached_value = redis_client.get(cache_key)
        assert cached_value is not None, "Value was not cached in Redis"
        assert eval(cached_value.decode()) == result1, "Cached value doesn't match"
        
        # Second call should be faster (from cache)
        start_time = time.time()
        result2 = generate_fibonacci_sequence(test_n)
        second_call_time = time.time() - start_time
        
        assert result1 == result2, "Results should be identical"
        assert second_call_time < first_call_time, "Cached call should be faster"
        
    except redis.ConnectionError:
        pytest.skip("Redis is not available - skipping cache test")