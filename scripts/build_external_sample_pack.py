#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import struct
from pathlib import Path


PACK_MAGIC = b"AIMSPK01"
MAX_EXTERNAL_PAD_SLOTS = 23
SUPPORTED_EXTENSIONS = {".wav", ".aif", ".aiff", ".flac", ".ogg"}

VEC1_FOLDER_ORDER = [
    "VEC1 Bassdrums",
    "VEC1 Bassdrums",
    "VEC1 Snares",
    "VEC1 Snares",
    "VEC1 Claps",
    "VEC1 Claps",
    "VEC1 Cymbals",
    "VEC1 Cymbals",
    "VEC1 Cymbals",
    "VEC1 Cymbals",
    "VEC1 Cymbals",
    "VEC1 Percussion",
    "VEC1 FX",
    "VEC1 Fills",
    "VEC1 BreakBeats",
    "VEC1 303 Acid",
    "VEC1 Long Basses",
    "VEC1 Offbeat Bass",
    "VEC1 Loops",
    "VEC1 Multis",
    "VEC1 Sounds",
    "VEC1 Special Sounds From Produc",
    "VEC1 Vinyl FX and Scratches",
]

VEC1_PAD_TITLES = [
    "Bassdrum C",
    "Bassdrum C#",
    "Snare D",
    "Snare D#",
    "Clap E",
    "Clap F",
    "Closed HH",
    "Open HH",
    "Ride",
    "Crash",
    "Rev Crash",
    "Perc",
    "FX",
    "Fills",
    "Breaks",
    "303 Acid",
    "Long Bass",
    "Offbeat",
    "Loops",
    "Multis",
    "Sounds",
    "Special",
    "Vinyl FX",
]

VEC1_PAD_NOTES = [
    "C1",
    "C#1",
    "D1",
    "D#1",
    "E1",
    "F1",
    "F#1",
    "G1",
    "G#1",
    "A1",
    "A#1",
    "B1",
    "C2",
    "C#2",
    "D2",
    "D#2",
    "E2",
    "F2",
    "F#2",
    "G2",
    "G#2",
    "A2",
    "A#2",
]

VEC1_PAD_SUBFOLDERS = [
    "",
    "",
    "",
    "",
    "",
    "",
    "VEC1 Close HH",
    "VEC1 Open HH",
    "VEC1 Ride",
    "VEC1 Crash",
    "VEC1 Reverse Crash",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
    "",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a single-file external sample pack for AI Music Studio.")
    parser.add_argument("--layout", choices=("vec1", "vve1"), required=True)
    parser.add_argument("--library-root", required=True)
    parser.add_argument("--library-id", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args()


def is_supported_audio_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS


def sorted_child_directories(folder: Path) -> list[Path]:
    directories: list[Path] = []
    for child in folder.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        lower_name = name.lower()
        if name.startswith(".") or lower_name.startswith("__") or "exs" in lower_name:
            continue
        directories.append(child)
    return sorted(directories, key=lambda item: item.name.lower())


def sorted_audio_files(folder: Path) -> list[Path]:
    return sorted(
        (child for child in folder.iterdir() if is_supported_audio_file(child)),
        key=lambda item: item.name.lower(),
    )


def sorted_audio_files_recursive(folder: Path) -> list[Path]:
    results: list[Path] = []
    results.extend(sorted_audio_files(folder))
    for child in sorted_child_directories(folder):
        results.extend(sorted_audio_files_recursive(child))
    return results


def clean_label(name: str) -> str:
    cleaned = name.strip()
    for prefix in ("VEC1 ", "VVE1 "):
        if cleaned.lower().startswith(prefix.lower()):
            cleaned = cleaned[len(prefix):].strip()
            break
    return cleaned


def clean_sample_name(path: Path) -> str:
    name = path.stem.strip()
    for prefix in ("VEC1 ", "VVE1 "):
        if name.lower().startswith(prefix.lower()):
            name = name[len(prefix):].strip()
            break
    return name


def midi_note_name(midi_note: int) -> str:
    names = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")
    octave = (midi_note // 12) - 2
    return f"{names[midi_note % 12]}{octave}"


def make_sample_entry(root: Path, sample_file: Path, preset_name: str) -> dict[str, object]:
    relative_path = sample_file.relative_to(root).as_posix()
    return {
        "path": relative_path,
        "displayName": clean_sample_name(sample_file),
        "presetName": preset_name,
    }


def build_vec1_pads(root: Path) -> list[dict[str, object]]:
    top_level = {folder.name.lower(): folder for folder in sorted_child_directories(root)}
    pads: list[dict[str, object]] = []

    for index, folder_name in enumerate(VEC1_FOLDER_ORDER):
        top_folder = top_level.get(folder_name.lower())
        pad = {
            "title": VEC1_PAD_TITLES[index],
            "note": VEC1_PAD_NOTES[index],
            "midiNote": 36 + index,
            "samples": [],
        }

        if top_folder is not None:
            subfolders = sorted_child_directories(top_folder)
            preferred_subfolder = VEC1_PAD_SUBFOLDERS[index].strip().lower()

            if preferred_subfolder:
                for subfolder in subfolders:
                    if subfolder.name.lower() != preferred_subfolder:
                        continue
                    for sample_file in sorted_audio_files(subfolder):
                        pad["samples"].append(make_sample_entry(root, sample_file, clean_label(subfolder.name)))
                    break
            else:
                for subfolder in subfolders:
                    for sample_file in sorted_audio_files(subfolder):
                        pad["samples"].append(make_sample_entry(root, sample_file, clean_label(subfolder.name)))

            if not pad["samples"]:
                for sample_file in sorted_audio_files(top_folder):
                    pad["samples"].append(make_sample_entry(root, sample_file, ""))

        pads.append(pad)

    return pads


def build_vve1_pads(root: Path) -> list[dict[str, object]]:
    pads: list[dict[str, object]] = []
    midi_note = 60

    for top_folder in sorted_child_directories(root):
        top_label = clean_label(top_folder.name)
        aggregate_samples = [
            make_sample_entry(root, sample_file, clean_label(sample_file.parent.name))
            for sample_file in sorted_audio_files_recursive(top_folder)
        ]
        pads.append(
            {
                "title": top_label,
                "note": midi_note_name(midi_note),
                "midiNote": midi_note,
                "samples": aggregate_samples,
            }
        )
        midi_note += 1

        for subfolder in sorted_child_directories(top_folder):
            pads.append(
                {
                    "title": clean_label(subfolder.name),
                    "note": midi_note_name(midi_note),
                    "midiNote": midi_note,
                    "samples": [
                        make_sample_entry(root, sample_file, top_label)
                        for sample_file in sorted_audio_files(subfolder)
                    ],
                }
            )
            midi_note += 1

    return pads


def build_pad_manifest(layout: str, root: Path, library_id: str) -> dict[str, object]:
    if layout == "vec1":
        pads = build_vec1_pads(root)
    elif layout == "vve1":
        pads = build_vve1_pads(root)
    else:
        raise ValueError(f"Unsupported layout: {layout}")

    if len(pads) > MAX_EXTERNAL_PAD_SLOTS:
        raise SystemExit(
            f"{library_id} exposes {len(pads)} pads, but the current external-pad engine only supports "
            f"{MAX_EXTERNAL_PAD_SLOTS} slots."
        )

    unique_files: dict[str, dict[str, int]] = {}
    write_order: list[str] = []
    current_offset = 0

    for pad in pads:
        for sample in pad["samples"]:
            relative_path = str(sample["path"])
            if relative_path in unique_files:
                continue
            absolute_path = root / relative_path
            file_size = absolute_path.stat().st_size
            unique_files[relative_path] = {"offset": current_offset, "size": file_size}
            write_order.append(relative_path)
            current_offset += file_size

    manifest_pads: list[dict[str, object]] = []
    for pad in pads:
        manifest_samples: list[dict[str, object]] = []
        for sample in pad["samples"]:
            relative_path = str(sample["path"])
            metadata = unique_files[relative_path]
            manifest_samples.append(
                {
                    "path": relative_path,
                    "displayName": sample["displayName"],
                    "presetName": sample["presetName"],
                    "offset": metadata["offset"],
                    "size": metadata["size"],
                }
            )

        manifest_pads.append(
            {
                "title": pad["title"],
                "note": pad["note"],
                "midiNote": pad["midiNote"],
                "samples": manifest_samples,
            }
        )

    return {
        "format": "AIMS_EXTERNAL_PAD_PACK",
        "version": 1,
        "libraryId": library_id,
        "padCount": len(manifest_pads),
        "sampleFileCount": len(write_order),
        "totalAudioBytes": current_offset,
        "pads": manifest_pads,
        "_writeOrder": write_order,
    }


def write_pack(root: Path, output_path: Path, manifest: dict[str, object]) -> None:
    write_order = list(manifest.pop("_writeOrder"))
    manifest_bytes = json.dumps(manifest, ensure_ascii=True, separators=(",", ":")).encode("utf-8")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("wb") as handle:
        handle.write(PACK_MAGIC)
        handle.write(struct.pack("<Q", len(manifest_bytes)))
        handle.write(manifest_bytes)

        for relative_path in write_order:
            with (root / relative_path).open("rb") as sample_handle:
                while True:
                    chunk = sample_handle.read(1024 * 1024)
                    if not chunk:
                        break
                    handle.write(chunk)


def main() -> None:
    args = parse_args()
    library_root = Path(args.library_root).expanduser().resolve()
    output_path = Path(args.output).expanduser().resolve()

    if not library_root.is_dir():
        raise SystemExit(f"Library root does not exist: {library_root}")

    manifest = build_pad_manifest(args.layout, library_root, args.library_id)
    write_pack(library_root, output_path, manifest)

    print(
        f"Packed {args.library_id}: {manifest['padCount']} pads, "
        f"{manifest['sampleFileCount']} files, {manifest['totalAudioBytes']} bytes -> {output_path}"
    )


if __name__ == "__main__":
    main()
