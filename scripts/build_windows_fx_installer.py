#!/usr/bin/env python3
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from build_windows_installer import detect_project_version


REPO_ROOT = Path(__file__).resolve().parents[1]
FX_CATALOG_PATH = REPO_ROOT / "packaging" / "catalogs" / "fx-pack.json"
PACKAGE_SCRIPT = REPO_ROOT / "scripts" / "package_platform_builds.py"
INSTALLER_SCRIPT = REPO_ROOT / "scripts" / "build_windows_installer.py"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Package and optionally compile a Windows installer for the AI Music Studio FX pack."
    )
    parser.add_argument("--build-dir", type=Path, default=REPO_ROOT / "build-installer-refresh",
                        help="Build directory containing the FX VST3 artefacts.")
    parser.add_argument("--package-root", type=Path, default=REPO_ROOT / "dist" / "release-input" / "windows-fx",
                        help="Intermediate packaged-artifact root for the FX installer.")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "dist" / "windows-installer-fx",
                        help="Directory for the staged FX installer layout and compiled installer.")
    parser.add_argument("--version", default=detect_project_version(),
                        help="Installer version string. Defaults to the CMake project version.")
    parser.add_argument("--skip-package", action="store_true",
                        help="Reuse the existing packaged FX artefacts instead of collecting them from the build directory first.")
    parser.add_argument("--skip-compile", action="store_true",
                        help="Only stage the installer files and generate the Inno Setup script.")
    parser.add_argument("--compiler", type=Path, default=None,
                        help="Optional explicit path to ISCC.exe.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    build_dir = args.build_dir.resolve()
    package_root = args.package_root.resolve()
    output_dir = args.output_dir.resolve()

    if not args.skip_package:
        subprocess.run(
            [
                sys.executable,
                str(PACKAGE_SCRIPT),
                "--build-dir",
                str(build_dir),
                "--platform",
                "windows",
                "--output-dir",
                str(package_root),
                "--catalog",
                str(FX_CATALOG_PATH),
                "--formats",
                "vst3",
            ],
            check=True,
        )

    command = [
        sys.executable,
        str(INSTALLER_SCRIPT),
        "--catalog",
        str(FX_CATALOG_PATH),
        "--package-root",
        str(package_root),
        "--output-dir",
        str(output_dir),
        "--build-dir",
        str(build_dir),
        "--version",
        args.version,
        "--app-name",
        "AI Music Studio FX Pack",
        "--app-id-scope",
        "ai-music-studio-fx-pack-vst3-installer",
        "--output-base-name",
        "AI-Music-Studio-FX-Pack-Windows-Installer",
        "--script-name",
        "AI-Music-Studio-FX-Pack.iss",
        "--default-dir-name",
        r"{commonpf64}\AI Music Studio\FX Pack",
        "--skip-standalone",
    ]

    if args.skip_compile:
        command.append("--skip-compile")
    if args.compiler is not None:
        command.extend(["--compiler", str(args.compiler.resolve())])

    subprocess.run(command, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
