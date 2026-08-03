import json
import sys
from pathlib import Path

import pathspec

EXT_LANGUAGE_MAP = {
    ".py": "python",
    ".go": "go",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".rs": "rust",
    ".java": "java",
    ".c": "c",
    ".cpp": "cpp",
    ".rb": "ruby",
}

ALWAYS_SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "vectordb"}


def load_gitignore_spec(repo_path: Path):
    gitignore = repo_path / ".gitignore"
    lines = gitignore.read_text().splitlines() if gitignore.exists() else []
    return pathspec.PathSpec.from_lines("gitwildmatch", lines)


def walk_repo(repo_path: Path):
    spec = load_gitignore_spec(repo_path)
    files = []
    lang_counts: dict[str, int] = {}
    for path in repo_path.rglob("*"):
        if path.is_dir():
            continue
        if any(part in ALWAYS_SKIP_DIRS for part in path.parts):
            continue
        rel = path.relative_to(repo_path)
        if spec.match_file(str(rel)):
            continue
        ext = path.suffix
        language = EXT_LANGUAGE_MAP.get(ext, "unknown")
        try:
            size = path.stat().st_size
        except OSError:
            continue
        files.append({
            "path": str(rel),
            "ext": ext,
            "language": language,
            "size_bytes": size,
        })
        lang_counts[language] = lang_counts.get(language, 0) + 1
    return {
        "repo_path": str(repo_path),
        "file_count": len(files),
        "language_breakdown": lang_counts,
        "files": files,
    }


def write_inventory(repo_path: Path):
    inventory = walk_repo(repo_path)
    out_dir = Path(__file__).resolve().parent.parent / "data" / "logs"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{repo_path.name}_files.json"
    out_file.write_text(json.dumps(inventory, indent=2))
    return out_file


def main():
    if len(sys.argv) != 2:
        print("ISSUELOOP:: usage: python -m issueloop.folder_reader <path-to-repo>")
        sys.exit(1)
    repo_path = Path(sys.argv[1]).resolve()
    if not repo_path.is_dir():
        print(f"ISSUELOOP:: There is no directory: {repo_path}")
        sys.exit(1)
    out_file = write_inventory(repo_path)
    inventory = json.loads(out_file.read_text())

    print(f"ISSUELOOP:: scanned {inventory['file_count']} files in {repo_path}")
    print(f"ISSUELOOP:: language breakdown: {inventory['language_breakdown']}")
    print(f"ISSUELOOP:: written: {out_file}")


if __name__ == "__main__":
    main()