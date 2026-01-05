from langchain_core.messages import HumanMessage, AIMessage


class ConversationMemory:
    def __init__(self, max_turns=3):
        self.max_turns = max_turns
        self.messages = []
        self.last_location = None

    def add_user(self, text: str, location: str = None):
        self.messages.append(HumanMessage(content=text))
        if location:
            self.last_location = location.lower()
        self._trim()

    def add_ai(self, text: str):
        self.messages.append(AIMessage(content=text))
        self._trim()

    def get(self):
        return self.messages
    
    def get_last_location(self):
        return self.last_location

    def _trim(self):
        if len(self.messages) > self.max_turns * 2:
            self.messages = self.messages[-self.max_turns * 2:]
