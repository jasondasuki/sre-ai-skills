"""Offline regression tests for Kubernetes inventory and cost arithmetic helpers."""

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path


EVALS = Path(__file__).resolve().parent
CORE = EVALS.parent
SCRIPTS = CORE / "scripts"
sys.path.insert(0, str(SCRIPTS))

from costlib import effective_requests, load, quantity  # noqa: E402


def load_script(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


inventory = load_script("collect_inventory", "collect-inventory.py")
calculator = load_script("calculate_savings", "calculate-savings.py")


def pod(spec, status=None):
    return {"spec": spec, "status": status or {}}


class QuantityAndRequestAccountingTests(unittest.TestCase):
    def test_quantity_binary_decimal_exponent_and_ceiling(self):
        self.assertEqual(quantity("1Ki", "memory"), 1024)
        self.assertEqual(quantity("1.5Mi", "memory"), 1_572_864)
        self.assertEqual(quantity("1k", "memory"), 1000)
        self.assertEqual(quantity("1e3", "memory"), 1000)
        self.assertEqual(quantity("1e-3", "cpu"), 1)
        self.assertEqual(quantity("1.1e-3", "cpu"), 2)
        self.assertEqual(quantity("1.1m", "cpu"), 2)
        self.assertEqual(quantity("0.0000001", "cpu"), 1)

    def test_restartable_init_sidecars_accumulate_across_sequential_init_phases(self):
        candidate = pod({
            "containers": [{"name": "app", "resources": {"requests": {"cpu": "500m", "memory": "500Mi"}}}],
            "initContainers": [
                {"name": "sidecar-a", "restartPolicy": "Always", "resources": {"requests": {"cpu": "100m", "memory": "100Mi"}}},
                {"name": "init-a", "resources": {"requests": {"cpu": "700m", "memory": "700Mi"}}},
                {"name": "sidecar-b", "restartPolicy": "Always", "resources": {"requests": {"cpu": "200m", "memory": "200Mi"}}},
                {"name": "init-b", "resources": {"requests": {"cpu": "600m", "memory": "600Mi"}}},
            ],
        })
        result, reasons = effective_requests(candidate, "v1.35.0")
        self.assertEqual(reasons, [])
        self.assertEqual(result, {"cpu": 900, "memory": 900 * 1024**2})

    def test_pod_level_requests_override_container_aggregate_then_add_overhead(self):
        candidate = pod({
            "containers": [{"name": "app", "resources": {"requests": {"cpu": "2", "memory": "4Gi"}}}],
            "resources": {"requests": {"cpu": "1250m", "memory": "2Gi"}},
            "overhead": {"cpu": "100m", "memory": "128Mi"},
        })
        result, reasons = effective_requests(candidate, "v1.35.0")
        self.assertEqual(reasons, [])
        self.assertEqual(result, {"cpu": 1350, "memory": 2 * 1024**3 + 128 * 1024**2})

    def test_unsupported_versions_and_unverified_feature_gates_fail_closed(self):
        base = {"containers": [{"name": "app", "resources": {"requests": {"cpu": "1"}}}]}
        for version in ("v1.27.9", "v1.36.0", "unknown"):
            with self.subTest(version=version):
                result, reasons = effective_requests(pod(base), version)
                self.assertIsNone(result)
                self.assertTrue(reasons)
        sidecar = {**base, "initContainers": [{"name": "sidecar", "restartPolicy": "Always"}]}
        result, reasons = effective_requests(pod(sidecar), "v1.28.8")
        self.assertIsNone(result)
        self.assertTrue(any("feature gate" in reason for reason in reasons))
        pod_resources = {**base, "resources": {"requests": {"cpu": "1"}}}
        result, reasons = effective_requests(pod(pod_resources), "v1.33.5")
        self.assertIsNone(result)
        self.assertTrue(any("PodLevelResources" in reason for reason in reasons))

    def test_in_place_resize_and_spec_status_request_mismatch_are_unresolved(self):
        base = {"containers": [{"name": "app", "resources": {"requests": {"cpu": "1"}}}]}
        resize, reasons = effective_requests(pod(base, {"resize": "InProgress"}), "v1.35.0")
        self.assertIsNone(resize)
        self.assertTrue(any("resize state" in reason for reason in reasons))
        mismatch_status = {"containerStatuses": [{"name": "app", "allocatedResources": {"cpu": "500m"}}]}
        mismatch, reasons = effective_requests(pod(base, mismatch_status), "v1.35.0")
        self.assertIsNone(mismatch)
        self.assertTrue(any("spec/status requests differ" in reason for reason in reasons))


class ProjectionAndInventoryTests(unittest.TestCase):
    def test_cli_fixture_mode_never_invokes_kubectl_and_preserves_source_time(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fake = root / "kubectl"
            marker = root / "called"
            fake.write_text('#!/bin/sh\ntouch "' + str(marker) + '"\nexit 9\n')
            fake.chmod(0o700)
            source = EVALS / "fixtures" / "sidecar-fragmentation" / "inventory.json"
            supplied = load(source)
            supplied["collected_at"] = "2026-10-01T00:00:00Z"
            source = root / "fixture.json"
            source.write_text(json.dumps(supplied))
            output = root / "out.json"
            result = subprocess.run([sys.executable, str(SCRIPTS / "collect-inventory.py"),
                                     "--context", "sandbox-a", "--input", str(source), "--output", str(output)],
                                    env={**os.environ, "PATH": str(root), "PYTHONDONTWRITEBYTECODE": "1"},
                                    text=True, capture_output=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertFalse(marker.exists())
            self.assertEqual(load(output)["collected_at"], load(source)["collected_at"])
            wrong = subprocess.run([sys.executable, str(SCRIPTS / "collect-inventory.py"),
                                    "--context", "wrong", "--input", str(source), "--output", str(root / "wrong.json")],
                                   env={**os.environ, "PATH": str(root), "PYTHONDONTWRITEBYTECODE": "1"},
                                   text=True, capture_output=True, timeout=10)
            self.assertNotEqual(wrong.returncode, 0)
            self.assertFalse(marker.exists())

    def test_missing_pod_api_is_unknown_not_complete_zero_demand(self):
        output = inventory.normalize({"version": "v1.35.0", "sources": [{"name": "pods", "status": "unavailable"}]}, "fixture")
        self.assertFalse(output["accounting_complete"])

    def test_projection_excludes_secrets_commands_annotations_and_host_path(self):
        raw = {
            "metadata": {"name": "safe-name", "namespace": "team", "annotations": {"private": "annotation-secret"}},
            "spec": {
                "containers": [{"name": "app", "command": ["private-command"], "env": [{"name": "TOKEN", "value": "env-secret"}]}],
                "volumes": [{"name": "local", "hostPath": {"path": "/private/host/path", "type": "Directory"}}],
            },
        }
        projected = inventory.project(raw, inventory.POD)
        serialized = json.dumps(projected)
        for forbidden in ("annotations", "command", "env", "annotation-secret", "env-secret", "private-command", "/private/host/path"):
            self.assertNotIn(forbidden, serialized)
        self.assertEqual(projected["spec"]["volumes"][0]["hostPath"], {"type": "Directory"})

    def test_completed_pending_and_scope_are_classified_without_counting_completed(self):
        raw = {
            "version": "v1.35.0",
            "nodes": [],
            "pods": [
                {"metadata": {"name": "scheduled", "namespace": "target"}, "spec": {"nodeName": "node-a", "containers": [{"name": "app", "resources": {"requests": {"cpu": "250m"}}}]}, "status": {"phase": "Running"}},
                {"metadata": {"name": "pending", "namespace": "target"}, "spec": {"containers": [{"name": "app", "resources": {"requests": {"cpu": "500m"}}}]}, "status": {"phase": "Pending"}},
                {"metadata": {"name": "done", "namespace": "target"}, "spec": {"containers": [{"name": "app", "resources": {"requests": {"cpu": "9"}}}]}, "status": {"phase": "Succeeded"}},
                {"metadata": {"name": "other-scope", "namespace": "elsewhere"}, "spec": {"containers": [{"name": "app", "resources": {"requests": {"cpu": "7"}}}]}, "status": {"phase": "Running"}},
            ],
        }
        output = inventory.normalize(raw, "sandbox", "target")
        self.assertEqual([item["metadata"]["name"] for item in output["pods"]], ["scheduled", "pending", "done"])
        self.assertEqual(output["scheduled_requests"], {"cpu": 250})
        self.assertEqual(output["pending_requests"], {"cpu": 500})
        self.assertEqual([item["demand_class"] for item in output["pods"]], ["scheduled", "pending", "completed"])


class CostCalculatorTests(unittest.TestCase):
    def test_decimal_scenarios_preserve_fixed_commitment_and_do_not_aggregate_alternatives(self):
        result = calculator.calculate({
            "currency": "USD", "basis": "marginal", "period": "month",
            "rate_source": "fixture", "rate_date": "2026-10-01",
            "scenarios": [
                {"id": "partial", "action_ids": ["resize"],
                 "baseline": [{"id": "nodes", "kind": "hourly", "quantity": "3", "rate": "0.1", "hours": "730"}, {"id": "commitment", "kind": "fixed", "amount": "81"}],
                 "proposed": [{"id": "nodes", "kind": "hourly", "quantity": "2", "rate": "0.1", "hours": "730"}, {"id": "commitment", "kind": "fixed", "amount": "81"}]},
                {"id": "alternative", "action_ids": ["remove"],
                 "baseline": [{"id": "commitment", "kind": "fixed", "amount": "81"}],
                 "proposed": [{"id": "commitment", "kind": "fixed", "amount": "81"}]},
            ],
        })
        self.assertEqual(result["scenarios"][0]["baseline"], 300.0)
        self.assertEqual(result["scenarios"][0]["proposed"], 227.0)
        self.assertEqual(result["scenarios"][0]["saving_exact"], "73.0")
        self.assertEqual(result["scenarios"][1]["saving_exact"], "0")
        self.assertEqual(len(result["scenarios"]), 2)
        self.assertNotIn("total_saving", result)
        self.assertNotIn("combined_saving", result)

    def test_fixture_calculation_targets_and_evidence_gaps(self):
        sidecar = EVALS / "fixtures" / "sidecar-fragmentation"
        sidecar_costs = calculator.calculate(load(sidecar / "costs.json"))["scenarios"]
        self.assertEqual([(s["baseline"], s["proposed"], s["saving"]) for s in sidecar_costs],
                         [(730.0, 730.0, 0.0), (730.0, 547.5, 182.5)])
        sidecar_evidence = load(sidecar / "evidence.json")
        self.assertEqual(sidecar_evidence["historical_demand"]["status"], "unavailable")
        self.assertEqual(sidecar_evidence["placement"]["verification"], "not supplied")
        inventory_raw = load(sidecar / "inventory.json")
        normalized = inventory.normalize(inventory_raw, inventory_raw["context"])
        self.assertEqual(normalized["scheduled_requests"], {"cpu": 8200, "memory": 23 * 1024**3 // 2})

        billing = EVALS / "fixtures" / "billing-mix"
        billing_costs = calculator.calculate(load(billing / "costs.json"))["scenarios"]
        self.assertEqual((billing_costs[0]["baseline"], billing_costs[0]["proposed"], billing_costs[0]["saving"]),
                         (1693.48, 1483.24, 210.24))
        self.assertEqual((billing_costs[1]["baseline"], billing_costs[1]["proposed"], billing_costs[1]["saving"]),
                         (1273.0, 1273.0, 0.0))
        billing_evidence = load(billing / "evidence.json")
        self.assertEqual(billing_evidence["metrics"]["status"], "stale_and_incomplete")
        self.assertFalse(billing_evidence["hardware"]["cancelable"])

    def test_malformed_json_nonfinite_and_invalid_cost_inputs_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.json"
            path.write_text('{"value": NaN}')
            with self.assertRaises(ValueError):
                load(path)
            for invalid_json in ('{"value":1e999}', '{"value":1,"value":2}'):
                path.write_text(invalid_json)
                with self.assertRaises(ValueError):
                    load(path)
            path.write_text("{")
            with self.assertRaises(json.JSONDecodeError):
                load(path)
        with self.assertRaises(ValueError):
            quantity("2XB", "memory")
        invalid = {"currency": "USD", "basis": "marginal", "period": "month", "rate_source": "fixture", "rate_date": "2026-10-01", "scenarios": [{"id": "bad", "baseline": [{"id": "x", "kind": "fixed", "amount": "-1"}], "proposed": []}]}
        with self.assertRaises(ValueError):
            calculator.calculate(invalid)
        missing = {"basis": "marginal", "period": "month", "rate_source": "fixture", "rate_date": "2026-10-01", "scenarios": []}
        with self.assertRaises(ValueError):
            calculator.calculate(missing)


if __name__ == "__main__":
    unittest.main()
