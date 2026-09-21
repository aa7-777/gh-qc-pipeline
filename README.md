# Skill: gh-qc

> GitHub Repo + Milestone 快照质检流水线
>
> 采集固定快照 → 三级自动质检 → 单轮人工质检 → 结构化落盘

---

## 1. 这个 Skill 做什么

对 GitHub 仓库及其 Milestone 做质量把关，输出可复现、可追溯的样本。

```
[采集] -> [准入] -> [Repo QC] -> [Milestone QC] -> [人工 QC] -> [输出]
   |        |          |              |                |
   v        v          v              v                v
 snapshot  拒绝/通过  拒绝/通过      拒绝/通过       通过/拒绝/不确定
```

典型用途：

- 构建代码/任务数据集前的质量过滤
- 评测集样本筛选
- 大规模 Repo + Milestone 的自动分级
- 人工质检的登记与追溯

不负责：

- 代码执行、依赖安装验证
- 深度安全审计
- 数据抓取（采集器需另行接入）

---

## 2. 安装

无第三方依赖，Python >= 3.10。

```bash
cd gh_qc_skill
python --version   # 确认 >= 3.10
```

---

## 3. 快速开始

### 3.1 自动质检

```bash
python -m gh_qc_skill.cli run \
  --input  examples/sample.json \
  --output ./output
```

输出示例：

```json
{
  "sample_id": "octocat/Hello-World@7fd1a60b...#1",
  "state": "milestone_qc_passed",
  "history": [
    {"stage": "admission",     "result": "pass", "reason_codes": []},
    {"stage": "repo_qc",       "result": "pass", "score": 0.9,  "reason_codes": []},
    {"stage": "milestone_qc",  "result": "pass", "score": 0.87, "reason_codes": []}
  ]
}
```

### 3.2 人工质检

```bash
python -m gh_qc_skill.cli human \
  --input  examples/sample.json \
  --output ./output \
  --result pass \
  --operator alice \
  --notes "符合要求"
```

`--result` 可选 `pass` / `reject` / `uncertain`。
`reject` / `uncertain` 必须带 `--reason-codes`，多个用逗号分隔：

```bash
--result reject --reason-codes "BOT_FLOOD,NO_ISSUES"
```

---

## 4. 输入格式

单个样本 JSON：

```json
{
  "repo": {
    "repo_id": "owner/name",
    "repo_url": "https://github.com/owner/name",
    "commit_sha": "abc123...",
    "license": "MIT",
    "stars": 2000,
    "forks": 1500,
    "language": "Python",
    "size_kb": 1024,
    "is_fork": false,
    "is_archived": false,
    "readme": "...",
    "has_tests": true,
    "has_ci": true,
    "has_lockfile": true,
    "last_commit_at": "2026-06-01T00:00:00Z",
    "contributors": 5
  },
  "milestone": {
    "milestone_id": 1,
    "repo_id": "owner/name",
    "title": "v1.0 release",
    "description": "...",
    "state": "open",
    "open_issues": 2,
    "closed_issues": 8,
    "issues": [
      {
        "issue_id": 101,
        "title": "Add login",
        "body": "...",
        "state": "closed",
        "labels": ["feature"],
        "comments_count": 3,
        "author": "alice"
      }
    ]
  }
}
```

字段说明见 `models.py` 中的 `RepoSnapshot` / `Milestone` / `Issue`。

---

## 5. 输出结构

```text
output/
  snapshots/
    <owner>__<name>/
      <commit_sha>/
        meta.json              # 仓库快照元数据
  milestones/
    <owner>__<name>/
      <milestone_id>.json      # Milestone 及 issue 列表
  qc/
    admission.jsonl            # 准入质检结果（逐行追加）
    repo_qc.jsonl              # Repo 质量结果
    milestone_qc.jsonl         # Milestone 质量结果
    human_qc.jsonl             # 人工质检结果
  state/
    <safe_sample_id>.json      # 单样本最终状态（含 history）
```

> `sample_id` 含 `/`、`@`、`#` 等字符，落盘时会做文件名安全化：`/` → `__`，其它非 `[A-Za-z0-9._-]` → `__`。

---

## 6. 状态机

```text
collected
  -> snapshot_fixed
  -> admission_passed / admission_rejected
  -> repo_qc_passed / repo_qc_rejected
  -> milestone_qc_passed / milestone_qc_rejected
  -> human_qc_passed / human_qc_rejected / human_qc_uncertain
  -> done / discarded
```

级联策略：任一阶段 `reject` 立即终止（`Pipeline(stop_on_reject=True)`，默认）。

---

## 7. 质检规则

### 7.1 准入（Admission）

一票否决，任一不满足即 `reject`：

| 原因码 | 触发条件 |
|---|---|
| `NO_REPO_URL` | 缺少 repo URL |
| `NO_COMMIT_SHA` | 缺少 commit |
| `IS_FORK` | 是 fork |
| `IS_ARCHIVED` | 已归档 |
| `NO_LICENSE` | 无 license |
| `EMPTY_REPO` | `size_kb <= 0` |
| `TOO_LARGE` | `size_kb > 500MB` |
| `NO_MILESTONE` | 无 milestone |
| `SENSITIVE_CONTENT` | README 命中 `AKIA` / `BEGIN RSA PRIVATE KEY` / `ghp_` / `sk-` |

### 7.2 Repo 质量（Repo QC）

加权求和，阈值 **0.6**。

| 维度 | 权重 | 说明 |
|---|---|---|
| recency | 0.15 | 最近提交时间 |
| community | 0.10 | stars / forks / contributors |
| docs | 0.15 | README 长度 |
| engineering | 0.20 | tests / CI / lockfile |
| content | 0.20 | 非 awesome/list/教程 |
| security | 0.10 | 无明显敏感内容 |
| reproducibility | 0.10 | 有 lockfile 优先 |

硬性失败项：`LOW_QUALITY_CONTENT`、`SECURITY_RISK`。
低于阈值：`LOW_SCORE`。

### 7.3 Milestone 质量（Milestone QC）

加权求和，阈值 **0.6**。

| 维度 | 权重 | 说明 |
|---|---|---|
| title | 0.15 | 非默认模板标题 |
| description | 0.15 | 描述长度 |
| issue_count | 0.15 | 3~100 为佳 |
| issue_quality | 0.20 | 有 body + 有 labels 的占比 |
| completion | 0.10 | 完成率合理区间 |
| consistency | 0.15 | 标题与描述一致 |
| non_bot | 0.10 | 非 bot 批量创建 |

硬性失败项：`NO_ISSUES`、`BOT_FLOOD`。
低于阈值：`LOW_SCORE`。

### 7.4 人工质检（Human QC）

单轮，审核员基于 checklist 判定：

- 标题与描述是否清晰表达目标
- issue 内容是否真实、非灌水
- milestone 与 repo 主题是否一致
- 是否包含敏感或违规内容
- 是否适合作为任务/样本

输出 `pass` / `reject` / `uncertain`，`reject` / `uncertain` 必须填原因码。

---

## 8. 项目结构

```text
gh_qc_skill/
├── README.md
├── PIPELINE.md                # 设计文档
├── examples/
│   └── sample.json            # 示例样本
└── gh_qc_skill/
    ├── __init__.py
    ├── SKILL.md               # 本文件
    ├── cli.py                 # 命令行入口
    ├── models.py              # 数据模型
    ├── pipeline.py            # 级联编排
    ├── human_qc.py            # 人工质检
    ├── storage.py             # 落盘
    └── rules/
        ├── __init__.py
        ├── admission.py       # 准入规则
        ├── repo_qc.py         # Repo 质量规则
        └── milestone_qc.py    # Milestone 质量规则
```

---

## 9. 扩展点

### 9.1 新增/替换规则

每个规则函数返回一个 `QCResult`，在 `pipeline.py` 中注册即可。

```python
# rules/my_rule.py
from ..models import RepoSnapshot, QCResult

def check_my_rule(repo: RepoSnapshot) -> QCResult:
    reasons = []
    if some_condition:
        reasons.append("MY_REASON")
    return QCResult(
        stage="my_rule",
        subject_type="repo",
        subject_id=repo.repo_id,
        result="pass" if not reasons else "reject",
        reason_codes=reasons,
        rule_version="v1",
    )
```

```python
# pipeline.py
stages = [
    ("admission", lambda: check_admission(sample.repo, sample.milestone)),
    ("my_rule",   lambda: check_my_rule(sample.repo)),   # 新增
    ("repo_qc",   lambda: check_repo_qc(sample.repo)),
    ("milestone_qc", lambda: check_milestone_qc(sample.milestone)),
]
```

### 9.2 调整级联策略

```python
pipeline = Pipeline(stop_on_reject=False)  # 不中断，跑完所有阶段
```

### 9.3 替换人工 checklist

编辑 `human_qc.py` 中的 `HUMAN_CHECKLIST`。

### 9.4 引入 LLM 辅助

在 `rules/` 下新增一个 LLM 规则模块，把打分结果映射到 `QCResult` 即可。

### 9.5 接入真实采集器

当前输入是本地 JSON。接入 GitHub API 采集器时，只需产出相同结构的 JSON，再调 `cli run` 即可。

---

## 10. 常见问题

### Q1: `FileNotFoundError: output/state/owner/name@sha#1.json`

`sample_id` 含 `/`，被当路径分隔符。已在 `storage.py` 中通过 `_safe()` 修复。
若仍出现，检查 `storage.py` 是否包含：

```python
import re

def _safe(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "__", name)
```

以及 state 落盘处使用 `_safe(sample.sample_id)`。

### Q2: 输出目录被覆盖怎么办？

`qc/*.jsonl` 是追加写；`state/*.json` 和 `snapshots/.../meta.json` 是覆盖写。
如需保留历史，在 `--output` 里带时间戳：

```bash
--output ./output/$(date +%Y%m%d_%H%M%S)
```

### Q3: 批量样本怎么跑？

当前 CLI 一次一个样本。批量可自行循环：

```bash
for f in samples/*.json; do
  python -m gh_qc_skill.cli run --input "$f" --output ./output
done
```

或写一个 Python 脚本调用 `Pipeline` + `Storage`。

### Q4: 为什么准入把 fork 也拒了？

默认策略偏严，避免镜像/派生仓库污染数据集。
如业务需要，编辑 `rules/admission.py` 去掉 `IS_FORK` 检查。

### Q5: 阈值想调怎么办？

- Repo QC: `rules/repo_qc.py` 里的 `THRESHOLD`
- Milestone QC: `rules/milestone_qc.py` 里的 `THRESHOLD`

维度权重是 `dims` 字典里的第二个元素。

---

## 11. 指标建议

生产使用时建议采集：

- 采集成功率、快照完整率
- 准入 / Repo QC / Milestone QC 通过率
- 人工通过率、人工与自动一致率
- 各原因码分布
- 平均处理时延、单样本成本
- 误杀率、漏杀率、人工不确定率

---

## 12. 版本

| 组件 | 版本 |
|---|---|
| pipeline | v1 |
| rules | v1 |
| schema | v1 |

---

## 13. 相关文档

- `README.md`：快速开始
- `PIPELINE.md`：设计文档与规则细节


## 14. 自动生成样本 (gen_sample.py)

`gen_sample.py` 用于从当前 git 仓库自动生成质检输入样本 `examples/sample.json`，免去手动填写 `repo_id`、`commit_sha`、`readme` 等重复字段。

### 用途

- 读取当前仓库的 `git remote`、`HEAD`、`README.md`
- 生成符合 `gh_qc_skill` 输入格式的 `examples/sample.json`
- 生成后可直接运行自动质检

### 用法

```bash
# 进入项目根目录
cd gh_qc_skill

# 自动从 git 读取（需要当前目录是 git 仓库且配置了 origin）
python3 gen_sample.py

# 或者手动指定参数
python3 gen_sample.py --owner 你的用户名 --repo 你的仓库名 --sha <commit_sha>
