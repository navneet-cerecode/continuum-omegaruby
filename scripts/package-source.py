"""Reviewable source archive; excludes credentials, runtimes, dependencies and logs."""

from pathlib import Path
import zipfile

root = Path(__file__).resolve().parents[1]
out = root / "CONTINUUM-OmegaRuby-source.zip"
excluded = {
    ".git",
    ".venv",
    ".runtime",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
}
with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if any(part in excluded for part in relative.parts):
            continue
        if path.name.startswith(".env") and path.name != ".env.example":
            continue
        if path.suffix in (".zip", ".log", ".pid", ".xml"):
            continue
        archive.write(path, relative.as_posix())
with zipfile.ZipFile(out) as archive:
    assert archive.testzip() is None
    assert ".env" not in archive.namelist()
    assert "README.md" in archive.namelist()
    print(
        f"Validated {len(archive.namelist())} files in {out.name} ({out.stat().st_size:,} bytes)."
    )
