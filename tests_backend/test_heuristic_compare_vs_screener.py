import pytest

from backend.ai.agent.routing.heuristic_routing import HeuristicRouter


@pytest.mark.parametrize(
    ("text", "syms", "expected_intent"),
    [
        ("Airbus vs Boeing", ["AIR.PA", "BA"], "compare"),
        ("Entre Apple et Tesla, lequel est le plus performant ?", ["AAPL", "TSLA"], "compare"),
        ("Microsoft ou Google lequel est le moins volatil ?", ["MSFT", "GOOGL"], "compare"),
        ("je veux un portefeuille avec Airbus et LVMH", ["AIR.PA", "MC.PA"], "screener"),
        ("Je cherche des actions US dans la tech", [], "screener"),
        ("Actions Europe faible volatilité", [], "screener"),
        ("je cherche des actions", [], "unknown"),
        ("donne-moi des actions", [], "unknown"),
        ("je veux investir", [], "unknown"),
    ],
)
def test_detect_tool_intent_compare_vs_screener(text, syms, expected_intent):
    assert HeuristicRouter.detect_tool_intent(text, syms) == expected_intent
