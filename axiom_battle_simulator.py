#!/usr/bin/env python3
"""
Axiom Battle 收敛性模拟器

目标：验证 axiom-battle 在有限步内收敛
方法：蒙特卡洛模拟 + 状态机追踪

运行:
  python axiom_battle_simulator.py
  python axiom_battle_simulator.py --trials 1000
"""

import random, json, argparse
from collections import defaultdict
from dataclasses import dataclass, asdict
from typing import List, Dict, Set, Optional

# ── Axiom 定义 ────────────────────────────────────────────
AXIOMS = ['A1', 'A2', 'A4', 'A6', 'A7', 'A8', 'A9']

# 初始强度系数
INITIAL_SIGMA = {a: 0.5 for a in AXIOMS}

# 偏序关系（强度相等时的优先级）
AXIOM_RANK = {'A8': 7, 'A2': 6, 'A1': 5, 'A4': 4, 'A6': 3, 'A7': 2, 'A9': 1}

@dataclass
class AxiomState:
    sigma: float
    alive: bool
    wins: int
    losses: int

class AxiomBattleSimulator:
    def __init__(self, seed: Optional[int] = None):
        self.rng = random.Random(seed)
        self.history = []

    def reset(self):
        self.state = {a: AxiomState(
            sigma=INITIAL_SIGMA[a],
            alive=True,
            wins=0, losses=0
        ) for a in AXIOMS}
        self.round = 0
        self.history = []

    def select_pair(self) -> tuple:
        """从存活公理中随机选择一对"""
        alive = [a for a in AXIOMS if self.state[a].alive]
        if len(alive) < 2:
            return None, None
        pair = self.rng.sample(alive, 2)
        return pair[0], pair[1]

    def battle_round(self) -> Dict:
        """执行一轮对抗，返回结果"""
        self.round += 1
        a, b = self.select_pair()
        if a is None:
            return {"converged": True, "reason": "fewer_than_two_alive"}

        sigma_a = self.state[a].sigma
        sigma_b = self.state[b].sigma

        # 强度高者胜率更高（带随机性）
        total = sigma_a + sigma_b + 0.1  # 防止除零
        prob_a = (sigma_a + 0.05) / total

        if self.rng.random() < prob_a:
            winner, loser = a, b
        else:
            winner, loser = b, a

        # 更新强度
        delta = 0.1
        self.state[winner].sigma = min(1.0, self.state[winner].sigma + delta)
        self.state[winner].wins += 1
        self.state[loser].sigma = max(0.0, self.state[loser].sigma - delta)
        self.state[loser].losses += 1

        # 检查死亡条件
        death_threshold = 0.1
        if self.state[loser].sigma <= death_threshold:
            self.state[loser].alive = False

        return {
            "round": self.round,
            "winner": winner,
            "loser": loser,
            "sigma_a": self.state[a].sigma,
            "sigma_b": self.state[b].sigma,
            "dead": loser if not self.state[loser].alive else None,
            "alive_count": sum(1 for s in self.state.values() if s.alive)
        }

    def run(self, max_rounds: int = 1000) -> Dict:
        """运行模拟直到收敛或达到最大轮数"""
        self.reset()
        events = []
        for _ in range(max_rounds):
            result = self.battle_round()
            events.append(result)
            if result.get("converged"):
                events[-1]["converged_at"] = self.round
                break
            if result.get("dead"):
                events[-1]["dead_at"] = self.round

        survivors = [a for a in AXIOMS if self.state[a].alive]
        return {
            "total_rounds": self.round,
            "survivors": survivors,
            "survivor_count": len(survivors),
            "events": events,
            "final_sigma": {a: round(s.sigma, 4) for a, s in self.state.items()},
            "converged": len(survivors) <= 2  # 剩余1-2个公理视为收敛
        }


def run_trials(n: int = 100, seed: int = 42) -> Dict:
    """运行多次模拟，统计收敛性"""
    results = []
    for i in range(n):
        sim = AxiomBattleSimulator(seed=seed + i)
        r = sim.run()
        results.append(r)

    total_rounds = [r["total_rounds"] for r in results]
    survivor_counts = [r["survivor_count"] for r in results]

    return {
        "n_trials": n,
        "avg_rounds_to_converge": sum(total_rounds) / n,
        "min_rounds": min(total_rounds),
        "max_rounds": max(total_rounds),
        "survivor_distribution": {
            f"{k} survivors": survivor_counts.count(k)
            for k in sorted(set(survivor_counts))
        },
        "convergence_rate": sum(1 for r in results if r["converged"]) / n,
        "samples": results[:5]  # 前5个样本详情
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=100)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    print(f"运行 {args.trials} 次 axiom-battle 模拟...\n")
    results = run_trials(n=args.trials, seed=args.seed)

    print("=" * 50)
    print("  Axiom Battle 收敛性验证报告")
    print("=" * 50)
    print(f"\n总试验次数: {results['n_trials']}")
    print(f"平均收敛轮数: {results['avg_rounds_to_converge']:.1f}")
    print(f"最快收敛: {results['min_rounds']} 轮")
    print(f"最慢收敛: {results['max_rounds']} 轮")
    print(f"收敛率: {results['convergence_rate']:.1%}")
    print(f"\n幸存者分布:")
    for k, v in results["survivor_distribution"].items():
        print(f"  {k}: {v} 次 ({v/args.trials:.0%})")

    print(f"\n样本详情（前5个）:")
    for i, r in enumerate(results["samples"]):
        print(f"\n  样本{i+1}: 轮数={r['total_rounds']}, "
              f"幸存={r['survivors']}, "
              f"最终强度={r['final_sigma']}")
