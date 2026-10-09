#!/usr/bin/env python3
"""Self-test for alarmctl.py against a local stub API. Run: python3 -I test_alarmctl.py

No real service is contacted. Fake credentials are built from fragments.
"""
import contextlib
import copy
import importlib.util
import io
import json
import os
import re
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("alarmctl", os.path.join(HERE, "alarmctl.py"))
ctl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ctl)

GH = "gh" + "p_" + "a1B2c3D4e5F6g7H8i9J0k1L2"
SEED = {
    1: {"id": 1, "name": "High 5xx", "tags": ["team:core", "env:prod"], "query": "avg(last_5m):x > 5",
        "message": "Paged @alice@corp.internal. token=" + GH + " mail bob@corp.internal",
        "options": {"thresholds": {"critical": 5}, "renotify_interval": 10, "escalation_message": "ok"}},
    2: {"id": 2, "name": "Clean one", "tags": ["team:core"], "query": "q", "message": "nothing here",
        "options": {"thresholds": {"critical": 1}}},
    3: {"id": 3, "name": "Other team", "tags": ["team:other"], "query": "q",
        "message": "secret=hunter22x", "options": {}},
}
STATE = {}


class Stub(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, obj):
        raw = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):
        m = re.match(r"/api/v1/monitor/(\d+)$", self.path)
        if m:
            mon = STATE.get(int(m.group(1)))
            return self._send(200, mon) if mon else self._send(404, {})
        if self.path.startswith("/api/v1/monitor?"):
            tags = re.search(r"monitor_tags=([^&]*)", self.path)
            want = tags.group(1).replace("%3A", ":").split("%2C") if tags else []
            out = [m for m in STATE.values() if all(t in m["tags"] for t in want)]
            return self._send(200, out)
        self._send(404, {})

    def do_PUT(self):
        m = re.match(r"/api/v1/monitor/(\d+)$", self.path)
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        STATE[int(m.group(1))].update(body)
        self._send(200, STATE[int(m.group(1))])


def jl(path):
    with open(path) as fh:
        return json.load(fh)


def jd(obj, path):
    with open(path, "w") as fh:
        json.dump(obj, fh)


def rd(path):
    with open(path) as fh:
        return fh.read()


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = ctl.main(argv)
    return code, out.getvalue(), err.getvalue()


class Flow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = HTTPServer(("127.0.0.1", 0), Stub)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = "http://127.0.0.1:%d" % cls.srv.server_port
        os.environ.update(DD_API_KEY="k", DD_APP_KEY="a", DD_SITE="x.test")

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def setUp(self):
        STATE.clear()
        STATE.update(copy.deepcopy(SEED))
        self.tmp = tempfile.mkdtemp()
        self.f = os.path.join(self.tmp, "fetched.json")
        self.c = os.path.join(self.tmp, "changes.json")
        self.base = ["--base-url", self.url, "--sleep", "0"]

    def fetch(self):
        code, out, _ = run(["fetch", "--tag", "team:core", "--out", self.f] + self.base)
        self.assertEqual(code, 0, out)
        return json.loads(out)

    def plan(self):
        code, out, _ = run(["plan-redact", "--fetched", self.f, "--out", self.c])
        self.assertEqual(code, 0)
        return json.loads(out)

    def approve(self, **kw):
        path = os.path.join(self.tmp, "approved.json")
        plan = jl(self.c)
        jd(dict(plan_id=plan["plan_id"], **kw), path)
        return path

    def test_fetch_by_tag_and_private_file(self):
        res = self.fetch()
        self.assertEqual(sorted(res["ids"]), [1, 2])
        self.assertEqual(oct(os.stat(self.f).st_mode & 0o777), "0o600")

    def test_fetch_refuses_unscoped(self):
        code, _, err = run(["fetch", "--out", self.f] + self.base)
        self.assertEqual(code, 2)
        self.assertIn("scope", err)

    def test_plan_keeps_no_secret_and_keeps_handle(self):
        self.fetch()
        self.plan()
        text = rd(self.c)
        self.assertNotIn(GH, text)
        self.assertNotIn("bob@corp.internal", text)
        plan = json.loads(text)
        self.assertEqual({i["monitor_id"] for i in plan["items"]}, {1})
        item = plan["items"][0]
        self.assertIn("@alice@corp.internal", item["proposed"])
        self.assertEqual(len(item["current_sha256"]), 64)

    def test_dry_run_writes_nothing(self):
        self.fetch(); self.plan()
        code, out, _ = run(["apply", "--changes", self.c, "--approved", self.approve(approve_all=True)] + self.base)
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["tally"], {"would_apply": 1})
        self.assertIn(GH, STATE[1]["message"])

    def test_apply_changes_only_approved_and_verifies(self):
        self.fetch(); self.plan()
        code, out, _ = run(["apply", "--apply", "--changes", self.c, "--rollback-dir", self.tmp,
                            "--approved", self.approve(approve_all=True)] + self.base)
        self.assertEqual(code, 0, out)
        self.assertEqual(json.loads(out)["tally"], {"applied": 1})
        self.assertNotIn(GH, STATE[1]["message"])
        self.assertEqual(STATE[3]["message"], SEED[3]["message"])
        self.assertEqual(STATE[1]["options"]["thresholds"], {"critical": 5})
        self.assertEqual(os.listdir(self.tmp).count("rollback-%s.json" % jl(self.c)["plan_id"]), 0)

    def test_exclusion_is_respected(self):
        self.fetch(); self.plan()
        ids = [i["id"] for i in jl(self.c)["items"]]
        code, out, _ = run(["apply", "--apply", "--changes", self.c, "--rollback-dir", self.tmp,
                            "--approved", self.approve(approve_all=True, exclude=ids)] + self.base)
        self.assertEqual(json.loads(out)["tally"], {})
        self.assertIn(GH, STATE[1]["message"])

    def test_drift_is_skipped(self):
        self.fetch(); self.plan()
        STATE[1]["message"] += " edited by a person"
        code, out, _ = run(["apply", "--apply", "--changes", self.c, "--rollback-dir", self.tmp,
                            "--approved", self.approve(approve_all=True)] + self.base)
        self.assertEqual(json.loads(out)["tally"], {"drifted": 1})
        self.assertIn("edited by a person", STATE[1]["message"])

    def test_wrong_plan_id_refused(self):
        self.fetch(); self.plan()
        path = os.path.join(self.tmp, "bad.json")
        jd({"plan_id": "0000", "approve_all": True}, path)
        code, _, err = run(["apply", "--apply", "--changes", self.c, "--approved", path] + self.base)
        self.assertEqual(code, 2)
        self.assertIn("approval is for plan", err)
        self.assertIn(GH, STATE[1]["message"])

    def test_edited_plan_refused(self):
        self.fetch(); self.plan()
        plan = jl(self.c)
        plan["items"][0]["proposed"] = "something else"
        jd(plan, self.c)
        code, _, err = run(["apply", "--changes", self.c, "--approved", self.approve(approve_all=True)] + self.base)
        self.assertEqual(code, 2)
        self.assertIn("edited after", err)

    def test_build_hygiene_with_rollback_and_guards(self):
        self.fetch(); self.plan()
        props = os.path.join(self.tmp, "p.json")
        good = {"monitor_id": 2, "mode": "hygiene", "field": "options.renotify_interval", "proposed": 60,
                "reason": "stops 10-minute repeats", "risk": "low", "approver": "owner", "alerts_removed": 40}
        jd([good], props)
        code, out, _ = run(["build", "--fetched", self.f, "--proposals", props, "--into", self.c])
        self.assertEqual(code, 0, out)
        code, out, _ = run(["apply", "--apply", "--changes", self.c, "--rollback-dir", self.tmp,
                            "--approved", self.approve(approve_all=True)] + self.base)
        self.assertEqual(json.loads(out)["tally"], {"applied": 2})
        self.assertEqual(STATE[2]["options"]["renotify_interval"], 60)
        self.assertEqual(STATE[2]["options"]["thresholds"], {"critical": 1})
        rb = jl(os.path.join(self.tmp, "rollback-%s.json" % jl(self.c)["plan_id"]))
        self.assertEqual(list(rb["previous"]), ["2"])
        for bad, msg in (({"field": "options.silenced"}, "may not be changed"),
                         ({"field": "query"}, "allow_query")):
            jd([dict(good, **bad)], props)
            code, _, err = run(["build", "--fetched", self.f, "--proposals", props, "--into", self.c])
            self.assertEqual(code, 2)
            self.assertIn(msg, err)

    def test_build_filters_credentials_out_of_proposed_text(self):
        self.fetch(); self.plan()
        props = os.path.join(self.tmp, "p.json")
        jd([{"monitor_id": 2, "mode": "normalize", "field": "message", "proposed": "token=" + GH + " ok",
             "reason": "r", "risk": "low", "approver": "o"}], props)
        run(["build", "--fetched", self.f, "--proposals", props, "--into", self.c])
        self.assertNotIn(GH, rd(self.c))

    def test_inspect_flags_without_exposing_text(self):
        self.fetch()
        STATE[2]["options"]["silenced"] = {"*": None}
        self.fetch()
        code, out, _ = run(["inspect", "--fetched", self.f])
        self.assertEqual(code, 0)
        rows = {r["monitor_id"]: r for r in json.loads(out)["monitors"]}
        self.assertIn("muted_with_no_end", rows[2]["flags"])
        self.assertIn("no_link_in_message", rows[2]["flags"])
        self.assertNotIn("nothing here", out)
        self.assertNotIn(GH, out)

    def test_summary_has_no_text(self):
        self.fetch(); self.plan()
        code, out, _ = run(["summary", "--changes", self.c])
        data = json.loads(out)
        self.assertEqual(data["items"], 1)
        self.assertNotIn("proposed", out)


if __name__ == "__main__":
    sys.exit(unittest.main(verbosity=1))
