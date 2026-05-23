from __future__ import annotations

import os
from pathlib import Path

import structlog

logger = structlog.get_logger(__name__)

JS_EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".d.ts")
INDEX_FILES = tuple(f"/index{ext}" for ext in JS_EXTENSIONS)
PY_INDEX = "__init__.py"


class ModulePathResolver:
    """Resolves import statements to absolute file paths."""

    def __init__(self, repo_root: str, known_files: set[str]):
        self.repo_root = Path(repo_root).resolve()
        self._known_files = known_files
        self._file_set: set[str] = {str(Path(f)) for f in known_files}
        self._basename_map: dict[str, list[str]] = {}
        for f in self._file_set:
            bn = Path(f).name
            self._basename_map.setdefault(bn, []).append(f)

    def resolve(self, source_file: str, import_specifier: str, language: str) -> str | None:
        source_dir = str(Path(source_file).parent)

        if language in ("typescript", "tsx", "javascript"):
            return self._resolve_ts(source_dir, import_specifier)
        elif language == "python":
            return self._resolve_python(source_dir, import_specifier)
        elif language == "go":
            return self._resolve_go(import_specifier)
        elif language == "rust":
            return self._resolve_rust(import_specifier)
        elif language == "java":
            return self._resolve_java(import_specifier)
        return None

    def _resolve_ts(self, source_dir: str, specifier: str, max_depth: int = 10) -> str | None:
        base_dir = str(self.repo_root)

        if specifier.startswith("."):
            target = self._abs_path(source_dir, specifier)
            if not target.startswith(base_dir) or max_depth <= 0:
                return None

            for ext in JS_EXTENSIONS:
                candidate = target + ext
                if candidate in self._file_set:
                    return candidate

            for idx in INDEX_FILES:
                candidate = target + idx
                if candidate in self._file_set:
                    return candidate

            return None

        return self._resolve_node_modules(base_dir, source_dir, specifier, max_depth)

    def _resolve_node_modules(
        self, base_dir: str, source_dir: str, specifier: str, max_depth: int
    ) -> str | None:
        if specifier.startswith("@"):
            parts = specifier.split("/", 2)
            if len(parts) >= 2:
                scope = "/".join(parts[:2])
                subpath = parts[2] if len(parts) > 2 else "index"
            else:
                return None
        else:
            pkg = specifier.split("/", 1)
            scope = pkg[0]
            subpath = pkg[1] if len(pkg) > 1 else "index"

        search_dir = Path(source_dir)
        depth = 0
        while depth <= max_depth and str(search_dir.resolve()) >= base_dir:
            node_modules = search_dir / "node_modules" / scope
            if node_modules.exists():
                pkg_json = node_modules / "package.json"
                entry = "index.js"
                if pkg_json.exists():
                    try:
                        import json
                        with open(pkg_json) as f:
                            data = json.load(f)
                        entry = data.get("main", "index.js")
                        if "exports" in data and isinstance(data["exports"], dict):
                            for k in (".", "./index"):
                                if k in data["exports"]:
                                    entry = data["exports"][k]
                                    if isinstance(entry, str):
                                        break
                    except Exception:
                        pass

                candidate = str(node_modules / subpath)
                for ext in JS_EXTENSIONS:
                    if candidate + ext in self._file_set:
                        return candidate + ext
                for idx in INDEX_FILES:
                    if candidate + idx in self._file_set:
                        return candidate + idx
                resolved = str(node_modules / entry)
                for ext in JS_EXTENSIONS:
                    if resolved + ext in self._file_set:
                        return resolved + ext
                return None

            search_dir = search_dir.parent
            depth += 1

        return None

    def _resolve_python(self, source_dir: str, specifier: str) -> str | None:
        parts = specifier.lstrip(".").split(".")
        dot_count = len(specifier) - len(specifier.lstrip("."))

        if dot_count > 0:
            target_dir = Path(source_dir)
            for _ in range(dot_count - 1):
                target_dir = target_dir.parent
        else:
            target_dir = self.repo_root

        target = target_dir / "/".join(parts)
        candidate_py = str(target) + ".py"
        if candidate_py in self._file_set:
            return candidate_py
        candidate_pyi = str(target) + ".pyi"
        if candidate_pyi in self._file_set:
            return candidate_pyi
        candidate_init = str(target / "__init__.py")
        if candidate_init in self._file_set:
            return candidate_init
        return None

    def _resolve_go(self, specifier: str) -> str | None:
        parts = specifier.split("/")
        base = parts[-1]
        candidates = self._basename_map.get(base + ".go", [])
        if len(candidates) == 1:
            return candidates[0]
        for c in candidates:
            if all(p in str(Path(c).parent) for p in specifier.split("/")):
                return c
        return None

    def _resolve_rust(self, specifier: str) -> str | None:
        parts = specifier.split("::")
        for i in range(len(parts), 0, -1):
            search = parts[i - 1]
            candidates = self._basename_map.get(search + ".rs", [])
            if len(candidates) == 1:
                return candidates[0]
            for c in candidates:
                if all(p in str(Path(c)) for p in parts[:i]):
                    return c
        return None

    def _resolve_java(self, specifier: str) -> str | None:
        path = specifier.replace(".", "/") + ".java"
        if path in self._file_set:
            return path
        for f in self._file_set:
            if f.endswith("/" + path.split("/")[-1]):
                if path.replace("/", ".") in f.replace("/", "."):
                    return f
        return None

    @staticmethod
    def _abs_path(base: str, rel: str) -> str:
        return str((Path(base) / rel).resolve())
