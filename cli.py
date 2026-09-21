from __future__ import annotations

import argparse
import json
from pathlib import Path

from .models import RepoSnapshot, Milestone, Issue, Sample
from .pipeline import Pipeline
from .storage import Storage
from .human_qc import human_review


def _load_sample(path: str) -> Sample:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    repo = RepoSnapshot(**data["repo"])
    ms_data = dict(data["milestone"])
    issues = [Issue(**i) for i in ms_data.pop("issues", [])]
    ms = Milestone(issues=issues, **ms_data)
    return Sample.make(repo, ms)


def cmd_run(args):
    sample = _load_sample(args.input)
    pipeline = Pipeline()
    pipeline.run_auto(sample)

    storage = Storage(args.output)
    storage.save_sample(sample)
    for h in sample.history:
        storage.append_qc(h)

    print(json.dumps({
        "sample_id": sample.sample_id,
        "state": sample.state,
        "history": [h.to_dict() for h in sample.history],
    }, ensure_ascii=False, indent=2))


def cmd_human(args):
    sample = _load_sample(args.input)
    res = human_review(
        sample,
        result=args.result,
        reason_codes=args.reason_codes.split(",") if args.reason_codes else [],
        operator=args.operator,
        notes=args.notes or "",
    )
    Pipeline.finalize_human(sample, res)

    storage = Storage(args.output)
    storage.save_sample(sample)
    storage.append_qc(res)

    print(json.dumps(sample.to_dict(), ensure_ascii=False, indent=2))


def main():
    p = argparse.ArgumentParser(prog="gh-qc")
    sub = p.add_subparsers(dest="cmd", required=True)

    r = sub.add_parser("run", help="运行自动质检")
    r.add_argument("--input", required=True)
    r.add_argument("--output", required=True)
    r.set_defaults(func=cmd_run)

    h = sub.add_parser("human", help="提交人工质检结果")
    h.add_argument("--input", required=True)
    h.add_argument("--output", required=True)
    h.add_argument("--result", required=True,
                   choices=["pass", "reject", "uncertain"])
    h.add_argument("--reason-codes", default="")
    h.add_argument("--operator", required=True)
    h.add_argument("--notes", default="")
    h.set_defaults(func=cmd_human)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
