"""Setup script: downloads and compiles tree-sitter grammars."""

import subprocess
from pathlib import Path

GRAMMARS_DIR = Path(__file__).parent / "grammars"

LANGUAGES = {
    "python": {
        "repo": "https://github.com/tree-sitter/tree-sitter-python.git",
        "tag": "v0.23.6",
        "dirs": ["src"],
    },
    "typescript": {
        "repo": "https://github.com/tree-sitter/tree-sitter-typescript.git",
        "tag": "v0.23.2",
        "dirs": ["tsx/src", "typescript/src"],
    },
    "javascript": {
        "repo": "https://github.com/tree-sitter/tree-sitter-javascript.git",
        "tag": "v0.23.1",
        "dirs": ["src"],
    },
    "go": {
        "repo": "https://github.com/tree-sitter/tree-sitter-go.git",
        "tag": "v0.23.4",
        "dirs": ["src"],
    },
    "rust": {
        "repo": "https://github.com/tree-sitter/tree-sitter-rust.git",
        "tag": "v0.23.2",
        "dirs": ["src"],
    },
    "java": {
        "repo": "https://github.com/tree-sitter/tree-sitter-java.git",
        "tag": "v0.23.5",
        "dirs": ["src"],
    },
    "c": {
        "repo": "https://github.com/tree-sitter/tree-sitter-c.git",
        "tag": "v0.23.4",
        "dirs": ["src"],
    },
    "cpp": {
        "repo": "https://github.com/tree-sitter/tree-sitter-cpp.git",
        "tag": "v0.23.4",
        "dirs": ["src"],
    },
}


def run(cmd: list[str], cwd: Path | None = None) -> None:
    print(f"  $ {' '.join(cmd)}")
    subprocess.run(cmd, check=True, cwd=cwd)


def setup() -> None:
    GRAMMARS_DIR.mkdir(exist_ok=True)

    for name, config in LANGUAGES.items():
        repo_dir = GRAMMARS_DIR / name
        print(f"\n=== {name} ===")

        if repo_dir.exists():
            print("  Already cloned, skipping")
        else:
            run(["git", "clone", "--depth=1", "--branch", config["tag"], config["repo"], str(repo_dir)])

        for src_dir in config["dirs"]:
            src_path = repo_dir / src_dir
            grammar_path = src_path / "grammar.json"
            if not grammar_path.exists():
                print(f"  No grammar.json in {src_dir}, skipping")
                continue

            out_name = name
            if src_dir.startswith("tsx"):
                out_name = "tsx"
            elif src_dir.startswith("typescript"):
                out_name = "typescript"

            out_path = GRAMMARS_DIR / f"{out_name}.so"
            if out_path.exists():
                print(f"  {out_name}.so already built, skipping")
                continue

            parser_c = src_path / "parser.c"
            if not parser_c.exists():
                run(["tree-sitter", "generate"], cwd=src_path)

            sources = [str(parser_c)]
            scanner_c = src_path / "scanner.c"
            if scanner_c.exists():
                sources.append(str(scanner_c))

            run(["gcc", "-shared", "-o", str(out_path), "-fPIC",
                 "-I", str(src_path), *sources])

    print("\n=== Done ===")
    for f in sorted(GRAMMARS_DIR.glob("*.so")):
        print(f"  {f.name}")


if __name__ == "__main__":
    setup()
