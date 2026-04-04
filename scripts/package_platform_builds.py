from __future__ import annotations

import argparse
import json
import os
import stat
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


def handle_remove_readonly(func, path: str, exc_info) -> None:
    os.chmod(path, stat.S_IWRITE)
    func(path)


def remove_path(path: Path) -> None:
    if not path.exists():
        return

    if path.is_dir():
        shutil.rmtree(path, onerror=handle_remove_readonly)
    else:
        path.chmod(path.stat().st_mode | stat.S_IWRITE)
        path.unlink()


def copy_artifact(source: Path, destination: Path) -> None:
    if destination.exists():
        remove_path(destination)

    destination.parent.mkdir(parents=True, exist_ok=True)

    if source.is_dir():
        shutil.copytree(source, destination)
    else:
        shutil.copy2(source, destination)


def prune_unlisted_children(root: Path, allowed_names: set[str]) -> None:
    if not root.exists():
        return

    for child in root.iterdir():
        if child.name in allowed_names:
            continue
        remove_path(child)


def package_platform_builds(build_dir: Path, platform: str, output_dir: Path) -> None:
    standalone_suffix = ".app" if platform == "macos" else ".exe"
    catalog = load_catalog()
    expected_slugs = {instrument["slug"] for instrument in catalog}

    prune_unlisted_children(output_dir / "vst3", expected_slugs)
    prune_unlisted_children(output_dir / "standalone", expected_slugs)

    for instrument in catalog:
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
