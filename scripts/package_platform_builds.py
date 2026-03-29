from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "docs" / "data" / "instruments.json"


def load_catalog() -> list[dict]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def find_single(root: Path, pattern: str) -> Path:
    matches = [path for path in root.rglob(pattern)]
    if not matches:
        raise FileNotFoundError(f"Could not find '{pattern}' under {root}")

    matches.sort(key=lambda path: len(path.parts))
    return matches[0]


def copy_artifact(source: Path, destination: Path) -> None:
    if destination.exists():
        if destination.is_dir():
            shutil.rmtree(destination)
        else:
            destination.unlink()

    destination.parent.mkdir(parents=True, exist_ok=True)

    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


def package_platform_builds(build_dir: Path, platform: str, output_dir: Path) -> None:
    standalone_suffix = ".app" if platform == "macos" else ".exe"

    for instrument in load_catalog():
        product_name = instrument["productName"]
        slug = instrument["slug"]

        vst3_source = find_single(build_dir, f"{product_name}.vst3")
        standalone_source = find_single(build_dir, f"{product_name}{standalone_suffix}")

        copy_artifact(vst3_source, output_dir / "vst3" / slug / vst3_source.name)
        copy_artifact(standalone_source, output_dir / "standalone" / slug / standalone_source.name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect build outputs into a predictable per-platform layout.")
    parser.add_argument("--build-dir", required=True, type=Path)
    parser.add_argument("--platform", required=True, choices=("windows", "macos"))
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    package_platform_builds(args.build_dir.resolve(), args.platform, args.output_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
