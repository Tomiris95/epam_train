# Weather & News Agent

## Overview
A Python-based application using **Streamlit**, **LLM**, and **MCP servers** to answer user questions about weather and the latest news. The agent can handle **multi-turn conversations** and remembers the last queried location for weather.

Key features:
- Ask about **current weather** for any city.
- Get **latest news** or news about a **specific topic**.
- Handles queries like:
  - "What is the weather in Astana?"
  - "Latest news"
  - "News about technology"
- Supports **multi-turn conversation**:
  - Remembers the last location for weather queries.
  - Can answer follow-up questions without repeating the city.
- Displays up to **5 news articles** with:
  - Article title
  - Summary/description
  - Source
  - URL
- Clean and friendly formatting using an **LLM**.

---

## Architecture

The application uses a **modular agent orchestration pattern**:

```
User → Streamlit → Orchestrator → (Memory + MCP Servers) → LLM formats → Streamlit → User

```

**Components:**

## Components

### 1. Streamlit UI (`app.py`)
- Captures user queries and displays chat history.
- Calls the agent orchestrator to get responses.

### 2. Agent Orchestrator (`agents/orchestrator.py`)
- Determines query intent (**WEATHER**, **NEWS**, or **BOTH**) using LLM.
- Routes requests to the appropriate MCP servers.
- Uses conversation memory for multi-turn queries.
- Formats the final response using LLM.

### 3. MCP Servers (`mcp_config/`)
- **Weather MCP:** Fetches current weather from Open-Meteo.
- **News MCP:** Retrieves up to 5 latest articles or topic-specific news from NewsAPI.org.

### 4. Conversation Memory (`agents/memory.py`)
- Stores the last N messages and the last city mentioned.
- Enables follow-up queries to reference the previous city.


---

## Features

- Ask about **current weather** in any city.
- Ask **follow-up questions** for the last mentioned city.
- Get **latest news headlines** or news by topic (up to 5 articles).
- Multi-turn conversation with **context memory**.
- Friendly, **summarized responses** via LLM.
- Combined queries: **weather + news**.
- Clear display of **weather info** (temperature, conditions, wind) and **news articles** (title, summary, source, URL).

---

## Setup Instructions

1. **Create and activate a Python virtual environment**
```bash
python -m venv venv
# Linux / Mac
source venv/bin/activate
# Windows
venv\Scripts\activate
```

2. **Install dependencies**
```bash
pip install -r requirements.txt
```

3. **Environment Variables**
Create a .env file in the project root directory and add your OpenAI API key:
OPENAI_API_KEY=sk-your_api_key_here
NEWS_API_KEY=sk-your_api_key_here

4. **Run the Streamlit app**
```bash
streamlit run app.py
```

5. **Open the web interface**
- The app will open at `http://localhost:8501/` by default

---

## Project Structure

```
project/
├── app.py                  # Streamlit UI
├── agents/
│   ├── memory.py          # Conversation memory
│   └── orchestrator.py     # Agent orchestrator
├── mcp_config/
|   ├── location.py      # extract_location function
│   ├── news_mcp.py         # News MCP 
│   └── weather_mcp.py      # Weather MCP 
├── requirements.txt
└── README.md
└── video_link.txt
```
---

## Notes

- The app requires **internet access** 
- API keys are required for **NewsAPI.org**
- LLM responses depend on OpenAI API access — ensure your API key is set in the environment if needed  

---


The full implementation and evaluation code are available in the project repository:
[https://github.com/](#)