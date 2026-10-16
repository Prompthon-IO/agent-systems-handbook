import importlib.util
import tempfile
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("init_project", Path(__file__).parents[1] / "scripts/init_project.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class InitTests(unittest.TestCase):
    def test_copy_is_complete_and_existing_projects_survive(self):
        with tempfile.TemporaryDirectory() as folder:
            destination = Path(folder) / "project"
            module.initialize(destination)
            self.assertTrue((destination / "src/Promotion.tsx").is_file())
            self.assertTrue((destination / "package-lock.json").is_file())
            marker = destination / "my-edit.txt"
            marker.write_text("keep this")
            with self.assertRaises(ValueError):
                module.initialize(destination)
            self.assertEqual(marker.read_text(), "keep this")

if __name__ == "__main__":
    unittest.main()
