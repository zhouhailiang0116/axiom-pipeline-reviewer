#!/usr/bin/env python3
import yaml, sys

AXIOMS = {
    "AX1_GROWTH": {"name": "公理一·生长", "check": "依赖覆盖"},
    "AX4_LAYOUT": {"name": "公理四·结构", "check": "孤证检查"},
    "AX6_BOUNDARY": {"name": "公理六·边界", "check": "终止条件"},
    "AX7_FREEDOM": {"name": "公理七·自由", "check": "备选路径"},
    "AX8_CAUSAL": {"name": "公理八·因果", "check": "因果链"},
}

nodes = [
    {"id": "user_input", "name": "用户输入", "output": "原始问题"},
    {"id": "retrieval", "name": "向量检索", "input_from": ["user_input"], "output": "文档"},
    {"id": "llm", "name": "LLM生成", "input_from": ["retrieval"], "critical": True, "terminal": True},
]

edges = [("user_input", "retrieval"), ("retrieval", "llm")]
consumed = set(e[0] for e in edges)
orphans = [n["id"] for n in nodes if n["id"] not in consumed]
terminals = [n["id"] for n in nodes if n.get("terminal")]
critical = [n["id"] for n in nodes if n.get("critical")]

print("=== Axiom Pipeline Review Demo ===")
print(f"Nodes: {[n['id'] for n in nodes]}")
print(f"Edges: {edges}")
print(f"Terminals: {terminals}")
print()
print(f"✅ AX1_GROWTH: 所有依赖覆盖 ✓")
print(f"{'❌' if orphans else '✅'} AX4_LAYOUT: 孤证节点={orphans or '无'}")
print(f"{'✅' if terminals else '❌'} AX6_BOUNDARY: 终止节点={terminals or '无'}")
print(f"❌ AX7_FREEDOM: 关键节点{critical}无fallback")
print(f"✅ AX8_CAUSAL: user_input→retrieval→llm 因果链完整")
print()
print("Score: 3/5")
print()
print("结论: RAG pipeline 结构完整，但关键节点(LLM)无 fallback。")
print("建议: 给 LLM 节点加 retry 或 backup 模型。")
