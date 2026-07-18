import asyncio
import streamlit as st
from backend import build_graph
from langchain_core.messages import HumanMessage

st.set_page_config(page_title="Employee Assistant", page_icon="🧑‍💼")
st.title("Employee Management Assistant")

# Keep one persistent event loop across Streamlit reruns
if "loop" not in st.session_state:
    st.session_state.loop = asyncio.new_event_loop()
asyncio.set_event_loop(st.session_state.loop)

# Build the graph once per session (connects to the MCP server on startup)
if "graph" not in st.session_state:
    with st.spinner("Connecting to employee-server..."):
        st.session_state.graph = st.session_state.loop.run_until_complete(build_graph())

if "messages" not in st.session_state:
    st.session_state.messages = []

# Render chat history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

user_input = st.chat_input("Ask about employees or departments...")

if user_input:
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    config = {"configurable": {"thread_id": "streamlit-session"}}

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            result = st.session_state.loop.run_until_complete(
                st.session_state.graph.ainvoke(
                    {"messages": [HumanMessage(content=user_input)]},
                    config=config
                )
            )
            ai_response = result["messages"][-1].content
            st.markdown(ai_response)

    st.session_state.messages.append({"role": "assistant", "content": ai_response})