from __future__ import annotations

from parser.resolver import ModulePathResolver


def make_resolver(known: set[str], root: str = "/repo") -> ModulePathResolver:
    return ModulePathResolver(root, known)


def test_ts_relative_import_resolves_repo_relative_paths():
    # Regression: the old implementation absolutized candidates against CWD
    # while the known-file set holds repo-relative paths, so every relative
    # TS/JS import failed to resolve.
    resolver = make_resolver({"src/util.ts", "src/app.ts"})
    assert resolver.resolve("src/app.ts", "./util", "typescript") == "src/util.ts"


def test_ts_relative_import_rejects_escape_outside_repo():
    resolver = make_resolver({"secrets.ts", "src/app.ts"})
    assert resolver.resolve("src/app.ts", "../../secrets", "typescript") is None


def test_include_resolves_relative_to_source_file():
    resolver = make_resolver({"src/core/util.h", "src/app.cpp"})
    assert resolver.resolve("src/app.cpp", "core/util.h", "cpp") == "src/core/util.h"


def test_include_falls_back_to_repo_root():
    resolver = make_resolver({"include/global.h", "src/main.cpp"})
    assert resolver.resolve("src/main.cpp", "include/global.h", "c") == "include/global.h"


def test_include_never_escapes_the_repository():
    resolver = make_resolver({"/etc/passwd"})
    assert resolver.resolve("src/app.cpp", "../../../etc/passwd", "cpp") is None


def test_unresolvable_specifier_returns_none():
    resolver = make_resolver({"src/app.ts"})
    assert resolver.resolve("src/app.ts", "./missing", "typescript") is None
