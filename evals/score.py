#!/usr/bin/env python3
"""
evals/score.py — Score all wiki outputs with eval.py and produce a comparison table.

Discovers every {repo}-{harness}-{model}/outputs/wiki/ directory under
evals/outputs/ (or a custom path), scores each with scripts/eval.py, and
writes a markdown + JSON comparison report.

Usage:
    python3 evals/score.py                          # auto-detect outputs dir
    python3 evals/score.py --outputs-dir path/to/   # custom outputs dir
    python3 evals/score.py --no-baseline            # omit Claude baseline row
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).parent
SKILL_ROOT  = SCRIPT_DIR.parent
EVAL_SCRIPT = SKILL_ROOT / "scripts" / "eval.py"

# ── Claude baseline (from evals/results/benchmark.json) ─────
CLAUDE_BASELINE = {
    "axios":   {"score": 99.4, "files": 10, "words": 15321, "citations": 113,
                "mermaid": 9,  "tables": 38,
                "ss": {"structure": 25, "citations": 30, "diagrams": 15,
                       "tables": 10, "completeness": 10, "transparency": 10}},
    "flask":   {"score": 96.5, "files": 12, "words": 15527, "citations": 194,
                "mermaid": 11, "tables": 44,
                "ss": {"structure": 25, "citations": 30, "diagrams": 15,
                       "tables": 10, "completeness": 10, "transparency": 10}},
    "express": {"score": 94.6, "files":  9, "words": 17759, "citations": 145,
                "mermaid":  9, "tables": 60,
                "ss": {"structure": 25, "citations": 30, "diagrams": 15,
                       "tables": 10, "completeness": 10, "transparency": 6.9}},
}
REPOS = ["axios", "flask", "express"]


# ── Discovery ────────────────────────────────────────────────
def find_runs(outputs_dir: Path) -> list[dict]:
    runs = []
    for run_dir in sorted(outputs_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        wiki_dir = run_dir / "outputs" / "wiki"
        if not wiki_dir.is_dir():
            continue
        md_files = list(wiki_dir.glob("*.md"))
        if not md_files:
            continue

        name = run_dir.name
        # Detect repo prefix (always first segment before first -)
        repo = next((r for r in REPOS if name.startswith(f"{r}-")), None)
        rest = name[len(repo) + 1:] if repo else name

        # Normalise harness label from directory suffix
        if rest.startswith("codex-"):
            model = rest[len("codex-"):]
            harness = f"codex-cli"
        elif rest.startswith("gemini-"):
            model = rest[len("gemini-"):]
            harness = "gemini-cli"
        elif rest.startswith("claude-"):
            model = rest[len("claude-"):]
            harness = "claude"
        else:
            harness, model = rest, rest

        runs.append({
            "name":     name,
            "repo":     repo or "unknown",
            "harness":  harness,
            "model":    model,
            "run_dir":  run_dir,
            "wiki_dir": wiki_dir,
            "md_count": len(md_files),
        })
    return runs


# ── Scoring ─────────────────────────────────────────────────
def score_all(outputs_dir: Path) -> dict:
    report_file = outputs_dir.parent / "scores.json"
    result = subprocess.run(
        [sys.executable, str(EVAL_SCRIPT), str(outputs_dir),
         "--output", str(report_file)],
        capture_output=True, text=True,
    )
    print(result.stdout)
    if result.returncode != 0:
        print("STDERR:", result.stderr[:800], file=sys.stderr)

    if report_file.exists():
        return json.loads(report_file.read_text())
    return {}


# ── Report ───────────────────────────────────────────────────
def build_report(scores: dict, run_meta: dict[str, dict],
                 include_baseline: bool = True) -> str:
    all_runs = scores.get("runs", [])
    runs = [r for r in all_runs if r.get("score", 0) > 0]

    by_repo: dict[str, list] = {r: [] for r in REPOS}
    for run in runs:
        for repo in REPOS:
            if run["name"].startswith(repo):
                by_repo[repo].append(run)
                break

    lines = []
    lines.append("# Eval Results\n")
    lines.append(f"*Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}*\n")

    # Summary table
    lines.append("## Score Summary\n")
    lines.append("| Run | Harness | Model | Score | Files | Cit/page | Mermaid | Tables | Δ Claude |")
    lines.append("|-----|---------|-------|------:|------:|---------:|:-------:|-------:|---------:|")

    if include_baseline:
        for repo, b in CLAUDE_BASELINE.items():
            lines.append(
                f"| {repo}-claude | claude | claude-code | **{b['score']}** | {b['files']} | "
                f"{b['citations']/b['files']:.1f} | {b['mermaid']} | {b['tables']} | — |"
            )

    for run in sorted(runs, key=lambda r: r.get("score", 0), reverse=True):
        name    = run["name"]
        score   = run.get("score", 0)
        files   = run.get("markdown_files", 0)
        cits    = run.get("citation_count", 0)
        cit_pp  = round(cits / files, 1) if files else 0
        mermaid = run.get("mermaid_blocks", 0)
        tables  = run.get("tables", 0)
        meta    = run_meta.get(name, {})
        harness = meta.get("harness", "?")
        model   = meta.get("model", "?")

        delta = "?"
        for repo in REPOS:
            if name.startswith(repo):
                b = CLAUDE_BASELINE.get(repo, {})
                if b:
                    delta = f"{score - b['score']:+.1f}"
                break

        lines.append(
            f"| {name} | {harness} | {model} | {score:.2f} | {files} | "
            f"{cit_pp} | {mermaid} | {tables} | {delta} |"
        )
    lines.append("")

    # Per-repo subscore breakdown
    for repo in REPOS:
        repo_runs = [r for r in runs if r["name"].startswith(repo)]
        if not repo_runs:
            continue
        lines.append(f"## {repo.capitalize()} — Subscore Breakdown\n")
        lines.append("| Run | Structure /25 | Citations /30 | Diagrams /15 | Tables /10 | Completeness /10 | Transparency /10 |")
        lines.append("|-----|:---:|:---:|:---:|:---:|:---:|:---:|")

        if include_baseline:
            b = CLAUDE_BASELINE.get(repo, {})
            ss = b.get("ss", {})
            lines.append(
                f"| {repo}-claude (baseline) | {ss.get('structure',25)} | "
                f"{ss.get('citations',30)} | {ss.get('diagrams',15)} | "
                f"{ss.get('tables',10)} | {ss.get('completeness',10)} | "
                f"{ss.get('transparency',10)} |"
            )

        for run in sorted(repo_runs, key=lambda r: r.get("score", 0), reverse=True):
            ss = run.get("subscores", {})
            lines.append(
                f"| {run['name']} | {ss.get('structure','?')} | {ss.get('citations','?')} | "
                f"{ss.get('diagrams','?')} | {ss.get('tables','?')} | "
                f"{ss.get('completeness','?')} | {ss.get('transparency','?')} |"
            )
        lines.append("")

    return "\n".join(lines)


# ── Main ────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(description="Score multi-harness wiki outputs")
    parser.add_argument("--outputs-dir", default=None)
    parser.add_argument("--no-baseline", action="store_true",
                        help="Omit Claude baseline from comparison")
    args = parser.parse_args()

    outputs_dir = Path(args.outputs_dir) if args.outputs_dir else SCRIPT_DIR / "outputs"
    if not outputs_dir.exists():
        print(f"No outputs found at {outputs_dir}")
        print("Run  bash evals/run.sh  first to generate outputs.")
        sys.exit(0)

    runs = find_runs(outputs_dir)
    if not runs:
        print(f"No completed wiki runs found in {outputs_dir}")
        sys.exit(0)

    print(f"\nFound {len(runs)} completed run(s):")
    for r in runs:
        print(f"  {r['name']}  ({r['md_count']} pages)  [{r['harness']} · {r['model']}]")

    print("\nScoring with eval.py...")
    scores = score_all(outputs_dir)

    run_meta = {r["name"]: r for r in runs}
    report_md = outputs_dir.parent / "report.md"
    report_md.write_text(
        build_report(scores, run_meta, include_baseline=not args.no_baseline),
        encoding="utf-8",
    )
    print(f"\nReport → {report_md}")

    successful = [r for r in scores.get("runs", []) if r.get("score", 0) > 0]
    if successful:
        sc = [r["score"] for r in successful]
        print(f"\nSummary ({len(successful)} successful runs):")
        print(f"  Mean:  {sum(sc)/len(sc):.2f}")
        print(f"  Best:  {max(successful, key=lambda r: r['score'])['name']}")
        print(f"  Worst: {min(successful, key=lambda r: r['score'])['name']}")


if __name__ == "__main__":
    main()
