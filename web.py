"""Entry point for Flask web application.

This script starts the BOCHK monitoring web interface with the monitor
running in a background thread. Used by Procfile for web dyno.

Environment variables:
    PORT: Port to listen on (default: 5000)
    HOST: Host to bind to (default: 0.0.0.0)
    FLASK_SECRET_KEY: Flask session secret key
"""

import os
from src.app import app, monitor_state

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("PORT", 5000))
    host = os.getenv("HOST", "0.0.0.0")

    # Start monitor in background thread
    monitor_state.start()

    # In production, gunicorn will handle the web server
    # This block is for local development only
    app.run(host=host, port=port, debug=False, use_reloader=False)
