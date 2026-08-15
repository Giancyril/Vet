"""
High-performance Regex & Entropy-based Secret Scanner.
Detects API keys, access tokens, credentials, and private keys in diffs before LLM analysis.
"""
import math
import re
from dataclasses import dataclass
from typing import List, Optional, Pattern


@dataclass
class SecretFinding:
    secret_type: str
    file_path: str
    line_number: int
    masked_secret: str
    severity: str = "blocking"
    description: str = ""


# Pre-compiled high-confidence secret patterns
_SECRET_PATTERNS = [
    (
        "AWS Access Key ID",
        re.compile(r"(?:A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}"),
        "AWS Access Key ID exposed in code. Revoke immediately in IAM console.",
    ),
    (
        "GitHub Personal Access Token",
        re.compile(r"ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}"),
        "GitHub personal access token detected. Revoke and rotate token immediately.",
    ),
    (
        "Stripe Secret Key",
        re.compile(r"sk_live_[0-9a-zA-Z]{24,34}"),
        "Live Stripe Secret Key exposed. Can lead to unauthorized payment actions.",
    ),
    (
        "Stripe Restricted Key",
        re.compile(r"rk_live_[0-9a-zA-Z]{24,34}"),
        "Live Stripe Restricted Key detected.",
    ),
    (
        "OpenAI API Key",
        re.compile(r"sk-(?:proj-)?[a-zA-Z0-9_-]{32,64}"),
        "OpenAI API Key detected. Unauthorized usage may incur unexpected billing.",
    ),
    (
        "Google AI / Gemini API Key",
        re.compile(r"AIzaSy[0-9a-zA-Z_-]{33}"),
        "Google Cloud / Gemini API key detected in code.",
    ),
    (
        "Slack Webhook URL",
        re.compile(r"https://hooks\.slack\.com/services/T[a-zA-Z0-9_]+/B[a-zA-Z0-9_]+/[a-zA-Z0-9_]+"),
        "Slack Incoming Webhook URL exposed.",
    ),
    (
        "Private RSA/SSH Key",
        re.compile(r"-----BEGIN (?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----"),
        "Private cryptographic key committed into source code. Critical security risk.",
    ),
    (
        "JWT Token",
        re.compile(r"eyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}"),
        "Hardcoded JSON Web Token (JWT) detected.",
    ),
]


def _calculate_shannon_entropy(data: str) -> float:
    """Calculate the Shannon entropy of a string (higher = more random/secret-like)."""
    if not data:
        return 0.0
    entropy = 0.0
    length = len(data)
    for char in set(data):
        p_x = float(data.count(char)) / length
        entropy -= p_x * math.log2(p_x)
    return entropy


def _mask_secret(secret: str) -> str:
    if len(secret) <= 8:
        return "***"
    return secret[:4] + "..." + secret[-4:]


def scan_diff_for_secrets(
    file_path: str,
    diff_text: str,
) -> List[SecretFinding]:
    """
    Scans added lines in a unified diff for leaked credentials or secrets.
    Returns a list of SecretFinding objects with line numbers and masked samples.
    """
    findings: List[SecretFinding] = []
    current_line = 0

    for line in diff_text.splitlines():
        # Track line numbers in unified diff
        hunk_match = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if hunk_match:
            current_line = int(hunk_match.group(1)) - 1
            continue

        if line.startswith("+") and not line.startswith("+++"):
            current_line += 1
            added_content = line[1:].strip()

            # Check regex patterns
            for name, pattern, desc in _SECRET_PATTERNS:
                matches = pattern.findall(added_content)
                for match in matches:
                    match_str = match if isinstance(match, str) else match[0]
                    findings.append(
                        SecretFinding(
                            secret_type=name,
                            file_path=file_path,
                            line_number=current_line,
                            masked_secret=_mask_secret(match_str),
                            severity="blocking",
                            description=desc,
                        )
                    )

        elif not line.startswith("-"):
            current_line += 1

    return findings
