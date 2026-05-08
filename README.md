# Axiom Pipeline Reviewer

用悟道体系审查 AI 系统的因果链。

**不是帮你做 AI 系统，是帮你审查你做的 AI 系统是否因果链完整。**

---

## 适用场景

- RAG 系统返回答非所问 → 检索和生成之间的因果链断了
- Agent 调用工具失败整个流程卡死 → 没有 fallback
- prompt 链里某个步骤的输出没被下一步使用 → 孤证节点
- 循环调用直到 token 耗尽 → 没有终止条件

---

## 五维审查

| 公理 | 检查什么 |
|------|---------|
| **AX1 生长** | 每个节点的依赖是否都有节点产出？ |
| **AX4 结构** | 有没有输出没被任何节点使用的"孤证节点"？ |
| **AX6 边界** | 有没有明确的终止条件？ |
| **AX7 自由** | 关键节点（LLM调用）有没有 fallback？ |
| **AX8 因果** | 从输入到输出，有没有完整的因果链？ |

---

## 安装

```bash
pip install pyyaml
```

---

## 使用

```bash
# Demo
python axiom_pipeline_reviewer.py --demo

# 审查你的 pipeline
python axiom_pipeline_reviewer.py --input my_pipeline.yaml
```

---

## 输入格式

```yaml
# my_pipeline.yaml
claim: "这个 pipeline 能回答用户问题"

nodes:
  - id: user_input
    name: 用户输入
    output: 原始问题

  - id: retrieval
    name: 向量检索
    input_from: [user_input]
    output: 相关文档

  - id: llm
    name: LLM生成
    input_from: [retrieval]
    output: 回答
    critical: true
    fallback: gpt-3.5
    terminal: true

terminal: llm
max_depth: 5
```

---

## 示例输出

```
Score: 4/5

✅ AX1_GROWTH: 所有依赖覆盖 ✓
✅ AX4_LAYOUT: 无孤证节点 ✓
✅ AX6_BOUNDARY: 终止节点: ['llm'] ✓
✅ AX7_FREEDOM: 关键节点均有fallback机制 ✓
❌ AX8_CAUSAL: 缺少显性的"验证节点"，无法确认检索结果质量

建议: 在 retrieval 后加一个 relevance filter
```

---

## 打赏

有用的话，欢迎请我喝咖啡：

https://cdn.jsdelivr.net/gh/zhouhailiang0116/axiom-battle@main/微信收款码.png

---

*哲学基础：悟道体系 · 证伪主义 + 因果链约束。不承诺预测结果，只保证判断过程可追溯。*
