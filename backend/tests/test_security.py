"""Unit tests for secret scanning engine and OWASP compliance mapping."""
import pytest
from app.security.owasp_rules import classify_owasp, OWASP_RULES
from app.security.secret_scanner import (
    _calculate_shannon_entropy,
    _mask_secret,
    scan_diff_for_secrets,
)


# Use separated string tokens to prevent GitHub Push Protection false alarms on test files
DUMMY_AWS = "AKIA" + "0000000000000000"
DUMMY_GH = "ghp_" + "0" * 36
DUMMY_STRIPE = "sk_live_" + "0" * 24

SAMPLE_DIFF_WITH_AWS_KEY = f"""
@@ -1,5 +1,6 @@
 import os
+AWS_SECRET_KEY = "{DUMMY_AWS}"
 def connect():
     pass
"""

SAMPLE_DIFF_WITH_GITHUB_PAT = f"""
@@ -10,3 +10,4 @@
+GITHUB_TOKEN = "{DUMMY_GH}"
"""

SAMPLE_DIFF_WITH_STRIPE = f"""
@@ -1,2 +1,3 @@
+stripe.api_key = "{DUMMY_STRIPE}"
"""

SAMPLE_DIFF_CLEAN = """
@@ -1,3 +1,4 @@
+user_name = os.environ.get("USER_NAME")
+api_key = os.environ.get("API_KEY")
"""


class TestSecretScanner:
    def test_detects_aws_key(self):
        findings = scan_diff_for_secrets("app/config.py", SAMPLE_DIFF_WITH_AWS_KEY)
        assert len(findings) == 1
        assert findings[0].secret_type == "AWS Access Key ID"
        assert findings[0].severity == "blocking"
        assert findings[0].line_number == 2
        assert "AKIA" in findings[0].masked_secret

    def test_detects_github_pat(self):
        findings = scan_diff_for_secrets("app/auth.py", SAMPLE_DIFF_WITH_GITHUB_PAT)
        assert len(findings) == 1
        assert "GitHub" in findings[0].secret_type
        assert findings[0].severity == "blocking"

    def test_detects_stripe_key(self):
        findings = scan_diff_for_secrets("app/billing.py", SAMPLE_DIFF_WITH_STRIPE)
        assert len(findings) == 1
        assert "Stripe" in findings[0].secret_type

    def test_clean_diff_returns_zero_findings(self):
        findings = scan_diff_for_secrets("app/safe.py", SAMPLE_DIFF_CLEAN)
        assert len(findings) == 0

    def test_mask_secret(self):
        masked = _mask_secret(DUMMY_AWS)
        assert masked.startswith("AKIA")
        assert "..." in masked

    def test_shannon_entropy_calculation(self):
        low_entropy = _calculate_shannon_entropy("aaaaaaaaaa")
        high_entropy = _calculate_shannon_entropy("aB8$kP9!zL2@mQ4#")
        assert low_entropy == 0.0
        assert high_entropy > 3.5


class TestOWASPRules:
    def test_all_10_owasp_rules_defined(self):
        assert len(OWASP_RULES) == 10

    def test_classify_sqli(self):
        rule = classify_owasp("SQL Injection detected", "User input not escaped before query execution")
        assert rule is not None
        assert rule.code == "A03:2021"

    def test_classify_hardcoded_secret(self):
        rule = classify_owasp("Secret leak", "Found hardcoded token in config file")
        assert rule is not None
        assert rule.code == "A02:2021"

    def test_classify_missing_auth(self):
        rule = classify_owasp("Authorization bypass", "Missing RBAC check on delete endpoint")
        assert rule is not None
        assert rule.code == "A01:2021"

    def test_classify_ssrf(self):
        rule = classify_owasp("SSRF vulnerability", "Fetching url without whitelist validation")
        assert rule is not None
        assert rule.code == "A10:2021"
