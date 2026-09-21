from __future__ import annotations

from .models import Sample, QCResult

VALID_RESULTS = {"pass", "reject", "uncertain"}

HUMAN_CHECKLIST = [
    "标题与描述是否清晰表达目标",
    "issue 内容是否真实、非灌水",
    "milestone 与 repo 主题是否一致",
    "是否包含敏感或违规内容",
    "是否适合作为任务/样本",
]


def human_review(sample: Sample, result: str, reason_codes: list[str],
                 operator: str, notes: str = "") -> QCResult:
    if result not in VALID_RESULTS:
        raise ValueError(f"invalid human result: {result}")
    if result != "pass" and not reason_codes:
        raise ValueError("reject/uncertain 必须填写 reason_codes")

    return QCResult(
        stage="human_qc",
        subject_type="milestone",
        subject_id=f"{sample.repo.repo_id}#{sample.milestone.milestone_id}",
        result=result,
        reason_codes=reason_codes,
        evidence={"notes": notes, "checklist": HUMAN_CHECKLIST},
        rule_version="v1",
        operator=f"human:{operator}",
    )
