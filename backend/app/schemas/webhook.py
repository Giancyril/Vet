from typing import Any, Dict, Optional
from pydantic import BaseModel, Field


class GitHubUser(BaseModel):
    login: str
    id: int
    avatar_url: Optional[str] = None


class GitHubRepo(BaseModel):
    id: int
    name: str
    full_name: str
    private: bool
    owner: GitHubUser
    default_branch: str = "main"


class GitHubPullRequestHead(BaseModel):
    sha: str
    ref: str


class GitHubPullRequest(BaseModel):
    id: int
    number: int
    title: str
    user: GitHubUser
    head: GitHubPullRequestHead
    base: GitHubPullRequestHead
    html_url: str
    diff_url: Optional[str] = None


class GitHubInstallation(BaseModel):
    id: int
    account: Optional[Dict[str, Any]] = None


class WebhookPayload(BaseModel):
    action: str
    number: Optional[int] = None
    pull_request: Optional[GitHubPullRequest] = None
    repository: Optional[GitHubRepo] = None
    installation: Optional[GitHubInstallation] = None
    sender: Optional[GitHubUser] = None
