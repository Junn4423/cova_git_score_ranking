"""
SQLAlchemy ORM models matching the MySQL schema.
"""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, Text, DateTime, Date,
    Boolean, Enum, ForeignKey, Index, JSON, DECIMAL,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


# ── developers ──────────────────────────────────────────────
class Developer(Base):
    __tablename__ = "developers"

    id = Column(Integer, primary_key=True, autoincrement=True)
    github_login = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(200))
    email = Column(String(255))
    avatar_url = Column(String(500))
    is_bot = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    aliases = relationship("DeveloperAlias", back_populates="developer", cascade="all, delete-orphan")
    team_memberships = relationship("TeamMember", back_populates="developer", cascade="all, delete-orphan")
    commits = relationship("Commit", foreign_keys="Commit.author_id", back_populates="author")
    work_items = relationship("WorkItem", back_populates="developer")
    score_snapshots = relationship("ScoreSnapshot", back_populates="developer")


class DeveloperAlias(Base):
    __tablename__ = "developer_aliases"

    id = Column(Integer, primary_key=True, autoincrement=True)
    developer_id = Column(Integer, ForeignKey("developers.id", ondelete="CASCADE"), nullable=False)
    alias_type = Column(Enum("email", "github_login", "name"), nullable=False)
    alias_value = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    developer = relationship("Developer", back_populates="aliases")

    __table_args__ = (
        Index("uq_alias", "alias_type", "alias_value", unique=True),
    )


# ── teams ───────────────────────────────────────────────────
class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(200), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")


class TeamMember(Base):
    __tablename__ = "team_members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    team_id = Column(Integer, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    developer_id = Column(Integer, ForeignKey("developers.id", ondelete="CASCADE"), nullable=False)
    role = Column(String(50), default="member")
    joined_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    team = relationship("Team", back_populates="members")
    developer = relationship("Developer", back_populates="team_memberships")

    __table_args__ = (
        Index("uq_team_dev", "team_id", "developer_id", unique=True),
    )


# ── repositories ────────────────────────────────────────────
class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    github_id = Column(BigInteger, unique=True, nullable=False)
    full_name = Column(String(300), unique=True, nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    default_branch = Column(String(100), default="main")
    is_tracked = Column(Boolean, default=True, nullable=False)
    exclude_from_ranking = Column(Boolean, default=False, nullable=False)
    last_synced_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    commits = relationship("Commit", back_populates="repository")
    pull_requests = relationship("PullRequest", back_populates="repository")


# ── commits ─────────────────────────────────────────────────
class Commit(Base):
    __tablename__ = "commits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    sha = Column(String(40), nullable=False)
    author_id = Column(Integer, ForeignKey("developers.id", ondelete="SET NULL"))
    committer_id = Column(Integer, ForeignKey("developers.id", ondelete="SET NULL"))
    message = Column(Text)
    committed_at = Column(DateTime)
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    total_changes = Column(Integer, default=0)
    parent_count = Column(Integer, default=0)
    branch = Column(String(200))
    is_merge = Column(Boolean, default=False)
    raw_author_email = Column(String(255))
    raw_author_name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    repository = relationship("Repository", back_populates="commits")
    author = relationship("Developer", foreign_keys=[author_id], back_populates="commits")
    committer = relationship("Developer", foreign_keys=[committer_id])
    files = relationship("CommitFile", back_populates="commit", cascade="all, delete-orphan")

    __table_args__ = (
        Index("uq_repo_sha", "repo_id", "sha", unique=True),
        Index("idx_commit_author", "author_id"),
        Index("idx_commit_repo_time", "repo_id", "committed_at"),
        Index("idx_commit_time", "committed_at"),
    )


# ── commit_files ────────────────────────────────────────────
class CommitFile(Base):
    __tablename__ = "commit_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    commit_id = Column(Integer, ForeignKey("commits.id", ondelete="CASCADE"), nullable=False)
    filename = Column(String(500), nullable=False)
    status = Column(String(20))
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    changes = Column(Integer, default=0)
    patch = Column(Text)
    is_generated = Column(Boolean, default=False)
    is_lockfile = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    commit = relationship("Commit", back_populates="files")

    __table_args__ = (
        Index("idx_cfile_commit", "commit_id"),
    )


# ── pull_requests ───────────────────────────────────────────
class PullRequest(Base):
    __tablename__ = "pull_requests"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False)
    github_pr_number = Column(Integer, nullable=False)
    title = Column(String(500))
    body = Column(Text)
    state = Column(String(20))
    author_id = Column(Integer, ForeignKey("developers.id", ondelete="SET NULL"))
    merged = Column(Boolean, default=False)
    merged_at = Column(DateTime)
    closed_at = Column(DateTime)
    head_branch = Column(String(200))
    base_branch = Column(String(200))
    additions = Column(Integer, default=0)
    deletions = Column(Integer, default=0)
    changed_files = Column(Integer, default=0)
    review_comments = Column(Integer, default=0)
    github_created_at = Column(DateTime)
    github_updated_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    repository = relationship("Repository", back_populates="pull_requests")
    author = relationship("Developer", foreign_keys=[author_id])
    pr_commits = relationship("PullRequestCommit", back_populates="pull_request", cascade="all, delete-orphan")
    reviews = relationship("Review", back_populates="pull_request", cascade="all, delete-orphan")

    __table_args__ = (
        Index("uq_pr_repo_number", "repo_id", "github_pr_number", unique=True),
        Index("idx_pr_author", "author_id"),
        Index("idx_pr_repo_state", "repo_id", "state"),
    )


# ── pull_request_commits ────────────────────────────────────
class PullRequestCommit(Base):
    __tablename__ = "pull_request_commits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pull_request_id = Column(Integer, ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False)
    commit_id = Column(Integer, ForeignKey("commits.id", ondelete="CASCADE"), nullable=False)

    pull_request = relationship("PullRequest", back_populates="pr_commits")
    commit = relationship("Commit")

    __table_args__ = (
        Index("uq_pr_commit", "pull_request_id", "commit_id", unique=True),
    )


# ── reviews ─────────────────────────────────────────────────
class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pull_request_id = Column(Integer, ForeignKey("pull_requests.id", ondelete="CASCADE"), nullable=False)
    reviewer_id = Column(Integer, ForeignKey("developers.id", ondelete="SET NULL"))
    github_review_id = Column(BigInteger)
    state = Column(String(30))
    body = Column(Text)
    submitted_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    pull_request = relationship("PullRequest", back_populates="reviews")
    reviewer = relationship("Developer")

    __table_args__ = (
        Index("idx_review_pr", "pull_request_id"),
        Index("idx_review_reviewer", "reviewer_id"),
    )


# ── work_items ──────────────────────────────────────────────
class WorkItem(Base):
    __tablename__ = "work_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    developer_id = Column(Integer, ForeignKey("developers.id", ondelete="CASCADE"), nullable=False)
    repo_id = Column(Integer, ForeignKey("repositories.id", ondelete="SET NULL"))
    pull_request_id = Column(Integer, ForeignKey("pull_requests.id", ondelete="SET NULL"))
    title = Column(String(500))
    grouping_method = Column(String(50))
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    commit_count = Column(Integer, default=0)
    total_additions = Column(Integer, default=0)
    total_deletions = Column(Integer, default=0)
    file_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    developer = relationship("Developer", back_populates="work_items")
    repository = relationship("Repository")
    pull_request = relationship("PullRequest")
    wi_commits = relationship("WorkItemCommit", back_populates="work_item", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_wi_dev", "developer_id"),
        Index("idx_wi_repo", "repo_id"),
        Index("idx_wi_time", "start_time", "end_time"),
    )


# ── work_item_commits ──────────────────────────────────────
class WorkItemCommit(Base):
    __tablename__ = "work_item_commits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    work_item_id = Column(Integer, ForeignKey("work_items.id", ondelete="CASCADE"), nullable=False)
    commit_id = Column(Integer, ForeignKey("commits.id", ondelete="CASCADE"), nullable=False)

    work_item = relationship("WorkItem", back_populates="wi_commits")
    commit = relationship("Commit")

    __table_args__ = (
        Index("uq_wi_commit", "work_item_id", "commit_id", unique=True),
    )


# ── ai_commit_analysis ─────────────────────────────────────
class AICommitAnalysis(Base):
    __tablename__ = "ai_commit_analysis"

    id = Column(Integer, primary_key=True, autoincrement=True)
    target_type = Column(Enum("commit", "pull_request", "work_item"), nullable=False)
    target_id = Column(Integer, nullable=False)
    change_type = Column(String(50))
    summary = Column(Text)
    complexity_score = Column(Integer)
    risk_score = Column(Integer)
    message_alignment_score = Column(Integer)
    test_presence = Column(Boolean)
    confidence = Column(DECIMAL(3, 2))
    notes = Column(JSON)
    model_version = Column(String(100))
    prompt_version = Column(String(50))
    schema_version = Column(String(20))
    raw_response = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_ai_target", "target_type", "target_id"),
        Index("idx_ai_change_type", "change_type"),
    )


# ── score_snapshots ─────────────────────────────────────────
class ScoreSnapshot(Base):
    __tablename__ = "score_snapshots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    developer_id = Column(Integer, ForeignKey("developers.id", ondelete="CASCADE"), nullable=False)
    period_start = Column(Date, nullable=False)
    period_end = Column(Date, nullable=False)
    activity_score = Column(DECIMAL(6, 2))
    quality_score = Column(DECIMAL(6, 2))
    impact_score = Column(DECIMAL(6, 2))
    final_score = Column(DECIMAL(6, 2))
    confidence_score = Column(DECIMAL(3, 2))
    top_positive_reasons = Column(JSON)
    top_negative_reasons = Column(JSON)
    evidence_links = Column(JSON)
    calculated_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    developer = relationship("Developer", back_populates="score_snapshots")
    breakdowns = relationship("ScoreBreakdown", back_populates="snapshot", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_score_dev", "developer_id"),
        Index("idx_score_period", "period_start", "period_end"),
    )


# ── score_breakdowns ───────────────────────────────────────
class ScoreBreakdown(Base):
    __tablename__ = "score_breakdowns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    snapshot_id = Column(Integer, ForeignKey("score_snapshots.id", ondelete="CASCADE"), nullable=False)
    component = Column(String(100), nullable=False)
    raw_value = Column(DECIMAL(10, 4))
    weight = Column(DECIMAL(5, 4))
    weighted_value = Column(DECIMAL(10, 4))
    details = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    snapshot = relationship("ScoreSnapshot", back_populates="breakdowns")

    __table_args__ = (
        Index("idx_breakdown_snapshot", "snapshot_id"),
    )


# ── app_configs ─────────────────────────────────────────────
class AppConfig(Base):
    __tablename__ = "app_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    config_key = Column(String(200), unique=True, nullable=False)
    config_value = Column(JSON, nullable=False)
    description = Column(Text)
    updated_by = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


# ── job_queue ───────────────────────────────────────────────
class JobQueue(Base):
    __tablename__ = "job_queue"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_type = Column(String(100), nullable=False)
    payload = Column(JSON)
    status = Column(
        Enum("pending", "running", "done", "failed", "retry"),
        default="pending",
        nullable=False,
    )
    priority = Column(Integer, default=0)
    attempts = Column(Integer, default=0)
    max_attempts = Column(Integer, default=3)
    error_message = Column(Text)
    scheduled_at = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_job_status", "status"),
        Index("idx_job_type_status", "job_type", "status"),
        Index("idx_job_scheduled", "scheduled_at"),
    )


# ── audit_logs ──────────────────────────────────────────────
class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_id = Column(Integer)
    action = Column(String(100), nullable=False)
    target_type = Column(String(100))
    target_id = Column(Integer)
    details = Column(JSON)
    ip_address = Column(String(45))
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("idx_audit_actor", "actor_id"),
        Index("idx_audit_action", "action"),
        Index("idx_audit_time", "created_at"),
    )


# ── users (auth) ───────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum("admin", "lead", "developer"), default="developer", nullable=False)
    developer_id = Column(Integer, ForeignKey("developers.id", ondelete="SET NULL"))
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    developer = relationship("Developer")
