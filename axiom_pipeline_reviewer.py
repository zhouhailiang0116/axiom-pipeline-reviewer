#!/usr/bin/env python3
"""
Axiom Pipeline Reviewer — 悟道体系因果链审查器

用法:
  python axiom_pipeline_reviewer.py --input pipeline.yaml
  python axiom_pipeline_reviewer.py --demo

输入格式 (YAML):
  nodes:
    - id: step1
      name: 用户输入
      output: 原始问题
    - id: step2
      name: RAG检索
      input_from: [step1]
      output: 相关文档
      context: [向量库检索]
    - id: step3
      name: LLM生成
      input_from: [step2]
      output: 回答

  claim: "这个pipeline能回答用户问题"
"""

import yaml, json, sys
from typing import List, Dict

# ── Axiom 定义 ────────────────────────────────────────────
AXIOMS = {
    "AX1_GROWTH": {
        "name": "公理一·生长",
        "question": "这个节点的输出是下一个节点的必要输入吗？",
        "check": "每个consumer节点的所有required_input是否都被某个producer节点覆盖？"
    },
    "AX4_LAYOUT": {
        "name": "公理四·结构",
        "question": "有没有孤证节点（输出没被任何节点使用）？",
        "check": "所有非terminal节点的output都应该被至少一个节点引用"
    },
    "AX6_BOUNDARY": {
        "name": "公理六·边界",
        "question": "有没有明确的终止条件？",
        "check": "是否存在end节点，或者最大深度限制？"
    },
    "AX7_FREEDOM": {
        "name": "公理七·自由",
        "question": "关键节点是否有备选路径（冗余设计）？",
        "check": "核心节点（LLM调用）是否有fallback机制？"
    },
    "AX8_CAUSAL": {
        "name": "公理八·因果",
        "question": "从输入到最终输出，有没有完整的因果链？",
        "check": "每条路径都能追溯到起点、延伸到终点？"
    }
}

class AxiomResult:
    def __init__(self, axiom_id, name, passed, detail):
        self.axiom_id = axiom_id
        self.name = name
        self.passed = passed
        self.detail = detail

def load_pipeline(path: str) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)

def review(pipeline: dict, claim: str) -> List[AxiomResult]:
    nodes = {n["id"]: n for n in pipeline.get("nodes", [])}
    edges = []  # (producer, consumer)
    for n in nodes.values():
        for src in n.get("input_from", []):
            edges.append((src, n["id"]))

    results = []

    # ── AX1_GROWTH: 覆盖检查 ─────────────────────────────
    coverage = {}
    for node_id, node in nodes.items():
        for src in node.get("input_from", []):
            coverage.setdefault(src, []).append(node_id)

    missing = []
    for node_id, node in nodes.items():
        required = node.get("requires", [])
        for req in required:
            producers = [s for s, cs in edges if s == req and node_id in cs]
            if not producers:
                missing.append(f"  ❌ {node_id} 需要 {req}，但没有节点产出")

    if missing:
        results.append(AxiomResult("AX1_GROWTH", AXIOMS["AX1_GROWTH"]["name"], False,
            f"发现 {len(missing)} 个缺失依赖\n" + "\n".join(missing)))
    else:
        results.append(AxiomResult("AX1_GROWTH", AXIOMS["AX1_GROWTH"]["name"], True,
            "所有依赖均已覆盖 ✓"))

    # ── AX4_LAYOUT: 孤证检查 ─────────────────────────────
    consumed = set(src for src, _ in edges)
    terminals = [n["id"] for n in nodes.values() if n.get("terminal")]
    orphans = [n["id"] for n in nodes.values()
               if n["id"] not in consumed and n["id"] not in terminals]

    if orphans:
        results.append(AxiomResult("AX4_LAYOUT", AXIOMS["AX4_LAYOUT"]["name"], False,
            f"孤证节点: {orphans}，输出未被任何节点使用"))
    else:
        results.append(AxiomResult("AX4_LAYOUT", AXIOMS["AX4_LAYOUT"]["name"], True,
            "所有节点输出均被消费，无孤证 ✓"))

    # ── AX6_BOUNDARY: 终止条件 ──────────────────────────
    terminals = [n["id"] for n in nodes.values() if n.get("terminal")]
    max_depth = pipeline.get("max_depth", 10)

    if not terminals:
        results.append(AxiomResult("AX6_BOUNDARY", AXIOMS["AX6_BOUNDARY"]["name"], False,
            f"无终止节点，可能无限循环（当前最大深度={max_depth}）"))
    else:
        results.append(AxiomResult("AX6_BOUNDARY", AXIOMS["AX6_BOUNDARY"]["name"], True,
            f"有终止节点: {terminals} ✓"))

    # ── AX7_FREEDOM: 备选路径 ────────────────────────────
    critical = [n["id"] for n in nodes.values() if n.get("critical")]
    no_fallback = []
    for cid in critical:
        crit_node = nodes[cid]
        if not crit_node.get("fallback") and not any(
            other.get("fallback") == cid for other in nodes.values()):
            no_fallback.append(cid)

    if no_fallback:
        results.append(AxiomResult("AX7_FREEDOM", AXIOMS["AX7_FREEDOM"]["name"], False,
            f"关键节点无备选: {no_fallback}"))
    else:
        results.append(AxiomResult("AX7_FREEDOM", AXIOMS["AX7_FREEDOM"]["name"], True,
            "关键节点均有fallback机制 ✓"))

    # ── AX8_CAUSAL: 因果链完整性 ─────────────────────────
    # BFS从起点到终点的路径检查
    start_nodes = [n["id"] for n in nodes.values() if not n.get("input_from")]
    end_nodes = terminals if terminals else [n["id"] for n in nodes.values()
                                               if not n.get("output_to")]

    def bfs_paths(start, end):
        from collections import deque
        queue = deque([(start, [start])])
        all_paths = []
        while queue:
            node, path = queue.popleft()
            for next_node in [n for n, cs in edges if n == node]:
                new_path = path + [next_node]
                if next_node == end:
                    all_paths.append(new_path)
                else:
                    queue.append((next_node, new_path))
        return all_paths

    if start_nodes and end_nodes:
        complete_paths = bfs_paths(start_nodes[0], end_nodes[0])
        if complete_paths:
            avg_len = sum(len(p) for p in complete_paths) / len(complete_paths)
            results.append(AxiomResult("AX8_CAUSAL", AXIOMS["AX8_CAUSAL"]["name"], True,
                f"从 {start_nodes[0]} 到 {end_nodes[0]} 共 {len(complete_paths)} 条因果链，平均长度 {avg_len:.1f} 步 ✓"))
        else:
            results.append(AxiomResult("AX8_CAUSAL", AXIOMS["AX8_CAUSAL"]["name"], False,
                f"从 {start_nodes[0]} 到 {end_nodes[0]} 无完整路径，因果链断裂"))
    else:
        results.append(AxiomResult("AX8_CAUSAL", AXIOMS["AX8_CAUSAL"]["name"], False,
            "无法确定起点或终点节点"))

    return results

def print_report(claim: str, results: List[AxiomResult]):
    score = sum(1 for r in results if r.passed)
    print(f"\n{'='*50}")
    print(f"  Axiom Pipeline Review")
    print(f"{'='*50}")
    print(f"\nClaim: {claim}")
    print(f"\nScore: {score}/{len(results)}")
    print()
    for r in results:
        icon = "✅" if r.passed else "❌"
        print(f"  {icon} {r.name}")
        print(f"     {r.detail}")
        print()

# ── Demo ──────────────────────────────────────────────────
DEMO_PIPELINE = {
    "nodes": [
        {"id": "user_input", "name": "用户输入", "output": "原始问题", "output_to": ["retrieval"]},
        {"id": "retrieval", "name": "向量检索", "requires": ["user_input"], "input_from": ["user_input"], "output": "相关文档", "output_to": ["llm"]},
        {"id": "llm", "name": "LLM生成", "requires": ["retrieval"], "input_from": ["retrieval"], "output": "回答", "critical": True, "terminal": True},
    ],
    "terminal": "llm",
    "max_depth": 5
}

if __name__ == "__main__":
    if "--demo" in sys.argv:
        print_report("这个RAG pipeline能正确回答用户问题", review(DEMO_PIPELINE, "这个RAG pipeline能正确回答用户问题"))

    elif "--input" in sys.argv:
        idx = sys.argv.index("--input")
        path = sys.argv[idx + 1]
        pipe = load_pipeline(path)
        claim = pipe.get("claim", "pipeline有效")
        print_report(claim, review(pipe, claim))

    else:
        print(__doc__)
