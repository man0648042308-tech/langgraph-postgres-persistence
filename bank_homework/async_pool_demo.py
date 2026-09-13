"""psycopg异步连接池：并发查询与自动资源回收。"""

from __future__ import annotations

import asyncio
import os
import sys

from psycopg_pool import AsyncConnectionPool


DEFAULT_DB_URI = "postgresql://postgres:123456@localhost:5432/bank?sslmode=disable"


async def query_value(pool: AsyncConnectionPool, value: int) -> int:
    async with pool.connection() as connection:
        async with connection.cursor() as cursor:
            await cursor.execute("SELECT %s::integer", (value,))
            row = await cursor.fetchone()
            return row[0]


async def run_demo() -> None:
    db_uri = os.getenv("BANK_DB_URI", DEFAULT_DB_URI)
    async with AsyncConnectionPool(db_uri, min_size=2, max_size=4) as pool:
        values = await asyncio.gather(*(query_value(pool, number) for number in range(1, 6)))
        assert values == [1, 2, 3, 4, 5]
        print("并发查询结果:", values)
        print("连接池统计:", pool.get_stats())
    print("AsyncConnectionPool并发与关闭验证全部通过。")


def main() -> None:
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(run_demo())


if __name__ == "__main__":
    main()

