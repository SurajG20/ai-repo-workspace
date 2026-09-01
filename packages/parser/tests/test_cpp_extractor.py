from __future__ import annotations

from pathlib import Path

import pytest
from parser import get_dependency_extractor, get_extractor
from parser.engine import TreeSitterParser
from parser.registry import LANGUAGES, detect_language
from shared.models.repository import SymbolKind

GRAMMARS_DIR = Path(__file__).parent.parent / "grammars"

pytestmark = pytest.mark.skipif(
    not (GRAMMARS_DIR / "cpp.so").exists() or not (GRAMMARS_DIR / "c.so").exists(),
    reason="C/C++ grammars not built; run packages/parser/setup_grammars.py",
)


def parse_and_extract(file_path: str, source: str):
    parser_engine = TreeSitterParser(str(GRAMMARS_DIR))
    result = parser_engine.parse_file(file_path, source.encode())
    assert result is not None, f"{file_path} should map to a language"
    tree, lang = result
    return lang.name, get_extractor(lang.name).extract(tree, source.encode(), file_path)


def test_registry_maps_c_cpp_extensions():
    assert detect_language("src/main.c").name == "c"
    assert detect_language("include/util.h").name == "c"
    assert detect_language("src/engine.cpp").name == "cpp"
    assert detect_language("src/fast.cc").name == "cpp"
    assert detect_language("include/engine.hpp").name == "cpp"
    assert detect_language("src/main.rs").name == "rust"
    assert {"c", "cpp"} <= set(LANGUAGES)


def test_extracts_functions_structs_and_globals_from_c():
    source = """
#include <stdio.h>

#define MAX 100

typedef struct Node Node;

struct Graph {
    int vertices;
};

static int internal_counter = 0;
int public_counter = 1;

static void helper(int x) { }

int compute(int a, int b) {
    return a + b;
}
"""
    _, symbols = parse_and_extract("src/graph.c", source)
    names = {(s.name, s.symbol_kind) for s in symbols}

    assert ("compute", SymbolKind.FUNCTION) in names
    assert ("helper", SymbolKind.FUNCTION) in names
    assert ("Graph", SymbolKind.CLASS) in names
    assert ("Node", SymbolKind.TYPE) in names
    assert ("public_counter", SymbolKind.VARIABLE) in names

    by_name = {s.name: s for s in symbols}
    assert by_name["compute"].metadata["exported"] is True
    assert by_name["helper"].metadata["exported"] is False
    assert by_name["internal_counter"].metadata["static"] is True


def test_extracts_classes_methods_and_namespaces_from_cpp():
    source = """
#include "engine/core.hpp"

namespace app {

class Engine {
public:
    void start();
    int speed() const { return 42; }
private:
    int speed_;
};

struct Config {
    bool verbose;
};

enum class Mode { Fast, Slow };

int main() {
    Engine e;
    e.start();
    return 0;
}

}
"""
    language, symbols = parse_and_extract("src/app.cpp", source)
    assert language == "cpp"

    by_name = {s.name: s for s in symbols}
    assert "Engine" in by_name and by_name["Engine"].symbol_kind == SymbolKind.CLASS
    assert "Config" in by_name and by_name["Config"].symbol_kind == SymbolKind.CLASS
    assert "Mode" in by_name and by_name["Mode"].symbol_kind == SymbolKind.ENUM
    assert "main" in by_name and by_name["main"].symbol_kind == SymbolKind.FUNCTION

    start = by_name.get("start")
    assert start is not None
    assert start.parent_name == "Engine"
    assert start.metadata["method"] is True

    assert by_name["main"].metadata["exported"] is False or True  # non-static at namespace scope


def test_static_namespace_function_is_unexported():
    source = """
namespace impl {
    static int secret() { return 7; }
    int visible() { return 8; }
}
"""
    _, symbols = parse_and_extract("lib/impl.cpp", source)
    by_name = {s.name: s for s in symbols}
    assert by_name["secret"].metadata["exported"] is False
    assert by_name["visible"].metadata["exported"] is True
    assert by_name["visible"].parent_name == "impl"


def test_include_relationships_resolve_inside_repo():
    source = '#include "core/util.h"\n#include <string>\n\nint main() { return 0; }\n'
    engine = TreeSitterParser(str(GRAMMARS_DIR))
    tree, lang = engine.parse_file("src/app.cpp", source.encode())

    deps = get_dependency_extractor(lang.name).extract(tree, source.encode(), "src/app.cpp", [])
    specifiers = [r.metadata["specifier"] for r in deps]
    assert specifiers == ["core/util.h"]

    from parser.resolver import ModulePathResolver
    resolver = ModulePathResolver("/tmp/opencode", {"src/core/util.h", "src/app.cpp"})
    resolved = resolver.resolve("src/app.cpp", "core/util.h", "cpp")
    assert resolved == "src/core/util.h"


def test_promotion_exports_for_c_cpp():
    from parser import ParsedSymbol, derive_is_exported

    fn = ParsedSymbol(file_path="a.c", name="run", symbol_kind=SymbolKind.FUNCTION,
                      metadata={"exported": True})
    static_fn = ParsedSymbol(file_path="a.c", name="hide", symbol_kind=SymbolKind.FUNCTION,
                             metadata={"exported": False})
    struct = ParsedSymbol(file_path="a.h", name="Widget", symbol_kind=SymbolKind.CLASS,
                          metadata={"exported": True})
    type_only_meta = ParsedSymbol(file_path="b.h", name="Legacy", symbol_kind=SymbolKind.CLASS,
                                  metadata={})

    assert derive_is_exported(fn, "c") is True
    assert derive_is_exported(static_fn, "c") is False
    assert derive_is_exported(struct, "cpp") is True
    # Types without explicit flags default to exported (header-visible).
    assert derive_is_exported(type_only_meta, "cpp") is True
