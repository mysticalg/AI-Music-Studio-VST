# AdvancedVSTi Bundled Instruments (JUCE VST3)

This folder adds a JUCE-based VST instrument scaffold with these implemented blocks:

- Oscillator types: sine, saw, square, noise, sample (internal placeholder sample buffer).
- Unison voice stacking + detune.
- FM operator amount.
- Oscillator hard-sync style reset control.
- Amp and filter ADSR envelopes with logarithmic/exponential shaping.
- Filter modes: low-pass, high-pass, band-pass, notch.
- Two assignable LFOs (pitch and filter assignments in this version).
- Arpeggiator modes: up, down, up/down, random.
- Rhythm gate and per-note oscillator length gate.

The shared source now builds these VST3 products:

- `Virus Synth`
- `AI 909 Drum Machine`
- `AI Bass Synth`
- `AI Lead Synth`
- `AI Pad Synth`
- `AI Pluck Synth`
- `AI Sampler`
- `AI VEC1 Drum Pads`
- `AI Piano`
- `AI Strings`
- `AI Violin`
- `AI Flute`
- `AI Saxophone`
- `AI Bass Guitar`
- `AI Organ`

The packaged lineup has been trimmed to the newer primary instruments rather than overlapping variants. `AI 909 Drum Machine` now carries the drum-machine slot, `AI Bass Synth` covers the mono synth-bass role, and `AI Strings` is the main string-family instrument. The sampler variant adds internal sample-bank playback with loop-window controls, so it behaves like a compact ROMpler/sampler without depending on external content. The acoustic suite now covers `AI Piano`, `AI Strings`, `AI Violin`, `AI Flute`, `AI Saxophone`, `AI Bass Guitar`, and `AI Organ`: piano uses the bundled Splendid Grand library, and the others can load open multisample libraries from `.cache/OpenInstrumentSamples` for real SFZ-based playback.

## Fetch acoustic sample libraries

Run this once from the plugin repo root to populate `.cache/OpenInstrumentSamples` with the open sample sets used by the acoustic plugins:

```bash
python scripts/fetch_open_instrument_samples.py
```

That script pulls a sparse subset of Sonatina Symphonic Orchestra for strings / violin / flute, the FreePats electric bass repository for bass guitar, and small FreePats archive sets for tenor saxophone and church organ.

To try the newer GrandOrgue-based `AI Organ` banks locally, run:

```bash
python scripts/fetch_open_instrument_samples.py --include-grandorgue-organ
```

That downloads Lars Palo's `Burea Church` GrandOrgue package, extracts a curated subset of stops, converts the internal WavPack-compressed samples to PCM `.wav` with `ffmpeg`, and generates four SFZ banks for `Cathedral Principal`, `Soft Stops`, `Bright Mixture`, and `Warm Diapason`. The runtime will prefer those generated banks automatically when they are present. The upstream set is published under `CC BY-SA 2.5`, so treat this as a user-local fetch path rather than content to bundle blindly into installers or releases.

## Fetch TR-909 drum samples

`AI 909 Drum Machine` can now switch to real TR-909 one-shots if a local library is present. The recommended fetch path is:

```bash
python scripts/fetch_tr909_samples.py
```

That downloads the Audiorealism TR-909 pack into `.cache/TR909Samples/Audiorealism/TR-909-44.1kHz-16bit`, which the plugin will discover automatically. You can also point the runtime at another local root with `AI_MUSIC_STUDIO_TR909_LIBRARY`.

Important: the upstream Audiorealism readme says the sample pack may not be redistributed without permission. Treat this as a user-local download step rather than content to bundle into public installers or releases.

## GitHub Pages catalog

This repo now includes a static catalog site in `docs/` that is designed for GitHub Pages. The page:

- shows every bundled instrument in a responsive grid,
- loads real screenshot PNGs from `docs/screenshots/`,
- checks the latest GitHub release at runtime,
- and enables direct **VST3** / **Standalone** download buttons when the matching release assets exist.

The deployment workflow lives at `.github/workflows/deploy-pages.yml`.

## Automated GitHub build + download

This repository includes a GitHub Actions workflow at `.github/workflows/build-vsti.yml` that compiles the bundled VST3 instruments on `windows-latest` and `macos-latest` and uploads downloadable ZIP artifacts.

For durable public downloads, use `.github/workflows/release-vsti.yml`. That workflow:

- builds Windows and macOS release outputs,
- packages every instrument separately,
- creates cross-platform ZIPs for **VST3** and **Standalone**,
- and uploads them to a GitHub release with predictable asset names that the catalog page can discover automatically.

### When it runs

- Pushes affecting the native VST source tree
- Pull requests affecting the native VST source tree
- Manual runs from **Actions > Build Bundled VST3 Instruments > Run workflow**

### How to publish downloads

1. Open **Actions > Release Bundled Instruments**.
2. Run the workflow and provide a tag such as `v0.2.0`, or push a matching Git tag.
3. Wait for the release workflow to finish.
4. The GitHub Pages catalog will then pick up the latest release automatically and enable the matching download buttons.

## Build locally (Windows example)

1. Install JUCE and CMake.
2. Configure:

```bash
cmake -S . -B build -DJUCE_DIR=C:/dev/JUCE
```

3. Build:

```bash
cmake --build build --config Release
```

4. JUCE creates one `*.vst3` bundle per target in the build artifacts.
5. If you are using this repo as the `plugins/AdvancedVSTi` submodule inside AI Music Studio, copy the desired `.vst3` bundles into `../vsti/` from the parent app repo to package them with the app.

## Build a Windows installer

The runtime now looks for shared sample data in this order:

- bundled plugin resources inside the `.vst3` itself,
- `%ProgramData%\AI Music Studio\VSTData\...`,
- and explicit overrides from `AI_MUSIC_STUDIO_VST_DATA_ROOT`, `AI_MUSIC_STUDIO_OPEN_INSTRUMENT_SAMPLES`, `AI_MUSIC_STUDIO_PIANO_LIBRARY`, `AI_MUSIC_STUDIO_VEC1_LIBRARY`, or `AI_MUSIC_STUDIO_TR909_LIBRARY`.

That lets a Windows installer place every plugin in `C:\Program Files\Common Files\VST3` while keeping shared libraries in `%ProgramData%` where the DAW-facing VSTs can still resolve them consistently.

1. Build the Windows release artifacts:

```bash
cmake -S . -B build -DJUCE_DIR=C:/dev/JUCE
cmake --build build --config Release
```

2. Collect the built `.vst3` bundles into the expected packaging layout:

```bash
python scripts/package_platform_builds.py --build-dir build --platform windows --output-dir dist/release-input/windows
```

3. Install [Inno Setup 6](https://jrsoftware.org/isinfo.php) and build the installer:

```bash
python scripts/build_windows_installer.py --package-root dist/release-input/windows --build-dir build --fetch-open-instrument-samples
```

If `AI Piano` or `AI VEC1 Drum Pads` are not already carrying their sample libraries inside the built `.vst3` bundles, pass the source roots explicitly with `--piano-library-dir` and `--vec1-library-dir`, or configure CMake with `-DAIMS_PIANO_LIBRARY_DIR=...` and `-DAIMS_VEC1_LIBRARY_DIR=...` before building.

Use `--skip-compile` if you only want the staged installer layout plus the generated `.iss` file. A successful compiled build writes `AI-Music-Studio-Bundled-Instruments-Windows-Installer-<version>.exe` into `dist/windows-installer/`.

The installer now lets the user choose either the default VST3 target folder (`C:\Program Files\Common Files\VST3`) or a custom VST3 folder during setup. Standalone `.exe` builds still install into `C:\Program Files\AI Music Studio\Standalone\...`, and shared sample libraries still install into `%ProgramData%\AI Music Studio\VSTData`. There is no separate VST3 registration step beyond copying the bundles into the chosen VST3 folder and rescanning plugins in the DAW if needed.

## Build a Windows installer for the FX pack

For the native FX suite, use the dedicated wrapper:

```bash
python scripts/build_windows_fx_installer.py --build-dir build-installer-refresh
```

That script:

- packages the FX `.vst3` bundles into `dist/release-input/windows-fx/`,
- generates an Inno Setup installer in `dist/windows-installer-fx/`,
- defaults plugin installation to `C:\Program Files\Common Files\VST3`,
- and shows the same custom-folder choice page if the user wants a different VST3 location.

Use `--skip-package` if `dist/release-input/windows-fx/` is already staged, or `--skip-compile` if you only want the packaged layout plus the generated `.iss` file.

## Render catalog screenshots locally

If you want to refresh the UI screenshots used by the GitHub Pages catalog, build the optional screenshot exporters and run the helper script:

```bash
cmake -S . -B build-screens -DJUCE_DIR=/path/to/JUCE -DAIMS_BUILD_SCREENSHOT_EXPORTERS=ON
cmake --build build-screens --config Release
python scripts/render_instrument_screenshots.py --build-dir build-screens
```

That writes PNG files into `docs/screenshots/`.

## About `.dll`

Modern plugin hosts typically use **VST3** (`.vst3`). Legacy VST2 `.dll` output is generally not enabled in current JUCE/public SDK workflows.

If you specifically need a `.dll`, use one of:
- a host that supports CLAP/LV2 with bridge tools,
- an older licensed VST2 pipeline,
- or deploy VST3 and rely on host-native support (recommended).
