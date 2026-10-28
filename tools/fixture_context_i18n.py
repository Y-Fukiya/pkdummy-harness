"""Validate display translations against the canonical English fixture context."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypedDict

import yaml


class LocalizedText(TypedDict):
    en: str
    ja: str


class FixtureContextI18n(TypedDict):
    reasons: list[LocalizedText]
    correction_notes: list[LocalizedText]
    fixture_limitations: dict[str, LocalizedText]


CATALOG_PATH = Path("docs/fixture-context-i18n.yml")
CONTEXT_FIELDS = {"reasons", "correction_notes", "fixture_limitations"}


def _mapping(value: Any, allowed: set[str], location: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{location}: expected a mapping")
    unknown = set(value) - allowed
    if unknown:
        raise ValueError(f"{location}: unknown fields {sorted(unknown, key=str)}")
    return value


def _strings(value: Any, location: str) -> list[str]:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ValueError(f"{location}: expected a list of nonempty strings")
    return value


def _localized(value: Any, english: str, location: str) -> LocalizedText:
    item = _mapping(value, {"en", "ja"}, location)
    for language in ("en", "ja"):
        if not isinstance(item.get(language), str) or not item[language].strip():
            raise ValueError(f"{location}.{language}: expected a nonempty string")
    if item["en"] != english:
        raise ValueError(f"{location}.en: does not match canonical English")
    return {"en": item["en"], "ja": item["ja"]}


def _localized_list(value: Any, english: list[str], location: str) -> list[LocalizedText]:
    if not isinstance(value, list) or len(value) != len(english):
        raise ValueError(f"{location}: expected {len(english)} translations in canonical order")
    return [
        _localized(item, original, f"{location}[{index}]")
        for index, (item, original) in enumerate(zip(value, english))
    ]


def load_fixture_context_i18n(root: Path) -> dict[str, FixtureContextI18n]:
    """Require complete, current translations without altering canonical records."""
    canonical: dict[str, tuple[list[str], list[str], dict[str, str]]] = {}
    for pk_path in sorted((root / "drugs").glob("*/pk.yml")):
        slug = pk_path.parent.name
        pk = yaml.safe_load(pk_path.read_text(encoding="utf-8"))
        validity = pk.get("simulation_validity") or {}
        reasons = _strings(validity.get("reasons", []), f"{slug}.reasons")
        notes = _strings(validity.get("correction_notes", []), f"{slug}.correction_notes")
        limitations: dict[str, str] = {}
        for limitation in pk.get("fixture_limitations") or []:
            code, statement = limitation.get("code"), limitation.get("statement")
            if not isinstance(code, str) or not code.strip() or code in limitations:
                raise ValueError(f"{slug}.fixture_limitations: missing or duplicate code")
            if not isinstance(statement, str) or not statement.strip():
                raise ValueError(f"{slug}.fixture_limitations.{code}: missing statement")
            limitations[code] = statement
        canonical[slug] = reasons, notes, limitations

    path = root / CATALOG_PATH
    if path.exists():
        payload = _mapping(
            yaml.safe_load(path.read_text(encoding="utf-8")),
            {"schema_version", "drugs"}, str(CATALOG_PATH),
        )
        if payload.get("schema_version") != "1":
            raise ValueError(f"{CATALOG_PATH}: unsupported schema_version; expected '1'")
        translations = _mapping(payload.get("drugs"), set(canonical), f"{CATALOG_PATH}.drugs")
    elif any(reasons or notes or limitations for reasons, notes, limitations in canonical.values()):
        raise ValueError(f"{CATALOG_PATH}: missing translations for canonical fixture context")
    else:
        translations = {}

    result: dict[str, FixtureContextI18n] = {}
    for slug, (reasons, notes, limitations) in canonical.items():
        location = f"{CATALOG_PATH}.drugs.{slug}"
        entry = _mapping(translations.get(slug, {}), CONTEXT_FIELDS, location)
        translated_limitations = _mapping(
            entry.get("fixture_limitations", {}), set(limitations), f"{location}.fixture_limitations",
        )
        if set(translated_limitations) != set(limitations):
            raise ValueError(f"{location}.fixture_limitations: codes must match canonical limitations")
        result[slug] = {
            "reasons": _localized_list(entry.get("reasons", []), reasons, f"{location}.reasons"),
            "correction_notes": _localized_list(
                entry.get("correction_notes", []), notes, f"{location}.correction_notes",
            ),
            "fixture_limitations": {
                code: _localized(translated_limitations[code], english, f"{location}.fixture_limitations.{code}")
                for code, english in limitations.items()
            },
        }
    return result
