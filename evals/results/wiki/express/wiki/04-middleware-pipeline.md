# 4 — Middleware Pipeline

## Relevant Source Files

- `lib/application.js:L152-L178` — `app.handle()` request dispatcher
- `lib/application.js:L190-L244` — `app.use()` middleware registration
- `lib/express.js:L37-L39` — App as middleware function
- External `router` module — Middleware chain execution
- `test/app.use.js` — Comprehensive middleware tests (430+ lines)
- `test/middleware.basic.js` — Basic middleware patterns

## TL;DR

Express middleware is a series of functions that process HTTP requests. Each middleware can modify the request/response, call `next()` to pass control to the next middleware, or send a response to end the chain. Error handlers (4-parameter middleware) are invoked when a previous middleware calls `next(err)`. The entire system is implemented via the external `router` module.

## Overview

The middleware pipeline is the backbone of request processing in Express. Instead of a rigid framework that dictates what happens at each stage, Express gives developers the freedom to compose their own processing pipeline by stacking middleware.

Middleware is simply a function with signature:

```javascript
(req, res, next) => { ... }
```

Or for error handling:

```javascript
(err, req, res, next) => { ... }
```

When a request arrives, it flows through the middleware chain in order. Each middleware can:

1. **Process** the request (e.g., log it, parse body, authenticate user)
2. **Forward** control to the next middleware by calling `next()`
3. **Skip** remaining middleware by calling `next(err)` (jumps to error handlers)
4. **End** the request by sending a response (e.g., `res.send()`)
5. **Do nothing** (pass control implicitly to next middleware)

The middleware pipeline operates at two levels:

- **Global middleware** — Registered via `app.use()`, runs for all requests
- **Route-specific middleware** — Attached to specific routes, runs only when route matches

## Architecture Diagram

```mermaid
graph TD
    subgraph Request["Request Arrives"]
        IN["HTTP Request"]
    end

    subgraph Global["Global Middleware Chain<br/>(app.use registered)"]
        MW1["Middleware 1<br/>Logger"]
        MW2["Middleware 2<br/>Body Parser"]
        MW3["Middleware 3<br/>Auth Check"]
    end

    subgraph Routing["Route Matching"]
        ROUTE["Match path & method"]
        FOUND{"Match found?"}
    end

    subgraph RouteHandlers["Route Handlers<br/>(matched route's middleware stack)"]
        RH1["Route Handler 1"]
        RH2["Route Handler 2"]
    end

    subgraph Error["Error Handling"]
        EH["Error Handler<br/>(4-parameter middleware)"]
    end

    subgraph Response["Response"]
        OUT["res.send() / res.json() / etc."]
    end

    subgraph Final["Final Handler"]
        FH["finalhandler<br/>404 or 500"]
    end

    IN --> MW1
    MW1 -->|next()| MW2
    MW2 -->|next()| MW3
    MW3 -->|next()| ROUTE

    ROUTE --> FOUND
    FOUND -->|Yes| RH1
    FOUND -->|No| FH

    RH1 -->|next()| RH2
    RH2 -->|next(err)| EH
    RH1 -->|res.send()| OUT
    RH2 -->|res.send()| OUT
    EH -->|res.send()| OUT

    OUT --> Response

    RH1 -.->|error| EH
    RH2 -.->|error| EH

    style MW1 fill:#4a7ba7,stroke:#2d5a8e,color:#fff
    style MW2 fill:#4a7ba7,stroke:#2d5a8e,color:#fff
    style MW3 fill:#4a7ba7,stroke:#2d5a8e,color:#fff
    style RH1 fill:#6a9bc4,stroke:#4a7ba7,color:#fff
    style RH2 fill:#6a9bc4,stroke:#4a7ba7,color:#fff
    style EH fill:#d9534f,stroke:#c9302c,color:#fff
```

## Key Concepts

| Concept | Description | Source |
|---------|-------------|--------|
| **Middleware** | A function that processes a request and either calls `next()` or ends the request. Signature: `(req, res, next) => void`. | `lib/application.js:L190+` |
| **Handler** | A middleware function registered to a route or globally. Same as middleware. | [Same as above] |
| **Chain** | Ordered sequence of middleware/handlers. Each calls `next()` to pass control to the next. | External `router` module |
| **Error Handler** | Special middleware with 4 parameters: `(err, req, res, next) => void`. Invoked when a handler calls `next(err)`. | `lib/application.js:L152+` |
| **Middleware Stack** | The list of middleware functions registered for a path or globally. Executed in registration order. | External `router` module |
| **Global Middleware** | Middleware registered via `app.use(fn)` that runs for all requests. | `lib/application.js:L190-L244` |
| **Route Middleware** | Middleware registered via `app.METHOD(path, fn)` that runs only for matching routes. | [External `router` module] |
| **Next Function** | A callback passed to each middleware. Calling `next()` passes control to the next middleware. | External `router` module |
| **Termination** | A middleware ends the chain by calling a response method (`res.send()`, etc.) without calling `next()`. | [Standard pattern] |
| **Error Propagation** | When a middleware calls `next(err)`, the error is passed through error handlers until one responds. | External `router` module |

## Component Reference

| Component | Type | Responsibility | Source |
|-----------|------|-----------------|--------|
| `app.handle(req, res, callback)` | method | Main request dispatcher. Sets up prototypes, initializes locals, calls router.handle(). | `lib/application.js:L152-L178` |
| `app.use(path?, fn|array)` | method | Registers global or path-prefixed middleware. Flattens arrays, handles sub-apps. | `lib/application.js:L190-L244` |
| `app.get(path, fn...)` | method | Registers route handler for GET. Can chain multiple handlers. | [Generated] |
| `app.post(path, fn...)` | method | Registers route handler for POST. Can chain multiple handlers. | [Generated] |
| `app.all(path, fn...)` | method | Registers route handler for all HTTP methods. | [Generated] |
| `next()` | function | Callback to pass control to next middleware. If called with error, skips to error handlers. | External `router` module |
| `router.handle(req, res, done)` | method | Core dispatcher. Iterates through middleware, calls handler chain. | External `router` module |
| Error handler | middleware | 4-parameter function: `(err, req, res, next)`. Invoked on `next(err)`. | [Error handling pattern] |

## How It Works

### Request Dispatch

When an HTTP request arrives at the app:

1. Node.js calls the app function directly: `app(req, res)` (since app is a function) → `app.handle(req, res)` (`lib/express.js:L37-L39`)

2. `app.handle()` performs setup (`lib/application.js:L152-L178`):

```javascript
app.handle = function handle(req, res, callback) {
  // Set up final handler
  var done = callback || finalhandler(req, res, {
    env: this.get('env'),
    onerror: logerror.bind(this)
  });

  // Set X-Powered-By header if enabled
  if (this.enabled('x-powered-by')) {
    res.setHeader('X-Powered-By', 'Express');
  }

  // Create circular references
  req.res = res;
  res.req = req;

  // Alter prototypes to Express versions
  Object.setPrototypeOf(req, this.request);
  Object.setPrototypeOf(res, this.response);

  // Setup locals
  if (!res.locals) {
    res.locals = Object.create(null);
  }

  // Dispatch to router
  this.router.handle(req, res, done);
};
```

Key points:

- **Prototype chain alteration** — `req` and `res` are re-prototyped to the Express request/response objects, gaining all Express methods
- **Locals initialization** — `res.locals` is created, allowing template variables to be set
- **Router delegation** — Control passes to the router's `handle()` method

3. The router matches the request to routes and executes handlers.

### Middleware Execution Order

Global middleware registered via `app.use()` is executed in registration order:

```javascript
app.use((req, res, next) => {
  console.log('1. Middleware 1');
  next();
});

app.use((req, res, next) => {
  console.log('2. Middleware 2');
  next();
});

app.get('/', (req, res) => {
  console.log('3. Route handler');
  res.send('OK');
});

// Request: GET /
// Output: 1. Middleware 1
//         2. Middleware 2
//         3. Route handler
```

After global middleware, route-specific handlers execute if the route matches.

### Middleware Registration

`app.use()` handles multiple scenarios (`lib/application.js:L190-L244`):

```javascript
app.use(fn)                    // Global middleware for all routes
app.use(path, fn)              // Middleware for /path and sub-paths
app.use(path, [fn1, fn2])      // Array of middleware (flattened)
app.use(subapp)                // Mount another Express app
```

Implementation:

```javascript
app.use = function use(fn) {
  var offset = 0;
  var path = '/';

  // Determine if first arg is a path
  if (typeof fn !== 'function') {
    var arg = fn;
    while (Array.isArray(arg) && arg.length !== 0) {
      arg = arg[0];
    }
    if (typeof arg !== 'function') {
      offset = 1;
      path = fn;
    }
  }

  // Flatten arrays of middleware
  var fns = flatten.call(slice.call(arguments, offset), Infinity);

  if (fns.length === 0) {
    throw new TypeError('app.use() requires a middleware function');
  }

  var router = this.router;

  fns.forEach(function (fn) {
    // Check if it's a sub-app (has .handle and .set)
    if (!fn || !fn.handle || !fn.set) {
      return router.use(path, fn);
    }

    // Mount sub-app with prototype wrapping
    fn.mountpath = path;
    fn.parent = this;

    router.use(path, function mounted_app(req, res, next) {
      var orig = req.app;
      fn.handle(req, res, function (err) {
        Object.setPrototypeOf(req, orig.request);
        Object.setPrototypeOf(res, orig.response);
        next(err);
      });
    });

    fn.emit('mount', this);
  }, this);

  return this;
};
```

Key behaviors:

- **Flexible path parameter** — Can be omitted for global middleware
- **Array flattening** — Nested arrays are flattened
- **Sub-app detection** — If middleware has `.handle()` and `.set()` methods, it's treated as an Express app and mounted with prototype handling
- **Method chaining** — Returns `this` to allow chaining

### Error Handling

When a middleware calls `next(err)`, Express jumps to error handlers:

```javascript
app.get('/', (req, res, next) => {
  const err = new Error('Something went wrong');
  next(err);  // Pass error to error handlers
});

// Error handler (must have 4 parameters)
app.use((err, req, res, next) => {
  res.status(500).send('Error: ' + err.message);
});
```

Error handlers are identified by their 4-parameter signature. When `next(err)` is called, the router skips normal handlers and invokes error handlers.

### Async Middleware

Express 5+ supports async handlers:

```javascript
app.get('/', async (req, res, next) => {
  try {
    const user = await fetchUser(req.params.id);
    res.json(user);
  } catch (err) {
    next(err);  // Errors caught and passed to error handlers
  }
});
```

However, automatic error catching is not guaranteed. Best practice is to wrap async calls or use middleware that wraps handlers.

### Handler Chaining

Multiple handlers can be registered for a single route:

```javascript
app.get('/user/:id',
  // Middleware 1: Validate
  (req, res, next) => {
    if (!req.params.id) {
      return res.status(400).send('Missing ID');
    }
    next();
  },

  // Middleware 2: Authenticate
  (req, res, next) => {
    if (!req.headers.authorization) {
      return res.status(401).send('Not authenticated');
    }
    next();
  },

  // Handler: Send response
  (req, res) => {
    res.json({ id: req.params.id });
  }
);
```

Handlers execute in order. If any sends a response, the chain stops.

## Configuration & Environment

### Middleware Stack Management

The middleware stack is managed internally by the `router` module. Express provides no public API to inspect or modify the stack, but you can log handlers during development:

```javascript
app.use((req, res, next) => {
  console.log(`${req.method} ${req.path}`);
  next();
});
```

### Conditional Middleware

Middleware can be conditional:

```javascript
// Only for development
if (app.get('env') === 'development') {
  app.use(require('morgan')('dev'));
}

// Only for API routes
app.use('/api', (req, res, next) => {
  res.setHeader('Content-Type', 'application/json');
  next();
});

// Based on route pattern
app.use(/^\/admin/, requireAuth);
```

## Extension Points

### Custom Middleware

Developers can create custom middleware:

```javascript
// Logging middleware
function loggerMiddleware(req, res, next) {
  console.log(`${req.method} ${req.path}`);
  next();
}

// Authentication middleware
function authMiddleware(req, res, next) {
  const token = req.headers.authorization?.replace('Bearer ', '');
  if (!token) {
    return res.status(401).send('Unauthorized');
  }
  req.user = verifyToken(token);
  next();
}

// Data loading middleware
function loadUser(req, res, next) {
  const user = fetchUser(req.params.id);
  req.user = user;
  next();
}

// Apply them
app.use(loggerMiddleware);
app.use(authMiddleware);
app.get('/user/:id', loadUser, (req, res) => {
  res.json(req.user);
});
```

### Error Handling Middleware

Error handlers must have exactly 4 parameters:

```javascript
// Error handler for JSON parse errors
app.use(express.json());

app.use((err, req, res, next) => {
  if (err instanceof SyntaxError && err.status === 400 && 'body' in err) {
    return res.status(400).json({ error: 'Invalid JSON' });
  }
  next(err);
});

// Generic error handler
app.use((err, req, res, next) => {
  res.status(err.status || 500).json({
    error: err.message,
    status: err.status || 500
  });
});
```

### Sub-App Mounting

Express apps can be mounted as middleware:

```javascript
const main = express();
const api = express();
const admin = express();

api.get('/users', (req, res) => res.json([...]));
admin.post('/users', (req, res) => res.json({...}));

main.use('/api', api);      // Mount api under /api
main.use('/admin', admin);  // Mount admin under /admin

main.listen(3000);
```

When a sub-app is mounted:

1. Its `mountpath` property is set to the mount path
2. Its `parent` property is set to the parent app
3. It emits a 'mount' event
4. It inherits parent's request/response prototypes and settings

## Gotchas & Conventions

> ⚠️ **Gotcha**: If a middleware doesn't call `next()` or send a response, the request will hang. Always ensure every middleware either calls `next()` or sends a response.
> Source: `lib/application.js:L152+`, standard middleware pattern

> ⚠️ **Gotcha**: The order of middleware registration matters. If you register an error handler before regular middleware, errors from later middleware won't reach it because error handlers are only invoked when `next(err)` is called.
> Source: External `router` module behavior

> ⚠️ **Gotcha**: Error handlers must have exactly 4 parameters: `(err, req, res, next)`. If you define only 3 parameters, Express will treat it as regular middleware, not an error handler.
> Source: Standard Express pattern

> 📌 **Convention**: Place error handlers last, after all other middleware and routes. They should be the final middleware in the chain.
> Source: Best practices

> 📌 **Convention**: Use `app.use()` for middleware that applies to all routes. Use `app.METHOD()` or `app.route()` for route-specific handlers.
> Source: Best practices

> 💡 **Tip**: Use middleware for cross-cutting concerns (logging, authentication, parsing). Use route handlers for business logic.
> Source: Best practices

> 💡 **Tip**: If you need to run async code, use `async/await` and call `next(err)` in a catch block, or use wrapper middleware.
> Source: [NEEDS INVESTIGATION]

## Common Middleware Patterns

### Chain of Responsibility

```javascript
app.get('/protected',
  authenticateToken,
  authorizeRole('admin'),
  checkResourceOwnership,
  handleRequest
);
```

### Conditional Next

```javascript
app.use((req, res, next) => {
  if (req.path === '/health') {
    return res.send('OK');  // Don't call next()
  }
  next();
});
```

### Error Recovery

```javascript
app.use((req, res, next) => {
  res.on('finish', () => {
    console.log(`${req.method} ${req.path} - ${res.statusCode}`);
  });
  next();
});
```

## Cross-References

- For routing details, see [Page 3 — Routing System](03-routing-system.md)
- For request/response methods, see [Page 5 — Request & Response](05-request-response.md)
- For app configuration, see [Page 2 — Application Core](02-application-core.md)
- For built-in middleware, see [Page 7 — Static Files & Content Handling](07-static-middleware.md)
- For architecture overview, see [Page 1 — Overview](01-overview.md)

---

## Test Coverage

Comprehensive middleware tests:

- `test/app.use.js` — `app.use()` tests (430+ lines)
- `test/middleware.basic.js` — Basic middleware patterns
- `test/app.routes.error.js` — Error handling
- `test/app.router.js` — Router integration with middleware (1210+ lines)
