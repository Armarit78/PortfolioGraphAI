import time
import uuid

import pytest
import pytest_asyncio
from langchain_core.messages import AIMessage

from backend.ai.controller.AILocalController import LocalController


BENCHMARK_EXTENSIONS = [
    {
        "text": "compare Apple",
        "expected_route": "tool",
        "expected_intent": "compare",
        "expected_args": {"symbol1": "AAPL", "period": "1y"},
        "expected_clarification": True,
    },
    {
        "text": "prix de",
        "expected_route": "tool",
        "expected_intent": "price",
        "expected_args": {},
        "expected_clarification": True,
    },
    {
        "text": "prix de Orange",
        "expected_route": "tool",
        "expected_intent": "price",
        "expected_args": {},
        "expected_clarification": True,
    },
    {
        "text": "je cherche des actions",
        "expected_route": "chat",
        "expected_intent": "unknown",
        "expected_args": {},
    },
    {
        "text": "donne-moi des actions",
        "expected_route": "chat",
        "expected_intent": "unknown",
        "expected_args": {},
    },
    {
        "text": "je veux investir",
        "expected_route": "chat",
        "expected_intent": "unknown",
        "expected_args": {},
    },
    {
        "text": "je veux un portefeuille avec Airbus et LVMH",
        "expected_route": "tool",
        "expected_intent": "screener",
        "expected_args": {"description": "je veux un portefeuille avec Airbus et LVMH"},
    },
    {
        "text": "trouve des actions comme Nvidia",
        "expected_route": "chat",
        "expected_intent": "unknown",
        "expected_args": {},
    },
    {
        "text": "Airbus vs Boeing",
        "expected_route": "tool",
        "expected_intent": "compare",
        "expected_args": {"period": "1y"},
    },
    {
        "text": "Google",
        "expected_route": "tool",
        "expected_intent": "price",
        "expected_args": {"symbol": "GOOGL"},
    },
    {
        "text": "Hermès",
        "expected_route": "tool",
        "expected_intent": "price",
        "expected_args": {"symbol": "RMS.PA"},
    },
    {
        "text": "Je veux le prix de Apple",
        "expected_route": "tool",
        "expected_intent": "price",
        "expected_args": {"symbol": "AAPL"},
    },
]


def args_exact_match(expected, predicted, intent=None):
    if not expected and not predicted:
        return True

    if intent == "compare":
        expected_period = expected.get("period")
        if expected_period is not None and predicted.get("period", "1y") != expected_period:
            return False

        for key in ("symbol1", "symbol2"):
            if key in expected and predicted.get(key) != expected[key]:
                return False

        return True

    for key, value in expected.items():
        if predicted.get(key) != value:
            return False

    return True


def _last_ai_message(messages):
    ai_messages = [message for message in messages if isinstance(message, AIMessage)]
    return ai_messages[-1] if ai_messages else None


@pytest_asyncio.fixture(scope="module")
async def ai_instance():
    ai = LocalController()
    await ai.initialize()
    return ai


@pytest_asyncio.fixture
async def session_id(ai_instance):
    sid = str(uuid.uuid4())[:8]
    await ai_instance.create_chat(sid)
    return sid


async def _run_router_case(ai_instance, session_id, sample):
    response = await ai_instance.chat(session_id, sample["text"])
    time.sleep(2.0)

    if response.get("status") == "error":
        pytest.fail(f"Erreur API: {response.get('message')}")

    config = {"configurable": {"thread_id": session_id}}
    result_state = ai_instance.app.get_state(config)
    result = result_state.values

    pred_route = result.get("route")
    pred_intent = result.get("tool_intent")
    pred_args = result.get("tool_args", {})

    assert pred_route == sample["expected_route"], \
        f"Route incorrecte pour '{sample['text']}'"

    assert pred_intent == sample["expected_intent"], \
        f"Intention incorrecte pour '{sample['text']}'"

    assert args_exact_match(sample["expected_args"], pred_args, sample["expected_intent"]), \
        f"Arguments incorrects. Reçu: {pred_args}, Attendu: {sample['expected_args']}"

    if sample.get("expected_clarification"):
        assert result.get("needs_clarification") is True, \
            f"Clarification attendue pour '{sample['text']}'"

        clarification_message = result.get("clarification_message")
        assert isinstance(clarification_message, str) and clarification_message.strip(), \
            f"clarification_message vide pour '{sample['text']}'"

        messages = result.get("messages")
        assert isinstance(messages, list) and messages, \
            f"messages absent pour '{sample['text']}'"

        last_ai_message = _last_ai_message(messages)
        assert last_ai_message is not None, \
            f"Aucun AIMessage trouvé pour '{sample['text']}'"

        assert last_ai_message.content == clarification_message, \
            f"Le dernier AIMessage ne correspond pas à clarification_message pour '{sample['text']}'"


@pytest.mark.asyncio
@pytest.mark.parametrize("sample", BENCHMARK_EXTENSIONS, ids=lambda s: s["text"])
async def test_semantic_router_case_benchmark_extensions(ai_instance, session_id, sample):
    await _run_router_case(ai_instance, session_id, sample)
