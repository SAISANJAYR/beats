import time
import logging
from collections import deque

logger = logging.getLogger("beats.requests")

# In-memory buffer storing the last 50 requests for the health check page
RECENT_REQUESTS_LOG = deque(maxlen=50)


class RequestLoggingMiddleware:
    """
    Assessment Requirement: Request logging middleware.
    Tracks every incoming request and outgoing response, calculating duration in ms,
    recording client IP, HTTP status, and user-agent.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start_time = time.time()

        # Capture client IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR', '127.0.0.1')

        response = self.get_response(request)

        duration_ms = round((time.time() - start_time) * 1000, 2)

        log_entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "method": request.method,
            "path": request.path,
            "ip": ip,
            "status_code": response.status_code,
            "duration_ms": duration_ms,
            "user_agent": request.META.get('HTTP_USER_AGENT', 'Unknown')[:80],
        }

        # Store in buffer
        RECENT_REQUESTS_LOG.append(log_entry)

        # Log via standard logging
        logger.info(
            "%s %s %s from %s - %sms",
            request.method,
            request.path,
            response.status_code,
            ip,
            duration_ms
        )

        # Add custom response header
        response['X-Response-Time-Ms'] = str(duration_ms)
        return response
