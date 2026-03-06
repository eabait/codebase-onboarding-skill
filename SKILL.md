---
name: codebase-onboarding
description: "Generate a DeepWiki-style structured wiki for any codebase to accelerate developer onboarding. Use this skill whenever a user wants to understand, document, or onboard into an unfamiliar repository — including requests like 'explain this codebase', 'generate documentation for this repo', 'help me understand this project', 'create an onboarding guide', 'map out the architecture', or 'how does this codebase work'. Also trigger when a user provides a repo URL or file tree and asks for analysis, or when onboarding new team members into existing codebases. Even if the user doesn't say 'wiki' or 'onboarding', trigger this skill if they want a structured understanding of a codebase."
license: Apache-2.0
metadata:
  author: eabait
  version: "2.1"
allowed-tools: Bash(python3:*) Bash(pip:*) Bash(git:*) Read
---

# Codebase Onboarding Wiki Generator

Generate a hierarchical, source-linked, diagram-rich wiki from any repository — modeled after DeepWiki's format.

## When to Use

- User provides a repository (URL, path, or uploaded files) and wants to understand it
- User asks to onboard developers into a codebase
- User wants architecture documentation generated from code
- User asks "how does this repo work" or "map this codebase"

## Workflow Overview

```
Phase 1: Reconnaissance ──→ Phase 2: Architecture Mapping ──→ Phase 3: Deep Docs ──→ Phase 4: Assembly
  (scripts/analyze.py)        (you + diagrams)                  (you + templates)      (final output)
```

### Phase 1 — Reconnaissance (Automated)

Run the analysis script to gather structured data about the codebase:

```bash
pip install -r scripts/requirements.txt  # optional, graceful degradation
python scripts/analyze.py <repo_path> --output /tmp/codebase-analysis.json
```

## Execution Contract

Use this contract to reduce output variance across models and harnesses.

**MUST**
- Run `scripts/analyze.py` first when a repository path is available.
- Read the JSON report before writing any architecture claims.
- Check `summary.capabilities_missing` and adapt output scope accordingly.
- Cite source files for every technical claim.
- Mark unverifiable claims as `[NEEDS INVESTIGATION]`.

**SHOULD**
- Install optional Python dependencies for better structural analysis: `pip install -r scripts/requirements.txt`.
- Prioritize `key_entities` and `git.hotspots` when choosing what to document first.
- Keep diagrams and tables aligned with observed code structure, not assumptions.

**MAY**
- Continue with manual reconnaissance when script execution is not possible.
- Produce a reduced-scope onboarding document when capabilities are limited.

## Quality Tiers

Use these tiers to set expectations explicitly:

- **Tier A (high confidence):** `tree_sitter`, `networkx`, and `git` available. Full wiki with ranked entities and ownership/hotspot analysis.
- **Tier B (medium confidence):** At least one of `tree_sitter` or `networkx` missing. Full wiki allowed, but include limitations section.
- **Tier C (baseline):** Script unavailable or major capabilities missing. Produce structured overview only and explicitly call out unknowns.

The script runs 7 phases automatically and reports what it could and couldn't do:
1. **File discovery** — .gitignore-aware traversal (pathspec)
2. **Language stats** — Accurate LOC by language (tokei/scc)
3. **Manifest parsing** — Dependencies from package.json, pyproject.toml, Cargo.toml, go.mod, .csproj (proper parsers, not regex)
4. **Framework detection** — Cross-referenced against actual dependencies, not just filenames
5. **Code structure** — Classes, functions, interfaces, types via tree-sitter AST parsing
6. **Importance ranking** — PageRank over cross-file reference graph (networkx)
7. **Git insights** — Hotspot files, top contributors, per-directory ownership

Read the JSON output before proceeding. The `key_entities` field tells you which code entities are most important — start documentation there.

#### How to Use the Analysis Report

Each field in the JSON report drives specific documentation decisions. Follow this mapping:

**`key_entities` → Page Structure & Priority**
The PageRank-scored symbols tell you what matters most. Use them to:
- Decide which components deserve their own wiki page (top 10-15 entities almost always do)
- Determine documentation order — document highest-ranked entities first
- Identify hub abstractions: entities with high rank are referenced across many files, meaning they're architectural load-bearing walls
- Build the "Key Concepts" table on the Overview page from the top ~10 entries

Example: if `RepomixConfigMerged` ranks #1, it's central to the codebase — it gets prominent placement in Overview, its own section, and every page that touches config cross-references it.

**`symbols.by_kind` → Wiki Depth Decisions**
The distribution of classes vs functions vs interfaces reveals the codebase's architecture style:
- Heavy on interfaces/types → document contracts and type hierarchies, use ER diagrams
- Heavy on classes → document inheritance and composition, use class relationship diagrams
- Heavy on functions → document data flow and pipelines, use sequence diagrams
- This directly selects which patterns from `references/diagram-patterns.md` to use

**`frameworks` → Adaptation Path**
Match detected frameworks to the "Adaptation by Codebase Type" table to decide which special pages to include. Cross-reference with `references/language-guides.md` for framework-specific analysis patterns (e.g., if Django is detected, read the Django section to know which files to examine first).

**`git.hotspots` → "Active Development Areas" Section**
The most-changed files indicate where the team is actively working. Use this to:
- Add a "Current Development Areas" callout on the Overview page
- Prioritize documenting hotspot files in detail (they're what new devs will touch first)
- Flag files that change frequently but have low symbol count — they may be config or glue code that needs explanation

**`git.ownership` → "Who to Talk To" Guidance**
Per-directory top contributors map directly to an onboarding essential: knowing who owns what. Include this as a table in the Overview page or as a dedicated "Team & Ownership" section:
```
| Area          | Primary Contact    | Commits (12mo) |
|---------------|--------------------|----------------|
| src/core/     | Alice              | 142            |
| src/api/      | Bob                | 87             |
```

**`manifests` → Dependencies & Build Section**
Parsed dependency data drives the "Build & Development" wiki page:
- `dependencies` → runtime architecture (what the app actually uses)
- `devDependencies` → toolchain (what developers need to understand)
- `scripts` → available commands for the dev workflow page
- `engines` → version requirements and constraints

**`languages` + `languages_source` → Scope & Confidence**
The language breakdown tells you the primary language (drives which tree-sitter queries produced the best data) and whether stats are accurate (`tokei`/`scc`) or estimated (fallback). If using fallback stats, note this limitation.

**`capabilities_missing` → Report Limitations**
If the report says tree-sitter was skipped, you'll need to manually read key files to extract structure. If networkx was skipped, you won't have importance ranking — fall back to reading entry points and README to determine what's important. Always check this field and adjust your approach accordingly.

**`file_tree` → Navigation & Gap Detection**
Scan the full file list to find files the automated analysis might have missed:
- Config files (`.env.example`, `nginx.conf`, `terraform/`) → infrastructure docs
- Migration files → database schema evolution
- Seed/fixture files → data model understanding
- Files in unconventional locations that don't match the dominant framework's conventions

If the script is unavailable or the repo is provided as file contents in context, perform manual reconnaissance:

1. **Read the file tree** — Identify project type, language(s), framework(s), mono/polyrepo structure
2. **Read foundational files**: README, package.json / Cargo.toml / go.mod / pyproject.toml, Dockerfile, CI configs, docs/ folder
3. **Identify entry points**: main/index files, CLI commands, server bootstrap, route definitions
4. **Detect patterns**: monorepo tools (Nx, Turborepo, Lerna), plugin systems, multi-process architecture, DI containers

### Phase 2 — Architecture Mapping

Based on reconnaissance, define the wiki page tree. Use these inputs from the analysis report:

1. **`key_entities` (top 15)** → Each high-ranked entity cluster becomes a major section. Group related entities by directory or domain.
2. **`frameworks`** → Select the matching row from "Adaptation by Codebase Type" to add mandatory special pages.
3. **`symbols.by_kind`** → Choose diagram strategy: class-heavy = component diagrams, function-heavy = sequence diagrams, interface-heavy = contract/ER diagrams.
4. **`git.ownership`** → Use top-level directory ownership to validate your section boundaries align with team boundaries.

Build the numbered hierarchy:

```
1   - Overview
2   - [Major System A]
2.1 - [Subsystem A.1]
3   - [Major System B]
...
N   - Build & Development
N+1 - Testing Infrastructure
```

Rules:
- Max depth: 4 levels (e.g., `3.2.1`)
- 8-15 top-level sections for medium codebases, 15-25 for large ones
- Each top-level section gets 2-6 subsections
- Last two sections are always Build/Dev and Testing

Produce a top-level architecture diagram (Mermaid `graph TD`) before writing any pages.

### Phase 3 — Deep Documentation

For each page, follow the template in `references/page-template.md`. Use the analysis report to populate structured sections:

1. **Relevant Source Files** — Pull from `key_entities` items that match this page's scope. Use the `file` and `line` fields for precise source links.
2. **TL;DR** — 2-3 sentences; developer decides if they need to read further
3. **Architecture Diagram** — Select the right Mermaid pattern from `references/diagram-patterns.md` based on `symbols.by_kind` distribution (see Phase 2 decisions)
4. **Key Concepts table** — Populate from `key_entities` that belong to this section. The `kind` field gives you the type column, `file:line` gives you the Source column.
5. **Component Reference table** — Use `symbols.items` filtered to this page's directory/domain. Include name, kind, file:line, and a one-line description from reading the actual code.
6. **Source-linked claims** — every technical claim cites `path/to/file.ts:L42-L87`. The `symbols` data gives you starting points; read the actual files to verify and add line ranges.
7. **Active areas** — Cross-reference `git.hotspots` to flag which components on this page are under active development.

Read `references/page-template.md` before writing any page.
Read `references/diagram-patterns.md` before creating any Mermaid diagrams.

For language/framework-specific analysis patterns, read `references/language-guides.md`.

### Phase 4 — Assembly

Assemble pages into the final output. Output format depends on what the user needs:

| User Request | Output Format |
|-------------|---------------|
| "Generate a wiki" | Set of numbered .md files in a `wiki/` directory |
| "Create an onboarding doc" | Single consolidated .md file with all pages |
| "Help me understand this repo" | Conversational walkthrough with embedded diagrams |
| "Make a presentation" | Defer to pptx skill with wiki content as input |

For file-based output, structure as:
```
wiki/
├── 00-index.md          (table of contents with links)
├── 01-overview.md
├── 02-system-a.md
├── 02.1-subsystem-a1.md
├── ...
└── assets/
    └── diagrams/        (exported Mermaid if requested)
```

## Core Principles — Read These

These are non-negotiable quality standards:

**Never invent.** Every claim must trace to real code. If you can't verify it, mark it `[NEEDS INVESTIGATION]` with the specific files that need review.

**Progressive disclosure.** TL;DR → Overview → Details. Every section opens with a summary paragraph.

**Systems thinking.** Architecture → Subsystems → Components → Methods. Map connections before explaining internals.

**Table-driven.** Any structured info with 3+ items goes in a table. Always include a Source column.

**Diagram-first.** If a system has 3+ interacting components, it needs a Mermaid diagram. No exceptions.

**Depth before breadth.** Trace actual code paths. Never guess from file names — read the file.

## Adaptation by Codebase Type

| Codebase Type | Special Pages to Include |
|--------------|-------------------------|
| Monorepo | "Repository Structure" mapping packages/services; per-package subtrees |
| Microservices | "Service Communication" (protocols, contracts, discovery); per-service sections |
| Frontend SPA | Routing, State Management, Component Hierarchy, Build/Bundle |
| Backend API | Route Definitions, Middleware Pipeline, Data Access Layer, Auth Flow |
| Library/SDK | Public API Surface, Extension Points, Usage Examples |
| CLI Tool | Command Hierarchy, Argument Parsing, Plugin System |
| Mobile App | Navigation, State Management, Platform-Specific Code, Build Variants |

## Anti-Patterns to Avoid

- **Narrating the file tree** — Don't just list files. Explain what they do and how they connect.
- **Repeating the README** — Synthesize and add value beyond existing docs.
- **Surface-level descriptions** — "This handles auth" is useless. Trace the flow.
- **Missing the "why"** — Infer architectural decisions from code. Flag unknowns as questions.
- **Orphaned pages** — Every page is reachable from Overview and cross-references siblings.
- **Diagram-less systems** — 3+ interacting components = mandatory diagram.
- **Guessing from names** — `utils/helpers.ts` could be anything. Read it first.

## Dependencies & Tools

The analyzer (`scripts/analyze.py`) follows an orchestrator pattern — it composes specialized tools instead of reimplementing parsers. Every dependency is optional; the script reports what it used and what it skipped.

Install everything: `pip install -r scripts/requirements.txt`

**Python packages** (all optional, graceful degradation):

| Package | What It Enables | Without It |
|---------|----------------|------------|
| `tree-sitter-language-pack` | AST extraction: classes, functions, interfaces, types across 165+ languages | No code structure data — only file-level stats |
| `pathspec` | Proper .gitignore-aware file traversal | Hardcoded skip-list only |
| `networkx` | PageRank importance ranking of code entities | No ranking — all symbols treated equally |
| `tomli` (Python <3.11) | Proper TOML parsing for pyproject.toml, Cargo.toml | Python 3.11+ uses stdlib `tomllib` |

**CLI tools** (optional, detected at runtime):

| Tool | What It Enables | Without It |
|------|----------------|------------|
| `tokei` or `scc` | Accurate LOC stats with proper comment handling across all languages | Rough estimate from file sizes |
| `git` | Hotspot detection, contributor mapping, code ownership | No git insights section |

**Not required:**
- Mermaid CLI (`mmdc`) — diagrams are output as Mermaid source; rendering is the viewer's job
- Language toolchains (cargo, npm, pip) — the analyzer reads manifests directly via proper parsers (JSON, TOML, XML)
- `ripgrep`, `jq`, `tree` — the script handles search and formatting internally

## Available Scripts

- **`scripts/analyze.py`** — Automated codebase reconnaissance. Produces a JSON report with file discovery, language stats, manifest parsing, framework detection, AST-based code structure, PageRank importance ranking, and git insights. All dependencies optional with graceful degradation.
- **`scripts/eval.py`** — Quality evaluator for comparing onboarding-doc outputs across multiple LLM/harness runs. Scores structure, citation coverage, diagrams/tables, completeness, and cross-run consistency.
- **`scripts/requirements.txt`** — Python dependencies for analyze.py. Install with `pip install -r scripts/requirements.txt`.

## File Reference

| File | Purpose | When to Read |
|------|---------|-------------|
| `references/page-template.md` | Full page template with all sections | Before writing any wiki page |
| `references/diagram-patterns.md` | Mermaid diagram patterns by scenario | Before creating any diagram |
| `references/language-guides.md` | Language-specific analysis patterns | When analyzing unfamiliar language/framework |
| `scripts/analyze.py` | Automated codebase reconnaissance | Phase 1, when repo is on local filesystem |
| `scripts/eval.py` | Evaluate run-to-run documentation quality and consistency | After generating outputs from multiple LLM/harness runs |
| `scripts/requirements.txt` | Python dependencies for scripts | Setup |
