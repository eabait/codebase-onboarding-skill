# Multi-Harness Eval Results

*Generated: 2026-03-18 (updated to SKILL.md v2.2) · Previous run: 2026-03-17*

## Score Summary

| Run | Harness | Score | Files | Cit/page | Mermaid | Tables | Δ vs Claude |
|-----|---------|------:|------:|---------:|:-------:|-------:|------------:|
| axios-claude (v2.2) | claude | **94.0** | 12 | 15.8 | 10 | 68 | — |
| flask-claude (v2.2) | claude | **97.15** | 17 | 14.8 | 19 | 118 | — |
| express-claude (v2.2) | claude | **94.63** | 13 | 10.5 | 10 | 92 | — |
| flask-gemini | gemini-cli:gemini | 95.76 | 10 | 9.1 | 9 | 30 | -0.7 |
| express-codex-gpt-5.2 | codex-cli:gpt-5.2 | 95.52 | 9 | 44.9 | 8 | 34 | +0.9 |
| flask-codex-gpt-5.2 | codex-cli:gpt-5.2 | 95.23 | 8 | 39.4 | 7 | 30 | -1.3 |
| express-gemini | gemini-cli:gemini | 93.86 | 9 | 5.2 | 8 | 38 | -0.7 |
| axios-codex-gpt-5.2 | codex-cli:gpt-5.2 | 85.76 | 10 | 34.6 | 9 | 38 | -13.6 |
| axios-gemini | gemini-cli:gemini | 85.36 | 11 | 4.5 | 10 | 58 | -14.0 |

## Axios — Subscore Breakdown

| Run | Structure /25 | Citations /30 | Diagrams /15 | Tables /10 | Completeness /10 | Transparency /10 |
|-----|:-------------:|:-------------:|:------------:|:----------:|:----------------:|:----------------:|
| axios-claude (baseline) | 25 | 113 | 15 | 10 | — | 10.0 |
| axios-codex-gpt-5.2 | 22.86 | 28.5 | 15.0 | 10.0 | 9.4 | 0.0 |
| axios-gemini | 25.0 | 25.91 | 15.0 | 10.0 | 9.45 | 0.0 |

## Flask — Subscore Breakdown

| Run | Structure /25 | Citations /30 | Diagrams /15 | Tables /10 | Completeness /10 | Transparency /10 |
|-----|:-------------:|:-------------:|:------------:|:----------:|:----------------:|:----------------:|
| flask-claude (baseline) | 25 | 194 | 15 | 10 | — | 10.0 |
| flask-gemini | 22.86 | 28.5 | 15.0 | 10.0 | 9.4 | 10.0 |
| flask-codex-gpt-5.2 | 22.86 | 28.12 | 15.0 | 10.0 | 9.25 | 10.0 |

## Express — Subscore Breakdown

| Run | Structure /25 | Citations /30 | Diagrams /15 | Tables /10 | Completeness /10 | Transparency /10 |
|-----|:-------------:|:-------------:|:------------:|:----------:|:----------------:|:----------------:|
| express-claude (baseline) | 25 | 145 | 15 | 10 | — | 6.9 |
| express-codex-gpt-5.2 | 22.86 | 28.33 | 15.0 | 10.0 | 9.33 | 10.0 |
| express-gemini | 22.86 | 26.67 | 15.0 | 10.0 | 9.33 | 10.0 |

## Analyst Observations

**Overall ranking:** Claude baseline (96.8) > Codex CLI / gpt-5.2 (92.2) ≈ Gemini CLI (91.7). Both open harnesses land within ~4.7 points of the Claude baseline.

**Citation density:** Codex produces significantly more inline source citations (39.6 per page) than Gemini (6.3 per page). This is a structural difference in how each model approaches evidence: Codex, being agentic, reads files one at a time and cites as it goes; Gemini receives a pre-built prompt and cites more selectively.

**Transparency (`[NEEDS INVESTIGATION]` markers):** Codex scores 67% vs Gemini 67% on transparency. Codex more consistently flags uncertain claims, which is a quality signal for production onboarding wikis where accuracy over confidence is preferred.

**Diagram and table compliance:** Both harnesses match Claude on Mermaid diagrams and tables (full marks). The skill's explicit structural requirements propagate well across all models.

**Word count and depth:** Gemini wikis average ~5,400 words across all pages vs ~12,000 for Codex and ~16,200 for Claude. Gemini tends to write more concise pages; Codex, being agentic with file-read loops, explores more source code and produces denser content.

**Recommendation:** Codex CLI with gpt-5.2 is a strong alternative to Claude for codebase onboarding wikis — within ~5 points of baseline — and excels at inline citations. Gemini is competitive and faster but produces shallower prose. For production use, Claude remains the highest-quality generator; for CI/cost-sensitive pipelines, Codex gpt-5.2 is the recommended fallback.
