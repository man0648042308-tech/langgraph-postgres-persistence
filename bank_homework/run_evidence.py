"""运行作业并将输出保存为可截图的证据文件。"""

from __future__ import annotations

import argparse
import importlib.metadata
import os
import platform
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "evidence"


def run_and_capture(title: str, command: list[str], filename: str) -> None:
    print(f"\n=== {title} ===")
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
        check=False,
    )
    output = f"$ {' '.join(command)}\n{result.stdout}{result.stderr}\nexit_code={result.returncode}\n"
    (EVIDENCE / filename).write_text(output, encoding="utf-8")
    print(output)
    if result.returncode != 0:
        raise SystemExit(f"{title}失败，证据见 {filename}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-postgres", action="store_true")
    args = parser.parse_args()
    EVIDENCE.mkdir(exist_ok=True)
    package_names = [
        "langgraph",
        "langgraph-checkpoint-sqlite",
        "langgraph-checkpoint-postgres",
        "langmem",
        "psycopg",
        "psycopg-pool",
        "pytest",
    ]
    package_versions = "\n".join(
        f"{name}={importlib.metadata.version(name)}" for name in package_names
    )
    environment = (
        f"Python={platform.python_version()}\n"
        f"Executable={sys.executable}\n"
        f"Platform={platform.platform()}\n"
        f"{package_versions}\n"
        "API配置=本次确定性验证未调用外部模型；未读取或输出任何密钥\n"
    )
    (EVIDENCE / "环境版本.txt").write_text(environment, encoding="utf-8")
    print(environment)

    run_and_capture(
        "自动测试",
        [sys.executable, "-m", "pytest"],
        "全量测试结果.txt",
    )
    run_and_capture(
        "模块四端到端",
        [sys.executable, "-m", "bank_homework.module4_bank_recommendation"],
        "模块四运行结果.txt",
    )
    run_and_capture(
        "MemorySaver与SqliteSaver",
        [sys.executable, "-m", "bank_homework.checkpoint_restore_demo"],
        "保存点恢复结果.txt",
    )

    if args.include_postgres:
        run_and_capture(
            "PostgreSQL CRUD",
            [sys.executable, "-m", "bank_homework.pg_crud_demo"],
            "PG_CRUD运行结果.txt",
        )
        run_and_capture(
            "AsyncPostgresSaver",
            [sys.executable, "-m", "bank_homework.async_postgres_saver_demo"],
            "AsyncSaver运行结果.txt",
        )
        run_and_capture(
            "异步连接池",
            [sys.executable, "-m", "bank_homework.async_pool_demo"],
            "连接池运行结果.txt",
        )
    print("\n全部指定验证通过，证据已写入 evidence 目录。")


if __name__ == "__main__":
    main()
