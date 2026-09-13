> 本仓库为个人作品集公开版：AI 大模型应用开发课程实战项目，模拟数据，非生产系统。更多项目见作品集主页。

# Day29～Day30作业运行与提交说明

## 作业对应关系

| 作业要求 | 本项目文件 |
|---|---|
| 1. Typora学习总结 | `Day29_Day30学习总结.md` |
| 2. 模块四银行推荐Agent | `bank_homework/module4_bank_recommendation.py` |
| 3. PostgreSQL入门 | `sql/pg_crud.sql`、`bank_homework/pg_crud_demo.py` |
| 4. CRUD与AsyncPostgresSaver | `pg_crud_demo.py`、`async_postgres_saver_demo.py` |
| 5. AsyncPG连接池 | `async_pool_demo.py` |
| 6. 保存点类型实践 | `checkpoint_restore_demo.py` |

## 第一次安装

在PowerShell中进入本目录：

```powershell
Set-Location ./BankRS_Day29_Day30
uv sync
```

## 先运行不依赖PostgreSQL的作业

```powershell
uv run python -m bank_homework.run_evidence
```

## 启动PostgreSQL

先确保Docker Desktop显示Engine running，然后执行：

```powershell
docker compose up -d postgres
docker compose ps
```

Compose使用DaoCloud公开镜像代理获取官方`library/postgres:16-alpine`，用于解决国内访问Docker Hub速度过慢的问题；镜像版本仍为PostgreSQL 16 Alpine。

`STATUS`中出现`healthy`后运行数据库部分：

```powershell
uv run python -m bank_homework.run_evidence --include-postgres
```

## 单独运行

```powershell
uv run python -m bank_homework.module4_bank_recommendation
uv run python -m bank_homework.checkpoint_restore_demo
uv run python -m bank_homework.pg_crud_demo
uv run python -m bank_homework.async_postgres_saver_demo
uv run python -m bank_homework.async_pool_demo
uv run pytest
```

## 截图顺序

1. `uv run pytest`显示全部测试通过。
2. 模块四显示四个场景及“全部通过”。
3. 保存点练习显示检查点数量、历史状态、恢复后状态。
4. PG CRUD显示CREATE/INSERT、READ、UPDATE、DELETE、FINAL COUNT。
5. AsyncPostgresSaver显示持久化消息数量和两轮消息。
6. 异步连接池显示并发结果`[1, 2, 3, 4, 5]`。
7. Typora打开学习总结，截图标题和核心总结。

不要提交`.env`、真实API Key、数据库个人密码或`.venv`目录。
