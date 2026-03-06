#!/usr/bin/env python3
"""
Evaluate onboarding doc quality across multiple LLM/harness runs.

The script expects a directory where each immediate subdirectory is one run,
for example:

  runs/
    gpt5-codex/
      wiki/00-index.md
      wiki/01-overview.md
    claude-code/
      wiki/00-index.md
      wiki/01-overview.md

Scoring is heuristic and deterministic:
- Structure coverage (required sections, file count)
- Citation quality (source-linked claims)
- Diagram/table presence
- Completeness (index + TL;DR coverage)
- Transparency markers ([NEEDS INVESTIGATION], limitations)

It also reports cross-run consistency based on heading-set Jaccard similarity.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


REQUIRED_HEADINGS = {
    "relevant source files",
    "tl;dr",
    "overview",
    "key concepts",
    "how it works",
    "component reference",
    "cross-references",
}

CITATION_RE = re.compile(
    r"(?:^|[\s`(])(?:[\w./-]+\.[A-Za-z0-9_+-]+):L?\d+(?:-L?\d+)?(?:\b|`)"
)
HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*$")
TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
TABLE_SEPARATOR_RE = re.compile(r"^\s*\|?[\s:-]+\|[\s|:-]+\|?\s*$")
CODE_FENCE_RE = re.compile(r"^\s*```")
MERMAID_BLOCK_RE = re.compile(r"^\s*```mermaid\b", re.IGNORECASE)


@dataclass
class RunMetrics:
    name: str
    path: str
    markdown_files: int
    total_words: int
    total_headings: int
    required_heading_coverage: float
    pages_with_tldr: int
    pages_with_citations: int
    citation_count: int
    citation_density_per_1k_words: float
    mermaid_blocks: int
    tables: int
    index_present: bool
    needs_investigation_mentions: int
    limitations_mentions: int
    score: float
    subscores: dict[str, float]
    notes: list[str]


def normalize_heading(text: str) -> str:
    text = text.strip().lower()
    text = re.sub(r"[`*_]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


def find_run_dirs(root: Path) -> list[Path]:
    runs = [p for p in root.iterdir() if p.is_dir() and not p.name.startswith(".")]
    return sorted(runs, key=lambda p: p.name.lower())


def markdown_files_for_run(run_dir: Path) -> list[Path]:
    files = [p for p in run_dir.rglob("*.md") if p.is_file()]
    return sorted(files, key=lambda p: str(p).lower())


def analyze_markdown(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="ignore")
    words = len(re.findall(r"\b\w+\b", text))
    citations = len(CITATION_RE.findall(text))
    needs_inv = text.count("[NEEDS INVESTIGATION]")
    limitations = len(re.findall(r"\blimitations?\b", text, re.IGNORECASE))

    headings: set[str] = set()
    heading_count = 0
    has_tldr = False
    mermaid_blocks = 0
    tables = 0

    in_code = False
    prev_table_row = False
    count_separator = False

    for line in text.splitlines():
        if CODE_FENCE_RE.match(line):
            if not in_code and MERMAID_BLOCK_RE.match(line):
                mermaid_blocks += 1
            in_code = not in_code
            prev_table_row = False
            continue
        if in_code:
            continue

        heading_match = HEADING_RE.match(line)
        if heading_match:
            heading_count += 1
            norm = normalize_heading(heading_match.group(1))
            headings.add(norm)
            if norm == "tl;dr":
                has_tldr = True

        is_table_row = bool(TABLE_ROW_RE.match(line))
        if is_table_row and TABLE_SEPARATOR_RE.match(line):
            count_separator = True

        if prev_table_row and not is_table_row:
            tables += 1
            if count_separator:
                tables += 1
            count_separator = False

        prev_table_row = is_table_row

    if prev_table_row:
        tables += 1
        if count_separator:
            tables += 1

    return {
        "words": words,
        "citations": citations,
        "needs_inv": needs_inv,
        "limitations": limitations,
        "headings": headings,
        "heading_count": heading_count,
        "has_tldr": has_tldr,
        "mermaid_blocks": mermaid_blocks,
        "tables": tables,
    }


def score_run(run_dir: Path) -> RunMetrics:
    files = markdown_files_for_run(run_dir)
    notes: list[str] = []
    if not files:
        notes.append("No markdown files found in run directory.")

    totals = {
        "words": 0,
        "citations": 0,
        "needs_inv": 0,
        "limitations": 0,
        "headings": set(),
        "heading_count": 0,
        "tldr_pages": 0,
        "pages_with_citations": 0,
        "mermaid_blocks": 0,
        "tables": 0,
    }

    for path in files:
        data = analyze_markdown(path)
        totals["words"] += data["words"]
        totals["citations"] += data["citations"]
        totals["needs_inv"] += data["needs_inv"]
        totals["limitations"] += data["limitations"]
        totals["headings"] |= data["headings"]
        totals["heading_count"] += data["heading_count"]
        totals["mermaid_blocks"] += data["mermaid_blocks"]
        totals["tables"] += data["tables"]
        if data["has_tldr"]:
            totals["tldr_pages"] += 1
        if data["citations"] > 0:
            totals["pages_with_citations"] += 1

    file_count = len(files)
    heading_coverage = len(REQUIRED_HEADINGS & totals["headings"]) / len(REQUIRED_HEADINGS)
    pages_with_citation_ratio = (
        totals["pages_with_citations"] / file_count if file_count else 0.0
    )
    tldr_ratio = totals["tldr_pages"] / file_count if file_count else 0.0
    citations_per_1k_words = (
        totals["citations"] / max(totals["words"] / 1000.0, 1.0) if totals["words"] else 0.0
    )

    structure_score = 10.0 * clamp(file_count / 5.0) + 15.0 * heading_coverage
    citation_score = 15.0 * clamp(citations_per_1k_words / 6.0) + 15.0 * pages_with_citation_ratio
    diagram_target = max(1, file_count // 4) if file_count else 1
    table_target = max(1, file_count // 3) if file_count else 1
    diagram_score = 15.0 * clamp(totals["mermaid_blocks"] / diagram_target)
    table_score = 10.0 * clamp(totals["tables"] / table_target)

    index_present = any(p.name in {"00-index.md", "index.md"} for p in files)
    completeness_score = 4.0 * (1.0 if index_present else 0.0) + 6.0 * tldr_ratio

    transparency_markers = totals["needs_inv"] + totals["limitations"]
    if transparency_markers == 0:
        transparency_score = 0.0
    else:
        soft_cap = max(1, file_count)
        transparency_score = 10.0 * clamp(soft_cap / transparency_markers)
        transparency_score = max(transparency_score, 3.0)

    score = (
        structure_score
        + citation_score
        + diagram_score
        + table_score
        + completeness_score
        + transparency_score
    )

    if file_count == 0:
        score = 0.0
    if heading_coverage < 0.4:
        notes.append("Low required-section coverage; outputs likely inconsistent.")
    if pages_with_citation_ratio < 0.5:
        notes.append("Many pages have no source citations.")
    if totals["mermaid_blocks"] == 0:
        notes.append("No Mermaid diagrams found.")
    if not index_present:
        notes.append("No index page (`00-index.md` or `index.md`) found.")

    subscores = {
        "structure": round(structure_score, 2),
        "citations": round(citation_score, 2),
        "diagrams": round(diagram_score, 2),
        "tables": round(table_score, 2),
        "completeness": round(completeness_score, 2),
        "transparency": round(transparency_score, 2),
    }

    return RunMetrics(
        name=run_dir.name,
        path=str(run_dir.resolve()),
        markdown_files=file_count,
        total_words=totals["words"],
        total_headings=totals["heading_count"],
        required_heading_coverage=round(heading_coverage, 4),
        pages_with_tldr=totals["tldr_pages"],
        pages_with_citations=totals["pages_with_citations"],
        citation_count=totals["citations"],
        citation_density_per_1k_words=round(citations_per_1k_words, 4),
        mermaid_blocks=totals["mermaid_blocks"],
        tables=totals["tables"],
        index_present=index_present,
        needs_investigation_mentions=totals["needs_inv"],
        limitations_mentions=totals["limitations"],
        score=round(score, 2),
        subscores=subscores,
        notes=notes,
    )


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    return (len(a & b) / len(union)) if union else 0.0


def heading_set_for_run(run_dir: Path) -> set[str]:
    all_headings: set[str] = set()
    for path in markdown_files_for_run(run_dir):
        data = analyze_markdown(path)
        all_headings |= data["headings"]
    return all_headings


def build_summary(runs: list[RunMetrics], run_dirs: list[Path]) -> dict:
    scores = [r.score for r in runs]
    ranking = sorted(runs, key=lambda r: (-r.score, r.name.lower()))

    similarities: list[float] = []
    heading_sets = {run_dir.name: heading_set_for_run(run_dir) for run_dir in run_dirs}
    run_names = sorted(heading_sets)
    for i, left in enumerate(run_names):
        for right in run_names[i + 1 :]:
            similarities.append(jaccard_similarity(heading_sets[left], heading_sets[right]))

    if scores:
        score_mean = round(statistics.mean(scores), 2)
        score_std = round(statistics.pstdev(scores), 2) if len(scores) > 1 else 0.0
        best = ranking[0].name
        worst = ranking[-1].name
    else:
        score_mean = 0.0
        score_std = 0.0
        best = ""
        worst = ""

    consistency = round(statistics.mean(similarities), 4) if similarities else 1.0

    return {
        "run_count": len(runs),
        "score_mean": score_mean,
        "score_stddev": score_std,
        "best_run": best,
        "worst_run": worst,
        "heading_jaccard_mean": consistency,
        "ranking": [r.name for r in ranking],
    }


def print_report(runs: list[RunMetrics], summary: dict) -> None:
    print(
        "run".ljust(22)
        + "score".rjust(8)
        + " files".rjust(7)
        + " cit/page".rjust(10)
        + " mermaid".rjust(9)
        + " req%".rjust(7)
        + " index".rjust(7)
    )
    print("-" * 70)
    for run in sorted(runs, key=lambda x: (-x.score, x.name.lower())):
        cit_per_page = run.citation_count / run.markdown_files if run.markdown_files else 0.0
        req_percent = int(round(run.required_heading_coverage * 100))
        print(
            run.name[:22].ljust(22)
            + f"{run.score:8.2f}"
            + f"{run.markdown_files:7d}"
            + f"{cit_per_page:10.2f}"
            + f"{run.mermaid_blocks:9d}"
            + f"{req_percent:7d}"
            + f"{('yes' if run.index_present else 'no'):>7}"
        )
    print("-" * 70)
    print(
        f"mean={summary['score_mean']:.2f} "
        f"stddev={summary['score_stddev']:.2f} "
        f"heading_jaccard_mean={summary['heading_jaccard_mean']:.4f}"
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Score onboarding-doc outputs across LLM/harness runs."
    )
    parser.add_argument(
        "runs_dir",
        help="Directory containing one subdirectory per run.",
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Write JSON report to this path.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress console table output.",
    )
    args = parser.parse_args()

    root = Path(args.runs_dir).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory.")
        return 1

    run_dirs = find_run_dirs(root)
    if not run_dirs:
        print(f"Error: no run directories found under {root}")
        return 1

    runs = [score_run(run_dir) for run_dir in run_dirs]
    summary = build_summary(runs, run_dirs)
    report = {
        "version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runs_dir": str(root),
        "runs": [asdict(run) for run in runs],
        "summary": summary,
    }

    if args.output:
        output_path = Path(args.output).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(report, indent=2))

    if not args.quiet:
        print_report(runs, summary)
        if args.output:
            print(f"\nReport written to: {Path(args.output).resolve()}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
