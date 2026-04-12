from __future__ import annotations

import re
from dataclasses import dataclass

from honeyhex.commit.models import StateDiff


@dataclass(frozen=True)
class AuditFinding:
    rule: str
    severity: str
    detail: str


_EMAIL = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
_CC_LIKE = re.compile(r"\b(?:\d[ -]*?){13,16}\d\b")
_SK = re.compile(r"sk-[a-zA-Z0-9]{10,}")
_BEARER = re.compile(r"Bearer\s+\S+")


def audit_state_diff(diff: StateDiff) -> list[AuditFinding]:
    """Heuristic PII / secret checks on snapshot fields (stdlib only)."""
    findings: list[AuditFinding] = []
    blob = diff.model_dump_json()
    if _EMAIL.search(blob):
        findings.append(
            AuditFinding(
                rule="pii_email",
                severity="warn",
                detail="Possible email address in snapshot text",
            ),
        )
    if _CC_LIKE.search(blob):
        findings.append(
            AuditFinding(
                rule="pii_card_like",
                severity="warn",
                detail="Digit groups resembling a payment card number",
            ),
        )
    if _SK.search(blob):
        findings.append(
            AuditFinding(
                rule="secret_sk_prefix",
                severity="error",
                detail="Substring matching sk- API key pattern",
            ),
        )
    if _BEARER.search(blob):
        findings.append(
            AuditFinding(
                rule="secret_bearer",
                severity="error",
                detail="Bearer token pattern",
            ),
        )
    return findings
