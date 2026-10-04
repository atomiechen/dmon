"""Build a skills-only plugin archive from the canonical repository files."""

from pathlib import Path
import hashlib
import json
import re
import zipfile
import xml.etree.ElementTree as ET

try:
    import tomllib
except ImportError:
    import tomli as tomllib


def packaged_file(root, relative):
    """Read only explicit, contained regular files; never follow symlinks."""
    path = Path(relative)
    if path.is_absolute() or ".." in path.parts or "\\" in relative:
        raise ValueError(f"Invalid package path: {relative}")
    target = root / path
    if any(p.is_symlink() for p in (target, *target.parents)):
        raise ValueError(f"Symlink in package path: {relative}")
    if not target.is_file():
        raise ValueError(f"Missing package file: {relative}")
    return target.read_bytes()


def build(root):
    root = Path(root).resolve()
    manifest = json.loads((root / "plugin.json").read_text())
    project = tomllib.loads((root / "pyproject.toml").read_text())["project"]
    if manifest["version"] != project["version"]:
        raise SystemExit("Plugin and CLI versions must match before packaging")
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", manifest["name"]):
        raise ValueError("Plugin name must use lowercase letters, numbers, and hyphens")
    if not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+", manifest["version"]):
        raise ValueError("Expected a three-part release version")
    extension = manifest.get("extensions", {}).get("com.openai", {})
    interface = extension.get("interface", {})
    for key, limit in (
        ("displayName", 30),
        ("shortDescription", 30),
        ("longDescription", 4000),
        ("developerName", 80),
    ):
        value = interface.get(key)
        if not isinstance(value, str) or not value.strip() or len(value) > limit:
            raise ValueError(f"Invalid interface.{key} (1..{limit} characters)")
    if (
        not isinstance(interface.get("category"), str)
        or not interface["category"].strip()
    ):
        raise ValueError("A listing category is required")
    capabilities = interface.get("capabilities", [])
    if (
        not isinstance(capabilities, list)
        or len(capabilities) > 20
        or any(
            not isinstance(c, str) or not c.strip() or len(c) > 120
            for c in capabilities
        )
    ):
        raise ValueError("Invalid capability labels")
    prompts = interface.get("defaultPrompt", [])
    if isinstance(prompts, str):
        prompts = [prompts]
    if not isinstance(prompts, list) or len(prompts) > 3:
        raise ValueError("At most three defaultPrompt entries are allowed")
    if any(
        not isinstance(p, str) or not p.strip() or len(p) > 128 or "@" in p
        for p in prompts
    ):
        raise ValueError("Invalid starter prompt")
    if len(set(prompts)) != len(prompts):
        raise ValueError("Starter prompts must be distinct")
    files = [root / "LICENSE"]
    if not (root / "skills/dmon/SKILL.md").is_file():
        raise SystemExit("Missing skills/dmon/SKILL.md")
    files += [root / "skills/dmon/SKILL.md", root / "skills/dmon/agents/openai.yaml"]
    for path in files:
        if path.is_symlink() or path.suffix not in (".md", ".yaml", ".json", ""):
            raise SystemExit(f"Unexpected plugin file: {path.relative_to(root)}")
    shared = {
        path.relative_to(root).as_posix(): packaged_file(
            root, path.relative_to(root).as_posix()
        )
        for path in files
    }
    onboarding = extension.get("onboardingSkill")
    if onboarding is not None:
        if not onboarding.startswith("./skills/") or not onboarding.endswith(
            "/SKILL.md"
        ):
            raise ValueError("onboardingSkill must reference a packaged skill")
        if onboarding[2:] not in shared:
            raise ValueError("onboardingSkill is not included in the package")
    assets = {}
    references = [
        interface[k]
        for k in ("logo", "logoDark", "composerIcon", "composerIconDark")
        if k in interface
    ]
    references += interface.get("screenshots", [])
    for relative in references:
        if not isinstance(relative, str) or not relative.startswith("./assets/"):
            raise ValueError("Visual assets must use ./assets/ paths")
        if Path(relative).suffix.lower() not in (
            ".svg",
            ".png",
            ".jpg",
            ".jpeg",
            ".webp",
        ):
            raise ValueError(f"Unsupported image format: {relative}")
        data = packaged_file(root, relative)
        if len(data) > 5 * 1024 * 1024:
            raise ValueError(f"Image exceeds 5 MiB: {relative}")
        if Path(relative).suffix.lower() == ".svg" and relative in [
            interface.get(k)
            for k in ("logo", "logoDark", "composerIcon", "composerIconDark")
        ]:
            svg = ET.fromstring(data)
            box = svg.get("viewBox", "").split()
            dimensions = (
                [float(v) for v in box[2:]]
                if len(box) == 4
                else [float(svg.get("width", "0")), float(svg.get("height", "0"))]
            )
            if (
                len(dimensions) != 2
                or dimensions[0] != dimensions[1]
                or dimensions[0] < 48
            ):
                raise ValueError(
                    f"SVG icon must be square and at least 48x48: {relative}"
                )
        assets[relative[2:]] = data
    claude_manifest = {
        key: manifest[key]
        for key in (
            "name",
            "version",
            "description",
            "author",
            "repository",
            "homepage",
            "license",
            "keywords",
        )
    }
    claude_assets = {}
    if "composerIcon" in interface:
        # Both platforms use the same compact brand mark.
        claude_manifest["icon"] = interface["composerIcon"]
        icon_path = interface["composerIcon"][2:]
        claude_assets[icon_path] = assets[icon_path]
    packages = {
        "openai": dict(assets, **{"plugin.json": packaged_file(root, "plugin.json")}),
        "claude": {
            **claude_assets,
            ".claude-plugin/plugin.json": (
                json.dumps(claude_manifest, indent=2) + "\n"
            ).encode("utf-8"),
        },
    }
    outputs = []
    for platform, metadata in packages.items():
        output = (
            root
            / ".local"
            / "plugin-dist"
            / f"{manifest['name']}-{platform}-plugin-{manifest['version']}.zip"
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        contents = dict(shared, **metadata)
        with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
            for filename, data in sorted(contents.items()):
                info = zipfile.ZipInfo(filename, (2020, 1, 1, 0, 0, 0))
                info.external_attr = 0o100644 << 16
                archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
        with zipfile.ZipFile(output) as archive:
            if archive.namelist() != sorted(contents) or archive.testzip() is not None:
                raise SystemExit(f"Invalid plugin archive: {output}")
            for filename, data in contents.items():
                if archive.read(filename) != data:
                    raise SystemExit(f"Plugin content mismatch: {filename}")
        outputs.append(output)
        print(output)
        print("Files:", ", ".join(sorted(contents)))
        print("SHA256", hashlib.sha256(output.read_bytes()).hexdigest())

    return outputs


if __name__ == "__main__":
    build(Path(__file__).resolve().parents[1])
