import csv
import math
import re
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
import pytest_asyncio
from langchain_core.messages import AIMessage

from backend.ai.controller.AILocalController import LocalController


BENCHMARK = [
    # -------------------------
    # PRICE
    # -------------------------
    {
        "text": "Donne-moi le prix de Apple",
        "task_type": "price",
        "expected_route": "tool",
        "expected_intent": "price",
        "expected_symbol": "AAPL",
        "must_contain_any": ["aapl", "apple", "cours actuel", "prix"],
    },
    {
        "text": "Donne-moi le prix de Microsoft",
        "task_type": "price",
        "expected_route": "tool",
        "expected_intent": "price",
        "expected_symbol": "MSFT",
        "must_contain_any": ["msft", "microsoft", "cours actuel", "prix"],
    },
    {
        "text": "prix de Hermes",
        "task_type": "price",
        "expected_route": "tool",
        "expected_intent": "price",
        "expected_symbol": "RMS.PA",
        "must_contain_any": ["préciser", "ticker", "marché", "correspondances"],
    },
    {
        "text": "Google",
        "task_type": "price",
        "expected_route": "tool",
        "expected_intent": "price",
        "expected_symbol": "GOOGL",
        "must_contain_any": ["googl", "alphabet", "préciser", "ticker"],
    },

    # -------------------------
    # STATS
    # -------------------------
    {
        "text": "Je veux les stats de Apple sur 1 an",
        "task_type": "stats",
        "expected_route": "tool",
        "expected_intent": "stats",
        "expected_symbol": "AAPL",
        "expected_period": "1y",
        "must_contain_any": ["analyse de", "rendement annuel", "volatilité annuelle", "ratio de sharpe"],
    },
    {
        "text": "Peux-tu me dire le Sharpe ratio de Nvidia ?",
        "task_type": "stats",
        "expected_route": "tool",
        "expected_intent": "stats",
        "expected_symbol": "NVDA",
        "expected_period": "1y",
        "must_contain_any": ["analyse de", "rendement annuel", "volatilité annuelle", "ratio de sharpe"],
    },

    # -------------------------
    # COMPARE
    # -------------------------
    {
        "text": "Airbus vs Boeing",
        "task_type": "compare",
        "expected_route": "tool",
        "expected_intent": "compare",
        "expected_period": "1y",
        "must_contain_any": ["comparaison sur", "rendement annuel", "volatilité annuelle", "ratio de sharpe"],
    },
    {
        "text": "Hermès ou LVMH, lequel est le plus performant ?",
        "task_type": "compare",
        "expected_route": "tool",
        "expected_intent": "compare",
        "expected_period": "1y",
        "must_contain_any": ["comparaison sur", "rendement annuel", "volatilité annuelle", "ratio de sharpe"],
    },

    # -------------------------
    # SCREENER
    # -------------------------
    {
        "text": "je veux un portefeuille avec Airbus et LVMH",
        "task_type": "screener",
        "expected_route": "tool",
        "expected_intent": "screener",
        "must_contain_any": ["portefeuille", "souhaitez vous", "avec assistance", "sans assistance"],
    },
    {
        "text": "Portefeuille sans energie en Europe",
        "task_type": "screener",
        "expected_route": "tool",
        "expected_intent": "screener",
        "must_contain_any": ["portefeuille", "souhaitez vous", "avec assistance", "sans assistance"],
    },
    {
        "text": "Je veux des actions de santé hors USA",
        "task_type": "screener",
        "expected_route": "tool",
        "expected_intent": "screener",
        "must_contain_any": ["portefeuille", "souhaitez vous", "avec assistance", "sans assistance"],
    },
    # -------------------------
    # CHAT / UNKNOWN
    # -------------------------
    {
        "text": "trouve des actions comme Nvidia",
        "task_type": "chat",
        "expected_route": "chat",
        "expected_intent": "unknown",
        "must_contain_any": ["etf", "fonds", "indice", "bourse"],
    },
    {
        "text": "C'est quoi un ETF exactement ?",
        "task_type": "chat",
        "expected_route": "chat",
        "expected_intent": "unknown",
        "must_contain_any": ["etf", "fonds", "indice", "bourse"],
    },
    {
        "text": "je cherche des actions",
        "task_type": "chat",
        "expected_route": "chat",
        "expected_intent": "unknown",
        "must_contain_any": ["actions", "invest", "préciser", "aider"],
    },
    {
        "text": "donne-moi des actions",
        "task_type": "chat",
        "expected_route": "chat",
        "expected_intent": "unknown",
        "must_contain_any": ["actions", "préciser", "aider", "besoin"],
    },
    {
        "text": "je veux investir",
        "task_type": "chat",
        "expected_route": "chat",
        "expected_intent": "unknown",
        "must_contain_any": ["invest", "préciser", "objectif", "aider"],
    },

    # -------------------------
    # CLARIFICATIONS
    # -------------------------
    {
        "text": "compare Apple",
        "task_type": "clarification",
        "expected_route": "tool",
        "expected_intent": "compare",
        "expected_clarification": True,
        "must_contain_any": ["préciser", "deux tickers", "deux entreprises", "comparaison"],
    },
    {
        "text": "prix de",
        "task_type": "clarification",
        "expected_route": "tool",
        "expected_intent": "price",
        "expected_clarification": True,
        "must_contain_any": ["préciser", "entreprise", "ticker"],
    },
    {
        "text": "prix de Orange",
        "task_type": "clarification",
        "expected_route": "tool",
        "expected_intent": "price",
        "expected_clarification": True,
        "expected_candidates": [
            "Orange S.A.",
            "Orange Polska S.A.",
            "Orange Tour Cultural Holding Limited",
        ],
        "must_contain_any": ["préciser", "ticker", "marché", "correspondances"],
    },
]


NUMBER_RE = re.compile(r"-?\d+(?:[.,]\d+)?")
PERCENT_RE = re.compile(r"-?\d+(?:[.,]\d+)?\s*%")


def normalize_text(text: str) -> str:
    t = (text or "").strip().lower()
    t = t.replace("â€™", "'").replace("’", "'")
    t = re.sub(r"\s+", " ", t)
    return t


def strip_markdown(text: str) -> str:
    t = text or ""
    return t.replace("**", "").replace("*", "").replace("`", "")


def mask_numbers(text: str) -> str:
    t = text or ""
    t = PERCENT_RE.sub("<PERCENT>", t)
    t = NUMBER_RE.sub("<NUMBER>", t)
    return t


def tokenize(text: str) -> List[str]:
    t = normalize_text(strip_markdown(mask_numbers(text)))
    return re.findall(r"\w+|<number>|<percent>|[{}[\]:,.-]", t)


def ngrams(tokens: List[str], n: int) -> List[Tuple[str, ...]]:
    if len(tokens) < n:
        return []
    return [tuple(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def bleu_like(reference: str, candidate: str, max_n: int = 4) -> float:
    ref = tokenize(reference)
    hyp = tokenize(candidate)
    if not hyp:
        return 0.0

    precisions = []
    for n in range(1, max_n + 1):
        hyp_ngrams = ngrams(hyp, n)
        ref_ngrams = ngrams(ref, n)
        if not hyp_ngrams:
            precisions.append(0.0)
            continue

        ref_counts: Dict[Tuple[str, ...], int] = {}
        for ng in ref_ngrams:
            ref_counts[ng] = ref_counts.get(ng, 0) + 1

        hit = 0
        hyp_counts: Dict[Tuple[str, ...], int] = {}
        for ng in hyp_ngrams:
            hyp_counts[ng] = hyp_counts.get(ng, 0) + 1

        for ng, count in hyp_counts.items():
            hit += min(count, ref_counts.get(ng, 0))

        precisions.append(hit / len(hyp_ngrams))

    if min(precisions) == 0:
        geo_mean = 0.0
    else:
        geo_mean = math.exp(sum(math.log(p) for p in precisions) / max_n)

    bp = 1.0
    if len(hyp) < len(ref) and len(hyp) > 0:
        bp = math.exp(1 - len(ref) / len(hyp))

    return bp * geo_mean


def lcs_length(a: List[str], b: List[str]) -> int:
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(1, len(a) + 1):
        for j in range(1, len(b) + 1):
            if a[i - 1] == b[j - 1]:
                dp[i][j] = dp[i - 1][j - 1] + 1
            else:
                dp[i][j] = max(dp[i - 1][j], dp[i][j - 1])
    return dp[-1][-1]


def rouge_l_f1(reference: str, candidate: str) -> float:
    ref = tokenize(reference)
    hyp = tokenize(candidate)
    if not ref or not hyp:
        return 0.0
    lcs = lcs_length(ref, hyp)
    prec = lcs / len(hyp)
    rec = lcs / len(ref)
    if prec + rec == 0:
        return 0.0
    return 2 * prec * rec / (prec + rec)


def meteor_like(reference: str, candidate: str) -> float:
    ref = set(tokenize(reference))
    hyp = set(tokenize(candidate))
    if not ref or not hyp:
        return 0.0
    overlap = len(ref & hyp)
    prec = overlap / len(hyp)
    rec = overlap / len(ref)
    if prec + rec == 0:
        return 0.0
    return (10 * prec * rec) / (rec + 9 * prec)


def jaccard_similarity(reference: str, candidate: str) -> float:
    ref = set(tokenize(reference))
    hyp = set(tokenize(candidate))
    if not ref and not hyp:
        return 1.0
    if not ref or not hyp:
        return 0.0
    return len(ref & hyp) / len(ref | hyp)


def semantic_similarity(reference: str, answer: str) -> float:
    b = bleu_like(reference, answer)
    r = rouge_l_f1(reference, answer)
    m = meteor_like(reference, answer)
    j = jaccard_similarity(reference, answer)
    return 0.15 * b + 0.35 * r + 0.35 * m + 0.15 * j


def contains_any(text: str, patterns: List[str]) -> bool:
    low = normalize_text(strip_markdown(text))
    return any(normalize_text(pattern) in low for pattern in patterns)


def is_infra_error(answer: str) -> bool:
    low = normalize_text(answer)
    return (
        "error response 429" in low
        or "rate limit exceeded" in low
        or "[erreur graph/llm]" in low
        or "503" in low
        or "service unavailable" in low
    )


def reference_for_sample(sample: Dict[str, Any]) -> str:
    task = sample["task_type"]
    if task == "price":
        return f"Le cours actuel de {sample['expected_symbol']} est disponible."
    if task == "stats":
        return "Analyse de l'actif avec rendement annuel, volatilité annuelle et ratio de sharpe."
    if task == "compare":
        return "Comparaison sur la période demandée avec rendement annuel, volatilité annuelle et ratio de sharpe."
    if task == "screener":
        return "Question de construction de portefeuille ou de screener avec options d'assistance."
    if task == "clarification":
        return "Demande de précision sur le ticker, le marché ou les actifs à comparer."
    return "Réponse explicative cohérente en français."


def score_price(answer: str, sample: Dict[str, Any]) -> float:
    score = 0.0
    low = normalize_text(answer)
    if sample["expected_symbol"].lower() in low:
        score += 0.35
    if NUMBER_RE.search(answer):
        score += 0.35
    if contains_any(answer, sample.get("must_contain_any", [])):
        score += 0.30
    return min(1.0, score)


def score_stats(answer: str, sample: Dict[str, Any]) -> float:
    score = 0.0
    low = normalize_text(answer)
    if sample["expected_symbol"].lower() in low:
        score += 0.20
    if sample["expected_period"].lower() in low:
        score += 0.10
    if contains_any(answer, ["rendement annuel", "volatilité annuelle", "ratio de sharpe"]):
        score += 0.45
    if NUMBER_RE.search(answer):
        score += 0.25
    return min(1.0, score)


def score_compare(answer: str, sample: Dict[str, Any]) -> float:
    score = 0.0
    low = normalize_text(answer)
    if sample["expected_period"].lower() in low:
        score += 0.10
    if contains_any(answer, ["comparaison sur", "rendement annuel", "volatilité annuelle", "ratio de sharpe"]):
        score += 0.60
    if NUMBER_RE.search(answer):
        score += 0.30
    return min(1.0, score)


def score_screener(answer: str, sample: Dict[str, Any]) -> float:
    score = 0.0
    if contains_any(answer, sample.get("must_contain_any", [])):
        score += 0.70
    if len(answer.strip()) > 20:
        score += 0.30
    return min(1.0, score)


def score_chat(answer: str, sample: Dict[str, Any]) -> float:
    score = 0.0
    if contains_any(answer, sample.get("must_contain_any", [])):
        score += 0.70
    if len(answer.strip()) > 40:
        score += 0.30
    return min(1.0, score)


def score_clarification(answer: str, sample: Dict[str, Any]) -> float:
    score = 0.0
    if contains_any(answer, sample.get("must_contain_any", [])):
        score += 0.70
    if "?" in answer or "préciser" in normalize_text(answer):
        score += 0.30
    return min(1.0, score)


def business_score(answer: str, sample: Dict[str, Any]) -> float:
    task = sample["task_type"]
    if task == "price":
        return score_price(answer, sample)
    if task == "stats":
        return score_stats(answer, sample)
    if task == "compare":
        return score_compare(answer, sample)
    if task == "screener":
        return score_screener(answer, sample)
    if task == "clarification":
        return score_clarification(answer, sample)
    return score_chat(answer, sample)


def format_correctness(answer: str, sample: Dict[str, Any]) -> float:
    low = normalize_text(answer)
    task = sample["task_type"]

    if task == "price":
        score = 0.0
        if "cours actuel" in low or "prix" in low:
            score += 0.4
        if NUMBER_RE.search(answer):
            score += 0.3
        if sample["expected_symbol"].lower() in low:
            score += 0.3
        return min(1.0, score)

    if task == "stats":
        score = 0.0
        if "analyse de" in low:
            score += 0.3
        if "rendement annuel" in low:
            score += 0.25
        if "volatilité annuelle" in low or "volatilite annuelle" in low:
            score += 0.25
        if "ratio de sharpe" in low:
            score += 0.20
        return min(1.0, score)

    if task == "compare":
        score = 0.0
        if "comparaison sur" in low:
            score += 0.3
        if "rendement annuel" in low:
            score += 0.25
        if "volatilité annuelle" in low or "volatilite annuelle" in low:
            score += 0.25
        if "ratio de sharpe" in low:
            score += 0.20
        return min(1.0, score)

    if task == "clarification":
        score = 0.0
        if "préciser" in low:
            score += 0.5
        if "ticker" in low or "marché" in low or "marche" in low:
            score += 0.3
        if "?" in answer:
            score += 0.2
        return min(1.0, score)

    if task == "screener":
        return 1.0 if contains_any(answer, sample.get("must_contain_any", [])) else 0.4

    return 1.0 if len(answer.strip()) > 40 else 0.4


def business_pass_fail(business: float, sample: Dict[str, Any], infra_error: bool = False) -> bool:
    if infra_error:
        return False

    thresholds = {
        "price": 0.75,
        "stats": 0.75,
        "compare": 0.70,
        "screener": 0.60,
        "chat": 0.55,
        "clarification": 0.70,
    }
    return business >= thresholds.get(sample["task_type"], 0.60)


def final_score(semantic: float, business: float, fmt: float) -> float:
    return 0.45 * business + 0.30 * fmt + 0.25 * semantic


CSV_PATH = Path("tests_backend/benchmark_outputs/full_pipeline_benchmark_v2.csv")


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class BenchRow:
    text: str
    task_type: str
    answer: str
    elapsed_s: float
    semantic_similarity: float
    business_score: float
    business_pass: bool
    infra_error: bool
    format_correctness: float
    final_score: float
    route: str
    intent: str
    needs_clarification: bool


def _extract_answer_text(response_message: Any) -> str:
    if hasattr(response_message, "content"):
        return str(response_message.content)
    return str(response_message or "")


def _last_ai_message(messages: List[Any]) -> Optional[AIMessage]:
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


@pytest.mark.asyncio
async def test_full_pipeline_benchmark_v2(ai_instance, session_id):
    rows: List[BenchRow] = []

    for index, sample in enumerate(BENCHMARK):
        sample_session_id = f"{session_id}-{index}"
        await ai_instance.create_chat(sample_session_id)

        start = time.perf_counter()
        response = await ai_instance.chat(sample_session_id, sample["text"])
        elapsed_s = time.perf_counter() - start

        if response.get("status") == "error":
            pytest.fail(f"Erreur API pour '{sample['text']}': {response.get('message')}")

        config = {"configurable": {"thread_id": sample_session_id}}
        result_state = ai_instance.app.get_state(config)
        result = result_state.values

        pred_route = result.get("route")
        pred_intent = result.get("tool_intent")
        needs_clarification = bool(result.get("needs_clarification", False))
        clarification_message = result.get("clarification_message", "")
        messages = result.get("messages", [])
        last_ai_message = _last_ai_message(messages)

        response_message = response.get("message")
        answer = _extract_answer_text(response_message)
        if not answer and last_ai_message is not None:
            answer = last_ai_message.content

        assert pred_route == sample["expected_route"], \
            f"Route incorrecte pour '{sample['text']}'"
        assert pred_intent == sample["expected_intent"], \
            f"Intent incorrect pour '{sample['text']}'"

        if sample.get("expected_clarification") or sample["task_type"] == "clarification":
            assert needs_clarification is True, \
                f"Clarification attendue pour '{sample['text']}'"
            assert isinstance(clarification_message, str) and clarification_message.strip(), \
                f"clarification_message vide pour '{sample['text']}'"
            assert last_ai_message is not None, \
                f"Aucun AIMessage de clarification pour '{sample['text']}'"
            assert last_ai_message.content == clarification_message

            if sample.get("expected_candidates"):
                for candidate in sample["expected_candidates"]:
                    assert candidate in clarification_message, \
                        f"Candidat attendu absent pour '{sample['text']}': {candidate}"

                print(f"\n[INTENDED TOP3] {sample['text']}")
                for candidate in sample["expected_candidates"]:
                    print(f" - {candidate}")
        else:
            assert not needs_clarification, \
                f"Clarification inattendue pour '{sample['text']}'"

        if sample.get("expected_symbol"):
            tool_args = result.get("tool_args", {})
            assert tool_args.get("symbol") == sample["expected_symbol"], \
                f"Symbole incorrect pour '{sample['text']}'"

            if sample.get("expected_candidates"):
                candidates = tool_args.get("symbol_candidates", [])
                print(f"\n[RESOLVER TOP3] {sample['text']}")
                for c in candidates[:3]:
                    print(f" - {c.get('longName')} ({c.get('ticker')})")

        if sample.get("expected_period"):
            tool_args = result.get("tool_args", {})
            if sample["task_type"] == "compare":
                assert tool_args.get("period", "1y") == sample["expected_period"]
            else:
                assert tool_args.get("period", "1y") == sample["expected_period"]

        reference = reference_for_sample(sample)
        sem = semantic_similarity(reference, answer)
        biz = business_score(answer, sample)
        fmt = format_correctness(answer, sample)
        infra_error = is_infra_error(answer)
        passed = business_pass_fail(biz, sample, infra_error=infra_error)
        final = final_score(semantic=sem, business=biz, fmt=fmt)

        rows.append(
            BenchRow(
                text=sample["text"],
                task_type=sample["task_type"],
                answer=answer,
                elapsed_s=elapsed_s,
                semantic_similarity=sem,
                business_score=biz,
                business_pass=passed,
                infra_error=infra_error,
                format_correctness=fmt,
                final_score=final,
                route=pred_route,
                intent=pred_intent,
                needs_clarification=needs_clarification,
            )
        )

    n = len(rows)
    avg_sem = sum(row.semantic_similarity for row in rows) / n
    avg_biz = sum(row.business_score for row in rows) / n
    avg_fmt = sum(row.format_correctness for row in rows) / n
    avg_final = sum(row.final_score for row in rows) / n
    pass_rate = sum(1 for row in rows if row.business_pass) / n

    ensure_parent_dir(CSV_PATH)
    with CSV_PATH.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=[
                "text",
                "task_type",
                "route",
                "intent",
                "needs_clarification",
                "elapsed_s",
                "semantic_similarity",
                "business_score",
                "business_pass",
                "infra_error",
                "format_correctness",
                "final_score",
                "answer",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(asdict(row))

    assert avg_final >= 0.55
    assert avg_biz >= 0.60
    assert avg_fmt >= 0.55
    assert pass_rate >= 0.60
