#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict

import urllib.request


def _base(url: str) -> str:
    return url.rstrip("/")


def http(method: str, url: str, body: Dict[str, Any] | None = None) -> Any:
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def cmd_agents(args):
    if args.subcmd == "add":
        payload = {"name": args.name, "kind": args.kind}
        res = http("POST", f"{_base(args.url)}/agents", payload)
        print(json.dumps(res, indent=2))
    elif args.subcmd == "list":
        res = http("GET", f"{_base(args.url)}/agents")
        print(json.dumps(res, indent=2))


def cmd_contexts(args):
    if args.subcmd == "create":
        payload = {"name": args.name}
        res = http("POST", f"{_base(args.url)}/contexts", payload)
        print(json.dumps(res, indent=2))
    elif args.subcmd == "list":
        res = http("GET", f"{_base(args.url)}/contexts")
        print(json.dumps(res, indent=2))


def cmd_memories(args):
    if args.subcmd == "add":
        payload = {"author": args.author, "text": args.text, "tags": args.tags}
        res = http("POST", f"{_base(args.url)}/contexts/{args.context}/memories", payload)
        print(json.dumps(res, indent=2))
    elif args.subcmd == "list":
        url = f"{_base(args.url)}/contexts/{args.context}/memories"
        if args.q:
            url += f"?q={args.q}"
        res = http("GET", url)
        print(json.dumps(res, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description="Memory Broker CLI helper")
    parser.add_argument("--url", default="http://localhost:7070")

    sub = parser.add_subparsers(dest="cmd", required=True)

    # agents
    p_agents = sub.add_parser("agents")
    sub_agents = p_agents.add_subparsers(dest="subcmd", required=True)
    pa_add = sub_agents.add_parser("add")
    pa_add.add_argument("--name", required=True)
    pa_add.add_argument("--kind", default="agent", choices=["agent", "human"])
    pa_add.set_defaults(func=cmd_agents)
    pa_list = sub_agents.add_parser("list")
    pa_list.set_defaults(func=cmd_agents)

    # contexts
    p_ctx = sub.add_parser("contexts")
    sub_ctx = p_ctx.add_subparsers(dest="subcmd", required=True)
    pc_create = sub_ctx.add_parser("create")
    pc_create.add_argument("--name", required=True)
    pc_create.set_defaults(func=cmd_contexts)
    pc_list = sub_ctx.add_parser("list")
    pc_list.set_defaults(func=cmd_contexts)

    # memories
    p_mem = sub.add_parser("memories")
    sub_mem = p_mem.add_subparsers(dest="subcmd", required=True)
    pm_add = sub_mem.add_parser("add")
    pm_add.add_argument("--context", required=True)
    pm_add.add_argument("--author", required=True)
    pm_add.add_argument("--text", required=True)
    pm_add.add_argument("--tags", nargs="*", default=[])
    pm_add.set_defaults(func=cmd_memories)
    pm_list = sub_mem.add_parser("list")
    pm_list.add_argument("--context", required=True)
    pm_list.add_argument("--q")
    pm_list.set_defaults(func=cmd_memories)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    main(sys.argv[1:])

