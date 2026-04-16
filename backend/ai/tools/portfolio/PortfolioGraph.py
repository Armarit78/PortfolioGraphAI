import asyncio
import datetime
from dataclasses import asdict
from typing import Optional, Literal
from langchain_core.messages import AIMessage
from pydantic import BaseModel,Field
from backend.ai.core.llm import general_llm, dbg
from backend.portfolioConstruction.HotGraph import HotGraph
from backend.portfolioConstruction.Portfolio import Portfolio
from backend.portfolioConstruction.PortfolioFactory import PortfolioFactory
from backend.portfolioGestion.ServiceSavePortfolio import ServiceSavePortfolio

REQUIRED_THEMATICS = [
    "régions d'investissement ou d'exclusion",
    "secteur d'investissement ou d'exclusion (classe d'investissement : action)",
    "indicateurs financiers à respecter (dividendes, performance, résultat,...)",
    "le client veut-il ajouter une autre contrainte ?"
]

STATIC_NODES = [
    {
    "name":"intro",
    "type":"qcm",
    "options":["Avec assistance","Sans assistance"],
    "description":"Bienvenue sur votre outil de construction de portefeuilles. \n Souhaitez vous être accompagné pas à pas pour construire ce portefeuille où souhaitez vous décrire directement votre besoin ?",
    "output":"construction_mode"
},
{
    "name":"risque",
    "type":"qcm",
    "description":"Quel est votre profil de risque ?",
    "options":["Prudent","Equilibré","Dynamique"],
    "output":"risk"
},{
    "name":"construction_portefeuille",
    "type":"action",
    "action":"optimize",
    "output":"portfolios",
},{
    "name":"presentation_portefeuille",
    "payload":"portfolios",
    "payload_type":"portfolio",
    "type":"qcm",
    "description":"Voici votre portefeuille, souhaitez vous l'enregistrer ?",
    "options":["Enregistrer","Supprimer"],
    "output":"save_portfolio"
},{
    "name":"save_portefeuille",
    "type":"action",
    "description":"Votre portefeuille a été enregistré. Vous le retrouverez dans l'onglet 'Portefeuilles'. \n Ce chat est maintenant désactivé pour créer un nouveau portefeuille, créez un nouveau chat. ",
    "action":"save_portfolio"
},{
    "name":"freeride",
    "type":"question",
    "description":"Décris ton besoin",
    "output":"constraints_llm"
    }
]

STATIC_EDGES = [
    {
        "start":"intro",
        "end":{"Avec assistance":"risque","Sans assistance":"freeride"},
        "entry_point":True,
        "conditional":True,
        "condition":"check_intro"
},
    {
        "start": "freeride",
        "end": "construction_portefeuille",
        "entry_point": False,
        "conditional": False,
        "condition": None
    },
{
        "start": "risque",
        "end": {True:"construction_portefeuille",False:"risque"},
        "entry_point":False,
        "conditional": True,
        "condition": "check_qcm"
    },{
        "start":"construction_portefeuille",
        "end":"presentation_portefeuille",
        "entry_point":False,
        "conditional":False,
        "condition":None
    },{
        "start":"presentation_portefeuille",
        "end": {True:"save_portefeuille",False:"end"},
        "entry_point":False,
        "conditional":True,
        "condition":"check_save",
    },{
        "start":"save_portefeuille",
        "end": "end",
        "entry_point":False,
        "conditional":False,
        "condition":None,
    }

]

class NodeModel(BaseModel):
    name:str = Field(
        description="Ce champs décrit le nom du noeud, il est en lien avec la question qui est posé"
    )
    type: Literal["question","qcm"] = Field(
        default= "question",
        description="ce champs te permet de poser à l'utilisateur soit une question soit un qcm avec des reponses préformés"
    )
    description:str = Field(
        description="Dans ce champs tu renseignes la question que tu vas poser à l'utilisateur afin de réponse à la thématique choisie"
    )
    options: list[str] = Field(
        default=None,
        description="si tu as choisi une question à choix multiple (qcm) tu listes ici les options qui sont offertes à l'utilisateur"
    )



class PortfolioGraph(HotGraph):
    required_thematics = REQUIRED_THEMATICS
    portfolioFactory = PortfolioFactory()

    def build_dynamic_node(self, state: dict, node_def: dict, answer: str) -> Optional[dict]:
        current_idx = state.get("_thematic_index", 0)

        if current_idx >= len(self.required_thematics):
            return None

        current_thematic = self.required_thematics[current_idx]

        extractor = general_llm.with_structured_output(NodeModel)
        prompt = f"Tu dois poser une question directe (comme un banquier) sur la thématique : {current_thematic} afin de connaitre ses préférences, tu peux poser des questions ouvertes ou des qcm mais pour les qcm tu dois renseigner une liste d'options pour l'utilisateur"

        try:
            result = extractor.invoke(prompt)
            node_data = result.model_dump()

            node_data["output_state_updates"] = {"_thematic_index": current_idx + 1}

            return node_data
        except Exception as e:
            print(f"Erreur LLM : {e}")
            return None

    def check_qcm(self,state):
        messages = state.get("messages")
        ai_messages = [m for m in messages if isinstance(m,AIMessage)]
        last_ai_message = ai_messages[-1]
        if last_ai_message.response_type=="qcm":
            try:
                output_name = last_ai_message.output_name
                cstr = state.get("constraints_manu").get(output_name)
            except:
                return False
            if cstr in last_ai_message.response_options:
                return True
            return False

    def check_intro(self,state):
        cstr = state.get("constraints_manu")
        dbg(f"INTRO : {cstr}")
        return cstr.get("construction_mode","Avec assistance")

    def check_save(self,state):
        cstr = state.get("constraints_manu")
        dbg(f"SAVE : {cstr}")
        return cstr.get("save_portfolio","Supprimer") == "Enregistrer"

    async def optimize(self,state):
        #on essaye de récupérer les contraintes :
        try:
            constraints_llm = state.get("constraints_llm",[])
            constraints_manu = state.get("constraints_manu",[])
        except Exception as e:
            raise ValueError(f"Etape Optimisation : Erreur lors de la récupération des contraintes : {str(e)}")
        if len(constraints_llm)==0:
            return None

        #optimisation du portefeuille

        date_construction = datetime.datetime(year=2025,month=4,day=12)
        portfolio : Portfolio = Portfolio(constraints_llm=constraints_llm,constraints_manu=constraints_manu)
        universe = self.portfolioFactory.get_universe(portfolio)
        quotes = self.portfolioFactory.get_quotes(universe=universe)
        dbg("Quotes : ",quotes)
        try:
            historic_prices, return_matrix, covariance_matrix = await asyncio.to_thread(
                self.portfolioFactory.calculate_metrics,
                quotes,
                date_construction
            )
        except Exception as e:
            raise Exception(f"Erreur lors du calcul des métriques : {str(e)}")

        dbg("Historic_prices : ",historic_prices)
        dbg("Return matrix : ",return_matrix)
        dbg("Covariance matrix: ",covariance_matrix)
        dbg("Historic_prices : ",type(historic_prices))
        dbg("Return matrix : ",type(return_matrix))
        dbg("Covariance matrix: ",type(covariance_matrix))
        try:

            optimized_portfolio = await asyncio.to_thread(
                self.portfolioFactory.optimize,
                historic_prices,
                return_matrix,
                covariance_matrix,
                portfolio,
                date_construction
            )

        except Exception as e:
            raise Exception(f"Erreur lors de l'optimisation du portefeuille : {str(e)}")
        return asdict(optimized_portfolio)


    def save_portfolio(self,state):
        serviceSavePortfolio:ServiceSavePortfolio = ServiceSavePortfolio()
        try:
            serviceSavePortfolio.create_portfolio(state.get("user_context").get("email"),state.get("portfolios"))
        except Exception as e:
            raise Exception(f"Erreur lors de l'enregistrement du portefeuille : {str(e)}")

