from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from dotenv import load_dotenv

load_dotenv()

from agents.memory import ConversationMemory
from mcp_config.weather_mcp import get_weather
from mcp_config.news_mcp import get_news
from mcp_config.location import extract_location 


llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0
)

INTENT_PROMPT = """
You are an AI agent that decides which tool to use.

Available tools:
- WEATHER
- NEWS
- BOTH

Reply with ONLY one word:
WEATHER, NEWS, or BOTH.
"""

FORMAT_PROMPT = """
You are a helpful assistant.
Using the provided information, generate a clear and friendly response.
You MUST keep all articles, do NOT remove or summarize them into one.
Just format them clearly and friendly.
"""

class AgentOrchestrator:
    def __init__(self):
        self.memory = ConversationMemory()

    def handle_query(self, query: str) -> str:
        # Add user message to memory
        self.memory.add_user(query)

        # Step 1: Intent decision
        intent_response = llm.invoke(
            [SystemMessage(content=INTENT_PROMPT)] + self.memory.get()
        )

        intent = intent_response.content.strip()

        # Step 2: Call MCP tools
        if intent == "WEATHER":
            city = extract_location(query, memory=self.memory)
            self.memory.add_user(query, location=city)
            tool_data = get_weather(city)

        elif intent == "NEWS":
            tool_data = get_news(query)

        elif intent == "BOTH":
            city = extract_location(query, memory=self.memory)
            self.memory.add_user(query, location=city)
            tool_data = (
                f"{get_weather(city)}\n\n"
                f"{get_news(query)}"
            )

        else:
            tool_data = "I could not determine the request."

        # Step 3: LLM synthesizes final response
        final_response = llm.invoke(
            [
                SystemMessage(content=FORMAT_PROMPT),
                HumanMessage(content=tool_data)
            ]
        )

        answer = final_response.content

        # Save AI response to memory
        self.memory.add_ai(answer)

        return answer


# from langchain_openai import ChatOpenAI
# from langchain_core.messages import SystemMessage, HumanMessage

# from agents.memory import ConversationMemory
# from mcp_config.weather_mcp import get_weather
# from mcp_config.news_mcp import get_news

# # LLM for intent detection and formatting
# llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)

# INTENT_PROMPT = """
# You are an AI agent that decides which tool to use.

# Available tools:
# - WEATHER
# - NEWS
# - BOTH

# Reply with ONLY one word:
# WEATHER, NEWS, or BOTH.
# """

# FORMAT_PROMPT = """
# You are a helpful assistant.
# Using the provided information, generate a clear and friendly response.
# Keep the data factual and do not invent any news.
# """

# class AgentOrchestrator:
#     def __init__(self):
#         self.memory = ConversationMemory()

#     def handle_query(self, query: str) -> str:
#         # Add user query to memory
#         self.memory.add_user(query)

#         # Step 1: Intent detection
#         intent_response = llm.invoke(
#             [SystemMessage(content=INTENT_PROMPT)] + self.memory.get()
#         )
#         intent = intent_response.content.strip().upper()

#         # Step 2: Fetch data from MCPs
#         tool_data = ""
#         if intent == "WEATHER":
#             tool_data = get_weather(query)

#         elif intent == "NEWS":
#             tool_data = get_news(query)

#         elif intent == "BOTH":
#             weather_data = get_weather(query)
#             news_data = get_news(query)
#             tool_data = f"{weather_data}\n\n{news_data}"

#         else:
#             tool_data = "I could not determine the request. Please ask about weather or news."

#         # Step 3: LLM formats the response
#         final_response = llm.invoke(
#             [
#                 SystemMessage(content=FORMAT_PROMPT),
#                 HumanMessage(content=tool_data)
#             ]
#         )

#         answer = final_response.content

#         # Step 4: Save AI response to memory
#         self.memory.add_ai(answer)

#         return answer
