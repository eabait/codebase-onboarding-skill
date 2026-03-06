# Language & Framework Analysis Guides

When analyzing a codebase, the specific files to read and patterns to look for depend on the language and framework. This reference helps you know where to look.

---

## JavaScript / TypeScript

### Key Files to Read First
| File | What It Tells You |
|------|------------------|
| `package.json` | Dependencies, scripts, project metadata, monorepo config |
| `tsconfig.json` | Module system (ESM/CJS), path aliases, strict mode, target |
| `.eslintrc` / `eslint.config.js` | Code conventions, custom rules |
| `vite.config.ts` / `webpack.config.js` / `next.config.js` | Build system, plugins, env handling |
| `nx.json` / `turbo.json` / `lerna.json` | Monorepo orchestration |

### Entry Point Detection
- `package.json` → `"main"`, `"module"`, `"exports"`, `"bin"` fields
- `"scripts"` → `"start"`, `"dev"`, `"build"` reveal the runtime entry
- Next.js: `pages/` or `app/` directory IS the entry point (file-based routing)
- Express/Fastify: look for `app.listen()` or `server.listen()`

### Framework-Specific Patterns
- **React**: Component tree in `src/components/`, state in `src/store/` or `src/context/`, routing in `src/routes/` or `app/`
- **Next.js**: `app/` (App Router) or `pages/` (Pages Router), API routes in `app/api/` or `pages/api/`, middleware in `middleware.ts`
- **NestJS**: Modules in `*.module.ts`, DI via decorators, guards/interceptors/pipes pattern
- **Express**: Middleware chain in app setup, routes in `routes/` dir, error handler at end of chain

### Dependency Graph
```bash
# If madge is available (npm install -g madge)
madge --image /tmp/deps.svg src/index.ts
# Otherwise, trace imports manually from entry point
```

---

## Python

### Key Files to Read First
| File | What It Tells You |
|------|------------------|
| `pyproject.toml` | Dependencies, build system, project metadata, tool configs |
| `setup.py` / `setup.cfg` | Legacy dependency/metadata (older projects) |
| `requirements.txt` | Pinned dependencies |
| `Dockerfile` | Runtime, entry command, env vars |
| `conftest.py` (root) | Test fixtures, shared test infrastructure |
| `alembic.ini` / `migrations/` | Database migration setup |

### Entry Point Detection
- `pyproject.toml` → `[project.scripts]` or `[tool.poetry.scripts]`
- `Dockerfile` → `CMD` or `ENTRYPOINT`
- `__main__.py` in any package
- Flask: look for `app = Flask(__name__)` and `app.run()`
- FastAPI: look for `app = FastAPI()` and `uvicorn.run()`
- Django: `manage.py`, `settings.py`, `urls.py`

### Framework-Specific Patterns
- **Django**: `settings.py` → `INSTALLED_APPS` maps the full system; `urls.py` → route tree; `models.py` → data layer; `views.py` → business logic
- **FastAPI**: Routers in `routers/` or `api/`, Pydantic models in `schemas/`, dependency injection via `Depends()`
- **Flask**: Blueprints in separate files, `app.register_blueprint()` in factory function

---

## Go

### Key Files to Read First
| File | What It Tells You |
|------|------------------|
| `go.mod` | Module path, Go version, dependencies |
| `cmd/` directory | CLI entry points (each subdir = one binary) |
| `internal/` | Private packages (not importable outside module) |
| `pkg/` | Public/shared packages |
| `Makefile` | Build targets, test commands, tooling |

### Entry Point Detection
- `cmd/*/main.go` — standard Go project layout
- `main.go` in root — simpler projects
- Look for `func main()` — there may be multiple binaries

### Framework-Specific Patterns
- **Gin/Echo/Chi**: Router setup in `main.go` or `routes.go`, middleware registration, handler functions
- **gRPC**: `.proto` files define the API contract, generated code in `pb/` or `gen/`
- **Wire/fx**: Dependency injection — trace the provider graph

---

## Rust

### Key Files to Read First
| File | What It Tells You |
|------|------------------|
| `Cargo.toml` | Dependencies, features, workspace members |
| `Cargo.lock` | Pinned dependency versions |
| `src/main.rs` or `src/lib.rs` | Entry point, module tree via `mod` declarations |
| `build.rs` | Build-time code generation |

### Entry Point Detection
- Binary: `src/main.rs` → `fn main()`
- Library: `src/lib.rs` → public API surface
- Workspace: `Cargo.toml` → `[workspace]` → `members` lists all crates

### Key Patterns
- Module tree declared via `mod` statements — trace from `main.rs`/`lib.rs`
- `pub` visibility = public API surface
- `impl` blocks define methods on types
- Traits define interfaces — look for `impl Trait for Type`

---

## Java / Kotlin (JVM)

### Key Files to Read First
| File | What It Tells You |
|------|------------------|
| `pom.xml` / `build.gradle` / `build.gradle.kts` | Dependencies, plugins, module structure |
| `settings.gradle` | Multi-module project structure |
| `application.yml` / `application.properties` | Spring config |
| `src/main/resources/` | Config files, templates, static assets |

### Entry Point Detection
- Spring Boot: class with `@SpringBootApplication` annotation
- Plain Java: class with `public static void main(String[] args)`
- Multi-module: each module may have its own entry point

### Framework-Specific Patterns
- **Spring Boot**: `@RestController` for API endpoints, `@Service` for business logic, `@Repository` for data access, `@Configuration` for DI wiring
- **Spring modules**: Each `@Configuration` class defines a module boundary

---

## C# / .NET

### Key Files to Read First
| File | What It Tells You |
|------|------------------|
| `*.sln` | Solution structure, project references |
| `*.csproj` | Dependencies (PackageReference), target framework, build properties |
| `Program.cs` | Application entry point, DI container setup, middleware pipeline |
| `appsettings.json` | Configuration hierarchy |
| `Startup.cs` (older) | Service registration and middleware (pre-.NET 6) |

### Entry Point Detection
- .NET 6+: `Program.cs` with top-level statements
- Older: `Program.cs` → `Main()` → `CreateHostBuilder()` → `Startup.cs`
- Minimal API: route definitions directly in `Program.cs`

---

## General Analysis Checklist

Regardless of language, always investigate:

1. **Dependency Injection / Service Registration** — How are components wired together? DI container? Manual factory? Module system?
2. **Configuration Loading** — Where do config values come from? Env vars → config files → defaults? What's the precedence order?
3. **Error Handling Strategy** — Global error handlers? Error types/codes? Retry logic? Circuit breakers?
4. **Authentication/Authorization Flow** — Middleware? Decorators? Guards? Where is the user identity established?
5. **Data Access Pattern** — ORM? Raw SQL? Repository pattern? Where are queries defined?
6. **Test Organization** — Unit vs integration vs e2e? How are tests structured relative to source?
7. **Logging & Observability** — Structured logging? Tracing? Metrics collection? What library?
8. **Background Processing** — Job queues? Cron jobs? Event handlers? Where are async operations defined?
