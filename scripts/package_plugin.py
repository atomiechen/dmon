"""Build a skills-only plugin archive from the canonical repository files."""

from pathlib import Path
import hashlib
import json
import zipfile

try:
    import tomllib
except ImportError:
    import tomli as tomllib


def main():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "plugin.json").read_text())
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    if manifest["version"] != project["version"]:
        raise SystemExit("Plugin and CLI versions must match before packaging")
    files = [root / "plugin.json", root / "LICENSE"]
    files += sorted(p for p in (root / "skills").rglob("*") if p.is_file())
    for path in files:
        if path.is_symlink() or path.suffix not in (".md", ".yaml", ".json", ""):
            raise SystemExit(f"Unexpected plugin file: {path.relative_to(root)}")
    output = root / ".local" / "plugin-dist" / f"dmon-plugin-{manifest['version']}.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            info = zipfile.ZipInfo(
                path.relative_to(root).as_posix(), (2020, 1, 1, 0, 0, 0)
            )
            info.external_attr = 0o100644 << 16
            archive.writestr(
                info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED
            )
    print(output)
    print("SHA256", hashlib.sha256(output.read_bytes()).hexdigest())


if __name__ == "__main__":
    main()
