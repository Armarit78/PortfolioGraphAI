from langchain_core.messages import HumanMessage

import backend.ai.agent.router as router_module
from backend.ai.agent.router import Router


class DummyRegex:
    def __init__(self, syms=None, companies=None, period="1y", resolutions=None):
        self._syms = syms or []
        self._companies = companies or []
        self._period = period
        self.last_symbol_resolution = resolutions or []

    def extract_symbols(self, text: str):
        return self._syms, self._companies

    def extract_period(self, text: str):
        return self._period


def _state(text: str):
    return {"messages": [HumanMessage(content=text)]}


def test_router_keeps_high_confidence_heuristic_decision(monkeypatch):
    semantic_called = {"value": False}

    class DummyHeuristicRouter:
        def __init__(self, last_message, syms, companies, period):
            self.result = {
                "route": "tool",
                "tool_intent": "price",
                "tool_args": {"symbol": "AAPL", "company": "Apple"},
                "confidence": 0.95,
                "source": "heuristic",
                "reason": "heuristic_scoring",
            }

    class DummySemanticRouter:
        def __init__(self, last_message, syms, companies, period):
            semantic_called["value"] = True

        def predict(self):
            return {
                "route": "tool",
                "tool_intent": "compare",
                "tool_args": {"symbol1": "AAPL", "symbol2": "MSFT", "period": "1y"},
                "confidence": 0.99,
                "source": "semantic_classifier",
                "reason": "classifier_prediction",
            }

    monkeypatch.setattr(router_module, "HeuristicRouter", DummyHeuristicRouter)
    monkeypatch.setattr(router_module, "SemanticRouter", DummySemanticRouter)

    router = Router()
    result = router.route(_state("Apple"), DummyRegex(["AAPL"], ["Apple"]))

    assert semantic_called["value"] is False
    assert result["tool_intent"] == "price"
    assert result["reason"] == "heuristic_high_confidence"


def test_router_prefers_semantic_when_above_threshold_and_better(monkeypatch):
    class DummyHeuristicRouter:
        def __init__(self, last_message, syms, companies, period):
            self.result = {
                "route": "tool",
                "tool_intent": "price",
                "tool_args": {"symbol": "AAPL", "company": "Apple"},
                "confidence": 0.56,
                "source": "heuristic",
                "reason": "heuristic_scoring",
            }

    class DummySemanticRouter:
        def __init__(self, last_message, syms, companies, period):
            pass

        def predict(self):
            return {
                "route": "tool",
                "tool_intent": "compare",
                "tool_args": {"symbol1": "AAPL", "symbol2": "MSFT", "period": "1y"},
                "confidence": 0.74,
                "source": "semantic_classifier",
                "reason": "classifier_prediction",
            }

    monkeypatch.setattr(router_module, "HeuristicRouter", DummyHeuristicRouter)
    monkeypatch.setattr(router_module, "SemanticRouter", DummySemanticRouter)

    router = Router()
    result = router.route(_state("Apple vs Microsoft"), DummyRegex(["AAPL", "MSFT"], ["Apple", "Microsoft"]))

    assert result["tool_intent"] == "compare"
    assert result["source"] == "semantic_classifier"


def test_router_falls_back_to_unknown_when_no_signal(monkeypatch):
    class DummyHeuristicRouter:
        def __init__(self, last_message, syms, companies, period):
            self.result = {
                "route": "chat",
                "tool_intent": "unknown",
                "tool_args": {},
                "confidence": 0.20,
                "source": "heuristic",
                "reason": "heuristic_scoring",
            }

    class DummySemanticRouter:
        def __init__(self, last_message, syms, companies, period):
            pass

        def predict(self):
            return {
                "route": "chat",
                "tool_intent": "unknown",
                "tool_args": {},
                "confidence": 0.10,
                "source": "semantic_classifier",
                "reason": "low_confidence_prediction",
            }

    monkeypatch.setattr(router_module, "HeuristicRouter", DummyHeuristicRouter)
    monkeypatch.setattr(router_module, "SemanticRouter", DummySemanticRouter)

    router = Router()
    result = router.route(_state("Bonjour"), DummyRegex())

    assert result["route"] == "chat"
    assert result["tool_intent"] == "unknown"
    assert result["reason"] == "ambiguous_after_validation"
