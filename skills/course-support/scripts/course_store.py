#!/usr/bin/env python3
"""Inspect canonical course context, records and recent runs; preview/reset demo rows."""
import argparse
from course_runtime import Config, Store, add_storage_args, cli_main, emit


def main():
    p = argparse.ArgumentParser(description=__doc__)
    add_storage_args(p)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("context")
    runs = sub.add_parser("runs")
    runs.add_argument("--limit", type=int, default=20)
    runs.add_argument("--skill")
    read = sub.add_parser("read")
    read.add_argument("collection")
    read.add_argument("id")
    reset = sub.add_parser("reset")
    reset.add_argument("--confirm")
    a = p.parse_args()
    store = Store(Config.from_args(a))
    if a.command == "context":
        emit(store.context())
    elif a.command == "runs":
        values = store.list("skill_runs", a.limit)
        emit([r for r in values if not a.skill or r["data"]["skill_name"] == a.skill])
    elif a.command == "read":
        emit(store.get(a.collection, a.id))
    else:
        emit(store.reset(a.confirm))


if __name__ == "__main__":
    cli_main(main)
