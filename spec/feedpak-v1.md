<!--
SPDX-License-Identifier: CC0-1.0
This specification text is dedicated to the public domain under CC0 1.0.
The JSON Schemas, examples, and reference code that accompany it are MIT-licensed
(see LICENSE-CODE).
-->

# feedpak Format Specification

- **Specification version:** 1.18.0
- **Format major version:** 1
- **Status:** Draft
- **Date:** 2026-07-20
- **Editors:** The feedpak authors
- **License:** [CC0 1.0 Universal](../LICENSE) (this document)
- **Machine-readable schemas:** [`schemas/`](../schemas/) (MIT)

## Abstract

**feedpak** is an open, hand-editable package format for interactive music notation —
guitar/bass tab, standard notation, drum tabs, lyrics, vocal pitch, beats, sections, and the
audio stems that go with them. A feedpak holds the authored data for a single song. The format
is plain-text-first (YAML index + JSON data), self-describing, and designed to be extended
without breaking existing readers.

This document is the **authoritative reference** for the on-disk format. It is independent of
any single implementation: anyone may read, write, implement, or extend feedpak under the terms
above, with no obligation to any project.

---

## 1. Conformance

### 1.1. Requirement keywords

The key words **MUST**, **MUST NOT**, **REQUIRED**, **SHALL**, **SHALL NOT**, **SHOULD**,
**SHOULD NOT**, **RECOMMENDED**, **MAY**, and **OPTIONAL** in this document are to be
interpreted as described in [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) and
[RFC 8174](https://www.rfc-editor.org/rfc/rfc8174) when, and only when, they appear in all
capitals, as shown here.

### 1.2. Roles

- A **Reader** is any program that opens a feedpak and consumes its data.
- A **Writer** is any program that produces a feedpak.
- A **conformant feedpak** is a package that satisfies every MUST in this document.

A conformant Reader **MUST NOT** reject a feedpak solely because it carries keys, files, or
fields the Reader does not recognise (see [§4, Versioning](#4-versioning) and
[§9, Extending the format](#9-extending-the-format)). Forward-compatibility through ignored-but-
preserved unknown data is a load-bearing property of this format.

### 1.3. What this document does and does not govern

This specification governs the **bytes of the package on disk** — its structure, its files, and
the schemas of those files. It does **not** govern any runtime transport, API, or rendering
behaviour an application layers on top. Where such implementation detail is informative, it is
confined to a clearly-labelled **non-normative** appendix (see [Appendix A](#appendix-a-non-normative--streaming-and-runtime-notes)).

---

## 2. Format at a glance

A feedpak exists in **two interchangeable forms** that hold identical contents:

| Form | What it is | Used for |
|---|---|---|
| **Directory** | A folder named `*.feedpak/` containing the files below | Authoring, hand editing, tooling development |
| **Zip archive** | A `.feedpak` file (a ZIP archive with the same files inside) | Distribution |

A Reader **MUST** accept both forms and **SHOULD** treat them as equivalent. A Reader that
unpacks the zip form to a cache **SHOULD** key that cache on the archive's size and
modification time so a re-packed archive is re-read.

### 2.1. Directory layout

```
my-song.feedpak/
├── manifest.yaml             # REQUIRED — all metadata + the file index
├── arrangements/
│   ├── lead.json             # One JSON per playable arrangement
│   ├── rhythm.json
│   └── bass.json
├── stems/
│   ├── full.ogg              # Mixed audio (single-stem packs); may be absent after stem splitting
│   ├── guitar.ogg            # Optional individual stems
│   ├── bass.ogg
│   ├── drums.ogg
│   ├── vocals.ogg
│   └── other.ogg
├── lyrics.json               # OPTIONAL — syllable-level lyrics (the primary track)
├── lyrics_romaji.json        # OPTIONAL — a transliteration track (lyric_tracks, §5.5)
├── lyrics_en.json            # OPTIONAL — a translation track (lyric_tracks, §5.5)
└── cover.jpg                 # OPTIONAL — album art
```

### 2.2. Three core rules

1. **`manifest.yaml` is the index.** Nothing inside a feedpak is auto-discovered by scanning —
   every consumed file is referenced from the manifest. Readers **MUST NOT** rely on filename
   conventions to locate data; they **MUST** resolve files through the manifest. (Writers MAY
   use the conventional filenames shown here, but Readers MUST follow the manifest's pointers.)
2. **Paths in `manifest.yaml` are POSIX-style relative paths** from the feedpak root: forward
   slashes, no leading `/`, no `..` segments, no empty segments (`//`), no colon (`:`) — which
   excludes drive letters and alternate-data-stream paths — and no backslashes. Readers **MUST**
   reject paths that escape the package root.
3. **YAML for the manifest, JSON (or JSONC) for data files.** The manifest is YAML so it is
   comfortable to hand-edit; all structured data files are JSON (or JSONC, where the `.jsonc`
   extension signals that the file MAY contain `//` line comments and `/* */` block comments).
   A YAML manifest is, by [YAML 1.2](https://spec.yaml.io/main/spec/1.2.2/) rules, valid against the
   JSON-Schema definitions in [`schemas/`](../schemas/) (YAML is a JSON superset for this
   purpose).

---

## 3. Encodings and conventions

- **Text files** (`manifest.yaml`, all `*.json`, all `*.jsonc`) **MUST** be UTF-8 encoded. A
  Writer **SHOULD NOT** emit a byte-order mark.
- **Time** is always expressed in **seconds as a JSON number** (floating point), measured from
  the start of the song's audio. Time fields are named `t` or `time`. Writers **MUST NOT** use
  milliseconds, ticks, or sample counts.
- **Field names** in hot-path data (notes, chords, hits, beats) are deliberately short because
  they may be repeated tens of thousands of times in one file. Writers **MUST NOT** expand
  them. One-off metadata MAY use long, descriptive names.
- **Audio stems** default to OGG (Vorbis) at a quality around `-q:a 5` (size/fidelity balance).
  OGG and WAV together form the **baseline every Reader MUST decode**; other formats MAY be
  carried and are dispatched by file extension (or an explicit `codec` override); see
  [§5.3.2](#532-audio-formats--baseline-dispatch-and-portability) for the full decoder baseline,
  codec-resolution precedence, and portability rule. **Cover art** is JPEG or PNG, conventionally
  square, 500–1500 px on a side.
- **Unknown keys / files / fields** are reserved for forward-compatibility. Readers **MUST**
  ignore them rather than error, and Writers that copy or re-emit a feedpak **SHOULD** preserve
  them verbatim.

---

## 4. Versioning

feedpak distinguishes **three independent version axes**. Conflating them is the most common
mistake when implementing the format, so they are defined separately here.

### 4.1. Format version — `feedpak_version`

The manifest **SHOULD** carry a top-level `feedpak_version` key whose value is a
[Semantic Versioning 2.0.0](https://semver.org/) string (for example `"1.0.0"`). It declares
which version of *this format* the package conforms to.

```yaml
feedpak_version: "1.18.0"
```

- A Writer producing a feedpak that conforms to this document **SHOULD** set
  `feedpak_version: "1.18.0"`. (The optional fields added since 1.0.0 —
  [`authors`](#54-authors) in 1.1.0; the song-level [`tempos`](#74-song_timelinejson) /
  [`time_signatures`](#74-song_timelinejson) plus the per-arrangement
  [`tempos`](#610-per-arrangement-tempo-optional) override in 1.2.0; the per-note bend shape
  [`bt`](#621-bend-shape-bt-bnv) / [`bnv`](#621-bend-shape-bt-bnv) in 1.4.0; the per-note
  teaching marks [`fg`](#622-teaching-marks-fg-ch-sd) / [`ch`](#622-teaching-marks-fg-ch-sd) /
  [`sd`](#622-teaching-marks-fg-ch-sd) in 1.5.0; and the per-chord harmony annotations
  [`fn`](#631-harmonic-function-fn) / [`voicing`](#66-chord-templates) in 1.7.0; and the
  template harmony descriptors [`caged`](#66-chord-templates) / [`guideTones`](#66-chord-templates)
  in 1.8.0; and the engine-agnostic rig library ([`rigs`](#79-rigsjson) side-file plus the
  arrangement [`tones.base_rig`](#69-tones-optional) / [`tones.changes[].rig`](#69-tones-optional)
  references) in 1.13.0 — are all additive, so an older Reader simply ignores what it does not recognise.
  1.3.0 added no on-disk field. 1.6.0 adds no new manifest
  key or note/side-file field either, but it does newly permit the `.jsonc` data-file extension
  (see [§8](#8-reading-and-writing)): such files MAY contain comments that a Reader **MUST** strip,
  so — unlike the additive fields above — a comment-bearing `.jsonc` file requires a JSONC-aware
  Reader rather than being silently ignorable. 1.9.0 adds the optional stem
  [`codec`](#53-stems) hint and broadens audio beyond OGG behind a MUST-decode baseline; a pack
  that stays within the baseline is unaffected, while one that carries a non-baseline stem
  format requires a Reader that supports it — the same opt-in shape as `.jsonc`, per the
  [§4.2 carve-out](#42-compatibility-policy). 1.10.0 adds the optional song-level
  [`harmony`](#78-harmonyjson) side-file (intended chord progression) — additive, an older Reader
  simply ignores the manifest key and file. 1.11.0 adds the optional multi-lingual keys — top-level
  [`language`](#51-top-level-keys), the per-stem [`language`](#53-stems) hint, and the
  [`lyric_tracks`](#55-lyric_tracks) list (original / transliteration / translation lyric tracks) —
  all additive, an older Reader ignores them and still loads the single [`lyrics`](#71-lyricsjson)
  pointer as before. 1.12.0 adds the optional album-grouping / genre keys —
  [`album_artist`](#51-top-level-keys), [`track`](#51-top-level-keys), [`disc`](#51-top-level-keys),
  and [`genres`](#51-top-level-keys) — all additive, an older Reader ignores them. 1.14.0 adds the
  optional recording-identity keys — [`mbid`](#51-top-level-keys) and [`isrc`](#51-top-level-keys) —
  additive, an older Reader ignores them. 1.15.0 adds no manifest key at all: it reserves the
  stem id [`full`](#the-full-stem--the-complete-mixdown) for the complete mixdown and asks Writers
  to retain that entry, `default: false`, after separating a pack into per-instrument stems. It is
  safe for an older Reader that honours [`default`](#53-stems) — normative since 1.0.0 — which is
  precisely why the retained entry is specified as `default: false`. 1.16.0 adds the optional
  per-stem display fields [`name`](#53-stems) / [`description`](#53-stems) — purely
  presentational, an older Reader ignores them and keeps showing the stem `id` — and tightens
  the retention of [`full`](#the-full-stem--the-complete-mixdown) after separation from a SHOULD
  to a MUST, scoped to packs declaring 1.16.0 or newer, so no earlier pack becomes
  non-conformant. 1.17.0 adds **drums as arrangements** — the arrangement `type` value
  [`drums`](#52-arrangements) and an optional per-arrangement [`drum_tab`](#52-arrangements)
  pointer, so a pack can carry more than one drum chart; additive, an older Reader keeps reading
  the single song-level [`drum_tab`](#51-top-level-keys) and ignores the extra parts. 1.18.0 adds MIDI-voiced **sound sources** to the rig model — the reserved
  realization engine [`soundfont`](#79-rigsjson), the reserved block role [`source`](#79-rigsjson),
  the normative-when-present [`intent.gm`](#79-rigsjson) General-MIDI floor, and the manifest
  binding keys (arrangement-entry [`tones`](#52-arrangements), top-level
  [`drum_tones`](#51-top-level-keys)) — all additive, an older Reader ignores them.)
- If `feedpak_version` is **absent**, a Reader **MUST** treat the package as `"1.0.0"`. (This
  makes every package authored before the field existed a valid 1.0.0 package.)
- The value **MUST** be a valid semver string when present. A Reader **MUST** reject a value
  that is not parseable as semver, or **MAY** fall back to treating the package as `"1.0.0"`
  with a logged warning.

### 4.2. Compatibility policy

Changes to the format are released under semver semantics, applied to `feedpak_version`:

| Change | Bump | Meaning |
|---|---|---|
| **MAJOR** (`2.0.0`) | breaking | Required structure or semantics changed. Existing packages may need regeneration. |
| **MINOR** (`1.1.0`) | additive | New OPTIONAL manifest keys or side-files. Older Readers keep working by ignoring them. |
| **PATCH** (`1.0.1`) | editorial | Clarifications, fixed wording, metadata-only adjustments. No schema change. |

**Reader rules.** A Reader that supports feedpak major version *X*:

- **MUST** accept any package whose declared major version is *X*, regardless of its minor or
  patch (it ignores unknown minor additions per [§1.2](#12-roles)) — with the single exception that
  a package which *uses* an opt-in file-format relaxation the Reader does not implement (see the
  carve-out below) **MAY** be rejected with a clear error. This MUST-accept guarantee otherwise
  holds for all ordinary additive minor/patch changes.
- **SHOULD** warn, and **MAY** refuse with a clear error, when a package declares a major
  version **greater** than *X*.
- **MAY** accept a package whose major version is **less** than *X*, applying the
  backward-compatibility provisions this document defines.

**Writer rules.** A Writer **MUST NOT** introduce a backward-incompatible structural change
without bumping the **major** version. Additive changes (new optional keys/files) **MUST** be
released as a **minor** bump and **MUST** be safe for an older Reader to ignore.

**Carve-out: opt-in file-format relaxations.** One narrow class of change is released as a
**minor** bump even though an older Reader cannot transparently ignore it: an *opt-in relaxation
of how a file is encoded* — a data file's text, or a stem's audio codec — that a pack uses only
if it chooses to. Two such relaxations exist
in this document:

1. The [`.jsonc` extension](#8-reading-and-writing) (1.6.0), whose files may contain comments a
   Reader **MUST** strip.
2. [Audio stem formats beyond OGG](#532-audio-formats--baseline-dispatch-and-portability)
   (1.9.0): any stem not encoded as OGG (Vorbis). 1.9.0 both widens the MUST-decode baseline from
   OGG alone to **OGG + WAV** and allows further formats above it (FLAC, Opus, …). Because OGG was
   the only format guaranteed before 1.9.0, a Reader predating 1.9.0 may not decode even a baseline
   WAV stem, and no Reader is ever required to decode the above-baseline formats.

The justification for keeping each minor rather than major is that they are **strictly opt-in and
per-file**: a pack that does not adopt `.jsonc` — and a `.jsonc` file with no comments — is
byte-for-byte ordinary JSON every Reader handles; likewise a pack whose stems are all OGG is
decodable by every Reader regardless of version. Only a pack that *actually uses* a relaxation (a
comment-bearing `.jsonc` file, or a non-OGG stem with no OGG alternative) requires a Reader
supporting a later version — a 1.9.0 Reader for a WAV-only pack, or a Reader that opted into the
above-baseline format otherwise. A Writer wanting maximum cross-version compatibility therefore
**SHOULD** include an OGG stem. This is therefore an explicit, bounded exception both to the "older Readers keep working by
ignoring them" rule and to the **Reader rule** that a major-*X* Reader MUST accept any *X.y.z*
package (a Reader **MAY** reject a package that uses a relaxation it does not implement). It is
**not** a general license to add un-ignorable changes under a minor bump; any
future relaxation of this kind **MUST** be opt-in and per-file in the same way, or else be released
as a **major** bump. A Writer that needs maximum Reader compatibility **SHOULD NOT** rely on the
relaxation (for `.jsonc`: keep data files as comment-free `.json`).

### 4.3. Side-file schema versions

Several side-files carry their own integer `version` field at their top level
(`lyrics`/`vocal_pitch`/`song_timeline`/`drum_tab`/`notation_<id>` — see [§7](#7-side-files)).
These are **per-file schema versions** and are **orthogonal** to `feedpak_version`:

- They are plain integers (`1`, `2`, …), not semver, and start at `1`.
- They are bumped only when *that file's* entry shape changes incompatibly.
- A Reader **MUST NOT** assume any relationship between a side-file's `version` and the
  package's `feedpak_version`. Every new **object-shaped** side-file **SHOULD** include
  `"version": 1`. `lyrics.json` is the one exception — it is a flat array retained for
  backward compatibility and carries no `version` field (see [§7.1](#71-lyricsjson)).

### 4.4. Specification-document version

This published document has its own version (shown in the header, e.g. `1.0.0`) tracking the
prose, schemas, and examples. It matches the format `major.minor` it describes. Major revisions
of the format are published as new documents (`spec/feedpak-v2.md`); minor and patch revisions
update this document in place and are recorded in [`CHANGELOG.md`](../CHANGELOG.md). Each
published version is frozen with a git tag (`v1.0.0`).

---

## 5. `manifest.yaml`

The manifest is the only REQUIRED file. It carries the song's metadata and indexes every other
file in the package.

Minimal valid manifest:

```yaml
feedpak_version: "1.0.0"
title: "Black Hole Sun"
artist: "Soundgarden"
duration: 320.5
arrangements:
  - id: lead
    name: Lead
    file: arrangements/lead.json
    tuning: [0, 0, 0, 0, 0, 0]
    capo: 0
stems:
  - id: full
    file: stems/full.ogg
    default: true
```

### 5.1. Top-level keys

| Key | Type | Required | Description |
|---|---|---|---|
| `feedpak_version` | string (semver) | SHOULD | Format version the package conforms to (see [§4.1](#41-format-version--feedpak_version)). Absent ⇒ `"1.0.0"`. |
| `title` | string | **yes** | Song title. |
| `artist` | string | **yes** | Artist name. |
| `album` | string | no | Album. |
| `album_artist` | string | no | Album artist for the release. Used to group multi-artist / **compilation** albums under one album identity. Absent ⇒ falls back to `artist`. |
| `year` | int | no | Release year. |
| `track` | int | no | 1-based track number within the album, for album playback order. Absent ⇒ order is unspecified (a consumer MAY fall back to a filename/title heuristic or the user's own ordering). |
| `disc` | int | no | 1-based disc number for a multi-disc release. Absent ⇒ `1`. |
| `genres` | list | no | Zero or more genre labels (strings), most specific first; a consumer treats `genres[0]` as the primary genre. Free-form, but authors SHOULD prefer common, normalized names. Absent ⇒ unspecified. |
| `mbid` | string (UUID) | no | [MusicBrainz](https://musicbrainz.org/) **Recording** MBID of the recording this pack transcribes, in lowercase canonical UUID form — an author-set, open, exact identity key. A consumer SHOULD prefer it over free-text `artist`/`title` matching when grouping charts of the same recording or looking up external metadata. Absent ⇒ identity is text-derived. |
| `isrc` | string | no | [International Standard Recording Code](https://isrc.ifpi.org/) of the recording (12 characters, e.g. `USABC2400001`) — an alternate author-set exact identity key for when the MBID is unknown. The stored form is the bare 12-character code: the hyphens in the common display form (`US-ABC-24-00001`) are presentation only and not part of the code, so authors SHOULD strip separators when writing the key and consumers SHOULD strip them before comparing. When both are present and disagree, a consumer SHOULD trust `mbid`. Absent ⇒ unspecified. |
| `language` | string | no | [BCP 47](https://www.rfc-editor.org/info/bcp47) tag for the song's **primary sung language** (e.g. `en`, `ja`, `ko`, `zh-Hans`). Absent ⇒ unspecified (treat as `und`). See [§5.5](#55-lyric_tracks). |
| `authors` | list | no | Human contributors who authored or edited this feedpak (see [§5.4](#54-authors)). Distinct from `artist`. |
| `duration` | number | **yes** | Song length in seconds. |
| `arrangements` | list | **yes** | Playable arrangements (see [§5.2](#52-arrangements)). MUST be non-empty. A notation-only entry still counts as an arrangement — it may omit `file` (see §5.2), but it is not an exception to the non-empty rule. |
| `stems` | list | **yes** | Audio stems (see [§5.3](#53-stems)). MUST be non-empty. |
| `stem_separation` | object | no | Provenance metadata when stems were produced by an automated separation engine. See [§5.3.1](#531-stem_separation). |
| `lyrics` | string (path) | no | Path to a lyrics JSON file (see [§7.1](#71-lyricsjson)). |
| `lyrics_source` | string | no | Origin of the lyrics: `authored`, `transcribed`, or `user`. Absent ⇒ treat as `authored`. See [§7.1](#71-lyricsjson). |
| `lyric_transcription` | object | no | Provenance metadata when lyrics came from an automated transcription engine. See [§7.1.1](#711-lyric_transcription). |
| `lyric_tracks` | list | no | Additional lyric representations — original-script, transliteration, and translation tracks, plus per-language sung originals. See [§5.5](#55-lyric_tracks). |
| `vocal_pitch` | string (path) | no | Path to per-syllable vocal pitch JSON (see [§7.2](#72-vocal_pitchjson)). |
| `pitch_extraction` | object | no | Provenance metadata when vocal pitch was extracted by an automated engine. See [§7.2.1](#721-pitch_extraction). |
| `vocal_pitch_contour` | string (path) | no | Path to a fine-grained pitch-contour JSON (see [§7.3](#73-vocal_pitch_contourjson)). |
| `cover` | string (path) | no | Path to cover image (JPEG/PNG). |
| `preview` | string (path) | no | Path to a short preview audio clip for hover-to-listen UIs. Same audio-format rules as stems ([§5.3.2](#532-audio-formats--baseline-dispatch-and-portability)) — OGG/WAV baseline, other formats allowed behind it. |
| `song_timeline` | string (path) | no | Path to a song-wide beats/sections file (see [§7.4](#74-song_timelinejson)). Takes priority over beats/sections embedded in arrangement JSON. |
| `drum_tab` | string (path) | no | Path to the song-level (primary) drum-tab file (see [§7.5](#75-drum_tabjson)). A pack with more than one drum part carries the extras as `type: drums` [arrangements](#52-arrangements); this key is then the primary drum part's back-compat alias (see [Multiple drum parts](#multiple-drum-parts)). |
| `drum_tones` | object | no | Sound binding for the **song-level (primary)** drum part — same shape as an arrangement entry's `tones` ([§5.2](#52-arrangements)). When the pack carries `type: drums` arrangements, each drum part binds through its entry `tones`, which **takes precedence**; `drum_tones` is the fallback binding for packs without drum arrangements, and a Reader **MUST NOT** apply both to the same part (see [Multiple drum parts](#multiple-drum-parts)). References kit rigs in [`rigs.json`](#79-rigsjson). |
| `keys` | string (path) | no | Path to a key/scale-annotation file (see [§7.7](#77-keysjson)). |
| `harmony` | string (path) | no | Path to a song-level harmony track (intended chord progression; see [§7.8](#78-harmonyjson)). |
| `rigs` | string (path) | no | Path to an engine-agnostic rig library — portable signal chains: effect graphs and, since 1.18.0, MIDI-voiced sound sources (see [§7.9](#79-rigsjson)). |

Any key not listed here is an **extension key** and **MUST** be ignored by Readers that do not
understand it (see [§9](#9-extending-the-format)).

### 5.2. `arrangements[]`

Each entry describes one playable arrangement and points at its JSON file:

```yaml
arrangements:
  - id: lead                     # filesystem-safe stable id, used for filenames
    name: Lead                   # display name
    file: arrangements/lead.json
    tuning: [0, 0, 0, 0, 0, 0]   # six semitone offsets from E A D G B E
    capo: 0
    centOffset: 0.0              # OPTIONAL float, cents; default 0.0
```

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | string | — | **REQUIRED.** Stable, filesystem-safe, lowercase identifier; used in filenames and referenced by consumers. |
| `name` | string | `id` | Display name. |
| `file` | string (path) | — | Path to the arrangement JSON (see [§6](#6-arrangement-json)). MAY be omitted only when `notation` or `drum_tab` is present (see below). |
| `tuning` | int[] | `[0,0,0,0,0,0]` | Semitone offsets from standard `E2 A2 D2 G3 B3 E4`. Six elements is the standard 6-string-guitar convention; lengths **4–8** are accepted (4–6 = bass, 6–8 = extended-range guitar; length 6 is shared). Readers **MUST NOT** hard-code length 6. |
| `capo` | int | `0` | Capo fret. |
| `centOffset` | number | `0.0` | Pitch-shift in cents. Common values: `-1200.0` (one octave down for extended-range bass), small non-zero values for non-A440 reference pitch (e.g. A443 ≈ `+11.8`). |
| `type` | string | — | OPTIONAL instrument hint (`guitar`, `bass`, `piano`, `violin`, `drums`, …). The value `drums` marks a **drum part**: its chart is a `drum_tab` (below), never a fretted `file` or `notation`, and it **MUST NOT** be selected or graded as a pitched/fretted arrangement. |
| `notation` | string (path) | — | OPTIONAL path to a standard-notation file for this arrangement (see [§7.6](#76-notation_idjson)). When present, `file` MAY be omitted and the arrangement is notation-only. |
| `drum_tab` | string (path) | — | OPTIONAL path to a per-arrangement [drum-tab file](#75-drum_tabjson), the same file shape the song-level [`drum_tab`](#75-drum_tabjson) key points at. Its presence makes the entry a **drum part** (`type` SHOULD be `drums`); `file` and `notation` are then omitted. A pack MAY carry several drum-part arrangements (e.g. two drummers, or an aux-percussion layer) — see [§7.5](#75-drum_tabjson) for how they relate to the song-level `drum_tab`. |
| `tones` | object | — | OPTIONAL sound binding for this arrangement — same shape as the arrangement JSON's [`tones`](#69-tones-optional) (§6.9): `base`, `base_rig`, `changes[]`, referencing rig ids in [`rigs.json`](#79-rigsjson). Available whether or not the arrangement has a `file` (notation-only and drum-part entries included). See the precedence rule below. |

Manifest-level `tuning`, `capo`, and `centOffset` **override** any equivalents embedded inside
the arrangement JSON; the in-JSON values are fallbacks. The same direction applies to `tones` —
and **wholesale**: when an arrangement entry carries `tones`, it **replaces the arrangement
JSON's `tones` object entirely** (no field-level merge); the in-JSON `tones` is the fallback
when the entry carries none. A Writer **SHOULD NOT** emit both.

### 5.3. `stems[]`

```yaml
stems:
  - id: full             # RESERVED — the complete mixdown (see below)
    file: stems/full.ogg
    default: false       # retained after separation, but never summed with the stems below
  - id: guitar
    file: stems/guitar.ogg
    default: true        # plays by default when the song opens
  - id: drums
    file: stems/drums.ogg
    default: true
  - id: click
    file: stems/click.ogg
    name: "Click"        # OPTIONAL display label; Readers fall back to `id` when absent
    description: "Metronome click with 4-count lead-in."
    default: false
```

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | string | — | **REQUIRED.** Stable identifier referenced by consumers. The id `full` is **RESERVED** for the complete mixdown — see [the `full` stem](#the-full-stem--the-complete-mixdown) below. |
| `file` | string (path) | — | **REQUIRED.** Path to the audio file. |
| `name` | string | `id` | OPTIONAL short display label for mixers and stem lists. Absent ⇒ a Reader falls back to the `id` (the same rule as [`arrangements[].name`](#52-arrangements)). |
| `description` | string | — | OPTIONAL free-form text saying what the stem *is* (e.g. a click track's count-in and BPM, or which take an alternate backing track carries). A Reader **MAY** surface it (tooltip, detail line) and **MAY** ignore it. |
| `codec` | string | — | OPTIONAL codec hint (e.g. `"vorbis"`, `"opus"`, `"pcm"`, `"mp3"`, `"flac"`). When absent, the codec is inferred from the file extension; when present it **overrides** the extension (see [§5.3.2](#532-audio-formats--baseline-dispatch-and-portability)). Its main use is disambiguating an extension that doesn't pin the codec (container ≠ codec), but it MAY be set redundantly to be explicit. |
| `language` | string | — | OPTIONAL [BCP 47](https://www.rfc-editor.org/info/bcp47) tag for a language-specific vocal stem (e.g. a `vocals_ja` stem with `language: ja` and a `vocals_en` stem with `language: en` for a song with two sung-language recordings). Absent ⇒ untagged — an instrumental stem or a stem whose language is unspecified. A [`lyric_tracks`](#55-lyric_tracks) entry's `stem` pointer pairs lyrics with the stem they were sung on. |
| `default` | boolean | `false` | Whether this stem is enabled when the song opens. |

`name` and `description` are presentational only — they carry **no semantics**. The `id`
remains the stable key consumers reference (and the only field with a reserved value); a
`name` on the `full` stem changes none of the rules below.

`default` is logically boolean. For hand-edited convenience, Readers **MUST** also accept the
case-insensitive strings `"true"`/`"false"`, `"on"`/`"off"`, and `"yes"`/`"no"`, mapping them to
the obvious boolean. Writers **SHOULD** emit a real boolean or `"on"`/`"off"`.

`stems` **MUST** be non-empty. Beyond that, no entry is guaranteed to be present and no filename
is required — a Reader **MUST** resolve every stem through the manifest rather than by scanning
for conventional names ([§2.2](#22-three-core-rules)). Exactly one `id` carries normative
meaning, and it is the subject of the next section.

#### The `full` stem — the complete mixdown

The stem id `full` is **RESERVED**. A stem with `id: full` **MUST** be the song's complete
mixdown — the entire song in one file, as heard before any source separation. A Writer **MUST
NOT** use the id `full` for anything else (a "full drum kit" stem is `drums`, not `full`).

A freshly converted pack typically carries `full` as its only stem. When a Writer separates that
mixdown into per-instrument stems (`guitar`, `bass`, `drums`, `vocals`, `other`, `piano`, …), it
**MUST** — for packs declaring `feedpak_version` 1.16.0 or newer; **SHOULD** for packs declaring
an earlier version — retain the `full` entry alongside them, with `default: false`. Source separation is
lossy: summing the per-instrument stems does **not** reproduce the mixdown. The `full` stem is
therefore the only way a Reader can play the song exactly as it was recorded, and a pack that
discards it has thrown away audio it cannot rebuild. Retaining it costs one more file and no new
manifest surface, and consumers rely on it — a Reader that plays `full` at unity gain to avoid
the separation loss (below) silently degrades to the lossy recombination on any pack that dropped
it.

The obligation is scoped to the pack's own version, as stated in the rule itself: the MUST binds
a Writer producing a pack at `feedpak_version` **1.16.0 or newer**. Before 1.16.0 the rule was a
`SHOULD`, so a pack authored
under an earlier version that separated without retaining `full` remains conformant to the version
it declares — nothing is retroactively invalidated. (This is not a requirement to *manufacture* a
mixdown: it binds only the act of *separating* one, where the mixdown provably existed a moment
earlier. A pack of real recorded multitrack stems, never separated from a single mix, is not
covered.)

**`full` is a mixdown, not a layer.** When a pack carries `full` *and* per-instrument stems:

- A Reader that sums stems into one mix **MUST NOT** include `full` in that sum. It already
  contains every instrument; summing it doubles the entire song, and muting `guitar` still
  leaves the guitar audible inside it.
- A Reader that presents a per-stem mixer **SHOULD NOT** offer `full` as an instrument channel.
- A Reader **SHOULD** prefer `full` over the summed per-instrument stems whenever every
  instrument stem is audible at unity gain — it is the same mix, without the separation loss.

This is safe for a Reader written before this rule existed, because the retained entry carries
`default: false` and honouring `default` has been normative since 1.0.0: a Reader that respects
`default` does not play `full` on open, whatever else it does with the list. A Reader that sums
every stem regardless of `default` was already mis-reading the format, and such a Reader is the
reason a Writer **MUST NOT** mark `full` `default: true` in a pack that also ships per-instrument
stems.

#### 5.3.1. `stem_separation`

When stems were produced by an automated source-separation engine, an OPTIONAL top-level
`stem_separation` object records the provenance:

```yaml
stem_separation:
  engine: demucs           # stable engine id
  model: htdemucs_6s       # engine-specific model name
  version: "1.0.0"         # semver for the stem-artifact contract
```

| Field | Type | Notes |
|---|---|---|
| `engine` | string | Stable identifier for the separation engine. |
| `model` | string | Engine-specific model id used for this split. |
| `version` | string (semver) | Version of the producer's stem-artifact contract, independent of the upstream engine version. Bump: patch = metadata-only, minor = backward-compatible additions, major = stem set / packaging / post-processing changed and existing splits should be regenerated. |

Omitted for single-stem packs and for hand-recorded or hand-edited stems. The three fields
together form a natural cache key: a consumer regenerating stems can treat any change among
them as a cache miss.

#### 5.3.2. Audio formats — baseline, dispatch, and portability

**Codec resolution (precedence).** A Reader determines a stem's codec in this order:

1. the explicit [`codec`](#53-stems) field, if present (it **overrides** the extension); else
2. the file extension (`.ogg` → Vorbis, `.opus` → Opus, `.wav` → PCM, `.mp3` → MP3, `.flac` → FLAC).

`codec` exists precisely for the cases where the extension is ambiguous or doesn't pin the codec
(a container that can hold more than one codec). A Reader decodes the formats it supports; for one
it does not, it **MUST** surface a clear error or fall back to another stem — it **MUST NOT** fail
silently into dead air.

**Decoder baseline.** A conformant Reader **MUST** decode:

- **OGG (Vorbis)** — `.ogg`
- **WAV (PCM)** — `.wav`

and **SHOULD** decode **MP3** (`.mp3`), **FLAC** (`.flac`), and **Opus** (`.opus`). These are
the recommended, broadly-portable formats; FLAC/WAV suit lossless masters, Opus/Vorbis/MP3 suit
compressed delivery.

**Portability rule.** A pack intended for distribution **MUST** include at least one stem whose
**resolved codec** (per the precedence above — `codec` override, else extension) is in the
MUST-decode baseline (in practice, an OGG or WAV `full` mix). The resolved codec, not the file
extension alone, is what counts: a stem declaring `file: stems/full.wav` with `codec: mp3` is an
MP3 stem and does **not** satisfy the baseline. Stems in any other
format are **opportunistic enhancements** layered on top of that guaranteed-playable baseline, so
a leaner Reader always has something to play. A Writer that controls its target environment **MAY**
omit the baseline stem, but such a pack is not portable and a Reader **MAY** reject it with a
clear error (see the [§4.2 opt-in carve-out](#42-compatibility-policy)).

**Other / proprietary formats (e.g. WEM).** The format is codec-agnostic enough that a Reader
**MAY** decode an extension outside the recommended set (for instance a desktop build that bundles
a decoder for Wwise `.wem`) — but such formats are **NOT** part of the baseline, **MUST NOT** be
the only stem in a distributable pack (the portability rule still applies), and this document
ships **no** reference decoder for them. Relying on a non-recommended format makes a pack
playable only on Readers that opted into it.

### 5.4. `authors[]`

An OPTIONAL top-level `authors` list credits the **people who authored or edited this feedpak** —
whoever transcribed the chart, arranged it, mixed the stems, or hand-corrected the data. This is
**distinct from `artist`**, which names the recording artist / musician who performed the song;
both MAY be present.

```yaml
authors:
  - name: Jane Smith            # display name or handle
    role: transcriber
    email: jane@example.com
    url: https://janesmith.dev
  - name: Bob Lee
    role: editor
```

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | string | — | **REQUIRED.** Contributor's name or handle. |
| `role` | string | — | OPTIONAL. What they contributed. The value is free-form and a Reader **MUST** accept any string; the RECOMMENDED vocabulary is `transcriber`, `arranger`, `charter`, `editor`, `mixer`, `engineer`, and `proofreader`. |
| `email` | string | — | OPTIONAL. Contact email. |
| `url` | string | — | OPTIONAL. Profile or homepage URL. |

When an entry omits `role`, a consumer **SHOULD** treat the contribution as unspecified rather
than infer one. The `authors` key is OPTIONAL: a pack with no contributor metadata simply omits
it, and a Reader that does not understand it ignores it per [§1.2](#12-roles).

### 5.5. `lyric_tracks[]`

An OPTIONAL top-level `lyric_tracks` list carries **multiple lyric representations** of a song so a
global audience can read along in the original script, a transliteration (romaji, pinyin, …), or a
translation — and so a song released with more than one sung-language recording can pair each
vocal with its own lyrics. Each entry points at a lyrics file that uses the **same flat-array shape
as [`lyrics.json`](#71-lyricsjson)** (the file schema is unchanged; only the manifest grows):

```yaml
language: ja                    # the song's primary sung language (§5.1)
lyrics: lyrics.json             # the legacy single pointer — kept for old Readers
lyric_tracks:
  - id: ja
    file: lyrics.json           # may reuse the same file the `lyrics` pointer names
    language: ja
    kind: original
    stem: vocals_ja
  - id: romaji
    file: lyrics_romaji.json
    language: ja-Latn
    kind: transliteration
  - id: en
    file: lyrics_en.json
    language: en
    kind: translation
```

| Field | Type | Default | Notes |
|---|---|---|---|
| `id` | string | — | **REQUIRED.** Stable, filesystem-safe, lowercase identifier for this track. |
| `file` | string (path) | — | **REQUIRED.** Path to a lyrics file in the [`lyrics.json`](#71-lyricsjson) flat-array shape. Two entries MAY name the same file (e.g. a `kind: original` track and the legacy `lyrics` pointer). |
| `language` | string | — | **REQUIRED.** [BCP 47](https://www.rfc-editor.org/info/bcp47) tag for this track's text. Use a script subtag for a transliteration (e.g. `ja-Latn` romaji, `zh-Latn` pinyin). |
| `kind` | string | — | **REQUIRED.** One of `original` (the sung lyrics in their own language/script), `transliteration` (a phonetic re-spelling of an original, typically sharing its timing 1:1), or `translation` (the meaning in another language, for reading rather than precise sing-along). A Reader **MUST** accept these three and **SHOULD** treat any other value as `translation`. |
| `lyrics_source` | string | `authored` | OPTIONAL origin of this track: `authored`, `transcribed`, or `user` — same vocabulary as the manifest [`lyrics_source`](#71-lyricsjson). |
| `lyric_transcription` | object | — | OPTIONAL `{engine, model, version}` provenance when this track was machine-produced (transcribed or machine-translated) — same shape and semver semantics as [`stem_separation`](#531-stem_separation) and [`lyric_transcription`](#711-lyric_transcription). |
| `stem` | string | — | OPTIONAL id of the [`stems[]`](#53-stems) entry this track's lyrics were sung on — pairs a per-language sung `original` with its vocal recording. Omitted for transliteration/translation tracks, which ride the original performance. |
| `name` | string | `id` | OPTIONAL display label. |

**Relationship to the single `lyrics` pointer.** The [`lyrics`](#71-lyricsjson) /
[`lyrics_source`](#71-lyricsjson) / [`lyric_transcription`](#711-lyric_transcription) keys are
unchanged and remain valid on their own. When `lyric_tracks` is **absent**, a Reader behaves
exactly as before. When `lyric_tracks` is **present** it is authoritative for multi-track display,
and a Writer **SHOULD** also set `lyrics` to point at the `file` of the `kind: original` track whose
`language` matches the song's primary [`language`](#51-top-level-keys) — pointing at the same file,
not a copy — so a Reader predating 1.11.0 still shows lyrics. A Reader that understands
`lyric_tracks` **MAY** ignore the `lyrics` pointer when the list is present.

**No new file schema.** Each track is an ordinary [`lyrics.json`](#71-lyricsjson) array: a
transliteration track typically mirrors the original's syllable timing 1:1, while a translation
track carries its own (looser, reading-oriented) timing. The [§7.1](#71-lyricsjson) rule that
`lyrics.json` is a versionless flat array is preserved for every track. Per-track vocal pitch is
out of scope for this version (the melody is largely language-independent); a future version MAY
add it.

`lyric_tracks` is OPTIONAL; a Reader that does not understand it ignores it per [§1.2](#12-roles)
and falls back to the single `lyrics` pointer.

---

## 6. Arrangement JSON

Arrangement files (`arrangements/<id>.json`, or `arrangements/<id>.jsonc` for hand-edited
packs) carry the playable note/chord data for one arrangement — the **wire format**. This
document defines that format; it is the authoritative reference for it.

### 6.1. Top-level shape

```jsonc
{
  "name": "Lead",
  "tuning": [0, 0, 0, 0, 0, 0],
  "capo": 0,
  "centOffset": 0.0,           // OPTIONAL, float cents, default 0.0
  "notes":      [ /* §6.2 */ ],
  "chords":     [ /* §6.3 */ ],
  "anchors":    [ /* §6.4 */ ],
  "handshapes": [ /* §6.5 */ ],
  "templates":  [ /* §6.6 */ ],
  "phrases":    [ /* OPTIONAL, §6.7 */ ],
  "tones":      { /* OPTIONAL, §6.9 */ },
  "tempos":     [ /* OPTIONAL, §6.10 — per-chart tempo override */ ],
  "beats":      [ /* §6.8 — see note */ ],
  "sections":   [ /* §6.8 — see note */ ]
}
```

`beats` and `sections` are **song-level** data. For historical reasons they MAY appear inside
the first arrangement's JSON, in which case a Reader **MUST** hoist them to the song. New
packages **SHOULD** instead use a dedicated [`song_timeline.json`](#74-song_timelinejson). When
both are present, the `song_timeline.json` values **MUST** take priority.

### 6.2. Notes

Field names are short on purpose. A Writer **MUST NOT** expand them.

```jsonc
{
  "t": 12.345,    // time (s)
  "s": 2,         // string (0 = lowest)
  "f": 7,         // fret (0 = open, 24 = max)
  "sus": 0.5,     // sustain (s, 0 = none)
  "sl": 9,        // pitched slide-to fret (-1 = no slide)
  "slu": -1,      // unpitched slide-to fret (-1 = no slide)
  "bn": 1.0,      // bend amount in semitones (peak)
  "bt": 4,        // OPTIONAL bend intent (§6.2.1): 0 up, 1 release, 2 pre-bend, 3 pre-bend-release, 4 round-trip
  "bnv": [{ "t": 0, "v": 0 }, { "t": 0.25, "v": 1.0 }, { "t": 0.5, "v": 0 }],  // OPTIONAL time-stamped bend curve
  "ho": false,    // hammer-on
  "po": false,    // pull-off
  "hm": false,    // natural harmonic
  "hp": false,    // pinch harmonic
  "pm": false,    // palm mute
  "mt": false,    // string mute
  "vb": false,    // vibrato
  "tr": false,    // tremolo
  "ac": false,    // accent
  "tp": false,    // tap
  "ln": false,    // link-next (chord-linking metadata; renderers may ignore)
  "fhm": false,   // fret-hand mute
  "plk": false,   // pluck / pop (bass)
  "slp": false,   // slap (bass)
  "rh": -1,       // right-hand fingering (-1 = unset)
  "pkd": -1,      // pick direction (-1 = unset, 0 = down, 1 = up)
  "fg": -1,       // OPTIONAL fret-hand finger, teaching mark (§6.2.2): -1 unset, 0 thumb, 1–4 index→pinky
  "ch": -1,       // OPTIONAL strum-group key, teaching mark (§6.2.2): notes sharing a value ≥ 0 are one strum gesture
  "sd": -1,       // OPTIONAL scale degree, teaching mark (§6.2.2): chromatic offset 0–11 above the active key's tonic
  "ig": false     // ignore (authoring flag — rendered but not scored / sequenced)
}
```

Only `t`, `s`, and `f` are REQUIRED. Numeric defaults are `0`, or `-1` for the slide / `rh` /
`pkd` / `fg` / `ch` / `sd` fields; boolean defaults are `false`. When authoring by hand, a Writer
**MAY** omit any field equal to its default; a Reader **MUST** fill in defaults for absent fields.

#### 6.2.1. Bend shape (`bt`, `bnv`)

`bn` is the bend's **peak** magnitude in semitones. Two OPTIONAL fields describe its shape over
time; both were added in 1.4.0 and an older Reader simply ignores them, treating the note as a
plain bend-up to `bn`.

- **`bt`** — bend **intent**, an integer (default `0`):

  | `bt` | meaning |
  |---|---|
  | `0` | bend up (default) |
  | `1` | release (a held bend let down) |
  | `2` | pre-bend (already bent at the note's onset) |
  | `3` | pre-bend-and-release |
  | `4` | round-trip (bend up then back down within the note) |

- **`bnv`** — a **time-stamped bend curve**: an array of `{ "t": <seconds from the note's onset>,
  "v": <semitones> }` points, in non-descending `t` order. When present, `bnv` is the authoritative
  shape and `bt` is advisory; `bn` remains the peak for Readers that don't interpolate the curve.
  Omit `bnv` for a simple bend.

A note **SHOULD NOT** carry `bnv` or a non-zero `bt` when `bn` is `0`.

#### 6.2.2. Teaching marks (`fg`, `ch`, `sd`)

Three OPTIONAL fields added in 1.5.0 annotate *how a note is taught or displayed*. They are
**teaching marks**, not performance data: a renderer **MAY** show them, but a grader **MUST NOT**
use them to decide whether a note was played correctly. An older Reader ignores them.

- **`fg`** — the **fret-hand finger** the chart prescribes, an integer (default `-1`):

  | `fg` | finger |
  |---|---|
  | `-1` | unset — no prescription (default) |
  | `0` | thumb |
  | `1` | index |
  | `2` | middle |
  | `3` | ring |
  | `4` | pinky |

  This is the same convention as a chord [`template.fingers`](#63-chords) entry, lifted to the
  single note. `fg = -1` (or absent) means the chart does **not** prescribe a finger — it does
  **not** mean "wrong finger". A grader **MUST NOT** penalise a performance for the finger used.

- **`ch`** — a **strum-group key**, an integer (default `-1`). Notes within one arrangement that
  share the same `ch` value `≥ 0` are performed as a single strum or rake gesture and **MAY** be
  drawn with a strum indicator; [`pkd`](#62-notes) gives the gesture's direction. The value is an
  opaque grouping label, not an index or an ordering. `ch = -1` (or absent) means ungrouped.
  Whereas a chord groups notes sounded *simultaneously*, `ch` groups notes — possibly slightly
  staggered in `t` — that the player executes as one motion.

- **`sd`** — the note's **scale degree**, an integer `0`–`11` (default `-1`). It is the note's
  pitch class expressed as a **chromatic offset in semitones above the tonic** of the key/scale
  active at the note's time (see [`keys.json`](#77-keysjson)): `0` = tonic, `2` = major second,
  `3` = minor third, `7` = perfect fifth, and so on. A display layer maps it to a conventional
  degree label (`1`, `♭3`, `5`, …) using the active scale. Because `sd` is fully derivable from
  `keys.json` and the note's pitch, a Reader **MAY** compute it itself and a Writer **MAY** omit
  it; when present it is a cached value or an author override. `sd = -1` (or absent) means unset —
  for instance when no key is in effect.

### 6.3. Chords

A chord groups note-shaped objects under a single time:

```jsonc
{
  "t": 30.0,
  "id": 12,           // index into templates[]
  "hd": false,        // high-density flag
  "notes": [
    {"s": 0, "f": 3, "sus": 0.0},
    {"s": 1, "f": 5, "sus": 0.0}
  ],
  "fn": {"rn": "ii7", "q": "m7", "deg": 2}  // OPTIONAL harmonic function (§6.3.1)
}
```

Chord notes use the same field set as standalone notes **except** that `t` is omitted — the
chord carries the time. `id` indexes into `templates[]` for the fingering/shape.

#### 6.3.1. Harmonic function (`fn`)

`fn` is an OPTIONAL object describing the chord's harmonic function in the active key. Added in
1.7.0, it is a **teaching annotation**, not performance data: a renderer **MAY** display it, but a
grader **MUST NOT** use it to score whether the chord was played correctly. An older Reader ignores
it.

| key | type | meaning |
|---|---|---|
| `rn` | string | Roman-numeral label, for display (e.g. `"ii7"`, `"V7"`, `"♭VII"`). |
| `q` | string | chord quality token (e.g. `"maj7"`, `"m7"`, `"7"`, `"m7b5"`, `"sus4"`). |
| `deg` | integer `0`–`11` | chromatic offset in semitones of the chord **root** above the tonic of the key/scale active at the chord's time (`0` = tonic), mirroring the per-note [`sd`](#622-teaching-marks-fg-ch-sd) convention. |

`fn` itself is OPTIONAL, but when present all three keys (`rn`, `q`, `deg`) are REQUIRED — a
half-specified function is ambiguous. `fn` describes the chord's **as-played** function and is fully derivable from the chord root and the
key active at its time (see [`keys.json`](#77-keysjson)), so a Reader **MAY** compute it and a
Writer **MAY** omit it; when present it is a cached value or an author override. It lives on the
chord **instance** (§6.3), not the [template](#66-chord-templates) — the same shape is reused across
keys, so its function is not a property of the shape. The song-level *harmony track*
([`harmony.json`](#78-harmonyjson)) instead carries the song's **intended** chord progression;
`fn` describes each chord as actually voiced, and the two are deliberately distinct (a Reader MAY
derive one from the other, but neither is authoritative).

The `q` token is drawn from a **shared chord-quality vocabulary** — a recommended (not closed) set
including `"maj"`, `"m"` (minor triad; `"min"` is an accepted synonym), `"maj7"`, `"m7"`, `"7"`,
`"m7b5"`, `"dim"`, `"aug"`, `"sus2"`, `"sus4"`, `"6"`, `"9"`, … — the same set
[`harmony.json`'s `quality`](#78-harmonyjson) uses, so the two stay interoperable.

### 6.4. Anchors

Where the fretting hand sits; drives a renderer's zoom/focus box.

```json
{"time": 12.0, "fret": 5, "width": 4}
```

### 6.5. Hand shapes

Spans during which a chord shape is held:

```json
{"chord_id": 12, "start_time": 30.0, "end_time": 31.5, "arp": false}
```

| Field | Type | Default | Notes |
|---|---|---|---|
| `chord_id` | int | `0` | Index into `templates[]`. |
| `start_time` | number | `0.0` | Span start (s). |
| `end_time` | number | `0.0` | Span end (s). |
| `arp` | boolean | `false` | Treat as an arpeggio span rather than a strummed hold. |

### 6.6. Chord templates

Named shapes referenced by `chord.id` and `handshape.chord_id`:

```json
{
  "name": "Em7",
  "displayName": "Em7",
  "arp": false,
  "fingers": [-1, 2, 1, -1, -1, -1],
  "frets":   [ 0, 2, 2,  0,  0,  0],
  "voicing": "open",
  "caged": "E",
  "guideTones": [3, 10]
}
```

| Field | Type | Default | Notes |
|---|---|---|---|
| `name` | string | `""` | Canonical template name. |
| `displayName` | string | `name` | UI label (MAY carry display-only variants). |
| `arp` | boolean | `false` | Whether the template is arpeggiated. |
| `fingers` | int[] | all `-1` | Fretting-hand fingers, lowest string first. `-1` = unused, `0` = open / no finger, `1..4` = index/middle/ring/pinky. Length matches the string count. |
| `frets` | int[] | all `-1` | Fret numbers, lowest string first. `-1` = unused, `0` = open, positive = fretted. |
| `voicing` | string | `""` | OPTIONAL voicing type of the shape (1.7.0) — e.g. `"open"`, `"triad"`, `"shell"`, `"drop2"`, `"drop3"`, `"barre"`. A **teaching annotation** (display only — a grader **MUST NOT** score it); free-form, but a Writer SHOULD prefer the listed tokens. It describes the key-independent shape, which is why it lives on the template rather than the chord instance (cf. [`fn`](#631-harmonic-function-fn)). |
| `caged` | string | `""` | OPTIONAL CAGED-system shape (1.8.0) the fingering derives from — one of `"C"`, `"A"`, `"G"`, `"E"`, `"D"`. A **teaching annotation** (display only — a grader **MUST NOT** score it). Like `voicing`, it describes the key-independent shape, so it rides the template. |
| `guideTones` | int[] | `[]` | OPTIONAL guide tones (1.8.0) — chromatic semitone offsets `0`–`11` above the chord **root** marking the tones that most define the chord's quality (typically the 3rd and 7th); e.g. a dominant-7 → `[4, 10]` (major 3rd, minor 7th). A **teaching annotation** (display only — a grader **MUST NOT** score it). Root-relative, hence key-independent, so it rides the template. |

### 6.7. Phrases (OPTIONAL — multi-difficulty data)

Sources that carry a per-phrase difficulty ladder include this:

```jsonc
"phrases": [
  {
    "start_time": 0.0,
    "end_time":   12.5,
    "max_difficulty": 4,
    "levels": [
      { "difficulty": 0, "notes": [], "chords": [], "anchors": [], "handshapes": [] },
      { "difficulty": 1, "notes": [], "chords": [], "anchors": [], "handshapes": [] }
    ]
  }
]
```

A Writer with no multi-difficulty data **MUST omit the `phrases` key entirely** rather than
emit `"phrases": []`. A missing key means "single fixed difficulty"; the distinction is
normative because consumers gate a difficulty control on the key's presence.

### 6.8. Beats and sections

```json
"beats":    [{"time": 0.5, "measure": 1}, {"time": 1.0, "measure": -1}],
"sections": [{"name": "verse", "number": 1, "time": 12.5}]
```

`measure: -1` marks a sub-beat (not a downbeat). Section `name` follows the usual
song-structure vocabulary (`intro`, `verse`, `chorus`, `bridge`, `solo`, `outro`, …). See the
note in [§6.1](#61-top-level-shape) regarding placement and the `song_timeline.json` priority
rule.

### 6.9. Tones (OPTIONAL)

`tones` carries the arrangement's sound — its rigs (effect chains and/or MIDI-voiced sound
sources, [§7.9](#79-rigsjson)) — and in-song tone switches. Omitted when the source carries no
tone data.

```jsonc
"tones": {
  "base": "Clean Rhythm",
  "base_rig": "clean-rhythm",
  "changes": [
    {"t": 12.5, "name": "Lead Drive", "rig": "lead-drive"},
    {"t": 48.0, "name": "Clean Rhythm", "rig": "clean-rhythm"}
  ],
  "definitions": [
    {"name": "Clean Rhythm", "id": "tone-1", "gear": { /* opaque, source-specific gear data */ }}
  ]
}
```

`tones` binds gear to time; the actual rigs are defined in one of two ways:

1. **Structured, portable** — the [`rigs.json`](#79-rigsjson) library (§7.9). `base_rig` and each
   `changes[].rig` reference a rig `id` there. This is the recommended, engine-agnostic
   representation and the only one a Reader can portably render.
2. **Legacy opaque** — `definitions`, a list of raw tone objects copied verbatim from the source
   (e.g. an opaque object from an external source). It is source-specific and not portably interpretable; Readers that do
   not interpret it **MUST** preserve `tones` verbatim.

A pack MAY carry both; a rig-aware Reader **SHOULD** prefer the `rig`/`base_rig` references over
`definitions`.

- `base` (string) — human-readable name of the tone in effect before the first change.
- `base_rig` (string, OPTIONAL) — rig `id` in [`rigs.json`](#79-rigsjson) for the base tone.
- `changes` (list, time-sorted) — `{"t": seconds, "name": str, "rig"?: str}` switches. `rig`
  references a rig `id` in [`rigs.json`](#79-rigsjson).
- `definitions` (list, OPTIONAL) — raw, opaque tone objects copied from the source.

All sub-keys are individually OPTIONAL.

When the manifest arrangement entry also carries a `tones` object ([§5.2](#52-arrangements)),
the manifest entry **overrides this one wholesale** — see the precedence rule there. A Writer
**SHOULD NOT** emit both.

### 6.10. Per-arrangement tempo (OPTIONAL)

A chart MAY declare its own tempo map, overriding the song-wide tempo for that arrangement only.
This supports an arrangement authored at a different tempo from the rest of the song (a half-time
feel, a slowed practice chart, …). The shape is identical to the song-level
[`tempos`](#74-song_timelinejson):

```json
"tempos": [
  {"time": 0.0, "bpm": 80.0},
  {"time": 30.0, "bpm": 160.0}
]
```

| Field | Type | Notes |
|---|---|---|
| `time` | number | Event time (s). REQUIRED. |
| `bpm` | number | Beats per minute, `> 0`. REQUIRED. Applies until the next event. |

**Priority.** When the consumer plays this arrangement and the arrangement carries a non-empty
`tempos`, a Reader **MUST** use it and **MUST** ignore the song-level
[`song_timeline.json` `tempos`](#74-song_timelinejson) for this chart. When the arrangement omits
`tempos`, the song-level tempo applies. A Writer **MUST omit the key entirely** when the chart
follows the song tempo rather than emit `"tempos": []`. `time_signatures` are **song-level only**
and are not overridden per arrangement.

---

## 7. Side-files

Each side-file is referenced from the manifest by a pointer key (the "manifest opt-in, file off
to the side" pattern; see [§9.1](#91-the-golden-rule-manifest-opt-in-file-off-to-the-side)).
Side-files use the `.json` extension by convention; hand-edited side-files MAY use `.jsonc` to
signal that the file contains comments. Every side-file that is a JSON **object SHOULD** carry a
top-level integer `version` (see [§4.3](#43-side-file-schema-versions)). The one exception is
`lyrics.json`, which is a flat JSON array kept for backward compatibility: it carries no
`version` field, and its origin and revision are tracked at the manifest level instead
(`lyrics_source`, `lyric_transcription`).

### 7.1. `lyrics.json`

Referenced by the manifest `lyrics` key. A flat JSON list of syllable objects. Unlike the
object-shaped side-files, `lyrics.json` carries **no** top-level `version` field — it is an
array kept in this shape for backward compatibility, and its origin/revision is tracked at the
manifest level (`lyrics_source`, `lyric_transcription`). This is the one documented exception to
the side-file `version` guidance in [§4.3](#43-side-file-schema-versions) and [§9.3](#93-always-include-version).

```json
[
  {"t": 12.34, "d": 0.18, "w": "Hel"},
  {"t": 12.52, "d": 0.22, "w": "lo-"},
  {"t": 13.10, "d": 0.30, "w": "world"}
]
```

| Field | Type | Notes |
|---|---|---|
| `t` | number | Time (s). |
| `d` | number | Duration (s). |
| `w` | string | Syllable text. A trailing `-` joins to the next syllable as one word; a trailing `+` marks the last syllable of a line. Both are suffixes on a real syllable, not standalone entries. |

The manifest `lyrics_source` key records the origin: `authored` (from an authored chart),
`transcribed` (machine-generated by an automated engine — speech transcription, and, for
[`lyric_tracks`](#55-lyric_tracks), machine translation or transliteration), or `user`
(hand-edited). Absent ⇒ `authored`. A UI MAY use this to badge machine-generated lyrics
differently.

A song MAY carry **more than one lyric track** — an original-script track plus a transliteration
and/or translation, or per-language sung originals. These additional tracks are listed in the
manifest [`lyric_tracks`](#55-lyric_tracks) key (§5.5); each one is a file in this same flat-array
shape. The single `lyrics` pointer remains the backward-compatible primary track.

#### 7.1.1. `lyric_transcription`

When `lyrics_source` is `transcribed` (or any future automated origin), an OPTIONAL top-level
`lyric_transcription` object records `{engine, model, version}` with the same shape and semver
semantics as [`stem_separation`](#531-stem_separation), identifying the automated engine that
produced the text — speech transcription, or (for a [`lyric_tracks`](#55-lyric_tracks) entry)
machine translation or transliteration. Omitted for `authored`/`user` lyrics.

### 7.2. `vocal_pitch.json`

Referenced by the manifest `vocal_pitch` key — the per-syllable karaoke companion to lyrics:

```json
{
  "version": 1,
  "notes": [
    {"t": 12.34, "d": 0.40, "midi": 64},
    {"t": 12.78, "d": 0.55, "midi": 67}
  ]
}
```

| Field | Type | Notes |
|---|---|---|
| `version` | int | Schema version of this file (currently `1`). |
| `notes` | list | One entry per syllable that could be pitched. `t`/`d` mirror the matching `lyrics.json` entry; `midi` is the MIDI note number (60 = middle C). Unpitched syllables are omitted, so this list MAY be shorter than `lyrics.json`. |

#### 7.2.1. `pitch_extraction`

When pitch came from an automated engine, an OPTIONAL top-level `pitch_extraction` object
records `{engine, model, version}` — same shape and semver-string semantics as
[`stem_separation`](#531-stem_separation). This is distinct from the in-file integer `version`
above. Omitted for hand-edited pitch tracks.

### 7.3. `vocal_pitch_contour.json`

Referenced by the manifest `vocal_pitch_contour` key — a fine-grained pitch contour (one sample
every ~20 ms, Hz rather than MIDI). It is a *different shape* from `vocal_pitch.json` and rides
its own manifest key so the two never collide:

```json
{
  "version": 1,
  "samples": [
    {"t": 0.000, "hz": 220.5},
    {"t": 0.020, "hz": 222.1}
  ]
}
```

### 7.4. `song_timeline.json`

Referenced by the manifest `song_timeline` key. Holds the song-wide rhythmic grid — beats,
sections, and (since 1.2.0) the song's tempo and time-signature maps — in one dedicated,
instrument-independent file, out of the first arrangement JSON:

```json
{
  "version": 1,
  "tempos": [
    {"time": 0.000, "bpm": 120.0},
    {"time": 64.000, "bpm": 90.0}
  ],
  "time_signatures": [
    {"time": 0.000, "ts": [4, 4]},
    {"time": 32.000, "ts": [6, 8]}
  ],
  "beats": [
    {"time": 0.500, "measure": 1},
    {"time": 1.000, "measure": -1},
    {"time": 2.000, "measure": 2}
  ],
  "sections": [
    {"name": "intro",  "number": 1, "time": 0.0},
    {"name": "verse",  "number": 1, "time": 16.0},
    {"name": "chorus", "number": 1, "time": 32.0}
  ]
}
```

`tempos` and `time_signatures` are each OPTIONAL, time-ordered, and follow the same
"each entry applies until the next" rule as [`keys.json`](#77-keysjson). Adding them did not
change the file's `version`, which stays `1`.

| `tempos[]` field | Type | Notes |
|---|---|---|
| `time` | number | Event time (s). REQUIRED. |
| `bpm` | number | Beats per minute, `> 0`. REQUIRED. In effect until the next `tempos` entry. |

| `time_signatures[]` field | Type | Notes |
|---|---|---|
| `time` | number | Event time (s). REQUIRED. |
| `ts` | int[2] | `[numerator, denominator]`, each `≥ 1` (same convention as notation `ts`, [§7.6](#76-notation_idjson)). REQUIRED. In effect until the next entry. |

| `beats[]` field | Type | Notes |
|---|---|---|
| `time` | number | Beat timestamp (s). |
| `measure` | int | 1-based downbeat number; `-1` = sub-beat. |

| `sections[]` field | Type | Notes |
|---|---|---|
| `name` | string | Song-structure name (`intro`, `verse`, `chorus`, …). |
| `number` | int | Repeat number. |
| `time` | number | Section start (s). |

The song-level `tempos` map is the song-wide **playback/timing** tempo, distinct from the
per-measure `tempo` inside [`notation_<id>.json`](#76-notation_idjson) (§7.6), which exists for
staff rendering. An arrangement MAY override `tempos` for its own chart — see
[§6.10](#610-per-arrangement-tempo-optional).

When `song_timeline.json` is present and valid, its data **MUST** take priority over any
beats/sections embedded in arrangement JSON. When absent, the Reader **MUST** fall back to the
arrangement-embedded data per [§6.1](#61-top-level-shape). No migration is required for older
packages.

### 7.5. `drum_tab.json`

Referenced by the song-level [`drum_tab`](#51-top-level-keys) manifest key, or by an
[arrangement entry's `drum_tab`](#52-arrangements) — per-piece drum hits (the file shape is the
same for both). A pack MAY carry **several** drum parts as `type: drums` arrangements; see
[Multiple drum parts](#multiple-drum-parts) below.

```json
{
  "version": 1,
  "name": "Drums",
  "kit": [
    {"id": "kick",      "name": "Kick"},
    {"id": "snare",     "name": "Snare"},
    {"id": "hh_closed", "name": "Hi-hat (closed)"},
    {"id": "ride",      "name": "Ride"}
  ],
  "hits": [
    {"t": 0.500, "p": "kick",      "v": 110},
    {"t": 0.750, "p": "snare",     "v":  92},
    {"t": 0.750, "p": "hh_closed", "v":  70},
    {"t": 1.000, "p": "snare",     "v":  60, "g": true},
    {"t": 1.250, "p": "snare",     "v": 105, "f": true},
    {"t": 4.000, "p": "crash_r",   "v": 120, "k": 0.080}
  ]
}
```

| `hits[]` field | Type | Notes |
|---|---|---|
| `t` | number | Hit time (s), REQUIRED, monotonic across `hits[]`. |
| `p` | string | Piece-id from the vocabulary below, REQUIRED. |
| `v` | int 1–127 | Velocity (default `100`). |
| `g` | boolean | Ghost note. |
| `f` | boolean | Flam. |
| `k` | number | Cymbal-choke tail duration (s). |

`kit[]` is the legend (stable metadata); `hits[]` is the hot path (short field names). Open and
closed hi-hat are **distinct piece-ids**, not articulation flags — a scorer can only reject a
wrong-articulation strike if the articulation is part of the id.

**Canonical piece-id vocabulary.** This is a closed list for v1; unknown piece-ids **MUST**
round-trip (a Reader renders them with a sensible default rather than erroring).

| Piece-id | Category | Default GM MIDI |
|---|---|---|
| `kick` | kick | 35, 36 |
| `snare` | drum | 38, 40 |
| `snare_xstick` | drum | 37 |
| `tom_hi` | drum | 50, 48 |
| `tom_mid` | drum | 47, 45 |
| `tom_low` | drum | 43 |
| `tom_floor` | drum | 41 |
| `hh_closed` | cymbal | 42 |
| `hh_open` | cymbal | 46 |
| `hh_pedal` | cymbal | 44 |
| `stack` | cymbal | 30 |
| `crash_l` | cymbal | 49 |
| `crash_r` | cymbal | 57 |
| `splash` | cymbal | 55 |
| `china` | cymbal | 52 |
| `ride` | cymbal | 51, 59 |
| `ride_bell` | cymbal | 53 |
| `bell` | cymbal | 80 |

#### Multiple drum parts

A song MAY have more than one drum chart — two drummers recorded separately, a programmed
layer beside an acoustic kit, or an aux-percussion part. Each extra drum part is an
[arrangement entry](#52-arrangements) with `type: drums` and its own `drum_tab` pointer (no
`file`, no `notation`), exactly as a keys part is an entry with a `notation` pointer. This is
purely additive over the single song-level [`drum_tab`](#51-top-level-keys) key:

- **Single drum part (the common case, unchanged).** A pack with one drum chart carries only the
  song-level `drum_tab` key and no `type: drums` arrangement. Nothing about it changes; a Writer
  SHOULD keep emitting exactly this shape when there is one drum part.
- **The song-level `drum_tab` is the PRIMARY part.** When a pack does carry `type: drums`
  arrangements, a Writer **SHOULD** set the song-level `drum_tab` to the primary drum part's file
  (the same path that part's arrangement-entry `drum_tab` points at), so that a Reader predating
  this section still gets one sensible drum chart.
- **Reader — no per-arrangement `drum_tab` support (older Reader).** It reads the song-level
  `drum_tab` as the one drum part and treats each `type: drums` arrangement as an entry with no
  `file` it can render — i.e. it silently ignores the extra parts. Graceful degradation to one
  drummer, never an error.
- **Reader — with per-arrangement `drum_tab` support.** It takes the pack's drum parts from the
  `type: drums` arrangements (each via its own `drum_tab`). When such arrangements are present it
  **MUST NOT** additionally load the song-level `drum_tab` as a separate part — that key is the
  compat alias of the primary and points at one of those same files. When there are **no**
  `type: drums` arrangements, the song-level `drum_tab`, if present, is the single drum part
  (identical to prior versions).
- **Sound binding.** A `type: drums` arrangement binds its sound through its entry
  [`tones`](#52-arrangements) like any other arrangement. The top-level
  [`drum_tones`](#51-top-level-keys) key binds the song-level (primary) drum part and is the
  **fallback** for packs without `type: drums` arrangements; when such arrangements are present,
  the entry `tones` **takes precedence** and a Reader **MUST NOT** additionally apply
  `drum_tones` to the same part — mirroring the `drum_tab` alias rule above. A Writer SHOULD
  keep `drum_tones` matching the primary part's binding, exactly as the song-level `drum_tab`
  mirrors the primary part's chart.
- **Grading/selection invariant.** A `type: drums` arrangement is a drum part: a consumer **MUST
  NOT** select or score it as a pitched/fretted arrangement (a drum chart carries piece hits, not
  string·fret or notated pitch, so grading it against a fretted or note detector is meaningless).

Drum-tab filenames are the Writer's choice (resolve through the manifest pointer, never by
scanning — [§2.2](#22-three-core-rules)); `drum_tab_<id>.json` alongside the primary `drum_tab.json`
is a readable convention.

### 7.6. `notation_<id>.json`

Referenced by an **arrangement entry's** `notation` key (per-arrangement, not song-wide — a
song MAY carry both `notation_keys.json` and `notation_violin.json`). Promotes staff-notation
instruments (keys, piano, strings, …) to first-class data, separate from the guitar wire
format.

```json
{
  "version": 1,
  "instrument": "piano",
  "staves": [
    {"id": "rh", "clef": "G2", "label": "Right Hand"},
    {"id": "lh", "clef": "F4", "label": "Left Hand"}
  ],
  "measures": [
    {
      "idx": 1,
      "t": 0.0,
      "ts": [4, 4],
      "ks": 0,
      "tempo": 120.0,
      "staves": {
        "rh": {"voices": [{"v": 1, "beats": [
          {"t": 0.000, "dur": 4, "notes": [{"midi": 64}]},
          {"t": 0.500, "dur": 4, "notes": [{"midi": 67}]}
        ]}]},
        "lh": {"voices": [{"v": 1, "beats": [
          {"t": 0.000, "dur": 1, "notes": [{"midi": 52}, {"midi": 60}]}
        ]}]}
      }
    }
  ]
}
```

**Top-level fields**

| Field | Type | Notes |
|---|---|---|
| `version` | int | Always `1` for this schema. |
| `instrument` | string | `piano`, `violin`, `guitar`, … Mirrors the arrangement `type`; makes the file self-describing. |
| `rights` / `lyricist` / `arranger` | string | OPTIONAL credits. Omit when absent. |
| `staves` | list | Static staff definitions: `id` (stable, referenced by `measures[].staves` keys), `clef`, OPTIONAL `label`. |
| `measures` | list | Ordered measure data — the hot path. |

**Clef vocabulary:** `G2` (treble), `F4` (bass), `C3` (alto), `C4` (tenor), `neutral`
(unpitched/percussion).

**Measure fields:** `idx` (1-based number), `t` (downbeat time, s), `ts` (`[num, den]`, omit if
unchanged), `beat_groups` (int[] for compound/irregular meters; the sum MUST equal the
numerator; omit for simple meters), `ks` (key signature, −7..+7 semitones from C; negative =
flats; omit if unchanged), `tempo` (BPM, omit if unchanged), `pickup` (bool anacrusis flag, omit
when false), `staves` (keyed by staff `id`; each has OPTIONAL `clef` and `voices`).

**Beat fields** (inside `staves → voices → beats`): `t` (required), `dur` (required denominator:
`1`=whole … `32`=thirty-second), `dot`, `rest`, `tu` (`[num, den]` tuplet), `beat_pos`
(`[num, den]` exact position within the measure), `notes`, `dyn`, `slr`/`slre`, `grace`
(`"a"`/`"p"`), `arp`, `ferm`, sustain-pedal `spd`/`sph`/`spu`, and additional optional effects
(`cre`, `dec`, `vib`, `vibw`, `fade`, `pm`, `lr`, `slap`, `pop`, `tap`, `su`, `sd`, `rasg`,
`golpe`, `wah`, `txt`, `chrd`).

**Note fields** (inside `beats → notes`): `midi` (required, 0–127), `tied`, `acc` (accidental
override: `0`=force natural, `−2..2` = double-flat..double-sharp), `stem` (`"up"`/`"down"`), and
additional optional effects (`stc`, `ten`, `ac`, `hac`, `vib`, `vibw`, `dead`, `ghost`, `fng`,
`rfng`, `str`, `harm`, `bend`, `slide`, `trill`, `ho`, `po`, `tp`, `barre`).

**v1 non-features (out of scope; ship later only as additive v1.x optional fields):** microtonal
pitch finer than `acc`; figured bass; mid-measure key/time/clef changes (all three are
measure-granular in v1); ottava lines, repeat/volta barline semantics, ornaments beyond trills,
notated tremolo, and glissando lines. A Writer **MUST** drop a source feature on this list (with
a logged warning) rather than approximate it into wrong notation; a Reader **MUST NOT** invent
semantics for an unspecified field name before a future version defines it.

### 7.7. `keys.json`

Referenced by the manifest `keys` key — key/scale annotations for theory-aware visualisations.
Each entry applies until the next:

```json
{
  "version": 1,
  "events": [
    {"t":   0.0, "key": "Em", "scale": "natural_minor"},
    {"t":  64.5, "key": "G",  "scale": "major"}
  ]
}
```

> **Note — `keys.json` is not a keyboard part.** Despite the name, this file is a song-level
> musical-key/scale track and is **instrument-independent**: it has nothing to do with a keyboard
> or piano arrangement (an arrangement `type: keys`, or a `notation_<id>.json`). A guitar-only,
> drums-only, or stems-only pack uses `keys.json` to tell the player "the song is in Em, then
> changes to G major at 64.5 s" with no keyboard part anywhere in the package. The `keys` manifest
> pointer (this file) and the `keys` instrument hint are unrelated.

---

### 7.8. `harmony.json`

Referenced by the manifest `harmony` key — the song's **intended chord progression**: the chords
the song *is*, independent of what any one arrangement plays. This is the reference/teaching
track a fretboard-theory overlay, a "chords" lyric line, or a practice-along reads; a simplified
or solo arrangement won't carry it per-chord, so it lives once at the song level. Time-ordered
events, each applying until the next (the same shape as [`keys.json`](#77-keysjson)):

```json
{
  "version": 1,
  "events": [
    {"t": 0.0, "root": "G",  "quality": "maj7", "rn": "I"},
    {"t": 2.0, "root": "E",  "quality": "m7",   "rn": "vi", "bass": "G"},
    {"t": 4.0, "root": "C",  "quality": "maj7", "rn": "IV"},
    {"t": 6.0, "root": null}
  ]
}
```

| Field | Type | Req | Meaning |
|---|---|---|---|
| `t` | number | **yes** | Event time (s); applies until the next event (matches `keys.json`'s `t`). |
| `root` | string \| null | — | Chord root note name — `"G"`, `"F#"`, `"Bb"` (same note-name convention as `keys.json`'s `key`). **`null` marks a no-chord (N.C.) event** — a rest/breakdown with no harmony until the next event; without it the apply-until-next rule would wrongly sustain the previous chord. Omitting `root` entirely is equivalent to `null`. |
| `quality` | string | — | Quality token (e.g. `"maj7"`, `"m7"`, `"7"`, `"dim"`, `"sus4"`). Drawn from the **shared chord-quality vocabulary** (see [§6.3.1](#631-harmonic-function-fn)); the set is recommended, not closed. |
| `rn` | string | — | Roman numeral relative to the active [`keys.json`](#77-keysjson) key, for display (like `fn.rn`). **Meaningful only when a key is active at this `t`** — omit it when `keys.json` is absent or has no event covering this time. |
| `bass` | string | — | Slash-chord bass note when different from `root` (e.g. `G/B` → `root: "G"`, `bass: "B"`). |

**Spelling.** `root` and `bass` **SHOULD** follow the active key's spelling convention (e.g. `Bb`
in F major, `A#` in B major) so a derived `rn`/notation reads correctly; the absolute spelling is
authoritative and the relative view is derived from it.

**Relationship to `fn`.** `harmony.json` is the song's *intended* progression (one per song,
reference data); per-chord [`fn`](#631-harmonic-function-fn) is the *as-played* function on a
specific arrangement's chords. They may agree or deliberately diverge (a simplified arrangement
plays a subset). A Reader **MAY** derive `fn` from `harmony.json` + the played chord, but neither
is authoritative over the other.

**No voicing.** `harmony.json` is abstract harmony only — it carries no fingering and does **not**
index the arrangement [chord templates](#66-chord-templates); voicings are an arrangement concern.

**Honesty rule.** The harmony track is reference/teaching data: a renderer/teacher **MAY** display
it; a grader **MUST NOT** use it to score the player's notes. (A backing engine that *plays* the
progression is a separate, dependent proposal, not part of this track.)

> **Note — repeats are flattened.** Events are a flat, time-ordered list, so a progression that
> recurs (e.g. a chorus) is repeated in full at each occurrence — the same tradeoff `keys.json`
> and `song_timeline.json` make. A section-relative encoding is out of scope for this version.

### 7.9. `rigs.json`

Referenced by the manifest `rigs` key — a **pack-level library of engine-agnostic rigs**:
portable signal chains. A rig can describe an **effect chain** for an incoming audio signal
(guitar / bass tones — amps, cabs, pedals) or, since 1.18.0, a **sound source** that voices a
MIDI part (piano, keys, drums), or both in one chain. Arrangements bind rigs to time via
[`tones.base_rig`](#69-tones-optional) / [`tones.changes[].rig`](#69-tones-optional) (§6.9), which
reference a rig's `id` here. Rigs live pack-level (not per-arrangement) so one rig can be shared
across arrangements and tone changes.

This is the portable successor to the opaque, source-specific [`tones.definitions`](#69-tones-optional)
passthrough. It is deliberately **not modelled on any one source or engine** (a
single serial chain, a fixed gear catalog, or one plugin format): a rig is an ordered set
of effect **blocks**, each of which separates *what it is* (`intent`, engine-independent) from *how
to render it* (`realizations`, an ordered preference list).

```jsonc
{
  "version": 1,
  "rigs": [
    {
      "id": "lead-drive",          // referenced by tones.base_rig / changes[].rig
      "name": "Lead Drive",
      "instrument": "guitar",       // OPTIONAL hint
      "channels": 1,                // OPTIONAL; default 1 (mono)
      "blocks": [
        {
          "id": "amp",              // OPTIONAL; required only if referenced by `graph`
          "role": "amp",            // open vocabulary (gain/drive/amp/cab/eq/delay/reverb/…)
          "name": "British Hi-Gain",
          "bypassed": false,        // OPTIONAL
          "mix": 1.0,               // OPTIONAL wet/dry, 0..1
          "intent": {               // engine-independent: what the block IS
            "kind": "amp", "family": "british-hi-gain", "tags": ["crunch", "lead"]
          },
          "realizations": [         // ordered; reader renders the FIRST engine it supports
            {"engine": "nam", "ref": "captures/british-higain.nam", "sha256": "…"},
            {"engine": "plugin", "format": "clap", "id": "com.vendor.amp",
             "name": "AmpX", "vendor": "Vendor", "state": "<base64>", "params": {"gain": 0.72}},
            {"engine": "builtin", "id": "feedback.amp.tubestage.v1", "params": {"gain": 0.72}}
          ],
          "params": {"gain": 0.72, "bass": 0.5, "mid": 0.62, "treble": 0.58, "master": 0.5},
          "automation": [           // OPTIONAL time-varying params
            {"param": "gain", "points": [{"t": 48.0, "v": 0.72}, {"t": 60.0, "v": 0.85}]}
          ]
        }
      ],
      "graph": {                    // OPTIONAL; non-serial topology (parallel/stereo/wet-dry)
        "nodes": ["input", "amp", "output"],
        "edges": [["input", "amp"], ["amp", "output"]]
      }
    }
  ]
}
```

| Top-level field | Type | Notes |
|---|---|---|
| `version` | integer ≥ 1 | REQUIRED. Side-file schema version (independent of `feedpak_version`). |
| `rigs` | array | REQUIRED. The rig library. |

**Rig** (`rigs[]`):

| Field | Type | Notes |
|---|---|---|
| `id` | string | REQUIRED. Stable id referenced by `tones.base_rig` / `changes[].rig`. |
| `name` | string | OPTIONAL, human-readable. |
| `instrument` | string | OPTIONAL hint (`guitar`, `bass`, `keys`, `drums`, …). Non-normative. |
| `channels` | integer ≥ 1 | OPTIONAL. Channels the rig is authored for; default `1`. |
| `blocks` | array | REQUIRED. Ordered serial signal chain (`input → blocks[0] → … → output`) unless `graph` overrides. |
| `graph` | object | OPTIONAL. Explicit `{nodes, edges}` topology for non-serial rigs. |

**Block** (`blocks[]`) — every field except at least one of `intent`/`realizations` is OPTIONAL:

| Field | Type | Notes |
|---|---|---|
| `id` | string | REQUIRED only if the block is referenced from `graph`. |
| `role` | string | Open vocabulary (`source`, `gain`, `drive`, `amp`, `cab`, `eq`, `dynamics`, `modulation`, `delay`, `reverb`, `pitch`, `filter`, `utility`, …). Reserved: `source` (see below). Unknown values MUST be preserved. |
| `name` | string | Human-readable. |
| `bypassed` | boolean | Default `false`. |
| `mix` | number 0..1 | Wet/dry mix; default `1`. |
| `intent` | object | Engine-independent description — `kind`, `family`, `model` (non-normative hints), `tags`, and, on a `source` block, an OPTIONAL **`gm`** object (normative-when-present, see below). Lets a Reader with no matching realization still display / approximate / remap the block — or, for a source block with `gm`, **voice** it. |
| `realizations` | array | Ordered by preference. A Reader renders the **first** realization whose `engine` (and `format`, where the engine defines one) it supports; if it supports none, it falls back to `intent`. |
| `params` | object | Open map of named controls: a number (normalized `0..1`), a string (discrete/enum), a boolean, or `{value, unit}` (e.g. `{"value": 320, "unit": "ms"}`). Not limited to any fixed knob set. |
| `automation` | array | OPTIONAL. `{param, points: [{t, v}]}` lanes; time-sorted, value held to the next point. |

**`role: "source"` — generator blocks.** A block with `role: "source"` is a **generator at the
head of the signal chain**: its input is **MIDI events supplied by the Reader** — whether those
come from the pack's own note data (notation, drum-tab) during playback or from the player's
live controller input is the Reader's business, not the pack's; the same declared sound voices
both. A `source` block feeds ordinary effect blocks (`input(MIDI) → source → amp → reverb →
output`); a rig that is *just* an instrument is a single `source` block. When the head block is
a `source`, the rig's `input` node is the Reader-supplied MIDI event stream rather than an audio
input; a source-headed rig has no audio input (a rig mixing a source head with parallel audio
input is out of scope). On a `source` block, `bypassed: true` means the part is not voiced by
this rig (an author mute — the same outcome as skipping the block, not a fall-through to
`intent.gm`), and `mix` has no meaning (there is no dry signal): Readers SHOULD ignore it and
Writers SHOULD omit it.

**`intent.gm` — the General MIDI floor.** A `source` block's `intent` MAY carry a GM identity so
that a Reader supporting no matching realization can still voice the part from a General MIDI
baseline:

```jsonc
"intent": {
  "kind": "instrument",
  "gm": { "program": 0 }        // melodic: GM program 0..127, 0-based (0 = Acoustic Grand)
  // or, for a percussion kit:
  // "gm": { "percussion": true, "kit": 0 }
}
```

Kit numbers use the **0-based** wire/SF2 numbering (0 = Standard, 8 = Room, 16 = Power,
24 = Electronic, …) — the values that travel in MIDI program-change bytes and appear as SF2
bank-128 preset numbers — matching `gm.program`'s 0-based convention. (GM documentation often
counts kits 1-based; that display convention is not used here.) `kit` absent ⇒ `0` (Standard),
matching the `bank`/`program` rule.

Unlike every other `intent` field, `gm` is **normative when present**: it is the first `intent`
content a Reader renders *audio* from. A Writer **SHOULD** give every `source` block a GM
`intent`, for the same reason it should give an effect block an `intent`: so the pack stays
renderable everywhere.

**Realization** (`realizations[]`):

| Field | Type | Notes |
|---|---|---|
| `engine` | string | REQUIRED. Open vocabulary. Reserved: `nam` (Neural Amp Modeler capture), `ir` (impulse response), `plugin` (host plugin), `builtin` (host DSP by id), `soundfont` (MIDI-voiced sound source — `source` blocks only). |
| `ref` | string | For `nam`/`ir`/`soundfont`: pack-relative path (no leading `/`, no `..` — see [§8](#8-reading-and-writing)) or absolute URI. REQUIRED for `soundfont`. |
| `sha256` | string | OPTIONAL integrity hash of the referenced asset. |
| `format` | string | For `plugin`: `vst3` \| `au` \| `lv2` \| `clap` \| … (open). For `soundfont`: `sf2` (reserved; open — future formats such as `sfz` or `ds` are added as renderers appear, each defining its own voice-addressing fields). |
| `id` | string | For `plugin`: bundle/unique id; for `builtin`: the host DSP id. |
| `name`, `vendor`, `preset` | string | OPTIONAL plugin identity/preset hints. |
| `bank`, `program` | integer | Voice selector for `engine: "soundfont"`, `format: "sf2"` (SF2 bank + preset number). Named `program`, not `preset`: `preset` is already reserved above as a **string** (plugin preset-name hint), and `program` matches `intent.gm.program`. OPTIONAL; absent ⇒ `0` (the SF2 default bank/preset). Other soundfont formats select the voice by their own means, documented per format. |
| `state` | string (base64) | OPTIONAL opaque plugin state for exact recall. MUST NOT be the only representation — pair with `intent`/`params` so a Reader without that plugin can still render something. |
| `params` | object | Same shape as block `params`; realization-specific control values. |

**Conformance.**

- A Writer **SHOULD** give every block an `intent` even when it also emits a `state` blob, so the
  rig stays renderable by Readers that lack the exact plugin/capture.
- A Reader that renders rigs **SHOULD** select, per block, the first `realizations[]` entry whose
  `engine` — and `format`, where the engine defines one — it supports; if none match, it **MAY**
  synthesize from `intent`/`params` or skip the block, and **MUST NOT** fail the whole pack.
  (The `format` gate is a general clarification, not a soundfont rule: it was always implicitly
  true — a Reader without VST3 hosting never could render a `format: "vst3"` realization.)
- **Source blocks tighten the skip rule.** Skipping an *effect* is benign (the signal passes
  through); skipping a *source* silences the part. A Reader that renders source rigs and matches
  no realization **SHOULD voice the part from `intent.gm` when present**; with no matching
  realization *and* no `intent.gm`, skipping remains the outcome. Skipping a source block is a
  last resort, not the peer fallback it is for effect blocks.
- A Reader voicing a `source` block — from a realization or from `intent.gm` — **SHOULD honour
  the part's control events** (sustain pedal `spd`/`sph`/`spu`, [§7.6](#76-notation_idjson);
  hi-hat pedal and chokes, [§7.5](#75-drum_tabjson)).
- A Reader that does not interpret rigs **MUST** ignore `rigs.json` and preserve it verbatim on
  round-trip, along with any unknown `role`/`engine`/`kind` values and `ext` namespaces.

---

## 8. Reading and writing

This section is **informative** — it describes the typical lifecycle, not additional
requirements.

**Reading.** Parse `manifest.yaml`; read `title`/`artist`/`duration`/`feedpak_version` for a
quick metadata view. For a full load, resolve each manifest pointer to its file, validate it
against the relevant schema, and merge per the priority rules in [§6.1](#61-top-level-shape) and
[§7.4](#74-song_timelinejson). Unknown manifest keys and files are retained, not discarded.

**JSONC comments (normative).** The requirements in this paragraph are binding, notwithstanding
the otherwise-informative framing of §8. When a manifest pointer resolves to a `.jsonc` file, a
Reader **MUST** strip C-style comments (`//` line comments and `/* */` block comments) before
parsing the JSON content.
Comments are the **only** relaxation permitted: trailing commas, single-quoted strings, and other
JSON5-style extensions are **NOT** allowed — after comment removal the content **MUST** be strict,
valid JSON. A Writer that preserves edits to a `.jsonc` file **SHOULD** leave the original comments
intact. For new hand-edited packs, Writers **MAY** write `.jsonc` data files and **MAY** include
comments in them.

Note on compatibility. `.jsonc` is governed by the **opt-in file-format relaxation carve-out** in
[§4.2](#42-compatibility-policy), not by the ordinary "older Readers keep working by ignoring them"
rule. Two facts must be kept separate:

1. **No existing pack breaks.** Packs that do not adopt `.jsonc` are entirely unchanged, and a
   comment-free `.jsonc` file is byte-for-byte valid JSON.
2. **A `.jsonc` file that actually contains comments is NOT readable by a strict-JSON-only
   Reader** — such a Reader errors on `//` and `/* */`. Only a Reader that implements the
   comment-stripping step above can read it. Unlike the optional fields added under a normal minor
   bump, comments cannot be safely *ignored* by an unaware Reader — which is exactly why §4.2 lists
   this as a bounded, opt-in exception.

A Writer that needs a pack to be readable by the broadest range of Readers therefore **SHOULD**
keep its data files as comment-free `.json`.

**Writing.** Build the package in a working directory: write `arrangements/<id>.json` per
arrangement; encode audio into `stems/`; write any side-files; compose `manifest.yaml` last so
its index matches what was written. Emit YAML with block style and **preserve key order** for
human readability (do not sort keys). Then either keep the directory form or zip it into a
`.feedpak` archive. A round-trip (write → read → write) **SHOULD** be lossless for all
recognised fields and **MUST** preserve unrecognised ones.

---

## 9. Extending the format

feedpak is designed to be extended without breaking older Readers. The conventions below are
how `lyrics`, `stems`, `drum_tab`, `song_timeline`, and `notation` were each added.

### 9.1. The golden rule: manifest opt-in, file off to the side

1. **Drop a new file** alongside the standard ones (`drums.json`, `keys.json`, …).
2. **Add a manifest key** that *points at* that file (`drum_tab: drum_tab.json`).
3. **Gate consumers on the manifest key.** If the key is absent, do nothing. Never
   auto-discover by filename — that breaks the "manifest is the index" rule ([§2.2](#22-three-core-rules)).

Older Readers ignore the unknown key; new consumers act on it. No coordination with other
implementations is required.

### 9.2. Naming conventions

- **Manifest keys:** `snake_case`, descriptive; singular for one value (`lyrics`, `cover`,
  `drum_tab`), plural for lists (`stems`, `arrangements`).
- **Filenames:** lowercase; JSON (`.json`) or JSONC (`.jsonc`) for structured data, audio in a baseline-or-recommended format (`.ogg`/`.wav`, or `.mp3`/`.flac`/`.opus` — see [§5.3.2](#532-audio-formats--baseline-dispatch-and-portability)), JPEG/PNG for images.
- **JSON fields:** short names for hot-path data streamed many times (`t`, `s`, `f`); long names
  for one-off metadata.
- **Time fields:** always `t` or `time`, always seconds as floats.
- **Ids/indexes:** stable, filesystem-safe, lowercase.

### 9.3. Always include `version`

Every new **object-shaped** side-file **SHOULD** carry `"version": 1`. It is free insurance: a
later incompatible change becomes `version: 2`, and old consumers can branch or fall back
gracefully. (The legacy `lyrics.json` array is the lone exception — see
[§7.1](#71-lyricsjson).)

### 9.4. Stay backward-compatible

- **Adding fields** is always safe (older Readers ignore them) — release as a **minor** format bump.
- **Removing fields** breaks older Readers — do not; release only under a **major** bump.
- **Repurposing fields** (changing meaning or units) is the most dangerous — bump the side-file
  `version` (and the format major if it is structural) and branch. Prefer adding a new field and
  sunsetting the old one over a version or two.

### 9.5. What does NOT belong in a feedpak

A feedpak holds the song's **authored data** only. The following **MUST NOT** be written into a
package, because they vary by user or machine:

- Per-machine settings (device picks, network addresses, hardware universes).
- UI state (zoom level, panel sizes).
- User progress, scores, or play counts.

---

## 10. Conformance checklist

A **conformant feedpak** (normative summary):

- [ ] Has a `manifest.yaml` at the root, UTF-8, parseable as YAML.
- [ ] Manifest has `title`, `artist`, `duration`, a non-empty `arrangements`, and a non-empty
      `stems`. (A notation-only arrangement counts toward `arrangements`; it may omit `file` —
      see [§5.2](#52-arrangements) — but does not relax the non-empty rule.)
- [ ] Every manifest pointer resolves to an existing file via a safe POSIX relative path.
- [ ] `feedpak_version`, if present, is a valid semver string.
- [ ] Every side-file validates against its schema and carries a `version` where this document
      requires one.
- [ ] Times are seconds; hot-path field names are unexpanded.

A **conformant Reader**:

- [ ] Accepts both directory and zip forms.
- [ ] Resolves all data through the manifest, never by filename scanning.
- [ ] Ignores (and, when re-emitting, preserves) unknown keys/files/fields.
- [ ] Applies the `feedpak_version` reader rules ([§4.2](#42-compatibility-policy)) and the
      `song_timeline` priority rule ([§7.4](#74-song_timelinejson)).
- [ ] Rejects paths that escape the package root.

---

## Appendix A (non-normative) — streaming and runtime notes

An application **MAY** transport feedpak data to a renderer over a streaming protocol (e.g. a
WebSocket) rather than handing over the on-disk files directly. Such protocols typically reuse
the same per-object field names defined here, often chunked into typed messages (song info,
notes, chords, beats, sections, lyrics, drum hits, notation measures, …). This is an
implementation choice and is **not** part of the format: the on-disk package defined by §2–§7 is
the sole normative artifact, and the byte-for-byte layout of any wire protocol is out of scope.

## Appendix B (non-normative) — media conventions

- **Stems:** OGG (Vorbis), ~`-q:a 5`, is the recommended default and baseline; other formats are
  allowed behind the decoder baseline + portability rule ([§5.3.2](#532-audio-formats--baseline-dispatch-and-portability)). Mono or stereo as the source dictates.
- **Preview clip:** a short clip (a few seconds) for hover-to-listen UIs; same format guidance as stems.
- **Cover art:** JPEG or PNG, square, 500–1500 px on a side.

## References

- [RFC 2119](https://www.rfc-editor.org/rfc/rfc2119) — Key words for use in RFCs.
- [RFC 8174](https://www.rfc-editor.org/rfc/rfc8174) — Ambiguity of uppercase vs lowercase.
- [Semantic Versioning 2.0.0](https://semver.org/).
- [YAML 1.2.2](https://spec.yaml.io/main/spec/1.2.2/).
- [JSON Schema 2020-12](https://json-schema.org/draft/2020-12/schema).
- [General MIDI percussion key map](https://en.wikipedia.org/wiki/General_MIDI#Percussion) (drum piece-id GM mapping).
