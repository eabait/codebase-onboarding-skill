# Page Template Reference

Every wiki page follows this template. Sections marked (required) must always be present. Sections marked (conditional) appear only when relevant to the page topic.

---

## Full Template

```markdown
# [Page Number] — [Page Title]

## Relevant Source Files
<!-- (required) List the key files this page documents, with relative paths -->
- `src/core/engine.ts`
- `src/core/types.ts`
- `config/default.yaml`

## TL;DR
<!-- (required) 2-3 sentences. A developer should know if they need to read further.
     Answer: What is this? Why does it matter? What's the one thing to remember? -->

## Overview
<!-- (required) 1-2 paragraphs setting context.
     - What is this system/component?
     - Why does it exist? What problem does it solve?
     - How does it fit into the broader architecture?
     - Cross-reference parent and sibling pages with [Page X.Y — Title] -->

## Architecture Diagram
<!-- (required for systems with 3+ interacting components)
     Mermaid diagram showing structure, data flow, or lifecycle.
     See diagram-patterns.md for the right diagram type. -->

## Key Concepts
<!-- (required) Table-driven. Define domain terms, patterns, and abstractions
     the developer must understand before reading the code.
     This is NOT a glossary — only concepts specific to THIS system. -->

| Concept | Description | Source |
|---------|-------------|--------|
| WorkUnit | Atomic unit of processing in the job queue | `src/queue/types.ts:L12-L28` |
| Resolver | Strategy pattern impl for dependency resolution | `src/core/resolver.ts` |

## How It Works
<!-- (required) Walk through the main code path(s).
     - Start with the happy path
     - Reference specific functions, classes, and files
     - Use sequence diagrams for multi-step flows
     - Include code snippets ONLY when the specific syntax matters (config formats, DSLs)
     - For complex flows, break into subsections: ### Request Flow, ### Error Handling, etc. -->

## Component Reference
<!-- (required) Table of key classes/functions/modules in this system.
     Sort by importance, not alphabetically. -->

| Component | Type | Responsibility | Source |
|-----------|------|----------------|--------|
| `JobProcessor` | class | Dequeues and executes work units | `src/queue/processor.ts:L15-L142` |
| `createResolver()` | factory fn | Builds resolver with injected deps | `src/core/resolver.ts:L8-L34` |
| `QUEUE_CONFIG` | const | Default queue tuning parameters | `src/queue/config.ts:L1-L22` |

## Data Flow
<!-- (conditional: include for systems that transform or pass data between components)
     Sequence diagram or data flow diagram showing what data enters, how it's
     transformed, and where it ends up. -->

## Configuration & Environment
<!-- (conditional: include when the system has configurable behavior)
     Config keys, env vars, feature flags. -->

| Key | Default | Description | Source |
|-----|---------|-------------|--------|
| `QUEUE_CONCURRENCY` | `5` | Max parallel job executions | `src/queue/config.ts:L8` |
| `RETRY_MAX_ATTEMPTS` | `3` | Retries before dead-letter | `src/queue/config.ts:L12` |

## Error Handling
<!-- (conditional: include when the system has non-trivial error handling)
     What errors can occur? How are they handled? What does the developer
     need to know for debugging? -->

## Extension Points
<!-- (conditional: include for plugin systems, middleware chains, or hookable architectures)
     How does a developer add new behavior to this system? -->

## Gotchas & Conventions
<!-- (conditional but strongly encouraged: include whenever there are non-obvious patterns)
     Use admonition blocks: -->

> ⚠️ **Gotcha**: The cache invalidation runs synchronously on the main thread.
> Under heavy load, this can block the event loop for 200ms+.
> See `src/cache/invalidator.ts:L89`.

> 📌 **Convention**: All service classes implement `I{Name}Service` and are
> registered in `src/di/container.ts`. Don't instantiate services directly.

> 💡 **Tip**: When debugging auth failures, enable `DEBUG=auth:*` to see
> the full token validation chain. Start from `src/middleware/auth.ts:L42`.

## Cross-References
<!-- (required) Links to related pages in the wiki -->
- For [related topic], see [Page X.Y — Title]
- Parent: [Page X — Title]
- Related: [Page Y — Title]
```

---

## Section Writing Guidelines

### TL;DR
- Must be self-contained — reader should understand the gist without reading further
- Format: "[System] does [what] by [how]. It's the [role] in the architecture. Key thing to know: [gotcha or core concept]."
- No jargon that hasn't been defined yet

### Overview
- First sentence defines what this is
- Second sentence explains why it exists
- Remaining sentences explain how it fits into the larger system
- Always cross-reference the parent page and at least one sibling

### How It Works
- Start with the most common/important code path
- Use present tense: "The processor dequeues a job, validates its schema, then dispatches to the appropriate handler."
- Reference specific functions: "Validation happens in `validateJob()` (`src/queue/validator.ts:L23`)"
- For multi-step flows, use a Mermaid sequence diagram THEN walk through each step in prose
- Don't dump entire functions — reference them by location. Only include code snippets when the syntax itself is the point (config formats, DSLs, regex patterns)

### Tables
- Always include a **Source** column with file paths
- Sort by importance/frequency, not alphabetically
- Keep cell content to one line where possible
- Link to detailed subsections for complex items

### Gotchas
- Only include genuinely non-obvious things
- Always include the source file reference
- Explain the consequence, not just the fact: "X does Y" → "X does Y, which means Z will happen if you..."
