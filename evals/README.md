# Evals

Benchmark the codebase-onboarding skill across multiple LLM harnesses on the same
three reference repos (axios, flask, express).

## Quick Start

```bash
# Install Python deps (first time only)
pip install -r scripts/requirements.txt

# Run all harnesses (Claude + Gemini + Codex) on all 3 repos
bash evals/run.sh

# Single harness
bash evals/run.sh --harness gemini
bash evals/run.sh --harness codex

# Single harness + single repo
bash evals/run.sh --harness codex axios

# Re-score existing outputs without regenerating
bash evals/run.sh --score-only
```

Model overrides via environment variables:

```bash
GEMINI_MODEL=gemini-2.0-flash bash evals/run.sh --harness gemini
CODEX_MODEL=gpt-5.2            bash evals/run.sh --harness codex
CLAUDE_MODEL=claude-opus-4-6   bash evals/run.sh --harness claude
```

## Prerequisites

Install the CLI tools for the harnesses you want to use:

| Harness | Install | Authenticate |
|---------|---------|--------------|
| Claude  | `npm install -g @anthropic-ai/claude-code` | `claude` (first run) |
| Gemini  | `npm install -g @google/gemini-cli`        | `gemini` (first run) |
| Codex   | `npm install -g @openai/codex`             | `codex` (first run)  |

The script detects which tools are available and skips missing ones automatically.

## Directory Layout

```
evals/
├── run.sh            ← unified runner (all harnesses in one command)
├── score.py          ← scorer: runs eval.py, writes comparison table
├── parse_gemini.py   ← splits Gemini's delimited text output into .md files
├── README.md         ← this file
│
├── results/          ← committed: baseline + benchmark artifacts
│   ├── benchmark.json
│   ├── baseline-report.md        ← Claude-only baseline comparison
│   ├── multi-harness-report.md   ← Claude vs Gemini vs Codex
│   ├── multi-harness-review.html ← interactive dashboard
│   ├── multi-harness-scores.json
│   └── wiki/
│       ├── axios/wiki/*.md    ← Claude baseline wiki (10 pages)
│       ├── flask/wiki/*.md    ← Claude baseline wiki (12 pages)
│       └── express/wiki/*.md  ← Claude baseline wiki (9 pages)
│
├── outputs/          ← gitignored: generated at eval runtime
│   └── {repo}-{harness}-{model}/
│       ├── analysis.json
│       ├── eval_metadata.json
│       └── outputs/wiki/*.md
│
└── repos/            ← gitignored: shallow clones of test repos
    ├── axios/
    ├── flask/
    └── express/
```

## How It Works

### Architecture: two harness types

**Non-agentic (Gemini)** — receives a single large prompt containing SKILL.md,
all reference docs, and the codebase analysis JSON. Responds with all wiki pages
in a delimited text format (`---FILE: name.md---`) which `parse_gemini.py` splits
into individual files.

**Agentic (Claude, Codex)** — receives a task prompt with file paths. The agent
reads source files autonomously, explores the repo, and writes wiki pages directly
to disk. No output parsing required.

### Scoring dimensions (`scripts/eval.py`)

| Dimension | Max | What is measured |
|-----------|----:|-----------------|
| Structure | 25 | TL;DR, "Relevant Source Files", required headings, index page |
| Citations | 30 | Citation count, format (`file.py:L45`), per-page density |
| Diagrams  | 15 | Mermaid blocks per page, multi-node diagrams |
| Tables    | 10 | Structured tables for concepts, references |
| Completeness | 10 | Page count, word count, topic breadth |
| Transparency | 10 | `[NEEDS INVESTIGATION]` markers on uncertain claims |

### Benchmark results (March 2026)

Evaluated against axios v1.7, flask 3.1, express 5.1:

| Harness | Model | Mean score | Cit/page | vs Claude |
|---------|-------|:----------:|:--------:|:---------:|
| Claude  | claude-sonnet-4-6 | **96.8** | 15.2 | — |
| Codex   | gpt-5.2 | **92.2** | 39.6 | −4.6 |
| Gemini  | gemini-2.5-pro | **91.7** | 6.3 | −5.1 |

See [`results/multi-harness-review.html`](results/multi-harness-review.html) for
the full interactive dashboard.

## Adding a New Harness

1. Add a `check_<name>()` function that verifies the CLI is on PATH.
2. Add a `build_<name>_prompt()` function that produces the task prompt.
3. Add a `run_<name>_for_repo()` function that calls the CLI and writes
   outputs to `evals/outputs/{repo}-{name}-{model}/outputs/wiki/`.
4. Wire it into the `--harness` flag in `run.sh`.

## Troubleshooting

**Gemini produces no FILE markers** — check `outputs/{run}/raw_response.txt`.
The model may have wrapped the output in a code fence. `parse_gemini.py` handles
this automatically; if it still fails, try `gemini-2.5-pro` (better format adherence).

**Codex writes fewer than 8 pages** — check `outputs/{run}/codex_run.log`. Common
causes: token/turn limits, authentication issues. Run `codex` interactively once to
re-authenticate.

**Model not supported on ChatGPT account** — as of March 2026, `gpt-5.4` and
`gpt-5.3-codex` require an API key. Use `CODEX_MODEL=gpt-5.2` for ChatGPT accounts.
