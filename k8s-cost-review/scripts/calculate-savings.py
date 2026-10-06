#!/usr/bin/env python3
"""Calculate disjoint billable-component scenarios using Decimal arithmetic."""

import argparse
from decimal import Decimal

from costlib import load, number, write_json


def cost(components):
    total, seen, rows = Decimal(0), set(), []
    for component in components:
        identity = component["id"]
        if identity in seen:
            raise ValueError("duplicate billable component id")
        seen.add(identity)
        required = ("quantity", "rate", "hours") if component["kind"] == "hourly" else ("amount",)
        if component["kind"] not in ("hourly", "fixed"):
            raise ValueError("component kind must be hourly or fixed")
        values = [number(component[key]) for key in required]
        if any(value < 0 for value in values):
            raise ValueError("cost inputs must be nonnegative")
        amount = values[0]
        for value in values[1:]:
            amount *= value
        total += amount
        rows.append({**component, "cost": float(amount), "cost_exact": str(amount)})
    return total, rows


def calculate(data):
    if not data.get("currency") or data.get("basis") not in ("marginal", "list", "amortized"):
        raise ValueError("currency and explicit cost basis are required")
    if not data.get("period") or not data.get("rate_source") or not data.get("rate_date"):
        raise ValueError("period, rate_source and rate_date are required")
    scenarios, seen = [], set()
    for scenario in data["scenarios"]:
        if scenario["id"] in seen:
            raise ValueError("duplicate scenario id")
        seen.add(scenario["id"])
        actions = scenario.get("action_ids", [])
        if len(set(actions)) != len(actions):
            raise ValueError("duplicate action in scenario")
        baseline, before = cost(scenario["baseline"])
        proposed, after = cost(scenario["proposed"])
        scenarios.append({"id": scenario["id"], "action_ids": actions,
                          "baseline": float(baseline), "proposed": float(proposed),
                          "saving": float(baseline - proposed), "saving_exact": str(baseline - proposed),
                          "baseline_components": before, "proposed_components": after})
    return {"schema_version": 1, "currency": data["currency"], "period": data["period"],
            "basis": data["basis"], "rate_source": data["rate_source"], "rate_date": data["rate_date"],
            "scenarios": scenarios,
            "limitations": ["Arithmetic does not establish marginal rates, removability or workload reliability; alternative scenarios are never added together."]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    try:
        write_json(args.output, calculate(load(args.input)))
    except (ValueError, KeyError, TypeError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
