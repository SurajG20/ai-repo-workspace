# Tree-sitter for AST parsing

The parser must produce a deterministic symbol graph (functions, classes, methods, imports, calls) across many languages without per-language compiler toolchains. We chose tree-sitter grammars compiled to shared objects (`gcc -shared`) and loaded via ctypes, with one extractor module per language translating node types into the canonical `ParsedSymbol` contract.

## Considered Options

- **Language servers (LSP)**: rejected — requires running per-language servers, heavy orchestration, and inconsistent symbol models across languages.
- **Regex/line heuristics**: rejected — cannot distinguish declarations from definitions or resolve nesting; graph quality would be fiction.
- **ctypes-loaded `.so` grammars over py-tree-sitter language wheels**: chosen because grammar versions are pinned in `setup_grammars.py`, builds are reproducible in Docker, and no pip dependency churn.

## Consequences

- Adding a language = pin a grammar tag + write an extractor + register it in `LANGUAGES`; nothing else changes downstream.
- Grammar `.so` artifacts are build outputs, never committed; CI and Docker rebuild them from pinned tags.
- Extractors own export semantics (`derive_is_exported`) because "importable" means something different in Go (case), Python (underscore), Rust (`pub`), Java (`public`), and C/C++ (`static`).
