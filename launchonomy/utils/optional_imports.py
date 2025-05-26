"""
Optional imports utility for handling missing dependencies gracefully.

This module provides safe imports for optional dependencies that may not be installed.
It allows the system to function with reduced features when optional packages are missing.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# FastAPI and web framework dependencies
try:
    import fastapi
    FASTAPI_AVAILABLE = True
except ImportError:
    fastapi = None
    FASTAPI_AVAILABLE = False
    logger.info("FastAPI not available - web interface features disabled")

try:
    import uvicorn
    UVICORN_AVAILABLE = True
except ImportError:
    uvicorn = None
    UVICORN_AVAILABLE = False
    logger.info("Uvicorn not available - web server features disabled")

# Enhanced HTTP clients
try:
    import aiohttp
    AIOHTTP_AVAILABLE = True
except ImportError:
    aiohttp = None
    AIOHTTP_AVAILABLE = False
    logger.info("aiohttp not available - using standard HTTP client")

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    httpx = None
    HTTPX_AVAILABLE = False
    logger.info("httpx not available - using standard HTTP client")

# Enhanced JSON processing
try:
    import orjson
    ORJSON_AVAILABLE = True
except ImportError:
    orjson = None
    ORJSON_AVAILABLE = False
    logger.info("orjson not available - using standard json module")

# Structured logging
try:
    import structlog
    STRUCTLOG_AVAILABLE = True
except ImportError:
    structlog = None
    STRUCTLOG_AVAILABLE = False
    logger.info("structlog not available - using standard logging")

# Metrics collection
try:
    import prometheus_client
    PROMETHEUS_AVAILABLE = True
except ImportError:
    prometheus_client = None
    PROMETHEUS_AVAILABLE = False
    logger.info("prometheus-client not available - metrics collection disabled")

def safe_json_dumps(data: Any, **kwargs) -> str:
    """Safely serialize JSON using orjson if available, otherwise standard json."""
    if ORJSON_AVAILABLE:
        # orjson returns bytes, need to decode
        return orjson.dumps(data, **kwargs).decode('utf-8')
    else:
        import json
        return json.dumps(data, **kwargs)

def safe_json_loads(data: str) -> Any:
    """Safely deserialize JSON using orjson if available, otherwise standard json."""
    if ORJSON_AVAILABLE:
        return orjson.loads(data)
    else:
        import json
        return json.loads(data)

def get_http_client():
    """Get the best available HTTP client."""
    if HTTPX_AVAILABLE:
        return httpx
    elif AIOHTTP_AVAILABLE:
        return aiohttp
    else:
        import urllib.request
        return urllib.request

def create_structured_logger(name: str):
    """Create a structured logger if structlog is available, otherwise standard logger."""
    if STRUCTLOG_AVAILABLE:
        return structlog.get_logger(name)
    else:
        return logging.getLogger(name)

def check_optional_dependencies() -> dict:
    """Check which optional dependencies are available."""
    return {
        "fastapi": FASTAPI_AVAILABLE,
        "uvicorn": UVICORN_AVAILABLE,
        "aiohttp": AIOHTTP_AVAILABLE,
        "httpx": HTTPX_AVAILABLE,
        "orjson": ORJSON_AVAILABLE,
        "structlog": STRUCTLOG_AVAILABLE,
        "prometheus_client": PROMETHEUS_AVAILABLE
    }

def get_missing_dependencies() -> list:
    """Get list of missing optional dependencies."""
    deps = check_optional_dependencies()
    return [name for name, available in deps.items() if not available]

def install_command_for_missing() -> str:
    """Generate pip install command for missing dependencies."""
    missing = get_missing_dependencies()
    if not missing:
        return "All optional dependencies are installed!"
    
    # Map to actual package names
    package_map = {
        "fastapi": "fastapi>=0.104.0",
        "uvicorn": "uvicorn[standard]>=0.24.0",
        "aiohttp": "aiohttp>=3.9.0",
        "httpx": "httpx>=0.25.0",
        "orjson": "orjson>=3.9.0",
        "structlog": "structlog>=23.0.0",
        "prometheus_client": "prometheus-client>=0.19.0"
    }
    
    packages = [package_map.get(dep, dep) for dep in missing]
    return f"pip install {' '.join(packages)}" 