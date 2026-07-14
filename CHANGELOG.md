# Changelog

All notable changes to the feedpak format specification are documented here.

The format is licensed under [CC0-1.0](LICENSE) (prose) and [MIT](LICENSE-CODE) (schemas,
examples, code). This file follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and the specification is versioned per [Semantic Versioning](https://semver.org/) — see
[spec §4](spec/feedpak-v1.md#4-versioning) for how format, side-file, and document versions
relate.

## [Unreleased]

### Added
- **Per-stem origin** (§5.3, §5.3.1) — a pack whose stems came from *different* sources can now
  describe itself. Four OPTIONAL keys on a `stems` entry:
  - `source` — `separated` | `authored` | `user`. Absent ⇒ inherit (`separated` by the pack's
    `stem_separation`, if it declares one). Same vocabulary shape as `lyrics_source` (§7.1).
  - `separation` — `{engine, model, version}` for **this** stem, overriding the pack-level
    `stem_separation`. Same triple, same semver semantics.
  - `edit` — `{tool, version}`: what produced or last modified a stem a **person** made. The
    human counterpart of `separation`, so a hand-made stem records what made it instead of being
    identified by the absence of engine metadata.
  - `derived_from` — the stem id an edited stem began life as, so a tool can warn before
    replacing the audio someone's edit was built on.

  `stem_separation` was one engine + model for the **whole** pack, so re-splitting a single stem
  with a better model, or hand-editing one stem among machine-separated ones, forced a writer to
  choose between *lying in the manifest* (stamping an engine over stems it never produced) and
  *destroying provenance* (dropping the key, discarding the truth about every stem nobody
  touched). Neither was acceptable. A pack produced by a single whole-pack split does not change
  shape at all: `stem_separation` keeps its meaning, and remains the default for stems that don't
  override it.

### Changed
- Docs (no format change): the §6.9 `tones.definitions` example now uses a neutral opaque
  placeholder instead of a source-specific field name. `definitions` is unchanged — still defined
  as raw, source-copied passthrough that Readers MUST preserve verbatim; only the illustrative
  field names in the example were genericised.

## [1.15.0] - 2026-07-13

Additive (MINOR) release: the stem id **`full`** is now reserved for the complete mixdown, and a
separated pack is asked to **keep** it rather than throw it away.

The format always had a home for the pre-separation mixdown — a stem — but §5.3 described `full`
as being "commonly replaced" by the per-instrument entries once a pack is split, which left the
mixdown nowhere to live. Source separation is lossy, so that lost audio is unrecoverable: summing
`guitar + bass + drums + vocals` does not reproduce the file they came from. In practice
implementations worked around this by inventing a *second* location for audio outside `stems`
(a top-level key pointing at an `original/` directory), which is exactly the redundancy an open
format should not have. Reserving `full` closes the gap with no new manifest surface at all.

### Added
- [§5.3](spec/feedpak-v1.md#the-full-stem--the-complete-mixdown) — the stem id `full` is
  **RESERVED** for the song's complete mixdown, and a Writer **MUST NOT** use it for anything
  else. A Writer that separates a pack into per-instrument stems **SHOULD** retain the `full`
  entry alongside them with `default: false`.
- Normative Reader rules for a pack that carries `full` *and* per-instrument stems: a Reader that
  sums stems **MUST NOT** include `full` in the sum (it already contains every instrument —
  summing it doubles the whole song), a per-stem mixer **SHOULD NOT** offer `full` as an
  instrument channel, and a Reader **SHOULD** prefer `full` over the summed stems when every
  instrument stem is at unity gain, since it is the same mix without the separation loss.
- `schemas/manifest.schema.json` documents the reserved id on `stemEntry.id`.
- `examples/extended.feedpak` is now a separated pack that retains `full` alongside `guitar`,
  `drums` and `vocals` (plus a `stem_separation` provenance block), exercising the new rule.

### Compatibility
- No manifest key is added, removed, renamed, or repurposed; a pack that predates this release
  stays valid, and `stems` semantics are unchanged for every id other than `full`.
- Safe for an older Reader **that honours `default`** — normative since 1.0.0 — which is exactly
  why the retained entry is specified as `default: false`: such a Reader does not play `full` on
  open, whatever else it does with the list. A Reader that sums every stem regardless of `default`
  was already mis-reading the format; the `default: false` requirement on `full` is what keeps
  even that Reader from doubling the mix on open.

## [1.14.0] - 2026-07-02

Additive (MINOR) release: optional **recording-identity keys**, so a pack can carry a stable,
open, exact identity for the recording it transcribes.

### Added
- New optional top-level manifest keys [`mbid`](spec/feedpak-v1.md#51-top-level-keys) — the
  MusicBrainz **Recording** MBID of the recording the pack transcribes (lowercase canonical
  UUID) — and [`isrc`](spec/feedpak-v1.md#51-top-level-keys) — its International Standard
  Recording Code. Both are author-set exact identity keys: a consumer SHOULD prefer them over
  free-text `artist`/`title` matching when grouping charts of the same recording or looking up
  external metadata, and SHOULD trust `mbid` when the two disagree. The stored ISRC is the bare
  12-character code — the hyphens in the common display form are presentation only, stripped
  when writing and before comparing.
  `schemas/manifest.schema.json` validates both formats.

### Compatibility
- Purely additive. Older Readers ignore both keys and still load. Nothing is removed, renamed,
  or repurposed.

## [1.13.0] - 2026-07-01

Additive (MINOR) release: an engine-agnostic **rig model** so a feedpak can carry tone information
natively — a structured, portable alternative to the opaque `tones.definitions` passthrough.

### Added
- New optional side-file [`rigs.json`](spec/feedpak-v1.md#79-rigsjson) (§7.9) and manifest `rigs`
  key: a pack-level library of rigs, each an ordered set of effect **blocks**. Every block splits
  *what it is* (`intent`, engine-independent) from *how to render it* (`realizations` — an ordered
  preference list over `nam` / `ir` / `plugin` / `builtin` engines, extensible to future ones). Open
  `role`/`kind`/`engine` vocabularies, an open normalized `params` map with optional time
  `automation`, and an optional `graph` for non-serial topology (parallel amps, wet/dry, stereo).
  `schemas/rigs.schema.json`.
- Arrangement [`tones`](spec/feedpak-v1.md#69-tones-optional) (§6.9) gains `base_rig` and
  `changes[].rig`, referencing a rig `id` in `rigs.json`. The legacy opaque `tones.definitions`
  passthrough is unchanged; a rig-aware Reader prefers the structured references.
- `examples/extended.feedpak` now ships a `rigs.json` and a `tones` block that exercises it.

### Compatibility
- Purely additive. Older Readers ignore the `rigs` key, `rigs.json`, and the new `base_rig`/`rig`
  fields, and still load. Nothing is removed, renamed, or repurposed.

## [1.12.0] - 2026-07-01

Additive (MINOR) release: album-grouping and genre metadata. Backward-compatible — a 1.0.0
(or 1.11.0) pack is also a valid 1.12.0 pack, and an older reader ignores the new optional keys.

### Added
- **Album grouping + genre metadata** ([spec §5.1](spec/feedpak-v1.md#51-top-level-keys)):
  four OPTIONAL, author-set top-level keys —
  - **`album_artist`** (string) — album artist for the release, so multi-artist / compilation
    albums group under one album identity; absent ⇒ falls back to `artist`.
  - **`track`** (int, 1-based) — track number within the album, for album playback order.
  - **`disc`** (int, 1-based, default 1) — disc number for multi-disc releases.
  - **`genres`** (list of strings, most specific first; `genres[0]` is primary) — genre labels.

  A reader predating 1.12.0 ignores all four.

## [1.11.0] - 2026-06-23

Additive (MINOR) release: multi-lingual lyric tracks, language tags, and language-tagged vocal
stems. Backward-compatible — a 1.0.0 pack is also a valid 1.11.0 pack, and an older reader ignores
the new optional keys and still loads the single `lyrics` pointer + stems as before.

### Added
- **Multi-lingual packs** ([spec §5.5](spec/feedpak-v1.md#55-lyric_tracks),
  [§5.1](spec/feedpak-v1.md#51-top-level-keys), [§5.3](spec/feedpak-v1.md#53-stems)): three OPTIONAL
  additive keys so a pack can express language and carry more than one lyric representation —
  - a top-level **`language`** ([BCP 47](https://www.rfc-editor.org/info/bcp47)) naming the song's
    primary sung language;
  - a per-stem **`language`** hint tagging a language-specific vocal stem (e.g. `vocals_ja` /
    `vocals_en` for a song with two sung-language recordings);
  - a **`lyric_tracks`** list of additional lyric files, each with `id`, `file`, `language`, and a
    `kind` of `original` / `transliteration` / `translation`, plus OPTIONAL `lyrics_source`,
    `lyric_transcription` provenance, and a `stem` pointer pairing a sung original with its vocal
    recording.

  Each track is an ordinary [`lyrics.json`](spec/feedpak-v1.md#71-lyricsjson)-shaped flat array, so
  **no new side-file schema** is introduced — only `schemas/manifest.schema.json` grows (a `bcp47`
  `$def`, a `lyricTrack` `$def`, the `lyric_tracks` array, and `language` on the manifest and on
  `$defs/stemEntry`). The legacy single `lyrics` pointer is unchanged: when `lyric_tracks` is absent
  a reader behaves exactly as before, and when present a writer SHOULD still point `lyrics` at the
  primary-language `original` track's file for pre-1.11.0 readers. Exercised by the extended example
  (an English original + a Japanese translation + a romaji transliteration, and a `language`-tagged
  `full` stem).

### Changed
- CI (no format change): the version-consistency guard (`tools/check_versions.py`) now covers
  every place the current version is written — the spec header, the §4.1 `feedpak_version`
  example + writer-SHOULD line, the README table **and** citation, and the extended example
  manifest, in addition to the newest `CHANGELOG.md` version. A missed spot during a bump now
  fails CI with a precise diff instead of drifting silently.
- Docs (no format change): the hand-editing guide's `.jsonc` section now spells out the two
  caveats — comments are the only relaxation (no trailing commas / JSON5), and a comment-bearing
  `.jsonc` needs a JSONC-aware reader, so keep distributed packs as comment-free `.json`.

## [1.10.0] - 2026-06-21

Additive (MINOR) release: a song-level harmony track. Backward-compatible — a 1.0.0 pack is also a
valid 1.10.0 pack, and older readers ignore the new optional manifest key + side-file.

### Added
- **Song-level harmony track — `harmony.json`** ([spec §7.8](spec/feedpak-v1.md#78-harmonyjson),
  manifest `harmony` key): the song's **intended** chord progression (the chords the song *is*,
  independent of what any arrangement plays) — reference/teaching data for fretboard-theory
  overlays, chord lyric lines, and practice-alongs. Time-ordered events applying until the next
  (same shape as `keys.json`): `t` (required), `root` (absolute note name; **`null` marks a
  no-chord/N.C. event**), `quality`, `rn` (Roman numeral relative to the active `keys.json` key,
  omitted when no key is active), and `bass` (slash-chord bass). Voicing-free (does not index
  arrangement chord templates) and **honesty-ruled** — a grader MUST NOT score against it. Defined
  as distinct from per-chord `fn` (as-played function): a Reader MAY derive one from the other, but
  neither is authoritative. `quality`/`fn.q` now reference a shared (recommended, not closed)
  chord-quality vocabulary so they stay interoperable. Schema:
  [`schemas/harmony.schema.json`](schemas/harmony.schema.json); exercised by the extended example
  (an Em→C→G→D7/F#→N.C. progression aligned to its Em/G `keys.json`). Implements #28.

## [1.9.0] - 2026-06-21

Additive (MINOR) release: audio stem formats beyond OGG. Backward-compatible — every existing
OGG-only pack stays valid, and a Reader that only decodes the baseline keeps working on any
portable pack.

### Added
- **Audio stem formats beyond OGG** ([spec §5.3.2](spec/feedpak-v1.md#532-audio-formats--baseline-dispatch-and-portability),
  [§1](spec/feedpak-v1.md#1-conventions)): stems are now dispatched **by file extension**, with a
  normative **decoder baseline** — a Reader **MUST** decode OGG (`.ogg`) and WAV (`.wav`) and
  **SHOULD** decode MP3 / FLAC / Opus. A new OPTIONAL `codec` hint on each `stems[]` entry
  disambiguates when an extension doesn't determine the codec (schema: `codec` on
  `$defs/stemEntry` in [`schemas/manifest.schema.json`](schemas/manifest.schema.json); exercised
  by the extended example's `full` stem as `codec: vorbis`). A **portability rule** requires a
  distributable pack to carry at least one baseline-format stem, so non-baseline stems are
  opportunistic enhancements rather than hard dependencies; a Reader **MUST** raise a clear error
  or fall back rather than fail silently on a format it can't decode. Proprietary/game formats
  (e.g. Wwise `.wem`) are explicitly **not** in the baseline, get **no** reference decoder, and
  **MUST NOT** be a distributable pack's only stem.

### Changed
- **§4.2 compatibility carve-out** now lists two opt-in file-format relaxations — the existing
  `.jsonc` extension and (new) audio stem formats beyond OGG (1.9.0 widens the baseline
  OGG→OGG+WAV and allows formats above it; since OGG was the only pre-1.9.0 guarantee, even a
  baseline WAV-only pack needs a 1.9.0 Reader) — both kept MINOR on the same "strictly opt-in,
  per-file; only a pack that actually uses it needs a supporting Reader" justification.

## [1.8.0] - 2026-06-21

Additive (MINOR) release: the two deferred per-chord harmony descriptors from the §6.3.1 FEP.
Backward-compatible — a 1.0.0 pack is also a valid 1.8.0 pack, and older readers ignore the new
optional fields.

### Added
- **Chord-template harmony descriptors** ([spec §6.6](spec/feedpak-v1.md#66-chord-templates)): two
  OPTIONAL template fields that annotate the chord shape for teaching/display, never grading (the
  **honesty rule** — a grader MUST NOT score them) — `caged` (the CAGED-system shape the fingering
  derives from: one of `C`/`A`/`G`/`E`/`D`) and `guideTones` (chromatic semitone offsets `0`–`11`
  above the chord **root** marking the quality-defining tones, typically the 3rd and 7th, e.g. a
  dominant-7 → `[4, 10]`). Both are key-independent shape properties, so they ride the template
  alongside `voicing`. Schema: `caged` (enum) + `guideTones` (int array) on `$defs/template` in
  [`schemas/arrangement.schema.json`](schemas/arrangement.schema.json); exercised by the extended
  example (the Em template → `caged: "E"`, `guideTones: [3]`). Completes the §6.3.1 FEP, whose
  `caged`/`guideTones` were deferred in 1.7.0.

## [1.7.0] - 2026-06-21

Additive (MINOR) release: per-chord harmony annotations. Backward-compatible — a 1.0.0 pack is also
a valid 1.7.0 pack, and older readers ignore the new optional fields.

### Added
- **Per-chord harmony annotations** ([spec §6.3.1](spec/feedpak-v1.md#631-harmonic-function-fn),
  [§6.6](spec/feedpak-v1.md#66-chord-templates)): two OPTIONAL fields that annotate a chord's
  harmony for teaching/display, never grading (the **honesty rule** — a grader MUST NOT score
  them) — `fn` on the chord **instance** (`{rn, q, deg}`: Roman-numeral label, quality token, and
  the chord root's chromatic offset `0`–`11` above the active [`keys.json`](spec/feedpak-v1.md#77-keysjson)
  tonic, mirroring `sd`; the chord's *as-played* function, derivable so a Reader MAY compute it),
  and `voicing` on the chord **template** (a key-independent voicing-type string, e.g. `open` /
  `shell` / `drop2`). Function rides the instance and voicing the template because the same shape
  recurs across keys. `fn`'s prose notes its boundary with a future song-level harmony track (the
  *intended* progression). Schema: `fn` on `$defs/chord` and `voicing` on `$defs/template` in
  [`schemas/arrangement.schema.json`](schemas/arrangement.schema.json); exercised by the extended
  example (an Em chord as `vi` in G major). `caged` and `guideTones` from the FEP are deferred.

## [1.6.0] - 2026-06-21

MINOR release under the new §4.2 *opt-in file-format relaxation* carve-out: the `.jsonc`
data-file extension (comment-annotated JSON), plus a docs-site version banner. No existing pack is
affected, and a comment-free `.jsonc` file is plain JSON — but a `.jsonc` file that actually
contains comments is **not** readable by a strict-JSON-only Reader; it requires a JSONC-aware
Reader. This is why `.jsonc` ships under an explicit, bounded carve-out rather than the ordinary
"older Readers keep working" minor rule (see the JSONC bullet below and spec §4.2 / §8).

### Added
- Docs site (no format change): a build-time version banner. The site now stamps the newest
  released `CHANGELOG.md` version (`SPEC_VERSION` env → `mkdocs.yml` `extra.spec_version` →
  `overrides/main.html`) into a top announcement bar, so the displayed version is deterministic
  and no longer depends on Material's client-side GitHub-release widget (which is cached in the
  browser's localStorage and could lag a release).
- **JSONC support** ([§2.2](spec/feedpak-v1.md#22-three-core-rules),
  [§3](spec/feedpak-v1.md#3-encodings-and-conventions),
  [§8](spec/feedpak-v1.md#8-reading-and-writing)): `.jsonc` files (C-style-commented JSON) are
  now accepted anywhere `.json` files are specified. Hand-edited data files MAY use the `.jsonc`
  extension to signal that they contain comments; Readers strip comments before parsing, and
  Writers SHOULD preserve them on round-trip. Only comments are permitted — trailing commas and
  other JSON5-style relaxations are not; after comment removal a `.jsonc` file MUST be strict JSON.
  The reference validator (`tools/validate.py`) parses `.jsonc` files accordingly. Shipped as a
  MINOR bump under the §4.2 opt-in-relaxation carve-out: no existing pack is affected, and a
  comment-free `.jsonc` file is plain JSON, but a `.jsonc` file that contains comments is readable
  only by Readers that implement the comment-stripping step (a plain JSON parser errors on `//`),
  so a Writer needing maximum reader compatibility SHOULD keep data files as comment-free `.json`.

## [1.5.0] - 2026-06-21

Additive (MINOR) release: per-note teaching marks. Backward-compatible — a 1.0.0 pack is also a
valid 1.5.0 pack, and older readers ignore the new optional note fields.

### Added
- **Per-note teaching marks** ([spec §6.2.2](spec/feedpak-v1.md#622-teaching-marks-fg-ch-sd)):
  three OPTIONAL note fields that annotate how a note is taught or displayed, never whether it was
  played correctly (the **honesty rule** — graders MUST NOT score them) — `fg` (fret-hand finger,
  `-1` unset / `0` thumb / `1`–`4` index→pinky, same convention as `template.fingers`), `ch`
  (strum-group key: notes sharing a value `≥ 0` are one strum/rake gesture, with `pkd` giving
  direction), and `sd` (scale degree as a chromatic offset `0`–`11` above the active
  [`keys.json`](spec/feedpak-v1.md#77-keysjson) tonic; derivable, so a Reader MAY compute it).
  Schema: `fg` / `ch` / `sd` on `$defs/note` in
  [`schemas/arrangement.schema.json`](schemas/arrangement.schema.json); exercised by the extended
  example pack (an Em-triad rake grouped by `ch`).

## [1.4.0] - 2026-06-20

Additive (MINOR) release: per-note bend shape. Backward-compatible — a 1.0.0 pack is also a valid
1.4.0 pack, and older readers ignore the new optional note fields.

### Added
- **Per-note bend shape** ([spec §6.2.1](spec/feedpak-v1.md#621-bend-shape-bt-bnv)): two OPTIONAL
  note fields complementing the scalar `bn` peak — `bt` (bend intent: up / release / pre-bend /
  pre-bend-release / round-trip) and `bnv` (a time-stamped `[{t, v}]` bend curve). Lets renderers
  draw the bend arc and graders judge the right pitch over the note. Schema: `bt` + `bnv` on
  `$defs/note` in [`schemas/arrangement.schema.json`](schemas/arrangement.schema.json); exercised
  by the extended example pack.

### Fixed
- §5.2 `tuning`: corrected the accepted-length range from "4–7 (4 = bass)" to **4–8**
  (4–6 = bass, 6–8 = extended-range guitar). 6-string bass and 7/8-string guitar were
  already permitted by the schema (`tuning` has no `maxItems`, note `s` has no maximum)
  and by the "Readers MUST NOT hard-code length 6" rule, but the prose under-stated the
  upper bound. Editorial clarification only — no on-disk format change.

## [1.3.0] - 2026-06-20

Tooling, docs, and example release — no on-disk format change (a 1.2.0 pack is also a valid
1.3.0 pack). Bundles the repository's testing/CI, the documentation site, release automation,
and a worked keyboard-notation example.

### Added
- Repository CI/CD (no format change): a `pytest` test suite for the reference validator
  (`tests/`), a Python 3.10–3.13 matrix and a `ruff` lint job in the validate workflow, and a
  GitHub Pages workflow that publishes the JSON Schemas so their `$id` URLs resolve. (Release
  automation is described in its own bullet below.)
- Docs site (no format change): the GitHub Pages site is now built with MkDocs Material
  (light/dark theme, search, rendered spec/hand-editing/changelog). `tools/gen_docs.py` assembles
  the site from the canonical sources and copies the schemas in verbatim so their hosted URLs are
  unchanged.
- Example (no format change): the extended pack now includes a notation-only `keys` arrangement
  (`type: piano`) with a two-stave `notation_<id>.json` part, so the §7.6 standard-notation /
  keyboard-arrangement path is exercised by the validator and CI.
- Release automation (no format change): a reviewed version bump now cuts its GitHub Release
  automatically on merge to `main` (idempotent release-on-merge), replacing the manual
  tag-triggered flow. A `tools/check_versions.py` CI guard enforces that the spec header, the
  README table, and the newest released `CHANGELOG.md` version stay in lockstep.

## [1.2.0] - 2026-06-20

Additive (MINOR) release: new optional song-level and per-arrangement timing data, all
backward-compatible with 1.0.0/1.1.0 readers.

### Added
- **Song-level `tempos` and `time_signatures`** in
  [`song_timeline.json`](spec/feedpak-v1.md#74-song_timelinejson) ([spec §7.4](spec/feedpak-v1.md#74-song_timelinejson)):
  two OPTIONAL time-ordered event arrays giving the song-wide tempo (`{time, bpm}`) and meter
  (`{time, ts: [num, den]}`) maps. Each event applies until the next, like `keys.json`. This gives
  guitar/game consumers a song-wide BPM and meter that previously existed only per-measure inside
  notation files. The file's `version` stays `1`.
- **Per-arrangement `tempos` override** ([spec §6.10](spec/feedpak-v1.md#610-per-arrangement-tempo-optional)):
  an arrangement JSON MAY carry its own `tempos` map; when present a Reader uses it for that chart
  and ignores the song-level tempo. Mirrors the §7.4 side-file-priority rule.
- **`keys.json` disambiguation note** ([spec §7.7](spec/feedpak-v1.md#77-keysjson)): clarifies that
  the key/scale track is instrument-independent and unrelated to a keyboard arrangement — a
  guitar-only pack can signal key changes with no keyboard part. No schema change.
- Schema and example updates: `tempos`/`time_signatures` in
  [`schemas/song-timeline.schema.json`](schemas/song-timeline.schema.json), a `$defs/tempoEvent`
  and `tempos` property in [`schemas/arrangement.schema.json`](schemas/arrangement.schema.json),
  exercised by the extended example pack (song timeline + a per-chart bass override).

## [1.1.0] - 2026-06-20

Additive (MINOR) release: a new optional manifest field, backward-compatible with 1.0.0 readers.

### Added
- **Manifest `authors` list** ([spec §5.4](spec/feedpak-v1.md#54-authors)): an OPTIONAL
  top-level array crediting the people who authored or edited a feedpak — each entry carries a
  required `name` plus optional `role`, `email`, and `url`. Distinct from `artist` (the recording
  artist). Released as a MINOR bump (`feedpak_version` 1.1.0); older readers ignore the unknown
  key. Schema: a new `$defs/author` in [`schemas/manifest.schema.json`](schemas/manifest.schema.json);
  exercised by the extended example pack.
- [`spec/hand-editing.md`](spec/hand-editing.md) — a practical, vendor-neutral hand-editing
  guide (record/replace stems, edit metadata/cover/lyrics/tuning, re-zip for distribution),
  adapted from the feedback project's user guide with application-specifics removed. Linked
  from the README.

## [1.0.0] - 2026-06-19

Initial public release of the feedpak format specification.

### Added
- Normative specification: [`spec/feedpak-v1.md`](spec/feedpak-v1.md), with a Conformance
  section (RFC 2119 / RFC 8174), Reader/Writer roles, and a "this document is authoritative"
  stance independent of any implementation.
- **Built-in versioning**: top-level `feedpak_version` semver field in the manifest, a
  MAJOR/MINOR/PATCH compatibility policy, and explicit rules separating the format version,
  per-file side-file `version` integers, and the specification-document version.
- Manifest reference (§5), arrangement wire format (§6), and side-file schemas (§7):
  lyrics, vocal pitch, vocal pitch contour, song timeline, drum tab, notation, and
  key/scale annotations.
- JSON Schemas (Draft 2020-12) for the manifest and all structured files, in
  [`schemas/`](schemas/).
- Worked examples in [`examples/`](examples/): a minimal pack and an extended pack
  exercising the optional side-files.
- Reference validator [`tools/validate.py`](tools/validate.py), doubling as the CI gate.
- Repository governance: README, CONTRIBUTING (DCO + enhancement-proposal process),
  GOVERNANCE, CODE_OF_CONDUCT, and dual CC0/MIT licensing.

[Unreleased]: https://github.com/got-feedback/feedpak-spec/compare/v1.11.0...HEAD
[1.11.0]: https://github.com/got-feedback/feedpak-spec/compare/v1.10.0...v1.11.0
[1.10.0]: https://github.com/got-feedback/feedpak-spec/compare/v1.9.0...v1.10.0
[1.9.0]: https://github.com/got-feedback/feedpak-spec/compare/v1.8.0...v1.9.0
[1.8.0]: https://github.com/got-feedback/feedpak-spec/compare/v1.7.0...v1.8.0
[1.7.0]: https://github.com/got-feedback/feedpak-spec/compare/v1.6.0...v1.7.0
[1.6.0]: https://github.com/got-feedback/feedpak-spec/compare/v1.5.0...v1.6.0
[1.5.0]: https://github.com/got-feedback/feedpak-spec/compare/v1.4.0...v1.5.0
[1.4.0]: https://github.com/got-feedback/feedpak-spec/compare/v1.3.0...v1.4.0
[1.3.0]: https://github.com/got-feedback/feedpak-spec/compare/v1.2.0...v1.3.0
[1.2.0]: https://github.com/got-feedback/feedpak-spec/compare/v1.1.0...v1.2.0
[1.1.0]: https://github.com/got-feedback/feedpak-spec/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/got-feedback/feedpak-spec/releases/tag/v1.0.0
