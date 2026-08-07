"""MCP-сервер семантического слоя: бизнес-термины -> схема БД.

Транспорт stdio, данные — glossary.yaml в корне проекта.
"""

from pathlib import Path
from typing import Any

import yaml
from fastmcp import FastMCP

GLOSSARY_PATH = Path(__file__).resolve().parent.parent / "glossary.yaml"

mcp = FastMCP("semantic-layer")


def _load_terms() -> list[dict[str, Any]]:
    # Читаем файл на каждый вызов: он крошечный, зато правки глоссария
    # видны без рестарта сервера.
    data = yaml.safe_load(GLOSSARY_PATH.read_text(encoding="utf-8"))
    return data["terms"]


def _normalize(value: str) -> str:
    return value.casefold().replace("ё", "е").strip()


def _names(entry: dict[str, Any]) -> list[str]:
    return [entry["term"], *entry.get("synonyms", [])]


def lookup_term(term: str) -> dict[str, Any]:
    """Каноническое определение бизнес-термина и его маппинг на данные.

    Возвращает term, synonyms, definition, mapping (source, table, field,
    filter — SQL-выражение для WHERE), опционально related_enrichment
    и notes. Ищет по каноническому имени и синонимам без учёта
    регистра: сначала точное совпадение, затем частичное.
    """
    query = _normalize(term)
    terms = _load_terms()
    for entry in terms:
        if any(_normalize(name) == query for name in _names(entry)):
            return entry
    for entry in terms:
        if any(
            query in _normalize(name) or _normalize(name) in query
            for name in _names(entry)
        ):
            return entry
    return {"error": f"Термин '{term}' не найден"}


def list_terms() -> str:
    """Все термины глоссария: по одной строке «термин — определение»."""
    return "\n".join(
        f"{entry['term']} — {entry['definition']}" for entry in _load_terms()
    )


mcp.tool(lookup_term)
mcp.tool(list_terms)

if __name__ == "__main__":
    mcp.run()
