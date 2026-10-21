"""Verify the published official catalog matches installable plugin manifests.

Run: python -m unittest discover -s tests -v
"""
import json
from pathlib import Path
import re
import tomllib
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLUGINS = ROOT / "plugins"
CATALOG = ROOT / "catalog.json"


class CatalogConsistencyTests(unittest.TestCase):
    def test_catalog_matches_plugin_directories_and_manifests(self):
        document = json.loads(CATALOG.read_text(encoding="utf-8"))
        self.assertEqual(document["schema_version"], 1)
        entries = document["plugins"]
        self.assertIsInstance(entries, list)
        directories = {
            directory.name for directory in PLUGINS.iterdir()
            if directory.is_dir() and (directory / "uls-plugin.toml").is_file()
        }
        self.assertEqual({entry["id"] for entry in entries}, directories)
        self.assertEqual(len(entries), len(directories), "duplicate catalog IDs")
        for entry in entries:
            with self.subTest(plugin=entry["id"]):
                plugin_id = entry["id"]
                self.assertRegex(plugin_id, r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)*$")
                self.assertEqual(
                    set(entry), {"id", "name", "description", "version", "source"}
                )
                manifest = tomllib.loads(
                    (PLUGINS / plugin_id / "uls-plugin.toml").read_text(encoding="utf-8")
                )
                self.assertEqual(entry["id"], manifest["id"])
                self.assertEqual(entry["name"], manifest["name"])
                self.assertEqual(entry["version"], manifest["version"])
                self.assertTrue(entry["description"].strip())
                self.assertEqual(
                    entry["source"],
                    f"https://github.com/mcangeli/uls-plugins/tree/main/plugins/{plugin_id}",
                )


if __name__ == "__main__":
    unittest.main()
