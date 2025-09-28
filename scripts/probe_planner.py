#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from collections import Counter
from typing import Any, Dict, List, Optional

from memory_broker.planner import get_planner


def summarize_plan(plan: Dict[str, Any]) -> Dict[str, Any]:
    agents = plan.get("agents", []) or []
    actions = plan.get("actions", []) or []
    types = [a.get("type", "?") for a in actions if isinstance(a, dict)]
    counts = Counter(types)
    return {
        "agents": len(agents),
        "actions": len(actions),
        "by_type": dict(counts),
    }


def run(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Probe the configured planner and report plan complexity")
    p.add_argument("--prompt", help="User prompt", default="Build a non-trivial web application")
    p.add_argument("--context-id", help="Context id to embed in prompt", default="probe-context")
    p.add_argument("--planner", choices=["mock", "codex"], default=None, help="Planner backend to use (overrides env)")
    p.add_argument("--repeat", type=int, default=1, help="Number of plans to sample")
    p.add_argument("--print-json", action="store_true", help="Print full plan JSON for each sample")
    p.add_argument("--out", default=None, help="Directory to write sampled plans (plan_<i>.json)")
    args = p.parse_args(argv)

    if args.planner:
        os.environ["BROKER_PLANNER"] = args.planner

    planner = get_planner()
    results: List[Dict[str, Any]] = []

    if args.out:
        os.makedirs(args.out, exist_ok=True)

    for i in range(args.repeat):
        plan_obj = planner.plan(context_id=args.context_id, prompt=args.prompt)
        plan = plan_obj.model_dump(mode="json")
        summary = summarize_plan(plan)
        results.append(summary)

        print(f"Sample {i+1}: agents={summary['agents']} actions={summary['actions']} by_type={summary['by_type']}")
        if args.print_json:
            print(json.dumps(plan, indent=2))
        if args.out:
            path = os.path.join(args.out, f"plan_{i+1:03d}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2)

    # Aggregate
    total_agents = sum(r["agents"] for r in results)
    total_actions = sum(r["actions"] for r in results)
    merged_types: Counter[str] = Counter()
    for r in results:
        merged_types.update(r["by_type"]) 

    print("\n=== Aggregate ===")
    print(json.dumps({
        "samples": len(results),
        "avg_agents": (total_agents / len(results)) if results else 0,
        "avg_actions": (total_actions / len(results)) if results else 0,
        "action_types_total": dict(merged_types),
    }, indent=2))

    return 0


if __name__ == "__main__":
    raise SystemExit(run())

