from __future__ import annotations

from datetime import datetime, timezone

from ..models import RepoSnapshot, QCResult

RULE_VERSION = "v1"
THRESHOLD = 0.6

LOW_QUALITY_KEYWORDS = [
    "awesome-", "awesome_", "-list", "collection of",
    "tutorial", "cheatsheet", "interview-questions",
]


def _recency_score(last_commit_at):
    if not last_commit_at:
        return 0.0
    try:
        t = datetime.fromisoformat(last_commit_at.replace("Z", "+00:00"))
    except Exception:
        return 0.0
    days = (datetime.now(timezone.utc) - t).days
    if days <= 90:
        return 1.0
    if days <= 365:
        return 0.6
    if days <= 365 * 3:
        return 0.3
    return 0.0


def _community_score(repo: RepoSnapshot) -> float:
    s = 0.0
    if repo.stars >= 100:
        s += 0.5
    elif repo.stars >= 20:
        s += 0.3
    if repo.forks >= 20:
        s += 0.3
    elif repo.forks >= 5:
        s += 0.15
    if repo.contributors >= 3:
        s += 0.2
    return min(s, 1.0)


def _docs_score(repo: RepoSnapshot) -> float:
    if not repo.readme:
        return 0.0
    length = len(repo.readme)
    if length >= 2000:
        return 1.0
    if length >= 800:
        return 0.7
    if length >= 200:
        return 0.4
    return 0.2


def _engineering_score(repo: RepoSnapshot) -> float:
    s = 0.0
    if repo.has_tests:
        s += 0.5
    if repo.has_ci:
        s += 0.3
    if repo.has_lockfile:
        s += 0.2
    return min(s, 1.0)


def _content_score(repo: RepoSnapshot) -> float:
    name = repo.repo_id.lower()
    if any(k in name for k in LOW_QUALITY_KEYWORDS):
        return 0.0
    return 1.0


def _security_score(repo: RepoSnapshot) -> float:
    if "BEGIN RSA PRIVATE KEY" in (repo.readme or ""):
        return 0.0
    return 1.0


def _repro_score(repo: RepoSnapshot) -> float:
    if repo.has_lockfile:
        return 1.0
    if repo.has_tests:
        return 0.6
    return 0.3


def check_repo_qc(repo: RepoSnapshot) -> QCResult:
    dims = {
        "recency": (_recency_score(repo.last_commit_at), 0.15),
        "community": (_community_score(repo), 0.10),
        "docs": (_docs_score(repo), 0.15),
        "engineering": (_engineering_score(repo), 0.20),
        "content": (_content_score(repo), 0.20),
        "security": (_security_score(repo), 0.10),
        "reproducibility": (_repro_score(repo), 0.10),
    }
    score = sum(v * w for v, w in dims.values())

    reasons: list[str] = []
    if dims["content"][0] == 0.0:
        reasons.append("LOW_QUALITY_CONTENT")
    if dims["security"][0] == 0.0:
        reasons.append("SECURITY_RISK")
    if score < THRESHOLD:
        reasons.append("LOW_SCORE")

    result = "pass" if not reasons else "reject"
    return QCResult(
        stage="repo_qc",
        subject_type="repo",
        subject_id=f"{repo.repo_id}@{repo.commit_sha}",
        result=result,
        reason_codes=reasons,
        score=round(score, 4),
        evidence={k: round(v, 4) for k, (v, _) in dims.items()},
        rule_version=RULE_VERSION,
    )
