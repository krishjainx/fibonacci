from functools import lru_cache
import redis
import logging
import os
import time

logger = logging.getLogger(__name__)

# Initialize Redis client with connection error handling and retry
try:
    redis_host = os.getenv('REDIS_HOST', 'localhost')
    print(f"Connecting to Redis at {redis_host}:6379...")  # Debug print
    
    # Add retry logic
    max_retries = 5
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            redis_client = redis.Redis(
                host=redis_host, 
                port=6379, 
                db=0,
                socket_timeout=5,
                decode_responses=True
            )
            redis_client.ping()
            print("Successfully connected to Redis")  # Debug print
            break
        except redis.ConnectionError as e:
            if attempt == max_retries - 1:
                raise
            print(f"Attempt {attempt + 1}/{max_retries} failed, retrying in {retry_delay}s...")
            time.sleep(retry_delay)
            
except redis.ConnectionError as e:
    print(f"Redis connection failed after {max_retries} attempts: {e}")
    logger.warning("Redis not available - falling back to in-memory cache only")
    redis_client = None

@lru_cache(maxsize=1000)
def generate_fibonacci_sequence(n: int) -> list[int]:
    # Try Redis cache first for exact match
    if redis_client:
        try:
            cache_key = f"fib_seq_{n}"
            cached = redis_client.get(cache_key)
            if cached:
                return eval(cached)
        except redis.RedisError as e:
            logger.error(f"Redis error: {e}")
    
    # Base cases
    if n <= 0:
        return []
    if n == 1:
        return [0]
    if n == 2:
        return [0, 1]
    
    # Try to find the largest cached sequence less than n
    largest_cached = None
    if redis_client:
        try:
            for i in range(n-1, 1, -1):
                cache_key = f"fib_seq_{i}"
                cached = redis_client.get(cache_key)
                if cached:
                    largest_cached = eval(cached)
                    break
        except redis.RedisError:
            pass
    
    # If we found a cached sequence, extend it
    if largest_cached:
        fib_seq = largest_cached.copy()
        start = len(fib_seq)
    else:
        # Start from scratch
        fib_seq = [0, 1]
        start = 2
    
    # Generate remaining numbers
    for i in range(start, n):
        fib_seq.append(fib_seq[-1] + fib_seq[-2])
    
    # Cache the new result
    if redis_client:
        try:
            cache_key = f"fib_seq_{n}"
            redis_client.setex(cache_key, 3600, str(fib_seq))
        except redis.RedisError as e:
            logger.error(f"Redis caching error: {e}")
    
    return fib_seq
