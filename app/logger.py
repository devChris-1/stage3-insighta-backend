import time
import logging
from flask import request, g

logging.basicConfig(
    format="%(asctime)s %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def init_logger(app):
    @app.before_request
    def start_timer():
        g.start_time = time.time()

    @app.after_request
    def log_request(response):
        duration_ms = round((time.time() - g.start_time) * 1000, 2)
        logger.info(f"{request.method} {request.path} {response.status_code} {duration_ms}ms")
        return response
