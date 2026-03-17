#!/usr/bin/env bash
# ============================================================
# evals/run.sh — Codebase Onboarding Skill | Unified Harness
# ============================================================
# Runs the wiki-generation task across one or more LLM harnesses
# (Claude Code CLI, Gemini CLI, OpenAI Codex CLI) and scores all
# outputs automatically when done.
#
# Prerequisites (install what you plan to use):
#   Claude  —  npm install -g @anthropic-ai/claude-code
#   Gemini  —  npm install -g @google/gemini-cli
#   Codex   —  npm install -g @openai/codex
#
#   Python  —  pip install -r scripts/requirements.txt
#
# Usage:
#   bash evals/run.sh                          # all harnesses, all repos
#   bash evals/run.sh --harness gemini         # one harness, all repos
#   bash evals/run.sh --harness codex axios    # one harness, one repo
#   bash evals/run.sh --score-only             # skip generation, re-score
#
# Model overrides (env vars):
#   CLAUDE_MODEL=claude-sonnet-4-6
#   GEMINI_MODEL=gemini-2.5-pro
#   CODEX_MODEL=gpt-5.2
#
# Output layout (all gitignored — only evals/results/ is committed):
#   evals/outputs/{repo}-{harness}-{model}/outputs/wiki/*.md
#   evals/repos/{repo}/                          ← shallow clones
# ============================================================

set -euo pipefail

# ── Paths ───────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUTS_DIR="$SCRIPT_DIR/outputs"
REPOS_DIR="$SCRIPT_DIR/repos"

# ── Models ──────────────────────────────────────────────────
CLAUDE_MODEL="${CLAUDE_MODEL:-claude-sonnet-4-6}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-2.5-pro}"
CODEX_MODEL="${CODEX_MODEL:-gpt-5.2}"

# ── Repos ───────────────────────────────────────────────────
ALL_REPOS=(
  "axios   https://github.com/axios/axios.git"
  "flask   https://github.com/pallets/flask.git"
  "express https://github.com/expressjs/express.git"
)

# ── Argument Parsing ────────────────────────────────────────
HARNESS="all"      # claude | gemini | codex | all
REPO_FILTER=""     # empty = all repos
SCORE_ONLY=false

usage() {
  echo "Usage: bash evals/run.sh [OPTIONS] [REPO]"
  echo ""
  echo "Options:"
  echo "  --harness <claude|gemini|codex|all>   Harness to run (default: all)"
  echo "  --score-only                          Skip generation, re-score existing outputs"
  echo "  --help                                Show this help"
  echo ""
  echo "Examples:"
  echo "  bash evals/run.sh                          # all harnesses, all repos"
  echo "  bash evals/run.sh --harness gemini         # gemini only, all repos"
  echo "  bash evals/run.sh --harness codex axios    # codex on axios only"
  echo "  bash evals/run.sh --score-only             # just re-score"
  echo ""
  echo "Environment:"
  echo "  CLAUDE_MODEL=claude-sonnet-4-6   GEMINI_MODEL=gemini-2.5-pro   CODEX_MODEL=gpt-5.2"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --harness)    HARNESS="$2"; shift 2 ;;
    --score-only) SCORE_ONLY=true; shift ;;
    --help|-h)    usage ;;
    axios|flask|express) REPO_FILTER="$1"; shift ;;
    *) echo "Unknown argument: $1"; echo "Run with --help for usage."; exit 1 ;;
  esac
done

# Filter repo list if a specific repo was requested
if [[ -n "$REPO_FILTER" ]]; then
  REPOS=("$(printf '%s\n' "${ALL_REPOS[@]}" | grep "^$REPO_FILTER ")")
else
  REPOS=("${ALL_REPOS[@]}")
fi

# ── Helpers ─────────────────────────────────────────────────
log_claude() { echo -e "\033[1;35m[claude]\033[0m $*"; }
log_gemini() { echo -e "\033[1;34m[gemini]\033[0m $*"; }
log_codex()  { echo -e "\033[1;36m[codex]\033[0m $*";  }
ok()         { echo -e "\033[1;32m[ok]\033[0m $*";    }
warn()       { echo -e "\033[1;33m[warn]\033[0m $*";  }
die()        { echo -e "\033[1;31m[error]\033[0m $*"; exit 1; }

print_header() {
  echo ""
  echo "══════════════════════════════════════════════════════════"
  echo "  Codebase Onboarding Skill — Eval Harness"
  echo "══════════════════════════════════════════════════════════"
  echo "  Harness(es): $HARNESS"
  [[ -n "$REPO_FILTER" ]] && echo "  Repo:        $REPO_FILTER" || echo "  Repos:       axios · flask · express"
  [[ "$HARNESS" == "claude" || "$HARNESS" == "all" ]] && echo "  Claude:      $CLAUDE_MODEL"
  [[ "$HARNESS" == "gemini" || "$HARNESS" == "all" ]] && echo "  Gemini:      $GEMINI_MODEL"
  [[ "$HARNESS" == "codex"  || "$HARNESS" == "all" ]] && echo "  Codex:       $CODEX_MODEL"
  echo "══════════════════════════════════════════════════════════"
  echo ""
}

# ── Shared: Clone repo ───────────────────────────────────────
clone_repo() {
  local name="$1" url="$2"
  local dest="$REPOS_DIR/$name"
  if [[ -d "$dest/.git" ]]; then
    echo "  Repo '$name' already cloned — skipping"
  else
    echo "  Cloning $url → $dest"
    git clone --depth=1 "$url" "$dest"
  fi
}

# ── Shared: Run analyzer ─────────────────────────────────────
run_analyzer() {
  local name="$1" run_dir="$2"
  local analysis_file="$run_dir/analysis.json"
  mkdir -p "$run_dir"
  if [[ -f "$analysis_file" ]]; then
    echo "  Analysis already exists — skipping"
    return
  fi
  echo "  Running analyze.py on '$name'..."
  python3 "$SKILL_ROOT/scripts/analyze.py" \
    "$REPOS_DIR/$name" \
    --output "$analysis_file"
  ok "Analysis → $analysis_file"
}

# ── Shared: Write eval metadata ──────────────────────────────
write_eval_metadata() {
  local name="$1" harness="$2" model="$3" run_dir="$4"
  python3 - <<PYEOF
import json, datetime
meta = {
  "eval_name": "${name}-${harness}-${model}",
  "harness": "${harness}",
  "model": "${model}",
  "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
  "repo": "${name}",
  "assertions": [
    {"text": "Index file (00-index.md) is present"},
    {"text": "Every content page contains a TL;DR section"},
    {"text": "At least one Mermaid diagram per content page"},
    {"text": "Source citations use file:line format"},
    {"text": "Key Concepts table present on every content page"},
    {"text": "At least 8 markdown files generated"},
    {"text": "No hallucinated file paths"}
  ]
}
with open("${run_dir}/eval_metadata.json", "w") as f:
    json.dump(meta, f, indent=2)
PYEOF
}

# ════════════════════════════════════════════════════════════
# HARNESS 1 — Claude Code CLI
# ════════════════════════════════════════════════════════════
check_claude() {
  command -v claude >/dev/null 2>&1 || {
    warn "claude CLI not found."
    warn "Install: npm install -g @anthropic-ai/claude-code"
    warn "Then run: claude (first time to authenticate)"
    return 1
  }
}

build_claude_prompt() {
  local name="$1" run_dir="$2"
  local wiki_out="$run_dir/outputs/wiki"
  local analysis_file="$run_dir/analysis.json"

  cat <<PROMPT
You are generating a DeepWiki-style onboarding wiki for the **${name}** codebase.
This is an automated evaluation run. Follow every instruction exactly.

## Context
- Skill root: ${SKILL_ROOT}/
- Repo path:  ${REPOS_DIR}/${name}/
- Analysis JSON: ${analysis_file}
- Output directory: ${wiki_out}/

## Step 1 — Read instructions
Read in order before writing anything:
1. ${SKILL_ROOT}/SKILL.md
2. ${SKILL_ROOT}/references/page-template.md
3. ${SKILL_ROOT}/references/diagram-patterns.md
4. ${SKILL_ROOT}/references/language-guides.md
5. ${analysis_file}

## Step 2 — Explore source code
Browse ${REPOS_DIR}/${name}/ and read at least 15–20 source files.

## Step 3 — Write the wiki
Create ${wiki_out}/ and write at least 8 Markdown files:
  00-index.md, 01-overview.md, 02-[subsystem].md ...

## Step 4 — Quality requirements (scored by evals/score.py)
Every content page MUST have: TL;DR · Relevant Source Files table · Mermaid diagram ·
Key Concepts table · prose with file:line citations · cross-references · [NEEDS INVESTIGATION] markers.

## Done
Print: EVAL_DONE: ${name} | <N> pages | <words> words
PROMPT
}

run_claude_for_repo() {
  local name="$1"
  local model_tag="$(echo "$CLAUDE_MODEL" | tr '/' '-' | tr ' ' '-')"
  local run_dir="$OUTPUTS_DIR/${name}-claude-${model_tag}"
  local wiki_dir="$run_dir/outputs/wiki"

  local page_count
  page_count=$(find "$wiki_dir" -name "*.md" 2>/dev/null | wc -l | tr -d ' ') || page_count=0
  if [[ "$page_count" -ge 8 ]]; then
    warn "Skipping '${name}-claude' — $page_count pages exist (delete $wiki_dir to re-run)"
    return
  fi

  mkdir -p "$wiki_dir"
  run_analyzer "$name" "$run_dir"

  log_claude "Building task prompt for '$name'..."
  local prompt_file="$run_dir/claude_prompt.txt"
  build_claude_prompt "$name" "$run_dir" > "$prompt_file"
  ok "Prompt → $prompt_file ($(wc -c < "$prompt_file") bytes)"

  local log_file="$run_dir/claude_run.log"
  log_claude "Invoking: claude --model $CLAUDE_MODEL -p <prompt>"
  log_claude "Log → $log_file"

  local exit_code=0
  set +e
  (
    cd "$SKILL_ROOT"
    claude \
      --model "$CLAUDE_MODEL" \
      -p "$(cat "$prompt_file")" \
      >"$log_file" 2>&1
  ) &
  local claude_pid=$!
  local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏' i=0
  while kill -0 "$claude_pid" 2>/dev/null; do
    printf "\r\033[1;35m[claude]\033[0m %s  Generating wiki for '%s' ..." \
      "${spin:$((i % ${#spin})):1}" "$name"
    sleep 0.15; ((i++)) || true
  done
  wait "$claude_pid"; exit_code=$?
  printf "\r\033[K"
  set -e

  if [[ $exit_code -ne 0 ]]; then
    warn "claude exited $exit_code — last 20 lines:"
    tail -20 "$log_file" 2>/dev/null | sed 's/^/    /'
  fi

  local count
  count=$(find "$wiki_dir" -name "*.md" 2>/dev/null | wc -l | tr -d ' ') || count=0
  if [[ "$count" -ge 8 ]]; then
    ok "Claude: $count pages → $wiki_dir"
    write_eval_metadata "$name" "claude" "$CLAUDE_MODEL" "$run_dir"
  else
    warn "Only $count pages found in $wiki_dir — check $log_file"
  fi
}

# ════════════════════════════════════════════════════════════
# HARNESS 2 — Gemini CLI
# ════════════════════════════════════════════════════════════
check_gemini() {
  command -v gemini >/dev/null 2>&1 || {
    warn "gemini CLI not found."
    warn "Install: npm install -g @google/gemini-cli"
    return 1
  }
}

build_gemini_prompt() {
  local name="$1" run_dir="$2"
  local analysis_file="$run_dir/analysis.json"

  cat <<PROMPT
You are a senior software architect generating a DeepWiki-style onboarding wiki.

## Skill Instructions
$(cat "$SKILL_ROOT/SKILL.md")

## Page Template
$(cat "$SKILL_ROOT/references/page-template.md")

## Diagram Patterns
$(cat "$SKILL_ROOT/references/diagram-patterns.md")

## Language Guide
$(cat "$SKILL_ROOT/references/language-guides.md" 2>/dev/null || echo "(not found)")

## Codebase Analysis
\`\`\`json
$(cat "$analysis_file")
\`\`\`

---

## Task

Generate a complete wiki for the **${name}** codebase using the skill instructions above.

**Output format** — use these exact markers, one per file:

\`\`\`
---FILE: 00-index.md---
(content)
---FILE: 01-overview.md---
(content)
\`\`\`

Generate at least 8 files: 00-index.md, 01-overview.md, and 6+ subsystem pages.

Every content page (not 00-index.md) MUST include:
- TL;DR (2–3 sentences)
- "Relevant Source Files" table with real paths + descriptions
- Mermaid diagram with 3+ nodes
- "Key Concepts" table
- Detailed prose with source citations: \`path/to/file.ext:L45-L87\`
- Cross-references to other pages
- \`[NEEDS INVESTIGATION]\` on any unverifiable claim

Do not add text before the first ---FILE: marker or after the last file.
PROMPT
}

run_gemini_for_repo() {
  local name="$1"
  local model_tag="$(echo "$GEMINI_MODEL" | tr '/' '-' | tr ' ' '-')"
  local run_dir="$OUTPUTS_DIR/${name}-gemini-${model_tag}"
  local wiki_dir="$run_dir/outputs/wiki"

  local page_count
  page_count=$(find "$wiki_dir" -name "*.md" 2>/dev/null | wc -l | tr -d ' ') || page_count=0
  if [[ "$page_count" -ge 8 ]]; then
    warn "Skipping '${name}-gemini' — $page_count pages exist (delete $wiki_dir to re-run)"
    return
  fi

  mkdir -p "$wiki_dir"
  run_analyzer "$name" "$run_dir"

  log_gemini "Building prompt for '$name'..."
  local prompt_file="$run_dir/gemini_prompt.txt"
  build_gemini_prompt "$name" "$run_dir" > "$prompt_file"
  ok "Prompt → $prompt_file ($(wc -c < "$prompt_file") bytes)"

  local raw_file="$run_dir/raw_response.txt"
  log_gemini "Calling: gemini --model $GEMINI_MODEL"

  local exit_code=0
  set +e
  gemini --model "$GEMINI_MODEL" < "$prompt_file" > "$raw_file" 2>&1
  exit_code=$?
  set -e

  if [[ $exit_code -ne 0 ]]; then
    warn "gemini exited $exit_code — response: $(head -5 "$raw_file")"
    return
  fi
  ok "Raw response → $raw_file ($(wc -c < "$raw_file") bytes)"

  log_gemini "Parsing output into wiki files..."
  python3 "$SCRIPT_DIR/parse_gemini.py" "$raw_file" "$wiki_dir"

  local count
  count=$(find "$wiki_dir" -name "*.md" 2>/dev/null | wc -l | tr -d ' ') || count=0
  if [[ "$count" -ge 8 ]]; then
    ok "Gemini: $count pages → $wiki_dir"
    write_eval_metadata "$name" "gemini" "$GEMINI_MODEL" "$run_dir"
  else
    warn "Only $count pages found — check $raw_file"
  fi
}

# ════════════════════════════════════════════════════════════
# HARNESS 3 — OpenAI Codex CLI
# ════════════════════════════════════════════════════════════
check_codex() {
  command -v codex >/dev/null 2>&1 || {
    warn "codex CLI not found."
    warn "Install: npm install -g @openai/codex"
    warn "Then run: codex (first time to authenticate)"
    return 1
  }
}

build_codex_prompt() {
  local name="$1" run_dir="$2"
  local wiki_out="$run_dir/outputs/wiki"
  local analysis_file="$run_dir/analysis.json"

  cat <<PROMPT
You are generating a DeepWiki-style onboarding wiki for the **${name}** codebase.
This is an automated evaluation run. Follow every instruction exactly.

## Context
- Skill root: ${SKILL_ROOT}/
- Repo path:  ${REPOS_DIR}/${name}/
- Analysis JSON: ${analysis_file}
- Output directory: ${wiki_out}/

## Step 1 — Read instructions
Read in order before writing anything:
1. ${SKILL_ROOT}/SKILL.md
2. ${SKILL_ROOT}/references/page-template.md
3. ${SKILL_ROOT}/references/diagram-patterns.md
4. ${SKILL_ROOT}/references/language-guides.md
5. ${analysis_file}

## Step 2 — Explore source code
Browse ${REPOS_DIR}/${name}/ and read at least 15–20 source files.

## Step 3 — Write the wiki
Create ${wiki_out}/ and write at least 8 Markdown files:
  00-index.md, 01-overview.md, 02-[subsystem].md ...

## Step 4 — Quality requirements (scored by evals/score.py)
Every content page MUST have: TL;DR · Relevant Source Files table · Mermaid diagram ·
Key Concepts table · prose with file:line citations · cross-references · [NEEDS INVESTIGATION] markers.

## Step 5 — Write eval metadata
Write: ${run_dir}/eval_metadata.json
{ "eval_name": "${name}-codex-${CODEX_MODEL}", "harness": "codex-cli", "model": "${CODEX_MODEL}" }

## Done
Print: EVAL_DONE: ${name} | <N> pages | <words> words
PROMPT
}

run_codex_for_repo() {
  local name="$1"
  local model_tag="$(echo "$CODEX_MODEL" | tr '/' '-' | tr ' ' '-')"
  local run_dir="$OUTPUTS_DIR/${name}-codex-${model_tag}"
  local wiki_dir="$run_dir/outputs/wiki"

  local page_count
  page_count=$(find "$wiki_dir" -name "*.md" 2>/dev/null | wc -l | tr -d ' ') || page_count=0
  if [[ "$page_count" -ge 8 ]]; then
    warn "Skipping '${name}-codex' — $page_count pages exist (delete $wiki_dir to re-run)"
    return
  fi

  mkdir -p "$wiki_dir"
  run_analyzer "$name" "$run_dir"

  log_codex "Building prompt for '$name'..."
  local prompt_file="$run_dir/codex_prompt.txt"
  build_codex_prompt "$name" "$run_dir" > "$prompt_file"
  ok "Prompt → $prompt_file ($(wc -c < "$prompt_file") bytes)"

  # Auto-detect flags supported by this Codex version
  local extra_flags=""
  if codex exec --help 2>&1 | grep -q -- "--full-auto"; then
    extra_flags="--full-auto"
  elif codex exec --help 2>&1 | grep -q -- "--approval-policy"; then
    extra_flags="--approval-policy never"
  fi

  local log_file="$run_dir/codex_run.log"
  log_codex "Invoking: codex exec --model $CODEX_MODEL $extra_flags"
  log_codex "Log → $log_file"

  local exit_code=0
  set +e
  (
    cd "$SKILL_ROOT"
    codex exec \
      --model "$CODEX_MODEL" \
      $extra_flags \
      "$(cat "$prompt_file")" \
      >"$log_file" 2>&1
  ) &
  local codex_pid=$!
  local spin='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏' i=0
  while kill -0 "$codex_pid" 2>/dev/null; do
    printf "\r\033[1;36m[codex]\033[0m %s  Generating wiki for '%s' ..." \
      "${spin:$((i % ${#spin})):1}" "$name"
    sleep 0.15; ((i++)) || true
  done
  wait "$codex_pid"; exit_code=$?
  printf "\r\033[K"
  set -e

  if [[ $exit_code -ne 0 ]]; then
    warn "codex exited $exit_code — last 20 lines:"
    tail -20 "$log_file" 2>/dev/null | sed 's/^/    /'
  fi

  local count
  count=$(find "$wiki_dir" -name "*.md" 2>/dev/null | wc -l | tr -d ' ') || count=0
  if [[ "$count" -ge 8 ]]; then
    ok "Codex: $count pages → $wiki_dir"
    write_eval_metadata "$name" "codex" "$CODEX_MODEL" "$run_dir"
  else
    warn "Only $count pages found — check $log_file"
  fi
}

# ════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════
check_python() {
  command -v python3 >/dev/null 2>&1 || die "python3 not found"
  python3 -c "import tree_sitter" 2>/dev/null || {
    warn "Python deps not installed — running pip install..."
    pip install -r "$SKILL_ROOT/scripts/requirements.txt" --break-system-packages -q
  }
}

if [[ "$SCORE_ONLY" == "false" ]]; then
  print_header
  check_python
  mkdir -p "$REPOS_DIR" "$OUTPUTS_DIR"

  # Determine which harnesses to run
  RUN_CLAUDE=false; RUN_GEMINI=false; RUN_CODEX=false
  case "$HARNESS" in
    all)    RUN_CLAUDE=true; RUN_GEMINI=true; RUN_CODEX=true ;;
    claude) RUN_CLAUDE=true ;;
    gemini) RUN_GEMINI=true ;;
    codex)  RUN_CODEX=true  ;;
    *) die "Unknown harness '$HARNESS'. Choose: claude | gemini | codex | all" ;;
  esac

  # Skip harnesses whose CLI is unavailable
  $RUN_CLAUDE && { check_claude || { warn "Skipping Claude harness."; RUN_CLAUDE=false; }; }
  $RUN_GEMINI && { check_gemini || { warn "Skipping Gemini harness."; RUN_GEMINI=false; }; }
  $RUN_CODEX  && { check_codex  || { warn "Skipping Codex harness.";  RUN_CODEX=false;  }; }

  for entry in "${REPOS[@]}"; do
    read -r name url <<< "$entry"
    echo ""
    echo "────────────────────────────────────────────────────"
    echo "  Repo: $name"
    echo "────────────────────────────────────────────────────"
    clone_repo "$name" "$url"
    $RUN_CLAUDE && run_claude_for_repo "$name"
    $RUN_GEMINI && run_gemini_for_repo "$name"
    $RUN_CODEX  && run_codex_for_repo  "$name"
  done
fi

# ── Score all outputs ────────────────────────────────────────
echo ""
echo "────────────────────────────────────────────────────"
echo "  Scoring all runs..."
echo "────────────────────────────────────────────────────"
python3 "$SCRIPT_DIR/score.py" --outputs-dir "$OUTPUTS_DIR" 2>&1 || \
  warn "Scoring failed — run manually: python3 evals/score.py"

echo ""
ok "All done. Results → evals/outputs/"
