#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = REPO_ROOT / "docs" / "data" / "instruments.json"
CMAKE_LISTS_PATH = REPO_ROOT / "CMakeLists.txt"
FETCH_OPEN_SAMPLES_SCRIPT = REPO_ROOT / "scripts" / "fetch_open_instrument_samples.py"


@dataclass(frozen=True)
class SharedDataSpec:
    folder_name: str
    display_name: str
    cli_attr: str
    env_var: str
    build_cache_var: str
    required_slugs: tuple[str, ...]
    bundled_resource_folder: str | None = None
    can_fetch: bool = False


SHARED_DATA_SPECS = (
    SharedDataSpec(
        folder_name="OpenInstrumentSamples",
        display_name="OpenInstrumentSamples",
        cli_attr="open_instrument_samples_dir",
        env_var="AI_MUSIC_STUDIO_OPEN_INSTRUMENT_SAMPLES",
        build_cache_var="AIMS_OPEN_INSTRUMENT_SAMPLES_EFFECTIVE_LIBRARY_DIR",
        required_slugs=(
            "ai-strings",
            "ai-violin",
            "ai-flute",
            "ai-saxophone",
            "ai-bass-guitar",
            "ai-organ",
        ),
        bundled_resource_folder="OpenInstrumentSamples",
        can_fetch=True,
    ),
    SharedDataSpec(
        folder_name="SplendidGrandPiano",
        display_name="Splendid Grand Piano",
        cli_attr="piano_library_dir",
        env_var="AI_MUSIC_STUDIO_PIANO_LIBRARY",
        build_cache_var="AIMS_PIANO_EFFECTIVE_LIBRARY_DIR",
        required_slugs=("ai-piano",),
        bundled_resource_folder="Piano",
    ),
    SharedDataSpec(
        folder_name="VEC1",
        display_name="VEC1",
        cli_attr="vec1_library_dir",
        env_var="AI_MUSIC_STUDIO_VEC1_LIBRARY",
        build_cache_var="AIMS_VEC1_EFFECTIVE_LIBRARY_DIR",
        required_slugs=("ai-vec1-drum-pads",),
        bundled_resource_folder="VEC1",
    ),
)


def load_catalog(catalog_path: Path) -> list[dict]:
    return json.loads(catalog_path.read_text(encoding="utf-8"))


def detect_project_version() -> str:
    match = re.search(r"project\s*\(\s*\w+\s+VERSION\s+([0-9]+(?:\.[0-9]+)*)\s*\)", CMAKE_LISTS_PATH.read_text(encoding="utf-8"))
    if not match:
        raise RuntimeError(f"Could not detect project version from {CMAKE_LISTS_PATH}")
    return match.group(1)


def parse_cmake_cache(build_dir: Path | None) -> dict[str, str]:
    if build_dir is None:
        return {}

    cache_path = build_dir / "CMakeCache.txt"
    if not cache_path.exists():
        return {}

    values: dict[str, str] = {}
    for raw_line in cache_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//") or line.startswith("#"):
            continue

        match = re.match(r"([^:=]+):[^=]*=(.*)", line)
        if match:
            values[match.group(1)] = match.group(2)
    return values


def copy_path(source: Path, destination: Path) -> None:
    if destination.exists():
        if destination.is_dir():
            shutil.rmtree(destination, onexc=handle_remove_readonly)
        else:
            destination.unlink()

    destination.parent.mkdir(parents=True, exist_ok=True)
    if source.is_dir():
        shutil.copytree(source, destination, ignore=shutil.ignore_patterns(".git", "_downloads"))
    else:
        shutil.copy2(source, destination)


def handle_remove_readonly(function, path: str, excinfo) -> None:
    exc = excinfo[1]
    if not isinstance(exc, PermissionError):
        raise exc

    os.chmod(path, 0o700)
    function(path)


def find_single_vst3_bundle(slug_root: Path) -> Path:
    bundles = [path for path in slug_root.iterdir() if path.is_dir() and path.suffix.lower() == ".vst3"]
    if not bundles:
        raise FileNotFoundError(f"Could not find a .vst3 bundle under {slug_root}")
    if len(bundles) > 1:
        names = ", ".join(path.name for path in bundles)
        raise RuntimeError(f"Expected exactly one .vst3 bundle under {slug_root}, found: {names}")
    return bundles[0]


def discover_vst3_bundles(package_root: Path, catalog: list[dict]) -> dict[str, Path]:
    bundles: dict[str, Path] = {}
    for instrument in catalog:
        slug = instrument["slug"]
        slug_root = package_root / "vst3" / slug
        if not slug_root.is_dir():
            raise FileNotFoundError(f"Expected packaged VST3 directory for '{slug}' under {package_root / 'vst3'}")
        bundles[slug] = find_single_vst3_bundle(slug_root)
    return bundles


def discover_standalone_roots(package_root: Path, catalog: list[dict]) -> dict[str, Path]:
    standalones: dict[str, Path] = {}
    for instrument in catalog:
        slug = instrument["slug"]
        slug_root = package_root / "standalone" / slug
        if not slug_root.is_dir():
            raise FileNotFoundError(f"Expected packaged standalone directory for '{slug}' under {package_root / 'standalone'}")
        standalones[slug] = slug_root
    return standalones


def bundle_contains_resource(bundle_root: Path, resource_folder: str) -> bool:
    return (bundle_root / "Contents" / "Resources" / resource_folder).is_dir()


def repo_cache_candidates(folder_name: str) -> list[Path]:
    candidates = [
        REPO_ROOT / ".cache" / folder_name,
        REPO_ROOT.parent / ".cache" / folder_name,
    ]

    sibling_parent = REPO_ROOT.parent
    if sibling_parent.is_dir():
        candidates.append(sibling_parent / "AI-Music-Studio" / ".cache" / folder_name)
        for sibling in sibling_parent.iterdir():
            if sibling == REPO_ROOT or not sibling.is_dir():
                continue
            candidates.append(sibling / ".cache" / folder_name)

    unique_candidates: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate.resolve(strict=False)).lower()
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(candidate)
    return unique_candidates


def runtime_data_root_candidates(folder_name: str) -> list[Path]:
    candidates: list[Path] = []
    general_root = os.environ.get("AI_MUSIC_STUDIO_VST_DATA_ROOT", "").strip()
    if general_root:
        candidates.append(Path(general_root) / folder_name)
    return candidates


def resolve_data_source(spec: SharedDataSpec, args: argparse.Namespace, cmake_cache: dict[str, str]) -> Path | None:
    explicit_path = getattr(args, spec.cli_attr)
    if explicit_path:
        candidate = explicit_path.resolve()
        if candidate.is_dir():
            return candidate
        raise FileNotFoundError(f"{spec.display_name} directory was provided but does not exist: {candidate}")

    env_path = os.environ.get(spec.env_var, "").strip()
    if env_path:
        candidate = Path(env_path).expanduser().resolve()
        if candidate.is_dir():
            return candidate
        raise FileNotFoundError(f"{spec.env_var} points to a missing directory: {candidate}")

    for candidate in runtime_data_root_candidates(spec.folder_name):
        if candidate.is_dir():
            return candidate.resolve()

    build_cache_value = cmake_cache.get(spec.build_cache_var, "").strip()
    if build_cache_value:
        candidate = Path(build_cache_value).expanduser().resolve()
        if candidate.is_dir():
            return candidate

    for candidate in repo_cache_candidates(spec.folder_name):
        if candidate.is_dir():
            return candidate.resolve()

    return None


def ensure_shared_data_available(
    spec: SharedDataSpec,
    bundles: dict[str, Path],
    args: argparse.Namespace,
    cmake_cache: dict[str, str],
    staging_root: Path,
) -> Path | None:
    required_bundles = [bundles[slug] for slug in spec.required_slugs if slug in bundles]
    if not required_bundles:
        return None

    if spec.bundled_resource_folder and all(bundle_contains_resource(bundle, spec.bundled_resource_folder) for bundle in required_bundles):
        return None

    source = resolve_data_source(spec, args, cmake_cache)
    if source is not None:
        return source

    if spec.can_fetch and args.fetch_open_instrument_samples:
        fetched_root = staging_root / "_downloads" / spec.folder_name
        subprocess.run(
            [sys.executable, str(FETCH_OPEN_SAMPLES_SCRIPT), "--root", str(fetched_root)],
            check=True,
        )
        return fetched_root

    message = [
        f"{spec.display_name} is required for the bundled installer but was not found.",
        f"Expected one of the packaged plugins to have '{spec.bundled_resource_folder}' embedded or provide a shared data directory.",
    ]
    if spec.can_fetch:
        message.append("Rerun with --fetch-open-instrument-samples to download the open sample set automatically.")
    message.append(f"You can also pass --{spec.cli_attr.replace('_', '-')} or set {spec.env_var}.")
    raise FileNotFoundError(" ".join(message))


def stage_vst3_bundles(bundles: dict[str, Path], staging_root: Path, catalog: list[dict]) -> list[dict[str, str]]:
    staged_plugins: list[dict[str, str]] = []
    vst3_root = staging_root / "vst3"
    vst3_root.mkdir(parents=True, exist_ok=True)

    for instrument in catalog:
        slug = instrument["slug"]
        bundle = bundles[slug]
        destination = vst3_root / bundle.name
        copy_path(bundle, destination)
        staged_plugins.append(
            {
                "slug": slug,
                "productName": instrument["productName"],
                "bundleName": bundle.name,
            }
        )

    return staged_plugins


def stage_standalone_apps(standalone_roots: dict[str, Path], staging_root: Path, catalog: list[dict]) -> list[dict[str, str]]:
    staged_apps: list[dict[str, str]] = []
    standalone_root = staging_root / "standalone"
    standalone_root.mkdir(parents=True, exist_ok=True)

    for instrument in catalog:
        slug = instrument["slug"]
        source_root = standalone_roots[slug]
        destination_root = standalone_root / slug
        destination_root.mkdir(parents=True, exist_ok=True)

        exe_names: list[str] = []
        for child in source_root.iterdir():
            copy_path(child, destination_root / child.name)
            if child.is_file() and child.suffix.lower() == ".exe":
                exe_names.append(child.name)

        if not exe_names:
            raise FileNotFoundError(f"Expected a standalone .exe under {source_root}")

        staged_apps.append(
            {
                "slug": slug,
                "productName": instrument["productName"],
                "installDirName": instrument["productName"],
                "primaryExeName": exe_names[0],
            }
        )

    return staged_apps


def stage_shared_data(
    bundles: dict[str, Path],
    args: argparse.Namespace,
    cmake_cache: dict[str, str],
    staging_root: Path,
) -> list[dict[str, str]]:
    staged_shared_data: list[dict[str, str]] = []
    shared_root = staging_root / "data"
    shared_root.mkdir(parents=True, exist_ok=True)

    for spec in SHARED_DATA_SPECS:
        source = ensure_shared_data_available(spec, bundles, args, cmake_cache, staging_root)
        if source is None:
            continue

        destination = shared_root / spec.folder_name
        copy_path(source, destination)
        staged_shared_data.append(
            {
                "folderName": spec.folder_name,
                "displayName": spec.display_name,
                "sourcePath": str(source),
            }
        )

    return staged_shared_data


def write_manifest(
    version: str,
    staged_plugins: list[dict[str, str]],
    staged_apps: list[dict[str, str]],
    staged_shared_data: list[dict[str, str]],
    staging_root: Path,
) -> Path:
    manifest_path = staging_root / "installer-manifest.json"
    manifest = {
        "version": version,
        "plugins": staged_plugins,
        "standalones": staged_apps,
        "sharedData": staged_shared_data,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest_path


def discover_inno_setup_compiler(explicit_compiler: Path | None) -> Path:
    if explicit_compiler is not None:
        compiler = explicit_compiler.resolve()
        if compiler.is_file():
            return compiler
        raise FileNotFoundError(f"Inno Setup compiler was provided but does not exist: {compiler}")

    for candidate in (
        shutil.which("ISCC.exe"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles(x86)", "")) / "Inno Setup 6" / "ISCC.exe",
        Path(os.environ.get("ProgramFiles", "")) / "Inno Setup 6" / "ISCC.exe",
    ):
        if not candidate:
            continue
        candidate_path = Path(candidate)
        if candidate_path.is_file():
            return candidate_path.resolve()

    raise FileNotFoundError(
        "Could not find ISCC.exe. Install Inno Setup 6 or pass --compiler with the full path to ISCC.exe."
    )


def inno_escape(path: Path) -> str:
    return str(path).replace("\\", "\\")


def build_inno_script(
    version: str,
    output_dir: Path,
    staging_root: Path,
    staged_plugins: list[dict[str, str]],
    staged_apps: list[dict[str, str]],
    staged_shared_data: list[dict[str, str]],
    manifest_path: Path,
    app_name: str,
    app_id_scope: str,
    output_base_name: str,
    default_dir_name: str,
) -> str:
    app_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, app_id_scope)).upper()
    output_base_name = f"{output_base_name}-{version}"
    script_lines = [
        "#define StagingRoot \"" + inno_escape(staging_root) + "\"",
        "#define OutputRoot \"" + inno_escape(output_dir) + "\"",
        "",
        "[Setup]",
        f"AppId={{{{{app_id}}}}}",
        f"AppName={app_name}",
        f"AppVersion={version}",
        "AppPublisher=AI Music Studio",
        "ArchitecturesAllowed=x64compatible",
        "ArchitecturesInstallIn64BitMode=x64compatible",
        "PrivilegesRequired=admin",
        f"DefaultDirName={default_dir_name}",
        "DisableDirPage=yes",
        "DisableProgramGroupPage=yes",
        "WizardStyle=modern",
        "CloseApplications=yes",
        "RestartApplications=no",
        "Compression=lzma2/ultra64",
        "SolidCompression=yes",
        "OutputDir={#OutputRoot}",
        f"OutputBaseFilename={output_base_name}",
        f"VersionInfoVersion={version}",
        "",
        "[InstallDelete]",
    ]

    for plugin in staged_plugins:
        script_lines.append(f'Type: filesandordirs; Name: "{{code:GetVst3InstallDir}}\\{plugin["bundleName"]}"')
    for app in staged_apps:
        script_lines.append(
            f'Type: filesandordirs; Name: "{{commonpf64}}\\AI Music Studio\\Standalone\\{app["installDirName"]}"'
        )
    for shared_data in staged_shared_data:
        script_lines.append(
            f'Type: filesandordirs; Name: "{{commonappdata}}\\AI Music Studio\\VSTData\\{shared_data["folderName"]}"'
        )

    script_lines.extend(
        [
            "",
            "[Files]",
        ]
    )

    for plugin in staged_plugins:
        bundle_name = plugin["bundleName"]
        script_lines.append(
            'Source: "{#StagingRoot}\\vst3\\'
            + bundle_name
            + '\\*"; DestDir: "{code:GetVst3InstallDir}\\'
            + bundle_name
            + '"; Flags: ignoreversion recursesubdirs createallsubdirs'
        )

    for app in staged_apps:
        script_lines.append(
            'Source: "{#StagingRoot}\\standalone\\'
            + app["slug"]
            + '\\*"; DestDir: "{commonpf64}\\AI Music Studio\\Standalone\\'
            + app["installDirName"]
            + '"; Flags: ignoreversion recursesubdirs createallsubdirs'
        )

    for shared_data in staged_shared_data:
        folder_name = shared_data["folderName"]
        script_lines.append(
            'Source: "{#StagingRoot}\\data\\'
            + folder_name
            + '\\*"; DestDir: "{commonappdata}\\AI Music Studio\\VSTData\\'
            + folder_name
            + '"; Flags: ignoreversion recursesubdirs createallsubdirs'
        )

    script_lines.append(
        'Source: "'
        + inno_escape(manifest_path)
        + '"; DestDir: "{commonappdata}\\AI Music Studio\\VSTData"; DestName: "installer-manifest.json"; Flags: ignoreversion'
    )

    script_lines.extend(
        [
            "",
            "[UninstallDelete]",
            'Type: files; Name: "{commonappdata}\\AI Music Studio\\VSTData\\installer-manifest.json"',
            'Type: dirifempty; Name: "{commonappdata}\\AI Music Studio\\VSTData"',
            'Type: dirifempty; Name: "{commonappdata}\\AI Music Studio"',
            'Type: dirifempty; Name: "{app}"',
            "",
            "[Code]",
            "var",
            "  Vst3LocationPage: TInputOptionWizardPage;",
            "  Vst3CustomDirPage: TInputDirWizardPage;",
            "",
            "procedure InitializeWizard();",
            "var",
            "  DefaultVst3Dir: String;",
            "begin",
            "  DefaultVst3Dir := ExpandConstant('{commoncf64}\\VST3');",
            "",
            "  Vst3LocationPage := CreateInputOptionPage(",
            "    wpWelcome,",
            "    'VST3 Installation Folder',",
            "    'Choose where the VST3 plugins should be installed.',",
            "    'Use the standard VST3 folder for automatic DAW discovery, or choose a custom VST3 folder.',",
            "    True,",
            "    False);",
            "",
            "  Vst3LocationPage.Add('Use the standard VST3 folder (' + DefaultVst3Dir + ')');",
            "  Vst3LocationPage.Add('Use a custom VST3 folder');",
            "  Vst3LocationPage.SelectedValueIndex := 0;",
            "",
            "  Vst3CustomDirPage := CreateInputDirPage(",
            "    Vst3LocationPage.ID,",
            "    'Custom VST3 Folder',",
            "    'Choose the custom VST3 folder.',",
            "    'Select the folder where the VST3 bundles should be installed.',",
            "    False,",
            "    '');",
            "  Vst3CustomDirPage.Add('Custom VST3 folder');",
            "  Vst3CustomDirPage.Values[0] := DefaultVst3Dir;",
            "end;",
            "",
            "function GetVst3InstallDir(Param: String): String;",
            "begin",
            "  if (Vst3LocationPage <> nil) and Vst3LocationPage.Values[1] then",
            "    Result := RemoveBackslashUnlessRoot(Trim(Vst3CustomDirPage.Values[0]))",
            "  else",
            "    Result := ExpandConstant('{commoncf64}\\VST3');",
            "end;",
            "",
            "function ShouldSkipPage(PageID: Integer): Boolean;",
            "begin",
            "  Result := False;",
            "",
            "  if (Vst3CustomDirPage <> nil) and (PageID = Vst3CustomDirPage.ID) then",
            "    Result := not Vst3LocationPage.Values[1];",
            "end;",
            "",
            "function NextButtonClick(CurPageID: Integer): Boolean;",
            "begin",
            "  Result := True;",
            "",
            "  if (Vst3CustomDirPage <> nil) and (CurPageID = Vst3CustomDirPage.ID) then",
            "  begin",
            "    if Trim(Vst3CustomDirPage.Values[0]) = '' then",
            "    begin",
            "      MsgBox('Choose a custom VST3 folder, or go back and select the standard VST3 folder.', mbError, MB_OK);",
            "      Result := False;",
            "    end;",
            "  end;",
            "end;",
            "",
        ]
    )

    return "\n".join(script_lines)


def write_inno_script(
    version: str,
    output_dir: Path,
    staging_root: Path,
    staged_plugins: list[dict[str, str]],
    staged_apps: list[dict[str, str]],
    staged_shared_data: list[dict[str, str]],
    manifest_path: Path,
    app_name: str,
    app_id_scope: str,
    output_base_name: str,
    default_dir_name: str,
    script_name: str,
) -> Path:
    script_path = output_dir / script_name
    script_path.parent.mkdir(parents=True, exist_ok=True)
    script_path.write_text(
        build_inno_script(version,
                          output_dir,
                          staging_root,
                          staged_plugins,
                          staged_apps,
                          staged_shared_data,
                          manifest_path,
                          app_name,
                          app_id_scope,
                          output_base_name,
                          default_dir_name),
        encoding="utf-8",
    )
    return script_path


def compile_installer(script_path: Path, compiler: Path) -> None:
    subprocess.run([str(compiler), str(script_path)], check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stage and optionally compile a Windows installer for the bundled AI Music Studio VST3 instruments.")
    parser.add_argument("--catalog", type=Path, default=CATALOG_PATH,
                        help="Catalog JSON describing the products to include in the installer.")
    parser.add_argument("--package-root", type=Path, default=REPO_ROOT / "dist" / "release-input" / "windows",
                        help="Packaged Windows artifact root that contains the 'vst3/' layout from package_platform_builds.py.")
    parser.add_argument("--build-dir", type=Path, default=None,
                        help="Optional CMake build directory used to read resolved asset paths from CMakeCache.txt.")
    parser.add_argument("--output-dir", type=Path, default=REPO_ROOT / "dist" / "windows-installer",
                        help="Directory for the staged installer layout and final compiled installer.")
    parser.add_argument("--version", default=detect_project_version(),
                        help="Installer version string. Defaults to the CMake project version.")
    parser.add_argument("--app-name", default="AI Music Studio Bundled Instruments",
                        help="Installer display name.")
    parser.add_argument("--app-id-scope", default="ai-music-studio-bundled-vst3-installer",
                        help="Stable string used to derive the installer AppId.")
    parser.add_argument("--output-base-name", default="AI-Music-Studio-Bundled-Instruments-Windows-Installer",
                        help="Base filename for the compiled installer, without the version suffix.")
    parser.add_argument("--script-name", default="AI-Music-Studio-Bundled-VST3.iss",
                        help="Filename for the generated Inno Setup script.")
    parser.add_argument("--default-dir-name", default=r"{commonpf64}\AI Music Studio\Bundled VST3",
                        help="DefaultDirName value for the generated Inno Setup script.")
    parser.add_argument("--open-instrument-samples-dir", type=Path, default=None,
                        help="Optional explicit OpenInstrumentSamples source directory.")
    parser.add_argument("--piano-library-dir", type=Path, default=None,
                        help="Optional explicit Splendid Grand Piano source directory.")
    parser.add_argument("--vec1-library-dir", type=Path, default=None,
                        help="Optional explicit VEC1 source directory.")
    parser.add_argument("--fetch-open-instrument-samples", action="store_true",
                        help="Download the open sample library automatically if it is required and not already available.")
    parser.add_argument("--skip-standalone", action="store_true",
                        help="Do not stage or install standalone application builds.")
    parser.add_argument("--skip-compile", action="store_true",
                        help="Only stage the installer files and write the .iss script.")
    parser.add_argument("--compiler", type=Path, default=None,
                        help="Optional explicit path to ISCC.exe.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    catalog_path = args.catalog.resolve()
    package_root = args.package_root.resolve()
    output_dir = args.output_dir.resolve()
    staging_root = output_dir / "staging"

    if not catalog_path.is_file():
        raise FileNotFoundError(f"Catalog does not exist: {catalog_path}")
    if not package_root.is_dir():
        raise FileNotFoundError(f"Package root does not exist: {package_root}")

    if staging_root.exists():
        shutil.rmtree(staging_root, onexc=handle_remove_readonly)
    staging_root.mkdir(parents=True, exist_ok=True)

    catalog = load_catalog(catalog_path)
    cmake_cache = parse_cmake_cache(args.build_dir.resolve() if args.build_dir else None)
    bundles = discover_vst3_bundles(package_root, catalog)
    staged_plugins = stage_vst3_bundles(bundles, staging_root, catalog)
    staged_apps: list[dict[str, str]] = []
    if not args.skip_standalone:
        standalone_roots = discover_standalone_roots(package_root, catalog)
        staged_apps = stage_standalone_apps(standalone_roots, staging_root, catalog)
    staged_shared_data = stage_shared_data(bundles, args, cmake_cache, staging_root)
    manifest_path = write_manifest(args.version, staged_plugins, staged_apps, staged_shared_data, staging_root)
    script_path = write_inno_script(args.version,
                                    output_dir,
                                    staging_root,
                                    staged_plugins,
                                    staged_apps,
                                    staged_shared_data,
                                    manifest_path,
                                    args.app_name,
                                    args.app_id_scope,
                                    args.output_base_name,
                                    args.default_dir_name,
                                    args.script_name)

    if args.skip_compile:
        print(f"Staged installer files in {staging_root}")
        print(f"Wrote Inno Setup script to {script_path}")
        return 0

    compiler = discover_inno_setup_compiler(args.compiler)
    compile_installer(script_path, compiler)
    print(f"Built Windows installer using {compiler}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
