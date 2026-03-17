# 10 — Build and Deployment

## Relevant Source Files

- `src/flask/app.py` — Development server (L1550-L1625)
- `src/flask/cli.py` — CLI system (1127 lines)
- `pyproject.toml` — Build configuration
- `src/flask/sansio/app.py` — WSGI entry point

## TL;DR

Flask is a WSGI application that can run on any WSGI-compatible server. For development, use `flask run` (powered by Werkzeug's development server) for hot-reloading and debugging. For production, deploy using production WSGI servers like Gunicorn, uWSGI, or Waitress behind a reverse proxy (Nginx, Apache). The Flask application itself is just the WSGI callable; the deployment environment provides the HTTP server, process management, and reverse proxying.

## Overview

Flask deployment involves several layers:

1. **WSGI Application** — The Flask app (a callable)
2. **WSGI Server** — Executes the application (Gunicorn, uWSGI, etc.)
3. **Reverse Proxy** — Routes requests, handles SSL, compression (Nginx, Apache)
4. **Infrastructure** — Process management, logging, monitoring

### Development vs Production

| Aspect | Development | Production |
|--------|-------------|------------|
| Server | Werkzeug dev server (`flask run`) | Gunicorn, uWSGI, Waitress |
| Workers | Single threaded | Multiple (process/thread pool) |
| Reloading | Auto-reload on code change | No reloading |
| Debugging | Interactive debugger enabled | Disabled |
| Error pages | Detailed tracebacks | Generic 500 page |
| Concurrency | Not suitable for >1 request | Handles many concurrent requests |

## Architecture Diagram

```mermaid
graph LR
    subgraph Client["Client"]
        Browser["Web Browser"]
    end

    subgraph Proxy["Reverse Proxy<br/>(Nginx/Apache)"]
        ProxyServer["Listen 80/443<br/>SSL termination<br/>Compression"]
    end

    subgraph AppServer["WSGI Server<br/>(Gunicorn/uWSGI)"]
        Master["Master Process<br/>(manages workers)"]
        Worker1["Worker 1"]
        Worker2["Worker 2"]
        Worker3["Worker N"]
    end

    subgraph App["Flask Application"]
        Flask["Flask WSGI app<br/>Request handling"]
    end

    subgraph System["System Services"]
        Logger["Logging"]
        Monitor["Monitoring"]
        Static["Static file server<br/>(Nginx)"]
    end

    Browser -->|HTTP request| ProxyServer
    ProxyServer -->|forwarded request| Master
    Master -->|distribute| Worker1
    Master -->|distribute| Worker2
    Master -->|distribute| Worker3
    Worker1 -->|execute| Flask
    Worker2 -->|execute| Flask
    Worker3 -->|execute| Flask
    Flask -->|response| Worker1
    Flask -->|logs| Logger
    Flask -->|metrics| Monitor
    ProxyServer -->|serve| Static
    Worker1 -->|response| ProxyServer
    ProxyServer -->|HTTP response| Browser

    style ProxyServer fill:#2d5a8e,stroke:#1a3a5c,color:#fff
    style Master fill:#4d7a9e,stroke:#2d5a7c,color:#fff
```

## Development Server

### Running Locally

```bash
# Basic development server
flask run
# Runs on http://127.0.0.1:5000

# Specify host and port
flask run --host 0.0.0.0 --port 8000

# Enable debugger and reload
flask run --debug

# Or set environment variable
export FLASK_ENV=development
flask run
```

The `flask run` command in `src/flask/cli.py` uses Werkzeug's development server:

```python
# src/flask/app.py:L1550-L1625
def run(self, host=None, port=None, debug=None, ...):
    """Runs the application on a local development server."""
    from werkzeug.serving import run_simple

    # Configure
    if host is None:
        host = '127.0.0.1'
    if port is None:
        port = 5000

    # Run development server
    run_simple(
        host,
        port,
        self,  # WSGI callable
        use_debugger=debug,
        use_reloader=True,  # Auto-reload on code change
        static_files=self.static_folder,
    )
```

### Environment Variables

Development configuration via environment:

```bash
export FLASK_APP=app.py         # App module
export FLASK_ENV=development    # Environment
export FLASK_DEBUG=1            # Enable debugger
export SECRET_KEY=dev-secret    # Secret key
```

Or in `.env` file (with python-dotenv):

```
FLASK_APP=app.py
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=dev-secret
DATABASE_URL=sqlite:///dev.db
```

## Production Deployment

### Using Gunicorn

Gunicorn is a popular production WSGI server:

```bash
# Install
pip install gunicorn

# Run with default settings
gunicorn app:app

# With workers and threading
gunicorn --workers 4 --worker-class sync app:app

# With async workers
gunicorn --workers 4 --worker-class gevent app:app

# With configuration file
gunicorn --config gunicorn_config.py app:app
```

Configuration file (`gunicorn_config.py`):

```python
import multiprocessing

bind = '127.0.0.1:8000'
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = 'sync'
timeout = 30
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
```

### Reverse Proxy (Nginx)

Nginx configuration:

```nginx
upstream flask_app {
    server 127.0.0.1:8000;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
}

server {
    listen 80;
    server_name example.com;

    # Static files (served directly by Nginx)
    location /static/ {
        alias /path/to/app/static/;
    }

    # API requests (proxied to Flask)
    location / {
        proxy_pass http://flask_app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Process Management

Use supervisor or systemd to manage application processes:

#### Supervisor (`/etc/supervisor/conf.d/flask.conf`)

```ini
[program:flask_app]
command=/path/to/venv/bin/gunicorn --workers 4 app:app
directory=/path/to/app
user=www-data
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/flask_app.log
```

Start:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start flask_app
```

#### Systemd (`/etc/systemd/system/flask.service`)

```ini
[Unit]
Description=Flask Application
After=network.target

[Service]
Type=notify
User=www-data
WorkingDirectory=/path/to/app
ExecStart=/path/to/venv/bin/gunicorn --workers 4 app:app
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
```

Start:

```bash
sudo systemctl daemon-reload
sudo systemctl start flask
sudo systemctl enable flask
```

## WSGI Interface

Flask implements the WSGI interface:

```python
# src/flask/app.py
class Flask:
    def wsgi_app(self, environ, start_response):
        """The actual WSGI application."""
        # ... creates context, dispatches request, returns response ...
        return response(environ, start_response)

    def __call__(self, environ, start_response):
        """Callable WSGI entry point."""
        return self.wsgi_app(environ, start_response)

# Usage with any WSGI server:
app = Flask(__name__)
# app is now a WSGI callable
```

WSGI servers call the app like:

```python
# What the WSGI server does
status = None
headers = []

def start_response(status_str, response_headers):
    global status, headers
    status = status_str
    headers = response_headers

# Call the Flask app
response_data = app(environ, start_response)

# Send response to client
send_status(status)
send_headers(headers)
for chunk in response_data:
    send_body(chunk)
```

## Database Connections

In production, maintain database connections:

```python
from flask import g
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

@app.before_request
def before_request():
    g.db = db.engine.connect()

@app.teardown_request
def teardown_request(exc):
    if hasattr(g, 'db'):
        g.db.close()
```

Or use connection pooling:

```python
from sqlalchemy import create_engine, pool

engine = create_engine(
    'postgresql://user:pass@localhost/dbname',
    poolclass=pool.QueuePool,
    pool_size=10,
    max_overflow=20,
)
```

## Configuration Management

### Environment-Based Config

```python
import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY')
    DEBUG = False
    TESTING = False

class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True

class ProductionConfig(Config):
    DEBUG = False

class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
}

app.config.from_object(config[os.environ.get('FLASK_ENV', 'production')])
```

### Secrets Management

Never commit secrets to version control:

```python
# ✗ Bad
app.config['SECRET_KEY'] = 'hardcoded-secret'
app.config['DATABASE_PASSWORD'] = 'hardcoded-password'

# ✓ Good: use environment variables
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config['DATABASE_PASSWORD'] = os.environ['DATABASE_PASSWORD']

# ✓ Better: use secrets management service
import hvac
client = hvac.Client(url='https://vault.example.com')
app.config['SECRET_KEY'] = client.secrets.kv.read_secret_version(path='flask/secret_key')
```

## Monitoring and Logging

### Application Logging

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure logging
if not app.debug:
    handler = RotatingFileHandler('app.log', maxBytes=10240, backupCount=10)
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    app.logger.addHandler(handler)
    app.logger.setLevel(logging.INFO)

# Use in app
app.logger.info(f'User {user_id} logged in')
app.logger.error(f'Database error: {e}')
```

### Health Checks

```python
@app.route('/health')
def health():
    """Health check endpoint for monitoring."""
    checks = {
        'database': check_database(),
        'cache': check_cache(),
    }
    status = 'healthy' if all(checks.values()) else 'unhealthy'
    return {'status': status, 'checks': checks}
```

## Gotchas & Conventions

> ⚠️ **Gotcha**: The development server is single-threaded and not suitable for production.
>
> Werkzeug's development server cannot handle multiple concurrent requests. Always use a production WSGI server (Gunicorn, uWSGI) with multiple workers.
> ```bash
> # Development only
> flask run
>
> # Production
> gunicorn --workers 4 app:app
> ```
> See `src/flask/app.py:L1550-L1625`.

> 📌 **Convention**: Use environment variables for configuration:
> ```python
> # Good
> app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
>
> # Not for production
> app.config['DEBUG'] = False  # Never set DEBUG=True in production
> ```

> 💡 **Tip**: Use a reverse proxy (Nginx) in production for:
> - **SSL termination** — Handle HTTPS certificates
> - **Static file serving** — Bypass Flask for static assets
> - **Load balancing** — Distribute to multiple workers
> - **Compression** — gzip responses
> - **Caching** — Cache static content

## Cross-References

- **Parent**: [01 — Overview](01-overview.md)
- **Related**: [02 — Application Core](02-application-core.md)
- **Related**: [15 — CLI System](15-cli-system.md)
- **Related**: [14 — Testing Framework](14-testing-framework.md)
