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

### 1. Install Python dependencies (optional but recommended)

```bash
pip install -r scripts/requirements.txt
```

Enables AST-level analysis (tree-sitter), PageRank file ranking (networkx), and
git history insights. All features degrade gracefully if deps are missing.

### 2. Analyse your repository

```bash
python3 scripts/analyze.py /path/to/repo --output analysis.json
```

This produces a structured JSON with ranked files, framework detection, key symbols,
dependency graphs, and git contribution patterns.

### 3. Generate the wiki

Use the analysis output to drive the skill. Pass it to your LLM of choice along
with `SKILL.md` and the reference documents.

Minimum invocation pattern (Claude Code):

```bash
claude "Read SKILL.md, references/page-template.md, references/diagram-patterns.md,
and analysis.json. Then generate a full onboarding wiki for the repo at /path/to/repo
and write the pages to wiki/"
```

Or with Gemini / Codex — see [`evals/README.md`](evals/README.md) for per-harness examples.

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

View the full interactive report: [`evals/results/multi-harness-review.html`](evals/results/multi-harness-review.html)

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
