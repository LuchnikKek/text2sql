"""Тесты MCP-сервера семантического слоя (servers/semantic_layer.py)."""

from fastmcp import Client

from servers.semantic_layer import _load_terms, list_terms, lookup_term, mcp

REQUIRED_KEYS = {"term", "synonyms", "definition", "mapping"}
MAPPING_KEYS = {"source", "table", "field", "filter"}


def test_glossary_entries_complete() -> None:
    terms = _load_terms()
    assert len(terms) >= 5
    for entry in terms:
        assert REQUIRED_KEYS <= entry.keys(), entry.get("term")
        assert MAPPING_KEYS <= entry["mapping"].keys(), entry["term"]
        assert entry["synonyms"]


def test_lookup_by_canonical_name() -> None:
    entry = lookup_term("активный сотрудник")
    assert entry["mapping"]["source"] == "clickhouse"
    assert entry["mapping"]["table"] == "hr.employees"
    assert "termination_date IS NULL" in entry["mapping"]["filter"]


def test_lookup_by_synonym_case_insensitive() -> None:
    assert lookup_term("ФИНБЛОК")["term"] == "блок Финансы"


def test_lookup_partial_match() -> None:
    assert lookup_term("просрочил")["term"] == "просроченное назначение"


def test_lookup_unknown_term() -> None:
    result = lookup_term("зарплата за декабрь")
    assert "не найден" in result["error"]


def test_list_terms_one_line_per_term() -> None:
    lines = list_terms().splitlines()
    terms = _load_terms()
    assert len(lines) == len(terms)
    for entry in terms:
        assert any(line.startswith(entry["term"]) for line in lines)


async def test_tools_callable_via_mcp_protocol() -> None:
    async with Client(mcp) as client:
        tools = {tool.name for tool in await client.list_tools()}
        assert {"lookup_term", "list_terms"} <= tools
        result = await client.call_tool("lookup_term", {"term": "финблок"})
        assert result.data["term"] == "блок Финансы"
