#!/usr/bin/env python3
"""Validate evidence structure, provenance, references, arithmetic and report facts."""

import argparse
import importlib.util
import json
import re
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path

from costlib import load, number, write_json


def validate_schema(value, schema, path="$", errors=None):
    """Offline validator for the keywords used by the bundled JSON Schema.

    Deliberately rejects unsupported keywords instead of silently passing them.
    The schema can also be used by a full Draft 2020-12 implementation.
    """
    errors = [] if errors is None else errors
    supported = {"$schema", "title", "description", "type", "required", "properties", "items",
                 "enum", "const", "minLength", "minItems"}
    if set(schema) - supported:
        errors.append(f"{path}: unsupported schema keyword")
        return errors
    checks = {"object": lambda v: isinstance(v, dict), "array": lambda v: isinstance(v, list),
              "string": lambda v: isinstance(v, str), "null": lambda v: v is None,
              "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
              "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
              "boolean": lambda v: isinstance(v, bool)}
    types = schema.get("type", [])
    types = [types] if isinstance(types, str) else types
    if types and not any(checks[t](value) for t in types):
        errors.append(f"{path}: expected {types}")
        return errors
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        errors.append(f"{path}: incorrect constant")
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: invalid enum")
    if isinstance(value, dict):
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key}: required")
        for key, child in schema.get("properties", {}).items():
            if key in value:
                validate_schema(value[key], child, f"{path}.{key}", errors)
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(f"{path}: too few items")
        for index, item in enumerate(value):
            validate_schema(item, schema.get("items", {}), f"{path}[{index}]", errors)
    if isinstance(value, str) and len(value) < schema.get("minLength", 0):
        errors.append(f"{path}: empty string")
    return errors


def facts(data):
    return {"schema_version": 1,
            "findings": [{k: f[k] for k in ("id", "readiness", "target", "action", "evidence_ids", "saving")}
                         for f in data["findings"]],
            "scenarios": [{k: s[k] for k in ("id", "action_ids", "baseline", "proposed", "saving")}
                          for s in data["scenarios"]]}


def timestamp(value):
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("timezone required")
    return parsed


def semantic_checks(data):
    errors = []
    ids = {}
    for name in ("observations", "findings", "scenarios"):
        values = [row["id"] for row in data[name]]
        if len(set(values)) != len(values):
            errors.append(f"{name}: duplicate IDs")
        ids[name] = set(values)
    if len(set.union(*ids.values())) != sum(len(v) for v in ids.values()):
        errors.append("IDs must be unique across evidence, findings and scenarios")
    sources = {s["name"]: s for s in data["sources"]}
    if len(sources) != len(data["sources"]):
        errors.append("duplicate source name")
    for source in sources.values():
        if source["status"] != "available" and not source["reason"]:
            errors.append("unavailable/partial source requires reason")
    for value in [data["review_started_at"], data["collected_at"], data["window"]["start"], data["window"]["end"]]:
        if value is not None:
            try:
                timestamp(value)
            except (ValueError, TypeError):
                errors.append("invalid ISO-8601 timestamp/timezone")
    start, end = data["window"]["start"], data["window"]["end"]
    if bool(start) != bool(end):
        errors.append("window start and end must both be known or both null")
    if start and end:
        try:
            if timestamp(start) >= timestamp(end):
                errors.append("window start must precede end")
        except ValueError:
            pass
    if (start is None or data["collected_at"] is None) and not data["window"]["coverage_notes"]:
        errors.append("unknown collection/window timestamp requires coverage notes")
    for observation in data["observations"]:
        source = sources.get(observation["source"])
        if source is None:
            errors.append(f"{observation['id']}: unknown source")
        if source and source["status"] == "unavailable" and observation["value"] is not None:
            errors.append(f"{observation['id']}: unavailable source cannot supply a measurement")
        if observation["timestamp"] is not None:
            try:
                timestamp(observation["timestamp"])
            except (ValueError, TypeError):
                errors.append(f"{observation['id']}: invalid timestamp")
        if observation["value"] is not None:
            if not observation["unit"] or not observation["aggregation"]:
                errors.append(f"{observation['id']}: observed values require units and aggregation")
            if observation["timestamp"] is None and not observation["limitations"]:
                errors.append(f"{observation['id']}: missing timestamp requires limitation")
    for finding in data["findings"]:
        if set(finding["evidence_ids"]) - ids["observations"]:
            errors.append(f"{finding['id']}: dangling evidence reference")
        if set(finding["dependencies"]) - ids["findings"] or finding["id"] in finding["dependencies"]:
            errors.append(f"{finding['id']}: invalid dependency")
        saving = finding["saving"]
        if (saving["low"] is None) != (saving["high"] is None):
            errors.append(f"{finding['id']}: both savings bounds must be known or null")
        if saving["low"] is not None:
            if number(saving["low"]) > number(saving["high"]):
                errors.append(f"{finding['id']}: reversed savings bounds")
            for key in ("currency", "basis", "formula", "period"):
                if not saving[key]:
                    errors.append(f"{finding['id']}: priced saving needs {key}")
            if saving["currency"] != data["pricing"]["currency"] or saving["basis"] != data["pricing"]["basis"]:
                errors.append(f"{finding['id']}: pricing basis/currency mismatch")
            if any(not data["pricing"][k] for k in ("rate_source", "rate_date", "period")):
                errors.append(f"{finding['id']}: missing rate provenance")
    # Dependencies form an acyclic implementation order.
    graph = {f["id"]: f["dependencies"] for f in data["findings"]}
    def visit(node, trail):
        if node in trail:
            return True
        return any(visit(child, trail | {node}) for child in graph.get(node, []))
    if any(visit(node, set()) for node in graph):
        errors.append("cyclic finding dependencies")
    spec = importlib.util.spec_from_file_location("calculator", Path(__file__).with_name("calculate-savings.py"))
    calculator = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(calculator)
    for scenario in data["scenarios"]:
        if set(scenario["action_ids"]) - ids["findings"] or len(set(scenario["action_ids"])) != len(scenario["action_ids"]):
            errors.append(f"{scenario['id']}: invalid action IDs")
        values = [scenario[k] for k in ("baseline", "proposed", "saving")]
        if any(v is not None for v in values):
            if any(v is None for v in values):
                errors.append(f"{scenario['id']}: partial scenario cost")
                continue
            if any(not data["pricing"][k] for k in ("currency", "basis", "rate_source", "rate_date", "period")):
                errors.append(f"{scenario['id']}: missing rate provenance")
            try:
                before, _ = calculator.cost(scenario["baseline_components"])
                after, _ = calculator.cost(scenario["proposed_components"])
                for key, expected in (("baseline", before), ("proposed", after), ("saving", before - after)):
                    if abs(number(scenario[key]) - expected) > number("0.000001"):
                        errors.append(f"{scenario['id']}: {key} does not reconcile with component arithmetic")
            except (KeyError, ValueError, TypeError) as error:
                errors.append(f"{scenario['id']}: invalid components ({error})")
    priced = {action for s in data["scenarios"] if s["saving"] is not None for action in s["action_ids"]}
    for finding in data["findings"]:
        if finding["saving"]["low"] is not None and finding["id"] not in priced:
            errors.append(f"{finding['id']}: priced finding lacks a reconciled scenario")
    # For standalone actions, the reported range must enclose its scenario delta.
    for scenario in data["scenarios"]:
        if len(scenario["action_ids"]) == 1 and scenario["saving"] is not None:
            finding = next((f for f in data["findings"] if f["id"] == scenario["action_ids"][0]), None)
            if finding and finding["saving"]["low"] is not None and not (
                number(finding["saving"]["low"]) <= number(scenario["saving"]) <= number(finding["saving"]["high"])):
                errors.append(f"{finding['id']}: saving range excludes standalone scenario delta")
    return errors


LOCAL_PATH = re.compile(r"(?:/Users/|/home/|/private/var/|/var/folders/|/tmp/|/etc/|/opt/|/usr/local/|[A-Za-z]:[\\/]|(?:~|\$HOME)/)")


class FactsParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.blocks = []
        self.unsafe_scripts = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "script" and attributes.get("id") == "cost-review-facts" and attributes.get("type") == "application/json":
            self.active = True
            self.blocks.append("")
            if attributes.get("src"):
                self.unsafe_scripts.append("external source on facts block")
        elif tag == "script":
            self.unsafe_scripts.append("unexpected script element")

    def handle_data(self, text):
        if self.active:
            self.blocks[-1] += text

    def handle_endtag(self, tag):
        if tag == "script":
            self.active = False


def report_checks(path, kind, expected):
    text = Path(path).read_text()
    errors = []
    if not text.strip():
        errors.append(f"{kind}: empty report")
    if LOCAL_PATH.search(text):
        errors.append(f"{kind}: machine-local path remains")
    if kind == "markdown":
        blocks = re.findall(r"<!-- cost-review-facts -->\s*```json\s*(.*?)\s*```", text, re.S)
    else:
        parser = FactsParser()
        parser.feed(text)
        blocks = parser.blocks
        if parser.unsafe_scripts:
            errors.append("html: only the inert inline canonical facts script is permitted")
    try:
        if len(blocks) != 1 or json.loads(blocks[0]) != expected:
            errors.append(f"{kind}: canonical finding/scenario facts missing or inconsistent")
    except (ValueError, IndexError):
        errors.append(f"{kind}: invalid report facts JSON")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--markdown")
    parser.add_argument("--html")
    parser.add_argument("--facts-output", help="Write canonical facts for embedding in both reports")
    parser.add_argument("--checks-output")
    args = parser.parse_args()
    try:
        data = load(args.evidence)
        schema = load(Path(__file__).parent.parent / "references" / "evidence.schema.json")
        errors = validate_schema(data, schema)
        if not errors:
            errors += semantic_checks(data)
            if LOCAL_PATH.search(json.dumps(data)):
                errors.append("evidence: machine-local path remains")
            for name, value in data["outputs"].items():
                if value and ("/" in value or "\\" in value):
                    errors.append(f"outputs.{name}: use standalone filenames")
            for kind in ("markdown", "html"):
                path = getattr(args, kind)
                if path:
                    if data["outputs"][kind] != Path(path).name:
                        errors.append(f"outputs.{kind}: filename mismatch")
                    errors += report_checks(path, kind, facts(data))
        if not errors and args.facts_output:
            write_json(args.facts_output, facts(data))
    except (OSError, ValueError, TypeError, KeyError) as error:
        errors = [f"validation input error: {type(error).__name__}"]
    checks = {"passed": not errors, "errors": errors,
              "limitations": ["Report facts validate the embedded contract; inspect rendered prose/tables and provider feasibility separately."]}
    if args.checks_output:
        write_json(args.checks_output, checks)
    print(json.dumps(checks, indent=2))
    raise SystemExit(bool(errors))


if __name__ == "__main__":
    main()
