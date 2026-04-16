from backend.ai.controller.AIController import AIController
from langgraph.checkpoint.memory import MemorySaver


class LocalController(AIController):

    async def initialize(self):
        checkpointer = MemorySaver()
        self.app = self.workflow.compile(checkpointer=checkpointer)


    async def close(self):
        pass



