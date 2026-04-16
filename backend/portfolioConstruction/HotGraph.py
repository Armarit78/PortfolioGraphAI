from __future__ import annotations

import sys
import inspect
from abc import abstractmethod
from typing import Any, Callable, Optional, Tuple
from xml.sax import parse

from langchain_core.messages import AIMessage, HumanMessage
from langgraph.constants import END
from langgraph.graph import StateGraph
from langgraph.types import interrupt

from backend.ai.core.llm import dbg
from backend.portfolioConstruction.Filter import Filter


class HotGraph:
    """
    HotGraph — injecte des nœuds directement dans un StateGraph parent avec génération à la volée.
    """

    def __init__(
            self,
            nodes: list[dict],
            edges: list[dict],
            parser: Callable[[str, str,list[Filter]], dict],
            state_schema: type,
    ):
        self.nodes = nodes
        self.edges = edges
        self.parser = parser
        self.state_schema = state_schema

    @abstractmethod
    def build_dynamic_node(self, state: dict, node_def: dict, answer: str) -> Optional[dict]:
        """Génère la définition du prochain nœud en fonction de l'état."""
        raise NotImplementedError

    def _ask(self, state: dict, node_def: dict) -> dict:
        name = node_def["name"]
        description = node_def["description"]
        q_type = node_def.get("type", "question")
        options = node_def.get("options", [])
        output_name = node_def.get("output",None)
        payload = state.get(node_def.get("payload",None),None)
        payload_type = node_def.get("payload_type",None)

        question_message = AIMessage(
            content=description,
            response_type=q_type,
            response_options=options,
            output_name = output_name,
            payload = payload,
            payload_type = payload_type
        )

        answer = interrupt({
            "question": question_message,
            "node_name": name
        })

        dbg(f"RÉPONSE REÇUE ({name}) : ", answer)

        updates = {
            "messages": [question_message, HumanMessage(content=answer)],
            **node_def.get("output_state_updates", {})
        }

        if q_type == "qcm":
            value = answer if answer in options else "input_error"
            updates["constraints_manu"] = {**(state.get("constraints_manu") or {}), output_name: value}
        else:
            constraints_llm = state.get("constraints_llm",[])
            if self.parser:
                parsed = self.parser(answer, description,constraints_llm)
                dbg(f"Nouvelles contraintes : ",parsed)
                dbg(f"Anciennes contraintes : ",constraints_llm)
                updates["constraints_llm"] = parsed
            #if node_def.get("output"):
                #updates[node_def["output"]] = answer

        return updates

    def register(
            self,
            workflow: StateGraph,
            entry_from: str,
            exit_to: str,
            prefix: str = "",
            n_dynamic: int = 0,
            dynamic_after: Optional[str] = None,
    ):
        def p(name: str) -> str:
            return f"{prefix}{name}" if prefix else name

        for nd in self.nodes:
            workflow.add_node(p(nd["name"]), self._make_fn(nd))

        if n_dynamic > 0:
            for i in range(n_dynamic):
                workflow.add_node(p(f"dynamic_{i}"), self._make_dynamic_slot(i))

        for edge in self.edges:
            src = p(edge["start"])
            raw = self._to_end(edge["end"])
            cond = edge.get("conditional", False)

            if edge.get("entry_point"):
                workflow.add_edge(entry_from, src)

            dst = {k: (exit_to if v is END else p(v)) for k, v in raw.items()} if isinstance(raw, dict) else (
                exit_to if raw is END else p(raw))

            if n_dynamic > 0 and dynamic_after and edge["start"] == dynamic_after:
                if cond:
                    new_dst = {}
                    for k, v in dst.items():
                        if k is True or k == "True":
                            new_dst[k] = p("dynamic_0")
                            self._wire_dynamic_chain(workflow, p, n_dynamic, v)
                        else:
                            new_dst[k] = v
                    workflow.add_conditional_edges(src, self._resolve(edge["condition"]), new_dst)
                else:
                    workflow.add_edge(src, p("dynamic_0"))
                    self._wire_dynamic_chain(workflow, p, n_dynamic, dst)
            else:
                if cond:
                    workflow.add_conditional_edges(src, self._resolve(edge["condition"]), dst)
                else:
                    workflow.add_edge(src, dst)

    def _wire_dynamic_chain(self, workflow, p, n_dynamic: int, final_dst: str):
        for i in range(n_dynamic - 1):
            workflow.add_edge(p(f"dynamic_{i}"), p(f"dynamic_{i + 1}"))
        workflow.add_edge(p(f"dynamic_{n_dynamic - 1}"), final_dst)


    def _make_dynamic_slot(self, index: int) -> Callable:
        def fn(state: dict) -> dict:
            generated_nodes = dict(state.get("_generated_dynamic_nodes", {}))
            str_index = str(index)

            # Idempotence : on vérifie si le nœud a déjà été généré pour ce slot
            if str_index in generated_nodes:
                node_def = generated_nodes[str_index]
            else:
                last_answer = ""
                if state.get("messages") and isinstance(state["messages"][-1], HumanMessage):
                    last_answer = state["messages"][-1].content

                node_def = self.build_dynamic_node(state, {}, last_answer)
                generated_nodes[str_index] = node_def

            if node_def is None:
                return {"_generated_dynamic_nodes": generated_nodes}

            # Appel de la logique commune
            updates = self._ask(state, node_def)
            updates["_generated_dynamic_nodes"] = generated_nodes
            return updates

        fn.__name__ = f"dynamic_{index}"
        return fn

    def _make_fn(self, nd: dict) -> Callable:
        t = nd.get("type")
        if t in ["question", "qcm"]: return self._fn_interactive(nd)
        if t == "affirmation":       return self._fn_affirmation(nd)
        if t == "action":             return self._fn_action(nd)
        raise ValueError(f"Type inconnu : {t!r}")

    def _fn_interactive(self, nd: dict) -> Callable:
        def fn(state: dict) -> dict:
            return self._ask(state, nd)

        fn.__name__ = nd["name"]
        return fn

    def _fn_affirmation(self, nd: dict) -> Callable:
        def fn(state: dict) -> dict:
            msg = AIMessage(
                content=nd["description"],
                response_type=nd["type"],
            )

            interrupt({
                "question": msg,
                "node_name": nd["name"]
            })
            return {}

        fn.__name__ = nd["name"]
        return fn

    def _fn_action(self, nd: dict) -> Callable:
        action = self._resolve(nd.get("action",""))

        if inspect.iscoroutinefunction(action):
            async def async_fn(state:dict)->dict:
                result = await action(state)
                return {nd["output"]:result} if result else None
            async_fn.__name__ = nd["name"]
            return async_fn
        else:
            def sync_fn(state:dict)->dict:
                result = action(state)
                if "description" in nd:
                    msg = AIMessage(
                        content=nd["description"],
                    )
                    return {nd["output"]: result,"question":msg,"node_name":nd["name"]} if result is not None and nd.get("output") else {}
                else:
                    return {nd["output"]: result} if result is not None and nd.get("output") else {}
            sync_fn.__name__ = nd["name"]
            return sync_fn

    # Utilitaires

    def _resolve(self, name: str) -> Callable:
        if hasattr(self, name): return getattr(self, name)
        frame = sys._getframe(1)
        while frame:
            if name in frame.f_globals and callable(frame.f_globals[name]):
                return frame.f_globals[name]
            frame = frame.f_back
        raise NameError(f"{name!r} introuvable.")

    @staticmethod
    def _to_end(value) -> Any:
        if isinstance(value, str) and value.lower() == "end": return END
        if isinstance(value, dict):
            return {k: (END if isinstance(v, str) and v.lower() == "end" else v) for k, v in value.items()}
        return value