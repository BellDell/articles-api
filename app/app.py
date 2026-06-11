"""Flask application factory and WSGI entry point."""

import logging
import os

from app.routes import register_routes
from flask import Flask


class HealthLogFilter(logging.Filter):
    """Suppress werkzeug access-log lines for successful health checks."""

    def filter(self, record):
        msg = record.getMessage()
        if '"GET /health HTTP/1.1" 200' in msg or '"GET /health HTTP/1.0" 200' in msg:
            return False
        return True


app = Flask(__name__)
register_routes(app)

# Suppress noisy health-check access logs
werkzeug_logger = logging.getLogger("werkzeug")
werkzeug_logger.addFilter(HealthLogFilter())

if __name__ == '__main__':  # pragma: no cover
    host = os.environ.get('HOST', '127.0.0.1')
    port = int(os.environ.get('PORT', 5000))
    app.run(host=host, port=port, debug=False)
