from __future__ import annotations

from .models import Sample, QCResult
from .rules.admission import check_admission
from .rules.repo_qc import check_repo_qc
from .rules.milestone_qc import check_milestone_qc

STAGE_TO_STATE = {
    "admission": ("admission_passed", "admission_rejected"),
    "repo_qc": ("repo_qc_passed", "repo_qc_rejected"),
    "milestone_qc": ("milestone_qc_passed", "milestone_qc_rejected"),
}


class Pipeline:
    def __init__(self, stop_on_reject: bool = True):
        self.stop_on_reject = stop_on_reject

    def run_auto(self, sample: Sample) -> Sample:
        sample.state = "snapshot_fixed"

        stages = [
            ("admission", lambda: check_admission(sample.repo, sample.milestone)),
            ("repo_qc", lambda: check_repo_qc(sample.repo)),
            ("milestone_qc", lambda: check_milestone_qc(sample.milestone)),
        ]

        for stage_name, fn in stages:
            res: QCResult = fn()
            sample.history.append(res)
            passed_state, rejected_state = STAGE_TO_STATE[stage_name]
            if res.result == "pass":
                sample.state = passed_state
            else:
                sample.state = rejected_state
                if self.stop_on_reject:
                    return sample

        return sample

    @staticmethod
    def finalize_human(sample: Sample, res: QCResult) -> Sample:
        sample.history.append(res)
        if res.result == "pass":
            sample.state = "human_qc_passed"
        elif res.result == "reject":
            sample.state = "human_qc_rejected"
        else:
            sample.state = "human_qc_uncertain"
        return sample

    @staticmethod
    def is_done(sample: Sample) -> bool:
        return sample.state in {
            "human_qc_passed", "human_qc_rejected", "human_qc_uncertain"
        }
