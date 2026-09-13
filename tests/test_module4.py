from langchain_core.messages import HumanMessage

from bank_homework.module4_bank_recommendation import (
    RiskTolerance,
    create_bank_recommendation_agent,
    eligible_products,
    generate_mock_data,
    invoke_for_user,
)


def test_conservative_user_never_receives_higher_risk_product():
    products, users = generate_mock_data()
    profile = next(user for user in users if user.user_id == "U003").to_dict()
    selected = eligible_products(profile, products)
    assert selected
    assert {product.risk_level for product in selected} == {RiskTolerance.CONSERVATIVE}


def test_products_over_investment_amount_are_excluded():
    products, users = generate_mock_data()
    profile = next(user for user in users if user.user_id == "U001").to_dict()
    profile["investment_amount"] = 500
    selected = eligible_products(profile, products)
    assert selected
    assert all(product.min_investment <= 500 for product in selected)


def test_long_term_profile_survives_a_new_thread():
    graph, _store, memory_tools = create_bank_recommendation_agent()
    assert {tool.name for tool in memory_tools} == {"manage_memory", "search_memory"}
    invoke_for_user(
        graph,
        "U001",
        "请记录我的偏好",
        "profile-thread-1",
        profile_updates={"preferred_contact": "手机"},
    )
    result = invoke_for_user(graph, "U001", "你还记得吗", "profile-thread-2")
    assert result["user_profile"]["preferred_contact"] == "手机"


def test_short_term_messages_accumulate_in_same_thread():
    graph, _store, _memory_tools = create_bank_recommendation_agent()
    config = {"configurable": {"thread_id": "same-thread"}}
    graph.invoke(
        {"user_id": "U002", "messages": [HumanMessage(content="第一轮咨询")]},
        config,
    )
    result = graph.invoke(
        {"user_id": "U002", "messages": [HumanMessage(content="第二轮咨询")]},
        config,
    )
    contents = [message.content for message in result["messages"]]
    assert "第一轮咨询" in contents
    assert "第二轮咨询" in contents
