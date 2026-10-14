"""
Gunicorn configuration file for FOTOSTREAM.
Enables Uvicorn ASGI worker class, binding, and debugging logs.
"""

wsgi_app = "main:app"
worker_class = "uvicorn.workers.UvicornWorker"
workers = 2
bind = "0.0.0.0:5000"
loglevel = "debug"
accesslog = "-"
errorlog = "-"
capture_output = True
keepalive = 65
timeout = 120
