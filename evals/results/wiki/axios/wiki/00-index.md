# Axios Onboarding Wiki — Complete Index

A promise-based HTTP client library for the browser and Node.js with interceptors, transformations, and adapter architecture.

## Quick Navigation

**Core Concepts**
- [01 — Architecture Overview](#01--architecture-overview)
- [02 — HTTP Client Core](#02--http-client-core)
- [03 — Request Pipeline](#03--request-pipeline)
- [04 — Interceptors & Middleware](#04--interceptors--middleware)
- [05 — Adapters](#05--adapters)
- [06 — Configuration & Config Merging](#06--configuration--config-merging)
- [07 — Error Handling & Cancellation](#07--error-handling--cancellation)
- [08 — Build & Development](#08--build--development)
- [09 — Testing Infrastructure](#09--testing-infrastructure)

---

## [01 — Architecture Overview](01-overview.md)

**Scope:** High-level system architecture, core abstractions, and entry points.

- **TL;DR:** Axios is a promise-based HTTP client built around the `Axios` class that orchestrates request/response interceptors, config merging, and adapter selection to support both browser (XHR) and Node.js (HTTP/Fetch) environments.

**Covers:**
- Request/response lifecycle
- Interceptor chains
- Adapter pattern for environment abstraction
- Default configuration system

---

## [02 — HTTP Client Core](02-http-client-core.md)

**Scope:** The `Axios` class, instance creation, and public API methods.

- **TL;DR:** The `Axios` class is the central orchestrator: it holds defaults and interceptors, implements HTTP method shortcuts (get, post, put, etc.), and provides the `request()` method that drives the entire request/response pipeline.

**Covers:**
- `Axios` class constructor and lifecycle
- HTTP method aliases (get, post, patch, delete, etc.)
- Instance creation and `axios.create()`
- Config validation
- Method shortcuts

---

## [03 — Request Pipeline](03-request-pipeline.md)

**Scope:** The multi-step request execution flow from method call to response settlement.

- **TL;DR:** Requests flow through five stages: (1) config merging, (2) request interceptors, (3) request transformation, (4) adapter dispatch, (5) response transformation, and (6) response interceptors—with error handling and cancellation checks at each step.

**Covers:**
- `_request()` execution flow
- Config validation and merging
- Request and response transformation
- Interceptor execution order
- Promise chain orchestration
- Error propagation

---

## [04 — Interceptors & Middleware](04-interceptors.md)

**Scope:** Interceptor registration, execution, and the `InterceptorManager` implementation.

- **TL;DR:** `InterceptorManager` maintains a stack of fulfilled/rejected handlers. Request interceptors run before dispatch, response interceptors run after. Synchronous execution is supported via introspection of handler properties.

**Covers:**
- `InterceptorManager` class and API
- Interceptor registration (`use()`, `eject()`, `clear()`)
- Execution order and synchronous vs. asynchronous handling
- Multiple interceptor chains
- Conditional execution (`runWhen`)

---

## [05 — Adapters](05-adapters.md)

**Scope:** Adapter selection, the HTTP/XHR/Fetch adapter abstraction, and environment detection.

- **TL;DR:** Adapters are environment-specific transports. The `adapters` module provides a `getAdapter()` function that selects from HTTP (Node.js), XHR (browser), or Fetch API based on config and environment. Each adapter implements the same contract: `adapter(config) → Promise<response>`.

**Covers:**
- Adapter selection strategy
- HTTP adapter (Node.js)
- XHR adapter (browser)
- Fetch adapter (fetch API)
- Adapter resolution and fallback behavior

---

## [06 — Configuration & Config Merging](06-config-merging.md)

**Scope:** The config system, default configuration, and deep merge semantics.

- **TL;DR:** `mergeConfig()` combines instance defaults with request-specific config using strategy functions that determine merge behavior per property (e.g., `headers` are merged deeply, `timeout` uses the source value). Headers support case-insensitive merging via the `AxiosHeaders` class.

**Covers:**
- Default configuration structure
- `mergeConfig()` algorithm and strategies
- `AxiosHeaders` class and case-insensitive header handling
- Configuration precedence
- Transitional options for backward compatibility

---

## [07 — Error Handling & Cancellation](07-error-handling.md)

**Scope:** `AxiosError`, `CancelToken`, abort signals, and error recovery strategies.

- **TL;DR:** `AxiosError` wraps all errors with request/response context. Cancellation supports two mechanisms: (1) `CancelToken` (promise-based, deprecated), (2) `AbortSignal` (modern, preferred). Both integrate into `dispatchRequest()` to prevent sending or complete canceled requests.

**Covers:**
- `AxiosError` structure and properties
- `CancelToken` lifecycle
- `AbortSignal` and `AbortController` integration
- Cancellation points in the request pipeline
- Error transformation in adapters
- Custom error handling

---

## [08 — Build & Development](08-build-development.md)

**Scope:** Build system (Rollup), development toolchain, and release process.

- **TL;DR:** Axios uses Rollup with plugins for Node resolution, Babel transpilation, and tree-shaking. npm scripts automate builds, testing (Vitest), linting (ESLint), and module publishing to support CJS, ESM, and UMD formats.

**Covers:**
- Rollup configuration and build pipeline
- Module format support (CJS/ESM/UMD)
- Babel transpilation
- Development scripts
- Testing setup and commands
- Linting and code quality

---

## [09 — Testing Infrastructure](09-testing.md)

**Scope:** Test organization, test runners (Vitest), and testing strategy.

- **TL;DR:** Axios uses Vitest for unit/integration tests (`tests/`) with browser and module tests organized by feature. Smoke tests in `tests/smoke/` validate real-world scenarios. Legacy tests in `test/specs/` and `test/unit/` test individual components.

**Covers:**
- Test structure and organization
- Vitest configuration for browser and Node.js
- Unit test patterns
- Integration tests
- Smoke tests
- Module loading and format tests

---

## Legend

| Symbol | Meaning |
|--------|---------|
| `[NEEDS INVESTIGATION]` | Claim not yet verified in source code—reader should check. |
| `src/core/Axios.js:L45-L87` | Source file location with line range. |
| **Bold** | Key classes, functions, or modules. |
| _Italic_ | Terms being defined. |

---

## How to Use This Wiki

1. **Start here:** Read [01 — Architecture Overview](01-overview.md) for the big picture.
2. **Dive into a subsystem:** Each subsequent page documents a specific component or feature.
3. **Follow cross-references:** Pages link to related topics—use them to navigate between related systems.
4. **Verify claims:** All claims cite source files; read the actual code for details beyond the wiki.

---

## File Organization

```
lib/
├── axios.js                  # Main entry point; factory function
├── core/
│   ├── Axios.js              # Core class
│   ├── InterceptorManager.js # Interceptor stack
│   ├── dispatchRequest.js    # Request dispatch orchestrator
│   ├── mergeConfig.js        # Config merging logic
│   ├── AxiosHeaders.js       # Header management
│   ├── AxiosError.js         # Error wrapper
│   ├── transformData.js      # Request/response transformation
│   └── settle.js             # Response settlement
├── adapters/
│   ├── adapters.js           # Adapter resolution
│   ├── http.js               # Node.js HTTP adapter
│   ├── xhr.js                # Browser XHR adapter
│   └── fetch.js              # Fetch API adapter
├── defaults/
│   ├── index.js              # Default configuration
│   └── transitional.js       # Backward compatibility flags
├── cancel/
│   ├── CancelToken.js        # Promise-based cancellation
│   ├── CanceledError.js      # Cancellation error
│   └── isCancel.js           # Cancellation check
├── helpers/                  # 40+ utility functions
│   ├── buildURL.js
│   ├── toFormData.js
│   ├── parseHeaders.js
│   └── [many more]
├── platform/                 # Environment detection
│   ├── browser/
│   └── node/
└── env/                      # Environment-specific config
    ├── data.js
    └── classes/
```

---

## Key Statistics

- **Total Files:** 327
- **Core JavaScript:** ~25,240 lines (lib + src)
- **Tests:** ~95+ test files (unit, integration, browser, module, smoke)
- **Languages:** JavaScript (primary), TypeScript (typings and examples)
- **Framework Integrations:** Express (dev dependency for test servers), Vitest (test runner)
- **Module Formats:** CJS, ESM, UMD, TypeScript definitions (*.d.ts)

---

## Questions to Explore Further

After reading this wiki, use these questions to guide code exploration:

1. How does the interceptor chain handle synchronous vs. asynchronous handlers?
2. What's the strategy for selecting adapters in non-browser, non-Node.js environments?
3. How does `mergeConfig()` handle custom config properties?
4. What are the security implications of the cancellation mechanism?
5. How do streaming and progress events work in the HTTP adapter?

---

**Last Updated:** 2026-03-16
**Wiki Version:** 2.1
**Axios Version Documented:** 1.13.6
