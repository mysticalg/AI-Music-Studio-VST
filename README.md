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
- `AI Drum Machine`
- `AI 808 Machine`
- `AI Bass Synth`
- `AI TB303`
- `AI String Synth`
- `AI Lead Synth`
- `AI Pad Synth`
- `AI Pluck Synth`
- `AI Sampler`
- `AI VEC1 Drum Pads`
- `AI Piano`
- `AI Strings`
- `AI Choir`
- `AI Violin`
- `AI Flute`
- `AI Saxophone`
- `AI Bass Guitar`
- `AI Organ`

The packaged variants use flavor-specific defaults. `AI Drum Machine` is now voiced as a punchier 909-style kit, `AI 808 Machine` adds longer analogue-style low-end drums, and `AI TB303` adds a more resonant acid-bass flavor. The sampler variant adds internal sample-bank playback with loop-window controls, so it behaves like a compact ROMpler/sampler without depending on external content. The acoustic suite now covers `AI Piano`, `AI Strings`, `AI Choir`, `AI Violin`, `AI Flute`, `AI Saxophone`, `AI Bass Guitar`, and `AI Organ`: piano uses the bundled Splendid Grand library, and the others can load open multisample libraries from `.cache/OpenInstrumentSamples` for real SFZ-based playback.

## Fetch acoustic sample libraries

Run this once from the plugin repo root to populate `.cache/OpenInstrumentSamples` with the open sample sets used by the acoustic plugins:

```bash
python scripts/fetch_open_instrument_samples.py
```

That script pulls a sparse subset of Sonatina Symphonic Orchestra for choir / strings / violin / flute, the FreePats electric bass repository for bass guitar, and small FreePats archive sets for tenor saxophone and church organ.

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
