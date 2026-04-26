"""
GitHub API client using httpx.
Handles: repos, commits, pull requests, reviews, diffs.
"""

from typing import Optional

import httpx

from app.core.config import settings

GITHUB_API = "https://api.github.com"
PER_PAGE = 100


class GitHubRateLimitError(Exception):
    """Raised when GitHub rate limits or abuse limits the current request."""

    def __init__(self, message: str, reset_at: str | None = None, retry_after: str | None = None):
        super().__init__(message)
        self.reset_at = reset_at
        self.retry_after = retry_after


class GitHubClient:
    """Thin wrapper around the GitHub REST API."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.GITHUB_TOKEN
        self.headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            self.headers["Authorization"] = f"Bearer {self.token}"
        self._client = httpx.Client(
            base_url=GITHUB_API,
            headers=self.headers,
            timeout=30.0,
        )

    # ── helpers ──────────────────────────────────────────────

    def _get(self, path: str, params: dict | None = None) -> dict | list:
        resp = self._client.get(path, params=params)

        if resp.status_code in (403, 429):
            body = (resp.text or "").lower()
            remaining = resp.headers.get("x-ratelimit-remaining")
            reset_at = resp.headers.get("x-ratelimit-reset")
            retry_after = resp.headers.get("retry-after")
            rate_limited = (
                remaining == "0"
                or resp.status_code == 429
                or "rate limit" in body
                or "secondary rate limit" in body
                or "too many requests" in body
                or "abuse detection" in body
            )
            if rate_limited:
                raise GitHubRateLimitError(
                    "GitHub rate limit exceeded. Configure a GITHUB_TOKEN with repo read access, reduce pages, or retry later.",
                    reset_at=reset_at,
                    retry_after=retry_after,
                )

        resp.raise_for_status()
        return resp.json()

    def _get_paginated(self, path: str, params: dict | None = None, max_pages: int = 10) -> list:
        """Return up to max_pages pages of results."""
        params = params or {}
        params.setdefault("per_page", PER_PAGE)
        results = []
        for page in range(1, max_pages + 1):
            params["page"] = page
            data = self._get(path, params)
            if not data:
                break
            results.extend(data)
            if len(data) < PER_PAGE:
                break
        return results

    # ── repos ────────────────────────────────────────────────

    def list_org_repos(self, org: str | None = None) -> list[dict]:
        org = org or settings.GITHUB_ORG
        if org:
            return self._get_paginated(f"/orgs/{org}/repos", {"type": "all"})
        # Fallback: list repos of authenticated user
        return self._get_paginated("/user/repos", {"affiliation": "owner,collaborator,organization_member"})

    def get_repo(self, full_name: str) -> dict:
        return self._get(f"/repos/{full_name}")

    # ── commits ──────────────────────────────────────────────

    def list_commits(self, full_name: str, since: str | None = None, until: str | None = None,
                     branch: str | None = None, max_pages: int = 10) -> list[dict]:
        params: dict = {}
        if since:
            params["since"] = since
        if until:
            params["until"] = until
        if branch:
            params["sha"] = branch
        return self._get_paginated(f"/repos/{full_name}/commits", params, max_pages=max_pages)

    def get_commit(self, full_name: str, sha: str) -> dict:
        return self._get(f"/repos/{full_name}/commits/{sha}")

    # ── pull requests ────────────────────────────────────────

    def list_pull_requests(self, full_name: str, state: str = "all", max_pages: int = 10) -> list[dict]:
        return self._get_paginated(
            f"/repos/{full_name}/pulls",
            {"state": state, "sort": "updated", "direction": "desc"},
            max_pages=max_pages,
        )

    def get_pull_request(self, full_name: str, pr_number: int) -> dict:
        return self._get(f"/repos/{full_name}/pulls/{pr_number}")

    def list_pr_commits(self, full_name: str, pr_number: int) -> list[dict]:
        return self._get_paginated(f"/repos/{full_name}/pulls/{pr_number}/commits")

    # ── reviews ──────────────────────────────────────────────

    def list_pr_reviews(self, full_name: str, pr_number: int) -> list[dict]:
        return self._get_paginated(f"/repos/{full_name}/pulls/{pr_number}/reviews")

    # ── utility ──────────────────────────────────────────────

    def get_authenticated_user(self) -> dict:
        return self._get("/user")

    def get_rate_limit(self) -> dict:
        return self._get("/rate_limit")

    def close(self):
        self._client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
