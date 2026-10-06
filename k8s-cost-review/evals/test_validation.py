"""Evidence contract regression checks with intentionally inconsistent artifacts."""

import copy
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

CORE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CORE / "scripts"))
spec = importlib.util.spec_from_file_location("validator", CORE / "scripts" / "validate-evidence.py")
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)


def evidence():
    return {
        "schema_version": 1,
        "scope": {"contexts": ["fixture"], "namespaces": [], "mode": "supplied"},
        "collected_at": "2026-10-01T00:00:00Z", "review_started_at": "2026-10-02T00:00:00Z",
        "outputs": {"markdown": "report.md", "html": "report.html", "evidence": "evidence.json"},
        "report_checks": {"markup": None, "visual": None, "limitations": []},
        "window": {"start": None, "end": None, "coverage_notes": ["fixture snapshot only"]},
        "pricing": {"currency": "USD", "basis": "marginal", "rate_source": "fixture", "rate_date": "2026-10-01", "period": "monthly"},
        "sources": [{"name": "fixture", "status": "available", "reason": None}],
        "observations": [{"id": "E1", "resource": "pool", "source": "fixture", "query_or_reference": "fixture.json",
                          "timestamp": "2026-10-01T00:00:00Z", "aggregation": "snapshot", "value": 4, "unit": "nodes", "limitations": []}],
        "findings": [{"id": "F1", "readiness": "conditional", "target": "pool", "action": "consolidate",
                      "evidence_ids": ["E1"], "dependencies": [], "overlap_group": None,
                      "saving": {"low": 0, "high": 73, "currency": "USD", "period": "monthly", "basis": "marginal",
                                 "formula": "one node x 0.1 x 730", "assumptions": ["placement verification needed"]},
                      "capacity_benefit": None, "confidence": "medium"}],
        "scenarios": [{"id": "S1", "action_ids": ["F1"], "baseline": 292, "proposed": 219, "saving": 73,
                       "baseline_components": [{"id": "pool", "kind": "hourly", "quantity": 4, "rate": "0.1", "hours": 730}],
                       "proposed_components": [{"id": "pool", "kind": "hourly", "quantity": 3, "rate": "0.1", "hours": 730}],
                       "assumptions": ["placement not verified"]}], "gaps": ["placement"]
    }


class EvidenceValidationTests(unittest.TestCase):
    def test_valid_evidence_and_schema(self):
        data = evidence()
        schema = json.loads((CORE / "references" / "evidence.schema.json").read_text())
        self.assertEqual(validator.validate_schema(data, schema), [])
        self.assertEqual(validator.semantic_checks(data), [])

    def test_schema_rejects_boolean_cost_and_missing_provenance(self):
        data = evidence()
        schema = json.loads((CORE / "references" / "evidence.schema.json").read_text())
        data["scenarios"][0]["baseline"] = True
        del data["scope"]["contexts"]
        self.assertTrue(validator.validate_schema(data, schema))
        self.assertTrue(validator.validate_schema({}, {"type": "object", "anyOf": []}))

    def test_references_units_pricing_and_arithmetic_corruption(self):
        mutations = [
            lambda d: d["findings"][0]["evidence_ids"].append("missing"),
            lambda d: d["findings"][0]["dependencies"].append("F1"),
            lambda d: d["observations"][0].update(unit=None),
            lambda d: d["sources"][0].update(status="unavailable", reason="Forbidden"),
            lambda d: d["pricing"].update(rate_date=None),
            lambda d: d["scenarios"][0].update(saving=74),
            lambda d: d["findings"][0]["saving"].update(high=72),
            lambda d: d["window"].update(start="2026-10-02T00:00:00Z", end="2026-10-01T00:00:00Z"),
            lambda d: d["observations"][0].update(timestamp="2026-10-01"),
        ]
        for mutate in mutations:
            data = evidence()
            mutate(data)
            with self.subTest(mutation=mutate):
                self.assertTrue(validator.semantic_checks(data))

    def test_contract_detects_drift_and_missing_data_blocks(self):
        data = evidence()
        expected = validator.facts(data)
        serialized = json.dumps(expected)
        with tempfile.TemporaryDirectory() as directory:
            md, page = Path(directory) / "report.md", Path(directory) / "report.html"
            md.write_text("# Report\n<!-- cost-review-facts -->\n```json\n" + serialized + "\n```\n")
            page.write_text('<script type="application/json" id="cost-review-facts">' + serialized + '</script>')
            self.assertEqual(validator.report_checks(md, "markdown", expected), [])
            self.assertEqual(validator.report_checks(page, "html", expected), [])
            changed = copy.deepcopy(expected)
            changed["scenarios"][0]["saving"] = 100
            page.write_text('<script type="application/json" id="cost-review-facts">' + json.dumps(changed) + '</script>')
            self.assertTrue(validator.report_checks(page, "html", expected))
            page.write_text('<script type="application/json" id="cost-review-facts">' + serialized + '</script><script>alert(1)</script>')
            self.assertTrue(validator.report_checks(page, "html", expected))
            md.write_text("# Report with no data block")
            self.assertTrue(validator.report_checks(md, "markdown", expected))

    def test_rounding_occurs_after_container_aggregation(self):
        from costlib import effective_requests
        pod = {"spec": {"containers": [{"resources": {"requests": {"cpu": "0.0004"}}},
                                      {"resources": {"requests": {"cpu": "0.0004"}}}]}}
        self.assertEqual(effective_requests(pod, "v1.35.0"), ({"cpu": 1}, []))


if __name__ == "__main__":
    unittest.main()
