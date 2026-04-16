from langchain_core.messages import AIMessage

from backend.ai.agent.workflow import compare_node, price_node, stats_node


def _assert_clarification(result: dict):
    assert result.get("needs_clarification") is True
    clarification_message = result.get("clarification_message")
    assert isinstance(clarification_message, str) and clarification_message.strip()

    messages = result.get("messages", [])
    assert messages
    assert isinstance(messages[-1], AIMessage)
    assert messages[-1].content == clarification_message


def test_price_requires_symbol():
    result = price_node({"tool_args": {"company": "Apple"}})
    _assert_clarification(result)


def test_stats_requires_symbol():
    result = stats_node({"tool_args": {"company": "Microsoft", "period": "1y"}})
    _assert_clarification(result)


def test_compare_requires_two_symbols():
    result = compare_node({"tool_args": {"symbol1": "AAPL", "company1": "Apple", "period": "1y"}})
    _assert_clarification(result)


def test_compare_rejects_identical_symbols():
    result = compare_node(
        {
            "tool_args": {
                "symbol1": "AAPL",
                "company1": "Apple",
                "symbol2": "AAPL",
                "company2": "Apple",
                "symbol1_confidence": 0.95,
                "symbol2_confidence": 0.95,
                "period": "1y",
            }
        }
    )
    _assert_clarification(result)


def test_price_rejects_low_entity_confidence():
    result = price_node(
        {
            "tool_args": {
                "symbol": "ORA.PA",
                "company": "Orange",
                "symbol_query": "Orange",
                "entity_confidence": 0.30,
                "symbol_ambiguous": False,
                "symbol_multiple_matches": True,
            }
        }
    )
    _assert_clarification(result)
