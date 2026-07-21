#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
# Copyright (c) 2026 The feedpak authors
"""
feedpak reference validator.

Validates a feedpak package (directory `*.feedpak/` or zip `*.feedpak`) against the
feedpak format specification (spec/feedpak-v1.md) and the JSON Schemas in schemas/.

This is both a CI gate for this repository's examples and a minimal reference
implementation of how to read and check a feedpak. It deliberately uses only the
manifest as an index (never filename scanning) and treats unknown keys/files as
forward-compatible.

Usage:
    python tools/validate.py PACK [PACK ...]
    python tools/validate.py examples/minimal.feedpak

Exit status is 0 only when every package passes.

Requires: PyYAML, jsonschema.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
import zipfile
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    sys.exit("error: PyYAML is required (pip install pyyaml)")
try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    sys.exit("error: jsonschema is required (pip install jsonschema)")

REPO_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_DIR = REPO_ROOT / "schemas"

SUPPORTED_MAJOR = 1


def _semver_re() -> re.Pattern[str]:
    """Use the manifest schema as the single source of truth for the semver pattern, so the
    validator and the schema can never disagree (e.g. on rejecting `1.0.0-01`)."""
    with open(SCHEMA_DIR / "manifest.schema.json", encoding="utf-8") as fh:
        pattern = json.load(fh)["$defs"]["semver"]["pattern"]
    return re.compile(pattern)


SEMVER_RE = _semver_re()

# manifest pointer key -> schema file used to validate the pointed-at JSON.
# (Audio/image pointers validate as "exists + safe path" only.)
SIDE_FILE_SCHEMAS = {
    "lyrics": "lyrics.schema.json",
    "vocal_pitch": "vocal-pitch.schema.json",
    "song_timeline": "song-timeline.schema.json",
    "drum_tab": "drum-tab.schema.json",
    "vocal_pitch_contour": "vocal-pitch-contour.schema.json",
    "keys": "keys.schema.json",
    "harmony": "harmony.schema.json",
    "rigs": "rigs.schema.json",
}
NON_JSON_POINTERS = ("cover", "preview")

# Regex to match JSON string literals (preserved) and C-style comments (stripped).
# This is used by _parse_jsonc to handle .jsonc files.
_JSONC_STRIP_RE = re.compile(
    r'"(?:[^"\\]|\\.)*"|'   # string literal — keep as-is
    r'//.*|'                  # // line comment — strip
    r'/\*[\s\S]*?\*/',        # /* block comment */ — strip
)


def _parse_jsonc(text: str) -> object:
    """Parse a JSONC string, stripping C-style comments before JSON parsing.

    Handles ``//`` line comments and ``/* */`` block comments, respecting
    string boundaries so that comment-like text inside strings is preserved.
    Newlines inside block comments are kept, so a JSON parse error still points
    at roughly the right line in the original source.
    """
    def _strip(m: re.Match[str]) -> str:
        s = m.group(0)
        if s.startswith('"'):
            return s                      # string literal — keep verbatim
        if s.startswith("/*"):
            # A comment is whitespace: never concatenate the tokens around it
            # (e.g. 1/*c*/2 must not become 12). Keep embedded newlines for
            # error-line fidelity; otherwise collapse to a single space.
            return "\n" * s.count("\n") if "\n" in s else " "
        return ""                         # // line comment — the EOL newline remains

    return json.loads(_JSONC_STRIP_RE.sub(_strip, text))


def load_schema(name: str) -> Draft202012Validator:
    with open(SCHEMA_DIR / name, encoding="utf-8") as fh:
        return Draft202012Validator(json.load(fh))


def safe_relpath(p: str) -> bool:
    """Mirror the spec's path rule (§2.2): a POSIX relative path with no leading slash,
    no backslash, no drive letter / colon, and no '..' segment."""
    if not isinstance(p, str) or not p:
        return False
    if p.startswith("/") or "\\" in p or ":" in p:  # ':' rejects C:/foo, C:foo, and NTFS streams
        return False
    parts = p.split("/")
    return ".." not in parts and "" not in parts[:-1]


def within_root(root: Path, target: Path) -> bool:
    """True if `target`, with symlinks resolved, stays inside the package root.
    Rejects symlinks (a file or directory, including manifest.yaml itself) that point
    outside the pack — matching the spec's "reject paths that escape the package root" rule."""
    root_real = root.resolve()
    target_real = target.resolve()
    return root_real == target_real or root_real in target_real.parents


class Report:
    def __init__(self, label: str):
        self.label = label
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_json_file(root: Path, relpath: str, validator: Draft202012Validator,
                       rep: Report) -> None:
    target = root / relpath
    if not target.is_file():
        rep.err(f"missing file referenced by manifest: {relpath}")
        return
    is_jsonc = relpath.endswith(".jsonc")
    try:
        raw = target.read_text(encoding="utf-8")
        data = _parse_jsonc(raw) if is_jsonc else json.loads(raw)
    except Exception as exc:  # noqa: BLE001
        kind = "not valid JSON (after JSONC comment-stripping)" if is_jsonc else "not valid JSON"
        rep.err(f"{relpath}: {kind} ({exc})")
        return
    for e in sorted(validator.iter_errors(data), key=lambda e: list(e.path)):
        loc = "/".join(str(x) for x in e.path) or "<root>"
        rep.err(f"{relpath}: {loc}: {e.message}")


def check_pointer_exists(root: Path, relpath: str, key: str, rep: Report) -> bool:
    if not safe_relpath(relpath):
        rep.err(f"manifest '{key}' is not a safe relative path: {relpath!r}")
        return False
    # Resolve symlinks and confirm the real target stays inside the package root.
    # A safe-looking relpath can still escape via a symlinked directory/file
    # (e.g. stems/ -> /etc); the spec requires rejecting paths that escape the root.
    if not within_root(root, root / relpath):
        rep.err(f"manifest '{key}' escapes the package root (symlink?): {relpath}")
        return False
    if not (root / relpath).resolve().is_file():
        rep.err(f"missing file referenced by manifest '{key}': {relpath}")
        return False
    return True


def validate_dir(root: Path, rep: Report) -> None:
    manifest_path = root / "manifest.yaml"
    if not within_root(root, manifest_path):
        rep.err("manifest.yaml escapes the package root (symlink?)")
        return
    if not manifest_path.is_file():
        rep.err("no manifest.yaml at package root")
        return
    try:
        manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        rep.err(f"manifest.yaml: not valid YAML ({exc})")
        return
    if not isinstance(manifest, dict):
        rep.err("manifest.yaml: top level must be a mapping")
        return

    # 1. manifest schema
    manifest_validator = load_schema("manifest.schema.json")
    for e in sorted(manifest_validator.iter_errors(manifest), key=lambda e: list(e.path)):
        loc = "/".join(str(x) for x in e.path) or "<root>"
        rep.err(f"manifest.yaml: {loc}: {e.message}")

    # 2. feedpak_version semantics
    fv = manifest.get("feedpak_version", "1.0.0")
    if not isinstance(fv, str) or not SEMVER_RE.match(fv):
        rep.err(f"feedpak_version is not a valid semver string: {fv!r}")
    else:
        major = int(fv.split(".")[0])
        if major > SUPPORTED_MAJOR:
            rep.warn(
                f"feedpak_version {fv} has major {major} > supported {SUPPORTED_MAJOR}; "
                "this validator may not understand it"
            )

    # 3. arrangements: each entry's file + optional notation + optional drum_tab
    arr_validator = load_schema("arrangement.schema.json")
    notation_validator = load_schema("notation.schema.json")
    drum_tab_validator = load_schema(SIDE_FILE_SCHEMAS["drum_tab"])
    for i, arr in enumerate(manifest.get("arrangements", []) or []):
        if not isinstance(arr, dict):
            continue
        f = arr.get("file")
        if f is not None and check_pointer_exists(root, f, f"arrangements[{i}].file", rep):
            validate_json_file(root, f, arr_validator, rep)
        n = arr.get("notation")
        if n is not None and check_pointer_exists(root, n, f"arrangements[{i}].notation", rep):
            validate_json_file(root, n, notation_validator, rep)
        d = arr.get("drum_tab")
        if d is not None and check_pointer_exists(root, d, f"arrangements[{i}].drum_tab", rep):
            validate_json_file(root, d, drum_tab_validator, rep)

    # 4. stems: each file must exist
    for i, st in enumerate(manifest.get("stems", []) or []):
        if isinstance(st, dict) and "file" in st:
            check_pointer_exists(root, st["file"], f"stems[{i}].file", rep)

    # 5. JSON side-files with their own schema
    for key, schema_name in SIDE_FILE_SCHEMAS.items():
        rel = manifest.get(key)
        if rel is None:
            continue
        if check_pointer_exists(root, rel, key, rep):
            validate_json_file(root, rel, load_schema(schema_name), rep)

    # 6. non-JSON pointers: existence + safe path only
    for key in NON_JSON_POINTERS:
        rel = manifest.get(key)
        if rel is not None:
            check_pointer_exists(root, rel, key, rep)


def resolve_and_validate(pack: Path) -> Report:
    rep = Report(str(pack))
    if pack.is_dir():
        validate_dir(pack, rep)
    elif pack.is_file() and zipfile.is_zipfile(pack):
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(pack) as zf:
                # guard against zip-slip (incl. drive letters / colons, which can escape
                # the extraction root on Windows)
                for name in zf.namelist():
                    if (name.startswith("/") or ".." in Path(name).parts
                            or "\\" in name or ":" in name):
                        rep.err(f"unsafe path inside archive: {name}")
                if rep.ok:
                    zf.extractall(tmp)
                    validate_dir(Path(tmp), rep)
    else:
        rep.err("not a directory or a zip archive")
    return rep


def main(argv: list[str]) -> int:
    packs = argv[1:]
    if not packs:
        print(__doc__.strip())
        return 2
    failed = 0
    for arg in packs:
        rep = resolve_and_validate(Path(arg))
        for w in rep.warnings:
            print(f"  warning: {w}")
        if rep.ok:
            print(f"PASS  {rep.label}")
        else:
            failed += 1
            print(f"FAIL  {rep.label}")
            for e in rep.errors:
                print(f"  - {e}")
    print(f"\n{len(packs) - failed}/{len(packs)} package(s) valid")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
