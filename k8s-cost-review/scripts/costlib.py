"""Dependency-free quantity, resource and Decimal helpers for cost reviews."""

import json
import re
from decimal import Decimal, ROUND_CEILING
from pathlib import Path


def number(value):
    if isinstance(value, bool) or value is None:
        raise ValueError("expected a finite number")
    result = Decimal(str(value))
    if not result.is_finite():
        raise ValueError("expected a finite number")
    return result


def quantity(value, resource, exact=False):
    """Return CPU in millicores; memory/storage/hugepages in bytes; others in units.

    Match Kubernetes scheduler rounding (ceil positive quantities). Parse decimal,
    binary SI and exponent forms without floating-point intermediates.
    """
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+))([eE][+-]?\d+|[numkKMGTPE]|[KMGTPE]i)?", str(value))
    if not match:
        raise ValueError(f"invalid {resource} quantity")
    raw, suffix = match.groups()
    suffix = suffix or ""
    factors = {"": 1, "n": Decimal("1e-9"), "u": Decimal("1e-6"),
               "m": Decimal("1e-3"), "k": 1000, "K": 1000}
    factors.update({s: 1000 ** i for i, s in enumerate("MGTPE", 2)})
    factors.update({s + "i": 1024 ** i for i, s in enumerate("KMGTPE", 1)})
    factor = Decimal("1" + suffix) if re.fullmatch(r"[eE][+-]?\d+", suffix) else factors[suffix]
    result = number(raw) * factor * (1000 if resource == "cpu" else 1)
    if result < 0:
        raise ValueError("negative resource quantity")
    return result if exact else int(result.to_integral_value(rounding=ROUND_CEILING))


def resources(raw, exact=False):
    return {key: quantity(value, key, exact=exact) for key, value in (raw or {}).items()}


def add(*maps):
    result = {}
    for mapping in maps:
        for key, value in mapping.items():
            result[key] = result.get(key, 0) + value
    return result


def maximum(*maps):
    result = {}
    for mapping in maps:
        for key, value in mapping.items():
            result[key] = max(result.get(key, 0), value)
    return result


def effective_requests(pod, version):
    """Admitted spec requests; unresolved resize/version cases fail closed."""
    match = re.match(r"v?(\d+)\.(\d+)", version or "")
    if not match or int(match[1]) != 1 or not 28 <= int(match[2]) <= 35:
        return None, ["effective-request helper supports Kubernetes 1.28–1.35 only"]
    minor = int(match[2])
    spec, status = pod.get("spec", {}), pod.get("status", {})
    reasons = []
    sidecars = any(c.get("restartPolicy") == "Always" for c in spec.get("initContainers", []))
    if sidecars and minor < 29:
        reasons.append("restartable init sidecar feature gate must be verified on 1.28")
    pod_requests = spec.get("resources", {}).get("requests", {})
    if spec.get("resources") and minor < 34:
        reasons.append("PodLevelResources feature gate must be verified before 1.34")
    if status.get("resize") or any(c.get("type", "").startswith("PodResize") and c.get("status") == "True"
                                   for c in status.get("conditions", [])):
        reasons.append("in-place resize state requires scheduler status-resource accounting")
    for key in ("containerStatuses", "initContainerStatuses"):
        for container in status.get(key, []):
            allocated = container.get("allocatedResources")
            actuated = container.get("resources", {}).get("requests")
            originals = spec.get("containers" if key == "containerStatuses" else "initContainers", [])
            expected = next((c.get("resources", {}).get("requests", {}) for c in originals
                             if c.get("name") == container.get("name")), {})
            if any(raw is not None and resources(raw, exact=True) != resources(expected, exact=True) for raw in (allocated, actuated)):
                reasons.append("spec/status requests differ; scheduler resize accounting is unresolved")
    if status.get("allocatedResources") or status.get("resources"):
        reasons.append("pod-level status resource accounting requires scheduler verification")
    if reasons:
        return None, sorted(set(reasons))
    regular = add(*(resources(c.get("resources", {}).get("requests"), exact=True) for c in spec.get("containers", [])))
    running_sidecars, init_peak = {}, {}
    for container in spec.get("initContainers", []):
        req = resources(container.get("resources", {}).get("requests"), exact=True)
        if container.get("restartPolicy") == "Always":
            running_sidecars = add(running_sidecars, req)
            phase = running_sidecars
        else:
            phase = add(running_sidecars, req)
        init_peak = maximum(init_peak, phase)
    result = maximum(add(regular, running_sidecars), init_peak)
    for key, value in resources(pod_requests, exact=True).items():
        if key in ("cpu", "memory") or key.startswith("hugepages-"):
            result[key] = value
        else:
            return None, ["unsupported pod-level resource"]
    result = add(result, resources(spec.get("overhead"), exact=True))
    return {key: int(number(value).to_integral_value(rounding=ROUND_CEILING)) for key, value in result.items()}, []


def load(path):
    def finite_float(raw):
        value = float(raw)
        if not Decimal(str(value)).is_finite():
            raise ValueError("non-finite JSON number")
        return value

    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON key")
            result[key] = value
        return result

    return json.loads(Path(path).read_text(), parse_float=finite_float, object_pairs_hook=unique_keys,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite JSON")))


def write_json(path, value):
    """Never overwrite another run's evidence."""
    with Path(path).open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")
