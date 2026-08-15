"""
OWASP Top 10 compliance rules and classification helper.
Maps code review findings to standard OWASP categories with CWE references.
"""
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class OWASPRule:
    code: str          # e.g. "A01:2021"
    name: str
    cwe_ids: List[str]
    description: str
    keywords: List[str]


OWASP_RULES: List[OWASPRule] = [
    OWASPRule(
        code="A01:2021",
        name="Broken Access Control",
        cwe_ids=["CWE-200", "CWE-284", "CWE-285", "CWE-639"],
        description="Failures in enforcing permissions, IDOR, or bypassing access checks.",
        keywords=["idor", "access control", "permission", "authorization", "bypass", "rbac"],
    ),
    OWASPRule(
        code="A02:2021",
        name="Cryptographic Failures",
        cwe_ids=["CWE-259", "CWE-327", "CWE-330", "CWE-798"],
        description="Hardcoded secrets, weak encryption algorithms, or insecure random generators.",
        keywords=["secret", "token", "password", "crypto", "encryption", "md5", "sha1", "key"],
    ),
    OWASPRule(
        code="A03:2021",
        name="Injection",
        cwe_ids=["CWE-79", "CWE-89", "CWE-94", "CWE-77"],
        description="SQL injection, cross-site scripting (XSS), OS command injection, or template injection.",
        keywords=["injection", "sqli", "xss", "sanitize", "escape", "eval(", "exec(", "subprocess"],
    ),
    OWASPRule(
        code="A04:2021",
        name="Insecure Design",
        cwe_ids=["CWE-209", "CWE-256", "CWE-522"],
        description="Missing rate limiting, unbounded file uploads, or flawed business logic.",
        keywords=["rate limit", "upload", "dos", "denial of service", "unbounded", "design flaw"],
    ),
    OWASPRule(
        code="A05:2021",
        name="Security Misconfiguration",
        cwe_ids=["CWE-16", "CWE-611", "CWE-1004"],
        description="Default credentials, overly permissive CORS, debug mode enabled in production.",
        keywords=["cors", "debug=true", "misconfiguration", "default credential", "cookie", "httponly"],
    ),
    OWASPRule(
        code="A06:2021",
        name="Vulnerable and Outdated Components",
        cwe_ids=["CWE-1104"],
        description="Using libraries or packages with known CVE vulnerabilities.",
        keywords=["cve", "outdated", "vulnerable dependency", "package vulnerability"],
    ),
    OWASPRule(
        code="A07:2021",
        name="Identification and Authentication Failures",
        cwe_ids=["CWE-287", "CWE-384"],
        description="Session fixation, weak password policies, or missing MFA validation.",
        keywords=["session", "auth", "authentication", "login", "brute force", "jwt"],
    ),
    OWASPRule(
        code="A08:2021",
        name="Software and Data Integrity Failures",
        cwe_ids=["CWE-494", "CWE-502"],
        description="Insecure deserialization (pickle, yaml.load), unsigned code execution.",
        keywords=["pickle.loads", "yaml.load", "deserialization", "integrity", "unsafe load"],
    ),
    OWASPRule(
        code="A09:2021",
        name="Security Logging and Monitoring Failures",
        cwe_ids=["CWE-778", "CWE-117"],
        description="Missing audit trails or logging sensitive PII/passwords into log streams.",
        keywords=["logging", "log injection", "pii in logs", "audit trail"],
    ),
    OWASPRule(
        code="A10:2021",
        name="Server-Side Request Forgery (SSRF)",
        cwe_ids=["CWE-918"],
        description="Fetching remote resources without validating user-supplied destination URLs.",
        keywords=["ssrf", "fetch url", "internal network", "127.0.0.1", "metadata endpoint"],
    ),
]


def classify_owasp(title: str, explanation: str) -> Optional[OWASPRule]:
    """
    Classifies a finding into an OWASP Top 10 category using title and explanation keywords.
    """
    text = f"{title} {explanation}".lower()
    for rule in OWASP_RULES:
        for kw in rule.keywords:
            if kw in text:
                return rule
    return None
