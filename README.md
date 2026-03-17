# Codebase Onboarding Skill

Generate **DeepWiki-style onboarding documentation** for any codebase — source-linked,
diagram-rich, and structured for both humans and LLMs to navigate.

Validated against axios, flask, and express with a mean eval score of **96.8 / 100**
across three independent LLM harnesses (Claude, Gemini CLI, OpenAI Codex CLI).

---

## What This Skill Produces

A hierarchical wiki of Markdown pages, each containing:

- **TL;DR** — 2–3 sentences summarising the subsystem
- **Architecture diagram** — Mermaid flowchart or sequence diagram
- **Relevant Source Files** table — every claim links back to real file paths
- **Key Concepts** table — structured reference for onboarding engineers
- **Prose with inline citations** — `path/to/file.ext:L45–L87` on every claim
- **`[NEEDS INVESTIGATION]`** markers — honest flags on anything unverified

```
wiki/
├── 00-index.md          Table of contents + navigation guide
├── 01-overview.md       High-level architecture + Mermaid diagram
├── 02-request-lifecycle.md
├── 03-middleware.md
└── ...
```

### Example outputs (Claude baseline, scored 96.8/100)

**[axios](https://github.com/axios/axios)** — Promise-based HTTP client
- [00 · Index](evals/results/wiki/axios/wiki/00-index.md)
- [01 · Overview & Architecture](evals/results/wiki/axios/wiki/01-overview.md)
- [02 · HTTP Client Core](evals/results/wiki/axios/wiki/02-http-client-core.md)
- [03 · Request Pipeline](evals/results/wiki/axios/wiki/03-request-pipeline.md)
- [04 · Interceptors](evals/results/wiki/axios/wiki/04-interceptors.md)
- [05 · Adapters](evals/results/wiki/axios/wiki/05-adapters.md)
- [06 · Config Merging](evals/results/wiki/axios/wiki/06-config-merging.md)
- [07 · Error Handling](evals/results/wiki/axios/wiki/07-error-handling.md)
- [08 · Build & Development](evals/results/wiki/axios/wiki/08-build-development.md)
- [09 · Testing](evals/results/wiki/axios/wiki/09-testing.md)

**[flask](https://github.com/pallets/flask)** — Python web framework
- [00 · Index](evals/results/wiki/flask/wiki/00-index.md)
- [01 · Overview & Architecture](evals/results/wiki/flask/wiki/01-overview.md)
- [02 · Application Core](evals/results/wiki/flask/wiki/02-application-core.md)
- [03 · Request / Response Cycle](evals/results/wiki/flask/wiki/03-request-response-cycle.md)
- [04 · Routing System](evals/results/wiki/flask/wiki/04-routing-system.md)
- [05 · Blueprints](evals/results/wiki/flask/wiki/05-blueprints.md)
- [06 · Context Management](evals/results/wiki/flask/wiki/06-context-management.md)
- [07 · Globals & Proxies](evals/results/wiki/flask/wiki/07-globals-and-proxies.md)
- [08 · Templating](evals/results/wiki/flask/wiki/08-templating.md)
- [09 · Sessions & Cookies](evals/results/wiki/flask/wiki/09-sessions-and-cookies.md)
- [10 · Build & Deployment](evals/results/wiki/flask/wiki/10-build-and-deployment.md)

**[express](https://github.com/expressjs/express)** — Node.js web framework
- [00 · Index](evals/results/wiki/express/wiki/00-index.md)
- [01 · Overview & Architecture](evals/results/wiki/express/wiki/01-overview.md)
- [02 · Application Core](evals/results/wiki/express/wiki/02-application-core.md)
- [03 · Routing System](evals/results/wiki/express/wiki/03-routing-system.md)
- [04 · Middleware Pipeline](evals/results/wiki/express/wiki/04-middleware-pipeline.md)
- [05 · Request & Response](evals/results/wiki/express/wiki/05-request-response.md)
- [06 · View Engine](evals/results/wiki/express/wiki/06-view-engine.md)
- [07 · Static Middleware](evals/results/wiki/express/wiki/07-static-middleware.md)
- [08 · Build & Testing](evals/results/wiki/express/wiki/08-build-and-testing.md)

---

## Repository Layout

```
codebase-onboarding-skill/
├── SKILL.md                   ← Skill invocation & workflow instructions
├── scripts/
│   ├── analyze.py             ← Codebase reconnaissance (AST, PageRank, git)
│   ├── eval.py                ← Wiki quality scorer (6 dimensions, max 100)
│   └── requirements.txt       ← Optional Python deps
├── references/
│   ├── page-template.md       ← Required page structure
│   ├── diagram-patterns.md    ← Mermaid diagram templates by scenario
│   └── language-guides.md     ← Language/framework-specific analysis guidance
├── agents/
│   └── openai.yaml            ← Harness metadata for implicit invocation
└── evals/
    ├── run.sh                 ← Unified eval runner (Claude + Gemini + Codex)
    ├── score.py               ← Multi-harness comparison scorer
    ├── parse_gemini.py        ← Splits Gemini's delimited output into .md files
    ├── README.md              ← Eval setup & runbook
    └── results/               ← Committed benchmark artifacts
```

---

## Getting Started

### 1. Install the skill

Install via the [Vercel Labs Skills](https://github.com/vercel-labs/skills) framework:

```bash
skills install https://github.com/eabait/codebase-onboarding-skill
```

### 2. Ask your agent to onboard you

Point your agent at a repository and ask:

> "Onboard me to this codebase."

That's it. The skill instructs the agent to install dependencies, run the codebase
analysis, and generate the full wiki automatically — no manual steps required.

The agent will:
1. Install Python deps (`scripts/requirements.txt`) if needed
2. Run `scripts/analyze.py` on the repository to produce a structured analysis
3. Read `SKILL.md` and the reference docs
4. Generate a complete wiki and write the pages to `wiki/`

### Manual invocation (without the skills framework)

If you're using an agent directly, pass `SKILL.md` and the reference docs in context
alongside the repo path. See [`evals/README.md`](evals/README.md) for per-harness
examples with Claude Code, Gemini CLI, and Codex CLI.

---

## Evaluation

Run the built-in eval harness to benchmark quality across models:

```bash
# All harnesses (Claude + Gemini + Codex), all 3 reference repos
bash evals/run.sh

# Single harness
bash evals/run.sh --harness gemini
bash evals/run.sh --harness codex axios
```

### Benchmark results (March 2026)

| Harness | Model | Score | Cit/page | vs Baseline |
|---------|-------|:-----:|:--------:|:-----------:|
| Claude  | claude-sonnet-4-6 | **96.8** | 15.2 | — |
| Codex   | gpt-5.2 | **92.2** | 39.6 | −4.6 |
| Gemini  | gemini-2.5-pro | **91.7** | 6.3 | −5.1 |

Full results:
- [Multi-harness comparison report](evals/results/multi-harness-report.md) — Claude vs Codex vs Gemini, all repos
- [Claude baseline report](evals/results/baseline-report.md) — per-repo subscores and notes
- [Benchmark data (JSON)](evals/results/benchmark.json)

### Scorer dimensions

`scripts/eval.py` grades six dimensions (max 100 points):

| Dimension | Max | Measures |
|-----------|----:|---------|
| Structure | 25 | TL;DR, required headings, source-files table, index page |
| Citations | 30 | Citation count, format (`file.py:L45`), density per page |
| Diagrams  | 15 | Mermaid blocks, multi-node diagrams |
| Tables    | 10 | Key Concepts tables, component references |
| Completeness | 10 | Page count, word count, topic coverage |
| Transparency | 10 | `[NEEDS INVESTIGATION]` markers |

```bash
# Score any wiki output directory
python3 scripts/eval.py path/to/runs/ --output report.json
```

---

## Contributing

Pull requests welcome. When adding support for a new language or framework, update
`references/language-guides.md`. When adding a new eval harness, follow the pattern
in `evals/run.sh` and document it in `evals/README.md`.

---

## License

MIT — see [LICENSE](LICENSE).
