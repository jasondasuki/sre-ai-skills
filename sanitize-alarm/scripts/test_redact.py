#!/usr/bin/env python3
"""Self-test for redact.py. Run: python3 -I test_redact.py

Fake credentials are built from fragments at run time so this file never holds
a credential-shaped literal.
"""
import importlib.util
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("redact", os.path.join(HERE, "redact.py"))
redact = importlib.util.module_from_spec(spec)
spec.loader.exec_module(redact)

AWS_KEY = "AK" + "IA" + "ABCDEFGHIJKLMNOP"
GH_TOKEN = "gh" + "p_" + "a1B2c3D4e5F6g7H8i9J0k1L2"
JWT = "ey" + "JhbGciOiJIUzI1NiJ9" + "." + "ey" + "JzdWIiOiIxMjM0NTY3ODkwIn0" + "." + "abcDEF123456"
PEM = "-----" + "BEGIN RSA PRIVATE KEY-----\nMIIabc\n-----" + "END RSA PRIVATE KEY-----"


def run(text, level="outside", deny=(), always=(), keep=()):
    return redact.Redactor(level, deny, keep, always).redact(text)


class SecretTests(unittest.TestCase):
    def test_provider_tokens_and_jwt(self):
        out = run("k=%s t=%s j=%s" % (AWS_KEY, GH_TOKEN, JWT), "team")
        for raw in (AWS_KEY, GH_TOKEN, JWT):
            self.assertNotIn(raw, out)
        self.assertEqual(out.count("[REDACTED:SECRET]"), 3)

    def test_private_key_block(self):
        out = run("before\n%s\nafter" % PEM, "team")
        self.assertNotIn("MIIabc", out)
        self.assertIn("before", out)
        self.assertIn("after", out)

    def test_authorization_and_bearer(self):
        out = run("Authorization: Bearer abcdef1234567890xyz\nuse bearer zyxwvu98765432", "team")
        self.assertNotIn("abcdef1234567890xyz", out)
        self.assertNotIn("zyxwvu98765432", out)

    def test_key_value_and_json(self):
        out = run('db_password=hunter22x api_key: "sk_value_12345" {"client_secret": "abc123def"}', "team")
        for raw in ("hunter22x", "sk_value_12345", "abc123def"):
            self.assertNotIn(raw, out)

    def test_benign_values_survive(self):
        out = run("token_count=5 auth: failed secret=true", "team")
        self.assertEqual(out, "token_count=5 auth: failed secret=true")

    def test_url_userinfo_and_query(self):
        out = run("postgres://app:s3cretpw@db:5432/x https://x.example/y?sig=abcdef123456&a=1", "team")
        self.assertNotIn("s3cretpw", out)
        self.assertNotIn("abcdef123456", out)
        self.assertIn("a=1", out)

    def test_userinfo_without_password_is_kept(self):
        self.assertEqual(run("ssh://git@host/repo", "team"), "ssh://git@host/repo")


class PersonalDataTests(unittest.TestCase):
    def test_email_consistent_numbering(self):
        out = run("a@x.test b@x.test a@x.test", "team")
        self.assertEqual(out, "[EMAIL-1] [EMAIL-2] [EMAIL-1]")

    def test_phone(self):
        self.assertNotIn("8123456789", run("call +62 812 3456 789 now", "team"))


class InPlaceTests(unittest.TestCase):
    def test_email_notification_handle_kept_but_plain_email_removed(self):
        text = "page @alice.smith@corp.internal or write bob@corp.internal"
        out = redact.Redactor("team", in_place=True).redact(text)
        self.assertIn("@alice.smith@corp.internal", out)
        self.assertNotIn("bob@corp.internal", out)

    def test_unnamed_long_token_is_flagged_not_replaced(self):
        tok = "Xy9" * 15
        r = redact.Redactor("team", in_place=True)
        self.assertEqual(r.redact("see " + tok), "see " + tok)
        self.assertEqual(r.possible, 1)


class LevelTests(unittest.TestCase):
    TEXT = ("host db-1.corp.internal at 10.1.2.3 and 2001:db8::1 mac aa:bb:cc:dd:ee:ff "
            "acct 123456789012 see https://app.datadoghq.com/monitors/1?from=2 @slack-ops-team")

    def test_team_keeps_addresses(self):
        out = run(self.TEXT, "team")
        for kept in ("db-1.corp.internal", "10.1.2.3", "123456789012", "@slack-ops-team"):
            self.assertIn(kept, out)

    def test_outside_removes_addresses(self):
        out = run(self.TEXT, "outside")
        for gone in ("db-1.corp.internal", "10.1.2.3", "2001:db8::1", "aa:bb:cc:dd:ee:ff",
                     "123456789012", "from=2", "@slack-ops-team"):
            self.assertNotIn(gone, out)
        self.assertIn("app.datadoghq.com/monitors/1", out)

    def test_ip_numbering_consistent(self):
        out = run("10.0.0.1 10.0.0.2 10.0.0.1", "outside")
        self.assertEqual(out, "[IP-1] [IP-2] [IP-1]")

    def test_identifying_tags(self):
        out = run("pod_name:api-7f9c5-xk2lp kube_namespace:payments env:prod", "outside")
        self.assertNotIn("api-7f9c5-xk2lp", out)
        self.assertNotIn("payments", out)
        self.assertIn("env:prod", out)

    def test_denylist_matches_subdomains_and_not_lookalikes(self):
        out = run("x.stg.corp.test and corp.test but not corp.testing", "outside", deny=["corp.test"])
        self.assertNotIn("x.stg.corp.test", out)
        self.assertIn("corp.testing", out)

    def test_denylist_regex_and_always(self):
        out = run("proj-dev-api and Acme", "team", always=["Acme"])
        self.assertNotIn("Acme", out)
        out = run("proj-dev-api", "outside", deny=["re:proj-[a-z]+-[a-z]+"])
        self.assertNotIn("proj-dev-api", out)

    def test_denylist_ignored_at_team_level(self):
        self.assertEqual(run("corp.test", "team", deny=["corp.test"]), "corp.test")


class StabilityTests(unittest.TestCase):
    def test_second_pass_changes_nothing(self):
        text = ("pw=hunter22x a@x.test 10.0.0.1 db.corp.test pod_name:p1 "
                "Authorization: Bearer abcdef1234567890xyz %s "
                "postgres://svc:Sup3rS3cretPw@db.corp.internal:5432/app https://x.corp.internal/p?token=abcd1234efgh&a=1"
                % AWS_KEY)
        first = run(text)
        self.assertEqual(run(first), first)

    def test_check_mode_exit_codes(self):
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write("contact a@x.test")
            dirty = fh.name
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write("nothing to see here")
            clean = fh.name
        try:
            self.assertEqual(redact.main(["--check", "--level", "team", dirty]), 3)
            self.assertEqual(redact.main(["--check", "--level", "team", clean]), 0)
        finally:
            os.unlink(dirty)
            os.unlink(clean)

    def test_plain_alarm_text_is_untouched(self):
        text = "[Triggered] CPU high on env:prod service:checkout value 93.5 threshold 90"
        self.assertEqual(run(text), text)


if __name__ == "__main__":
    sys.exit(unittest.main(verbosity=1))
