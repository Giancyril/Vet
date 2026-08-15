import base64
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import httpx

from app.core.logging import logger

# Files to skip — lockfiles, minified bundles, generated code
SKIP_PATTERNS = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Pipfile.lock",
    "Cargo.lock",
    "composer.lock",
    "go.sum",
    "*.min.js",
    "*.min.css",
    "*.pb.go",
    "*.pb.py",
}

# Max raw file size to fetch for context (100 KB)
MAX_FILE_BYTES = 100_000


def _should_skip_file(path: str) -> bool:
    """Returns True if the file should be excluded from review."""
    filename = path.split("/")[-1]
    for pattern in SKIP_PATTERNS:
        if pattern.startswith("*"):
            if filename.endswith(pattern[1:]):
                return True
        elif filename == pattern:
            return True
    return False


@dataclass
class ChangedFile:
    filename: str
    status: str          # added | modified | removed | renamed
    patch: Optional[str] = None   # unified diff hunk for this file
    full_content: Optional[str] = None  # raw content of the NEW version
    additions: int = 0
    deletions: int = 0


@dataclass
class PRContext:
    owner: str
    repo: str
    pr_number: int
    head_sha: str
    base_sha: str
    pr_title: str
    pr_author: str
    pr_body: str
    changed_files: List[ChangedFile] = field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0


def _make_headers(token: str) -> Dict[str, str]:
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def fetch_pr_files(
    owner: str,
    repo: str,
    pr_number: int,
    token: str,
) -> List[Dict]:
    """Fetches the list of changed files (with patches) from the GitHub PR Files API."""
    headers = _make_headers(token)
    files = []
    page = 1

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            url = (
                f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
                f"?per_page=100&page={page}"
            )
            resp = await client.get(url, headers=headers)
            if resp.status_code != 200:
                raise RuntimeError(
                    f"GitHub PR Files API error {resp.status_code}: {resp.text}"
                )
            batch = resp.json()
            if not batch:
                break
            files.extend(batch)
            if len(batch) < 100:
                break
            page += 1

    logger.info(f"Fetched {len(files)} changed files for {owner}/{repo}#{pr_number}")
    return files


async def fetch_file_content(
    owner: str,
    repo: str,
    path: str,
    ref: str,
    token: str,
) -> Optional[str]:
    """
    Fetches the decoded raw content of a file at a specific git ref.
    Returns None if the file is too large or not found.
    """
    headers = _make_headers(token)
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}?ref={ref}"

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code == 404:
            return None
        if resp.status_code != 200:
            logger.warning(
                f"Could not fetch file content for {path}@{ref}: {resp.status_code}"
            )
            return None

        data = resp.json()
        size = data.get("size", 0)
        if size > MAX_FILE_BYTES:
            logger.info(
                f"Skipping full content for {path} — too large ({size} bytes > {MAX_FILE_BYTES})"
            )
            return None

        encoded = data.get("content", "")
        try:
            # GitHub encodes file contents in base64 with newlines
            decoded = base64.b64decode(encoded.replace("\n", "")).decode("utf-8", errors="replace")
            return decoded
        except Exception as e:
            logger.warning(f"Failed to decode content for {path}: {e}")
            return None


async def build_pr_context(
    owner: str,
    repo: str,
    pr_number: int,
    pr_title: str,
    pr_author: str,
    pr_body: str,
    head_sha: str,
    base_sha: str,
    installation_token: str,
) -> PRContext:
    """
    Builds a complete PRContext for review analysis:
    1. Fetches the list of changed files with unified diff patches.
    2. For each non-skipped file, fetches the full file content at head_sha.
    """
    context = PRContext(
        owner=owner,
        repo=repo,
        pr_number=pr_number,
        head_sha=head_sha,
        base_sha=base_sha,
        pr_title=pr_title,
        pr_author=pr_author,
        pr_body=pr_body,
    )

    raw_files = await fetch_pr_files(owner, repo, pr_number, installation_token)

    for raw_file in raw_files:
        path = raw_file.get("filename", "")
        status = raw_file.get("status", "modified")

        if _should_skip_file(path):
            logger.info(f"Skipping auto-generated/lockfile: {path}")
            continue

        # Skip removed files — nothing to review
        if status == "removed":
            continue

        patch = raw_file.get("patch")  # May be None for binary files
        additions = raw_file.get("additions", 0)
        deletions = raw_file.get("deletions", 0)

        # Fetch full file content for richer context
        full_content = await fetch_file_content(
            owner, repo, path, head_sha, installation_token
        )

        changed_file = ChangedFile(
            filename=path,
            status=status,
            patch=patch,
            full_content=full_content,
            additions=additions,
            deletions=deletions,
        )
        context.changed_files.append(changed_file)
        context.total_additions += additions
        context.total_deletions += deletions

    logger.info(
        f"Built PR context for {owner}/{repo}#{pr_number}: "
        f"{len(context.changed_files)} reviewable files, "
        f"+{context.total_additions}/-{context.total_deletions} lines"
    )
    return context
