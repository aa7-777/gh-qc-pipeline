# Skill: gh-qc

GitHub Repo + Milestone 快照质检流水线。

## 能力

- 准入质检（一票否决）
- Repo 质量评分
- Milestone 质量评分
- 人工质检登记
- 级联状态机编排
- 结构化落盘

## 使用

    python -m gh_qc_skill.cli run --input examples/sample.json --output ./output
    python -m gh_qc_skill.cli human --input examples/sample.json --output ./output --result pass --operator alice --notes "ok"

## 扩展点

- rules/*.py      新增或替换规则
- pipeline.py     调整级联顺序
- human_qc.py     替换 checklist 或引入 LLM 辅助
