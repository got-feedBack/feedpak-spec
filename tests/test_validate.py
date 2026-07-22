# SPDX-License-Identifier: MIT
"""Unit + end-to-end tests for the feedpak reference validator (tools/validate.py).

These exercise the validator's real surface: path-safety, the semver gate, schema
validation of whole packs (directory and zip form), and the zip-slip guard. They also
re-validate the committed example packs so the examples can never silently rot.

Run: python -m pytest -q
"""
from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import validate  # noqa: E402  (path is set up just above)


# --------------------------------------------------------------------------- #
# Unit: safe_relpath (spec §2.2 path rule)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("p", ["a.json", "arrangements/lead.json", "stems/full.ogg"])
def test_safe_relpath_accepts_clean_relative_paths(p):
    assert validate.safe_relpath(p)


@pytest.mark.parametrize(
    "p",
    [
        "/abs/path",      # leading slash
        "../escape",      # parent segment
        "a/../b",         # interior parent segment
        "C:/drive",       # drive letter / colon
        "a\\b",           # backslash
        "a//b",           # empty segment
        "",               # empty
        ":stream",        # colon (NTFS stream)
    ],
)
def test_safe_relpath_rejects_unsafe_paths(p):
    assert not validate.safe_relpath(p)


# --------------------------------------------------------------------------- #
# Unit: semver gate (shared with the manifest schema)
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("v", ["1.0.0", "1.2.0", "10.20.30", "1.0.0-rc.1", "2.0.0+build.5"])
def test_semver_accepts_valid(v):
    assert validate.SEMVER_RE.match(v)


@pytest.mark.parametrize("v", ["1.0", "x", "1.0.0-01", "01.0.0", "1.0.0.0", ""])
def test_semver_rejects_invalid(v):
    assert not validate.SEMVER_RE.match(v)


# --------------------------------------------------------------------------- #
# Helpers to build packs on the fly
# --------------------------------------------------------------------------- #
def _base_manifest() -> dict:
    return {
        "feedpak_version": "1.2.0",
        "title": "Test",
        "artist": "Tester",
        "duration": 1.0,
        "arrangements": [{"id": "lead", "file": "arrangements/lead.json"}],
        "stems": [{"id": "full", "file": "stems/full.ogg", "default": True}],
    }


def _make_pack(root: Path, manifest: dict, *, lead: dict | None = None,
               extra: dict[str, str] | None = None) -> Path:
    (root / "arrangements").mkdir(parents=True, exist_ok=True)
    (root / "stems").mkdir(parents=True, exist_ok=True)
    (root / "arrangements" / "lead.json").write_text(
        json.dumps(lead if lead is not None else {"notes": [{"t": 0.0, "s": 0, "f": 0}]}),
        encoding="utf-8",
    )
    (root / "stems" / "full.ogg").write_bytes(b"OggS\x00fake")
    for rel, content in (extra or {}).items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
    (root / "manifest.yaml").write_text(yaml.safe_dump(manifest), encoding="utf-8")
    return root


# --------------------------------------------------------------------------- #
# End-to-end: directory form
# --------------------------------------------------------------------------- #
def test_minimal_built_pack_passes(tmp_path):
    pack = _make_pack(tmp_path / "ok.feedpak", _base_manifest())
    assert validate.resolve_and_validate(pack).ok


def test_missing_required_field_fails(tmp_path):
    m = _base_manifest()
    del m["duration"]
    pack = _make_pack(tmp_path / "bad.feedpak", m)
    rep = validate.resolve_and_validate(pack)
    assert not rep.ok
    assert any("duration" in e for e in rep.errors)


def test_unsafe_pointer_fails(tmp_path):
    m = _base_manifest()
    m["lyrics"] = "../escape.json"
    pack = _make_pack(tmp_path / "bad.feedpak", m)
    rep = validate.resolve_and_validate(pack)
    assert not rep.ok
    assert any("lyrics" in e for e in rep.errors)


def test_missing_pointer_target_fails(tmp_path):
    m = _base_manifest()
    m["lyrics"] = "lyrics.json"  # never written
    pack = _make_pack(tmp_path / "bad.feedpak", m)
    rep = validate.resolve_and_validate(pack)
    assert not rep.ok
    assert any("lyrics" in e and "missing" in e for e in rep.errors)


def test_empty_arrangement_tempos_fails(tmp_path):
    # spec §6.10: omit the key entirely; an empty array is non-conformant.
    pack = _make_pack(
        tmp_path / "bad.feedpak",
        _base_manifest(),
        lead={"notes": [{"t": 0.0, "s": 0, "f": 0}], "tempos": []},
    )
    rep = validate.resolve_and_validate(pack)
    assert not rep.ok
    assert any("tempos" in e for e in rep.errors)


def _notation(measures: list[dict]) -> str:
    return json.dumps({
        "version": 1,
        "instrument": "piano",
        "staves": [{"id": "rh", "clef": "G2"}],
        "measures": measures,
    })


def _beats(t: float) -> dict:
    return {"rh": {"voices": [{"v": 1, "beats": [
        {"t": t, "dur": 4, "notes": [{"midi": 67}]}]}]}}


def test_pickup_measure_idx_zero_passes(tmp_path):
    # spec §7.6: idx 0 is reserved for an opening pickup (anacrusis) measure.
    # Before 1.19.0 the schema required idx >= 1, so a pickup had no valid
    # number at all — the conventional 0 was rejected outright.
    m = _base_manifest()
    m["arrangements"].append(
        {"id": "keys", "type": "piano", "notation": "notation_keys.json"}
    )
    notation = _notation([
        {"idx": 0, "t": 0.0, "ts": [4, 4], "pickup": True, "staves": _beats(0.0)},
        {"idx": 1, "t": 0.5, "ts": [4, 4], "staves": _beats(0.5)},
    ])
    pack = _make_pack(tmp_path / "ok.feedpak", m, extra={"notation_keys.json": notation})
    assert validate.resolve_and_validate(pack).ok


@pytest.mark.parametrize(
    "measure",
    [
        {"idx": 0, "t": 0.0, "ts": [4, 4]},                     # flag absent
        {"idx": 0, "t": 0.0, "ts": [4, 4], "pickup": False},    # flag explicitly false
    ],
)
def test_pickup_measure_idx_zero_without_pickup_fails(tmp_path, measure):
    # The reservation is enforced one-directionally: idx 0 implies pickup:true,
    # so 0 cannot be used as a general off-by-one measure number — neither by
    # omitting the flag nor by setting it false.
    m = _base_manifest()
    m["arrangements"].append(
        {"id": "keys", "type": "piano", "notation": "notation_keys.json"}
    )
    notation = _notation([{**measure, "staves": _beats(0.0)}])
    pack = _make_pack(tmp_path / "bad.feedpak", m, extra={"notation_keys.json": notation})
    rep = validate.resolve_and_validate(pack)
    assert not rep.ok
    # pin the location and the mechanism, not just a substring anywhere:
    # jsonschema reports either the missing required property or the const.
    assert any(
        "measures/0" in e and ("required" in e or "True" in e) for e in rep.errors
    ), rep.errors


def test_pickup_measure_may_keep_its_source_numbering(tmp_path):
    # ...but the converse does NOT hold: a pickup MAY carry whatever number its
    # source gives it (some publishers number the anacrusis 1), so pickup:true
    # with idx 1 stays valid.
    m = _base_manifest()
    m["arrangements"].append(
        {"id": "keys", "type": "piano", "notation": "notation_keys.json"}
    )
    notation = _notation([
        {"idx": 1, "t": 0.0, "ts": [4, 4], "pickup": True, "staves": _beats(0.0)},
        {"idx": 2, "t": 0.5, "ts": [4, 4], "staves": _beats(0.5)},
    ])
    pack = _make_pack(tmp_path / "ok.feedpak", m, extra={"notation_keys.json": notation})
    assert validate.resolve_and_validate(pack).ok


def test_negative_measure_idx_still_fails(tmp_path):
    # The relaxation is to 0, not to arbitrary integers.
    m = _base_manifest()
    m["arrangements"].append(
        {"id": "keys", "type": "piano", "notation": "notation_keys.json"}
    )
    notation = _notation([{"idx": -1, "t": 0.0, "ts": [4, 4], "staves": _beats(0.0)}])
    pack = _make_pack(tmp_path / "bad.feedpak", m, extra={"notation_keys.json": notation})
    rep = validate.resolve_and_validate(pack)
    assert not rep.ok
    assert any("measures/0/idx" in e and "minimum" in e for e in rep.errors), rep.errors


def test_per_arrangement_drum_tab_is_validated(tmp_path):
    # A `type: drums` arrangement's own `drum_tab` pointer must be resolved and
    # schema-validated, not ignored. Here the pointed-at file is missing the
    # required `hits` array — pre-fix the validator never opened it and passed.
    m = _base_manifest()
    m["arrangements"].append(
        {"id": "drums", "name": "Drums", "type": "drums", "drum_tab": "drum_tab.json"}
    )
    bad_drum_tab = json.dumps({"version": 1})  # no "hits"
    pack = _make_pack(
        tmp_path / "bad.feedpak", m, extra={"drum_tab.json": bad_drum_tab}
    )
    rep = validate.resolve_and_validate(pack)
    assert not rep.ok
    assert any("drum_tab" in e and "hits" in e for e in rep.errors)


# --------------------------------------------------------------------------- #
# .jsonc support
# --------------------------------------------------------------------------- #
def test_jsonc_arrangement_passes(tmp_path):
    m = _base_manifest()
    m["arrangements"][0]["file"] = "arrangements/lead.jsonc"
    pack = _make_pack(
        tmp_path / "ok.feedpak",
        m,
        lead={"notes": [{"t": 0.0, "s": 0, "f": 0}]},
        extra={"arrangements/lead.jsonc": '{"notes": [{"t": 0.0, "s": 0, "f": 0}]}'},
    )
    rep = validate.resolve_and_validate(pack)
    assert rep.ok, rep.errors


def test_jsonc_arrangement_with_comments_passes(tmp_path):
    m = _base_manifest()
    m["arrangements"][0]["file"] = "arrangements/lead.jsonc"
    jsonc = """
    {
        // this is a line comment
        "notes": [
            { "t": 0.0, "s": 0, "f": 0 }  /* inline block comment */
        ]
    }
    """
    pack = _make_pack(
        tmp_path / "ok.feedpak",
        m,
        extra={"arrangements/lead.jsonc": jsonc},
    )
    rep = validate.resolve_and_validate(pack)
    assert rep.ok, rep.errors


def test_jsonc_side_file_passes(tmp_path):
    m = _base_manifest()
    m["song_timeline"] = "song_timeline.jsonc"
    jsonc = """
    {
        "version": 1,
        "tempos": [
            { "time": 0.0, "bpm": 120.0 }
        ]
    }
    """
    pack = _make_pack(
        tmp_path / "ok.feedpak",
        m,
        extra={"song_timeline.jsonc": jsonc},
    )
    rep = validate.resolve_and_validate(pack)
    assert rep.ok, rep.errors


def test_jsonc_malformed_comments_fails(tmp_path):
    m = _base_manifest()
    m["arrangements"][0]["file"] = "arrangements/lead.jsonc"
    # Unterminated block comment — should fail
    bad_jsonc = '{"notes": [{"t": 0.0, "s": 0, "f": 0} /* no end }'
    pack = _make_pack(
        tmp_path / "bad.feedpak",
        m,
        extra={"arrangements/lead.jsonc": bad_jsonc},
    )
    rep = validate.resolve_and_validate(pack)
    assert not rep.ok
    assert any("not valid JSON" in e for e in rep.errors)


def test_jsonc_comment_like_text_in_strings_preserved():
    # String values that contain // or /* */ must survive comment stripping intact.
    text = '''{
        "url": "https://example.com//path",   // real comment
        "note": "a /* not a comment */ b",
        "q": "he said \\"hi //\\" loudly"
    }'''
    data = validate._parse_jsonc(text)
    assert data == {
        "url": "https://example.com//path",
        "note": "a /* not a comment */ b",
        "q": 'he said "hi //" loudly',
    }


def test_jsonc_block_comment_does_not_merge_tokens():
    # A block comment between two number tokens must not be stripped to nothing
    # (1/*c*/2 -> 12); a comment is whitespace, so the result is invalid JSON (1 2).
    with pytest.raises(ValueError):
        validate._parse_jsonc("1/*c*/2")


def test_tempo_event_missing_bpm_fails(tmp_path):
    m = _base_manifest()
    m["song_timeline"] = "song_timeline.json"
    bad_timeline = json.dumps({"version": 1, "tempos": [{"time": 0.0}]})
    pack = _make_pack(
        tmp_path / "bad.feedpak", m, extra={"song_timeline.json": bad_timeline}
    )
    rep = validate.resolve_and_validate(pack)
    assert not rep.ok
    assert any("bpm" in e for e in rep.errors)


# --------------------------------------------------------------------------- #
# End-to-end: zip form + zip-slip guard
# --------------------------------------------------------------------------- #
def _zip_dir(src: Path, dest: Path, *, extra_arcname: str | None = None) -> Path:
    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in src.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(src).as_posix())
        if extra_arcname is not None:
            zf.writestr(extra_arcname, "malicious")
    return dest


def test_zip_form_valid_pack_passes(tmp_path):
    pack = _make_pack(tmp_path / "ok.feedpak", _base_manifest())
    z = _zip_dir(pack, tmp_path / "ok.feedpak.zip")
    assert validate.resolve_and_validate(z).ok


def test_zip_slip_entry_rejected(tmp_path):
    pack = _make_pack(tmp_path / "ok.feedpak", _base_manifest())
    z = _zip_dir(pack, tmp_path / "evil.zip", extra_arcname="../evil.txt")
    rep = validate.resolve_and_validate(z)
    assert not rep.ok
    assert any("unsafe path inside archive" in e for e in rep.errors)


# --------------------------------------------------------------------------- #
# Regression: the committed examples must always validate
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("name", ["minimal.feedpak", "extended.feedpak"])
def test_committed_examples_validate(name):
    rep = validate.resolve_and_validate(ROOT / "examples" / name)
    assert rep.ok, rep.errors
