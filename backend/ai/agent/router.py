from langchain_core.messages import HumanMessage

from backend.ai.agent.routing.heuristic_routing import HeuristicRouter
from backend.ai.agent.routing.regex import RegexClass
from backend.ai.agent.routing.semantic_routing import SemanticRouter
from backend.ai.agent.state import AgentState
from langgraph.graph import END
from typing import Dict,Any

from backend.ai.core.llm import dbg


class Router:

    def __init__(self):
        self.heuristic_high_threshold: float = 0.88
        self.heuristic_low_threshold: float = 0.55
        self.semantic_threshold: float = 0.60

    def route_from_router(self, state: AgentState):
        if state.get("tool_intent") != "unknown":
            return state.get("tool_intent")
        else:
            return "chat"

    @staticmethod
    def _attach_symbol_resolution(tool_args: Dict[str, Any], intent: str, resolutions: list[dict]) -> Dict[str, Any]:
        if not tool_args or not resolutions:
            return tool_args

        enriched_args = dict(tool_args)

        if intent in {"price", "stats"} and len(resolutions) >= 1:
            resolution = resolutions[0]
            enriched_args["symbol_ambiguous"] = bool(
                resolution.get("multiple_matches") or resolution.get("used_volume_fallback")
            )
            enriched_args["symbol_multiple_matches"] = bool(resolution.get("multiple_matches"))
            enriched_args["symbol_used_fallback"] = bool(resolution.get("used_volume_fallback"))
            enriched_args["symbol_query"] = resolution.get("query")
            enriched_args["entity_confidence"] = float(resolution.get("entity_confidence", 0.0))
            enriched_args["symbol_candidates"] = list(resolution.get("candidates", []))

        if intent == "compare":
            confidences = []
            for index, resolution in enumerate(resolutions[:2], start=1):
                enriched_args[f"symbol{index}_ambiguous"] = bool(
                    resolution.get("multiple_matches") or resolution.get("used_volume_fallback")
                )
                enriched_args[f"symbol{index}_multiple_matches"] = bool(resolution.get("multiple_matches"))
                enriched_args[f"symbol{index}_used_fallback"] = bool(resolution.get("used_volume_fallback"))
                enriched_args[f"symbol{index}_query"] = resolution.get("query")
                enriched_args[f"symbol{index}_candidates"] = list(resolution.get("candidates", []))
                confidence = float(resolution.get("entity_confidence", 0.0))
                enriched_args[f"symbol{index}_confidence"] = confidence
                confidences.append(confidence)

            if confidences:
                enriched_args["entity_confidence"] = min(confidences)

        return enriched_args

    def route(self, state:AgentState,regex:RegexClass):
        messages = state.get("messages",[])
        if not messages:
            return END

        last_message = messages[-1]
        dbg("Dernier message reçu : ", last_message)
        if not isinstance(last_message,HumanMessage):
            return END

        #détection de la langue du message
        language = "French"
        #couche 0 : extraction des symbols éventuels
        syms,companies = [],[]
        syms, companies = regex.extract_symbols(last_message.content)
        period = regex.extract_period(last_message.content)
        #couche 1 : analyse heuristique
        heuristic_router = HeuristicRouter(last_message.content,syms,companies,period)
        heuristic_result = heuristic_router.result
        heuristic_confidence = heuristic_result.get("confidence",0.0)

        #couche 2 : analyse sémantique (que si on n'est pas sûr d'heuristique)
        semantic_result = {}
        semantic_confidence = 0.0
        if heuristic_confidence<self.heuristic_high_threshold:
            semantic_router = SemanticRouter(last_message.content,syms,companies,period)
            semantic_result = semantic_router.predict()
            semantic_confidence = semantic_result.get("confidence",0.0)

        #couche 3 : on décide en connaissance de cause
        res : Dict[str,Any]
        #confiance extrême dans l'analyse heuristique
        if heuristic_confidence >= self.heuristic_high_threshold:
            res = {
                **heuristic_result,
                "reason":"heuristic_high_confidence"
            }
        #confiance importante dans l'analyse sémantique et confiance plus importante dans l'analyse sémantique relativement
        elif semantic_result and semantic_confidence >= self.semantic_threshold and semantic_confidence > heuristic_confidence:
            res = semantic_result

        elif semantic_result and semantic_confidence >= self.semantic_threshold and heuristic_confidence >= self.heuristic_low_threshold:
            if semantic_result.get("tool_intent") == heuristic_result.get("tool_intent"):
                res = {
                    **semantic_result,
                    "confidence" : max(heuristic_confidence,semantic_confidence)
                }

        elif semantic_result.get("tool_intent") != "unknown":
            res = semantic_result

        elif heuristic_result.get("tool_intent") != "unknown":
            res = heuristic_result

        #ON REPREND L'IMPLEMENTATION D'ORIGINE
        # elif heuristic_result.get("tool_intent") != "unknown":
        #     res = {
        #         **heuristic_result,
        #         "reason":"heuristic_retained_after_comparison"
        #     }
        #
        # elif semantic_result and semantic_result.get("tool_intent") not in {"unknown","chat"}:
        #     res = {**semantic_result,
        #            "reason":"senamtic_used_as_best_available_signal"}

        else:
            res = {
                "route": "chat",
                "tool_intent": "unknown",
                "tool_args": {},
                "confidence": 0.0,
                "source": "fallback_chat",
                "reason": "ambiguous_after_validation",
            }
        # Important: do not overwrite the validated decision below.
        # The previous version discarded all threshold checks and fallback branches.

        dbg(f"router_node:semantic_result = ", semantic_result)
        dbg(f"router_node:heuristic_result = ", heuristic_result)
        res["tool_args"] = self._attach_symbol_resolution(
            res.get("tool_args", {}),
            res.get("tool_intent", "unknown"),
            getattr(regex, "last_symbol_resolution", []),
        )
        dbg(f"router_node:decision = {res}")
        return res


