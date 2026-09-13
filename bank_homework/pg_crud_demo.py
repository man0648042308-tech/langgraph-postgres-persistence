"""PostgreSQL入门：使用参数化SQL完成完整CRUD。"""

from __future__ import annotations

import os

import psycopg


DEFAULT_DB_URI = "postgresql://postgres:123456@localhost:5432/bank?sslmode=disable"


def get_db_uri() -> str:
    return os.getenv("BANK_DB_URI", DEFAULT_DB_URI)


def run_crud() -> None:
    with psycopg.connect(get_db_uri(), autocommit=True) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    email VARCHAR(200) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT NOW()
                )
                """
            )
            cursor.execute("DELETE FROM users WHERE email = %s", ("zhang@example.com",))
            cursor.execute(
                "INSERT INTO users (name, email) VALUES (%s, %s) RETURNING id, name, email",
                ("张三", "zhang@example.com"),
            )
            inserted = cursor.fetchone()
            print("CREATE/INSERT:", inserted)

            cursor.execute("SELECT id, name, email FROM users WHERE id = %s", (inserted[0],))
            print("READ:", cursor.fetchone())

            cursor.execute(
                "UPDATE users SET name = %s WHERE id = %s RETURNING id, name, email",
                ("李四", inserted[0]),
            )
            print("UPDATE:", cursor.fetchone())

            cursor.execute("DELETE FROM users WHERE id = %s RETURNING id", (inserted[0],))
            print("DELETE:", cursor.fetchone())

            cursor.execute("SELECT COUNT(*) FROM users WHERE id = %s", (inserted[0],))
            remaining = cursor.fetchone()[0]
            assert remaining == 0
            print("FINAL COUNT:", remaining)
    print("PostgreSQL CRUD全部通过。")


if __name__ == "__main__":
    run_crud()

