import logging
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi import Request, Response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("app.log"),  # Log to a file
        logging.StreamHandler()            # Log to console
    ]
)

logger = logging.getLogger(__name__)

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Log request details
        logger.info(f"Request: {request.method} {request.url}")

        # Process the request and get the response
        response: Response = await call_next(request)

        # Log response details
        logger.info(f"Response: {response.status_code} for {request.method} {request.url}")

        return response
