#!/usr/bin/env python3
"""
Codebase Analyzer v2 — Orchestrator for the Codebase Onboarding Skill.

Composes specialized tools instead of reimplementing parsers:
  - tree-sitter-language-pack: AST-level code structure extraction
  - pathspec: .gitignore-aware file traversal
  - networkx: PageRank-based importance ranking
  - tokei/scc (CLI): Accurate language statistics
  - git log: Hotspot detection and contributor mapping

Each phase degrades gracefully if its dependency is missing, producing
a partial report with clear markers for what was skipped.

Usage:
    pip install tree-sitter tree-sitter-language-pack pathspec networkx
    python analyze.py <repo_path> [--output <path>] [--max-depth <n>]
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Dependency detection — each tool is optional with graceful fallback
# ---------------------------------------------------------------------------

HAS_PATHSPEC = False
HAS_TREESITTER = False
HAS_NETWORKX = False
HAS_TOMLLIB = False

try:
    import pathspec
    HAS_PATHSPEC = True
except ImportError:
    pass

try:
    from tree_sitter_language_pack import get_parser, get_language
    HAS_TREESITTER = True
except ImportError:
    try:
        from tree_sitter_languages import get_parser, get_language
        HAS_TREESITTER = True
    except ImportError:
        pass

# Detect tree-sitter API version (0.25.x uses Query + QueryCursor)
HAS_QUERY_CURSOR = False
if HAS_TREESITTER:
    try:
        from tree_sitter import Query, QueryCursor
        HAS_QUERY_CURSOR = True
    except ImportError:
        pass

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    pass

try:
    import tomllib  # Python 3.11+
    HAS_TOMLLIB = True
except ImportError:
    try:
        import tomli as tomllib  # fallback for 3.10
        HAS_TOMLLIB = True
    except ImportError:
        pass


# ---------------------------------------------------------------------------
# Extension → tree-sitter language name mapping
# ---------------------------------------------------------------------------

EXT_TO_TS_LANG = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".tsx": "tsx", ".jsx": "javascript",
    ".go": "go", ".rs": "rust", ".java": "java", ".kt": "kotlin",
    ".cs": "c_sharp", ".rb": "ruby", ".php": "php", ".swift": "swift",
    ".c": "c", ".cpp": "cpp", ".h": "c", ".hpp": "cpp",
    ".scala": "scala", ".ex": "elixir", ".exs": "elixir",
    ".lua": "lua", ".dart": "dart", ".zig": "zig",
    ".sh": "bash", ".bash": "bash",
}

# Tree-sitter queries for extracting definitions per language family.
# These extract classes, functions, interfaces, type definitions, and exports.
TS_QUERIES = {
    "python": """
        (class_definition name: (identifier) @class_name) @class_def
        (function_definition name: (identifier) @func_name) @func_def
    """,
    "javascript": """
        (class_declaration name: (identifier) @class_name) @class_def
        (function_declaration name: (identifier) @func_name) @func_def
        (export_statement) @export
        (lexical_declaration (variable_declarator name: (identifier) @var_name)) @var_def
    """,
    "typescript": """
        (class_declaration name: (type_identifier) @class_name) @class_def
        (function_declaration name: (identifier) @func_name) @func_def
        (interface_declaration name: (type_identifier) @iface_name) @iface_def
        (type_alias_declaration name: (type_identifier) @type_name) @type_def
        (export_statement) @export
    """,
    "go": """
        (type_declaration (type_spec name: (type_identifier) @type_name)) @type_def
        (function_declaration name: (identifier) @func_name) @func_def
        (method_declaration name: (field_identifier) @method_name) @method_def
    """,
    "rust": """
        (struct_item name: (type_identifier) @struct_name) @struct_def
        (enum_item name: (type_identifier) @enum_name) @enum_def
        (function_item name: (identifier) @func_name) @func_def
        (trait_item name: (type_identifier) @trait_name) @trait_def
        (impl_item) @impl_def
    """,
    "java": """
        (class_declaration name: (identifier) @class_name) @class_def
        (interface_declaration name: (identifier) @iface_name) @iface_def
        (method_declaration name: (identifier) @method_name) @method_def
    """,
    "c_sharp": """
        (class_declaration name: (identifier) @class_name) @class_def
        (interface_declaration name: (identifier) @iface_name) @iface_def
        (method_declaration name: (identifier) @method_name) @method_def
    """,
    "ruby": """
        (class name: (constant) @class_name) @class_def
        (method name: (identifier) @method_name) @method_def
        (module name: (constant) @module_name) @module_def
    """,
}

# Alias shared queries for language variants
TS_QUERIES["tsx"] = TS_QUERIES["typescript"]
TS_QUERIES["kotlin"] = TS_QUERIES["java"]


# ---------------------------------------------------------------------------
# Phase 1: File Discovery (pathspec or fallback)
# ---------------------------------------------------------------------------

ALWAYS_SKIP = {
    "node_modules", ".git", ".svn", ".hg", "__pycache__", ".mypy_cache",
    ".pytest_cache", ".tox", ".nox", "venv", ".venv", ".env",
    "dist", "build", "out", ".next", ".nuxt", ".cache", ".turbo",
    "coverage", ".nyc_output", "target", "bin", "obj",
    ".gradle", ".idea", ".vscode", "vendor", "Pods",
}


def add_warning(
    warnings: list[dict],
    warning_keys: set[tuple[str, str, str]],
    phase: str,
    message: str,
    file_path: str | None = None,
    max_warnings: int = 200,
):
    """Add a deduplicated warning entry to the report."""
    if len(warnings) >= max_warnings:
        return
    key = (phase, message, file_path or "")
    if key in warning_keys:
        return
    warning_keys.add(key)
    entry = {"phase": phase, "message": message}
    if file_path:
        entry["file"] = file_path
    warnings.append(entry)


def load_gitignore_spec(root: Path):
    """Load .gitignore as a pathspec matcher, or return None."""
    if not HAS_PATHSPEC:
        return None
    gitignore = root / ".gitignore"
    if not gitignore.exists():
        return None
    with open(gitignore) as f:
        return pathspec.PathSpec.from_lines("gitwildmatch", f)


def discover_files(root: Path, max_depth: int = 4) -> list[dict]:
    """Walk the repo respecting .gitignore and skip dirs. Returns file metadata."""
    spec = load_gitignore_spec(root)
    files = []

    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted([
            d for d in dirnames
            if d not in ALWAYS_SKIP and not d.startswith(".")
        ])

        rel_dir = Path(dirpath).relative_to(root)
        if len(rel_dir.parts) > max_depth:
            dirnames.clear()
            continue

        for fname in sorted(filenames):
            if fname.startswith(".") and fname not in (
                ".env.example", ".gitignore", ".dockerignore"
            ):
                continue

            rel_path = str(rel_dir / fname) if str(rel_dir) != "." else fname

            if spec and spec.match_file(rel_path):
                continue

            full_path = Path(dirpath) / fname
            ext = Path(fname).suffix.lower()

            try:
                size = full_path.stat().st_size
            except OSError:
                size = 0

            files.append({
                "path": rel_path,
                "ext": ext,
                "size": size,
                "full_path": str(full_path),
            })

    return files


# ---------------------------------------------------------------------------
# Phase 2: Language Statistics (tokei/scc CLI or fallback)
# ---------------------------------------------------------------------------

def language_stats_via_cli(
    root: Path,
    warnings: list[dict] | None = None,
    warning_keys: set[tuple[str, str, str]] | None = None,
) -> dict | None:
    """Try tokei or scc for accurate language stats with proper comment handling."""
    if warnings is None:
        warnings = []
    if warning_keys is None:
        warning_keys = set()
    for tool, args, parser_fn in [
        ("tokei", ["tokei", "--output", "json", str(root)], _parse_tokei),
        ("scc", ["scc", "--format", "json", str(root)], _parse_scc),
    ]:
        if shutil.which(tool):
            try:
                result = subprocess.run(
                    args, capture_output=True, text=True, timeout=60
                )
                if result.returncode == 0:
                    return parser_fn(result.stdout)
                add_warning(
                    warnings,
                    warning_keys,
                    "language_stats",
                    f"{tool} exited with code {result.returncode}",
                )
            except subprocess.TimeoutExpired:
                add_warning(
                    warnings,
                    warning_keys,
                    "language_stats",
                    f"{tool} timed out after 60s",
                )
                continue
            except Exception as e:
                add_warning(
                    warnings,
                    warning_keys,
                    "language_stats",
                    f"{tool} invocation failed: {e}",
                )
                continue
    return None


def _parse_tokei(output: str) -> dict:
    data = json.loads(output)
    stats = {}
    for lang, info in data.items():
        if isinstance(info, dict) and "code" in info:
            stats[lang] = {
                "files": len(info.get("reports", [])),
                "code_lines": info["code"],
                "comment_lines": info.get("comments", 0),
                "blank_lines": info.get("blanks", 0),
            }
    return dict(sorted(stats.items(), key=lambda x: x[1]["code_lines"], reverse=True))


def _parse_scc(output: str) -> dict:
    data = json.loads(output)
    stats = {}
    for entry in data:
        stats[entry["Name"]] = {
            "files": entry.get("Count", 0),
            "code_lines": entry.get("Code", 0),
            "comment_lines": entry.get("Comment", 0),
            "blank_lines": entry.get("Blank", 0),
        }
    return dict(sorted(stats.items(), key=lambda x: x[1]["code_lines"], reverse=True))


def language_stats_fallback(files: list[dict]) -> dict:
    """Basic extension-based counting when no CLI tool is available."""
    lang_map = {
        ".py": "Python", ".js": "JavaScript", ".ts": "TypeScript",
        ".tsx": "TypeScript (React)", ".jsx": "JavaScript (React)",
        ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin",
        ".cs": "C#", ".rb": "Ruby", ".php": "PHP", ".swift": "Swift",
        ".c": "C", ".cpp": "C++", ".vue": "Vue", ".svelte": "Svelte",
        ".dart": "Dart", ".scala": "Scala", ".ex": "Elixir",
        ".sh": "Shell", ".bash": "Shell",
    }
    stats = defaultdict(lambda: {"files": 0, "code_lines": 0})
    for f in files:
        lang = lang_map.get(f["ext"])
        if lang:
            stats[lang]["files"] += 1
            stats[lang]["code_lines"] += f["size"] // 35  # ~35 bytes/line estimate
    return dict(sorted(stats.items(), key=lambda x: x[1]["code_lines"], reverse=True))


# ---------------------------------------------------------------------------
# Phase 3: Code Structure Extraction (tree-sitter)
# ---------------------------------------------------------------------------

def extract_symbols(
    root: Path,
    files: list[dict],
    warnings: list[dict] | None = None,
    warning_keys: set[tuple[str, str, str]] | None = None,
) -> list[dict]:
    """Use tree-sitter to extract classes, functions, interfaces from source files."""
    if not HAS_TREESITTER:
        return []
    if warnings is None:
        warnings = []
    if warning_keys is None:
        warning_keys = set()

    symbols = []
    parsers_cache = {}

    for f in files:
        ts_lang = EXT_TO_TS_LANG.get(f["ext"])
        if not ts_lang or ts_lang not in TS_QUERIES:
            continue

        if ts_lang not in parsers_cache:
            try:
                parsers_cache[ts_lang] = {
                    "parser": get_parser(ts_lang),
                    "language": get_language(ts_lang),
                }
            except Exception as e:
                add_warning(
                    warnings,
                    warning_keys,
                    "symbols",
                    f"Tree-sitter parser init failed for {ts_lang}: {e}",
                )
                parsers_cache[ts_lang] = None
                continue

        cached = parsers_cache[ts_lang]
        if cached is None:
            continue

        try:
            with open(f["full_path"], "rb") as fh:
                source = fh.read()
            if len(source) > 500_000:  # Skip very large generated files
                continue
            tree = cached["parser"].parse(source)
        except Exception as e:
            add_warning(
                warnings,
                warning_keys,
                "symbols",
                f"Failed to parse source file: {e}",
                f["path"],
            )
            continue

        query_src = TS_QUERIES[ts_lang]
        try:
            if HAS_QUERY_CURSOR:
                # tree-sitter 0.25.x: Query() + QueryCursor()
                q = Query(cached["language"], query_src)
                cursor = QueryCursor(q)
                captures = cursor.captures(tree.root_node)
                # Returns dict {capture_name: [nodes]}
                for capture_name, nodes in captures.items():
                    for node in nodes:
                        _collect_symbol(symbols, f["path"], capture_name, node, source)
            else:
                # Older tree-sitter: Language.query().captures(node)
                query = cached["language"].query(query_src)
                captures = query.captures(tree.root_node)
                if isinstance(captures, dict):
                    for capture_name, nodes in captures.items():
                        for node in nodes:
                            _collect_symbol(symbols, f["path"], capture_name, node, source)
                else:
                    for node, capture_name in captures:
                        _collect_symbol(symbols, f["path"], capture_name, node, source)
        except Exception as e:
            add_warning(
                warnings,
                warning_keys,
                "symbols",
                f"Tree-sitter query failed: {e}",
                f["path"],
            )
            continue

    return symbols


def _collect_symbol(symbols, file_path, capture_name, node, source):
    """Extract a named symbol from a tree-sitter capture."""
    if not capture_name.endswith("_name"):
        return
    kind = capture_name.replace("_name", "")
    name = source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
    line = node.start_point[0] + 1
    symbols.append({"name": name, "kind": kind, "file": file_path, "line": line})


# ---------------------------------------------------------------------------
# Phase 4: Importance Ranking (reference graph + PageRank)
# ---------------------------------------------------------------------------

def rank_symbols(
    symbols: list[dict],
    files: list[dict],
    root: Path,
    warnings: list[dict] | None = None,
    warning_keys: set[tuple[str, str, str]] | None = None,
) -> list[dict]:
    """Build a cross-file reference graph and rank entities by PageRank."""
    if not HAS_NETWORKX or not symbols:
        return []
    if warnings is None:
        warnings = []
    if warning_keys is None:
        warning_keys = set()

    G = nx.DiGraph()

    # Index: symbol name → [node keys]
    symbol_index = defaultdict(list)
    for sym in symbols:
        key = f"{sym['file']}::{sym['name']}"
        G.add_node(key, **sym)
        symbol_index[sym["name"]].append(key)

    # Scan files for cross-file references to known symbols
    for f in files:
        if f["ext"] not in EXT_TO_TS_LANG or f["size"] > 500_000:
            continue
        try:
            with open(f["full_path"], "r", encoding="utf-8", errors="ignore") as fh:
                content = fh.read()
        except Exception as e:
            add_warning(
                warnings,
                warning_keys,
                "ranking",
                f"Failed to read file for reference graph: {e}",
                f["path"],
            )
            continue

        file_prefix = f["path"] + "::"
        for sym_name, definitions in symbol_index.items():
            if len(sym_name) < 3:
                continue
            count = len(re.findall(r"\b" + re.escape(sym_name) + r"\b", content))
            if count > 1:
                for def_key in definitions:
                    if not def_key.startswith(file_prefix):
                        G.add_edge(f["path"], def_key, weight=count)

    try:
        ranks = nx.pagerank(G, weight="weight")
    except Exception as e:
        add_warning(
            warnings,
            warning_keys,
            "ranking",
            f"PageRank failed: {e}",
        )
        return []

    ranked = []
    for sym in symbols:
        key = f"{sym['file']}::{sym['name']}"
        ranked.append({**sym, "rank": round(ranks.get(key, 0.0), 6)})

    ranked.sort(key=lambda x: x["rank"], reverse=True)
    return ranked


# ---------------------------------------------------------------------------
# Phase 5: Git Insights (hotspots, contributors, code age)
# ---------------------------------------------------------------------------

def git_insights(
    root: Path,
    warnings: list[dict] | None = None,
    warning_keys: set[tuple[str, str, str]] | None = None,
) -> dict:
    """Analyze git history for hotspots and contributor mapping."""
    if not (root / ".git").is_dir():
        return {"available": False, "reason": "Not a git repository"}
    if warnings is None:
        warnings = []
    if warning_keys is None:
        warning_keys = set()

    insights = {"available": True}

    # Hotspots: most-changed files in last 6 months
    try:
        result = subprocess.run(
            ["git", "log", "--since=6 months ago", "--name-only",
             "--pretty=format:", "--diff-filter=ACMR"],
            capture_output=True, text=True, cwd=root, timeout=30
        )
        if result.returncode == 0:
            file_counts = Counter(
                line.strip() for line in result.stdout.splitlines() if line.strip()
            )
            insights["hotspots"] = [
                {"file": f, "changes": c}
                for f, c in file_counts.most_common(25)
            ]
    except Exception as e:
        add_warning(warnings, warning_keys, "git", f"Hotspots query failed: {e}")

    # Top contributors
    try:
        result = subprocess.run(
            ["git", "shortlog", "-sn", "--all", "--no-merges"],
            capture_output=True, text=True, cwd=root, timeout=30
        )
        if result.returncode == 0:
            contributors = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if line:
                    parts = line.split("\t", 1)
                    if len(parts) == 2:
                        contributors.append({
                            "name": parts[1].strip(),
                            "commits": int(parts[0].strip()),
                        })
            insights["top_contributors"] = contributors[:15]
    except Exception as e:
        add_warning(warnings, warning_keys, "git", f"Top contributors query failed: {e}")

    # Ownership: top contributor per top-level directory
    try:
        result = subprocess.run(
            ["git", "log", "--name-only", "--pretty=format:%aN", "--no-merges",
             "--since=12 months ago"],
            capture_output=True, text=True, cwd=root, timeout=30
        )
        if result.returncode == 0:
            dir_authors = defaultdict(Counter)
            current_author = None
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line:
                    current_author = None
                    continue
                if current_author is None:
                    current_author = line
                else:
                    top_dir = line.split("/")[0] if "/" in line else "(root)"
                    dir_authors[top_dir][current_author] += 1

            insights["ownership"] = {
                d: authors.most_common(3)
                for d, authors in sorted(dir_authors.items())
                if not d.startswith(".")
            }
    except Exception as e:
        add_warning(warnings, warning_keys, "git", f"Ownership query failed: {e}")

    # Recent activity
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "--since=30 days ago", "HEAD"],
            capture_output=True, text=True, cwd=root, timeout=10
        )
        if result.returncode == 0:
            insights["commits_last_30_days"] = int(result.stdout.strip())
    except Exception as e:
        add_warning(warnings, warning_keys, "git", f"Recent activity query failed: {e}")

    return insights


# ---------------------------------------------------------------------------
# Phase 6: Manifest Parsing (stdlib tomllib/json — proper parsers only)
# ---------------------------------------------------------------------------

def parse_manifests(root: Path) -> dict:
    """Parse dependency manifests using real parsers, never regex for structured data."""
    manifests = {}

    # package.json
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            with open(pkg_json) as f:
                pkg = json.load(f)
            manifests["npm"] = {
                "name": pkg.get("name", ""),
                "version": pkg.get("version", ""),
                "dependencies": list(pkg.get("dependencies", {}).keys()),
                "devDependencies": list(pkg.get("devDependencies", {}).keys()),
                "scripts": pkg.get("scripts", {}),
                "engines": pkg.get("engines", {}),
            }
        except Exception as e:
            manifests["npm"] = {"error": str(e)}

    # pyproject.toml
    pyproject = root / "pyproject.toml"
    if pyproject.exists():
        if HAS_TOMLLIB:
            try:
                with open(pyproject, "rb") as f:
                    data = tomllib.load(f)
                project = data.get("project", {})
                manifests["python"] = {
                    "name": project.get("name", ""),
                    "version": project.get("version", ""),
                    "python_requires": project.get("requires-python", ""),
                    "dependencies": project.get("dependencies", []),
                    "optional_dependencies": list(
                        project.get("optional-dependencies", {}).keys()
                    ),
                    "build_system": data.get("build-system", {}).get("build-backend", ""),
                    "tools": list(data.get("tool", {}).keys()),
                }
            except Exception as e:
                manifests["python"] = {"error": str(e)}
        else:
            manifests["python"] = {
                "error": "tomllib unavailable — upgrade to Python 3.11+ or pip install tomli",
            }

    # go.mod (line-oriented, so simple parsing is appropriate here)
    go_mod = root / "go.mod"
    if go_mod.exists():
        try:
            with open(go_mod) as f:
                content = f.read()
            module_match = re.search(r"^module\s+(\S+)", content, re.MULTILINE)
            go_match = re.search(r"^go\s+(\S+)", content, re.MULTILINE)
            require_block = re.findall(r"^\s+(\S+)\s+v(\S+)", content, re.MULTILINE)
            manifests["go"] = {
                "module": module_match.group(1) if module_match else "",
                "go_version": go_match.group(1) if go_match else "",
                "dependencies": [
                    {"name": n, "version": v} for n, v in require_block
                ],
            }
        except Exception as e:
            manifests["go"] = {"error": str(e)}

    # Cargo.toml
    cargo = root / "Cargo.toml"
    if cargo.exists():
        if HAS_TOMLLIB:
            try:
                with open(cargo, "rb") as f:
                    data = tomllib.load(f)
                package = data.get("package", {})
                manifests["cargo"] = {
                    "name": package.get("name", ""),
                    "version": package.get("version", ""),
                    "edition": package.get("edition", ""),
                    "dependencies": list(data.get("dependencies", {}).keys()),
                    "dev_dependencies": list(data.get("dev-dependencies", {}).keys()),
                    "workspace_members": data.get("workspace", {}).get("members", []),
                }
            except Exception as e:
                manifests["cargo"] = {"error": str(e)}

    # .csproj (XML — stdlib ElementTree)
    for csproj in root.glob("**/*.csproj"):
        rel = str(csproj.relative_to(root))
        if len(Path(rel).parts) > 3:
            continue
        try:
            import xml.etree.ElementTree as ET
            tree_xml = ET.parse(csproj)
            target = tree_xml.find("./PropertyGroup/TargetFramework")
            packages = [
                ref.get("Include", "") for ref in tree_xml.findall(".//PackageReference")
            ]
            manifests.setdefault("dotnet", {})[rel] = {
                "target_framework": target.text if target is not None else "",
                "packages": packages,
            }
        except Exception:
            continue

    return manifests


# ---------------------------------------------------------------------------
# Framework detection (validated against manifests, not just filenames)
# ---------------------------------------------------------------------------

def detect_frameworks(root: Path, files: list[dict], manifests: dict) -> list[dict]:
    """Detect frameworks by cross-referencing config files AND dependency manifests."""
    detected = []
    file_names = {Path(f["path"]).name for f in files}
    file_paths = {f["path"] for f in files}

    npm_deps = set()
    if "npm" in manifests and isinstance(manifests["npm"].get("dependencies"), list):
        npm_deps = set(manifests["npm"]["dependencies"])
        npm_deps.update(manifests["npm"].get("devDependencies", []))

    py_deps = set()
    if "python" in manifests and isinstance(manifests["python"].get("dependencies"), list):
        for dep in manifests["python"]["dependencies"]:
            py_deps.add(re.split(r"[<>=~!\[]", dep)[0].strip().lower())

    rules = [
        # JS/TS — validated against package.json dependencies
        (lambda: "next" in npm_deps, "Next.js", "frontend"),
        (lambda: "nuxt" in npm_deps, "Nuxt.js", "frontend"),
        (lambda: "svelte" in npm_deps or "@sveltejs/kit" in npm_deps, "SvelteKit", "frontend"),
        (lambda: "react" in npm_deps, "React", "frontend"),
        (lambda: "vue" in npm_deps, "Vue.js", "frontend"),
        (lambda: "@angular/core" in npm_deps, "Angular", "frontend"),
        (lambda: "@nestjs/core" in npm_deps, "NestJS", "backend"),
        (lambda: "express" in npm_deps, "Express", "backend"),
        (lambda: "fastify" in npm_deps, "Fastify", "backend"),
        (lambda: "prisma" in npm_deps or "@prisma/client" in npm_deps, "Prisma", "orm"),
        (lambda: "drizzle-orm" in npm_deps, "Drizzle", "orm"),
        (lambda: "vitest" in npm_deps, "Vitest", "testing"),
        (lambda: "jest" in npm_deps, "Jest", "testing"),
        (lambda: "@playwright/test" in npm_deps, "Playwright", "testing"),
        (lambda: "tailwindcss" in npm_deps, "Tailwind CSS", "styling"),
        # Python — validated against pyproject.toml dependencies
        (lambda: "django" in py_deps, "Django", "backend"),
        (lambda: "fastapi" in py_deps, "FastAPI", "backend"),
        (lambda: "flask" in py_deps, "Flask", "backend"),
        (lambda: "celery" in py_deps, "Celery", "task-queue"),
        (lambda: "sqlalchemy" in py_deps, "SQLAlchemy", "orm"),
        (lambda: "pytest" in py_deps, "pytest", "testing"),
        # Infrastructure — file-based (appropriate here, no manifest to check)
        (lambda: "nx.json" in file_names, "Nx", "monorepo"),
        (lambda: "turbo.json" in file_names, "Turborepo", "monorepo"),
        (lambda: "lerna.json" in file_names, "Lerna", "monorepo"),
        (lambda: "pnpm-workspace.yaml" in file_names, "pnpm workspaces", "monorepo"),
        (lambda: "Dockerfile" in file_names, "Docker", "infra"),
        (lambda: "docker-compose.yml" in file_names or "docker-compose.yaml" in file_names, "Docker Compose", "infra"),
        (lambda: any(p.startswith(".github/workflows/") for p in file_paths), "GitHub Actions", "ci"),
        (lambda: "Jenkinsfile" in file_names, "Jenkins", "ci"),
        (lambda: ".gitlab-ci.yml" in file_names, "GitLab CI", "ci"),
    ]

    for condition, name, category in rules:
        try:
            if condition():
                detected.append({"name": name, "category": category})
        except Exception:
            continue

    return detected


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def analyze(root: Path, max_depth: int = 4) -> dict:
    """Run all analysis phases and assemble the report."""
    warnings: list[dict] = []
    warning_keys: set[tuple[str, str, str]] = set()
    report = {
        "repository": str(root),
        "name": root.name,
        "analyzer_version": "2.0",
        "capabilities": {
            "pathspec (.gitignore)": HAS_PATHSPEC,
            "tree_sitter (AST)": HAS_TREESITTER,
            "networkx (PageRank)": HAS_NETWORKX,
            "tomllib (TOML)": HAS_TOMLLIB,
            "tokei (LOC stats)": shutil.which("tokei") is not None,
            "scc (LOC stats)": shutil.which("scc") is not None,
        },
    }

    # Phase 1: File Discovery
    print("  [1/7] File discovery...", file=sys.stderr)
    files = discover_files(root, max_depth)
    report["file_count"] = len(files)
    report["file_tree"] = [f["path"] for f in files]

    # Phase 2: Language Statistics
    print("  [2/7] Language statistics...", file=sys.stderr)
    cli_stats = language_stats_via_cli(root, warnings, warning_keys)
    if cli_stats:
        report["languages"] = cli_stats
        report["languages_source"] = "tokei" if shutil.which("tokei") else "scc"
    else:
        report["languages"] = language_stats_fallback(files)
        report["languages_source"] = "fallback (install tokei or scc for accurate stats)"

    # Phase 3: Manifest Parsing
    print("  [3/7] Manifest parsing...", file=sys.stderr)
    report["manifests"] = parse_manifests(root)

    # Phase 4: Framework Detection
    print("  [4/7] Framework detection...", file=sys.stderr)
    report["frameworks"] = detect_frameworks(root, files, report["manifests"])

    # Phase 5: Code Structure Extraction
    if HAS_TREESITTER:
        print("  [5/7] Code structure (tree-sitter)...", file=sys.stderr)
        symbols = extract_symbols(root, files, warnings, warning_keys)
        report["symbols"] = {
            "total": len(symbols),
            "by_kind": dict(Counter(s["kind"] for s in symbols)),
            "items": symbols[:500],
        }
    else:
        print("  [5/7] Code structure — SKIPPED (no tree-sitter)", file=sys.stderr)
        report["symbols"] = {
            "skipped": True,
            "reason": "pip install tree-sitter-language-pack",
        }
        symbols = []

    # Phase 6: Importance Ranking
    if HAS_NETWORKX and symbols:
        print("  [6/7] Importance ranking (PageRank)...", file=sys.stderr)
        ranked = rank_symbols(symbols, files, root, warnings, warning_keys)
        report["key_entities"] = ranked[:50]
    else:
        reason = "pip install networkx" if not HAS_NETWORKX else "No symbols to rank"
        print(f"  [6/7] Importance ranking — SKIPPED ({reason})", file=sys.stderr)
        report["key_entities"] = {"skipped": True, "reason": reason}

    # Phase 7: Git Insights
    print("  [7/7] Git insights...", file=sys.stderr)
    report["git"] = git_insights(root, warnings, warning_keys)

    # Summary
    primary_lang = next(iter(report["languages"]), "Unknown")
    report["summary"] = {
        "total_files": len(files),
        "primary_language": primary_lang,
        "framework_count": len(report["frameworks"]),
        "symbol_count": report["symbols"].get("total", 0),
        "is_git_repo": report["git"].get("available", False),
        "capabilities_active": [k for k, v in report["capabilities"].items() if v],
        "capabilities_missing": [k for k, v in report["capabilities"].items() if not v],
    }
    report["warnings"] = warnings

    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Codebase Analyzer v2 — Orchestrator for onboarding documentation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Dependencies (all optional, graceful degradation):
  pip install tree-sitter-language-pack   # AST code structure extraction
  pip install pathspec                    # .gitignore-aware file traversal
  pip install networkx                    # PageRank importance ranking
  brew install tokei                      # Accurate language statistics
        """,
    )
    parser.add_argument("repo_path", help="Path to the repository root")
    parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    parser.add_argument("--max-depth", type=int, default=4, help="Max traversal depth")
    args = parser.parse_args()

    root = Path(args.repo_path).resolve()
    if not root.is_dir():
        print(f"Error: {root} is not a directory", file=sys.stderr)
        sys.exit(1)

    print(f"Analyzing {root}...", file=sys.stderr)
    report = analyze(root, args.max_depth)
    print("Done.", file=sys.stderr)

    output = json.dumps(report, indent=2, default=str)

    if args.output:
        with open(args.output, "w") as f:
            f.write(output)
        print(f"Report: {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
