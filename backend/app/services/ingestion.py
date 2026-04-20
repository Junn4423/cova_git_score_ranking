"""
Ingestion service – synchronise GitHub data into MySQL.

Handles: repositories, developers (auto-create/resolve), commits,
commit files, pull requests, PR-commit links, and reviews.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.github.client import GitHubClient
from app.models.models import (
    Repository, Developer, DeveloperAlias,
    Commit, CommitFile, PullRequest, PullRequestCommit, Review,
)

logger = logging.getLogger(__name__)

# Files that should be flagged as generated / lockfile
LOCKFILE_NAMES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "composer.lock", "Gemfile.lock", "Pipfile.lock",
    "poetry.lock", "go.sum",
}
GENERATED_EXTENSIONS = {
    ".min.js", ".min.css", ".map", ".lock",
    ".pb.go", ".generated.ts", ".generated.js",
}


class IngestionService:
    """Pulls data from GitHub and persists it into the local DB."""

    def __init__(self, db: Session, gh: Optional[GitHubClient] = None):
        self.db = db
        self.gh = gh or GitHubClient()

    # ────────────────────────────────────────────────────────────
    #  Developer resolution
    # ────────────────────────────────────────────────────────────

    def resolve_developer(
        self,
        login: Optional[str],
        email: Optional[str] = None,
        name: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> Optional[Developer]:
        """Find or create a Developer from GitHub identity signals."""
        if not login and not email:
            return None

        # 1. Try by github_login
        dev = None
        if login:
            dev = self.db.query(Developer).filter_by(github_login=login).first()

        # 2. Try by alias
        if not dev and email:
            alias = (
                self.db.query(DeveloperAlias)
                .filter_by(alias_type="email", alias_value=email)
                .first()
            )
            if alias:
                dev = alias.developer

        if not dev and login:
            alias = (
                self.db.query(DeveloperAlias)
                .filter_by(alias_type="github_login", alias_value=login)
                .first()
            )
            if alias:
                dev = alias.developer

        # 3. Create new developer
        if not dev:
            dev = Developer(
                github_login=login or email.split("@")[0],
                display_name=name or login,
                email=email,
                avatar_url=avatar_url,
            )
            self.db.add(dev)
            self.db.flush()  # get id

            # Register aliases
            if email:
                self.db.add(DeveloperAlias(
                    developer_id=dev.id, alias_type="email", alias_value=email,
                ))
            if login:
                self.db.add(DeveloperAlias(
                    developer_id=dev.id, alias_type="github_login", alias_value=login,
                ))
            self.db.flush()
            logger.info("Created developer %s (id=%s)", dev.github_login, dev.id)

        # update avatar if missing
        if avatar_url and not dev.avatar_url:
            dev.avatar_url = avatar_url

        return dev

    # ────────────────────────────────────────────────────────────
    #  Sync repositories
    # ────────────────────────────────────────────────────────────

    def sync_repositories(self, org: Optional[str] = None) -> list[Repository]:
        """Fetch all repos from org and upsert into DB."""
        gh_repos = self.gh.list_org_repos(org)
        synced = []
        for r in gh_repos:
            repo = self.db.query(Repository).filter_by(github_id=r["id"]).first()
            if repo:
                repo.full_name = r["full_name"]
                repo.name = r["name"]
                repo.description = (r.get("description") or "")[:65535]
                repo.default_branch = r.get("default_branch", "main")
            else:
                repo = Repository(
                    github_id=r["id"],
                    full_name=r["full_name"],
                    name=r["name"],
                    description=(r.get("description") or "")[:65535],
                    default_branch=r.get("default_branch", "main"),
                )
                self.db.add(repo)
            synced.append(repo)
        self.db.commit()
        logger.info("Synced %d repositories", len(synced))
        return synced

    # ────────────────────────────────────────────────────────────
    #  Sync a SINGLE repo by full_name (for public testing)
    # ────────────────────────────────────────────────────────────

    def sync_single_repo(self, full_name: str) -> Repository:
        """Fetch a single repo by full_name and upsert."""
        r = self.gh.get_repo(full_name)
        repo = self.db.query(Repository).filter_by(github_id=r["id"]).first()
        if repo:
            repo.full_name = r["full_name"]
            repo.name = r["name"]
            repo.description = (r.get("description") or "")[:65535]
            repo.default_branch = r.get("default_branch", "main")
        else:
            repo = Repository(
                github_id=r["id"],
                full_name=r["full_name"],
                name=r["name"],
                description=(r.get("description") or "")[:65535],
                default_branch=r.get("default_branch", "main"),
            )
            self.db.add(repo)
        self.db.commit()
        logger.info("Synced repo: %s", repo.full_name)
        return repo

    # ────────────────────────────────────────────────────────────
    #  Sync commits
    # ────────────────────────────────────────────────────────────

    def sync_commits(
        self,
        repo: Repository,
        since: Optional[str] = None,
        max_pages: int = 5,
        fetch_files: bool = True,
    ) -> int:
        """Fetch commits for a repo and upsert, return count of new commits."""
        gh_commits = self.gh.list_commits(
            repo.full_name, since=since, max_pages=max_pages,
        )
        new_count = 0
        for gc in gh_commits:
            sha = gc["sha"]
            # skip if already exists
            existing = (
                self.db.query(Commit)
                .filter_by(repo_id=repo.id, sha=sha)
                .first()
            )
            if existing:
                continue

            author_data = gc.get("author") or {}
            commit_data = gc.get("commit", {})
            author_commit = commit_data.get("author", {})

            # Resolve developer
            author = self.resolve_developer(
                login=author_data.get("login"),
                email=author_commit.get("email"),
                name=author_commit.get("name"),
                avatar_url=author_data.get("avatar_url"),
            )

            committer_data = gc.get("committer") or {}
            committer_commit = commit_data.get("committer", {})
            committer = self.resolve_developer(
                login=committer_data.get("login"),
                email=committer_commit.get("email"),
                name=committer_commit.get("name"),
            )

            # Parse committed_at
            date_str = author_commit.get("date", "")
            committed_at = None
            if date_str:
                try:
                    committed_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

            parents = gc.get("parents", [])
            c = Commit(
                repo_id=repo.id,
                sha=sha,
                author_id=author.id if author else None,
                committer_id=committer.id if committer else None,
                message=commit_data.get("message", ""),
                committed_at=committed_at,
                parent_count=len(parents),
                is_merge=len(parents) > 1,
                raw_author_email=author_commit.get("email"),
                raw_author_name=author_commit.get("name"),
            )
            self.db.add(c)
            self.db.flush()

            # Fetch detailed commit to get file info and stats
            if fetch_files:
                try:
                    detail = self.gh.get_commit(repo.full_name, sha)
                    stats = detail.get("stats", {})
                    c.additions = stats.get("additions", 0)
                    c.deletions = stats.get("deletions", 0)
                    c.total_changes = stats.get("total", 0)

                    for f in detail.get("files", []):
                        fname = f.get("filename", "")
                        cf = CommitFile(
                            commit_id=c.id,
                            filename=fname,
                            status=f.get("status"),
                            additions=f.get("additions", 0),
                            deletions=f.get("deletions", 0),
                            changes=f.get("changes", 0),
                            patch=(f.get("patch") or "")[:16_000_000],  # MEDIUMTEXT limit
                            is_generated=self._is_generated(fname),
                            is_lockfile=self._is_lockfile(fname),
                        )
                        self.db.add(cf)
                except Exception as e:
                    logger.warning("Failed to fetch detail for %s: %s", sha[:7], e)

            new_count += 1

        repo.last_synced_at = datetime.utcnow()
        self.db.commit()
        logger.info("Synced %d new commits for %s (total fetched: %d)",
                     new_count, repo.full_name, len(gh_commits))
        return new_count

    # ────────────────────────────────────────────────────────────
    #  Sync pull requests
    # ────────────────────────────────────────────────────────────

    def sync_pull_requests(
        self,
        repo: Repository,
        state: str = "all",
        max_pages: int = 3,
        sync_reviews: bool = True,
    ) -> int:
        """Fetch PRs for a repo, upsert, and link commits & reviews."""
        gh_prs = self.gh.list_pull_requests(
            repo.full_name, state=state, max_pages=max_pages,
        )
        new_count = 0
        for gp in gh_prs:
            pr_number = gp["number"]
            pr = (
                self.db.query(PullRequest)
                .filter_by(repo_id=repo.id, github_pr_number=pr_number)
                .first()
            )

            # Resolve PR author
            user = gp.get("user") or {}
            author = self.resolve_developer(
                login=user.get("login"),
                avatar_url=user.get("avatar_url"),
            )

            def _parse_dt(s):
                if not s:
                    return None
                try:
                    return datetime.fromisoformat(s.replace("Z", "+00:00"))
                except ValueError:
                    return None

            if pr:
                pr.title = gp.get("title", "")
                pr.body = (gp.get("body") or "")[:16_000_000]
                pr.state = gp.get("state")
                pr.author_id = author.id if author else pr.author_id
                pr.merged = bool(gp.get("merged_at"))
                pr.merged_at = _parse_dt(gp.get("merged_at"))
                pr.closed_at = _parse_dt(gp.get("closed_at"))
                pr.head_branch = (gp.get("head") or {}).get("ref")
                pr.base_branch = (gp.get("base") or {}).get("ref")
                pr.github_updated_at = _parse_dt(gp.get("updated_at"))
            else:
                pr = PullRequest(
                    repo_id=repo.id,
                    github_pr_number=pr_number,
                    title=gp.get("title", ""),
                    body=(gp.get("body") or "")[:16_000_000],
                    state=gp.get("state"),
                    author_id=author.id if author else None,
                    merged=bool(gp.get("merged_at")),
                    merged_at=_parse_dt(gp.get("merged_at")),
                    closed_at=_parse_dt(gp.get("closed_at")),
                    head_branch=(gp.get("head") or {}).get("ref"),
                    base_branch=(gp.get("base") or {}).get("ref"),
                    github_created_at=_parse_dt(gp.get("created_at")),
                    github_updated_at=_parse_dt(gp.get("updated_at")),
                )
                self.db.add(pr)
                new_count += 1
            self.db.flush()

            # Link PR ↔ commits
            try:
                pr_commits = self.gh.list_pr_commits(repo.full_name, pr_number)
                for pc in pr_commits:
                    commit = (
                        self.db.query(Commit)
                        .filter_by(repo_id=repo.id, sha=pc["sha"])
                        .first()
                    )
                    if commit:
                        exists = (
                            self.db.query(PullRequestCommit)
                            .filter_by(pull_request_id=pr.id, commit_id=commit.id)
                            .first()
                        )
                        if not exists:
                            self.db.add(PullRequestCommit(
                                pull_request_id=pr.id,
                                commit_id=commit.id,
                            ))
            except Exception as e:
                logger.warning("Failed to sync PR commits for PR #%d: %s", pr_number, e)

            # Sync reviews
            if sync_reviews:
                try:
                    self._sync_reviews_for_pr(repo, pr)
                except Exception as e:
                    logger.warning("Failed to sync reviews for PR #%d: %s", pr_number, e)

        self.db.commit()
        logger.info("Synced %d new PRs for %s (total fetched: %d)",
                     new_count, repo.full_name, len(gh_prs))
        return new_count

    # ────────────────────────────────────────────────────────────
    #  Sync reviews for a PR
    # ────────────────────────────────────────────────────────────

    def _sync_reviews_for_pr(self, repo: Repository, pr: PullRequest) -> int:
        """Fetch and upsert reviews for a single PR."""
        gh_reviews = self.gh.list_pr_reviews(repo.full_name, pr.github_pr_number)
        new_count = 0
        for gr in gh_reviews:
            review_id = gr.get("id")
            existing = (
                self.db.query(Review)
                .filter_by(pull_request_id=pr.id, github_review_id=review_id)
                .first()
            )
            if existing:
                continue

            user = gr.get("user") or {}
            reviewer = self.resolve_developer(
                login=user.get("login"),
                avatar_url=user.get("avatar_url"),
            )

            submitted_str = gr.get("submitted_at", "")
            submitted_at = None
            if submitted_str:
                try:
                    submitted_at = datetime.fromisoformat(submitted_str.replace("Z", "+00:00"))
                except ValueError:
                    pass

            review = Review(
                pull_request_id=pr.id,
                reviewer_id=reviewer.id if reviewer else None,
                github_review_id=review_id,
                state=gr.get("state"),
                body=gr.get("body") or "",
                submitted_at=submitted_at,
            )
            self.db.add(review)
            new_count += 1

        return new_count

    # ────────────────────────────────────────────────────────────
    #  Full sync for one repo
    # ────────────────────────────────────────────────────────────

    def full_sync_repo(
        self,
        full_name: str,
        since: Optional[str] = None,
        max_commit_pages: int = 3,
        max_pr_pages: int = 2,
        fetch_files: bool = True,
    ) -> dict:
        """
        End-to-end sync for a single repo:
        repo → commits + files → PRs + reviews.
        Returns summary dict.
        """
        repo = self.sync_single_repo(full_name)
        new_commits = self.sync_commits(
            repo, since=since, max_pages=max_commit_pages, fetch_files=fetch_files,
        )
        new_prs = self.sync_pull_requests(
            repo, max_pages=max_pr_pages, sync_reviews=True,
        )
        return {
            "repo": repo.full_name,
            "new_commits": new_commits,
            "new_prs": new_prs,
            "total_developers": self.db.query(Developer).count(),
        }

    # ────────────────────────────────────────────────────────────
    #  Helpers
    # ────────────────────────────────────────────────────────────

    @staticmethod
    def _is_lockfile(filename: str) -> bool:
        import os
        return os.path.basename(filename) in LOCKFILE_NAMES

    @staticmethod
    def _is_generated(filename: str) -> bool:
        return any(filename.endswith(ext) for ext in GENERATED_EXTENSIONS)
