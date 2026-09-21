from __future__ import annotations

from ..models import RepoSnapshot, Milestone, QCResult

RULE_VERSION = "v1"

SENSITIVE_PATTERNS = [
    "AKIA", "BEGIN RSA PRIVATE KEY", "ghp_", "sk-",
]

MAX_SIZE_KB = 500 * 1024


def check_admission(repo: RepoSnapshot, milestone: Milestone) -> QCResult:
    reasons: list[str] = []
    evidence: dict = {}

    if not repo.repo_url:
        reasons.append("NO_REPO_URL")
    if not repo.commit_sha:
        reasons.append("NO_COMMIT_SHA")
    if repo.is_fork:
        reasons.append("IS_FORK")
    if repo.is_archived:
        reasons.append("IS_ARCHIVED")
    if not repo.license:
        reasons.append("NO_LICENSE")
    if repo.size_kb <= 0:
        reasons.append("EMPTY_REPO")
    elif repo.size_kb > MAX_SIZE_KB:
        reasons.append("TOO_LARGE")
        evidence["size_kb"] = repo.size_kb
    if not milestone:
        reasons.append("NO_MILESTONE")

    text = (repo.readme or "")
    for p in SENSITIVE_PATTERNS:
        if p in text:
            reasons.append("SENSITIVE_CONTENT")
            evidence["matched"] = p
            break

    result = "pass" if not reasons else "reject"
    return QCResult(
        stage="admission",
        subject_type="repo",
        subject_id=f"{repo.repo_id}@{repo.commit_sha}",
        result=result,
        reason_codes=reasons,
        evidence=evidence,
        rule_version=RULE_VERSION,
    )
