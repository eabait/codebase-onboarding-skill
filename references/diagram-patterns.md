# Diagram Patterns Reference

Choose the right Mermaid diagram type based on what you're documenting. Every major system (3+ interacting components) needs at least one diagram.

## Diagram Selection Guide

| Scenario | Diagram Type | When to Use |
|----------|-------------|-------------|
| System/component relationships | `graph TD` | Overview pages, dependency maps |
| Request/event lifecycle | `sequenceDiagram` | API flows, message passing, multi-step processes |
| Class/interface hierarchy | `classDiagram` | OOP-heavy systems, type hierarchies |
| State machines | `stateDiagram-v2` | Workflow engines, connection lifecycle, job states |
| Build/CI/deploy pipeline | `flowchart LR` | DevOps pages, build system docs |
| Data model relationships | `erDiagram` | Database schema, data layer docs |
| Component containment | `graph TD` with subgraphs | Monorepo structure, layered architecture |

## Pattern 1: High-Level Architecture (Overview Page)

```mermaid
graph TD
    subgraph Client["Client Layer"]
        WEB[Web App]
        MOB[Mobile App]
        CLI[CLI Tool]
    end

    subgraph API["API Layer"]
        GW[API Gateway]
        AUTH[Auth Middleware]
    end

    subgraph Core["Core Services"]
        SVC1[User Service]
        SVC2[Order Service]
        SVC3[Notification Service]
    end

    subgraph Data["Data Layer"]
        DB[(PostgreSQL)]
        CACHE[(Redis)]
        QUEUE[(RabbitMQ)]
    end

    WEB & MOB & CLI --> GW
    GW --> AUTH
    AUTH --> SVC1 & SVC2
    SVC2 --> SVC3
    SVC1 & SVC2 --> DB
    SVC1 --> CACHE
    SVC3 --> QUEUE
```

Use for: Page 1 — Overview. Shows all major systems and their relationships.

## Pattern 2: Request Lifecycle (API / Service Pages)

```mermaid
sequenceDiagram
    participant C as Client
    participant M as Middleware
    participant R as Router
    participant S as Service
    participant D as Database

    C->>M: HTTP Request
    M->>M: Validate JWT
    M->>R: Authenticated Request
    R->>S: Call service method
    S->>D: Query
    D-->>S: Result set
    S-->>R: Domain object
    R-->>C: JSON Response
```

Use for: Any multi-step process involving handoffs between components. Label every arrow with what's being passed.

## Pattern 3: State Machine (Workflow / Lifecycle Pages)

```mermaid
stateDiagram-v2
    [*] --> Pending: Job created
    Pending --> Processing: Worker picks up
    Processing --> Completed: Success
    Processing --> Failed: Error thrown
    Failed --> Pending: Retry (< max)
    Failed --> DeadLetter: Max retries exceeded
    Completed --> [*]
    DeadLetter --> [*]
```

Use for: Job queues, connection states, order workflows, build pipelines. Label transitions with the trigger event.

## Pattern 4: Dependency / Module Graph (Package Structure Pages)

```mermaid
graph TD
    APP[app] --> CORE[core]
    APP --> API[api]
    API --> CORE
    API --> AUTH[auth]
    CORE --> DB[db]
    CORE --> CACHE[cache]
    AUTH --> CORE

    style CORE fill:#2d5a8e,stroke:#1a3a5c,color:#fff
    style APP fill:#1a3a5c,stroke:#0d1f30,color:#fff
```

Use for: Package dependency graphs, module relationships. Highlight the "hub" module that everything depends on.

## Pattern 5: Data Model (Database / Schema Pages)

```mermaid
erDiagram
    USER ||--o{ ORDER : places
    USER {
        uuid id PK
        string email
        string name
        timestamp created_at
    }
    ORDER ||--|{ ORDER_ITEM : contains
    ORDER {
        uuid id PK
        uuid user_id FK
        enum status
        decimal total
    }
    ORDER_ITEM {
        uuid id PK
        uuid order_id FK
        uuid product_id FK
        int quantity
    }
    PRODUCT ||--o{ ORDER_ITEM : "ordered in"
    PRODUCT {
        uuid id PK
        string name
        decimal price
    }
```

Use for: Data layer documentation. Include PKs, FKs, and relationship cardinality.

## Pattern 6: Layered Architecture with Subgraphs

```mermaid
graph TD
    subgraph Presentation["Presentation Layer"]
        ROUTES[Route Handlers]
        MIDDLEWARE[Middleware Chain]
        SERIALIZERS[Response Serializers]
    end

    subgraph Domain["Domain Layer"]
        SERVICES[Service Classes]
        MODELS[Domain Models]
        EVENTS[Domain Events]
    end

    subgraph Infrastructure["Infrastructure Layer"]
        REPOS[Repositories]
        EXTERNAL[External APIs]
        QUEUE[Message Queue]
    end

    ROUTES --> MIDDLEWARE --> SERVICES
    SERVICES --> MODELS
    SERVICES --> EVENTS
    SERVICES --> REPOS
    SERVICES --> EXTERNAL
    EVENTS --> QUEUE
    REPOS --> DB[(Database)]
```

Use for: Showing architectural layers and the rules about which direction dependencies flow.

## Pattern 7: CI/CD Pipeline

```mermaid
flowchart LR
    PUSH[Git Push] --> LINT[Lint & Format]
    LINT --> TEST[Unit Tests]
    TEST --> BUILD[Build]
    BUILD --> ITEST[Integration Tests]
    ITEST --> STAGE{Branch?}
    STAGE -->|main| DEPLOY_PROD[Deploy Production]
    STAGE -->|develop| DEPLOY_STAGING[Deploy Staging]
    STAGE -->|feature/*| PREVIEW[Preview Environment]
```

Use for: Build & Development pages. Shows the pipeline from commit to deployment.

## Pattern 8: Plugin / Extension System

```mermaid
graph TD
    HOST[Host Application] --> REGISTRY[Plugin Registry]
    REGISTRY --> LIFECYCLE[Lifecycle Manager]

    LIFECYCLE --> |load| P1[Plugin A]
    LIFECYCLE --> |load| P2[Plugin B]
    LIFECYCLE --> |load| P3[Plugin C]

    P1 & P2 & P3 --> API[Plugin API Surface]
    API --> HOOKS[Hook System]
    API --> COMMANDS[Command Registry]
    API --> CONFIG[Config Provider]

    HOOKS --> HOST
    COMMANDS --> HOST
```

Use for: Extension systems, middleware chains, plugin architectures.

---

## Diagram Quality Rules

1. **Label every arrow** with the data or action being performed
2. **Use subgraphs** to group related components — it dramatically improves readability
3. **One concept per diagram** — split complex systems into multiple focused diagrams
4. **Consistent naming**: PascalCase for classes/services, camelCase for functions, UPPER_SNAKE for constants
5. **Optimize for dark mode** — avoid very light fill colors. Use medium blues, greens, grays
6. **Keep it scannable** — if a diagram has more than 15 nodes, break it into sub-diagrams on child pages
7. **Direction matters**: TD (top-down) for hierarchies and layers, LR (left-right) for flows and pipelines
8. **Shape semantics**: rectangles for processes, cylinders `[( )]` for storage, diamonds `{ }` for decisions, rounded `( )` for start/end
