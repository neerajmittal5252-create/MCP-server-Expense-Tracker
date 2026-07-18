from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Literal, Annotated
from langchain_core.messages import SystemMessage, HumanMessage, BaseMessage
from langchain_groq import ChatGroq
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import InMemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from dotenv import load_dotenv
import os

load_dotenv()


groq_api=os.getenv("GROQ_API_KEY")
# model=ChatGroq(model="meta-llama/llama-prompt-guard-2-22m")
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="nvidia/nemotron-nano-9b-v2:free",  # a chat-capable Nemotron variant, not the embed one
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)
client=MultiServerMCPClient({
    "employee-server": {
        "url": "http://localhost:8000/mcp",
        "transport": "streamable_http",
    }
})

class ChatState(TypedDict):
    messages:Annotated[list[BaseMessage],add_messages]

async def build_graph():
    tools=await client.get_tools()
    llm_with_tools=model.bind_tools(tools)
    def chatbot(state:ChatState):
        return {"messages":[llm_with_tools.invoke(state["messages"])]}
    graph=StateGraph(ChatState)
    graph.add_node("chatbot",chatbot)
    graph.add_node("tools",ToolNode(tools=tools))
    graph.add_edge(START,"chatbot")
    graph.add_conditional_edges("chatbot",tools_condition)
    graph.add_edge("tools","chatbot")

    checkpointer=InMemorySaver()
    final_graph=graph.compile(checkpointer=checkpointer)
    return final_graph