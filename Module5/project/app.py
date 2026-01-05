import streamlit as st
from agents.orchestrator import AgentOrchestrator

st.set_page_config(page_title="Weather & News Agent", layout="centered")

st.title("MCP Weather & News Agent")

if "agent" not in st.session_state:
    st.session_state.agent = AgentOrchestrator()

if "chat" not in st.session_state:
    st.session_state.chat = []

agent = st.session_state.agent

user_input = st.text_input("Ask a question:", key="user_msg")

if st.button("Send") and user_input:
    response = agent.handle_query(user_input)
    st.session_state.chat.append((user_input, response))

for user, assistant in st.session_state.chat:
    with st.chat_message("user"):
        st.write(user)
    with st.chat_message("assistant"):
        st.write(assistant)

# DEBUG
with st.sidebar:
    st.subheader("🧠 Agent Memory Location")
    last_city = agent.memory.get_last_location()
    st.info(f"Last location: {last_city if last_city else 'None'}")

