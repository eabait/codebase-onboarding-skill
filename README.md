# Codebase Onboarding Skill

This repository contains a skill for generating DeepWiki-style codebase onboarding documentation with source-linked claims, diagrams, and structured pages.

## What Is Included

- `SKILL.md`: Invocation and workflow instructions for the skill.
- `scripts/analyze.py`: Repository reconnaissance analyzer.
- `scripts/eval.py`: Output quality evaluator for multi-run comparisons.
- `references/page-template.md`: Required page structure.
- `references/diagram-patterns.md`: Mermaid diagram patterns.
- `references/language-guides.md`: Language/framework analysis guidance.
- `agents/openai.yaml`: Harness metadata for implicit invocation.

## Skill Usage

Use this skill when a user asks to understand, document, or onboard into a repository.

### 1) Install dependencies (optional, recommended)

```bash
python3 -m pip install -r scripts/requirements.txt
```

### 2) Run repository analysis first

```bash
python3 scripts/analyze.py /path/to/repo --output codebase-analysis.json
```

### 3) Use the analysis report to drive docs

Minimum workflow:

1. Read `codebase-analysis.json`
2. Check `summary.capabilities_missing`
3. Build page hierarchy from `key_entities`, `frameworks`, and `symbols.by_kind`
4. Write pages using `references/page-template.md`
5. Use Mermaid patterns from `references/diagram-patterns.md`
6. Mark unknowns as `[NEEDS INVESTIGATION]`

### 4) Typical output layouts

Wiki output:

```text
wiki/
├── 00-index.md
├── 01-overview.md
├── 02-*.md
└── ...
```

Single-file onboarding doc:

```text
onboarding.md
```

## Evaluation Workflow (Across LLM/Harness Runs)

Use `scripts/eval.py` to score and compare documentation quality across multiple runs.

### Expected input layout

`eval.py` expects one subdirectory per run:

```text
runs/
├── gpt5-codex/
│   └── wiki/*.md
├── claude-code/
│   └── wiki/*.md
└── copilot/
    └── wiki/*.md
```

### Run evaluation

```bash
python3 scripts/eval.py /path/to/runs --output onboarding-eval.json
```

### What is scored

- Required section coverage (`Relevant Source Files`, `TL;DR`, `Overview`, etc.)
- Citation coverage and citation density
- Mermaid diagram presence
- Table presence
- Completeness signals (index page and TL;DR coverage)
- Transparency signals (`[NEEDS INVESTIGATION]`, limitations mentions)
- Cross-run consistency (heading-set Jaccard similarity)

### Report outputs

- Console ranking table by run
- JSON report with per-run metrics, subscores, notes, and summary stats

## Reproducibility Tips

- Evaluate runs against the same repository commit.
- Keep dependency versions stable across environments.
- Track score trends over time instead of one-off scores.
- Use the same output format (`wiki/` or single file) across compared runs.
