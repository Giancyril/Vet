"""
GitHub API client for creating companion remediation PRs using httpx.
Creates a new branch on the repo, pushes patched files, and opens a PR.
"""
import base64
from typing import List, Optional
import httpx

from app.core.logging import logger
from app.services.remediation_service import RemediationPlan


async def create_companion_remediation_pr(
    owner: str,
    repo_name: str,
    base_branch: str,
    pr_number: int,
    plan: RemediationPlan,
    installation_token: str,
) -> Optional[dict]:
    """
    Creates a new branch `vet/fix-pr-{pr_number}` off `base_branch`,
    commits the remediated files, and opens a companion Pull Request.

    Returns:
        Dict with {pr_number, pr_url, branch_name} or None on error
    """
    if not plan.patches:
        logger.warning(f"No patches to apply for {owner}/{repo_name}#{pr_number}")
        return None

    headers = {
        "Authorization": f"Bearer {installation_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    base_url = f"https://api.github.com/repos/{owner}/{repo_name}"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Get SHA of base branch / commit
            ref_resp = await client.get(f"{base_url}/git/ref/heads/{base_branch}", headers=headers)
            if ref_resp.status_code == 200:
                base_sha = ref_resp.json()["object"]["sha"]
            else:
                # Treat base_branch as a direct SHA commit or default branch
                base_sha = base_branch

            target_branch = plan.branch_name

            # 2. Create target branch ref
            create_ref_payload = {
                "ref": f"refs/heads/{target_branch}",
                "sha": base_sha,
            }
            ref_create_resp = await client.post(f"{base_url}/git/refs", headers=headers, json=create_ref_payload)
            logger.info(f"Branch create response: {ref_create_resp.status_code}")

            # 3. Update / create patched files in the target branch
            for patch in plan.patches:
                # Get existing file SHA if present
                get_file_resp = await client.get(
                    f"{base_url}/contents/{patch.file_path}?ref={target_branch}",
                    headers=headers,
                )
                file_sha = None
                if get_file_resp.status_code == 200:
                    file_sha = get_file_resp.json().get("sha")

                b64_content = base64.b64encode(patch.patched_content.encode("utf-8")).decode("utf-8")
                file_payload = {
                    "message": f"fix(vet): auto-remediate findings in {patch.file_path}",
                    "content": b64_content,
                    "branch": target_branch,
                }
                if file_sha:
                    file_payload["sha"] = file_sha

                put_resp = await client.put(
                    f"{base_url}/contents/{patch.file_path}",
                    headers=headers,
                    json=file_payload,
                )
                logger.info(f"Updated file {patch.file_path}: {put_resp.status_code}")

            # 4. Open Companion Pull Request
            pr_body = (
                f"## 🤖 Auto-Remediation Companion PR\n\n"
                f"This pull request was automatically created by **Vet AI Code Reviewer** "
                f"to resolve issues identified in #{pr_number}.\n\n"
                f"### 📋 Applied Fixes ({plan.total_fixes}):\n"
            )
            for patch in plan.patches:
                pr_body += f"- **`{patch.file_path}`**:\n"
                for finding_title in patch.findings_fixed:
                    pr_body += f"  - {finding_title}\n"

            pr_body += "\n> 💡 *Review the diff carefully before merging into your feature branch.*"

            pr_payload = {
                "title": f"fix(vet): auto-remediate #{pr_number} review findings",
                "body": pr_body,
                "base": base_branch,
                "head": target_branch,
            }

            pr_resp = await client.post(f"{base_url}/pulls", headers=headers, json=pr_payload)
            if pr_resp.status_code in (200, 201):
                pr_data = pr_resp.json()
                logger.info(f"Created companion PR #{pr_data.get('number')}")
                return {
                    "pr_number": pr_data.get("number"),
                    "pr_url": pr_data.get("html_url"),
                    "branch_name": target_branch,
                    "total_fixes": plan.total_fixes,
                }
            else:
                logger.warning(f"Failed to open PR: {pr_resp.status_code} {pr_resp.text}")
                return {
                    "pr_number": None,
                    "pr_url": None,
                    "branch_name": target_branch,
                    "total_fixes": plan.total_fixes,
                }
    except Exception as e:
        logger.error(f"Error creating companion PR: {e}")
        return None
