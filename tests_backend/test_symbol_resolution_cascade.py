import json
import os
import sys
import time
import types
from pathlib import Path

import pandas as pd
import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.checkpoint.memory import MemorySaver

import backend.ai.agent.routing.regex as regex_module
from backend.ai.agent.routing.regex import CompanyExtraction, PeriodExtraction, RegexClass


_portfolio_stub = types.ModuleType("backend.portfolioConstruction.Portfolio")


class _StubPortfolio:
    pass


_portfolio_stub.Portfolio = _StubPortfolio
sys.modules.setdefault("backend.portfolioConstruction.Portfolio", _portfolio_stub)

_portfolio_graph_stub = types.ModuleType("backend.ai.tools.portfolio.PortfolioGraph")


class _StubPortfolioGraph:
    def __init__(self, *args, **kwargs):
        self.thread_id = "stub-portfolio"
        self.compiled = self

    def get_state(self, *args, **kwargs):
        return types.SimpleNamespace(next=[])

    def invoke(self, *args, **kwargs):
        return {}

    def register(self, *args, **kwargs):
        return None


_portfolio_graph_stub.PortfolioGraph = _StubPortfolioGraph
_portfolio_graph_stub.STATIC_NODES = {}
_portfolio_graph_stub.STATIC_EDGES = {}
sys.modules.setdefault("backend.ai.tools.portfolio.PortfolioGraph", _portfolio_graph_stub)

_constraints_builder_stub = types.ModuleType("backend.ai.tools.portfolio.constraints_builder")
_constraints_builder_stub.build_constraints_from_prompt = lambda *args, **kwargs: {"constraints": []}
sys.modules.setdefault("backend.ai.tools.portfolio.constraints_builder", _constraints_builder_stub)

_constraints_manager_stub = types.ModuleType("backend.ai.tools.portfolio.constraints_manager")
_constraints_manager_stub.merge_constraints = lambda existing, new: existing if existing is not None else new
sys.modules.setdefault("backend.ai.tools.portfolio.constraints_manager", _constraints_manager_stub)

import backend.ai.agent.workflow as workflow_module


FIXTURES_PATH = Path("tests_backend/fixtures/symbol_resolution_golden_set.json")


def _build_resolver() -> RegexClass:
    resolver = RegexClass.__new__(RegexClass)
    resolver.universe = pd.DataFrame(
        [
            {
                "ticker": "AAPL",
                "shortTicker": "AAPL",
                "longName": "Apple Inc.",
                "shortName": "Apple Inc.",
                "avgvolume3m": 45_621_310.0,
            },
            {
                "ticker": "J",
                "shortTicker": "J",
                "longName": "Jacobs Solutions Inc.",
                "shortName": "Jacobs Solutions Inc.",
                "avgvolume3m": 1_234_567.0,
            },
            {
                "ticker": "GOOGL",
                "shortTicker": "GOOGL",
                "longName": "Alphabet Inc.",
                "shortName": "Alphabet Inc.",
                "avgvolume3m": 32_353_422.0,
            },
            {
                "ticker": "AMZN",
                "shortTicker": "AMZN",
                "longName": "Amazon.com, Inc.",
                "shortName": "Amazon.com, Inc.",
                "avgvolume3m": 29_000_000.0,
            },
            {
                "ticker": "MSFT",
                "shortTicker": "MSFT",
                "longName": "Microsoft Corporation",
                "shortName": "Microsoft Corporation",
                "avgvolume3m": 33_424_477.0,
            },
            {
                "ticker": "TSLA",
                "shortTicker": "TSLA",
                "longName": "Tesla, Inc.",
                "shortName": "Tesla, Inc.",
                "avgvolume3m": 95_000_000.0,
            },
            {
                "ticker": "NVDA",
                "shortTicker": "NVDA",
                "longName": "NVIDIA Corporation",
                "shortName": "NVIDIA Corporation",
                "avgvolume3m": 173_089_045.0,
            },
            {
                "ticker": "BNP.PA",
                "shortTicker": "BNP",
                "longName": "BNP Paribas SA",
                "shortName": "BNP PARIBAS",
                "avgvolume3m": 3_100_000.0,
            },
            {
                "ticker": "GLE.PA",
                "shortTicker": "GLE",
                "longName": "Société Générale Société anonyme",
                "shortName": "SOCIETE GENERALE",
                "avgvolume3m": 2_700_000.0,
            },
            {
                "ticker": "RMS.PA",
                "shortTicker": "RMS",
                "longName": "Hermès International Société en commandite par actions",
                "shortName": "HERMES INTL",
                "avgvolume3m": 60_856.0,
            },
            {
                "ticker": "FHI",
                "shortTicker": "FHI",
                "longName": "Federated Hermes, Inc.",
                "shortName": "Federated Hermes, Inc.",
                "avgvolume3m": 648_194.0,
            },
            {
                "ticker": "MC.PA",
                "shortTicker": "MC",
                "longName": "LVMH Moët Hennessy - Louis Vuitton, Société Européenne",
                "shortName": "LVMH",
                "avgvolume3m": 468_324.0,
            },
            {
                "ticker": "ORA.PA",
                "shortTicker": "ORA",
                "longName": "Orange S.A.",
                "shortName": "ORANGE",
                "avgvolume3m": 4_487_734.0,
            },
            {
                "ticker": "OPL.WA",
                "shortTicker": "OPL",
                "longName": "Orange Polska S.A.",
                "shortName": "ORANGEPL",
                "avgvolume3m": 1_442_741.0,
            },
            {
                "ticker": "OBEL.BR",
                "shortTicker": "OBEL",
                "longName": "Orange Belgium S.A.",
                "shortName": "ORANGE BELGIUM",
                "avgvolume3m": 2_589.0,
            },
            {
                "ticker": "4554.TWO",
                "shortTicker": "4554",
                "longName": "Orange Electronic Co., Ltd.",
                "shortName": "ORANGE ELECTRONIC CO LTD",
                "avgvolume3m": 51_570.0,
            },
        ]
    )
    resolver._prepare_resolution_universe()
    resolver.external_alias_records = [
        {
            "alias": "Google",
            "tickers": ["GOOGL"],
            "source": "test_external_alias_table",
        }
    ]
    resolver._build_resolution_indexes()
    resolver.last_symbol_resolution = []
    resolver.model = None
    resolver.embeddings = None
    return resolver


def _build_live_resolver() -> RegexClass:
    return RegexClass()


def _load_golden_fixture() -> dict:
    with FIXTURES_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _candidate_tickers_from_resolution(resolution: dict | None) -> list[str]:
    if resolution is None:
        return []

    tickers = []
    selected_ticker = resolution.get("selected_ticker")
    if selected_ticker:
        tickers.append(selected_ticker)
    for candidate in resolution.get("candidates", []):
        ticker = candidate.get("ticker")
        if ticker:
            tickers.append(ticker)
    return list(dict.fromkeys(tickers))


def _build_large_scale_sample(universe: pd.DataFrame, target_rows: int = 1200, per_exchange: int = 25) -> pd.DataFrame:
    ranked = universe.copy()
    ranked = ranked.dropna(subset=["ticker", "longName"])
    ranked = ranked[ranked["ticker"].astype(str).str.strip() != ""]
    ranked = ranked[ranked["longName"].astype(str).str.strip() != ""]
    ranked["avgvolume3m"] = pd.to_numeric(ranked.get("avgvolume3m"), errors="coerce").fillna(0.0)
    ranked = ranked.sort_values(by=["avgvolume3m", "ticker"], ascending=[False, True])

    diverse = ranked.groupby("exchange", group_keys=False, sort=False).head(per_exchange)
    diverse = diverse.drop_duplicates(subset=["ticker"], keep="first")
    if len(diverse) < target_rows:
        remainder = ranked.loc[~ranked["ticker"].isin(diverse["ticker"])].head(target_rows - len(diverse))
        diverse = pd.concat([diverse, remainder], ignore_index=False)

    return diverse.head(target_rows).reset_index(drop=True)


def _build_case(case_type: str, input_text: str, expected_tickers: set[str], metadata: dict | None = None) -> dict:
    return {
        "case_type": case_type,
        "input": input_text,
        "expected_tickers": {ticker for ticker in expected_tickers if ticker},
        "metadata": metadata or {},
    }


def _resolve_consistency_case(resolver: RegexClass, case: dict) -> dict | None:
    case_type = case["case_type"]
    input_text = case["input"]

    if case_type == "free_text_ticker":
        candidates = resolver._extract_explicit_ticker_candidates(input_text)
        if not candidates:
            return None
        return resolver._resolve_candidate(candidates[0])

    if case_type == "free_text_name":
        entity = case["metadata"].get("entity")
        if not entity:
            return None
        return resolver._resolve_candidate(entity)

    return resolver._resolve_candidate(input_text)


def _compute_expected_outcome(resolver: RegexClass, input_text: str, fallback_tickers: set[str]) -> dict:
    acceptable = {ticker for ticker in fallback_tickers if ticker}
    deterministic = set()
    precedence_source = "fallback"

    if resolver._is_ticker_like(input_text):
        symbol_key = resolver._normalize_symbol_token(input_text)
        exact_ticker_rows = resolver._rows_for_lookup(resolver._ticker_to_indices, symbol_key)
        exact_tickers = set(exact_ticker_rows["ticker"].astype(str))
        if exact_tickers:
            return {
                "acceptable": exact_tickers,
                "deterministic": exact_tickers,
                "precedence_source": "exact_ticker",
            }

        exact_short_rows = resolver._rows_for_lookup(resolver._short_ticker_to_indices, symbol_key)
        exact_short_tickers = set(exact_short_rows["ticker"].astype(str))
        if exact_short_tickers:
            if len(exact_short_tickers) == 1:
                deterministic = set(exact_short_tickers)
            acceptable = exact_short_tickers
            precedence_source = "exact_short_ticker"
            return {
                "acceptable": acceptable,
                "deterministic": deterministic,
                "precedence_source": precedence_source,
            }

    if len(acceptable) == 1:
        deterministic = set(acceptable)

    return {
        "acceptable": acceptable,
        "deterministic": deterministic,
        "precedence_source": precedence_source,
    }


def _score_consistency_resolution(case: dict, resolution: dict | None) -> tuple[str, dict]:
    expected_tickers = case["expected_tickers"]
    deterministic_expected = set(case["metadata"].get("deterministic_expected", []))
    acceptable_expected = set(case["metadata"].get("acceptable_expected", expected_tickers))
    details = {
        "case_type": case["case_type"],
        "input": case["input"],
        "expected_tickers": sorted(expected_tickers),
        "deterministic_expected": sorted(deterministic_expected),
        "acceptable_expected": sorted(acceptable_expected),
        "metadata": case["metadata"],
    }
    if resolution is None:
        details["reason"] = "no_resolution"
        return "incorrect", details

    selected_ticker = resolution.get("selected_ticker")
    candidate_tickers = set(_candidate_tickers_from_resolution(resolution))
    multiple_matches = bool(resolution.get("multiple_matches"))

    details.update(
        {
            "selected_ticker": selected_ticker,
            "resolution_source": resolution.get("resolution_source"),
            "multiple_matches": multiple_matches,
            "candidate_tickers": sorted(candidate_tickers),
        }
    )

    acceptable_intersection = acceptable_expected.intersection(candidate_tickers)
    if deterministic_expected and selected_ticker in deterministic_expected and not multiple_matches:
        return "correct", details

    if not deterministic_expected and len(acceptable_expected) == 1 and selected_ticker in acceptable_expected and not multiple_matches:
        return "correct", details

    if acceptable_intersection and multiple_matches:
        return "ambiguous", details

    if selected_ticker in acceptable_expected and multiple_matches:
        return "ambiguous", details

    details["reason"] = "wrong_ticker"
    return "incorrect", details


def _build_large_scale_cases(resolver: RegexClass, sampled_rows: pd.DataFrame) -> list[dict]:
    universe = resolver.universe
    cases: list[dict] = []
    seen = set()

    def add_case(case_type: str, input_text: str, expected_tickers: set[str], metadata: dict | None = None):
        normalized_input = str(input_text)
        key = (case_type, normalized_input)
        if key in seen:
            return
        metadata = dict(metadata or {})
        expected_outcome = _compute_expected_outcome(resolver, normalized_input, expected_tickers)
        metadata["acceptable_expected"] = sorted(expected_outcome["acceptable"])
        metadata["deterministic_expected"] = sorted(expected_outcome["deterministic"])
        metadata["precedence_source"] = expected_outcome["precedence_source"]
        seen.add(key)
        cases.append(_build_case(case_type, normalized_input, expected_outcome["acceptable"], metadata))

    for _, row in sampled_rows.iterrows():
        ticker = str(row["ticker"])
        short_ticker = str(row.get("shortTicker") or "")
        long_name = str(row.get("longName") or "")
        short_name = str(row.get("shortName") or "")
        canonical_name = resolver._canonicalize_company_name(long_name)

        add_case("ticker_exact", ticker, {ticker}, {"ticker": ticker})

        if short_ticker:
            short_matches = set(
                universe.loc[universe["shortTickerKey"] == resolver._normalize_symbol_token(short_ticker), "ticker"].astype(str)
            )
            add_case("short_ticker", short_ticker, short_matches, {"ticker": ticker, "shortTicker": short_ticker})

        if long_name:
            long_name_matches = set(
                universe.loc[universe["normalizedLongName"] == resolver._normalize_entity_label(long_name), "ticker"].astype(str)
            )
            add_case("long_name", long_name, long_name_matches, {"ticker": ticker})

        if short_name:
            short_name_matches = set(
                universe.loc[universe["normalizedShortName"] == resolver._normalize_entity_label(short_name), "ticker"].astype(str)
            )
            add_case("short_name", short_name, short_name_matches, {"ticker": ticker})

        if canonical_name:
            canonical_matches = set(
                universe.loc[universe["canonicalLongName"] == canonical_name, "ticker"].astype(str)
            )
            add_case("canonical_name", canonical_name, canonical_matches, {"ticker": ticker, "canonical_name": canonical_name})

        add_case(
            "free_text_ticker",
            f"cours de {ticker}",
            {ticker},
            {"ticker": ticker, "template": "cours de {ticker}"},
        )
        add_case(
            "free_text_name",
            f"Donne-moi le prix de {long_name}",
            set(
                universe.loc[universe["normalizedLongName"] == resolver._normalize_entity_label(long_name), "ticker"].astype(str)
            ),
            {"ticker": ticker, "entity": long_name, "template": "Donne-moi le prix de {company}"},
        )

    return cases


def _score_resolver_business_case(case: dict, resolution: dict | None) -> dict:
    candidate_tickers = _candidate_tickers_from_resolution(resolution)
    expected_candidates = case.get("expected_candidates_contains", [])
    details = {
        "id": case["id"],
        "category": case["category"],
        "query": case["query"],
        "expected_ticker": case.get("expected_ticker"),
        "expected_ambiguous": bool(case.get("expected_ambiguous")),
        "expected_candidates_contains": expected_candidates,
        "selected_ticker": resolution.get("selected_ticker") if resolution else None,
        "resolution_source": resolution.get("resolution_source") if resolution else None,
        "multiple_matches": bool(resolution.get("multiple_matches")) if resolution else False,
        "candidate_tickers": candidate_tickers,
    }

    if resolution is None:
        details["status"] = "incorrect"
        details["reason"] = "no_resolution"
        return details

    if case.get("expected_ambiguous"):
        if resolution.get("multiple_matches") and set(expected_candidates).issubset(set(candidate_tickers)):
            details["status"] = "correct_ambiguous"
            return details
        details["status"] = "incorrect"
        details["reason"] = "expected_ambiguity_not_respected"
        return details

    expected_ticker = case.get("expected_ticker")
    if expected_ticker and resolution.get("selected_ticker") == expected_ticker and not resolution.get("multiple_matches"):
        details["status"] = "correct_exact"
        return details

    details["status"] = "incorrect"
    details["reason"] = "wrong_top1"
    return details


def _score_pipeline_case(case: dict, state: dict) -> dict:
    tool_args = state.get("tool_args", {})
    selected_symbol = tool_args.get("symbol")
    compare_symbols = [tool_args.get("symbol1"), tool_args.get("symbol2")]
    candidate_tickers = [candidate.get("ticker") for candidate in tool_args.get("symbol_candidates", []) if candidate.get("ticker")]
    if "symbol1_candidates" in tool_args:
        candidate_tickers.extend(candidate.get("ticker") for candidate in tool_args.get("symbol1_candidates", []) if candidate.get("ticker"))
    if "symbol2_candidates" in tool_args:
        candidate_tickers.extend(candidate.get("ticker") for candidate in tool_args.get("symbol2_candidates", []) if candidate.get("ticker"))
    candidate_tickers = list(dict.fromkeys(candidate_tickers))

    details = {
        "id": case["id"],
        "category": case["category"],
        "text": case["text"],
        "expected_route": case["expected_route"],
        "expected_intent": case["expected_intent"],
        "expected_symbol": case.get("expected_symbol"),
        "expected_symbols": case.get("expected_symbols", []),
        "expected_clarification": bool(case.get("expected_clarification")),
        "expected_candidates_contains": case.get("expected_candidates_contains", []),
        "route": state.get("route"),
        "intent": state.get("tool_intent"),
        "selected_symbol": selected_symbol,
        "compare_symbols": compare_symbols,
        "period": tool_args.get("period"),
        "needs_clarification": bool(state.get("needs_clarification")),
        "candidate_tickers": candidate_tickers,
    }

    if state.get("route") != case["expected_route"] or state.get("tool_intent") != case["expected_intent"]:
        details["status"] = "incorrect"
        details["reason"] = "wrong_route_or_intent"
        return details

    if case.get("expected_clarification"):
        if not state.get("needs_clarification"):
            details["status"] = "incorrect"
            details["reason"] = "clarification_missing"
            return details
        expected_candidates = set(case.get("expected_candidates_contains", []))
        if expected_candidates and not expected_candidates.issubset(set(candidate_tickers)):
            details["status"] = "incorrect"
            details["reason"] = "missing_expected_candidates"
            return details
        details["status"] = "correct_ambiguous"
        return details

    if state.get("needs_clarification"):
        details["status"] = "incorrect"
        details["reason"] = "unexpected_clarification"
        return details

    if case.get("expected_symbol"):
        if selected_symbol != case["expected_symbol"]:
            details["status"] = "incorrect"
            details["reason"] = "wrong_top1"
            return details

    if case.get("expected_symbols"):
        if set(compare_symbols) != set(case["expected_symbols"]):
            details["status"] = "incorrect"
            details["reason"] = "wrong_compare_symbols"
            return details

    if case.get("expected_period") and tool_args.get("period", "1y") != case["expected_period"]:
        details["status"] = "incorrect"
        details["reason"] = "wrong_period"
        return details

    details["status"] = "correct_exact"
    return details


def _summarize_business_results(results: list[dict]) -> dict:
    by_category: dict[str, dict] = {}
    overall = {
        "total": 0,
        "correct_exact": 0,
        "correct_ambiguous": 0,
        "incorrect": 0,
        "exact_cases": 0,
        "ambiguity_cases": 0,
    }

    for result in results:
        category = result["category"]
        bucket = by_category.setdefault(
            category,
            {
                "total": 0,
                "correct_exact": 0,
                "correct_ambiguous": 0,
                "incorrect": 0,
                "exact_cases": 0,
                "ambiguity_cases": 0,
            },
        )
        bucket["total"] += 1
        overall["total"] += 1

        if result["status"] == "correct_exact":
            bucket["correct_exact"] += 1
            overall["correct_exact"] += 1
        elif result["status"] == "correct_ambiguous":
            bucket["correct_ambiguous"] += 1
            overall["correct_ambiguous"] += 1
        else:
            bucket["incorrect"] += 1
            overall["incorrect"] += 1

        if result.get("expected_ambiguous") or result.get("expected_clarification"):
            bucket["ambiguity_cases"] += 1
            overall["ambiguity_cases"] += 1
        else:
            bucket["exact_cases"] += 1
            overall["exact_cases"] += 1

    def enrich(stats: dict) -> dict:
        exact_cases = stats["exact_cases"]
        ambiguity_cases = stats["ambiguity_cases"]
        total = stats["total"]
        stats["precision_at_1"] = round(100.0 * stats["correct_exact"] / exact_cases, 2) if exact_cases else None
        stats["ambiguity_success_rate"] = round(100.0 * stats["correct_ambiguous"] / ambiguity_cases, 2) if ambiguity_cases else None
        stats["strict_success_rate"] = round(
            100.0 * (stats["correct_exact"] + stats["correct_ambiguous"]) / total, 2
        ) if total else 0.0
        return stats

    return {
        "overall": enrich(overall),
        "by_category": {category: enrich(stats) for category, stats in by_category.items()},
        "worst_errors": [result for result in results if result["status"] == "incorrect"][:20],
    }


class _FakeStructuredLLM:
    def __init__(self, schema, companies_by_text: dict[str, list[str]], period_by_text: dict[str, str]):
        self.schema = schema
        self.companies_by_text = companies_by_text
        self.period_by_text = period_by_text

    @staticmethod
    def _extract_text(prompt: str) -> str:
        if ":" not in prompt:
            return prompt.strip()
        return prompt.rsplit(":", 1)[-1].strip()

    def invoke(self, prompt: str):
        text = self._extract_text(prompt)
        if self.schema is CompanyExtraction:
            return CompanyExtraction(companies=list(self.companies_by_text.get(text, [])))
        if self.schema is PeriodExtraction:
            return PeriodExtraction(period=self.period_by_text.get(text, "1 an"))
        raise AssertionError(f"Unsupported schema: {self.schema}")


class _FakeGeneralLLM:
    def __init__(self, companies_by_text: dict[str, list[str]], period_by_text: dict[str, str]):
        self.companies_by_text = companies_by_text
        self.period_by_text = period_by_text

    def with_structured_output(self, schema):
        return _FakeStructuredLLM(schema, self.companies_by_text, self.period_by_text)

    def invoke(self, messages):
        return AIMessage(content="Réponse de test.")


class _FakeTool:
    def __init__(self, result):
        self._result = result

    def invoke(self, payload):
        if callable(self._result):
            return self._result(payload)
        return self._result


def _build_pipeline_app():
    graph = StateGraph(workflow_module.AgentState)
    graph.add_node("router", workflow_module.analyzer_node)
    graph.add_node("chat", workflow_module.chat_node)
    graph.add_node("price", workflow_module.price_node)
    graph.add_node("stats", workflow_module.stats_node)
    graph.add_node("compare", workflow_module.compare_node)
    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        workflow_module.router.route_from_router,
        {
            "chat": "chat",
            "price": "price",
            "stats": "stats",
            "compare": "compare",
        },
    )
    graph.add_edge("chat", END)
    graph.add_edge("price", END)
    graph.add_edge("stats", END)
    graph.add_edge("compare", END)
    return graph.compile(checkpointer=MemorySaver())


def test_exact_ticker_is_resolved_deterministically():
    resolver = _build_resolver()

    result = resolver._resolve_candidate("AAPL")

    assert result is not None
    assert result["selected_ticker"] == "AAPL"
    assert result["resolution_source"] == "exact_ticker"
    assert result["multiple_matches"] is False
    assert result["used_volume_fallback"] is False


def test_google_prefers_alias_before_embeddings():
    resolver = _build_resolver()

    result = resolver._resolve_candidate("Google")

    assert result is not None
    assert result["selected_ticker"] == "GOOGL"
    assert result["resolution_source"] == "external_alias_exact"
    assert result["multiple_matches"] is False


def test_hermes_resolves_via_structured_name_before_embeddings():
    resolver = _build_resolver()

    result = resolver._resolve_candidate("Hermès")

    assert result is not None
    assert result["selected_ticker"] == "RMS.PA"
    assert result["resolution_source"] == "derived_form_exact"
    assert result["multiple_matches"] is False


def test_orange_remains_ambiguous_when_multiple_structured_matches_exist():
    resolver = _build_resolver()

    result = resolver._resolve_candidate("Orange")

    assert result is not None
    assert result["multiple_matches"] is True
    candidate_tickers = [candidate["ticker"] for candidate in result["candidates"]]
    assert "ORA.PA" in candidate_tickers
    assert "OPL.WA" in candidate_tickers


def test_explicit_ticker_tokens_are_extracted_from_free_text():
    resolver = _build_resolver()

    candidates = resolver._extract_explicit_ticker_candidates("Tu peux me dire le cours de AAPL ?")

    assert candidates == ["AAPL"]


def test_french_elision_does_not_inject_single_letter_ticker_candidates():
    resolver = _build_resolver()

    ascii_candidates = resolver._extract_explicit_ticker_candidates("J'aimerais le prix de AAPL")
    smart_candidates = resolver._extract_explicit_ticker_candidates("J’aimerais le prix de AAPL")

    assert ascii_candidates == ["AAPL"]
    assert smart_candidates == ["AAPL"]


def test_french_elision_filter_keeps_explicit_single_letter_ticker_when_isolated():
    resolver = _build_resolver()

    candidates = resolver._extract_explicit_ticker_candidates("prix de J")

    assert candidates == ["J"]


def test_external_alias_can_return_multiple_tickers_when_alias_is_ambiguous():
    resolver = _build_resolver()
    resolver.external_alias_records = [
        {
            "alias": "Orange Brand",
            "tickers": ["ORA.PA", "OPL.WA"],
            "source": "test_external_alias_table",
        }
    ]
    resolver._build_resolution_indexes()

    result = resolver._resolve_candidate("Orange Brand")

    assert result is not None
    assert result["resolution_source"] == "ambiguous_external_alias_exact"
    assert result["multiple_matches"] is True
    candidate_tickers = [candidate["ticker"] for candidate in result["candidates"]]
    assert "ORA.PA" in candidate_tickers
    assert "OPL.WA" in candidate_tickers


def test_structured_text_fallback_recovers_entity_when_llm_returns_nothing(monkeypatch):
    resolver = _build_resolver()
    fake_llm = _FakeGeneralLLM({"Hermès vaut combien en bourse ?": []}, {"Hermès vaut combien en bourse ?": "1 an"})
    monkeypatch.setattr(regex_module, "general_llm", fake_llm)

    tickers, companies = resolver.extract_symbols("Hermès vaut combien en bourse ?")

    assert tickers == ["RMS.PA"]
    assert companies == ["Hermès International Société en commandite par actions"]


def test_consolidation_removes_embedded_subentity_for_single_company_query(monkeypatch):
    resolver = _build_resolver()
    fake_llm = _FakeGeneralLLM(
        {"Je veux le rendement annualisé de BNP Paribas sur 5 ans": ["BNP", "BNP Paribas"]},
        {"Je veux le rendement annualisé de BNP Paribas sur 5 ans": "5 ans"},
    )
    monkeypatch.setattr(regex_module, "general_llm", fake_llm)

    tickers, companies = resolver.extract_symbols("Je veux le rendement annualisé de BNP Paribas sur 5 ans")

    assert tickers == ["BNP.PA"]
    assert companies == ["BNP Paribas SA"]


def test_consolidation_keeps_two_distinct_companies_in_compare_query(monkeypatch):
    resolver = _build_resolver()
    fake_llm = _FakeGeneralLLM(
        {
            "Entre BNP Paribas et Société Générale, laquelle performe le mieux sur 5 ans ?": [
                "BNP",
                "BNP Paribas",
                "Société Générale",
            ]
        },
        {"Entre BNP Paribas et Société Générale, laquelle performe le mieux sur 5 ans ?": "5 ans"},
    )
    monkeypatch.setattr(regex_module, "general_llm", fake_llm)

    tickers, companies = resolver.extract_symbols("Entre BNP Paribas et Société Générale, laquelle performe le mieux sur 5 ans ?")

    assert tickers == ["BNP.PA", "GLE.PA"]
    assert companies == ["BNP Paribas SA", "Société Générale Société anonyme"]


def test_resolver_consistency_benchmark():
    started_at = time.perf_counter()
    resolver = _build_live_resolver()
    sampled_rows = _build_large_scale_sample(resolver.universe, target_rows=1200, per_exchange=25)
    assert len(sampled_rows) >= 1000

    cases = _build_large_scale_cases(resolver, sampled_rows)
    assert cases

    summary: dict[str, dict] = {}
    failures: list[dict] = []
    case_type_order: list[str] = []

    for case in cases:
        resolution = _resolve_consistency_case(resolver, case)
        status, details = _score_consistency_resolution(case, resolution)
        case_type = case["case_type"]
        if case_type not in summary:
            summary[case_type] = {"total": 0, "correct": 0, "ambiguous": 0, "incorrect": 0}
            case_type_order.append(case_type)
        summary[case_type]["total"] += 1
        summary[case_type][status] += 1
        if status == "incorrect" and len(failures) < 10:
            failures.append(details)

    metrics = {}
    for case_type in case_type_order:
        stats = summary[case_type]
        total = stats["total"]
        metrics[case_type] = {
            **stats,
            "accuracy": round(100.0 * stats["correct"] / total, 2),
            "acceptable_rate": round(100.0 * (stats["correct"] + stats["ambiguous"]) / total, 2),
        }

    overall_total = sum(stats["total"] for stats in summary.values())
    overall_correct = sum(stats["correct"] for stats in summary.values())
    overall_ambiguous = sum(stats["ambiguous"] for stats in summary.values())
    overall_incorrect = sum(stats["incorrect"] for stats in summary.values())
    benchmark_summary = {
        "sampled_companies": len(sampled_rows),
        "total_cases": overall_total,
        "overall_accuracy": round(100.0 * overall_correct / overall_total, 2),
        "overall_acceptable_rate": round(100.0 * (overall_correct + overall_ambiguous) / overall_total, 2),
        "overall_ambiguous_rate": round(100.0 * overall_ambiguous / overall_total, 2),
        "overall_failure_rate": round(100.0 * overall_incorrect / overall_total, 2),
        "metrics_by_case_type": metrics,
        "failures": failures,
        "elapsed_seconds": round(time.perf_counter() - started_at, 2),
    }

    print("RESOLVER_CONSISTENCY_BENCHMARK_SUMMARY")
    print(json.dumps(benchmark_summary, ensure_ascii=False, indent=2))

    assert metrics["ticker_exact"]["accuracy"] >= 99.0
    assert metrics["long_name"]["acceptable_rate"] >= 99.0
    assert metrics["canonical_name"]["acceptable_rate"] >= 95.0
    assert metrics["short_ticker"]["acceptable_rate"] >= 90.0
    assert metrics["short_name"]["acceptable_rate"] >= 95.0
    assert metrics["free_text_ticker"]["accuracy"] >= 99.0
    assert benchmark_summary["overall_acceptable_rate"] >= 95.0


def test_symbol_resolution_business_golden_benchmark():
    started_at = time.perf_counter()
    fixture = _load_golden_fixture()
    resolver = _build_live_resolver()

    results = []
    for case in fixture["resolver_cases"]:
        resolution = resolver._resolve_candidate(case["query"])
        results.append(_score_resolver_business_case(case, resolution))

    summary = _summarize_business_results(results)
    summary["elapsed_seconds"] = round(time.perf_counter() - started_at, 2)

    print("SYMBOL_RESOLUTION_BUSINESS_GOLDEN_SUMMARY")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    assert summary["overall"]["incorrect"] == 0
    assert summary["overall"]["precision_at_1"] >= 99.0
    assert summary["overall"]["ambiguity_success_rate"] >= 99.0


def test_symbol_resolution_short_ticker_collision_benchmark():
    started_at = time.perf_counter()
    fixture = _load_golden_fixture()
    resolver = _build_live_resolver()
    collision_cases = [case for case in fixture["resolver_cases"] if case["category"] == "shortTicker collision"]

    results = []
    for case in collision_cases:
        resolution = resolver._resolve_candidate(case["query"])
        results.append(_score_resolver_business_case(case, resolution))

    summary = _summarize_business_results(results)
    summary["elapsed_seconds"] = round(time.perf_counter() - started_at, 2)

    print("SHORT_TICKER_COLLISION_BENCHMARK_SUMMARY")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    assert summary["overall"]["incorrect"] == 0
    assert summary["overall"]["ambiguity_success_rate"] == 100.0


def test_symbol_resolution_full_pipeline_golden_benchmark(monkeypatch):
    started_at = time.perf_counter()
    fixture = _load_golden_fixture()
    pipeline_cases = fixture["pipeline_cases"]
    companies_by_text = {case["text"]: case.get("llm_companies", []) for case in pipeline_cases}
    period_by_text = {case["text"]: case.get("llm_period", "1 an") for case in pipeline_cases}
    fake_llm = _FakeGeneralLLM(companies_by_text, period_by_text)

    monkeypatch.setattr(regex_module, "general_llm", fake_llm)
    monkeypatch.setattr(workflow_module, "general_llm", fake_llm)
    monkeypatch.setattr(workflow_module, "get_last_price", _FakeTool(123.45))
    monkeypatch.setattr(
        workflow_module,
        "get_asset_stats",
        _FakeTool(
            {
                "annualized_return": "12.0%",
                "annualized_volatility": "18.0%",
                "annualized_sharpe": "0.67",
            }
        ),
    )
    monkeypatch.setattr(
        workflow_module,
        "get_compare",
        _FakeTool(
            (
                {
                    "annualized_return": "10.0%",
                    "annualized_volatility": "16.0%",
                    "annualized_sharpe": "0.63",
                },
                {
                    "annualized_return": "11.0%",
                    "annualized_volatility": "17.0%",
                    "annualized_sharpe": "0.65",
                },
            )
        ),
    )

    resolver = _build_live_resolver()
    app = _build_pipeline_app()
    results = []

    for index, case in enumerate(pipeline_cases):
        config = {"configurable": {"thread_id": f"golden-pipeline-{index}", "regex": resolver}}
        app.invoke({"messages": [HumanMessage(content=case["text"])]}, config=config)
        state = app.get_state(config).values
        results.append(_score_pipeline_case(case, state))

    summary = _summarize_business_results(results)
    summary["elapsed_seconds"] = round(time.perf_counter() - started_at, 2)

    print("FULL_PIPELINE_GOLDEN_SUMMARY")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

    assert summary["overall"]["incorrect"] == 0
    assert summary["overall"]["precision_at_1"] >= 99.0
    assert summary["overall"]["ambiguity_success_rate"] >= 99.0
