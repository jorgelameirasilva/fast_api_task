import multiprocessing

# Server socket
bind = "0.0.0.0:8000"
backlog = 2048

# Worker processes
workers = (multiprocessing.cpu_count() * 2) + 1
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Logging
loglevel = "info"
accesslog = "-"
errorlog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = "hr-chatbot-api"

# Timeouts
timeout = 230
keepalive = 2
graceful_timeout = 30

# SSL/Security (if needed)
# keyfile = None
# certfile = None

# Server mechanics
preload_app = True
daemon = False
pidfile = None
user = None
group = None
tmp_upload_dir = None

# Application
wsgi_module = "app.main:app"

# For development
reload = False


def on_starting(server):
    """Called just before the master process is initialized."""
    server.log.info("Starting HR Chatbot API server...")


def on_reload(server):
    """Called to recycle workers during a reload via SIGHUP."""
    server.log.info("Reloading HR Chatbot API server...")


def worker_int(worker):
    """Called just after a worker exited on SIGINT or SIGQUIT."""
    worker.log.info("Worker received INT or QUIT signal")


def on_exit(server):
    """Called just before exiting."""
    server.log.info("HR Chatbot API server is shutting down...")
