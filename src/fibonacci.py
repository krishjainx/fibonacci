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

@lru_cache(maxsize=1000)  # Cache in memory for quick access
def generate_fibonacci_sequence(n: int) -> list[int]:
    # Try Redis cache if available
    if redis_client:
        try:
            cache_key = f"fib_seq_{n}"
            cached = redis_client.get(cache_key)
            if cached:
                return eval(cached.decode())  # Convert string back to list
        except redis.RedisError as e:
            logger.error(f"Redis error: {e}")
            # Continue with calculation if Redis fails
        
    if n <= 0:
        return []

    fib_seq = [0]
    if n == 1:
        return fib_seq

    fib_seq.append(1)
    for _ in range(2, n):
        fib_seq.append(fib_seq[-1] + fib_seq[-2])

    # Cache in Redis if available
    if redis_client:
        try:
            cache_key = f"fib_seq_{n}"
            redis_client.setex(cache_key, 3600, str(fib_seq))  # 1 hour expiration
        except redis.RedisError as e:
            logger.error(f"Redis caching error: {e}")
            # Continue without caching if Redis fails

    return fib_seq
