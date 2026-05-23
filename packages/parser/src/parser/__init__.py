from __future__ import annotations

from .engine import TreeSitterParser
from .models import ParsedSymbol, SymbolRelationship
from .registry import LANGUAGES, detect_language
from .resolver import ModulePathResolver
from .extractors import (
    TypeScriptExtractor,
    PythonExtractor,
    GoExtractor,
    RustExtractor,
    JavaExtractor,
)
from .dependencies import (
    TypeScriptDependencyExtractor,
    PythonDependencyExtractor,
    GoDependencyExtractor,
    RustDependencyExtractor,
    JavaDependencyExtractor,
)

_EXTRACTORS = {
    "typescript": TypeScriptExtractor,
    "tsx": TypeScriptExtractor,
    "javascript": TypeScriptExtractor,
    "python": PythonExtractor,
    "go": GoExtractor,
    "rust": RustExtractor,
    "java": JavaExtractor,
}

_DEPENDENCIES = {
    "typescript": TypeScriptDependencyExtractor,
    "tsx": TypeScriptDependencyExtractor,
    "javascript": TypeScriptDependencyExtractor,
    "python": PythonDependencyExtractor,
    "go": GoDependencyExtractor,
    "rust": RustDependencyExtractor,
    "java": JavaDependencyExtractor,
}


def get_extractor(language_name: str):
    cls = _EXTRACTORS.get(language_name)
    if cls is None:
        raise ValueError(f"No extractor for language: {language_name}")
    lang = LANGUAGES.get(language_name)
    return cls(lang)


def get_dependency_extractor(language_name: str):
    cls = _DEPENDENCIES.get(language_name)
    if cls is None:
        raise ValueError(f"No dependency extractor for language: {language_name}")
    lang = LANGUAGES.get(language_name)
    return cls(lang)


__all__ = [
    "TreeSitterParser",
    "ParsedSymbol",
    "SymbolRelationship",
    "LANGUAGES",
    "detect_language",
    "ModulePathResolver",
    "get_extractor",
    "get_dependency_extractor",
]
