#!/usr/bin/env python3
"""Project safe Kubernetes fields before collecting; offline input never uses CLI."""

import argparse
import json
import subprocess
from datetime import datetime, timezone

from costlib import add, effective_requests, load, resources, write_json


# Declarative allowlist is shared by server-side rendering and fixture projection.
# Arbitrary annotations, labels, env, commands, images and ConfigMaps are omitted.
RESOURCE = {"requests": "map", "limits": "map"}
CONTAINER = {"name": "str", "restartPolicy": "str", "resources": RESOURCE}
CONDITION = {"type": "str", "status": "str", "reason": "str"}
STATUS = {"name": "str", "restartCount": "number", "allocatedResources": "map",
          "resources": RESOURCE, "lastState": {"terminated": {"reason": "str", "exitCode": "number"}}}
META = {"name": "str", "namespace": "str", "ownerReferences": [{"kind": "str", "name": "str", "controller": "bool"}]}
POD = {"metadata": META, "spec": {"nodeName": "str", "containers": [CONTAINER],
       "initContainers": [CONTAINER], "overhead": "map", "resources": RESOURCE,
       "nodeSelector": "map", "tolerations": [{"key": "str", "operator": "str", "value": "str", "effect": "str"}],
       "volumes": [{"name": "str", "persistentVolumeClaim": {"claimName": "str"},
                    "emptyDir": {"medium": "str", "sizeLimit": "str"}, "hostPath": {"type": "str"}}]},
       "status": {"phase": "str", "resize": "str", "conditions": [CONDITION],
                  "containerStatuses": [STATUS], "initContainerStatuses": [STATUS],
                  "allocatedResources": "map", "resources": RESOURCE}}
NODE = {"metadata": {"name": "str"}, "spec": {"providerID": "str", "unschedulable": "bool",
        "taints": [{"key": "str", "value": "str", "effect": "str"}]},
        "status": {"allocatable": "map", "capacity": "map", "conditions": [CONDITION]}}


def project(value, shape):
    if isinstance(shape, dict):
        if not isinstance(value, dict):
            return {}
        return {k: project(value[k], child) for k, child in shape.items() if k in value and value[k] is not None}
    if isinstance(shape, list):
        return [project(v, shape[0]) for v in value] if isinstance(value, list) else []
    if shape == "map":
        return {str(k): str(v) for k, v in value.items()} if isinstance(value, dict) else {}
    return value


def template(shape):
    """Generate a kubectl Go template; absent fields render null, never raw objects."""
    if isinstance(shape, dict):
        fields = []
        for key, child in shape.items():
            fields.append(json.dumps(key) + ':{{with index . ' + json.dumps(key) + '}}' + template(child) + '{{else}}null{{end}}')
        return '{' + ','.join(fields) + '}'
    if isinstance(shape, list):
        return '[{{range $i, $v := .}}{{if $i}},{{end}}' + template(shape[0]) + '{{end}}]'
    if shape == "map":
        return '{ {{$comma := false}}{{range $k, $v := .}}{{if $comma}},{{end}}{{$comma = true}}{{printf "%q" $k}}:{{printf "%q" (printf "%v" $v)}}{{end}} }'
    return '{{printf "%q" (printf "%v" .)}}' if shape == "str" else '{{printf "%v" .}}'


def clean_nulls(value):
    if isinstance(value, dict):
        return {k: clean_nulls(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [clean_nulls(v) for v in value]
    return value


def query(context, timeout, arguments):
    result = subprocess.run(["kubectl", f"--context={context}", f"--request-timeout={timeout}s", *arguments],
                            capture_output=True, text=True, timeout=timeout + 5, check=True)
    return json.loads(result.stdout)


def normalize(raw, context, namespace=None):
    version = raw.get("version")
    if isinstance(version, dict):
        version = version.get("serverVersion", {}).get("gitVersion")
    pods = raw.get("pods", [])
    nodes = raw.get("nodes", [])
    pods = pods.get("items", []) if isinstance(pods, dict) else pods
    nodes = nodes.get("items", []) if isinstance(nodes, dict) else nodes
    output = {"schema_version": 1, "context": context, "namespace": namespace, "version": version,
              "collected_at": raw.get("collected_at"), "sources": raw.get("sources", []),
              "units": {"cpu": "millicores", "memory": "bytes", "ephemeral-storage": "bytes", "other": "units"},
              "nodes": [], "pods": [], "scheduled_requests": {}, "pending_requests": {},
              "unresolved_pods": [], "limitations": ["Inventory is not a placement simulation; affinity, topology, pool bounds, admission policy and billing need targeted evidence."]}
    for node in nodes:
        safe = clean_nulls(project(node, NODE))
        safe["allocatable_normalized"] = resources(safe.get("status", {}).get("allocatable"))
        output["nodes"].append(safe)
    for pod in pods:
        if namespace and pod.get("metadata", {}).get("namespace") != namespace:
            continue
        safe = clean_nulls(project(pod, POD))
        request, reasons = effective_requests(safe, version)
        safe["effective_requests"], safe["accounting_gaps"] = request, reasons
        phase, node = safe.get("status", {}).get("phase"), safe.get("spec", {}).get("nodeName")
        safe["demand_class"] = "completed" if phase in ("Succeeded", "Failed") else ("scheduled" if node else "pending")
        if safe["demand_class"] != "completed":
            if request is None:
                output["unresolved_pods"].append(safe.get("metadata", {}))
            else:
                key = safe["demand_class"] + "_requests"
                output[key] = add(output[key], request)
        output["pods"].append(safe)
    availability = {s.get("name"): s.get("status") for s in output["sources"]}
    output["accounting_complete"] = not output["unresolved_pods"] and bool(version) and "pods" in raw and all(
        availability.get(name, "available") == "available" for name in ("version", "pods"))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", required=True)
    parser.add_argument("--namespace")
    parser.add_argument("--input", help="Offline Kubernetes-shaped JSON; no live calls")
    parser.add_argument("--output", required=True)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    if not 1 <= args.timeout <= 120:
        parser.error("timeout must be 1–120 seconds")
    if args.input:
        raw = load(args.input)
        if raw.get("context") != args.context:
            parser.error("offline input context must match --context")
        raw = {**raw, "sources": [{"name": key, "status": "available" if key in raw else "unavailable"}
                                  for key in ("version", "nodes", "pods")]}
    else:
        raw = {"context": args.context, "collected_at": datetime.now(timezone.utc).isoformat(), "sources": []}
        jobs = [("version", ["version", "-o", "json"])]
        for name, shape in (("nodes", NODE), ("pods", POD)):
            scope = ["--namespace", args.namespace] if args.namespace and name == "pods" else (["-A"] if name == "pods" else [])
            jobs.append((name, ["get", name, *scope, "-o", "go-template=" + template({"items": [shape]})]))
        for name, arguments in jobs:
            try:
                raw[name] = query(args.context, args.timeout, arguments)
                raw["sources"].append({"name": name, "status": "available"})
            except (subprocess.SubprocessError, OSError, ValueError):
                # Stderr may contain local kubeconfig paths or credentials; never save it.
                raw["sources"].append({"name": name, "status": "unavailable", "reason": "client/API/projection failure; inspect runtime error separately"})
    write_json(args.output, normalize(raw, args.context, args.namespace))


if __name__ == "__main__":
    main()
