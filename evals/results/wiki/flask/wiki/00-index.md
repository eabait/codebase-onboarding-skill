# Flask Codebase Wiki

A comprehensive guide to understanding and navigating the Flask web framework codebase.

## Table of Contents

### Core Architecture
- **[01-overview.md](#overview-page)** — Architecture overview, major components, and design principles
- **[02-application-core.md](#application-core)** — The Flask application object and lifecycle
- **[03-request-response-cycle.md](#request-response-cycle)** — How Flask processes HTTP requests and generates responses

### Routing & Blueprints
- **[04-routing-system.md](#routing-system)** — URL routing, rules, and converters
- **[05-blueprints.md](#blueprints)** — Blueprint system for modular applications

### Context & Globals
- **[06-context-management.md](#context-management)** — Application and request context stack
- **[07-globals-and-proxies.md](#globals-and-proxies)** — Thread-local proxies and global objects

### Core Features
- **[08-templating.md](#templating)** — Jinja2 integration and template rendering
- **[09-sessions-and-cookies.md](#sessions)** — Secure session handling
- **[10-configuration.md](#configuration)** — Configuration system and environment handling

### Advanced Features
- **[11-error-handling.md](#error-handling)** — Exception handling and error pages
- **[12-signals-system.md](#signals)** — Event signaling system
- **[13-json-handling.md](#json)** — JSON encoding and decoding

### Testing & Development
- **[14-testing-framework.md](#testing)** — Test client and testing utilities
- **[15-cli-system.md](#cli)** — Command-line interface and commands
- **[16-build-and-deployment.md](#build)** — Build system, packaging, and deployment

---

## Quick Navigation by Task

### I want to understand...

**How Flask works**
→ Start with [01-overview.md](01-overview.md), then [02-application-core.md](02-application-core.md)

**How requests flow through the app**
→ [03-request-response-cycle.md](03-request-response-cycle.md) and [04-routing-system.md](04-routing-system.md)

**How to structure a large Flask app**
→ [05-blueprints.md](05-blueprints.md) and [02-application-core.md](02-application-core.md)

**How context works (g, request, session)**
→ [06-context-management.md](06-context-management.md) and [07-globals-and-proxies.md](07-globals-and-proxies.md)

**How to render templates**
→ [08-templating.md](08-templating.md)

**How to handle errors**
→ [11-error-handling.md](11-error-handling.md)

**How to test Flask apps**
→ [14-testing-framework.md](14-testing-framework.md)

---

## Key Statistics

- **Primary Language**: Python (16,838 lines)
- **Total Files**: 206 (79 Python files)
- **Main Modules**: 18 modules in `src/flask/`
- **Core Dependencies**: Werkzeug, Jinja2, Click, Blinker, ItsDangerous, MarkupSafe
- **Python Version**: >=3.10

## Architecture at a Glance

Flask follows a layered architecture:

```
Request
  ↓
WSGI Application (Flask.wsgi_app)
  ↓
Middleware Stack
  ↓
Request Context (→ context stack)
  ↓
Route Matching (URL Map)
  ↓
View Function Execution
  ↓
Response Generation
  ↓
Response Serialization
  ↓
Browser/Client
```

## Key Concepts

| Concept | Description | Key File |
|---------|-------------|----------|
| **Flask** | The main application object and WSGI entry point | `src/flask/app.py` |
| **Blueprint** | Reusable modular components for organizing code | `src/flask/blueprints.py` |
| **Request Context** | Holds request-specific state (request, session, g) | `src/flask/ctx.py` |
| **AppContext** | Holds application-wide state during request handling | `src/flask/ctx.py` |
| **Routing** | Maps URLs to view functions using Werkzeug's routing | `src/flask/app.py` (integrated) |
| **Signals** | Event system for application lifecycle events | `src/flask/signals.py` |
| **Session** | Secure, cookie-based session storage | `src/flask/sessions.py` |
| **Config** | Application configuration management | `src/flask/config.py` |

## Development Quick Start

Flask is organized as a single Python package with clear module boundaries. Key entry points:

1. **Creating an app**: `from flask import Flask; app = Flask(__name__)`
2. **Defining routes**: `@app.route('/path')` decorator
3. **Running the app**: `flask run` or `app.run()`
4. **Testing**: Use `app.test_client()` to create a test client

See [02-application-core.md](02-application-core.md) for initialization details.

---

*This wiki was generated from the Flask codebase analysis. All file references are accurate as of the current codebase version.*
