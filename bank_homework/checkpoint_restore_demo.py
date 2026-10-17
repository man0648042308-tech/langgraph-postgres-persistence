"""示例6：对比MemorySaver和SqliteSaver，并从历史检查点恢复。"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import END, START, StateGraph


class CheckpointState(TypedDict):
    customer_id: str
    balance: int
    risk_score: int
    status: str


def calculate_risk(state: CheckpointState) -> dict:
    score = min(100, state["balance"] // 1000)
    return {"risk_score": score, "status": "risk_calculated"}


def make_decision(state: CheckpointState) -> dict:
    decision = "人工复核" if state["risk_score"] >= 70 else "自动通过"
    return {"status": decision}


def build_graph(checkpointer):
    builder = StateGraph(CheckpointState)
    builder.add_node("calculate_risk", calculate_risk)
    builder.add_node("make_decision", make_decision)
    builder.add_edge(START, "calculate_risk")
    builder.add_edge("calculate_risk", "make_decision")
    builder.add_edge("make_decision", END)
    return builder.compile(checkpointer=checkpointer)


def run_memory_demo() -> dict:
    graph = build_graph(MemorySaver())
    config = {"configurable": {"thread_id": "memory-demo"}}
    result = graph.invoke(
        {"customer_id": "C001", "balance": 80000, "risk_score": 0, "status": "created"},
        config,
    )
    snapshot = graph.get_state(config)
    assert snapshot.values == result
    print(f"MemorySaver最新状态: {snapshot.values}")
    return result


def run_sqlite_restore_demo(db_path: Path) -> dict:
    if db_path.exists():
        db_path.unlink()

    connection = sqlite3.connect(db_path, check_same_thread=False)
    saver = SqliteSaver(connection)
    graph = build_graph(saver)
    config = {"configurable": {"thread_id": "sqlite-demo"}}
    initial = {"customer_id": "C002", "balance": 80000, "risk_score": 0, "status": "created"}
    final = graph.invoke(initial, config)
    history = list(graph.get_state_history(config))
    print(f"SqliteSaver检查点数量: {len(history)}")

    replay_target = next(
        snapshot
        for snapshot in history
        if snapshot.values.get("status") == "risk_calculated"
        and tuple(snapshot.next) == ("make_decision",)
    )
    print(f"选中的历史状态: {replay_target.values}")
    replayed = graph.invoke(None, replay_target.config)
    assert replayed["status"] == "人工复核"
    assert replayed["risk_score"] == 80
    print(f"从历史检查点继续执行后的状态: {replayed}")
    connection.close()

    # 重新连接文件，证明状态不是仅存在于进程内对象中。
    new_connection = sqlite3.connect(db_path, check_same_thread=False)
    new_graph = build_graph(SqliteSaver(new_connection))
    persisted = new_graph.get_state(config).values
    new_connection.close()
    assert persisted["customer_id"] == "C002"
    print(f"重新连接SQLite后读取到的状态: {persisted}")
    return final


def main() -> None:
    run_memory_demo()
    run_sqlite_restore_demo(Path("bank_checkpoints.sqlite"))
    print("示例6保存点类型与历史恢复全部通过。")


if __name__ == "__main__":
    main()

