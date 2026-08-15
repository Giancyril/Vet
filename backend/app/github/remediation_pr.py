"""
GitHub API client for creating companion remediation PRs.
Creates a new branch on the repo, pushes patched files, and opens a PR.
"""
import base64
from typing import List, Optional
from github import Github, InputGitTreeElement
from github.GithubException import GithubException

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

    try:
        gh = Github(installation_token)
        repo = gh.get_repo(f"{owner}/{repo_name}")

        # Get reference to the PR's head branch
        ref_name = f"heads/{base_branch}"
        try:
            base_ref = repo.get_git_ref(ref_name)
            base_sha = base_ref.object.sha
        except GithubException:
            base_ref = repo.get_branch(base_branch)
            base_sha = base_ref.commit.sha

        # Create new branch for the fix
        target_branch = plan.branch_name
        target_ref_name = f"refs/heads/{target_branch}"

        try:
            # If branch already exists, delete it first
            existing = repo.get_git_ref(f"heads/{target_branch}")
            existing.delete()
        except GithubException:
            pass

        repo.create_git_ref(ref=target_ref_name, sha=base_sha)
        logger.info(f"Created branch {target_branch} at {base_sha[:7]}")

        # Commit each patched file
        for patch in plan.patches:
            try:
                contents = repo.get_contents(patch.file_path, ref=target_branch)
                repo.update_file(
                    path=patch.file_path,
                    message=f"fix(vet): auto-remediate findings in {patch.file_path}",
                    content=patch.patched_content,
                    sha=contents.sha,
                    branch=target_branch,
                )
            except GithubException:
                repo.create_file(
                    path=patch.file_path,
                    message=f"fix(vet): auto-remediate findings in {patch.file_path}",
                    content=patch.patched_content,
                    branch=target_branch,
                )

        # Open Companion Pull Request
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

        created_pr = repo.create_pull(
            title=f"fix(vet): auto-remediate #{pr_number} review findings",
            body=pr_body,
            base=base_branch,
            head=target_branch,
        )

        logger.info(f"Created companion PR #{created_pr.number} ({created_pr.html_url})")

        return {
            "pr_number": created_pr.number,
            "pr_url": created_pr.html_url,
            "branch_name": target_branch,
            "total_fixes": plan.total_fixes,
        }
    except Exception as e:
        logger.error(f"Failed to create companion PR for {owner}/{repo_name}#{pr_number}: {e}")
        return None
