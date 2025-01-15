from flask import Flask, request, jsonify
from src.fibonacci import generate_fibonacci_sequence, redis_client
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import psutil
import os
from datetime import datetime

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)


START_TIME = datetime.now()

@app.route('/fibonacci', methods=['GET'])
@limiter.limit("10 per minute")
def get_fibonacci():
    """
    GET /fibonacci?n=<value>
    Returns a JSON array of the first n Fibonacci numbers, starting from 0.
    """
    try:
        # Validate the 'n' parameter
        n_str = request.args.get('n', default=None)
        if n_str is None:
            return jsonify({"error": "Parameter 'n' is required"}), 400

        try:
            n = int(n_str)
        except ValueError:
            return jsonify({"error": f"Invalid integer: {n_str}"}), 400

        if n < 0:
            return jsonify({"error": f"Negative value is not allowed: {n}"}), 422

        # Generate the Fibonacci sequence
        fib_seq = generate_fibonacci_sequence(n)
        return jsonify(fib_seq), 200
        
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

# Add health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    """
    GET /health
    Returns detailed health status of the application and its dependencies.
    Checks:
    - System health (CPU, memory, disk)
    - Redis connection
    - Application uptime
    - Request handling capability
    """
    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "uptime_seconds": (datetime.now() - START_TIME).total_seconds(),
        "components": {
            "system": {
                "status": "healthy",
                "cpu_usage_percent": None,
                "memory_usage_percent": None,
                "disk_usage_percent": None
            },
            "redis": {
                "status": "healthy",
                "latency_ms": None
            },
            "application": {
                "status": "healthy",
                "request_handling": True
            }
        }
    }

    try:
        # System Health Checks
        health_status["components"]["system"].update({
            "cpu_usage_percent": psutil.cpu_percent(interval=0.1),
            "memory_usage_percent": psutil.virtual_memory().percent,
            "disk_usage_percent": psutil.disk_usage('/').percent
        })

        # Mark system as unhealthy if resources are critically low
        if (psutil.virtual_memory().percent > 95 or  # Memory near exhaustion
            psutil.disk_usage('/').percent > 95 or   # Disk near full
            psutil.cpu_percent() > 95):              # CPU maxed out
            health_status["components"]["system"]["status"] = "unhealthy"
            health_status["status"] = "degraded"

    except Exception as e:
        logger.error(f"System health check failed: {str(e)}")
        health_status["components"]["system"]["status"] = "unknown"
        health_status["status"] = "degraded"

    # Redis Health Check
    try:
        start_time = datetime.now()
        redis_client.ping()
        redis_latency = (datetime.now() - start_time).total_seconds() * 1000  # Convert to milliseconds
        
        health_status["components"]["redis"]["latency_ms"] = round(redis_latency, 2)
        
        # Mark Redis as degraded if latency is too high
        if redis_latency > 100:  # 100ms threshold
            health_status["components"]["redis"]["status"] = "degraded"
            health_status["status"] = "degraded"

    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        health_status["components"]["redis"]["status"] = "unhealthy"
        health_status["status"] = "unhealthy"

    # Determine final status and HTTP code
    status_code = 200
    if health_status["status"] == "unhealthy":
        status_code = 503  # Service Unavailable
    elif health_status["status"] == "degraded":
        status_code = 200  # Still serving but degraded
        
    return jsonify(health_status), status_code

if __name__ == '__main__':
    # For local development
    app.run(host='0.0.0.0', port=5000, debug=False)
