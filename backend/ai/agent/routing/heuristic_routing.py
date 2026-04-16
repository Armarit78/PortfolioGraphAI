import re
from typing import Dict, Any

from backend.ai.agent.state import ToolIntent, Route


class HeuristicRouter:
    @staticmethod
    def is_explanation_question(text: str) -> bool:
        t = (text or "").strip().lower()
        if not t:
            return False

        patterns = [
            r"\bc[’']?est quoi\b",
            r"\bqu['’]est[- ]ce que\b",
            r"\bqu est ce que\b",
            r"\bce qu['’]est\b",
            r"\bexplique(?:-moi)?\b",
            r"\bm[’']expliquer\b",
            r"\bje veux comprendre\b",
            r"\bj[’']aimerais comprendre\b",
            r"\bje veux savoir ce qu['’]est\b",
            r"\bj[’']aimerais savoir ce qu['’]est\b",
            r"\bd[ée]finis\b",
            r"\bd[ée]finition\b",
            r"\bdiff[ée]rence entre\b",
            r"\bcomment fonctionne\b",
            r"\bpourquoi\b",
            r"\bwhat is\b",
            r"\bexplain\b",
            r"\bce que c['’]est\b",
            r"\bdifference between\b",
        ]
        return any(re.search(p, t) for p in patterns)

    @staticmethod
    def has_explicit_compare_signal(text: str, syms) -> bool:
        t = (text or "").lower()
        has_two_assets = len(syms) >= 2
        has_period = bool(re.search(r"\b(1 an|un an|6 mois|3 ans|1y|6mo|5 ans|3 mois|1 mois|5y|3mo|1mo)\b", t))

        has_relative_metric = any(
            k in t for k in [
                "lequel",
                "meilleur",
                "mieux",
                "plus performant",
                "plus rentable",
                "moins volatil",
                "plus volatil",
                "meilleure performance",
                "performance",
                "rendement",
                "sharpe",
            ]
        )

        if re.search(r"\b(compare|comparaison|comparatif|comparer|vs|versus|contre)\b", t):
            return True

        if has_two_assets and re.search(r"diff[ée]rence.*entre", t):
            return True

        if has_two_assets and has_relative_metric:
            return True

        if has_two_assets and has_period and ("entre " in t or " et " in t):
            return True

        if has_two_assets and " ou " in t and (has_period or has_relative_metric):
            return True

        return False

    @classmethod
    def has_strong_screener_signal(cls, text: str) -> bool:
        t = (text or "").lower()
        if not t or cls.is_explanation_question(text):
            return False

        strong_patterns = [
            r"\bfiltre(?:r)?\b",
            r"\bscreener\b",
            r"\bscreen\b",
            r"\bportefeuille\b",
            r"\bunivers\b",
        ]

        return any(re.search(p, t) for p in strong_patterns)

    @staticmethod
    def _has_search_verb(text: str) -> bool:
        t = (text or "").lower()
        return bool(re.search(r"\b(je cherche|cherche|trouve(?:-moi)?|peux-tu me trouver)\b", t))

    @staticmethod
    def _has_asset_universe(text: str) -> bool:
        t = (text or "").lower()
        return bool(re.search(r"\b(actions?|etf|valeurs?|small caps?)\b", t))

    @staticmethod
    def _has_filter_dimension(text: str) -> bool:
        t = (text or "").lower()
        return any(
            k in t for k in [
                "secteur",
                "sector",
                "industry",
                "europe",
                "europ",
                "monde",
                "usa",
                "us",
                "états-unis",
                "etats-unis",
                "santé",
                "sante",
                "tech",
                "technologie",
                "industrie",
                "divid",
                "rendement",
                "volatil",
                "bêta",
                "beta",
                "sharpe",
                "drawdown",
                "growth",
                "value",
                "qualit",
                "quality",
                "défensif",
                "defensif",
                "faible risque",
                "faible volatilité",
                "faible volatilite",
            ]
        )

    @staticmethod
    def _has_constraint(text: str) -> bool:
        t = (text or "").lower()
        return any(
            k in t for k in [
                "avec",
                "sans",
                "hors",
                "faible",
                "élevé",
                "elevé",
                "minimum",
                "maximum",
                "low",
                "high",
            ]
        )

    @classmethod
    def has_weak_screener_signal(cls, text: str) -> bool:
        t = (text or "").lower()
        if not t or cls.is_explanation_question(text):
            return False

        has_search_verb = cls._has_search_verb(text)
        has_asset_universe = cls._has_asset_universe(text)
        has_filter_dimension = cls._has_filter_dimension(text)
        has_constraint = cls._has_constraint(text)

        return (has_search_verb and has_asset_universe and (has_filter_dimension or has_constraint)) or (
            has_asset_universe and has_filter_dimension
        )

    @classmethod
    def is_screener_intent(cls, text: str) -> bool:
        return cls.has_strong_screener_signal(text) or cls.has_weak_screener_signal(text)

    @staticmethod
    def is_market_numbers_intent(text: str) -> bool:
        t = (text or "").lower()
        if not t:
            return False

        return bool(
            re.search(
                r"\b("
                r"prix|cours|price|quote|"
                r"stat|stats|statistique|statistiques|performance|perf|"
                r"sharpe|rendement|return|volatilité|volatilite|volatil|volatility|"
                r"compare|comparer|comparez|comparaison|vs|versus|contre|"
                r"historique|history|graph|chart|"
                r"1d|5d|1mo|3mo|6mo|1y|2y|5y|ytd|max"
                r")\b",
                t,
            )
        )

    @classmethod
    def detect_tool_intent(cls, text: str, syms) -> ToolIntent:
        t = (text or "").lower()

        if not t.strip():
            return "unknown"

        if cls.is_explanation_question(text):
            return "unknown"

        has_search_verb = cls._has_search_verb(text)
        has_asset_universe = cls._has_asset_universe(text)
        has_filter_dimension = cls._has_filter_dimension(text)
        has_constraint = cls._has_constraint(text)
        explicit_compare = cls.has_explicit_compare_signal(text, syms)
        strong_screener = cls.has_strong_screener_signal(text)
        weak_screener = cls.has_weak_screener_signal(text)

        if has_search_verb and has_asset_universe and not (has_filter_dimension or has_constraint):
            return "unknown"

        if strong_screener and not explicit_compare:
            return "screener"

        if explicit_compare:
            return "compare"

        if weak_screener and not explicit_compare:
            return "screener"

        if re.search(r"\b(stats?|statistiques?|volatilité|volatilite|rendement|performance|performances|perf|indicateur|indicateurs)\b", t):
            if len(syms) > 0 and not re.search(r"\bactions?\b", t):
                return "stats"

        if re.search(r"\b(prix|cours|price|quote|cote|vaut|combien)\b", t):
            return "price"

        if len(syms) == 1:
            return "price"

        if strong_screener or weak_screener:
            return "screener"

        return "unknown"

    def score_heuristic(self) -> float:
        t = (self.message or "").lower()
        args = self.args or {}
        score = 0.0

        if self.route == "chat":
            if any(
                k in t for k in [
                    "explique",
                    "c'est quoi",
                    "qu'est-ce que",
                    "definition",
                    "définition",
                    "expliquer",
                    "comprendre",
                    "ce qu'est",
                    "explique-moi",
                    "défini",
                ]
            ):
                return 0.93
            return 0.60

        if self.intent == "price":
            if any(k in t for k in ["prix", "cours", "price", "quote", "combien vaut"]):
                score += 0.35
            if args.get("symbol"):
                score += 0.45

        elif self.intent == "stats":
            if any(k in t for k in ["stats", "statistiques", "volatil", "sharpe", "rendement", "return", "performance", "perf"]):
                score += 0.40
            if args.get("symbol"):
                score += 0.35
            if args.get("period"):
                score += 0.10

        elif self.intent == "compare":
            if any(k in t for k in ["compare", "comparaison", "comparatif", " vs ", "versus", " contre ", "lequel", "meilleur"]):
                score += 0.40
            if args.get("symbol1") and args.get("symbol2"):
                score += 0.40
            elif args.get("symbol1") or args.get("symbol2"):
                score += 0.15
            if args.get("period"):
                score += 0.10

        elif self.intent == "screener":
            if any(k in t for k in ["screener", "screen", "filtre", "secteur", "yield", "dividende", "portfolio", "portefeuille", "actions", "contraintes"]):
                score += 0.55
            if args.get("description"):
                score += 0.20

        elif self.intent == "unknown":
            score = 0.20

        return min(max(score, 0.0), 0.99)

    def build_args(self, symb, companies, period) -> Dict[str, Any]:
        s1 = symb[0] if len(symb) > 0 else None
        c1 = companies[0] if len(companies) > 0 else None
        s2 = symb[1] if len(symb) > 1 else None
        c2 = companies[1] if len(companies) > 1 else None

        if self.intent == "price":
            return {"symbol": s1, "company": c1}

        if self.intent == "stats":
            return {"symbol": s1, "company": c1, "period": period}

        if self.intent == "compare":
            return {"symbol1": s1, "company1": c1, "symbol2": s2, "company2": c2, "period": period}

        if self.intent == "screener":
            return {"description": self.message.strip()}

        return {}

    def build_result(self) -> Dict[str, Any]:
        return {
            "route": self.route,
            "tool_intent": self.intent,
            "tool_args": self.args,
            "confidence": self.confidence,
            "source": "heuristic",
            "reason": "heuristic_scoring",
        }

    def __init__(self, last_message, syms, companies, period):
        self.message = last_message
        self.intent: ToolIntent = self.detect_tool_intent(self.message, syms)
        self.route: Route = "tool" if self.intent != "unknown" else "chat"
        self.args = self.build_args(syms, companies, period)
        self.confidence = self.score_heuristic()
        self.result = self.build_result()