import os

from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.types import Command
from psycopg_pool import AsyncConnectionPool

from backend.ai.agent.routing.regex import RegexClass
from backend.ai.core.config import Settings
from backend.ai.agent.workflow import workflow
from supabase import create_client

from backend.ai.core.llm import dbg


class AIController:
    def __init__(self):
        self.workflow = workflow
        self.pool = None
        self.app = None
        #init du regex
        self.regex = RegexClass()
        self.settings = Settings()

        #fonctions hors ia pour la gestion des historiques de chat
        self.supabase = create_client(self.settings.SUPABASE_URL,self.settings.SUPABASE_SERVICE_KEY)

    #init de la connexion à la BDD
    async def initialize(self):
        self.pool = AsyncConnectionPool(
            conninfo=self.settings.SUPABASE_DIRECT_LINK,
            max_size=20,
            kwargs={"autocommit":True,
                    "prepare_threshold": None}
        )

        await self.pool.wait()

        checkpointer = AsyncPostgresSaver(self.pool)

        await checkpointer.setup()

        self.app = self.workflow.compile(checkpointer=checkpointer)


    #close connexion à la BDD
    async def close(self):
        if self.pool:
            await self.pool.close()

    #aller chercher tous les chats dans la BDD
    def getAllChatsAi(self, email):
        try :
            response = self.supabase.table("chats").select("*").eq("user_email", email).execute()
            if response.data:
                chats = []
                for item in response.data:
                    chats.append({
                        "id": item["id"],
                        "name": item["chat_name"]
                    })
                chats.reverse()
                return True, chats, ""
            else:
                return True, [], ""
        except Exception as e:
            return False, [], f"Error retrieving chats: {str(e)}"


    async def get_chat(self,session_id):
        config = {"configurable": {"thread_id": session_id}}
        try:
             snap = await self.app.aget_state(config)
        except Exception as e:
            return False, [], f"Error retrieving chat: {str(e)}"


        messages = snap.values.get("messages",[])
        filtered_messages = [m for m in messages if not isinstance(m,SystemMessage)]
        return {"success":True,"message":"chargement du chat réussi","chat":filtered_messages}

    async def delete_chat(self, chat_id, email):

        try:
            # Vérifier que le chat appartient à l'utilisateur
            response = self.supabase.table("chats").select("*").eq("id", chat_id).eq("user_email", email).execute()
            if not response.data or len(response.data) == 0:
                return False, "Chat not found or does not belong to the user"

            if chat_id == 0:
                return True, "Chat deleted successfully"

            # Supprimer le chat (référence)
            self.supabase.table("chats").delete().eq("id", chat_id).execute()
            # Supprimer le state (contenu du chat)
            try:
                async with self.pool.connection() as conn:
                    async with conn.cursor() as cur:
                        await cur.execute("DELETE FROM checkpoint_blobs WHERE thread_id = %s", (str(chat_id),))
                        await cur.execute("DELETE FROM checkpoint_writes WHERE thread_id = %s", (str(chat_id),))
                        await cur.execute("DELETE FROM checkpoints WHERE thread_id = %s", (str(chat_id),))
            except Exception as e:
                return False, f"Error deleting chat content: {str(e)}"

            return True, "Chat deleted successfully"

        except Exception as e:
            return False, f"Error deleting chat: {str(e)}"

    async def create_chat_bdd(self,chat_name,email):
        try:
            response = self.supabase.table("chats").select("id").order("id", desc=True).limit(1).execute()
            print(f"response BDD : {response}")
            if response.data and len(response.data) > 0:
                new_id = response.data[0]["id"] + 1
                print(f"new_id : {new_id}")
            else:
                new_id = 0
        except Exception as e:
            return False, -1, f"Error creating chat: {str(e)}"

        # Insertion du nouveau chat dans la base de données
        data = {
            "id": new_id,
            "chat_name": chat_name,
            "user_email": email
        }

        try:
            response = self.supabase.table("chats").insert(data).execute()
            return True, new_id, "Chat created successfully"
        except Exception as e:
            return False, -1, f"Error creating chat: {str(e)}"


    async def create_chat(self,session_id=None,client_context:dict={}):
        config = {"configurable":{"thread_id": session_id}}

        initial_state = {
            "messages" : [AIMessage(content="## Bienvenue sur votre Assistant financier personnel \n Je suis là pour vous aider à naviguer sur les marchés financiers, analyser des données en temps réel et optimiser vos investissements. Que vous soyez un investisseur chevronné ou que vous fassiez vos premiers pas, voici ce que je peux faire pour vous : \n ## Mes fonctionnalités clés \n **Construction de Portefeuille** : Besoin d'aide pour structurer vos investissements ? Dites simplement Aide-moi à construire un portefeuille et je vous accompagnerai pas à pas selon votre profil de risque. \n **Cours en Temps Réel** : Obtenez le prix actuel de n'importe quelle action en me demandant simplement son nom ou son ticker (ex: Prix d'Airbus). \n **Analyses Historiques** : Consultez les performances passées. Demandez-moi des statistiques sur une période précise (ex: Statistiques d'Apple sur 6 mois).\n **Comparateur d'Actifs** : Vous hésitez entre deux titres ? Je peux les comparer pour vous sur la période de votre choix (ex: Compare Orange et Bouygues depuis 1 an). \n **Vous n'avez pas besoin de me donner votre budget, il n'est pas pris en compte dans les calculs**")],
            "user_context": client_context
        }
        try:
            await self.app.aupdate_state(config,initial_state)
            return {
                "status":"success",
                "message":f"Chat {session_id} initialisée avec succès"
            }

        except Exception as e:
            return {
                "status":"error",
                "message":f"Erreur lors de la création du chat : {str(e)}"
            }

    async def chat(self, session_id: str, user_message: str):
        config = {"configurable": {"thread_id": session_id, "regex": self.regex}}

        snap = await self.app.aget_state(config)
        is_interrupted = snap and snap.next and snap.next[0].startswith("screener_")
        dbg("SNAP NEXT : ", snap.next)

        if is_interrupted:
            input_state = Command(resume=user_message)
        else:
            input_state = {"messages": [HumanMessage(content=user_message)]}

        if user_message in ["quit"]:
            input_state = Command(goto="finalize")

        try:
            result_state = await self.app.ainvoke(input_state, config=config)

            # --- MOVED FROM FINALLY TO HERE ---
            # Check for pending interrupts (questions) after successful execution
            snap_after = await self.app.aget_state(config)
            if snap_after and snap_after.next and snap_after.next[0].startswith("screener_"):
                tasks = snap_after.tasks
                if tasks:
                    interrupt_value = tasks[0].interrupts[0].value if tasks[0].interrupts else None
                    if interrupt_value:
                        question = interrupt_value.get("question") if isinstance(interrupt_value, dict) else str(
                            interrupt_value)
                        return {"status": "success", "message": question, "data": None}
            # -----------------------------------

            messages = result_state.get("messages", [])
            last_message = messages[-1] if messages else AIMessage(content="")

            if isinstance(last_message, HumanMessage) or isinstance(last_message, SystemMessage):
                last_message = AIMessage(content="")

            if not messages:
                return {"status": "error", "message": "Aucun message retourné par l'agent", "data": None}

            return {"status": "success", "message": last_message, "data": None}

        except Exception as e:
            # THIS WILL NOW CORRECTLY BREAK THE LOOP AND SHOW THE ERROR
            return {"status": "error", "message": f"Erreur lors de l'execution de l'agent : {str(e)}", "data": None}
