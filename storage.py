from __future__ import annotations

import json
from pathlib import Path

from .models import Sample, QCResult


class Storage:
    def __init__(self, root):
        self.root = Path(root)
        (self.root / "snapshots").mkdir(parents=True, exist_ok=True)
        (self.root / "milestones").mkdir(parents=True, exist_ok=True)
        (self.root / "qc").mkdir(parents=True, exist_ok=True)
        (self.root / "state").mkdir(parents=True, exist_ok=True)

    def save_sample(self, sample: Sample) -> None:

        import re

        def _safe(name: str) -> str:
            """把 sample_id 转成安全文件名。"""
            return re.sub(r"[^A-Za-z0-9._-]+", "__", name)
        
        owner, name = sample.repo.repo_id.split("/", 1)
        d = self.root / "snapshots" / f"{owner}__{name}" / sample.repo.commit_sha
        d.mkdir(parents=True, exist_ok=True)
        (d / "meta.json").write_text(
            json.dumps(sample.repo.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        mdir = self.root / "milestones" / f"{owner}__{name}"
        mdir.mkdir(parents=True, exist_ok=True)
        (mdir / f"{sample.milestone.milestone_id}.json").write_text(
            json.dumps(sample.milestone.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        (self.root / "state" / f"{_safe(sample.sample_id)}.json").write_text(
            json.dumps(sample.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def append_qc(self, res: QCResult) -> None:
        path = self.root / "qc" / f"{res.stage}.jsonl"
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(res.to_dict(), ensure_ascii=False) + "\n")
