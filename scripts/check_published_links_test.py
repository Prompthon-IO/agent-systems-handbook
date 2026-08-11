from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import check_published_links


class PublishedLinkCheckTests(unittest.TestCase):
    def test_extensionless_route_normalizes_relative_index_target(self) -> None:
        source = check_published_links.REPO_ROOT / "reading-paths" / "practitioner.mdx"

        route = check_published_links.extensionless_route(
            source,
            "../workshops/index.mdx#setup",
        )

        self.assertEqual(route, "/workshops#setup")

    def test_finds_rendered_mdx_link_but_ignores_fenced_example(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            repo_root = Path(temporary_directory)
            source = repo_root / "reading-paths" / "practitioner.mdx"
            source.parent.mkdir(parents=True)
            source.write_text(
                "\n".join(
                    [
                        "[Broken](../systems/context-engineering.mdx)",
                        "",
                        "```md",
                        "[Example](../systems/example.mdx)",
                        "```",
                        "",
                        "[Healthy](/systems/context-engineering)",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.object(check_published_links, "REPO_ROOT", repo_root):
                violations = check_published_links.find_violations(source)

        self.assertEqual(len(violations), 1)
        self.assertEqual(
            violations[0].suggested_route,
            "/systems/context-engineering",
        )


if __name__ == "__main__":
    unittest.main()
