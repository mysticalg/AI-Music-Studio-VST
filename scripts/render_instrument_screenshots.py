from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "docs" / "data" / "instruments.json"


def load_catalog() -> list[dict]:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def find_exporter(build_dir: Path, target_name: str) -> Path:
    exe_name = f"{target_name}ScreenshotExporter.exe"
    matches = list(build_dir.rglob(exe_name))
    if not matches:
        raise FileNotFoundError(f"Could not find screenshot exporter '{exe_name}' under {build_dir}")

    matches.sort(key=lambda path: len(path.parts))
    return matches[0]


def render_screenshots(build_dir: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    for instrument in load_catalog():
        exporter = find_exporter(build_dir, instrument["targetName"])
        output_path = output_dir / f"{instrument['slug']}.png"
        subprocess.run([str(exporter), str(output_path)], check=True, cwd=REPO_ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="Render screenshot PNGs for all instrument UIs.")
    parser.add_argument("--build-dir", required=True, type=Path)
    parser.add_argument("--output-dir", default=REPO_ROOT / "docs" / "screenshots", type=Path)
    args = parser.parse_args()

    render_screenshots(args.build_dir.resolve(), args.output_dir.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
