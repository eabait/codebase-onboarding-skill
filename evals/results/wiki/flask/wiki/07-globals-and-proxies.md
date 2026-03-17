# 07 — Globals and Proxies

## Relevant Source Files

- `src/flask/globals.py` — Proxy objects and context variables (77 lines)
- `src/flask/ctx.py` — Context stack classes (540 lines)
- Werkzeug `local.py` — LocalProxy and LocalStack implementation

## TL;DR

Flask provides thread-local proxy objects (request, session, g, current_app) that automatically resolve to the correct object for the current thread. These proxies implement the LocalProxy pattern from Werkzeug, allowing global access to request-specific data without explicit parameter passing. Each thread gets its own isolated view of these proxies, making them safe for concurrent requests.

## Overview

The proxy system solves a fundamental challenge: how to provide global access to request-specific data in a thread-safe manner. Without proxies, you'd need to pass request objects through every function call.

### The Proxy Pattern

A proxy object behaves like the object it represents but redirects all operations:

```python
# Without proxy: pass through function chain
request_obj = get_request_from_environ(environ)
user = get_current_user(request_obj)
render_page(request_obj, user)

# With proxy: access globally via LocalProxy
from flask import request
user = get_current_user()  # Access request via proxy
render_page()              # No parameters needed
```

## Architecture Diagram

```mermaid
graph TD
    subgraph Thread1["Thread 1 (Request A)"]
        T1Stack["Context Stack<br/>(RequestContext A)"]
        T1Proxy["request proxy<br/>(refers to A)"]
        T1View["View function<br/>accesses request"]
    end

    subgraph Thread2["Thread 2 (Request B)"]
        T2Stack["Context Stack<br/>(RequestContext B)"]
        T2Proxy["request proxy<br/>(refers to B)"]
        T2View["View function<br/>accesses request"]
    end

    subgraph ThreadLocal["Thread-Local Storage"]
        TLS["LocalStack + ContextVar<br/>(Isolated per thread)"]
    end

    T1Stack -.->|uses| TLS
    T2Stack -.->|uses| TLS
    T1Proxy -->|resolves to| T1Stack
    T2Proxy -->|resolves to| T2Stack
    T1View -->|accesses| T1Proxy
    T2View -->|accesses| T2Proxy

    Note over T1Proxy,T2Proxy: Same proxy object,<br/>different values per thread

    style T1Proxy fill:#2d5a8e,stroke:#1a3a5c,color:#fff
    style T2Proxy fill:#2d5a8e,stroke:#1a3a5c,color:#fff
```

## Key Concepts

| Concept | Description | Source |
|---------|-------------|--------|
| **LocalProxy** | Werkzeug proxy that redirects to thread-local object | `werkzeug.local.LocalProxy` |
| **LocalStack** | Werkzeug thread-local stack for context stacks | `werkzeug.local.LocalStack` |
| **ContextVar** | Python contextvars for async support | `contextvars` module |
| **Thread-local storage** | Storage isolated per thread | Python threading module |
| **Lazy evaluation** | Proxy doesn't look up value until accessed | Design pattern |
| **Object identity** | Proxy redirects __getattr__, __setattr__, etc. | Special methods |

## Component Reference

| Component | Type | Responsibility | Source |
|-----------|------|-----------------|--------|
| `request` | proxy | Proxy to RequestContext.request | `src/flask/globals.py:L35-L50` |
| `session` | proxy | Proxy to RequestContext.session | `src/flask/globals.py:L55-L70` |
| `g` | proxy | Proxy to AppContext.g | `src/flask/globals.py:L75-L90` |
| `current_app` | proxy | Proxy to active Flask app | `src/flask/globals.py:L10-L30` |
| `_request_ctx_stack` | LocalStack | Stack of RequestContext objects | `src/flask/ctx.py:L380-L400` |
| `_app_ctx_stack` | LocalStack | Stack of AppContext objects | `src/flask/ctx.py:L400-L420` |
| `_cv_app` | ContextVar | Context variable for current app | `src/flask/globals.py:L5-L10` |

## How Proxies Work

### LocalProxy Implementation

Werkzeug's `LocalProxy` in `werkzeug.local`:

```python
# Simplified version
class LocalProxy:
    def __init__(self, local_fn):
        """
        local_fn: callable that returns the object for current thread
        """
        self._get_current_object = local_fn

    def __getattr__(self, name):
        """Redirect attribute access to the proxied object."""
        return getattr(self._get_current_object(), name)

    def __setattr__(self, name, value):
        """Redirect attribute setting to the proxied object."""
        if name in ('_get_current_object', '_local'):
            object.__setattr__(self, name, value)
        else:
            setattr(self._get_current_object(), name, value)

    def __repr__(self):
        """Delegate repr to proxied object."""
        return repr(self._get_current_object())
```

### The Proxy Chain

In `src/flask/globals.py`:

```python
# 1. Define lookup function
def _cv_request():
    """Return the current RequestContext."""
    top = _request_ctx_stack.top
    if top is None:
        raise RuntimeError('No request context.')
    return top

# 2. Create proxy to RequestContext
_request_ctx = LocalProxy(_cv_request)

# 3. Create proxies to attributes of RequestContext
request = LocalProxy(lambda: _request_ctx.request)
session = LocalProxy(lambda: _request_ctx.session)
g = LocalProxy(lambda: _request_ctx.g)
```

When you access `request.method`:

```
request.method
  ↓
LocalProxy.__getattr__('method')
  ↓
_get_current_object().method
  ↓
_cv_request().request.method
  ↓
_request_ctx_stack.top.request.method
  ↓
Current thread's RequestContext.request.method
```

### LocalStack Implementation

`LocalStack` from Werkzeug provides thread-isolated stack operations:

```python
# Simplified from werkzeug.local
class LocalStack:
    def __init__(self):
        self._local = threading.local()

    def push(self, obj):
        """Push object to this thread's stack."""
        stack = getattr(self._local, 'stack', None)
        if stack is None:
            stack = []
            self._local.stack = stack
        stack.append(obj)

    def pop(self):
        """Pop object from this thread's stack."""
        try:
            return self._local.stack.pop()
        except (AttributeError, IndexError):
            raise RuntimeError('Stack is empty.')

    @property
    def top(self):
        """Return top of this thread's stack without removing."""
        try:
            return self._local.stack[-1]
        except (AttributeError, IndexError):
            return None
```

## Cross-References

- **Parent**: [01 — Overview](01-overview.md)
- **Related**: [06 — Context Management](06-context-management.md)
- **Related**: [03 — Request/Response Cycle](03-request-response-cycle.md)
- **Related**: [14 — Testing Framework](14-testing-framework.md)
