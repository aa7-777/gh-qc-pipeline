# gh-qc

GitHub Repo + Milestone 快照质检流水线。

采集固定快照 → 三级自动质检 → 单轮人工质检 → 结构化落盘。

## 特性

- **固定快照**：基于 commit SHA，可复现
- **三级自动质检**：准入 / Repo 质量 / Milestone 质量
- **单轮人工质检**：pass / reject / uncertain，带原因码
- **结构化落盘**：所有结果可追溯
- **两种输入模式**：本地 git 生成 / GitHub HTTP API 直连

## 环境要求

- Python >= 3.10
- 无强制第三方依赖（HTTP 模式推荐装 `certifi`）

## 安装

```bash
git clone https://github.com/aa7-777/gh-qc-pipeline.git
cd gh-qc-pipeline
```

可选（用于修复 macOS 上 HTTPS 证书问题）：

```bash
python3 -m pip install --user certifi
```

## 快速开始

### 1. 生成质检样本

**方式 A：GitHub HTTP 直连（推荐）**

```bash
python3 gen_sample.py --repo-url https://github.com/aa7-777/gh-qc-pipeline
```

**方式 B：从本地 git 读取**

```bash
python3 gen_sample.py --owner aa7-777 --repo gh-qc-pipeline --sha <commit_sha>
```

生成结果写入 `examples/sample.json`。

### 2. 运行自动质检

```bash
python3 -m gh_qc_skill.cli run --input examples/sample.json --output ./output
```

输出示例：

```json
{
  "sample_id": "aa7-777/gh-qc-pipeline@abc123#1",
  "state": "milestone_qc_passed",
  "history": [
    {"stage": "admission",    "result": "pass", "reason_codes": []},
    {"stage": "repo_qc",      "result": "pass", "score": 0.9},
    {"stage": "milestone_qc", "result": "pass", "score": 0.87}
  ]
}
```

### 3. 提交人工质检

```bash
python3 -m gh_qc_skill.cli human \
  --input examples/sample.json \
  --output ./output \
  --result pass \
  --operator alice \
  --notes "符合要求"
```

`--result` 可选 `pass` / `reject` / `uncertain`。  
`reject` / `uncertain` 必须带 `--reason-codes`，多个用逗号分隔。

## gen_sample.py 用法

```bash
python3 gen_sample.py --repo-url https://github.com/owner/repo
```

| 参数 | 说明 |
|---|---|
| `--repo-url` | GitHub 仓库 URL，走 HTTP API 模式 |
| `--owner` | GitHub 用户名（本地模式） |
| `--repo` | 仓库名（本地模式） |
| `--sha` | commit SHA，默认取当前 git HEAD |
| `--license` | 许可证，默认 `MIT` |
| `--out` | 输出路径，默认 `examples/sample.json` |
| `--token` | GitHub Token，默认读环境变量 `GITHUB_TOKEN` |

HTTP 模式建议设置 token，避免匿名限流（每小时 60 次）：

```bash
export GITHUB_TOKEN=ghp_xxxxxxxx
python3 gen_sample.py --repo-url https://github.com/aa7-777/gh-qc-pipeline
```

## 质检规则

### 准入（一票否决）

- 公开可访问、非 fork、非归档
- 有 license、有有效 commit、非空
- 至少 1 个 Milestone
- 无敏感信息（AKIA / ghp_ / sk- / RSA 私钥）
- 大小 < 500MB

### Repo 质量（阈值 0.6）

| 维度 | 权重 |
|---|---|
| 活跃度 | 0.15 |
| 社区 | 0.10 |
| 文档 | 0.15 |
| 工程化 | 0.20 |
| 内容质量 | 0.20 |
| 安全 | 0.10 |
| 可复现 | 0.10 |

### Milestone 质量（阈值 0.6）

| 维度 | 权重 |
|---|---|
| 标题清晰度 | 0.15 |
| 描述完整度 | 0.15 |
| issue 数量 | 0.15 |
| issue 完整度 | 0.20 |
| 完成率 | 0.10 |
| 主题一致性 | 0.15 |
| 非机器人灌水 | 0.10 |

### 人工质检

单轮，基于 checklist 判定：

- 标题与描述是否清晰表达目标
- issue 内容是否真实、非灌水
- milestone 与 repo 主题是否一致
- 是否包含敏感或违规内容
- 是否适合作为任务/样本

## 状态机

```text
collected -> snapshot_fixed
  -> admission_passed / admission_rejected
  -> repo_qc_passed / repo_qc_rejected
  -> milestone_qc_passed / milestone_qc_rejected
  -> human_qc_passed / human_qc_rejected / human_qc_uncertain
  -> done / discarded
```

## 输出结构

```text
output/
  snapshots/<owner>__<name>/<commit_sha>/meta.json
  milestones/<owner>__<name>/<milestone_id>.json
  qc/admission.jsonl
  qc/repo_qc.jsonl
  qc/milestone_qc.jsonl
  qc/human_qc.jsonl
  state/<safe_sample_id>.json
```

## 项目结构

```text
gh-qc-pipeline/
├── README.md
├── PIPELINE.md
├── gen_sample.py
├── examples/
│   └── sample.json
└── gh_qc_skill/
    ├── __init__.py
    ├── SKILL.md
    ├── cli.py
    ├── models.py
    ├── pipeline.py
    ├── human_qc.py
    ├── storage.py
    └── rules/
        ├── __init__.py
        ├── admission.py
        ├── repo_qc.py
        └── milestone_qc.py
```

## 常见问题

### macOS 报 `SSL: CERTIFICATE_VERIFY_FAILED`

```bash
python3 -m pip install --user certifi
```

`gen_sample.py` 已自动使用 `certifi` 提供的证书。

### 报 `403 API rate limit exceeded`

设置 GitHub Token：

```bash
export GITHUB_TOKEN=ghp_xxxxxxxx
```

### 报 `reject: NO_LICENSE`

仓库需要添加 LICENSE 文件，或修改 `rules/admission.py` 放宽规则。

### 报 `reject: NO_MILESTONE`

在 GitHub 仓库创建至少一个 Milestone 并关联 issue。

### 输出被覆盖

`qc/*.jsonl` 是追加写；`state/*.json` 是覆盖写。  
保留历史可用时间戳：

```bash
--output ./output/$(date +%Y%m%d_%H%M%S)
```

## 扩展

- **新增规则**：在 `rules/` 下新建模块，返回 `QCResult`，在 `pipeline.py` 注册
- **调整阈值**：修改 `rules/repo_qc.py` / `rules/milestone_qc.py` 里的 `THRESHOLD`
- **替换 checklist**：修改 `human_qc.py` 中的 `HUMAN_CHECKLIST`
- **接入 LLM**：在 `rules/` 下新增 LLM 规则模块

## 版本

| 组件 | 版本 |
|---|---|
| pipeline | v1 |
| rules | v1 |
| schema | v1 |

## 相关文档

- `PIPELINE.md`：详细设计文档
- `gh_qc_skill/SKILL.md`：Skill 说明
