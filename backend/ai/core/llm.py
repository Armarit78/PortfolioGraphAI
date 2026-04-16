from backend.ai.core.config import Settings
from langchain_mistralai import ChatMistralAI

settings = Settings()


def dbg(*args):
    if settings.DEBUG_MODE:
        print("[GRAPH_DEBUG]", *args)


general_llm = ChatMistralAI(
    model=settings.MISTRAL_MODEL,
    api_key= settings.MISTRAL_API_KEY.get_secret_value(),
    temperature = settings.LLM_TEMPERATURE,
    max_retries=3,
    timeout=30
)

