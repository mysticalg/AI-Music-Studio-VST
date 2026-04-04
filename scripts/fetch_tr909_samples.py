#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = REPO_ROOT / ".cache" / "TR909Samples"

AUDIOREALISM_URL = "https://audiorealism.se/downloads/TR-909-44.1kHz-16bit.zip"
AUDIOREALISM_ARCHIVE = "TR-909-44.1kHz-16bit.zip"
AUDIOREALISM_FOLDER = "Audiorealism"
CONTENT_FOLDER = "TR-909-44.1kHz-16bit"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fetch a local TR-909 sample library for AI 909 Drum Machine."
    )
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Destination cache directory.")
    parser.add_argument("--clean", action="store_true", help="Remove the destination before downloading.")
    parser.add_argument("--force", action="store_true", help="Re-download and re-extract even if files already exist.")
    return parser.parse_args()


def download_to(url: str, destination: Path, force: bool) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and not force:
        return

    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request) as response, destination.open("wb") as handle:
        shutil.copyfileobj(response, handle)


def remove_junk_files(root: Path) -> None:
    for path in root.rglob("*"):
        if path.name == ".DS_Store" and path.is_file():
            path.unlink()

    for junk_dir in root.rglob("__MACOSX"):
        if junk_dir.is_dir():
            shutil.rmtree(junk_dir, ignore_errors=True)


def main() -> int:
    args = parse_args()
    root = args.root.resolve()

    if args.clean and root.exists():
        shutil.rmtree(root)

    root.mkdir(parents=True, exist_ok=True)

    download_dir = root / "_downloads"
    provider_root = root / AUDIOREALISM_FOLDER
    archive_path = download_dir / AUDIOREALISM_ARCHIVE
    content_root = provider_root / CONTENT_FOLDER

    if args.force and provider_root.exists():
        shutil.rmtree(provider_root)

    print(f"Fetching TR-909 samples into {root}")
    print("Source: Audiorealism TR-909 sample pack")
    print("Note: the upstream readme says the pack may not be redistributed without permission.")

    download_to(AUDIOREALISM_URL, archive_path, args.force)

    if args.force or not content_root.is_dir():
        provider_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(provider_root)

    remove_junk_files(provider_root)

    required_dirs = ("BassDrum", "SnareDrum", "ClosedHat")
    missing = [name for name in required_dirs if not (content_root / name).is_dir()]
    if missing:
        print(f"TR-909 sample library looks incomplete: missing {', '.join(missing)}", file=sys.stderr)
        return 1

    print(f"Ready: {content_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
