"""使用AsyncPostgresSaver持久化同一thread_id的多轮消息。"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Annotated, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


DEFAULT_DB_URI = "postgresql://postgres:123456@localhost:5432/bank?sslmode=disable"


class ConversationState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def echo_node(state: ConversationState) -> dict:
    last = state["messages"][-1]
    return {"messages": [AIMessage(content=f"银行助手已收到：{last.content}")]}


def build_graph(checkpointer):
    builder = StateGraph(ConversationState)
    builder.add_node("echo", echo_node)
    builder.add_edge(START, "echo")
    builder.add_edge("echo", END)
    return builder.compile(checkpointer=checkpointer)


async def run_demo() -> None:
    db_uri = os.getenv("BANK_DB_URI", DEFAULT_DB_URI)
    async with AsyncPostgresSaver.from_conn_string(db_uri) as saver:
        await saver.setup()
        graph = build_graph(saver)
        config = {"configurable": {"thread_id": "customer-C001"}}
        await graph.ainvoke({"messages": [HumanMessage(content="我叫张三")]}, config)
        result = await graph.ainvoke({"messages": [HumanMessage(content="我想购买稳健产品")]}, config)
        contents = [message.content for message in result["messages"]]
        assert "我叫张三" in contents
        assert "我想购买稳健产品" in contents
        snapshot = await graph.aget_state(config)
        print("持久化消息数量:", len(snapshot.values["messages"]))
        for message in snapshot.values["messages"]:
            print(f"[{message.type}] {message.content}")
    print("AsyncPostgresSaver多轮持久化全部通过。")


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()

