import pytest
from app.github.diff_fetcher import (
    _should_skip_file,
    ChangedFile,
    PRContext,
    build_pr_context,
)
from unittest.mock import AsyncMock, patch


def test_should_skip_lockfiles():
    assert _should_skip_file("package-lock.json") is True
    assert _should_skip_file("yarn.lock") is True
    assert _should_skip_file("poetry.lock") is True
    assert _should_skip_file("go.sum") is True


def test_should_skip_minified_files():
    assert _should_skip_file("app.min.js") is True
    assert _should_skip_file("style.min.css") is True


def test_should_not_skip_normal_files():
    assert _should_skip_file("app/main.py") is False
    assert _should_skip_file("src/index.ts") is False
    assert _should_skip_file("README.md") is False
    assert _should_skip_file("backend/app/core/config.py") is False


@pytest.mark.asyncio
async def test_build_pr_context_filters_skipped_and_removed():
    """
    Verifies that build_pr_context correctly:
    - Skips lockfiles
    - Skips 'removed' status files
    - Includes modified/added files
    """
    mock_files = [
        {
            "filename": "src/auth.py",
            "status": "modified",
            "patch": "@@ -1,5 +1,7 @@\n+import os",
            "additions": 2,
            "deletions": 0,
        },
        {
            "filename": "package-lock.json",
            "status": "modified",
            "patch": None,
            "additions": 100,
            "deletions": 80,
        },
        {
            "filename": "src/old_module.py",
            "status": "removed",
            "patch": None,
            "additions": 0,
            "deletions": 50,
        },
        {
            "filename": "src/utils.ts",
            "status": "added",
            "patch": "@@ -0,0 +1,20 @@\n+export function foo() {}",
            "additions": 20,
            "deletions": 0,
        },
    ]

    with patch(
        "app.github.diff_fetcher.fetch_pr_files",
        new=AsyncMock(return_value=mock_files),
    ), patch(
        "app.github.diff_fetcher.fetch_file_content",
        new=AsyncMock(return_value="mock content"),
    ):
        context = await build_pr_context(
            owner="Giancyril",
            repo="test-repo",
            pr_number=5,
            pr_title="feat: add auth",
            pr_author="giancyril",
            pr_body="",
            head_sha="abc123",
            base_sha="def456",
            installation_token="fake-token",
        )

    # Only src/auth.py and src/utils.ts should be in changed_files
    filenames = [f.filename for f in context.changed_files]
    assert "src/auth.py" in filenames
    assert "src/utils.ts" in filenames
    assert "package-lock.json" not in filenames   # filtered: lockfile
    assert "src/old_module.py" not in filenames   # filtered: removed

    assert context.total_additions == 22   # 2 + 20
    assert context.total_deletions == 0
