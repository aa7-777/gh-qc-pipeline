from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Optional
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class RepoSnapshot:
    repo_id: str
    repo_url: str
    commit_sha: str
    default_branch: str = "main"
    snapshot_at: str = field(default_factory=now_iso)
    archive_hash: Optional[str] = None
    license: Optional[str] = None
    stars: int = 0
    forks: int = 0
    language: Optional[str] = None
    size_kb: int = 0
    is_fork: bool = False
    is_archived: bool = False
    readme: str = ""
    files_index: list[str] = field(default_factory=list)
    has_tests: bool = False
    has_ci: bool = False
    has_lockfile: bool = False
    last_commit_at: Optional[str] = None
    contributors: int = 0
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Issue:
    issue_id: int
    title: str
    body: str = ""
    state: str = "open"
    labels: list[str] = field(default_factory=list)
    comments_count: int = 0
    author: Optional[str] = None
    is_bot: bool = False


@dataclass
class Milestone:
    milestone_id: int
    repo_id: str
    title: str
    description: str = ""
    state: str = "open"
    created_at: Optional[str] = None
    due_on: Optional[str] = None
    closed_at: Optional[str] = None
    open_issues: int = 0
    closed_issues: int = 0
    issues: list[Issue] = field(default_factory=list)

    @property
    def total_issues(self) -> int:
        return self.open_issues + self.closed_issues

    @property
    def completion_rate(self) -> float:
        if self.total_issues == 0:
            return 0.0
        return self.closed_issues / self.total_issues

    def to_dict(self) -> dict:
        d = asdict(self)
        d["issues"] = [asdict(i) for i in self.issues]
        return d


@dataclass
class QCResult:
    stage: str
    subject_type: str
    subject_id: str
    result: str
    reason_codes: list[str] = field(default_factory=list)
    score: Optional[float] = None
    evidence: dict[str, Any] = field(default_factory=dict)
    rule_version: str = "v1"
    operator: str = "auto"
    created_at: str = field(default_factory=now_iso)
    result_id: str = field(default_factory=lambda: uuid.uuid4().hex)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Sample:
    sample_id: str
    repo: RepoSnapshot
    milestone: Milestone
    state: str = "collected"
    history: list[QCResult] = field(default_factory=list)

    @staticmethod
    def make(repo: RepoSnapshot, milestone: Milestone) -> "Sample":
        sid = f"{repo.repo_id}@{repo.commit_sha}#{milestone.milestone_id}"
        return Sample(sample_id=sid, repo=repo, milestone=milestone)

    def to_dict(self) -> dict:
        return {
            "sample_id": self.sample_id,
            "state": self.state,
            "repo": self.repo.to_dict(),
            "milestone": self.milestone.to_dict(),
            "history": [h.to_dict() for h in self.history],
        }
