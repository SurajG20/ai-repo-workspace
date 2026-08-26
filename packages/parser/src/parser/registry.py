from __future__ import annotations

from pathlib import Path

from .models import Language

LANGUAGES: dict[str, Language] = {
    "typescript": Language(
        name="typescript",
        extensions=(".ts",),
        grammar_file="typescript.so",
        tree_sitter_name="typescript",
    ),
    "tsx": Language(
        name="tsx",
        extensions=(".tsx",),
        grammar_file="tsx.so",
        tree_sitter_name="tsx",
    ),
    "javascript": Language(
        name="javascript",
        extensions=(".js", ".mjs", ".cjs"),
        grammar_file="javascript.so",
        tree_sitter_name="javascript",
    ),
    "python": Language(
        name="python",
        extensions=(".py", ".pyi"),
        grammar_file="python.so",
        tree_sitter_name="python",
    ),
    "go": Language(
        name="go",
        extensions=(".go",),
        grammar_file="go.so",
        tree_sitter_name="go",
    ),
    "rust": Language(
        name="rust",
        extensions=(".rs",),
        grammar_file="rust.so",
        tree_sitter_name="rust",
    ),
    "java": Language(
        name="java",
        extensions=(".java",),
        grammar_file="java.so",
        tree_sitter_name="java",
    ),
    "c": Language(
        name="c",
        extensions=(".c", ".h"),
        grammar_file="c.so",
        tree_sitter_name="c",
    ),
    "cpp": Language(
        name="cpp",
        extensions=(".cpp", ".cc", ".cxx", ".hpp", ".hh", ".hxx"),
        grammar_file="cpp.so",
        tree_sitter_name="cpp",
    ),
}

EXTENSION_MAP: dict[str, Language] = {}
for lang in LANGUAGES.values():
    for ext in lang.extensions:
        EXTENSION_MAP[ext] = lang


def detect_language(file_path: str) -> Language | None:
    ext = Path(file_path).suffix.lower()
    mapping = {
        ".ts": "typescript",
        ".tsx": "tsx",
        ".js": "javascript",
        ".jsx": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".py": "python",
        ".pyi": "python",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".c": "c",
        ".h": "c",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".hpp": "cpp",
        ".hh": "cpp",
        ".hxx": "cpp",
    }
    name = mapping.get(ext)
    return LANGUAGES.get(name) if name else None
