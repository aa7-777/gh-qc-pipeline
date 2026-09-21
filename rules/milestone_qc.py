from __future__ import annotations

from ..models import Milestone, QCResult

RULE_VERSION = "v1"
THRESHOLD = 0.6

DEFAULT_TITLES = {"", "milestone", "v1", "todo", "backlog"}
BOT_AUTHORS = {"dependabot", "renovate", "github-actions"}


def _title_score(ms: Milestone) -> float:
    t = (ms.title or "").strip().lower()
    if t in DEFAULT_TITLES:
        return 0.2
    if len(t) < 3:
        return 0.4
    return 1.0


def _desc_score(ms: Milestone) -> float:
    d = (ms.description or "").strip()
    if not d:
        return 0.0
    if len(d) >= 200:
        return 1.0
    if len(d) >= 50:
        return 0.7
    return 0.4


def _issue_count_score(ms: Milestone) -> float:
    n = ms.total_issues
    if n == 0:
        return 0.0
    if 3 <= n <= 100:
        return 1.0
    if n < 3:
        return 0.5
    return 0.4


def _issue_quality_score(ms: Milestone) -> float:
    if not ms.issues:
        return 0.0
    good = 0
    for i in ms.issues:
        if i.body and len(i.body) >= 30 and i.labels:
            good += 1
    return good / len(ms.issues)


def _completion_score(ms: Milestone) -> float:
    r = ms.completion_rate
    if 0.2 <= r <= 0.95:
        return 1.0
    if r == 0.0 and ms.state == "open":
        return 0.5
    if r == 1.0:
        return 0.8
    return 0.4


def _consistency_score(ms: Milestone) -> float:
    if ms.title and ms.description:
        return 1.0
    return 0.5


def _non_bot_score(ms: Milestone) -> float:
    if not ms.issues:
        return 0.5
    bot = sum(1 for i in ms.issues if i.is_bot or (i.author or "") in BOT_AUTHORS)
    ratio = bot / len(ms.issues)
    if ratio >= 0.8:
        return 0.0
    if ratio >= 0.5:
        return 0.4
    return 1.0


def check_milestone_qc(ms: Milestone) -> QCResult:
    dims = {
        "title": (_title_score(ms), 0.15),
        "description": (_desc_score(ms), 0.15),
        "issue_count": (_issue_count_score(ms), 0.15),
        "issue_quality": (_issue_quality_score(ms), 0.20),
        "completion": (_completion_score(ms), 0.10),
        "consistency": (_consistency_score(ms), 0.15),
        "non_bot": (_non_bot_score(ms), 0.10),
    }
    score = sum(v * w for v, w in dims.values())

    reasons: list[str] = []
    if dims["issue_count"][0] == 0.0:
        reasons.append("NO_ISSUES")
    if dims["non_bot"][0] == 0.0:
        reasons.append("BOT_FLOOD")
    if score < THRESHOLD:
        reasons.append("LOW_SCORE")

    result = "pass" if not reasons else "reject"
    return QCResult(
        stage="milestone_qc",
        subject_type="milestone",
        subject_id=f"{ms.repo_id}#{ms.milestone_id}",
        result=result,
        reason_codes=reasons,
        score=round(score, 4),
        evidence={k: round(v, 4) for k, (v, _) in dims.items()},
        rule_version=RULE_VERSION,
    )
