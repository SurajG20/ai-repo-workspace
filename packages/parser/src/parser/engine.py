from __future__ import annotations

import ctypes
import os
from pathlib import Path

import structlog

from .models import Language
from .registry import Language as LangModel, detect_language

logger = structlog.get_logger(__name__)

try:
    from tree_sitter import Language, Parser
    HAS_TREE_SITTER = True
except ImportError:
    HAS_TREE_SITTER = False


class TreeSitterParser:
    def __init__(self, grammars_dir: str | None = None):
        if not HAS_TREE_SITTER:
            raise RuntimeError("tree-sitter is not installed. pip install tree-sitter")

        if grammars_dir is None:
            grammars_dir = os.environ.get(
                "GRAMMARS_DIR",
                str(Path(__file__).parent.parent.parent / "grammars"),
            )
        self._grammars_dir = Path(grammars_dir)
        self._loaded: dict[str, Language] = {}

    def _load_grammar(self, lang: Language) -> Language:
        if lang.name in self._loaded:
            return self._loaded[lang.name]

        so_path = self._grammars_dir / lang.grammar_file
        if not so_path.exists():
            raise FileNotFoundError(
                f"Grammar not found: {so_path}. Run setup_grammars.py first."
            )

        ts_lang = self._load_shared_language(str(so_path), lang.tree_sitter_name)
        self._loaded[lang.name] = ts_lang
        logger.info("grammar_loaded", language=lang.name, path=str(so_path))
        return ts_lang

    def _load_shared_language(self, so_path: str, symbol: str) -> Language:
        lib = ctypes.CDLL(so_path)
        getter = getattr(lib, f"tree_sitter_{symbol}")
        getter.restype = ctypes.c_void_p
        return Language(getter())

    def parse_file(self, file_path: str, source: bytes) -> "tuple[object, LangModel] | None":
        lang_model = detect_language(file_path)
        if lang_model is None:
            return None

        ts_lang = self._load_grammar(lang_model)
        parser = Parser(ts_lang)
        tree = parser.parse(source)
        return tree, lang_model

    def parse_many(
        self, files: list[tuple[str, bytes]]
    ) -> list[tuple[str, object, LangModel]]:
        results: list[tuple[str, object, LangModel]] = []
        for file_path, source in files:
            result = self.parse_file(file_path, source)
            if result is not None:
                tree, lang_model = result
                results.append((file_path, tree, lang_model))
        return results
