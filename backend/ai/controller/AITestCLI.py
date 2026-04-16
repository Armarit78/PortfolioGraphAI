import asyncio
import logging
import uuid
import sys
from backend.ai.controller.AILocalController import LocalController


async def main():
    print("========================================")
    print("   🚀 AXE - PROJECT 🚀   ")
    print("========================================")

    #Initialisation
    controller = LocalController()
    await controller.initialize()

    #Session locale
    session_id = str(uuid.uuid4())[:8]
    print(f"✅ Agent prêt ! (Session ID: {session_id})")


    #context_test = {"profil_risque" : "modéré"}
    await controller.create_chat(session_id, client_context={})

    print("\n💡 Tapez 'quit', 'exit' ou 'q' pour quitter la conversation.")
    print("-" * 40)

    while True:
        try:

            user_input = input("\n🧑 Vous : ").strip()

            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\n👋 Fermeture du chat. Au revoir !")
                break

            if not user_input:
                continue

            print("🤖 Agent réfléchit...", end="\r")

            response = await controller.chat(session_id, user_input)

            sys.stdout.write("\033[K")

            if response["status"] == "success":
                print(f"🤖 Agent : {response['message']}")
            else:
                print(f"❌ [ERREUR] : {response['message']}")

        except KeyboardInterrupt:
            print("\n\n🛑 Interruption forcée. Au revoir !")
            break
        except Exception as e:
            print(f"\n⚠️ Une erreur inattendue est survenue : {e}")

    await controller.close()


if __name__ == "__main__":
    # Lance la boucle d'événements asynchrone
    #logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())