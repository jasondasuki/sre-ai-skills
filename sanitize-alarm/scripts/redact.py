#!/usr/bin/env python3
"""Deterministic first pass of alarm sanitising.

Reads text from files or stdin, writes the redacted text to stdout, and writes a
count per category (never a value) to stderr with --report. It is a floor, not a
ceiling: free text such as customer names still needs a reading pass.

Levels
  team     credentials and personal data only (safe to share inside the org)
  outside  everything in team, plus addresses, hostnames, account numbers,
           notification handles, identifying tag values and URL query strings

Placeholders are typed, and the same value always gets the same number inside
one run ([IP-1] stays [IP-1]), so a reader can still follow a thread. The
mapping lives in memory only and is never written anywhere.

Exit status: 0 normally; with --check, 3 when anything would be redacted.
Run it as: python3 -I redact.py [options] [file ...]
"""
import argparse
import collections
import json
import re
import sys

LEVELS = ("team", "outside")

# Domains that identify a vendor, not the organisation, so they stay readable.
DEFAULT_KEEP = ("datadoghq.com", "datadoghq.eu", "ddog-gov.com", "kubernetes.io", "k8s.io")

# Tag and field keys whose values identify the estate.
IDENT_KEYS = (
    "host|hostname|pod_name|pod|node|kube_node|kube_namespace|namespace|kube_cluster_name|"
    "cluster|cluster_name|container_name|container_id|account|account_id|project|project_id|"
    "instance|instance_id|image_name|user|customer|tenant|org|org_id|region_zone"
)

# Words that follow a secret-looking key but are not secrets.
BENIGN_VALUES = {
    "true", "false", "null", "none", "undefined", "enabled", "disabled", "failed",
    "failure", "success", "error", "invalid", "expired", "missing", "denied",
    "required", "unknown", "default", "empty",
}

SECRET_KEY = (
    r"[A-Za-z0-9_.-]*(?:password|passwd|pwd|secret|token|api[_-]?key|apikey|credential|"
    r"private[_-]?key|access[_-]?key|session[_-]?id|cookie|routing[_-]?key|"
    r"integration[_-]?key|signing[_-]?key|client[_-]?secret|dsn|webhook[_-]?url)[A-Za-z0-9_.-]*"
)

# Built from fragments so this file never holds a credential-shaped literal.
PEM_BEGIN = "-----" + "BEGIN"
PEM_END = "-----" + "END"

TLDS = (
    "com|net|org|io|ai|dev|app|cloud|internal|local|link|edu|gov|info|biz|xyz|tech|us|uk|eu|sg"
)


class Redactor:
    def __init__(self, level, denylist_terms=(), keep=(), always_terms=(), in_place=False):
        # in_place: the text is a live monitor's own text, so it must keep working.
        # Notification handles stay (they route pages), and unnamed long tokens are
        # flagged for review instead of replaced, since a link or query could break.
        self.in_place = in_place
        self.level = level
        self.outside = level == "outside"
        self.keep = tuple(k.lower() for k in tuple(DEFAULT_KEEP) + tuple(keep))
        self.counts = collections.Counter()
        self.seen = collections.defaultdict(dict)
        self.possible = 0
        self.deny = [self._compile_term(t) for t in denylist_terms]
        self.always = [self._compile_term(t) for t in always_terms]

    # -- helpers -----------------------------------------------------------
    @staticmethod
    def _compile_term(term):
        if term.startswith("re:"):
            return re.compile(term[3:], re.IGNORECASE), None
        label = "HOST" if "." in term else ("ID" if term.isdigit() else "ORG")
        pat = r"(?<![A-Za-z0-9_-])(?:[A-Za-z0-9_-]+\.)*" + re.escape(term) + r"(?![A-Za-z0-9_-])"
        return re.compile(pat, re.IGNORECASE), label

    def _num(self, cat, value):
        table = self.seen[cat]
        key = value.lower()
        if key not in table:
            table[key] = len(table) + 1
        self.counts[cat] += 1
        return "[%s-%d]" % (cat, table[key])

    def _flat(self, cat):
        self.counts[cat] += 1
        return "[REDACTED:%s]" % cat

    def _kept(self, host):
        h = host.lower()
        return any(h == k or h.endswith("." + k) for k in self.keep)

    # -- passes ------------------------------------------------------------
    def _apply_terms(self, text, compiled):
        for rx, label in compiled:
            text = rx.sub(lambda m, l=label: self._num(l or "ORG", m.group(0)), text)
        return text

    def redact(self, text):
        text = self._apply_terms(text, self.always)

        # Private key blocks span lines, so they go first.
        text = re.sub(
            re.escape(PEM_BEGIN) + r" [A-Z ]*PRIVATE KEY" + re.escape("-----") + r".*?"
            + re.escape(PEM_END) + r" [A-Z ]*PRIVATE KEY" + re.escape("-----"),
            lambda m: self._flat("SECRET"), text, flags=re.DOTALL)

        provider = [
            r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{5,}",
            r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b",
            r"\bAIza[0-9A-Za-z_-]{30,}",
            r"\bya29\.[0-9A-Za-z_-]{20,}",
            r"\bgh[pousr]_[A-Za-z0-9]{20,}",
            r"\bgithub_pat_[A-Za-z0-9_]{20,}",
            r"\bglpat-[A-Za-z0-9_-]{16,}",
            r"\bxox[abprs]-[A-Za-z0-9-]{10,}",
            r"\b[sr]k_(?:live|test)_[A-Za-z0-9]{16,}",
            r"\bSG\.[A-Za-z0-9_-]{16,}\.[A-Za-z0-9_-]{16,}",
            r"\bsk-[A-Za-z0-9_-]{20,}",
            r"https://hooks\.slack\.com/services/[A-Za-z0-9/]+",
        ]
        for rx in provider:
            text = re.sub(rx, lambda m: self._flat("SECRET"), text)

        text = re.sub(
            r"(?i)\b((?:proxy-)?authorization)([\"']?\s*[:=]\s*[\"']?)([^\r\n\"']+)",
            lambda m: m.group(1) + m.group(2) + self._flat("SECRET"), text)
        text = re.sub(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}",
                      lambda m: m.group(1) + " " + self._flat("SECRET"), text)

        def userinfo(m):
            user, pwd = m.group(2), m.group(3)
            if user.startswith("["):
                return m.group(0)
            if pwd or len(user) >= 16:
                return m.group(1) + self._flat("CREDENTIAL") + "@"
            return m.group(0)
        text = re.sub(r"(?i)\b([a-z][a-z0-9+.-]*://)([^/\s:@]+)(?::([^/\s@]*))?@", userinfo, text)

        def keyval(m):
            value = m.group("v")
            if value.startswith("[") or len(value) < 6 or value.lower() in BENIGN_VALUES:
                return m.group(0)
            return m.group("k") + m.group("sep") + self._flat("SECRET")
        text = re.sub(
            r"(?P<k>\b" + SECRET_KEY + r")(?P<sep>[\"']?\s*[:=]\s*[\"']?)(?P<v>[^\s\"',;&}\]]+)",
            keyval, text, flags=re.IGNORECASE)
        text = re.sub(
            r"(?i)([?&](?:key|sig|signature|code|auth|sas|x-amz-signature|x-goog-signature)=)"
            r"([^&\s#\"']+)",
            lambda m: m.group(1) + self._flat("SECRET")
            if not m.group(2).startswith("[") else m.group(0), text)

        # Long mixed-case tokens that no rule named. Flagged, not trusted.
        def possible(m):
            tok = m.group(0)
            if (re.search(r"[A-Z]", tok) and re.search(r"[a-z]", tok) and re.search(r"\d", tok)
                    and not re.fullmatch(r"[0-9a-fA-F]+", tok)):
                self.possible += 1
                if self.in_place:
                    return tok
                return self._flat("SECRET")
            return tok
        text = re.sub(r"(?<![A-Za-z0-9+/_=-])[A-Za-z0-9+/_=-]{40,}(?![A-Za-z0-9+/_=-])", possible, text)

        lead = r"(?<![@A-Za-z0-9._%+-])" if self.in_place else ""
        text = re.sub(lead + r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+",
                      lambda m: self._num("EMAIL", m.group(0)), text)
        text = re.sub(r"(?<![\w.])\+\d[\d\s().-]{7,}\d(?!\w)", lambda m: self._flat("PHONE"), text)

        if not self.outside:
            return text

        # -- outside level --------------------------------------------------
        text = self._apply_terms(text, self.deny)
        text = re.sub(r"(?<![\w.])@(?:slack|pagerduty|opsgenie|webhook|teams|jira|servicenow)[-\w.]*",
                      lambda m: self._num("HANDLE", m.group(0)), text, flags=re.IGNORECASE)
        text = re.sub(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}[0-9A-Fa-f]{2}\b",
                      lambda m: self._num("MAC", m.group(0)), text)
        octet = r"(?:25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)"
        text = re.sub(r"(?<![\w.])" + octet + r"(?:\." + octet + r"){3}(?![\w]|\.\d)",
                      lambda m: self._num("IP", m.group(0)), text)
        h = r"[0-9A-Fa-f]{1,4}"
        v6 = (r"(?<![\w:])(?:(?:%(h)s:){7}%(h)s|(?:%(h)s:){1,7}:(?:%(h)s(?::%(h)s){0,6})?"
              r"|::(?:%(h)s:){0,6}%(h)s)(?![\w:])") % {"h": h}
        text = re.sub(v6, lambda m: self._num("IP", m.group(0)), text)

        def host(m):
            return m.group(0) if self._kept(m.group(0)) else self._num("HOST", m.group(0))
        text = re.sub(r"\b(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+(?:%s)\b" % TLDS,
                      host, text, flags=re.IGNORECASE)
        text = re.sub(r"(?<![\w.])\d{12}(?![\w.])", lambda m: self._num("ACCOUNT", m.group(0)), text)

        def tag(m):
            value = m.group("v")
            if value.startswith("["):
                return m.group(0)
            return m.group("k") + m.group("sep") + self._num("TAG", value)
        text = re.sub(r"(?P<k>\b(?:%s))(?P<sep>\s*:\s*)(?P<v>[^\s,\]\"')}]+)" % IDENT_KEYS,
                      tag, text, flags=re.IGNORECASE)

        text = re.sub(r"(https?://[^\s?#\"'<>)]+)\?(?!\[REDACTED:QUERY\])[^\s#\"'<>)]+",
                      lambda m: m.group(1) + "?" + self._flat("QUERY"), text)
        return text


def load_denylist(path):
    deny, always, keep = [], [], []
    if not path:
        return deny, always, keep
    with open(path, encoding="utf-8") as fh:
        for raw in fh:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("keep:"):
                keep.append(line[5:].strip())
            elif line.startswith("!"):
                always.append(line[1:].strip())
            else:
                deny.append(line)
    return deny, always, keep


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("files", nargs="*", help="input files; stdin when omitted")
    ap.add_argument("--level", choices=LEVELS, default="outside")
    ap.add_argument("--denylist", help="file of terms for the outside level (see the redaction guide)")
    ap.add_argument("--report", action="store_true", help="print category counts to stderr")
    ap.add_argument("--check", action="store_true",
                    help="write nothing to stdout; exit 3 if anything would be redacted")
    args = ap.parse_args(argv)

    deny, always, keep = load_denylist(args.denylist)
    red = Redactor(args.level, deny, keep, always)

    if args.files:
        chunks = []
        for name in args.files:
            with open(name, encoding="utf-8", errors="replace") as fh:
                chunks.append(fh.read())
        text = "\n".join(chunks)
    else:
        text = sys.stdin.read()

    out = red.redact(text)

    if not args.check:
        sys.stdout.write(out)
    if args.report or args.check:
        summary = dict(sorted(red.counts.items()))
        summary["possible_unnamed_secret"] = red.possible
        sys.stderr.write(json.dumps({"level": args.level, "redactions": summary}) + "\n")
    if args.check and sum(red.counts.values()) > 0:
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
