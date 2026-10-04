"""Distribution boundaries for the two plugin formats."""

import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import shutil
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "package_plugin", ROOT / "scripts/package_plugin.py"
)
PACKAGER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGER)


class PluginPackagingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name in ("plugin.json", "pyproject.toml", "LICENSE"):
            shutil.copy(ROOT / name, self.root / name)
        shutil.copytree(ROOT / "skills", self.root / "skills")
        shutil.copytree(ROOT / "assets", self.root / "assets")
        self.manifest = json.loads((self.root / "plugin.json").read_text())

    def build(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return PACKAGER.build(self.root)

    def write_manifest(self, manifest):
        (self.root / "plugin.json").write_text(json.dumps(manifest))

    def test_platform_manifests_shared_skill_and_determinism(self):
        (self.root / "skills/private.md").write_text("must not ship")
        first = {p.name: p.read_bytes() for p in self.build()}
        self.assertEqual(first, {p.name: p.read_bytes() for p in self.build()})
        for platform in ("openai", "claude"):
            name = f"dmon-{platform}-plugin-{self.manifest['version']}.zip"
            with zipfile.ZipFile(io.BytesIO(first[name])) as archive:
                path = (
                    "plugin.json"
                    if platform == "openai"
                    else ".claude-plugin/plugin.json"
                )
                self.assertEqual(
                    set(archive.namelist()),
                    {
                        path,
                        "LICENSE",
                        "skills/dmon/SKILL.md",
                        "skills/dmon/agents/openai.yaml",
                        "assets/icon.svg",
                    }
                    | ({"assets/logo.svg"} if platform == "openai" else set()),
                )
                self.assertEqual(
                    archive.read("skills/dmon/SKILL.md"),
                    (self.root / "skills/dmon/SKILL.md").read_bytes(),
                )
                manifest = json.loads(archive.read(path))
                if platform == "openai":
                    self.assertEqual(manifest, self.manifest)
                else:
                    self.assertNotIn("extensions", manifest)
                    self.assertEqual(manifest["author"], self.manifest["author"])

    def test_version_and_required_skill(self):
        wrong = copy.deepcopy(self.manifest)
        wrong["version"] = "999.0.0"
        self.write_manifest(wrong)
        with self.assertRaises(SystemExit):
            self.build()
        self.write_manifest(self.manifest)
        (self.root / "skills/dmon/SKILL.md").unlink()
        with self.assertRaises(SystemExit):
            self.build()

    def test_invalid_listing_and_references(self):
        for key, value in (
            ("shortDescription", "x" * 31),
            ("defaultPrompt", ["x" * 129]),
            ("logo", "./assets/missing.svg"),
            ("logo", "./assets/../../private.svg"),
        ):
            with self.subTest(key=key, value=value):
                manifest = copy.deepcopy(self.manifest)
                manifest["extensions"]["com.openai"]["interface"][key] = value
                self.write_manifest(manifest)
                with self.assertRaises(ValueError):
                    self.build()
        manifest = copy.deepcopy(self.manifest)
        manifest["extensions"]["com.openai"]["onboardingSkill"] = (
            "./skills/missing/SKILL.md"
        )
        self.write_manifest(manifest)
        with self.assertRaises(ValueError):
            self.build()

    def test_referenced_asset_only_in_openai_package(self):
        (self.root / "assets/test-logo.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"/>'
        )
        (self.root / "assets/private.txt").write_text("must not ship")
        self.manifest["extensions"]["com.openai"]["interface"]["logo"] = (
            "./assets/test-logo.svg"
        )
        self.write_manifest(self.manifest)
        for path in self.build():
            with zipfile.ZipFile(path) as archive:
                self.assertEqual(
                    "assets/test-logo.svg" in archive.namelist(),
                    "-openai-" in path.name,
                )
                self.assertNotIn("assets/private.txt", archive.namelist())

    def test_non_square_icon_rejected(self):
        (self.root / "assets/icon.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 48"/>'
        )
        with self.assertRaises(ValueError):
            self.build()
