from typing import TypedDict, Annotated, Dict, Any, Optional, Literal
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph.message import add_messages
from backend.ai.agent.routing.types import Route,ToolIntent
from backend.portfolioConstruction.Filter import Filter
from backend.portfolioConstruction.Portfolio import Portfolio


class AgentState(TypedDict, total=False):
    messages: Annotated[list[BaseMessage], add_messages]
    route: Route
    language:str
    needs_clarification: bool
    clarification_message: Optional[str]

    # router
    heuristic_result: Dict[str, Any]
    semantic_result: Dict[str, Any]
    validation_result: Dict[str, Any]
    #routing param
    tool_intent:ToolIntent
    tool_args:Dict[str,Any]

    #debug
    confidence: float
    source: str

    #hotGraph
    _thematic_index: int
    _generated_dynamic_nodes:dict
    _subgraph:object

    #contraintes
    constraints_llm: Optional[list[Filter]]
    constraints_manu: Optional[dict]

    #liste des portefeuilles générés dans le chat
    portfolios: Portfolio

    #stocker des métadonnées sur l'utilisateur actif (profil de risque, etc.)
    user_context: Optional[Dict[str, Any]]


