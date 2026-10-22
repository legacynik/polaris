#!/usr/bin/env python3
"""Redaction scan-at-sink — blocks PR creation on a live-looking secret.

Mechanism, not a reminder: exit 1 (BLOCKED) on any HIGH finding, exit 0 (CLEAN
or WARN) otherwise. Stdlib only, zero deps — must run on Claude Code, Codex,
Hermes, Pi without a package install.

    redact_scan.py --paths f1 f2 ...   scan files
    redact_scan.py --stdin             scan text piped in (e.g. git diff)
    redact_scan.py --selfcheck         prove each branch fails/passes as it must
"""
from __future__ import annotations
import re, sys, json, argparse
from dataclasses import dataclass, asdict

# name -> (compiled regex, severity). Groups: if the pattern has a capture
# group, group(1) is the secret value checked against the placeholder filter;
# otherwise the whole match is checked.
PATTERNS: dict[str, tuple[re.Pattern, str]] = {
    "aws_access_key_id": (re.compile(r"AKIA[0-9A-Z]{16}"), "HIGH"),
    "aws_secret_access_key": (re.compile(r'(?i)aws_secret_access_key\s*[:=]\s*["\']?([A-Za-z0-9/+=]{40})["\']?'), "HIGH"),
    "private_key_block": (re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA |PGP )?PRIVATE KEY-----"), "HIGH"),
    "github_token": (re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"), "HIGH"),
    "slack_token": (re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}"), "HIGH"),
    "stripe_live_key": (re.compile(r"sk_live_[A-Za-z0-9]{20,}"), "HIGH"),
    "openai_key": (re.compile(r"sk-[A-Za-z0-9]{20,}"), "HIGH"),
    "generic_secret_assignment": (
        re.compile(r'(?i)\b[A-Z0-9_]*(?:SECRET|API_KEY|TOKEN|PASSWORD|PASSWD)[A-Z0-9_]*\s*[:=]\s*["\']([^"\'\s]{12,})["\']'),
        "HIGH",
    ),
    # L3 (EVAL-ship-bypass.md): the three patterns above all key off the
    # variable NAME containing SECRET/API_KEY/TOKEN/PASSWORD — a live secret
    # in a connection string, a Bearer/JWT header, or an OAuth token never
    # matched because nothing in the line's *name* looked suspicious.
    "conn_string_creds": (
        re.compile(r'[a-zA-Z][a-zA-Z0-9+.-]*://[^\s/:"\']+:([^\s/@"\']{8,})@'), "HIGH",
    ),
    "bearer_token": (re.compile(r'Bearer\s+([A-Za-z0-9\-_.]{20,})'), "HIGH"),
    "google_oauth_token": (re.compile(r'(ya29\.[A-Za-z0-9_-]{20,})'), "HIGH"),
}

PLACEHOLDER_TOKENS = (
    "changeme", "your_key_here", "your-key-here", "yourkeyhere", "placeholder",
    "example", "insert_key_here", "<key>", "redacted", "todo", "fixme",
    "dummy", "fake", "test123", "xxxxxxxx",
)


def is_placeholder(value: str) -> bool:
    """A value that looks like a template slot, not a live secret."""
    lowered = value.lower()
    if any(tok in lowered for tok in PLACEHOLDER_TOKENS):
        return True
    if len(set(lowered)) <= 4:  # "aaaaaaaaaa", "xxxxxxxxxx" — low entropy
        return True
    return False


@dataclass
class Finding:
    pattern: str
    severity: str
    line: int
    snippet: str


def scan_text(text: str) -> list[Finding]:
    findings: list[Finding] = []
    lines = text.splitlines()
    for name, (pattern, severity) in PATTERNS.items():
        for m in pattern.finditer(text):
            value = m.group(1) if m.groups() else m.group(0)
            if is_placeholder(value):
                continue
            line_no = text.count("\n", 0, m.start()) + 1
            src = lines[line_no - 1] if 0 < line_no <= len(lines) else m.group(0)
            redacted = src[: m.start() - text.rfind("\n", 0, m.start()) - 1].strip() + " <REDACTED>"
            findings.append(Finding(name, severity, line_no, redacted[:120]))
    return findings


def scan_paths(paths: list[str]) -> list[Finding]:
    out: list[Finding] = []
    for p in paths:
        try:
            text = open(p, errors="replace").read()
        except OSError as e:
            out.append(Finding("unreadable_file", "MEDIUM", 0, f"{p}: {e}"))
            continue
        for f in scan_text(text):
            out.append(Finding(f.pattern, f.severity, f.line, f"{p}:{f.line} {f.snippet}"))
    return out


def report(findings: list[Finding]) -> dict:
    high = [f for f in findings if f.severity == "HIGH"]
    status = "BLOCKED" if high else ("WARN" if findings else "CLEAN")
    return {"status": status, "findings": [asdict(f) for f in findings]}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--paths", nargs="*", default=[])
    ap.add_argument("--stdin", action="store_true")
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args(argv)

    if args.selfcheck:
        return selfcheck()

    if not args.paths and not args.stdin:
        # L4 (EVAL-ship-bypass.md): a call with neither --paths nor --stdin used to
        # report CLEAN having scanned zero content — indistinguishable from a real
        # scan that found nothing. A distinct exit/status makes the difference visible.
        print(json.dumps({"status": "NO_INPUT", "findings": [],
                           "why": "neither --paths nor --stdin given — nothing was scanned"}, indent=2))
        return 2

    findings = scan_paths(args.paths) if args.paths else []
    if args.stdin:
        findings += [
            Finding(f.pattern, f.severity, f.line, f.snippet)
            for f in scan_text(sys.stdin.read())
        ]
    result = report(findings)
    print(json.dumps(result, indent=2))
    return 1 if result["status"] == "BLOCKED" else 0


def selfcheck() -> int:
    """Every branch must fail/pass as documented — a gate that can't fail isn't a gate."""
    cases = [
        ("aws key", 'const key = "AKIAABCDEFGHIJKLMNOP";', "BLOCKED"),
        ("private key", "-----BEGIN RSA PRIVATE KEY-----\nMIIB...\n-----END RSA PRIVATE KEY-----", "BLOCKED"),
        ("stripe live key", 'STRIPE_KEY="sk_live_51H8xj2KZ9dR7mNq3vWbYtLpXsAcGh4TfEab"', "BLOCKED"),
        ("placeholder", 'AWS_SECRET_ACCESS_KEY="your-key-here"', "CLEAN"),
        ("placeholder generic", 'API_TOKEN = "changeme_replace_me"', "CLEAN"),
        ("clean prose", "this function reads the config and returns a dict", "CLEAN"),
        # L3 (EVAL-ship-bypass.md): live secrets with no SECRET/TOKEN-shaped variable name.
        ("conn string creds", 'DATABASE_URL="postgresql://admin:Tr0ub4dor%263@prod-db.internal.acme.co:5432/app"', "BLOCKED"),
        ("bearer/JWT", 'headers = {"Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N"}', "BLOCKED"),
        ("google oauth token", 'x = {"clientSecretValue": "ya29.a0AfH6SMBx71234567890abcdefghijklmnopqrstuvwxyzABCDEFGH"}', "BLOCKED"),
        ("bearer placeholder", 'headers = {"Authorization": "Bearer your-key-here-0000000000000"}', "CLEAN"),
    ]
    for label, text, expect in cases:
        got = report(scan_text(text))["status"]
        assert got == expect, f"{label}: expected {expect}, got {got}"
    assert main(["--paths", "/nonexistent/path/x.env"]) == 0, "unreadable file must not crash/block"
    # L4 (EVAL-ship-bypass.md): no --paths and no --stdin must be distinguishable from a real CLEAN scan.
    assert main([]) == 2, "no input at all must be NO_INPUT (exit 2), never a silent CLEAN"
    print(f"SELFCHECK OK — {len(cases)} patterns + 1 IO-error branch + 1 NO_INPUT branch, all as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
