"""模块四：带短期记忆与长期用户画像的银行产品推荐系统。

推荐决策使用确定性规则，保证金融适当性规则可测试、可解释；
大模型可作为解释生成层扩展，但不参与风险准入的最终判断。
"""

from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AnyMessage, HumanMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.store.memory import InMemoryStore
from langmem import create_manage_memory_tool, create_search_memory_tool


class RiskTolerance(str, Enum):
    CONSERVATIVE = "保守型"
    MODERATE = "稳健型"
    BALANCED = "平衡型"
    AGGRESSIVE = "进取型"


class ProductCategory(str, Enum):
    DEPOSIT = "定期存款"
    WEALTH = "理财产品"
    MONEY_FUND = "货币基金"
    BOND_FUND = "债券基金"
    EQUITY_FUND = "股票基金"
    HYBRID_FUND = "混合基金"
    INSURANCE = "保险"
    GOLD = "黄金投资"


@dataclass(frozen=True)
class FinancialProduct:
    product_id: str
    name: str
    category: ProductCategory
    risk_level: RiskTolerance
    expected_return: float
    min_investment: float
    lock_period_months: int
    features: list[str]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["category"] = self.category.value
        result["risk_level"] = self.risk_level.value
        return result


@dataclass(frozen=True)
class UserProfile:
    user_id: str
    name: str
    age: int
    occupation: str
    monthly_income: float
    investment_amount: float
    risk_tolerance: RiskTolerance
    investment_goals: list[str]
    preferred_categories: list[ProductCategory]
    existing_products: list[str]

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["risk_tolerance"] = self.risk_tolerance.value
        result["preferred_categories"] = [item.value for item in self.preferred_categories]
        return result


def generate_mock_data() -> tuple[list[FinancialProduct], list[UserProfile]]:
    products = [
        FinancialProduct("P001", "安心存定期存款", ProductCategory.DEPOSIT, RiskTolerance.CONSERVATIVE, 2.5, 1000, 6, ["保本保息"]),
        FinancialProduct("P002", "稳盈理财产品", ProductCategory.WEALTH, RiskTolerance.CONSERVATIVE, 3.2, 10000, 12, ["预期收益稳定"]),
        FinancialProduct("P003", "天天利货币基金", ProductCategory.MONEY_FUND, RiskTolerance.CONSERVATIVE, 2.0, 0.01, 0, ["随存随取"]),
        FinancialProduct("P004", "稳健债券基金", ProductCategory.BOND_FUND, RiskTolerance.MODERATE, 4.0, 1000, 0, ["波动较小"]),
        FinancialProduct("P005", "成长混合基金", ProductCategory.HYBRID_FUND, RiskTolerance.BALANCED, 6.5, 1000, 0, ["股债平衡配置"]),
        FinancialProduct("P006", "进取股票基金", ProductCategory.EQUITY_FUND, RiskTolerance.AGGRESSIVE, 10.0, 5000, 0, ["适合长期投资"]),
        FinancialProduct("P007", "养老目标保险", ProductCategory.INSURANCE, RiskTolerance.MODERATE, 3.5, 20000, 60, ["年金领取", "身故保障"]),
        FinancialProduct("P008", "黄金积存金", ProductCategory.GOLD, RiskTolerance.MODERATE, 5.0, 500, 0, ["抗通胀"]),
    ]
    users = [
        UserProfile("U001", "张明", 35, "企业中层", 25000, 100000, RiskTolerance.MODERATE, ["子女教育储备", "资产稳健增值"], [ProductCategory.WEALTH, ProductCategory.BOND_FUND], ["P001"]),
        UserProfile("U002", "李芳", 28, "互联网工程师", 18000, 50000, RiskTolerance.BALANCED, ["购房首付积累"], [ProductCategory.HYBRID_FUND, ProductCategory.EQUITY_FUND], []),
        UserProfile("U003", "王建国", 58, "退休评审者", 8000, 200000, RiskTolerance.CONSERVATIVE, ["养老现金流", "资产保值"], [ProductCategory.DEPOSIT, ProductCategory.INSURANCE], ["P002", "P003"]),
    ]
    return products, users


class BankRecommendationState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], add_messages]
    user_id: str
    profile_updates: dict[str, Any]
    user_profile: dict[str, Any]
    needs: dict[str, Any]
    recommended_products: list[dict[str, Any]]
    final_response: str
    response_time_ms: float


RISK_ORDER = {
    RiskTolerance.CONSERVATIVE.value: 1,
    RiskTolerance.MODERATE.value: 2,
    RiskTolerance.BALANCED.value: 3,
    RiskTolerance.AGGRESSIVE.value: 4,
}


def eligible_products(
    profile: dict[str, Any], products: list[FinancialProduct]
) -> list[FinancialProduct]:
    """执行硬性适当性规则：产品风险不越级且满足起投金额。"""
    user_risk = RISK_ORDER.get(profile.get("risk_tolerance", "稳健型"), 2)
    amount = float(profile.get("investment_amount", 0))
    eligible = [
        product
        for product in products
        if RISK_ORDER[product.risk_level.value] <= user_risk
        and product.min_investment <= amount
    ]
    preferred = set(profile.get("preferred_categories", []))
    return sorted(
        eligible,
        key=lambda item: (
            item.category.value not in preferred,
            item.product_id in profile.get("existing_products", []),
            item.product_id,
        ),
    )


def create_bank_recommendation_agent():
    """创建图，并返回图和共享长期记忆Store，便于验证跨线程记忆。"""
    products, users = generate_mock_data()
    users_by_id = {user.user_id: user.to_dict() for user in users}
    store = InMemoryStore()
    checkpointer = MemorySaver()
    memory_tools = [
        create_manage_memory_tool(namespace=("bank_user_memories",), store=store),
        create_search_memory_tool(namespace=("bank_user_memories",), store=store),
    ]

    def load_user_profile(state: BankRecommendationState) -> dict[str, Any]:
        user_id = state["user_id"]
        if user_id not in users_by_id:
            raise ValueError(f"用户不存在: {user_id}")
        namespace = ("bank_user_profiles", user_id)
        stored = store.get(namespace, "profile")
        profile = dict(stored.value if stored else users_by_id[user_id])
        profile.update(state.get("profile_updates", {}))
        store.put(namespace, "profile", profile)
        return {"user_profile": profile}

    def analyze_user_needs(state: BankRecommendationState) -> dict[str, Any]:
        text = state["messages"][-1].content if state.get("messages") else ""
        profile = state["user_profile"]
        return {
            "needs": {
                "query": str(text),
                "goals": profile.get("investment_goals", []),
                "risk_tolerance": profile.get("risk_tolerance"),
            }
        }

    def recommend(state: BankRecommendationState) -> dict[str, Any]:
        started = time.perf_counter()
        profile = state["user_profile"]
        selected = eligible_products(profile, products)[:3]
        recommendations = [item.to_dict() for item in selected]
        if recommendations:
            lines = [
                f"{index}. {item['name']}（{item['risk_level']}，起投{item['min_investment']:g}元）"
                for index, item in enumerate(recommendations, 1)
            ]
            response = (
                f"{profile['name']}您好，根据您的风险承受能力和可投资金额，为您推荐：\n"
                + "\n".join(lines)
                + "\n以上为功能演示，不构成真实投资建议。"
            )
        else:
            response = "暂未找到同时满足风险等级和起投金额要求的产品。"
        return {
            "recommended_products": recommendations,
            "final_response": response,
            "messages": [{"role": "assistant", "content": response}],
            "response_time_ms": round((time.perf_counter() - started) * 1000, 3),
        }

    workflow = StateGraph(BankRecommendationState)
    workflow.add_node("load_profile", load_user_profile)
    workflow.add_node("analyze_needs", analyze_user_needs)
    workflow.add_node("recommend", recommend)
    workflow.add_edge(START, "load_profile")
    workflow.add_edge("load_profile", "analyze_needs")
    workflow.add_edge("analyze_needs", "recommend")
    workflow.add_edge("recommend", END)
    graph = workflow.compile(checkpointer=checkpointer, store=store)
    return graph, store, memory_tools


def invoke_for_user(graph, user_id: str, query: str, thread_id: str, **extra):
    state = {
        "user_id": user_id,
        "messages": [HumanMessage(content=query)],
        **extra,
    }
    return graph.invoke(state, {"configurable": {"thread_id": thread_id}})


def run_end_to_end_scenarios() -> list[dict[str, Any]]:
    graph, store, memory_tools = create_bank_recommendation_agent()
    assert {tool.name for tool in memory_tools} == {"manage_memory", "search_memory"}
    results = []

    results.append(invoke_for_user(graph, "U003", "我想为退休生活做准备", str(uuid.uuid4())))
    results.append(invoke_for_user(graph, "U002", "我想开始理财，可以承受一定风险", str(uuid.uuid4())))

    first_thread = str(uuid.uuid4())
    results.append(
        invoke_for_user(
            graph,
            "U001",
            "我主要想给孩子存教育金",
            first_thread,
            profile_updates={"preferred_contact": "手机"},
        )
    )
    second_thread = str(uuid.uuid4())
    remembered = invoke_for_user(graph, "U001", "你还记得我的联系方式偏好吗？", second_thread)
    assert remembered["user_profile"]["preferred_contact"] == "手机"
    assert store.get(("bank_user_profiles", "U001"), "profile") is not None
    results.append(remembered)
    return results


def main() -> None:
    for index, result in enumerate(run_end_to_end_scenarios(), 1):
        ids = [item["product_id"] for item in result["recommended_products"]]
        print(f"场景{index}: user={result['user_id']}, products={ids}, {result['response_time_ms']}ms")
        print(result["final_response"])
        print("-" * 60)
    print("模块四端到端场景全部通过。")


if __name__ == "__main__":
    main()
