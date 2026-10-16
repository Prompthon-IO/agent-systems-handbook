#!/usr/bin/env python3
"""Copy the small video starter into a new project without overwriting files."""
import argparse
import json
import shutil
from pathlib import Path


def initialize(destination: Path) -> Path:
    destination = destination.expanduser().absolute()
    if destination.exists() or destination.is_symlink():
        raise ValueError(f"Destination already exists: {destination}; select a new folder.")
    source = Path(__file__).resolve().parents[1] / "assets" / "starter"
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination)
    (destination / "public").mkdir(exist_ok=True)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    try:
        destination = initialize(args.destination)
    except (ValueError, OSError) as error:
        parser.exit(2, f"{error}\n")
    print(json.dumps({"status": "created", "project": str(destination),
                      "next": "Install lockfile dependencies during setup, set REMOTION_BROWSER_EXECUTABLE, edit brief.json, then npm run preview/render."}))


if __name__ == "__main__":
    main()
