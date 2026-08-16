"""
AI-Powered Pytest Test Suite Generator.

Analyzes modified functions via AST and uses Gemini 2.5 to synthesize:
- Runnable pytest test functions
- Mocks and fixtures for dependencies
- Boundary / edge-case assertions
- Parameterized test scenarios
"""
import asyncio
import ast
import re
from dataclasses import dataclass
from typing import List, Optional
from google import genai
from app.core.config import settings
from app.core.logging import logger


@dataclass
class GeneratedTestSuite:
    filename: str              # e.g. "test_auth_service.py"
    source_file: str           # e.g. "app/services/auth_service.py"
    test_code: str             # Full runnable pytest code
    functions_covered: List[str]
    coverage_estimate: str     # "~X% line coverage"


_TEST_SYSTEM_PROMPT = """You are a senior Python test engineer.
Given Python source code and its diff, generate a complete, runnable pytest test file.

Requirements:
- Use pytest style (def test_*, not unittest classes)
- Use unittest.mock or pytest-mock for all external dependencies
- Include parametrize decorators for boundary/edge cases
- Cover happy path, error cases, and boundary conditions
- Include fixtures at the top of the file
- All tests must be self-contained and not require a running server
- Return ONLY the Python test code, no markdown fences, no explanations
"""


def _extract_functions_from_patch(patch: str) -> List[str]:
    """Extract function names from a diff patch."""
    funcs = []
    added = "\n".join(l[1:] for l in patch.splitlines() if l.startswith("+"))
    try:
        tree = ast.parse(added)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_"):
                    funcs.append(node.name)
    except SyntaxError:
        for m in re.finditer(r"def (\w+)\(", added):
            funcs.append(m.group(1))
    return list(set(funcs))


async def generate_tests_for_diff(
    diff_files: List[dict],
    pr_context: str = "",
) -> List[GeneratedTestSuite]:
    """
    Generate pytest test suites for all modified Python files in a diff.

    Args:
        diff_files: List of dicts with keys "filename", "patch"
        pr_context: PR title and description for extra context

    Returns:
        List of GeneratedTestSuite objects (one per modified Python file)
    """
    client = genai.Client(api_key=settings.gemini_api_key)
    suites = []

    py_files = [f for f in diff_files if f.get("filename", "").endswith(".py")]

    async def _generate_for_file(file_info: dict) -> Optional[GeneratedTestSuite]:
        fname = file_info.get("filename", "")
        patch = file_info.get("patch", "") or ""
        if not patch.strip():
            return None

        functions_covered = _extract_functions_from_patch(patch)

        user_prompt = f"""Source file: {fname}
PR context: {pr_context}

Diff patch:
{patch[:5000]}

Functions modified/added: {", ".join(functions_covered) or "unknown"}

Generate a complete pytest test file for this code."""

        try:
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=settings.gemini_model,
                contents=[
                    {"role": "user", "parts": [{"text": _TEST_SYSTEM_PROMPT}]},
                    {"role": "model", "parts": [{"text": "I will generate a complete pytest file with no explanations."}]},
                    {"role": "user", "parts": [{"text": user_prompt}]},
                ],
            )
            code = response.text or ""
            # Strip markdown fences
            code = re.sub(r"```python\s*|```\s*", "", code).strip()

            test_filename = "test_" + fname.replace("/", "_").replace("\\", "_").removesuffix(".py") + ".py"

            return GeneratedTestSuite(
                filename=test_filename,
                source_file=fname,
                test_code=code,
                functions_covered=functions_covered,
                coverage_estimate=f"~{min(len(functions_covered) * 15, 85)}% line coverage",
            )
        except Exception as e:
            logger.error(f"[testgen] Failed for {fname}: {e}")
            return None

    tasks = [_generate_for_file(f) for f in py_files[:5]]  # Limit to 5 files
    results = await asyncio.gather(*tasks)
    suites = [r for r in results if r is not None]
    return suites
