from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from tests.test_parameter_contract import make_library
from tools.build_docs_site import build_bundle, build_drug
from tools.fixture_context_i18n import CATALOG_PATH, load_fixture_context_i18n


ROOT = Path(__file__).resolve().parents[1]


def write_catalog(root: Path, payload: object) -> None:
    path = root / CATALOG_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(payload, allow_unicode=True), encoding="utf-8")


@pytest.fixture
def translated_library(tmp_path: Path) -> tuple[Path, dict]:
    folder = make_library(tmp_path)
    pk_path = folder / "pk.yml"
    pk = yaml.safe_load(pk_path.read_text(encoding="utf-8"))
    pk["simulation_validity"] = {
        "status": "clinical_hold",
        "reasons": ["The model is an approximation.", "The parameters were not jointly estimated."],
        "source_correction_date": "2026-10-28",
        "correction_notes": ["The source description was corrected."],
    }
    pk["fixture_limitations"] = [{
        "code": "test_approximation",
        "statement": "The model omits a distribution phase.",
        "source_id": "source_1",
        "source_locator": "Discussion, first paragraph",
    }]
    pk_path.write_text(yaml.safe_dump(pk), encoding="utf-8")
    payload = {
        "schema_version": "1",
        "drugs": {"omeprazole": {
            "reasons": [
                {"en": pk["simulation_validity"]["reasons"][0], "ja": "このモデルは近似です。"},
                {"en": pk["simulation_validity"]["reasons"][1], "ja": "パラメータは同時に推定されていません。"},
            ],
            "correction_notes": [{"en": pk["simulation_validity"]["correction_notes"][0], "ja": "出典の記述を訂正しました。"}],
            "fixture_limitations": {"test_approximation": {
                "en": pk["fixture_limitations"][0]["statement"], "ja": "このモデルには分布相がありません。",
            }},
        }},
    }
    write_catalog(tmp_path, payload)
    return tmp_path, payload


def test_bundle_adds_full_translations_and_preserves_canonical_english(translated_library):
    root, payload = translated_library
    path = root / "drugs/omeprazole/pk.yml"
    before = path.read_bytes()
    canonical = yaml.safe_load(before)
    bundle = build_bundle(root)
    drug = bundle["drugs"][0]
    assert drug["fixture_context_i18n"] == payload["drugs"]["omeprazole"]
    assert drug["simulation_validity"] == canonical["simulation_validity"]
    assert drug["fixture_limitations"] == canonical["fixture_limitations"]
    assert drug["raw"] == canonical.get("pk_raw", {})
    assert drug["parsed"] == canonical["pk_parsed"]
    assert drug["derived"] == canonical["derived"]
    assert CATALOG_PATH.as_posix() in bundle["source"]
    assert path.read_bytes() == before
    assert build_drug(path)["fixture_context_i18n"] == drug["fixture_context_i18n"]


def test_long_japanese_text_survives_without_truncation(translated_library):
    root, payload = translated_library
    text = "この文章は表示時に省略せず全文を保持します。" * 20
    payload["drugs"]["omeprazole"]["reasons"][0]["ja"] = text
    write_catalog(root, payload)
    assert build_bundle(root)["drugs"][0]["fixture_context_i18n"]["reasons"][0]["ja"] == text


def test_empty_minimal_library_needs_no_translation_file(tmp_path):
    make_library(tmp_path)
    assert build_bundle(tmp_path)["drugs"][0]["fixture_context_i18n"] == {
        "reasons": [], "correction_notes": [], "fixture_limitations": {},
    }


def test_missing_catalog_fails_when_any_canonical_context_exists(translated_library):
    root, _ = translated_library
    (root / CATALOG_PATH).unlink()
    with pytest.raises(ValueError, match="missing translations"):
        build_bundle(root)


@pytest.mark.parametrize("field", ["reasons", "correction_notes", "fixture_limitations"])
def test_missing_category_fails_instead_of_falling_back_to_english(translated_library, field):
    root, payload = translated_library
    del payload["drugs"]["omeprazole"][field]
    write_catalog(root, payload)
    with pytest.raises(ValueError, match=field):
        build_bundle(root)


@pytest.mark.parametrize("field", ["reasons", "correction_notes"])
@pytest.mark.parametrize("change", ["stale", "extra", "missing"])
def test_translation_arrays_track_english_exactly(translated_library, field, change):
    root, payload = translated_library
    texts = payload["drugs"]["omeprazole"][field]
    if change == "stale":
        texts[0]["en"] += " Changed."
    elif change == "extra":
        texts.append(deepcopy(texts[0]))
    else:
        texts.pop()
    write_catalog(root, payload)
    with pytest.raises(ValueError, match=field):
        build_bundle(root)


def test_reordered_reasons_fail(translated_library):
    root, payload = translated_library
    payload["drugs"]["omeprazole"]["reasons"].reverse()
    write_catalog(root, payload)
    with pytest.raises(ValueError, match="canonical English"):
        build_bundle(root)


def test_later_canonical_english_edit_requires_translation_review(translated_library):
    root, _ = translated_library
    path = root / "drugs/omeprazole/pk.yml"
    pk = yaml.safe_load(path.read_text(encoding="utf-8"))
    pk["fixture_limitations"][0]["statement"] += " Changed."
    path.write_text(yaml.safe_dump(pk), encoding="utf-8")
    with pytest.raises(ValueError, match="canonical English"):
        build_bundle(root)


@pytest.mark.parametrize("change", ["unknown_slug", "unknown_code", "missing_code"])
def test_unknown_or_missing_translation_targets_fail(translated_library, change):
    root, payload = translated_library
    if change == "unknown_slug":
        payload["drugs"]["unknown_drug"] = {}
    elif change == "unknown_code":
        payload["drugs"]["omeprazole"]["fixture_limitations"]["unknown_code"] = {"en": "Extra", "ja": "追加"}
    else:
        payload["drugs"]["omeprazole"]["fixture_limitations"] = {}
    write_catalog(root, payload)
    with pytest.raises(ValueError):
        build_bundle(root)


@pytest.mark.parametrize("payload", [
    None, [], {"schema_version": "2", "drugs": {}},
    {"schema_version": 1, "drugs": {}}, {"drugs": {}},
    {"schema_version": "1", "drugs": []},
    {"schema_version": "1", "drugs": {}, "unknown": True},
])
def test_invalid_catalog_schema_fails_even_for_empty_context(tmp_path, payload):
    make_library(tmp_path)
    write_catalog(tmp_path, payload)
    with pytest.raises(ValueError):
        build_bundle(tmp_path)


@pytest.mark.parametrize("field,value", [
    ("ja", ""), ("ja", " \n\t"), ("ja", None), ("ja", 1),
    ("en", ""), ("en", None), ("en", 1),
    ("unknown", "unexpected field"),
])
def test_invalid_localized_text_fails(translated_library, field, value):
    root, payload = translated_library
    payload["drugs"]["omeprazole"]["reasons"][0][field] = value
    write_catalog(root, payload)
    with pytest.raises(ValueError):
        build_bundle(root)


@pytest.mark.parametrize("field,value", [
    ("reasons", {}), ("reasons", ["not a language pair", "second item"]),
    ("fixture_limitations", []), ("unknown", []),
])
def test_invalid_drug_translation_shape_fails(translated_library, field, value):
    root, payload = translated_library
    payload["drugs"]["omeprazole"][field] = value
    write_catalog(root, payload)
    with pytest.raises(ValueError):
        build_bundle(root)


def test_real_catalog_covers_all_37_context_texts_without_altering_english():
    translations = load_fixture_context_i18n(ROOT)
    assert len(translations) == 37
    active = [entry for entry in translations.values() if any(entry.values())]
    assert len(active) == 13
    assert sum(len(entry["reasons"]) for entry in active) == 16
    assert sum(len(entry["correction_notes"]) for entry in active) == 11
    assert sum(len(entry["fixture_limitations"]) for entry in active) == 10
    bundle = build_bundle(ROOT)
    for drug in bundle["drugs"]:
        canonical = yaml.safe_load((ROOT / "drugs" / drug["slug"] / "pk.yml").read_text(encoding="utf-8"))
        assert drug["simulation_validity"] == canonical["simulation_validity"]
        assert drug["fixture_limitations"] == canonical.get("fixture_limitations", [])
        context = drug["fixture_context_i18n"]
        assert [item["en"] for item in context["reasons"]] == canonical["simulation_validity"].get("reasons", [])
        assert [item["en"] for item in context["correction_notes"]] == canonical["simulation_validity"].get("correction_notes", [])
        assert {code: item["en"] for code, item in context["fixture_limitations"].items()} == {
            item["code"]: item["statement"] for item in canonical.get("fixture_limitations", [])
        }
