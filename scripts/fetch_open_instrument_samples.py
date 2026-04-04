#!/usr/bin/env python3
from __future__ import annotations

import argparse
import posixpath
import re
import shutil
import subprocess
import tarfile
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = REPO_ROOT / ".cache" / "OpenInstrumentSamples"

SFZ_OPCODE_RE = re.compile(r"([A-Za-z0-9_]+)=([^<>\r\n]*?)(?=(?:\s+[A-Za-z0-9_]+=)|$)")

BASS_RAW_ROOT = "https://raw.githubusercontent.com/freepats/electric-bass-YR/main/"

SSO_SPARSE_DIRS = [
    "Sonatina Symphonic Orchestra/Strings - Performance",
    "Sonatina Symphonic Orchestra/Woodwinds - Performance",
    "Sonatina Symphonic Orchestra/Samples/1st Violins",
    "Sonatina Symphonic Orchestra/Samples/Violas",
    "Sonatina Symphonic Orchestra/Samples/Celli",
    "Sonatina Symphonic Orchestra/Samples/Basses",
    "Sonatina Symphonic Orchestra/Samples/Violin 2",
    "Sonatina Symphonic Orchestra/Samples/Flute 1",
    "Sonatina Symphonic Orchestra/Samples/Flute 2",
    "Sonatina Symphonic Orchestra/Samples/Alto Flute",
    "Sonatina Symphonic Orchestra/Samples-looped/Violin 1",
    "Sonatina Symphonic Orchestra/Samples-looped/Violin 2",
    "Sonatina Symphonic Orchestra/Samples-looped/Flute 1",
]

BASS_TOP_LEVEL_FILES = [
    "FingerBassYR 20190930.sfz",
    "PickedBassYR 20190930.sfz",
    "LICENSE.txt",
    "README.txt",
]

ARCHIVES = [
    (
        "https://freepats.zenvoid.org/Reed/TenorSaxophone/TenorSaxophone-small-SFZ-20200717.tar.bz2",
        "Saxophone",
        "TenorSaxophone-small-SFZ-20200717.tar.bz2",
    ),
    (
        "https://freepats.zenvoid.org/Organ/ChurchOrganEmulation/ChurchOrganEmulation-SFZ-20190924.tar.xz",
        "Organ",
        "ChurchOrganEmulation-SFZ-20190924.tar.xz",
    ),
]

GRANDORGUE_BUREA_URL = "https://familjenpalo.se/sites/default/files/sampleset/packages/BureaChurch.orgue"
GRANDORGUE_BUREA_ARCHIVE = "BureaChurch.orgue"
GRANDORGUE_BUREA_SUBDIR = "Organ/GrandOrgue-BureaChurch"
GRANDORGUE_BUREA_BANKS = {
    "cathedral-principal.sfz": [
        ("HVPrincipal8", 0.0),
        ("HVOktava4", -6.0),
        ("HVMixtur", -11.0),
    ],
    "soft-stops.sfz": [
        ("HVGedakt8", 0.0),
        ("SVRorflojt8", -4.0),
        ("POSGedakt8", -6.0),
    ],
    "bright-mixture.sfz": [
        ("HVPrincipal8", -1.5),
        ("HVOktava4", -4.0),
        ("HVOktava2", -7.5),
        ("HVMixtur", -8.0),
        ("HVSesquialtera", -10.5),
    ],
    "warm-diapason.sfz": [
        ("SVSalicional8", 0.0),
        ("HVPrincipal8", -4.0),
        ("Quintadena8", -4.5),
        ("Halflojt8", -6.0),
    ],
}

GRANDORGUE_PITEA_URL = "https://familjenpalo.se/sites/default/files/sampleset/packages/PiteaMHS20250727.orgue"
GRANDORGUE_PITEA_ARCHIVE = "PiteaMHS20250727.orgue"
GRANDORGUE_PITEA_SUBDIR = "Organ/GrandOrgue-PiteaMHS"
GRANDORGUE_PITEA_BANKS = {
    "grand-principal.sfz": [
        ("HVPrincipal8", 0.0),
        ("HVGedPommer16", -12.0),
        ("HVDubbelflojt8", -8.0),
        ("HVOktava4", -4.5),
        ("HVOktava2", -8.5),
        ("HVMixtur", -11.0),
    ],
}


def quote_repo_path(path: str) -> str:
    return urllib.parse.quote(path.replace("\\", "/"), safe="/()+")


def normalize_repo_path(path: str | Path) -> str:
    return posixpath.normpath(str(path).replace("\\", "/"))


def fetch_text(url: str) -> str:
    try:
        with urllib.request.urlopen(url) as response:
            return response.read().decode("utf-8", errors="replace")
    except Exception as exc:
        raise RuntimeError(f"Failed to fetch text: {url}") from exc


def download_to(url: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return
    try:
        with urllib.request.urlopen(url) as response, destination.open("wb") as handle:
            shutil.copyfileobj(response, handle)
    except Exception as exc:
        raise RuntimeError(f"Failed to download: {url}") from exc


def ffmpeg_binary() -> str:
    binary = shutil.which("ffmpeg")
    if not binary:
        raise RuntimeError("ffmpeg is required to decode GrandOrgue WavPack samples. Install ffmpeg and retry.")
    return binary


def iter_sfz_opcodes(line: str):
    for match in SFZ_OPCODE_RE.finditer(line):
        yield match.group(1).strip().lower(), match.group(2).strip()


def sfz_dependencies(text: str):
    includes: list[str] = []
    samples: list[str] = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("//"):
            continue
        include_match = re.match(r'#include\s+"([^"]+)"', line)
        if include_match:
            includes.append(include_match.group(1).strip())
            continue
        for key, value in iter_sfz_opcodes(raw_line):
            if key == "sample" and value:
                samples.append(value)
    return includes, samples


def run_git(args: list[str], cwd: Path | None = None) -> None:
    subprocess.run(args, cwd=cwd, check=True)


def download_sso_tree(root: Path) -> None:
    checkout_dir = root / "_downloads" / "sso-sparse"
    source_dir = checkout_dir / "Sonatina Symphonic Orchestra"
    destination_dir = root / "Sonatina Symphonic Orchestra"

    if not checkout_dir.exists():
        run_git(
            [
                "git",
                "clone",
                "--depth",
                "1",
                "--filter=blob:none",
                "--sparse",
                "https://github.com/peastman/sso.git",
                str(checkout_dir),
            ]
        )

    run_git(
        ["git", "sparse-checkout", "set", "--cone", *SSO_SPARSE_DIRS],
        cwd=checkout_dir,
    )
    run_git(["git", "checkout", "master"], cwd=checkout_dir)

    if destination_dir.exists():
        shutil.rmtree(destination_dir)
    shutil.copytree(source_dir, destination_dir)


def download_bass_tree(root: Path) -> None:
    seen: set[str] = set()

    def download_dependency(rel_path: str) -> None:
        normalized = normalize_repo_path(rel_path)
        if normalized in seen:
            return
        seen.add(normalized)

        url = BASS_RAW_ROOT + quote_repo_path(normalized)
        destination = root / "BassGuitar" / normalized

        if normalized.lower().endswith(".sfz"):
            text = fetch_text(url)
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text, encoding="utf-8")
            _, samples = sfz_dependencies(text)
            base_dir = Path(normalized).parent
            for sample_path in samples:
                child = normalize_repo_path(base_dir / sample_path)
                download_to(BASS_RAW_ROOT + quote_repo_path(child), root / "BassGuitar" / child)
        else:
            download_to(url, destination)

    for rel_path in BASS_TOP_LEVEL_FILES:
        download_dependency(rel_path)


def extract_archive(url: str, subdir: str, archive_name: str, root: Path) -> None:
    destination_root = root / subdir
    archive_path = root / "_downloads" / archive_name
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if not archive_path.exists():
        download_to(url, archive_path)

    marker = destination_root / ".extracted"
    if marker.exists():
        return

    if destination_root.exists():
        shutil.rmtree(destination_root)
    destination_root.mkdir(parents=True, exist_ok=True)

    with tarfile.open(archive_path) as archive:
        archive.extractall(destination_root)

    marker.write_text(url, encoding="utf-8")


def midi_from_sample_filename(filename: str) -> int | None:
    match = re.match(r"(\d{2,3})-", Path(filename).name)
    if not match:
        return None
    value = int(match.group(1))
    if value < 0 or value > 127:
        return None
    return value


def convert_wavpack_member(zip_handle: zipfile.ZipFile, member_name: str, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return

    temp_source = destination.with_suffix(".wv")
    with zip_handle.open(member_name) as source, temp_source.open("wb") as handle:
        shutil.copyfileobj(source, handle)

    try:
        subprocess.run(
            [ffmpeg_binary(), "-y", "-v", "error", "-i", str(temp_source), str(destination)],
            check=True,
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to decode GrandOrgue sample: {member_name}") from exc
    finally:
        temp_source.unlink(missing_ok=True)


def write_grandorgue_bank_sfz(destination_root: Path, sfz_name: str, layers: list[tuple[str, float]]) -> None:
    sample_root = destination_root / "Samples"
    lines = [
        "// Generated from Lars Palo's Burea Church GrandOrgue sample set (CC BY-SA 2.5 Sweden).",
        "// This bank is a simplified stop blend for AI Organ and is intended for local testing.",
        "",
    ]

    for stop_name, gain_db in layers:
        stop_dir = sample_root / stop_name
        for sample_file in sorted(stop_dir.glob("*.wav")):
            midi_note = midi_from_sample_filename(sample_file.name)
            if midi_note is None:
                continue
            rel_path = sample_file.relative_to(destination_root).as_posix()
            lines.append(
                f"<region> sample={rel_path} key={midi_note} pitch_keycenter={midi_note} volume={gain_db:.2f}"
            )

    (destination_root / sfz_name).write_text("\n".join(lines) + "\n", encoding="utf-8")


def prepare_grandorgue_package(
    root: Path,
    package_url: str,
    archive_name: str,
    destination_subdir: str,
    banks: dict[str, list[tuple[str, float]]],
    notice_lines: list[str],
    extra_names: tuple[str, ...],
) -> None:
    destination_root = root / destination_subdir
    archive_path = root / "_downloads" / archive_name
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    if not archive_path.exists():
        download_to(package_url, archive_path)

    selected_stops = sorted({stop for layers in banks.values() for stop, _ in layers})
    marker = destination_root / ".prepared"
    if not marker.exists():
        if destination_root.exists():
            shutil.rmtree(destination_root)
        samples_root = destination_root / "Samples"
        samples_root.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(archive_path) as archive:
            for member_name in archive.namelist():
                member_path = Path(member_name)
                if len(member_path.parts) != 2 or member_path.suffix.lower() != ".wav":
                    continue

                stop_name = member_path.parts[0]
                if stop_name not in selected_stops:
                    continue

                destination = samples_root / stop_name / member_path.name
                convert_wavpack_member(archive, member_name, destination)

            for extra_name in extra_names:
                if extra_name in archive.namelist():
                    (destination_root / extra_name).write_bytes(archive.read(extra_name))

        notice = "\n".join(notice_lines)
        (destination_root / "NOTICE.txt").write_text(notice + "\n", encoding="utf-8")
        marker.write_text(package_url, encoding="utf-8")

    for sfz_name, layers in banks.items():
        write_grandorgue_bank_sfz(destination_root, sfz_name, layers)


def download_grandorgue_burea(root: Path) -> None:
    prepare_grandorgue_package(
        root,
        GRANDORGUE_BUREA_URL,
        GRANDORGUE_BUREA_ARCHIVE,
        GRANDORGUE_BUREA_SUBDIR,
        GRANDORGUE_BUREA_BANKS,
        [
            "Source: Lars Palo - Burea Church GrandOrgue sample set",
            f"Download: {GRANDORGUE_BUREA_URL}",
            "License: Creative Commons Attribution-ShareAlike 2.5 Sweden",
            "Original organ page: https://familjenpalo.se/vpo/about-burea-church/",
            "",
            "This cache only contains the extracted stop subset used to build AI Organ test banks.",
        ],
        ("BureaChurch.organ", "BureaChurchExtended.organ", "organindex.ini"),
    )


def download_grandorgue_pitea(root: Path) -> None:
    prepare_grandorgue_package(
        root,
        GRANDORGUE_PITEA_URL,
        GRANDORGUE_PITEA_ARCHIVE,
        GRANDORGUE_PITEA_SUBDIR,
        GRANDORGUE_PITEA_BANKS,
        [
            "Source: Lars Palo - Pitea MHS GrandOrgue sample set",
            f"Download: {GRANDORGUE_PITEA_URL}",
            "License: Creative Commons Attribution-ShareAlike 2.5",
            "Original organ page: https://familjenpalo.se/vpo/pitea-mhs/",
            "",
            "This cache only contains the extracted stop subset used to build AI Organ test banks.",
        ],
        ("PiteaMHS20250727.organ", "PiteaMHS20250727-not-remapped-organ.organ", "organindex.ini"),
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch open acoustic sample subsets for AI Music Studio native VSTs.")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="Destination cache directory.")
    parser.add_argument("--clean", action="store_true", help="Remove the destination before downloading.")
    parser.add_argument(
        "--include-grandorgue-organ",
        action="store_true",
        help="Also download Lars Palo's Burea Church GrandOrgue organ package and generate AI Organ SFZ banks.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    root = args.root.resolve()
    if args.clean and root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True, exist_ok=True)

    print(f"Fetching open instrument samples into {root}")
    download_sso_tree(root)
    download_bass_tree(root)
    for url, subdir, archive_name in ARCHIVES:
        extract_archive(url, subdir, archive_name, root)
    if args.include_grandorgue_organ:
        download_grandorgue_burea(root)
        download_grandorgue_pitea(root)
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
