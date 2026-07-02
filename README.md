# feedpak format specification

The official, open specification for the **feedpak** file format — an open,
hand-editable package format for interactive music notation: guitar/bass tab, standard
notation, drum tabs, lyrics, vocal pitch, beats, sections, and the audio stems that go
with them. One `.feedpak` holds all the authored data for a single song.

- 🌐 **Rendered site & hosted schemas:** <https://got-feedback.github.io/feedpak-spec/>
- 📖 **Read the spec:** [`spec/feedpak-v1.md`](spec/feedpak-v1.md)
- ✏️ **Hand-editing guide:** [`spec/hand-editing.md`](spec/hand-editing.md) — practical "edit your own pack" companion
- 🧩 **Machine-readable schemas:** [`schemas/`](schemas/) (JSON Schema, Draft 2020-12)
- 📦 **Worked examples:** [`examples/`](examples/)
- ✅ **Reference validator:** [`tools/validate.py`](tools/validate.py)

| | |
|---|---|
| **Specification version** | 1.14.0 |
| **Format major version** | 1 |
| **Status** | Draft |
| **Canonical extension** | `.feedpak` |

## What a feedpak looks like

A feedpak exists in two interchangeable forms — a **directory** (`my-song.feedpak/`) for
authoring and hand-editing, and a **zip archive** (`my-song.feedpak`) for distribution.
Both hold the same files:

```
my-song.feedpak/
├── manifest.yaml             # the index: metadata + pointers to every other file
├── arrangements/
│   └── lead.json             # note/chord data per arrangement
├── stems/
│   └── full.ogg              # audio
├── lyrics.json               # optional side-files, each opted-in from the manifest (the primary lyric track)
├── lyrics_romaji.json        # a transliteration track (lyric_tracks — see spec §5.5)
├── lyrics_en.json            # a translation track (lyric_tracks — see spec §5.5)
└── cover.jpg
```

The design rests on three ideas, spelled out in the spec:

1. **The manifest is the index.** Nothing is discovered by scanning filenames — every file
   is referenced from `manifest.yaml`.
2. **Plain-text first.** YAML for the hand-edited manifest, JSON for data. Audio is OGG/WAV by
   default (the decode baseline), with MP3/FLAC/Opus allowed behind it.
3. **Extensible without breaking readers.** New data is a new side-file plus a new manifest
   key; older readers ignore what they don't recognise.

## Versioning

feedpak has versioning built in, on three independent axes (see
[spec §4](spec/feedpak-v1.md#4-versioning)):

- **Format version** — `feedpak_version` in the manifest, a semver string
  (`"1.0.0"`), with a documented MAJOR/MINOR/PATCH compatibility policy.
- **Side-file schema versions** — each side-file's own integer `version`, independent of
  the format version.
- **Specification-document version** — this published document, frozen per release with a
  git tag.

## Validate a pack

```bash
pip install pyyaml jsonschema
python tools/validate.py path/to/song.feedpak      # zip or directory form
python tools/validate.py examples/minimal.feedpak
```

The validator is also a minimal reference reader: it resolves a pack through its manifest,
checks every pointer, and validates each file against the schemas in [`schemas/`](schemas/).

## Development

```bash
pip install -r requirements-dev.txt
python -m pytest -q          # unit + end-to-end tests for the validator
python -m ruff check tools/ tests/
```

CI (`.github/workflows/validate.yml`) runs the schema meta-check, validates the example packs
(directory and zip form), runs the tests across Python 3.10–3.13, lints, checks that the spec,
README, and `CHANGELOG.md` versions agree, and builds the docs site. On every push to `main` the
docs are published to GitHub Pages, and a GitHub Release is cut automatically for the newest
released `CHANGELOG.md` version if one does not already exist — so a reviewed version bump
releases itself on merge. No manual tagging required.

## License

This repository is dual-licensed so the format stays maximally open:

- **Specification prose and documentation** (`spec/`, `README.md`, `*.md`) are released
  into the public domain under [**CC0 1.0 Universal**](LICENSE). You may implement,
  excerpt, or republish the spec with no restrictions and no obligation to anyone.
- **Schemas, examples, and reference code** (`schemas/`, `examples/`, `tools/`) are
  licensed under the [**MIT License**](LICENSE-CODE).

Attribution is **not required**, but if you build on feedpak a link back to this
repository is appreciated. Suggested citation: *"feedpak format specification, version
1.14.0, https://github.com/got-feedback/feedpak-spec"*.

## Contributing

Proposals to evolve the format are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for the
enhancement-proposal process and the DCO sign-off requirement, and
[GOVERNANCE.md](GOVERNANCE.md) for how versions are decided and cut. Changes are tracked in
[CHANGELOG.md](CHANGELOG.md).
