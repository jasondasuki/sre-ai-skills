#!/usr/bin/env python3
"""Deterministic helpers for the jira-space-keeper skill.

Usage:
  space_keeper.py fingerprint [--prefix rec-] < batch.json
  space_keeper.py scan < batch.json

batch.json is the record batch from references/records.md, as JSON:
  {"source": "...", "records": [{"kind": "...", "title": "...", ...}, ...]}

Both commands print JSON to stdout. Python 3 standard library only, so every
colleague's machine computes the same fingerprint for the same record.
"""
import argparse
import hashlib
import json
import re
import sys
import unicodedata

FINGERPRINT_VERSION = "v1"
FINGERPRINT_HEX = 12


def normalize(value):
    """Lowercase, NFKC-normalize, replace punctuation with spaces, collapse whitespace."""
    text = unicodedata.normalize("NFKC", str(value or "")).lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return " ".join(text.split())


def fingerprint(source, record, prefix):
    src = normalize(source)
    stable_id = normalize(record.get("stable_id"))
    if stable_id:
        key = f"{FINGERPRINT_VERSION}|{src}|id:{stable_id}"
        basis = "stable_id"
    else:
        title = normalize(record.get("title"))
        if not title:
            return None, "missing title and stable_id"
        resource = normalize(record.get("resource"))
        key = f"{FINGERPRINT_VERSION}|{src}|t:{title}|r:{resource}"
        basis = "title+resource"
    digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:FINGERPRINT_HEX]
    return prefix + digest, basis


# Patterns are deliberately broad: a false positive costs one look in the
# preview, a miss costs a leaked credential or customer record.
SECRET_PATTERNS = [
    ("aws-access-key-id", re.compile(r"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})")),
    ("slack-token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("api-key-prefixed", re.compile(r"\b(?:sk|pk|rk)[-_](?:live|test|proj)?[-_]?[A-Za-z0-9_-]{20,}")),
    ("google-api-key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}")),
    ("private-key-block", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}")),
    ("bearer-token", re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/-]{16,}=*")),
    ("credential-in-url", re.compile(r"\b[a-z][a-z0-9+.-]*://[^/\s:@]+:[^/\s@]+@")),
    ("secret-assignment", re.compile(
        r"(?i)\b(?:password|passwd|pwd|secret|token|api[_-]?key|access[_-]?key|client[_-]?secret)"
        r"\b\s*[:=]\s*['\"]?[^\s'\",;]{4,}")),
]
PII_PATTERNS = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"(?<![\w+])\+\d{1,3}[\s.-]?\(?\d{1,4}\)?(?:[\s.-]?\d{2,4}){2,4}(?!\w)")),
]
CARD_CANDIDATE = re.compile(r"(?<!\d)(?:\d[ -]?){12,18}\d(?!\d)")


def luhn_ok(digits):
    total = 0
    for i, ch in enumerate(reversed(digits)):
        n = int(ch)
        if i % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def mask(text, pattern):
    """Keep just enough to locate the value; never enough to reuse it."""
    if pattern == "email":
        local, _, domain = text.partition("@")
        return f"{local[:1]}***@{domain}"
    if pattern == "credential-in-url":
        return text.split("://", 1)[0] + "://****:****@"
    return f"{text[:4]}****({len(text)} chars)"


def walk(value, path):
    """Yield (field_path, string) for every string inside a record."""
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, list):
        for i, item in enumerate(value):
            yield from walk(item, f"{path}[{i}]")
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from walk(item, f"{path}.{key}" if path else key)


def scan_text(text):
    hits, secret_spans = [], []
    for name, pattern in SECRET_PATTERNS:
        for m in pattern.finditer(text):
            secret_spans.append(m.span())
            hits.append({"type": "secret", "pattern": name, "masked": mask(m.group(0), name)})

    def inside_secret(span):
        # A PII-shaped match inside a secret (user@host in a credential URL) is
        # the same leak; reporting it again would only expose more of the value.
        return any(start < span[1] and span[0] < end for start, end in secret_spans)

    for name, pattern in PII_PATTERNS:
        for m in pattern.finditer(text):
            if not inside_secret(m.span()):
                hits.append({"type": "pii", "pattern": name, "masked": mask(m.group(0), name)})
    for m in CARD_CANDIDATE.finditer(text):
        digits = re.sub(r"\D", "", m.group(0))
        if 13 <= len(digits) <= 19 and luhn_ok(digits) and not inside_secret(m.span()):
            hits.append({"type": "pii", "pattern": "payment-card", "masked": mask(digits, "payment-card")})
    return hits


def load_batch():
    try:
        data = json.load(sys.stdin)
    except json.JSONDecodeError as exc:
        sys.exit(f"error: stdin is not valid JSON: {exc}")
    if isinstance(data, list):
        data = {"records": data}
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        sys.exit('error: expected {"source": ..., "records": [...]}')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    fp = sub.add_parser("fingerprint", help="print the fingerprint label for each record")
    fp.add_argument("--prefix", default="rec-", help="the profile's labels.fingerprint_prefix")
    sub.add_parser("scan", help="report secret- and PII-shaped strings, masked")
    args = parser.parse_args()

    batch = load_batch()
    out = []
    if args.command == "fingerprint":
        source = batch.get("source") or ""
        if not normalize(source):
            sys.exit("error: batch has no source; fingerprints would not be stable")
        for i, record in enumerate(batch["records"]):
            label, basis = fingerprint(source, record, args.prefix)
            entry = {"index": i, "title": record.get("title"), "fingerprint": label, "basis": basis}
            if label is None:
                entry = {"index": i, "error": basis}
            out.append(entry)
    else:
        for i, record in enumerate(batch["records"]):
            for path, text in walk(record, ""):
                for hit in scan_text(text):
                    out.append({"index": i, "field": path, **hit})
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
