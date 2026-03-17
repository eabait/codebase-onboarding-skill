#!/usr/bin/env python3
"""
parse_gemini.py — Split delimited gemini/LLM response into wiki files.

The gemini harness asks the model to output each wiki file wrapped in markers:

    ---FILE: 00-index.md---
    (markdown content)
    ---FILE: 01-overview.md---
    (markdown content)
    ...

This script parses that format and writes each block to a separate .md file
in the target directory. It also handles code-fence wrapping around the markers
in case the model wrapped the whole output in ```markdown ... ```.

Usage:
    python3 parse_gemini_output.py <raw_response.txt> <output_dir/>
"""

import re
import sys
from pathlib import Path


FILE_MARKER = re.compile(r'^---FILE:\s*(.+?)\s*---\s*$', re.MULTILINE)
# Also handle if model writes it inside a code block
FENCE_STRIP = re.compile(r'^```(?:markdown|md)?\s*\n?', re.MULTILINE)
FENCE_END = re.compile(r'\n?```\s*$', re.MULTILINE)


def strip_code_fences(text: str) -> str:
    """Remove outer ```markdown ... ``` fences if present."""
    text = text.strip()
    if text.startswith("```"):
        # Remove first fence line
        newline = text.find('\n')
        if newline != -1:
            text = text[newline + 1:]
        # Remove last fence
        if text.rstrip().endswith("```"):
            text = text.rstrip()
            text = text[: text.rfind("```")].rstrip()
    return text


def parse_files(raw: str) -> dict[str, str]:
    """Return {filename: content} dict extracted from the raw LLM response."""
    # First, try to strip any outer markdown code fence
    cleaned = strip_code_fences(raw)

    markers = list(FILE_MARKER.finditer(cleaned))
    if not markers:
        # Fallback: try the original raw text
        markers = list(FILE_MARKER.finditer(raw))
        if not markers:
            return {}
        cleaned = raw

    files: dict[str, str] = {}
    for i, match in enumerate(markers):
        filename = match.group(1).strip()
        start = match.end()
        end = markers[i + 1].start() if i + 1 < len(markers) else len(cleaned)
        content = cleaned[start:end].strip()
        files[filename] = content

    return files


def main() -> None:
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <raw_response.txt> <output_dir/>")
        sys.exit(1)

    raw_path = Path(sys.argv[1])
    out_dir = Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)

    raw = raw_path.read_text(encoding="utf-8", errors="replace")
    files = parse_files(raw)

    if not files:
        print("ERROR: No ---FILE: markers found in the response.")
        print("Check the raw response at:", raw_path)
        print("\nFirst 500 chars of response:")
        print(raw[:500])
        sys.exit(1)

    written = []
    for filename, content in files.items():
        # Sanitize filename
        safe_name = re.sub(r'[^\w\-.]', '_', filename)
        if not safe_name.endswith('.md'):
            safe_name += '.md'
        dest = out_dir / safe_name
        dest.write_text(content, encoding="utf-8")
        written.append(safe_name)
        print(f"  ✓ {safe_name}  ({len(content):,} chars)")

    print(f"\n{len(written)} files written to {out_dir}")

    # Warn if fewer than 8 files
    if len(written) < 8:
        print(f"\n⚠️  Only {len(written)} files found — expected ≥8.")
        print("   The model may have truncated its response or ignored the format.")
        print("   Try re-running with a shorter prompt or splitting into multiple calls.")


if __name__ == "__main__":
    main()
