from __future__ import annotations

import argparse
import json
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "docs" / "data" / "instruments.json"


def load_catalog() -> list[dict]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def add_path_to_zip(archive: zipfile.ZipFile, source: Path, archive_root: str) -> None:
    if source.is_dir():
        for child in sorted(source.rglob("*")):
            if child.is_dir():
                continue
            relative = child.relative_to(source)
            archive.write(child, f"{archive_root}/{relative.as_posix()}")
    else:
        archive.write(source, f"{archive_root}/{source.name}")


def discover_platform_name(path: Path) -> str:
    name = path.name.lower()
    if "mac" in name:
        return "macos"
    if "win" in name:
        return "windows"
    return name


def build_release_archives(platform_dirs: list[Path], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for instrument in load_catalog():
        slug = instrument["slug"]
        for package_format, asset_name in instrument["releaseAssets"].items():
            package_sources: list[tuple[str, Path]] = []

            for platform_dir in platform_dirs:
                platform_name = discover_platform_name(platform_dir)
                source_root = platform_dir / package_format / slug
                if not source_root.exists():
                    continue

                children = [child for child in source_root.iterdir()]
                if not children:
                    continue

                package_sources.append((platform_name, children[0]))

            if not package_sources:
                raise FileNotFoundError(f"No packaged '{package_format}' build found for {slug}")

            archive_path = output_dir / asset_name
            if archive_path.exists():
                archive_path.unlink()

            with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
                for platform_name, source_path in package_sources:
                    add_path_to_zip(archive, source_path, platform_name)


def main() -> int:
    parser = argparse.ArgumentParser(description="Create cross-platform release archives for each instrument.")
    parser.add_argument("--platform-dir", dest="platform_dirs", action="append", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    args = parser.parse_args()

    build_release_archives([path.resolve() for path in args.platform_dirs], args.output_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
